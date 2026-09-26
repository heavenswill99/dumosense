"""Calculate a population-level prediction from exported statistical weights."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parent.parent
MODEL_NAMES = ("accuracy", "rt", "rt_clustered_ols", "accuracy_binomial_clustered")


def load_bundle_model(bundle: Path, name: str) -> dict:
    if name not in MODEL_NAMES:
        raise ValueError(f"Unknown statistical model: {name}")
    manifest = json.loads((bundle / "bundle_manifest.json").read_text(encoding="utf-8"))
    path = bundle / f"{name}.json"
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != manifest["artifact_hashes"][path.name]:
        raise ValueError("Model weights do not match the bundle manifest")
    model = json.loads(path.read_text(encoding="utf-8"))
    if model["run_id"] != manifest["source_run_id"] or model["model_name"] != name:
        raise ValueError("Model identity does not match the bundle manifest")
    return model


def population_prediction(model: dict, *, started_at: str, difficulty_level: int,
                          cognitive_domain: str | None = None) -> float:
    info = model["inference"]
    if difficulty_level not in info["difficulty_levels"]:
        raise ValueError("Difficulty level is outside the fitted categories")
    if info["cognitive_domains"] is not None and cognitive_domain not in info["cognitive_domains"]:
        raise ValueError("A fitted cognitive domain is required")
    timestamp = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("started_at must include a UTC offset")
    origin = datetime.fromisoformat(info["time_days_origin_utc"])
    days = (timestamp.astimezone(timezone.utc) - origin.astimezone(timezone.utc)).total_seconds() / 86400
    coefficients = model["fit"]["coefficients"]
    linear = coefficients["Intercept"] + days * coefficients["time_days"]
    if difficulty_level != info["reference_difficulty"]:
        linear += coefficients[f"C(difficulty_level)[T.{difficulty_level}]" ]
    if info["cognitive_domains"] is not None and cognitive_domain != info["reference_domain"]:
        linear += coefficients[f"C(cognitive_domain)[T.{cognitive_domain}]" ]
    link = info["link"]
    if link == "identity":
        return linear
    if link == "log":
        return math.exp(linear)
    if link == "logit":
        return 1 / (1 + math.exp(-linear)) if linear >= 0 else math.exp(linear) / (1 + math.exp(linear))
    raise ValueError(f"Unsupported link: {link}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=None)
    parser.add_argument("--model", choices=MODEL_NAMES, required=True)
    parser.add_argument("--started-at", required=True, help="Timestamp with UTC offset")
    parser.add_argument("--difficulty", type=int, required=True)
    parser.add_argument("--domain")
    args = parser.parse_args()
    pointer = json.loads((ROOT / "outputs" / "latest_successful_run.json").read_text(encoding="utf-8"))
    bundle = args.bundle or ROOT / "model_artifacts" / pointer["run_id"]
    model = load_bundle_model(bundle, args.model)
    value = population_prediction(model, started_at=args.started_at,
                                  difficulty_level=args.difficulty, cognitive_domain=args.domain)
    print(json.dumps({"model": args.model, "population_prediction": value,
                      "output": model["inference"]["output"], "run_id": model["run_id"],
                      "release_status": "internal_validation_only"}, indent=2))


if __name__ == "__main__":
    main()
