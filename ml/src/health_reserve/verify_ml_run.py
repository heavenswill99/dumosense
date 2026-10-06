"""Independently recount a saved Health Reserve next-assessment ML benchmark."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix,
                             f1_score, log_loss, mean_absolute_error, mean_squared_error,
                             precision_score, r2_score, recall_score)

ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ("linear", "random_forest", "catboost", "lightgbm")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def close(a: float, b: float, label: str) -> None:
    if not np.isclose(a, b, rtol=0, atol=1e-10):
        raise ValueError(f"Metric mismatch: {label}: {a} vs {b}")


def user_split(user_id: str) -> str:
    bucket = int(hashlib.sha256(("health-reserve-42-" + str(user_id)).encode()).hexdigest()[:8], 16) % 10
    return "train" if bucket < 6 else "development" if bucket < 8 else "test"


def band(score: int) -> int:
    return 0 if score <= 3 else 1 if score <= 6 else 2 if score <= 8 else 3


def verify(run: Path, package: Path) -> dict:
    status = json.loads((run / "run_status.json").read_text(encoding="utf-8"))
    if status["status"] != "completed" or status["run_id"] != run.name:
        raise ValueError("Run not completed")
    for relative, expected in status["artifacts"].items():
        if digest(run / relative) != expected:
            raise ValueError(f"Run artifact hash mismatch: {relative}")
    manifest = json.loads((package / "package_manifest.json").read_text(encoding="utf-8"))
    if manifest["source_run_id"] != run.name or manifest["source_status_sha256"] != digest(run / "run_status.json"):
        raise ValueError("Package/source mismatch")
    for relative, expected in manifest["files"].items():
        if digest(package / relative) != expected:
            raise ValueError(f"Package hash mismatch: {relative}")
    if len(list((package / "weights").glob("*.joblib"))) != 9:
        raise ValueError("Expected nine saved estimators")
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    if digest(package / "metrics.json") != digest(run / "metrics.json"):
        raise ValueError("Package metrics differ from run")
    forbidden = {"estimated_healthcare_exposure", "preparedness_target", "preparedness_gap",
                 "preparedness_ratio", "reserve_status", "next_score", "next_band", "next_at"}
    if forbidden.intersection(metrics["features"]):
        raise ValueError("Leaked or cost-derived feature in model")

    source_run = ROOT / "outputs" / "health_reserve_runs" / metrics["baseline_run_id"]
    if digest(source_run / "run_status.json") != metrics["baseline_status_sha256"]:
        raise ValueError("Statistical baseline source changed")
    source = pd.read_json(source_run / "assessments.jsonl", lines=True)
    source["assessed_at"] = pd.to_datetime(source["assessed_at"], utc=True)
    source = source.sort_values(["user_id", "assessed_at", "reserve_assessment_id"])
    source["next_score"] = source.groupby("user_id").score.shift(-1)
    source["next_at"] = source.groupby("user_id").assessed_at.shift(-1)
    source = source[source.next_score.notna()].copy()
    source["next_band"] = source.next_score.astype(int).map(band)
    source["split"] = source.user_id.map(user_split)
    cutoff = pd.Timestamp(metrics["cutoff_utc"])
    cohorts = {
        "train": source[(source.split == "train") & (source.next_at < cutoff)],
        "development": source[(source.split == "development") & (source.assessed_at >= cutoff)],
        "test": source[(source.split == "test") & (source.assessed_at >= cutoff)],
    }
    for name, part in cohorts.items():
        if len(part) != metrics["cohorts"][name]["examples"] or part.user_id.nunique() != metrics["cohorts"][name]["users"]:
            raise ValueError(f"Cohort count mismatch: {name}")
    if cohorts["train"].next_at.max() >= cutoff or cohorts["test"].assessed_at.min() < cutoff:
        raise ValueError("Time split mismatch")
    if any(set(cohorts[a].user_id) & set(cohorts[b].user_id)
           for a, b in (("train", "development"), ("train", "test"), ("development", "test"))):
        raise ValueError("User overlap")

    predictions = pd.read_csv(run / "test_predictions.csv")
    expected = cohorts["test"].set_index("reserve_assessment_id")
    if predictions.reserve_assessment_id.duplicated().any() or set(predictions.reserve_assessment_id) != set(expected.index):
        raise ValueError("Test prediction IDs mismatch")
    predictions = predictions.set_index("reserve_assessment_id").loc[expected.index]
    if not np.array_equal(predictions.next_score.to_numpy(), expected.next_score.to_numpy()):
        raise ValueError("Next-score target mismatch")
    if not np.array_equal(predictions.next_band.to_numpy(), expected.next_band.to_numpy()):
        raise ValueError("Next-band target mismatch")
    if not np.array_equal(predictions.score.to_numpy(), expected.score.to_numpy()):
        raise ValueError("Current score mismatch")
    y_band = expected.next_band.to_numpy(dtype=int)
    y_score = expected.next_score.to_numpy(dtype=float)

    for family in FAMILIES:
        result = metrics["families"][family]
        label = predictions[family + "_band"].to_numpy(dtype=int)
        probability = predictions[[f"{family}_probability_{i}" for i in range(4)]].to_numpy()
        if not np.allclose(probability.sum(axis=1), 1, atol=1e-10):
            raise ValueError(f"Probabilities do not sum to one: {family}")
        c = result["classification"]["test"]
        close(accuracy_score(y_band, label), c["accuracy"], family + " accuracy")
        close(balanced_accuracy_score(y_band, label), c["balanced_accuracy"], family + " BA")
        close(precision_score(y_band, label, labels=range(4), average="macro", zero_division=0),
              c["macro_precision"], family + " precision")
        close(recall_score(y_band, label, labels=range(4), average="macro", zero_division=0),
              c["macro_recall"], family + " recall")
        close(f1_score(y_band, label, labels=range(4), average="macro", zero_division=0),
              c["macro_f1"], family + " F1")
        close(log_loss(y_band, probability, labels=range(4)), c["log_loss"], family + " log loss")
        if confusion_matrix(y_band, label, labels=range(4)).tolist() != c["confusion_matrix"]:
            raise ValueError(f"Confusion mismatch: {family}")
        predicted = predictions[family + "_score"].to_numpy()
        r = result["regression"]["test"]
        close(mean_absolute_error(y_score, predicted), r["mae_score_points"], family + " MAE")
        close(np.sqrt(mean_squared_error(y_score, predicted)), r["rmse_score_points"], family + " RMSE")
        close(r2_score(y_score, predicted), r["r2"], family + " R2")
        rounded = np.clip(np.rint(predicted), 1, 10).astype(int)
        close(np.mean(rounded == y_score), r["rounded_exact_accuracy"], family + " exact")
        close(np.mean(np.abs(rounded - y_score) <= 1), r["rounded_within_one_accuracy"], family + " within one")

    p = metrics["baselines"]["persistence_regression"]
    close(mean_absolute_error(y_score, expected.score.to_numpy()), p["mae_score_points"], "persistence MAE")
    p_class = metrics["baselines"]["persistence_classification"]
    close(accuracy_score(y_band, expected.score.map(band).to_numpy()),
          p_class["accuracy"], "persistence accuracy")
    anomaly = metrics["families"]["isolation_forest"]
    scores = predictions.isolation_forest_score.to_numpy()
    for suffix, threshold in (("train", anomaly["train_score_threshold"]),
                              ("development", anomaly["development_calibrated_threshold"])):
        close(np.mean(scores >= threshold), anomaly[f"test_flagged_fraction_at_{suffix}_threshold"],
              "anomaly " + suffix + " rate")
        if int(np.sum(scores >= threshold)) != anomaly[f"test_flagged_at_{suffix}_threshold"]:
            raise ValueError("Anomaly count mismatch")
    return {"run_id": run.name, "status": "passed",
            "test_predictions_verified": len(predictions),
            "classifiers_verified": 4, "regressors_verified": 4,
            "anomaly_comparator_verified": True,
            "run_artifacts_verified": len(status["artifacts"]),
            "package_files_verified": len(manifest["files"])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--package", type=Path)
    args = parser.parse_args()
    pointer_path = ROOT / "outputs" / "health_reserve_ml_runs" / "latest_successful_health_reserve_ml_run.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    run = args.run or Path(pointer["path"])
    package = args.package or Path(pointer["package_path"])
    if args.run is None and digest(run / "run_status.json") != pointer["status_sha256"]:
        raise ValueError("Latest-successful pointer mismatch")
    print(json.dumps(verify(run, package), indent=2))


if __name__ == "__main__":
    main()
