"""Independently verify a completed ML run and its distributable model package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, mean_absolute_error, mean_squared_error, r2_score


ROOT = Path(__file__).resolve().parents[2]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def near(a: float, b: float, label: str) -> None:
    if not np.isclose(a, b, rtol=0, atol=1e-11):
        raise ValueError(f"Metric mismatch for {label}: {a} vs {b}")


def verify(run: Path, package: Path) -> dict:
    status = json.loads((run / "run_status.json").read_text(encoding="utf-8"))
    if status["status"] != "completed" or status["run_id"] != run.name:
        raise ValueError("Run is not completed")
    for relative, details in status["artifacts"].items():
        if sha(run / relative) != details["sha256"]:
            raise ValueError(f"Run artifact hash mismatch: {relative}")
    package_manifest = json.loads((package / "package_manifest.json").read_text(encoding="utf-8"))
    if package_manifest["source_ml_run_id"] != run.name:
        raise ValueError("Package is for a different run")
    for relative, details in package_manifest["files"].items():
        if sha(package / relative) != details["sha256"]:
            raise ValueError(f"Package artifact hash mismatch: {relative}")
    if sha(run / "metrics.json") != sha(package / "metrics.json"):
        raise ValueError("Package metrics differ from run")
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    classification = pd.read_csv(run / "classification_test_predictions.csv")
    regression = pd.read_csv(run / "regression_test_predictions.csv")
    if len(classification) != metrics["cohorts"]["classification"]["test"]:
        raise ValueError("Classification test count mismatch")
    if len(regression) != metrics["cohorts"]["regression"]["test"]:
        raise ValueError("Regression test count mismatch")
    y = classification.trajectory_type.ne("stable_pattern").to_numpy(dtype=int)
    for family in ("linear", "random_forest", "catboost", "lightgbm"):
        result = metrics["families"][family]
        probability = classification[family + "_probability"].to_numpy()
        threshold = result["classification"]["development_threshold"]
        prediction = (probability >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, prediction, labels=[0, 1]).ravel()
        expected = result["classification"]["test"]
        if [int(tp), int(tn), int(fp), int(fn)] != [expected[k] for k in ("TP", "TN", "FP", "FN")]:
            raise ValueError(f"Classification confusion mismatch: {family}")
        near(balanced_accuracy_score(y, prediction), expected["balanced_accuracy"], family + " balanced accuracy")
        for target, actual in (("accuracy", "accuracy_rate"), ("rt", "median_rt_ms")):
            observed = regression[actual].to_numpy()
            predicted = regression[family + "_" + target].to_numpy()
            score = result[target + "_regression"]["test"]
            near(mean_absolute_error(observed, predicted), score["mae"], family + " " + target + " MAE")
            near(np.sqrt(mean_squared_error(observed, predicted)), score["rmse"], family + " " + target + " RMSE")
            near(r2_score(observed, predicted), score["r2"], family + " " + target + " R2")
    anomaly = metrics["families"]["isolation_forest"]["test"]
    scores = classification.isolation_forest_score.to_numpy()
    tn, fp, fn, tp = confusion_matrix(y, scores >= anomaly["threshold"], labels=[0, 1]).ravel()
    if [int(tp), int(tn), int(fp), int(fn)] != [anomaly[k] for k in ("TP", "TN", "FP", "FN")]:
        raise ValueError("Anomaly confusion mismatch")
    if anomaly["brier"] is not None or anomaly["log_loss"] is not None:
        raise ValueError("Anomaly score was incorrectly reported as a probability")
    if len(package_manifest["estimators"]) != 13:
        raise ValueError("Missing fitted estimator")
    return {"run_id": run.name, "run_artifacts_verified": len(status["artifacts"]),
            "package_files_verified": len(package_manifest["files"]),
            "classification_models_recounted": 5, "regression_models_recounted": 8,
            "status": "passed"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=None)
    parser.add_argument("--package", type=Path, default=None)
    args = parser.parse_args()
    pointer = json.loads((ROOT / "outputs" / "ml_runs" / "latest_successful_ml_run.json").read_text(encoding="utf-8"))
    run = args.run or Path(pointer["path"])
    package = args.package or ROOT / "weights" / pointer["run_id"]
    print(json.dumps(verify(run, package), indent=2))


if __name__ == "__main__":
    main()
