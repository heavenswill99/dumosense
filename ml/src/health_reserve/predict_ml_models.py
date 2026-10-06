"""Verify a trusted Health Reserve ML bundle and predict the next assessment internally."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / ".deps"))

import joblib
import numpy as np
import pandas as pd

from health_reserve.score import score_buffer

BANDS = ("1-3", "4-6", "7-8", "9-10")
FAMILIES = ("linear", "random_forest", "catboost", "lightgbm")
NUMERIC = (
    "score", "obligation_buffer_months", "health_resource_obligation_months",
    "current_preparedness_amount", "monthly_financial_obligations",
    "number_of_dependants", "prior_assessment_count",
    "prior_median_buffer_months", "delta_from_prior_median_months",
    "latest_prior_age_days",
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare(assessment: dict, expected_features: list[str]) -> pd.DataFrame:
    required = {
        "current_preparedness_amount", "monthly_financial_obligations",
        "healthcare_coverage_status", "number_of_dependants", "prior_assessment_count",
        "prior_median_buffer_months", "delta_from_prior_median_months",
        "latest_prior_age_days",
    }
    missing = required - set(assessment)
    if missing:
        raise ValueError(f"Missing required assessment fields: {sorted(missing)}")
    if not ({"health_resource_obligation_months", "emergency_health_resources"} & set(assessment)):
        raise ValueError("Health emergency resources must be supplied, possibly as null")
    prior_count = float(assessment["prior_assessment_count"])
    if not np.isfinite(prior_count) or prior_count < 0 or not prior_count.is_integer():
        raise ValueError("prior_assessment_count must be a nonnegative integer")
    scored = score_buffer(
        assessment["current_preparedness_amount"], assessment["monthly_financial_obligations"]
    )
    if prior_count >= 3:
        if assessment["prior_median_buffer_months"] is None or assessment["delta_from_prior_median_months"] is None:
            raise ValueError("A prior median and delta are required when a baseline is available")
        if not np.isclose(
                scored["obligation_buffer_months"] - float(assessment["prior_median_buffer_months"]),
                float(assessment["delta_from_prior_median_months"]), atol=1e-9, rtol=0):
            raise ValueError("Prior median and delta are inconsistent")
    elif assessment["prior_median_buffer_months"] is not None or assessment["delta_from_prior_median_months"] is not None:
        raise ValueError("No prior median is available with fewer than three earlier assessments")
    if prior_count > 0 and assessment["latest_prior_age_days"] is None:
        raise ValueError("Latest-prior age is required when earlier assessments exist")
    if "score" in assessment and int(assessment["score"]) != scored["score"]:
        raise ValueError("Provided score differs from the fixed score formula")
    if "obligation_buffer_months" in assessment and not np.isclose(
            float(assessment["obligation_buffer_months"]), scored["obligation_buffer_months"],
            rtol=0, atol=1e-9):
        raise ValueError("Provided buffer months differ from the fixed formula")
    values = {name: assessment.get(name) for name in expected_features}
    values["score"] = scored["score"]
    values["obligation_buffer_months"] = scored["obligation_buffer_months"]
    if values.get("health_resource_obligation_months") is None and assessment.get("emergency_health_resources") is not None:
        amount = float(assessment["emergency_health_resources"])
        if not np.isfinite(amount) or amount < 0:
            raise ValueError("Invalid emergency health resources")
        values["health_resource_obligation_months"] = amount / float(assessment["monthly_financial_obligations"])
    values["healthcare_coverage_status"] = assessment.get("healthcare_coverage_status") or "unknown"
    for name in NUMERIC:
        value = values.get(name)
        if value is not None and value != "":
            number = float(value)
            if not np.isfinite(number):
                raise ValueError(f"Nonfinite feature: {name}")
            values[name] = number
        else:
            values[name] = np.nan
    if set(values) != set(expected_features):
        raise ValueError("Feature schema mismatch")
    return pd.DataFrame([values], columns=expected_features)


def predict(bundle: Path, family: str, assessment: dict) -> dict:
    if family not in FAMILIES:
        raise ValueError(f"Unknown supervised family: {family}")
    manifest = json.loads((bundle / "package_manifest.json").read_text(encoding="utf-8"))
    for relative, expected in manifest["files"].items():
        if digest(bundle / relative) != expected:
            raise ValueError(f"Package file hash mismatch: {relative}")
    metrics = json.loads((bundle / "metrics.json").read_text(encoding="utf-8"))
    if metrics["model_version"] != manifest["model_version"]:
        raise ValueError("Package model version mismatch")
    frame = prepare(assessment, metrics["features"])
    classifier = joblib.load(bundle / "weights" / f"{family}_classifier.joblib")
    regressor = joblib.load(bundle / "weights" / f"{family}_regressor.joblib")
    probabilities = classifier.predict_proba(frame)[0]
    if probabilities.shape != (4,) or not np.isclose(probabilities.sum(), 1):
        raise ValueError("Invalid class probabilities")
    raw_score = float(regressor.predict(frame)[0])
    if not np.isfinite(raw_score):
        raise ValueError("Invalid regression prediction")
    return {
        "model_version": metrics["model_version"],
        "family": family,
        "target": "next recorded assessment; no fixed calendar horizon",
        "predicted_next_band": BANDS[int(np.argmax(probabilities))],
        "next_band_probabilities": {name: float(value) for name, value in zip(BANDS, probabilities)},
        "predicted_next_score_continuous": raw_score,
        "predicted_next_score_display": int(np.clip(np.rint(raw_score), 1, 10)),
        "release_status": "synthetic_engineering_validation_only",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=FAMILIES, required=True)
    parser.add_argument("--assessment-json", type=Path, required=True)
    parser.add_argument("--bundle", type=Path)
    args = parser.parse_args()
    if args.bundle is None:
        pointer_path = ROOT / "outputs" / "health_reserve_ml_runs" / "latest_successful_health_reserve_ml_run.json"
        args.bundle = Path(json.loads(pointer_path.read_text(encoding="utf-8"))["package_path"])
    assessment = json.loads(args.assessment_json.read_text(encoding="utf-8"))
    print(json.dumps(predict(args.bundle, args.family, assessment), indent=2))


if __name__ == "__main__":
    main()
