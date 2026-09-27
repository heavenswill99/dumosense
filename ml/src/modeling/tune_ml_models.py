"""Bounded development-only search for all five MindGuard ML model families."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
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
from sklearn.ensemble import IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import average_precision_score, balanced_accuracy_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline

from mvp_pipeline import sha, write_json
from modeling.train_ml_models import (SEED, FAMILIES, PRIOR_FEATURES, CLASS_FEATURES,
                             preprocessor, binary_metrics, regression_metrics, load_features, cohort, verify_source)


def configurations(family: str, task: str) -> list[dict]:
    if family == "linear":
        return [{"C": c} for c in (0.1, 1.0, 10.0, 100.0)] if task == "classification" else [
            {"alpha": alpha} for alpha in (0.1, 1.0, 10.0, 100.0)]
    if family == "random_forest":
        return [{"n_estimators": 100, "max_depth": depth, "min_samples_leaf": leaf}
                for depth in (8, 14) for leaf in (3, 10)]
    if family == "catboost":
        return [{"iterations": 250, "depth": depth, "learning_rate": rate}
                for depth in (4, 6) for rate in (0.03, 0.08)]
    if family == "lightgbm":
        return [{"n_estimators": 250, "num_leaves": leaves, "min_child_samples": child,
                 "learning_rate": 0.05} for leaves in (15, 31) for child in (20, 50)]
    if family == "isolation_forest":
        return [{"n_estimators": trees, "max_samples": samples, "contamination": "auto"}
                for trees in (100, 200) for samples in (256, 1024)]
    raise ValueError(family)


def make_estimator(family: str, task: str, config: dict):
    if family == "linear":
        return LogisticRegression(max_iter=2000, random_state=SEED, **config) if task == "classification" else Ridge(**config)
    if family == "random_forest":
        common = {"random_state": SEED, "n_jobs": 1, **config}
        return RandomForestClassifier(**common) if task == "classification" else RandomForestRegressor(**common)
    if family == "catboost":
        common = {"random_seed": SEED, "thread_count": 1, "verbose": False,
                  "allow_writing_files": False, **config}
        return CatBoostClassifier(loss_function="Logloss", **common) if task == "classification" else CatBoostRegressor(loss_function="RMSE", **common)
    if family == "lightgbm":
        common = {"random_state": SEED, "n_jobs": 1, "verbosity": -1, **config}
        return LGBMClassifier(**common) if task == "classification" else LGBMRegressor(**common)
    if family == "isolation_forest" and task == "anomaly":
        return IsolationForest(random_state=SEED, n_jobs=1, **config)
    raise ValueError(f"Unsupported estimator {family}/{task}")


def classifier_search(family: str, train: pd.DataFrame, dev: pd.DataFrame,
                      y_train: np.ndarray, y_dev: np.ndarray) -> tuple[Pipeline, dict, list[dict]]:
    candidates = []
    best = None
    for config in configurations(family, "classification"):
        pipeline = Pipeline([("features", preprocessor(CLASS_FEATURES, scale=family == "linear")),
                             ("model", make_estimator(family, "classification", config))])
        pipeline.fit(train[list(CLASS_FEATURES)], y_train)
        probability = pipeline.predict_proba(dev[list(CLASS_FEATURES)])[:, 1]
        for threshold in np.round(np.arange(0.05, 0.951, 0.025), 3):
            measured = binary_metrics(y_dev, probability, float(threshold))
            rank = (measured["balanced_accuracy"], measured["f1"], -abs(float(threshold) - 0.5))
            candidates.append({"config": config, "threshold": float(threshold),
                               "balanced_accuracy": measured["balanced_accuracy"],
                               "f1": measured["f1"], "false_positive_rate": measured["false_positive_rate"]})
            if best is None or rank > best[0]:
                best = (rank, pipeline, config, float(threshold), measured)
    assert best is not None
    return best[1], {"config": best[2], "threshold": best[3], "development": best[4]}, candidates


def regressor_search(family: str, target: str, train: pd.DataFrame, dev: pd.DataFrame) -> tuple[Pipeline, dict, list[dict]]:
    column = "accuracy_rate" if target == "accuracy" else "log_rt"
    observed = dev[column].to_numpy()
    if target == "rt":
        observed = np.exp(observed)
    candidates = []
    best = None
    for config in configurations(family, "regression"):
        pipeline = Pipeline([("features", preprocessor(PRIOR_FEATURES, scale=family == "linear")),
                             ("model", make_estimator(family, "regression", config))])
        pipeline.fit(train[list(PRIOR_FEATURES)], train[column].to_numpy())
        predicted = pipeline.predict(dev[list(PRIOR_FEATURES)])
        if target == "rt":
            predicted = np.exp(predicted)
        measured = regression_metrics(observed, predicted)
        candidates.append({"config": config, "rmse": measured["rmse"], "mae": measured["mae"]})
        rank = (measured["rmse"], measured["mae"])
        if best is None or rank < best[0]:
            best = (rank, pipeline, config, measured)
    assert best is not None
    return best[1], {"config": best[2], "development": best[3]}, candidates


def anomaly_search(train: pd.DataFrame, dev: pd.DataFrame,
                   y_dev: np.ndarray) -> tuple[Pipeline, dict, list[dict]]:
    candidates = []
    best = None
    for config in configurations("isolation_forest", "anomaly"):
        pipeline = Pipeline([("features", preprocessor(CLASS_FEATURES, scale=True)),
                             ("model", make_estimator("isolation_forest", "anomaly", config))])
        pipeline.fit(train[list(CLASS_FEATURES)])
        train_scores = -pipeline.score_samples(train[list(CLASS_FEATURES)])
        dev_scores = -pipeline.score_samples(dev[list(CLASS_FEATURES)])
        for percentile in np.round(np.arange(0.70, 0.991, 0.02), 2):
            threshold = float(np.quantile(train_scores, percentile))
            measured = binary_metrics(y_dev, dev_scores, threshold, probabilities=False)
            candidates.append({"config": config, "training_percentile": float(percentile),
                               "balanced_accuracy": measured["balanced_accuracy"],
                               "f1": measured["f1"], "false_positive_rate": measured["false_positive_rate"]})
            rank = (measured["balanced_accuracy"], measured["f1"], -abs(float(percentile) - 0.95))
            if best is None or rank > best[0]:
                best = (rank, pipeline, config, float(percentile), threshold, measured)
    assert best is not None
    return best[1], {"config": best[2], "training_percentile": best[3],
                     "score_threshold": best[4], "development": best[5]}, candidates


def with_accuracy(result: dict) -> dict:
    return {**result, "accuracy": (result["TP"] + result["TN"]) / result["n"]}


def execute(output: Path) -> dict:
    source_run, pointer, source_manifest = verify_source()
    source_summary = json.loads((source_run / "statistical_models_results.json").read_text(encoding="utf-8"))
    cutoff = pd.Timestamp(source_summary["selection"]["cutoff"])
    frame = load_features(source_run, source_manifest, cutoff)
    labels = pd.read_csv(source_run / "ground_truth_session_alignment.csv", usecols=["session_id", "trajectory_type"])
    labels = labels.loc[labels.trajectory_type.isin(["stable_pattern", "temporary_change", "gradual_change"])]
    if labels.session_id.duplicated().any():
        raise ValueError("Ambiguous labels")
    labelled = frame.merge(labels, on="session_id", how="inner", validate="one_to_one")
    cls = {s: cohort(labelled, s, cutoff) for s in ("train", "development", "test")}
    reg = {s: cohort(frame, s, cutoff) for s in ("train", "development", "test")}
    if any(data.empty for data in [*cls.values(), *reg.values()]):
        raise ValueError("Empty train/development/test cohort")
    user_sets = {s: set(reg[s].user_id) for s in reg}
    if any(user_sets[a] & user_sets[b] for a, b in (("train", "development"), ("train", "test"), ("development", "test"))):
        raise ValueError("User overlap")
    if reg["train"].index_time.max() >= cutoff or min(reg["development"].index_time.min(), reg["test"].index_time.min()) < cutoff:
        raise ValueError("Time overlap")
    y = {s: cls[s].trajectory_type.ne("stable_pattern").to_numpy(dtype=int) for s in cls}
    if any(len(np.unique(v)) != 2 for v in y.values()):
        raise ValueError("A cohort has only one class")

    print("Selecting all settings on development users", flush=True)
    selected = {}
    search = {}
    for family in FAMILIES[:4]:
        print("Searching", family, flush=True)
        model, choice, candidates = classifier_search(family, cls["train"], cls["development"], y["train"], y["development"])
        selected[(family, "classification")] = (model, choice)
        search[family + "_classification"] = candidates
        for target in ("accuracy", "rt"):
            model, choice, candidates = regressor_search(family, target, reg["train"], reg["development"])
            selected[(family, target)] = (model, choice)
            search[family + "_" + target] = candidates
    model, choice, candidates = anomaly_search(reg["train"], cls["development"], y["development"])
    selected[("isolation_forest", "anomaly")] = (model, choice)
    search["isolation_forest"] = candidates
    write_json(output / "development_search.json", search)

    print("Scoring frozen selections on test users", flush=True)
    weights = output / "weights"
    weights.mkdir()
    predictions = cls["test"][["session_id", "user_id", "trajectory_type"]].reset_index(drop=True).copy()
    regression_predictions = reg["test"][["session_id", "user_id", "accuracy_rate", "median_rt_ms"]].reset_index(drop=True).copy()
    metrics = {
        "run_kind": "bounded_development_tuning", "source_statistical_run": pointer["run_id"],
        "source_manifest_sha256": pointer["manifest_sha256"], "seed": SEED, "cutoff": cutoff.isoformat(),
        "primary_objectives": {"classification": "development balanced accuracy",
                               "regression": "development RMSE in natural units"},
        "test_reuse_note": "Prior untuned benchmarks were evaluated on these same synthetic test users; this is exploratory repeated-test evidence, not a fresh external holdout.",
        "cohorts": {"classification": {s: len(cls[s]) for s in cls},
                    "regression": {s: len(reg[s]) for s in reg}, "user_overlap": 0},
        "features": {"classification": list(CLASS_FEATURES), "regression": list(PRIOR_FEATURES)},
        "families": {}, "release_status": "engineering_validation_only",
    }
    for family in FAMILIES[:4]:
        classifier, choice = selected[(family, "classification")]
        probabilities = classifier.predict_proba(cls["test"][list(CLASS_FEATURES)])[:, 1]
        test_result = with_accuracy(binary_metrics(y["test"], probabilities, choice["threshold"]))
        metrics["families"][family] = {
            "classification": {"selected_config": choice["config"],
                               "development_threshold": choice["threshold"],
                               "development": with_accuracy(choice["development"]), "test": test_result},
        }
        predictions[family + "_probability"] = probabilities
        path = weights / (family + "_classifier.joblib")
        joblib.dump(classifier, path, compress=3)
        if not np.allclose(joblib.load(path).predict_proba(cls["test"][list(CLASS_FEATURES)])[:, 1], probabilities):
            raise ValueError(f"Classifier reload mismatch: {family}")
        for target, column in (("accuracy", "accuracy_rate"), ("rt", "log_rt")):
            regressor, choice = selected[(family, target)]
            predicted = regressor.predict(reg["test"][list(PRIOR_FEATURES)])
            observed = reg["test"][column].to_numpy()
            if target == "rt":
                predicted = np.exp(predicted); observed = np.exp(observed)
            metrics["families"][family][target + "_regression"] = {
                "selected_config": choice["config"], "development": choice["development"],
                "test": regression_metrics(observed, predicted),
                "unit": "milliseconds" if target == "rt" else "accuracy_fraction",
            }
            regression_predictions[family + "_" + target] = predicted
            path = weights / (family + "_" + target + "_regressor.joblib")
            joblib.dump(regressor, path, compress=3)
            if not np.allclose(joblib.load(path).predict(reg["test"][list(PRIOR_FEATURES)]),
                               regressor.predict(reg["test"][list(PRIOR_FEATURES)])):
                raise ValueError(f"Regressor reload mismatch: {family}/{target}")
    anomaly, choice = selected[("isolation_forest", "anomaly")]
    scores = -anomaly.score_samples(cls["test"][list(CLASS_FEATURES)])
    metrics["families"]["isolation_forest"] = {
        "selected_config": choice["config"], "training_percentile": choice["training_percentile"],
        "score_threshold": choice["score_threshold"],
        "development": with_accuracy(choice["development"]),
        "test": with_accuracy(binary_metrics(y["test"], scores, choice["score_threshold"], probabilities=False)),
        "fit": "Unsupervised; hyperparameters and threshold selected with synthetic development labels",
        "regression": "not applicable",
    }
    predictions["isolation_forest_score"] = scores
    path = weights / "isolation_forest.joblib"
    joblib.dump(anomaly, path, compress=3)
    if not np.allclose(joblib.load(path).score_samples(cls["test"][list(CLASS_FEATURES)]), -scores):
        raise ValueError("Anomaly reload mismatch")
    predictions.to_csv(output / "classification_test_predictions.csv", index=False)
    regression_predictions.to_csv(output / "regression_test_predictions.csv", index=False)
    return metrics


def main() -> int:
    run_id = "ml_tuned_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    output_root = ROOT / "outputs" / "ml_runs"
    output = output_root / run_id
    output.mkdir(parents=True, exist_ok=False)
    status = {"run_id": run_id, "status": "running", "started_at": datetime.now(timezone.utc).isoformat()}
    write_json(output / "run_status.json", status)
    try:
        metrics = execute(output)
        write_json(output / "metrics.json", metrics)
        status.update(status="completed", finished_at=datetime.now(timezone.utc).isoformat(),
                      statistical_source_run=metrics["source_statistical_run"],
                      dependencies={"sklearn": __import__("sklearn").__version__,
                                    "catboost": __import__("catboost").__version__,
                                    "lightgbm": __import__("lightgbm").__version__},
                      source_sha256={name: sha(ROOT / "src" / "modeling" / name) for name in
                                     ("train_ml_models.py", "tune_ml_models.py")},
                      artifacts={str(path.relative_to(output)): {"bytes": path.stat().st_size, "sha256": sha(path)}
                                 for path in output.rglob("*") if path.is_file() and path.name != "run_status.json"})
        write_json(output / "run_status.json", status)
        write_json(output_root / "latest_successful_ml_run.json", {
            "run_id": run_id, "path": str(output.resolve()), "status_sha256": sha(output / "run_status.json")})
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
