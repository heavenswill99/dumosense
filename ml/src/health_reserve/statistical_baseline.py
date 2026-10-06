"""Versioned statistical baseline for the Health Reserve obligation-buffer rank.

This is a deterministic index plus a robust, strictly prior within-user median.
There is no fitted clinical or treatment-cost model.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from itertools import groupby
import csv
import hashlib
import json
from pathlib import Path
from statistics import median
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from health_reserve.score import SCORE_LOWER_BOUNDS, score_assessment
VERSION = "HR_BUFFER_BASELINE_1.0"
MIN_PRIOR = 3
MAX_PRIOR = 5
LOOKBACK_DAYS = 365
REQUIRED = {"reserve_assessment_id", "user_id", "assessed_at",
            "current_preparedness_amount", "monthly_financial_obligations"}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def parse_time(value: str) -> datetime:
    if not value:
        raise ValueError("assessed_at is required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is not None:
        result = result.astimezone(timezone.utc).replace(tzinfo=None)
    return result


def load_assessments(path: Path) -> list[tuple[str, datetime, str, dict]]:
    rows = []
    ids = set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        absent = REQUIRED - set(reader.fieldnames or [])
        if absent:
            raise ValueError(f"Missing required fields: {sorted(absent)}")
        for line, row in enumerate(reader, start=2):
            assessment_id = row["reserve_assessment_id"]
            user_id = row["user_id"]
            if not assessment_id or not user_id:
                raise ValueError(f"Missing assessment or user ID at CSV line {line}")
            if assessment_id in ids:
                raise ValueError(f"Duplicate assessment ID at CSV line {line}")
            ids.add(assessment_id)
            timestamp = parse_time(row["assessed_at"])
            # Validate all scored and displayed numeric inputs before any output is written.
            score_assessment(row)
            rows.append((user_id, timestamp, assessment_id, row))
    if not rows:
        raise ValueError("No assessments")
    return rows


def build_records(rows: list[tuple[str, datetime, str, dict]]) -> list[dict]:
    """Use only strictly earlier snapshots; same-time records share the same prior history."""
    ordered = sorted(rows, key=lambda item: item[:3])
    histories: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    output = []
    for (user_id, timestamp), group_iter in groupby(ordered, key=lambda item: item[:2]):
        group = list(group_iter)
        prior = [(when, months) for when, months in histories[user_id]
                 if when < timestamp and timestamp - when <= timedelta(days=LOOKBACK_DAYS)]
        selected = prior[-MAX_PRIOR:]
        baseline = median(months for _, months in selected) if len(selected) >= MIN_PRIOR else None
        last_age = (timestamp - selected[-1][0]).total_seconds() / 86400 if selected else None
        for _, _, assessment_id, row in group:
            scored = score_assessment(row)
            months = scored["obligation_buffer_months"]
            output.append({
                "reserve_assessment_id": assessment_id,
                "user_id": user_id,
                "assessed_at": row["assessed_at"],
                "model_version": VERSION,
                "score": scored["score"],
                "band": scored["band"],
                "obligation_buffer_months": months,
                "health_resource_obligation_months": scored["health_resource_obligation_months"],
                "healthcare_coverage_status": scored["healthcare_coverage_status"],
                "number_of_dependants": scored["number_of_dependants"],
                "prior_assessment_count": len(selected),
                "baseline_available": baseline is not None,
                "prior_median_buffer_months": baseline,
                "delta_from_prior_median_months": months - baseline if baseline is not None else None,
                "latest_prior_age_days": last_age,
            })
        histories[user_id].extend(
            (timestamp, score_assessment(row)["obligation_buffer_months"]) for _, _, _, row in group
        )
    return output


def summarize(records: list[dict]) -> dict:
    all_counts = Counter(item["score"] for item in records)
    latest = {}
    for record in records:
        latest[record["user_id"]] = record
    latest_counts = Counter(item["score"] for item in latest.values())
    baseline_count = sum(item["baseline_available"] for item in records)
    return {
        "model_version": VERSION,
        "release_status": "synthetic_engineering_validation_only",
        "assessment_count": len(records),
        "user_count": len(latest),
        "baseline_available_count": baseline_count,
        "baseline_coverage": baseline_count / len(records),
        "score_counts": {str(i): all_counts[i] for i in range(1, 11)},
        "latest_user_score_counts": {str(i): latest_counts[i] for i in range(1, 11)},
        "metric_definition": "Fixed ordinal obligation-buffer rank; no accuracy metric exists without independent outcomes.",
    }


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run(input_path: Path, output_root: Path) -> Path:
    run_id = "hr_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / run_id
    output.mkdir(exist_ok=False)
    status = {"run_id": run_id, "status": "running", "model_version": VERSION}
    write_json(output / "run_status.json", status)
    try:
        rows = load_assessments(input_path)
        records = build_records(rows)
        with (output / "assessments.jsonl").open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, allow_nan=False) + "\n")
        summary = summarize(records)
        write_json(output / "summary.json", summary)
        parameters = {
            "version": VERSION,
            "score_lower_bounds_months": list(SCORE_LOWER_BOUNDS),
            "minimum_prior_assessments": MIN_PRIOR,
            "maximum_prior_assessments": MAX_PRIOR,
            "lookback_days": LOOKBACK_DAYS,
            "scored_fields": ["current_preparedness_amount", "monthly_financial_obligations"],
            "excluded_cost_derived_fields": [
                "estimated_healthcare_exposure", "preparedness_target", "preparedness_gap",
                "preparedness_ratio", "reserve_status",
            ],
        }
        write_json(output / "model_parameters.json", parameters)
        status.update(
            status="completed",
            input_path=str(input_path.resolve()),
            input_sha256=digest(input_path),
            source_sha256={
                "score.py": digest(Path(__file__).with_name("score.py")),
                "statistical_baseline.py": digest(Path(__file__)),
            },
            artifacts={name: digest(output / name) for name in
                       ("assessments.jsonl", "summary.json", "model_parameters.json")},
        )
        write_json(output / "run_status.json", status)
        write_json(output_root / "latest_successful_health_reserve_run.json",
                   {"run_id": run_id, "path": str(output.resolve()),
                    "status_sha256": digest(output / "run_status.json")})
        return output
    except BaseException as exc:
        status.update(status="failed", error=str(exc), traceback=traceback.format_exc())
        write_json(output / "run_status.json", status)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path,
                        default=ROOT.parent / "data" / "synthetic" / "health_reserve_assessments.csv")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "health_reserve_runs")
    args = parser.parse_args()
    output = run(args.input, args.output_root)
    print(json.dumps({"run": str(output), "summary": json.loads((output / "summary.json").read_text())}, indent=2))


if __name__ == "__main__":
    main()
