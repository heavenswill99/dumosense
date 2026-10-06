"""Five-family Health Reserve next-assessment benchmark on verified synthetic data.

Four supervised families predict the next recorded score/band. Isolation Forest
is an unsupervised current-assessment anomaly comparator, not a forecaster.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / ".deps"))

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, CatBoostRegressor
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix,
                             f1_score, log_loss, mean_absolute_error,
                             mean_squared_error, precision_score, r2_score, recall_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

VERSION = "HR_NEXT_ASSESSMENT_ML_1.0"
SEED = 42
FAMILIES = ("linear", "random_forest", "catboost", "lightgbm")
NUMERIC = (
    "score", "obligation_buffer_months", "health_resource_obligation_months",
    "current_preparedness_amount", "monthly_financial_obligations",
    "number_of_dependants", "prior_assessment_count",
    "prior_median_buffer_months", "delta_from_prior_median_months",
    "latest_prior_age_days",
)
CATEGORICAL = ("healthcare_coverage_status",)
FEATURES = NUMERIC + CATEGORICAL
BANDS = ("1-3", "4-6", "7-8", "9-10")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def band_index(score: int) -> int:
    return 0 if score <= 3 else 1 if score <= 6 else 2 if score <= 8 else 3


def user_split(user_id: str) -> str:
    bucket = int(hashlib.sha256(("health-reserve-42-" + str(user_id)).encode()).hexdigest()[:8], 16) % 10
    return "train" if bucket < 6 else "development" if bucket < 8 else "test"


def verified_baseline() -> tuple[Path, dict]:
    pointer_path = ROOT / "outputs" / "health_reserve_runs" / "latest_successful_health_reserve_run.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    run = ROOT / "outputs" / "health_reserve_runs" / pointer["run_id"]
    if run.resolve() != Path(pointer["path"]).resolve():
        raise ValueError("Baseline pointer path mismatch")
    if digest(run / "run_status.json") != pointer["status_sha256"]:
        raise ValueError("Baseline pointer status hash mismatch")
    status = json.loads((run / "run_status.json").read_text(encoding="utf-8"))
    if status["status"] != "completed":
        raise ValueError("Baseline run not completed")
    if digest(Path(status["input_path"])) != status["input_sha256"]:
        raise ValueError("Baseline input hash mismatch")
    for name, expected in status["artifacts"].items():
        if digest(run / name) != expected:
            raise ValueError(f"Baseline artifact hash mismatch: {name}")
    return run, status


def dataset() -> tuple[dict[str, pd.DataFrame], dict]:
    run, source_status = verified_baseline()
    baseline = pd.read_json(run / "assessments.jsonl", lines=True)
    raw = pd.read_csv(source_status["input_path"], usecols=[
        "reserve_assessment_id", "user_id", "assessed_at",
        "current_preparedness_amount", "monthly_financial_obligations",
    ])
    if baseline.reserve_assessment_id.duplicated().any() or raw.reserve_assessment_id.duplicated().any():
        raise ValueError("Duplicate assessment ID")
    frame = baseline.merge(
        raw.drop(columns=["user_id", "assessed_at"]), on="reserve_assessment_id",
        how="inner", validate="one_to_one",
    )
    if len(frame) != len(raw):
        raise ValueError("Baseline/raw row mismatch")
    frame["assessed_at"] = pd.to_datetime(frame["assessed_at"], utc=True)
    frame["number_of_dependants"] = pd.to_numeric(frame["number_of_dependants"], errors="raise")
    frame = frame.sort_values(["user_id", "assessed_at", "reserve_assessment_id"]).reset_index(drop=True)
    group = frame.groupby("user_id", sort=False)
    frame["next_score"] = group.score.shift(-1)
    frame["next_at"] = group.assessed_at.shift(-1)
    frame = frame.loc[frame.next_score.notna()].copy()
    frame["next_score"] = frame.next_score.astype(int)
    frame["next_band"] = frame.next_score.map(band_index)
    frame["horizon_days"] = (frame.next_at - frame.assessed_at).dt.total_seconds() / 86400
    if not frame.horizon_days.between(1, 90).all():
        raise ValueError("Next assessment horizon outside 1-90 days")
    frame["split"] = frame.user_id.map(user_split)
    cutoff = frame.loc[frame.split.eq("train"), "assessed_at"].quantile(0.6)
    cohorts = {
        "train": frame.loc[frame.split.eq("train") & frame.next_at.lt(cutoff)].copy(),
        "development": frame.loc[frame.split.eq("development") & frame.assessed_at.ge(cutoff)].copy(),
        "test": frame.loc[frame.split.eq("test") & frame.assessed_at.ge(cutoff)].copy(),
    }
    if any(part.empty for part in cohorts.values()):
        raise ValueError("Empty cohort")
    users = {name: set(part.user_id) for name, part in cohorts.items()}
    if any(users[a] & users[b] for a, b in
           (("train", "development"), ("train", "test"), ("development", "test"))):
        raise ValueError("User leakage")
    if cohorts["train"].next_at.max() >= cutoff:
        raise ValueError("Train labels extend beyond cutoff")
    if min(cohorts["development"].assessed_at.min(), cohorts["test"].assessed_at.min()) < cutoff:
        raise ValueError("Evaluation feature time before cutoff")
    if any(set(part.next_band) != set(range(4)) for part in cohorts.values()):
        raise ValueError("A cohort is missing a score band")
    meta = {
        "baseline_run_id": run.name, "baseline_status_sha256": digest(run / "run_status.json"),
        "cutoff_utc": cutoff.isoformat(),
        "cohorts": {name: {"examples": len(part), "users": part.user_id.nunique(),
                           "target_band_counts": {BANDS[i]: int((part.next_band == i).sum()) for i in range(4)},
                           "horizon_days_min": float(part.horizon_days.min()),
                           "horizon_days_median": float(part.horizon_days.median()),
                           "horizon_days_max": float(part.horizon_days.max())}
                    for name, part in cohorts.items()},
    }
    return cohorts, meta


def preprocessing(scale: bool = False) -> ColumnTransformer:
    numeric_steps = [("impute", SimpleImputer(strategy="median", add_indicator=True))]
    if scale:
        numeric_steps.append(("scale", StandardScaler()))
    return ColumnTransformer([
        ("numeric", Pipeline(numeric_steps), list(NUMERIC)),
        ("category", OneHotEncoder(handle_unknown="ignore"), list(CATEGORICAL)),
    ], sparse_threshold=0.0)


def configurations(family: str, task: str) -> list[dict]:
    if family == "linear":
        return [{"C": value} for value in (0.1, 1.0)] if task == "classification" else [
            {"alpha": value} for value in (1.0, 10.0)]
    if family == "random_forest":
        return [{"n_estimators": 150, "max_depth": depth, "min_samples_leaf": leaf}
                for depth, leaf in ((8, 5), (14, 10))]
    if family == "catboost":
        return [{"iterations": 200, "depth": depth, "learning_rate": 0.05}
                for depth in (4, 6)]
    if family == "lightgbm":
        return [{"n_estimators": 200, "num_leaves": leaves,
                 "min_child_samples": 30, "learning_rate": 0.05}
                for leaves in (15, 31)]
    raise ValueError(family)


def estimator(family: str, task: str, config: dict):
    if family == "linear":
        return (LogisticRegression(max_iter=2000, random_state=SEED, **config)
                if task == "classification" else Ridge(**config))
    if family == "random_forest":
        common = {"random_state": SEED, "n_jobs": 1, **config}
        return RandomForestClassifier(**common) if task == "classification" else RandomForestRegressor(**common)
    if family == "catboost":
        common = {"random_seed": SEED, "thread_count": 1, "verbose": False,
                  "allow_writing_files": False, **config}
        return CatBoostClassifier(loss_function="MultiClass", **common) if task == "classification" else CatBoostRegressor(loss_function="RMSE", **common)
    if family == "lightgbm":
        common = {"random_state": SEED, "n_jobs": 1, "verbosity": -1, **config}
        return LGBMClassifier(**common) if task == "classification" else LGBMRegressor(**common)
    raise ValueError(family)


def classification_metrics(y: np.ndarray, prediction: np.ndarray, probability: np.ndarray | None) -> dict:
    return {
        "accuracy": float(accuracy_score(y, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y, prediction)),
        "macro_precision": float(precision_score(y, prediction, labels=range(4), average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y, prediction, labels=range(4), average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y, prediction, labels=range(4), average="macro", zero_division=0)),
        "log_loss": float(log_loss(y, probability, labels=range(4))) if probability is not None else None,
        "confusion_matrix": confusion_matrix(y, prediction, labels=range(4)).astype(int).tolist(),
    }


def regression_metrics(y: np.ndarray, prediction: np.ndarray) -> dict:
    rounded = np.clip(np.rint(prediction), 1, 10).astype(int)
    return {
        "mae_score_points": float(mean_absolute_error(y, prediction)),
        "rmse_score_points": float(np.sqrt(mean_squared_error(y, prediction))),
        "r2": float(r2_score(y, prediction)),
        "rounded_exact_accuracy": float(np.mean(rounded == y)),
        "rounded_within_one_accuracy": float(np.mean(np.abs(rounded - y) <= 1)),
    }


def search_supervised(family: str, task: str, train: pd.DataFrame, development: pd.DataFrame):
    trials = []
    best = None
    y_train = train.next_band.to_numpy() if task == "classification" else train.next_score.to_numpy()
    y_dev = development.next_band.to_numpy() if task == "classification" else development.next_score.to_numpy()
    for config in configurations(family, task):
        model = Pipeline([
            ("features", preprocessing(scale=family == "linear")),
            ("model", estimator(family, task, config)),
        ])
        model.fit(train[list(FEATURES)], y_train)
        prediction = model.predict(development[list(FEATURES)])
        if task == "classification":
            probability = model.predict_proba(development[list(FEATURES)])
            measured = classification_metrics(y_dev, prediction, probability)
            rank = (measured["balanced_accuracy"], measured["macro_f1"])
        else:
            measured = regression_metrics(y_dev, prediction)
            rank = (-measured["mae_score_points"], -measured["rmse_score_points"])
        trials.append({"config": config, "development": measured})
        if best is None or rank > best[0]:
            best = (rank, model, config, measured)
    assert best is not None
    return best[1], {"selected_config": best[2], "development": best[3], "trials": trials}


def execute(output: Path) -> dict:
    cohorts, meta = dataset()
    train, development, test = (cohorts[name] for name in ("train", "development", "test"))
    selected = {}
    for family in FAMILIES:
        print("Searching", family, flush=True)
        for task in ("classification", "regression"):
            selected[(family, task)] = search_supervised(family, task, train, development)

    print("Scoring frozen selections on test users", flush=True)
    weights = output / "weights"
    weights.mkdir()
    truth_band = test.next_band.to_numpy()
    truth_score = test.next_score.to_numpy()
    predictions = test[["reserve_assessment_id", "user_id", "assessed_at",
                        "next_at", "score", "next_score", "next_band"]].copy()
    metrics = {
        "model_version": VERSION, "release_status": "synthetic_engineering_validation_only",
        "target": "next recorded assessment's fixed 1-10 buffer score and four-level band",
        "target_limitation": "Synthetic next-assessment score, not care affordability, medical risk, or a clinical outcome.",
        "test_reuse": "The first ML iteration evaluated these same synthetic test users; this revised run is exploratory repeated-test evidence, not a fresh holdout.",
        "features": list(FEATURES),
        "excluded": ["estimated_healthcare_exposure", "preparedness_target", "preparedness_gap",
                     "preparedness_ratio", "reserve_status", "next_score", "next_band", "next_at",
                     "horizon_days", "user_id", "reserve_assessment_id"],
        **meta,
        "baselines": {
            "persistence_regression": regression_metrics(truth_score, test.score.to_numpy()),
            "persistence_classification": classification_metrics(
                truth_band, test.score.map(band_index).to_numpy(), None,
            ),
            "train_median_regression": regression_metrics(
                truth_score, np.full(len(test), float(train.next_score.median()))),
        },
        "families": {},
    }
    for family in FAMILIES:
        classifier, csearch = selected[(family, "classification")]
        probabilities = classifier.predict_proba(test[list(FEATURES)])
        classes = classifier.named_steps["model"].classes_.astype(int)
        if not np.array_equal(classes, np.arange(4)):
            raise ValueError(f"Unexpected classes for {family}")
        classified = classifier.predict(test[list(FEATURES)]).astype(int)
        regressor, rsearch = selected[(family, "regression")]
        predicted_score = regressor.predict(test[list(FEATURES)])
        metrics["families"][family] = {
            "classification": {**csearch, "test": classification_metrics(truth_band, classified, probabilities)},
            "regression": {**rsearch, "test": regression_metrics(truth_score, predicted_score)},
        }
        predictions[family + "_band"] = classified
        predictions[family + "_score"] = predicted_score
        for class_index in range(4):
            predictions[f"{family}_probability_{class_index}"] = probabilities[:, class_index]
        for task, model in (("classifier", classifier), ("regressor", regressor)):
            path = weights / f"{family}_{task}.joblib"
            joblib.dump(model, path, compress=3)
            loaded = joblib.load(path)
            sample = test[list(FEATURES)].iloc[:10]
            if task == "classifier":
                if not np.allclose(loaded.predict_proba(sample), model.predict_proba(sample)):
                    raise ValueError(f"Classifier reload mismatch: {family}")
            elif not np.allclose(loaded.predict(sample), model.predict(sample)):
                raise ValueError(f"Regressor reload mismatch: {family}")

    anomaly = Pipeline([
        ("features", preprocessing(scale=True)),
        ("model", IsolationForest(n_estimators=200, max_samples=256,
                                  contamination=0.10, random_state=SEED, n_jobs=1)),
    ])
    anomaly.fit(train[list(FEATURES)])
    train_scores = -anomaly.score_samples(train[list(FEATURES)])
    development_scores = -anomaly.score_samples(development[list(FEATURES)])
    train_threshold = float(np.quantile(train_scores, 0.90))
    calibrated_threshold = float(np.quantile(development_scores, 0.90))
    test_scores = -anomaly.score_samples(test[list(FEATURES)])
    predictions["isolation_forest_score"] = test_scores
    joblib.dump(anomaly, weights / "isolation_forest.joblib", compress=3)
    if not np.allclose(joblib.load(weights / "isolation_forest.joblib").score_samples(
            test[list(FEATURES)].iloc[:10]), anomaly.score_samples(test[list(FEATURES)].iloc[:10])):
        raise ValueError("Isolation Forest reload mismatch")
    metrics["families"]["isolation_forest"] = {
        "task": "unsupervised current-assessment anomaly comparator",
        "threshold_percentile": 0.90,
        "train_score_threshold": train_threshold,
        "development_calibrated_threshold": calibrated_threshold,
        "test_flagged_at_train_threshold": int(np.sum(test_scores >= train_threshold)),
        "test_flagged_fraction_at_train_threshold": float(np.mean(test_scores >= train_threshold)),
        "test_flagged_at_development_threshold": int(np.sum(test_scores >= calibrated_threshold)),
        "test_flagged_fraction_at_development_threshold": float(np.mean(test_scores >= calibrated_threshold)),
        "calibration_note": "Development users calibrate the anomaly threshold; the train-only threshold and its test flag rate remain visible as a distribution-shift diagnostic.",
        "train_score_median": float(np.median(train_scores)),
        "development_score_median": float(np.median(development_scores)),
        "test_score_median": float(np.median(test_scores)),
        "accuracy": None, "reason": "No independently labelled anomalies.",
    }
    predictions.to_csv(output / "test_predictions.csv", index=False)
    write_json(output / "metrics.json", metrics)
    return metrics


def package_run(output: Path, status: dict) -> Path:
    package = ROOT / "weights" / status["run_id"]
    package.mkdir(parents=True, exist_ok=False)
    (package / "weights").mkdir()
    shutil.copy2(output / "metrics.json", package / "metrics.json")
    for source in sorted((output / "weights").glob("*.joblib")):
        shutil.copy2(source, package / "weights" / source.name)
    files = [package / "metrics.json", *sorted((package / "weights").glob("*.joblib"))]
    if len(files) != 10:
        raise ValueError("Expected 9 estimators and metrics")
    write_json(package / "package_manifest.json", {
        "model_version": VERSION, "source_run_id": status["run_id"],
        "source_status_sha256": digest(output / "run_status.json"),
        "release_status": "synthetic_engineering_validation_only",
        "files": {str(path.relative_to(package)).replace("\\", "/"): digest(path) for path in files},
    })
    return package


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "health_reserve_ml_runs")
    args = parser.parse_args()
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    run_id = "hr_ml_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    output = output_root / run_id
    output.mkdir(exist_ok=False)
    status = {"run_id": run_id, "status": "running", "model_version": VERSION}
    write_json(output / "run_status.json", status)
    try:
        metrics = execute(output)
        status.update(
            status="completed", finished_at=datetime.now(timezone.utc).isoformat(),
            baseline_run_id=metrics["baseline_run_id"],
            source_sha256={"train_ml_models.py": digest(Path(__file__))},
            dependencies={"sklearn": __import__("sklearn").__version__,
                          "catboost": __import__("catboost").__version__,
                          "lightgbm": __import__("lightgbm").__version__},
            artifacts={str(path.relative_to(output)).replace("\\", "/"): digest(path)
                       for path in output.rglob("*") if path.is_file() and path.name != "run_status.json"},
        )
        write_json(output / "run_status.json", status)
        package = package_run(output, status)
        write_json(output_root / "latest_successful_health_reserve_ml_run.json", {
            "run_id": run_id, "path": str(output.resolve()),
            "status_sha256": digest(output / "run_status.json"),
            "package_path": str(package.resolve()),
        })
        print(json.dumps({"run_id": run_id, "run": str(output), "package": str(package),
                          "status": "completed"}, indent=2))
        return 0
    except BaseException as exc:
        status.update(status="failed", error=str(exc), traceback=traceback.format_exc())
        write_json(output / "run_status.json", status)
        print(traceback.format_exc(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
