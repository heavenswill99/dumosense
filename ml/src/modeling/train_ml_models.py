"""Train five research model families on verified synthetic MindGuard data.

Four families have binary classification and two regression estimators each.
Isolation Forest is an unsupervised anomaly comparator, not a regression model.
All model selection uses development users; the test users are scored once.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
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
from sklearn.metrics import (average_precision_score, balanced_accuracy_score, brier_score_loss,
                             confusion_matrix, f1_score, log_loss, mean_absolute_error,
                             mean_squared_error, precision_score, r2_score, recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from mvp_pipeline import sha, write_json

SEED = 42
FAMILIES = ("linear", "random_forest", "catboost", "lightgbm", "isolation_forest")
PRIOR_FEATURES = (
    "difficulty_level", "cognitive_domain", "time_days", "per_domain_median", "per_domain_mad",
    "per_domain_n", "per_domain_age_days", "cross_domain_median", "cross_domain_mad",
    "cross_domain_n", "cross_domain_age_days", "adjusted_median", "adjusted_mad",
    "adjusted_n", "rt_median", "rt_mad", "rt_n", "rt_age_days",
)
CURRENT_FEATURES = (
    "accuracy_rate", "log_rt", "per_domain_z", "cross_domain_z", "adjusted_z", "rt_z",
)
CLASS_FEATURES = PRIOR_FEATURES + CURRENT_FEATURES
CAT = ["cognitive_domain"]


def verify_source() -> tuple[Path, dict, dict]:
    pointer = json.loads((ROOT / "outputs" / "latest_successful_run.json").read_text(encoding="utf-8"))
    run = Path(pointer["path"])
    if not run.is_dir() or sha(run / "manifest.json") != pointer["manifest_sha256"]:
        raise ValueError("Latest statistical run pointer/manifest is invalid")
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "completed" or pointer["release_status"] != "internal_validation_only":
        raise ValueError("Expected completed internal statistical run")
    needed = ["session_intelligence_results.jsonl", "ground_truth_session_alignment.csv",
              "statistical_models_results.json", "training_reference.csv"]
    for name in needed:
        if sha(run / name) != manifest["artifacts"][name]["sha256"]:
            raise ValueError(f"Source artifact changed: {name}")
    for name in ["cognitive_results", "user_profiles"]:
        if sha(Path(manifest["inputs"][name]["path"])) != manifest["inputs"][name]["sha256"]:
            raise ValueError(f"Source input changed: {name}")
    return run, pointer, manifest


def load_features(run: Path, manifest: dict, cutoff: pd.Timestamp) -> pd.DataFrame:
    difficulty = pd.read_csv(manifest["inputs"]["cognitive_results"]["path"],
                             usecols=["session_id", "difficulty_level"])
    if difficulty.session_id.duplicated().any():
        raise ValueError("Duplicate cognitive session")
    origin = None
    rows = []
    with (run / "session_intelligence_results.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            timestamp = pd.Timestamp(row["index_time"])
            start = pd.Timestamp(row["started_at"])
            if row["split"] == "train" and timestamp < cutoff and (origin is None or start < origin):
                origin = start
            item = {
                "session_id": row["session_id"], "user_id": row["user_id"],
                "cognitive_domain": row["cognitive_domain"], "index_time": timestamp,
                "started_at": start, "split": row["split"],
                "accuracy_rate": row["current_performance"]["accuracy"],
                "log_rt": np.log(row["current_performance"]["median_rt_ms"]),
                "median_rt_ms": row["current_performance"]["median_rt_ms"],
            }
            for name in ("per_domain", "cross_domain", "adjusted", "rt"):
                baseline = row["baselines"][name]
                item[name + "_median"] = baseline["median"]
                item[name + "_mad"] = baseline["mad"]
                item[name + "_n"] = baseline["n_valid"]
                if name != "adjusted":
                    prior_time = baseline["ts_max_prior"]
                    item[name + "_age_days"] = ((timestamp - pd.Timestamp(prior_time)).total_seconds() / 86400
                                                  if prior_time else np.nan)
                item[name + "_z"] = row["deviation"][name]
            rows.append(item)
    if origin is None:
        raise ValueError("No training observations before cutoff")
    frame = pd.DataFrame(rows).merge(difficulty, on="session_id", how="left", validate="one_to_one")
    if frame.session_id.duplicated().any() or frame.difficulty_level.isna().any():
        raise ValueError("Invalid feature join")
    frame["time_days"] = (frame.started_at - origin).dt.total_seconds() / 86400
    # The source run's adjusted references were trained before the cutoff.
    frame["period"] = np.where(frame.index_time < cutoff, "before", "after")
    if not np.isfinite(frame[["accuracy_rate", "log_rt", "median_rt_ms"]].to_numpy(dtype=float)).all():
        raise ValueError("Invalid current outcomes")
    return frame


def cohort(frame: pd.DataFrame, split: str, cutoff: pd.Timestamp) -> pd.DataFrame:
    before = split == "train"
    return frame.loc[frame.split.eq(split) & (frame.index_time.lt(cutoff) if before else frame.index_time.ge(cutoff))].copy()


def preprocessor(features: tuple[str, ...], *, scale: bool) -> ColumnTransformer:
    num = [name for name in features if name not in CAT]
    numeric_steps = [("fill", SimpleImputer(strategy="median", add_indicator=True))]
    if scale:
        numeric_steps.append(("scale", StandardScaler()))
    return ColumnTransformer([
        ("numeric", Pipeline(numeric_steps), num),
        ("domain", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT),
    ], sparse_threshold=0)


def estimator(family: str, task: str):
    if family == "linear":
        return LogisticRegression(max_iter=2000, random_state=SEED) if task == "classification" else Ridge(alpha=10.0)
    if family == "random_forest":
        common = dict(n_estimators=120, max_depth=10, min_samples_leaf=10, random_state=SEED, n_jobs=1)
        return RandomForestClassifier(**common) if task == "classification" else RandomForestRegressor(**common)
    if family == "catboost":
        common = dict(iterations=180, depth=5, learning_rate=0.05, random_seed=SEED,
                      thread_count=1, verbose=False, allow_writing_files=False)
        return CatBoostClassifier(loss_function="Logloss", **common) if task == "classification" else CatBoostRegressor(loss_function="RMSE", **common)
    if family == "lightgbm":
        common = dict(n_estimators=180, num_leaves=15, min_child_samples=30,
                      learning_rate=0.05, random_state=SEED, n_jobs=1, verbosity=-1)
        return LGBMClassifier(**common) if task == "classification" else LGBMRegressor(**common)
    raise ValueError(f"Unsupported supervised family: {family}")


def binary_metrics(y: np.ndarray, scores: np.ndarray, threshold: float, *, probabilities: bool = True) -> dict:
    predictions = (scores >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=[0, 1]).ravel()
    result = {
        "n": int(len(y)), "positives": int(y.sum()), "threshold": float(threshold),
        "TP": int(tp), "TN": int(tn), "FP": int(fp), "FN": int(fn),
        "sensitivity": float(recall_score(y, predictions, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else None,
        "precision": float(precision_score(y, predictions, zero_division=0)),
        "f1": float(f1_score(y, predictions, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y, predictions)),
        "false_positive_rate": float(fp / (tn + fp)) if tn + fp else None,
        "brier": float(brier_score_loss(y, scores)) if probabilities else None,
        "log_loss": float(log_loss(y, np.column_stack([1 - scores, scores]), labels=[0, 1])) if probabilities else None,
        "roc_auc": float(roc_auc_score(y, scores)) if len(np.unique(y)) == 2 else None,
        "average_precision": float(average_precision_score(y, scores)) if y.sum() else None,
        "score_type": "probability" if probabilities else "unnormalized_anomaly_score",
    }
    return result


def select_threshold(y: np.ndarray, probability: np.ndarray) -> tuple[float, list[dict]]:
    grid = np.round(np.arange(0.10, 0.91, 0.05), 2)
    candidates = [binary_metrics(y, probability, float(t)) for t in grid]
    chosen = max(candidates, key=lambda m: (m["balanced_accuracy"], -abs(m["threshold"] - 0.5)))
    return chosen["threshold"], candidates


def regression_metrics(y: np.ndarray, prediction: np.ndarray) -> dict:
    return {"n": int(len(y)), "mae": float(mean_absolute_error(y, prediction)),
            "rmse": float(np.sqrt(mean_squared_error(y, prediction))),
            "r2": float(r2_score(y, prediction)),
            "median_error": float(np.median(prediction - y)),
            "p90_absolute_error": float(np.quantile(np.abs(prediction - y), 0.90))}


def subgroup_metrics(frame: pd.DataFrame, y: np.ndarray, probability: np.ndarray, threshold: float,
                     profiles: pd.DataFrame) -> dict:
    data = frame[["user_id"]].reset_index(drop=True).merge(profiles, on="user_id", how="left", validate="many_to_one")
    output = {}
    for column in ("age_group", "sex"):
        output[column] = {}
        for value, index in data.groupby(column, dropna=False).indices.items():
            idx = np.asarray(index, dtype=int)
            if len(idx) >= 20 and len(np.unique(y[idx])) == 2:
                output[column][str(value)] = binary_metrics(y[idx], probability[idx], threshold)
            else:
                output[column][str(value)] = {"n": int(len(idx)), "status": "too_few_rows_or_one_class"}
    return output


def train(run: Path, pointer: dict, manifest: dict, output: Path) -> dict:
    summary = json.loads((run / "statistical_models_results.json").read_text(encoding="utf-8"))
    cutoff = pd.Timestamp(summary["selection"]["cutoff"])
    features = load_features(run, manifest, cutoff)
    labels = pd.read_csv(run / "ground_truth_session_alignment.csv", usecols=["session_id", "trajectory_type"])
    labels = labels.loc[labels.trajectory_type.isin(["stable_pattern", "temporary_change", "gradual_change"])]
    if labels.session_id.duplicated().any():
        raise ValueError("Ambiguous labels")
    labelled = features.merge(labels, on="session_id", how="inner", validate="one_to_one")
    train_class = cohort(labelled, "train", cutoff)
    dev_class = cohort(labelled, "development", cutoff)
    test_class = cohort(labelled, "test", cutoff)
    train_reg = cohort(features, "train", cutoff)
    dev_reg = cohort(features, "development", cutoff)
    test_reg = cohort(features, "test", cutoff)
    if any(x.empty for x in [train_class, dev_class, test_class, train_reg, dev_reg, test_reg]):
        raise ValueError("Empty train/development/test cohort")
    train_users = set(train_reg.user_id)
    dev_users = set(dev_reg.user_id)
    test_users = set(test_reg.user_id)
    if train_users & dev_users or train_users & test_users or dev_users & test_users:
        raise ValueError("User leakage across splits")
    if train_reg.index_time.max() >= cutoff or min(dev_reg.index_time.min(), test_reg.index_time.min()) < cutoff:
        raise ValueError("Time leakage across cutoff")
    y_train = train_class.trajectory_type.ne("stable_pattern").to_numpy(dtype=int)
    y_dev = dev_class.trajectory_type.ne("stable_pattern").to_numpy(dtype=int)
    y_test = test_class.trajectory_type.ne("stable_pattern").to_numpy(dtype=int)
    if any(len(np.unique(y)) != 2 for y in [y_train, y_dev, y_test]):
        raise ValueError("Both classes required in every labelled cohort")
    profile_path = manifest["inputs"]["user_profiles"]["path"]
    profiles = pd.read_csv(profile_path, usecols=["user_id", "age_group", "sex"])
    if profiles.user_id.duplicated().any():
        raise ValueError("Duplicate user profile")

    model_dir = output / "weights"
    model_dir.mkdir(parents=True)
    metrics = {
        "source_statistical_run": pointer["run_id"], "source_manifest_sha256": pointer["manifest_sha256"],
        "cutoff": cutoff.isoformat(), "seed": SEED,
        "cohorts": {"classification": {"train": len(train_class), "development": len(dev_class), "test": len(test_class)},
                    "regression": {"train": len(train_reg), "development": len(dev_reg), "test": len(test_reg)},
                    "user_overlap": 0},
        "targets": {"classification": "synthetic temporary or gradual change vs stable at current session",
                    "accuracy_regression": "current accuracy from prior history and task settings",
                    "rt_regression": "current log median RT from prior history and task settings"},
        "features": {"classification": list(CLASS_FEATURES), "regression": list(PRIOR_FEATURES)},
        "families": {},
        "benchmarks": {},
        "release_status": "engineering_validation_only",
    }
    baseline_probability = float(y_train.mean())
    metrics["benchmarks"]["classification_no_alert"] = binary_metrics(y_test, np.zeros(len(y_test)), 0.5)
    metrics["benchmarks"]["classification_prevalence"] = binary_metrics(y_test, np.full(len(y_test), baseline_probability), 0.5)
    for target, column in [("accuracy", "accuracy_rate"), ("rt", "log_rt")]:
        center = float(train_reg[column].mean())
        truth = test_reg[column].to_numpy()
        if target == "rt":
            truth = np.exp(truth); prediction = np.full(len(truth), np.exp(center))
        else:
            prediction = np.full(len(truth), center)
        metrics["benchmarks"][target + "_train_mean"] = regression_metrics(truth, prediction)

    test_predictions = test_class[["session_id", "user_id", "trajectory_type"]].reset_index(drop=True).copy()
    reg_predictions = test_reg[["session_id", "user_id", "accuracy_rate", "median_rt_ms"]].reset_index(drop=True).copy()
    for family in FAMILIES[:4]:
        print("Training", family, flush=True)
        result = {}
        classifier = Pipeline([
            ("features", preprocessor(CLASS_FEATURES, scale=family == "linear")),
            ("model", estimator(family, "classification")),
        ])
        classifier.fit(train_class[list(CLASS_FEATURES)], y_train)
        dev_probability = classifier.predict_proba(dev_class[list(CLASS_FEATURES)])[:, 1]
        threshold, sweep = select_threshold(y_dev, dev_probability)
        test_probability = classifier.predict_proba(test_class[list(CLASS_FEATURES)])[:, 1]
        if not np.isfinite(test_probability).all():
            raise ValueError(f"Nonfinite classification probabilities: {family}")
        result["classification"] = {
            "development_threshold": threshold,
            "development": binary_metrics(y_dev, dev_probability, threshold),
            "test": binary_metrics(y_test, test_probability, threshold),
            "subgroups": subgroup_metrics(test_class, y_test, test_probability, threshold, profiles),
            "threshold_grid": sweep,
        }
        test_predictions[family + "_probability"] = test_probability
        classifier_file = model_dir / (family + "_classifier.joblib")
        joblib.dump(classifier, classifier_file, compress=3)
        reloaded = joblib.load(classifier_file)
        if not np.allclose(reloaded.predict_proba(test_class[list(CLASS_FEATURES)])[:, 1], test_probability):
            raise ValueError(f"Reloaded classifier mismatch: {family}")
        for target, column in [("accuracy", "accuracy_rate"), ("rt", "log_rt")]:
            regressor = Pipeline([
                ("features", preprocessor(PRIOR_FEATURES, scale=family == "linear")),
                ("model", estimator(family, "regression")),
            ])
            regressor.fit(train_reg[list(PRIOR_FEATURES)], train_reg[column].to_numpy())
            predicted = regressor.predict(test_reg[list(PRIOR_FEATURES)])
            truth = test_reg[column].to_numpy()
            if target == "rt":
                predicted = np.exp(predicted); truth = np.exp(truth)
            if not np.isfinite(predicted).all():
                raise ValueError(f"Nonfinite regression predictions: {family}/{target}")
            result[target + "_regression"] = {"test": regression_metrics(truth, predicted),
                                              "unit": "milliseconds" if target == "rt" else "accuracy_fraction"}
            reg_predictions[family + "_" + target] = predicted
            path = model_dir / (family + "_" + target + "_regressor.joblib")
            joblib.dump(regressor, path, compress=3)
            if not np.allclose(joblib.load(path).predict(test_reg[list(PRIOR_FEATURES)]),
                               regressor.predict(test_reg[list(PRIOR_FEATURES)])):
                raise ValueError(f"Reloaded regressor mismatch: {family}/{target}")
        metrics["families"][family] = result

    print("Training isolation_forest", flush=True)
    anomaly = Pipeline([
        ("features", preprocessor(CLASS_FEATURES, scale=True)),
        ("model", IsolationForest(n_estimators=160, max_samples="auto", contamination=0.05,
                                  random_state=SEED, n_jobs=1)),
    ])
    # This estimator sees no labels. The 5% cutoff is fixed from its training scores.
    anomaly.fit(train_reg[list(CLASS_FEATURES)])
    train_scores = -anomaly.score_samples(train_reg[list(CLASS_FEATURES)])
    threshold = float(np.quantile(train_scores, 0.95))
    test_scores = -anomaly.score_samples(test_class[list(CLASS_FEATURES)])
    anomaly_result = binary_metrics(y_test, test_scores, threshold, probabilities=False)
    metrics["families"]["isolation_forest"] = {
        "test": anomaly_result,
        "fit": "Unsupervised on all train-user sessions before cutoff; no labels used",
        "threshold": "Fixed 95th percentile of training anomaly scores",
        "score_threshold": threshold,
        "regression": "not applicable",
    }
    test_predictions["isolation_forest_score"] = test_scores
    anomaly_file = model_dir / "isolation_forest.joblib"
    joblib.dump(anomaly, anomaly_file, compress=3)
    if not np.allclose(joblib.load(anomaly_file).score_samples(test_class[list(CLASS_FEATURES)]), -test_scores):
        raise ValueError("Reloaded anomaly model mismatch")
    test_predictions.to_csv(output / "classification_test_predictions.csv", index=False)
    reg_predictions.to_csv(output / "regression_test_predictions.csv", index=False)
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "ml_runs")
    args = parser.parse_args()
    run_id = "ml_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    output = args.output_root / run_id
    output.mkdir(parents=True, exist_ok=False)
    status = {"run_id": run_id, "status": "running", "started_at": datetime.now(timezone.utc).isoformat()}
    write_json(output / "run_status.json", status)
    try:
        run, pointer, manifest = verify_source()
        results = train(run, pointer, manifest, output)
        write_json(output / "metrics.json", results)
        status.update(status="completed", finished_at=datetime.now(timezone.utc).isoformat(),
                      statistical_source_run=pointer["run_id"],
                      dependencies={"sklearn": __import__("sklearn").__version__,
                                    "catboost": __import__("catboost").__version__,
                                    "lightgbm": __import__("lightgbm").__version__},
                      artifacts={str(p.relative_to(output)): {"bytes": p.stat().st_size, "sha256": sha(p)}
                                 for p in output.rglob("*") if p.is_file() and p.name != "run_status.json"})
        write_json(output / "run_status.json", status)
        write_json(args.output_root / "latest_successful_ml_run.json", {"run_id": run_id,
                    "path": str(output.resolve()), "status_sha256": sha(output / "run_status.json")})
        print(json.dumps({"run_id": run_id, "path": str(output), "status": "completed"}, indent=2))
        return 0
    except BaseException as exc:
        status.update(status="failed", finished_at=datetime.now(timezone.utc).isoformat(),
                      error=str(exc), traceback=traceback.format_exc())
        write_json(output / "run_status.json", status)
        print(traceback.format_exc(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
