"""Independently verify a Health Reserve baseline run from source CSV and saved files."""

from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_time(raw: str) -> datetime:
    value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def close(actual: object, expected: float | None, name: str) -> None:
    if expected is None:
        if actual is not None:
            raise ValueError(f"{name}: expected null")
    elif actual is None or not math.isclose(float(actual), expected, rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError(f"{name}: mismatch")


def verify(run: Path) -> dict:
    status = json.loads((run / "run_status.json").read_text(encoding="utf-8"))
    if status["status"] != "completed" or run.name != status["run_id"]:
        raise ValueError("Run is not completed")
    source = Path(status["input_path"])
    if digest(source) != status["input_sha256"]:
        raise ValueError("Input hash mismatch")
    for name, expected_hash in status["artifacts"].items():
        if digest(run / name) != expected_hash:
            raise ValueError(f"Artifact hash mismatch: {name}")

    parameters = json.loads((run / "model_parameters.json").read_text(encoding="utf-8"))
    bounds = parameters["score_lower_bounds_months"]
    if bounds != sorted(bounds) or len(bounds) != 10 or bounds[0] != 0:
        raise ValueError("Invalid score boundaries")
    if parameters["version"] != status["model_version"]:
        raise ValueError("Model version mismatch")
    with source.open(newline="", encoding="utf-8-sig") as handle:
        input_rows = list(csv.DictReader(handle))
    with (run / "assessments.jsonl").open(encoding="utf-8") as handle:
        output_rows = [json.loads(line) for line in handle if line.strip()]
    if len(input_rows) != len(output_rows):
        raise ValueError("Output count differs from input")
    by_id = {row["reserve_assessment_id"]: row for row in input_rows}
    emitted = {row["reserve_assessment_id"]: row for row in output_rows}
    if len(by_id) != len(input_rows) or set(by_id) != set(emitted):
        raise ValueError("Assessment IDs are missing or duplicated")

    scores = Counter()
    users: dict[str, list[tuple[datetime, str, float, int]]] = defaultdict(list)
    for assessment_id, row in by_id.items():
        result = emitted[assessment_id]
        amount = float(row["current_preparedness_amount"])
        obligations = float(row["monthly_financial_obligations"])
        months = amount / obligations
        expected_score = bisect_right(bounds, months)
        if result["user_id"] != row["user_id"] or result["assessed_at"] != row["assessed_at"]:
            raise ValueError("Identity mismatch")
        if result["score"] != expected_score:
            raise ValueError(f"Score mismatch: {assessment_id}")
        close(result["obligation_buffer_months"], months, "buffer months")
        if result["band"] != ("1-3" if expected_score <= 3 else "4-6" if expected_score <= 6 else
                              "7-8" if expected_score <= 8 else "9-10"):
            raise ValueError("Score band mismatch")
        scores[expected_score] += 1
        users[row["user_id"]].append((parse_time(row["assessed_at"]), assessment_id, months, expected_score))

    latest_scores = Counter()
    baseline_count = 0
    max_prior = parameters["maximum_prior_assessments"]
    min_prior = parameters["minimum_prior_assessments"]
    lookback = timedelta(days=parameters["lookback_days"])
    for user_id, items in users.items():
        items.sort(key=lambda item: item[:2])
        latest_scores[items[-1][3]] += 1
        for timestamp, assessment_id, months, _ in items:
            earlier = [(when, value) for when, _, value, _ in items
                       if when < timestamp and timestamp - when <= lookback][-max_prior:]
            expected_median = median(value for _, value in earlier) if len(earlier) >= min_prior else None
            result = emitted[assessment_id]
            if result["prior_assessment_count"] != len(earlier):
                raise ValueError(f"Prior count mismatch: {assessment_id}")
            if result["baseline_available"] != (expected_median is not None):
                raise ValueError(f"Baseline availability mismatch: {assessment_id}")
            close(result["prior_median_buffer_months"], expected_median, "prior median")
            close(result["delta_from_prior_median_months"],
                  months - expected_median if expected_median is not None else None, "delta")
            close(result["latest_prior_age_days"],
                  (timestamp - earlier[-1][0]).total_seconds() / 86400 if earlier else None, "prior age")
            baseline_count += expected_median is not None

    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    if summary["assessment_count"] != len(input_rows) or summary["user_count"] != len(users):
        raise ValueError("Summary row or user count mismatch")
    if summary["baseline_available_count"] != baseline_count:
        raise ValueError("Summary baseline count mismatch")
    close(summary["baseline_coverage"], baseline_count / len(input_rows), "baseline coverage")
    if summary["score_counts"] != {str(i): scores[i] for i in range(1, 11)}:
        raise ValueError("Summary score distribution mismatch")
    if summary["latest_user_score_counts"] != {str(i): latest_scores[i] for i in range(1, 11)}:
        raise ValueError("Summary latest score distribution mismatch")
    return {"run_id": run.name, "status": "passed", "assessments_verified": len(input_rows),
            "users_verified": len(users), "prior_medians_verified": baseline_count,
            "artifacts_verified": len(status["artifacts"])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path)
    args = parser.parse_args()
    pointer_path = ROOT / "outputs" / "health_reserve_runs" / "latest_successful_health_reserve_run.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    run = args.run or Path(pointer["path"])
    if args.run is None and digest(run / "run_status.json") != pointer["status_sha256"]:
        raise ValueError("Latest run pointer hash mismatch")
    print(json.dumps(verify(run), indent=2))


if __name__ == "__main__":
    main()
