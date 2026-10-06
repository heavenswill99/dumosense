"""Transparent, non-clinical Health Reserve buffer score.

The score uses only the current preparedness amount and monthly obligations.
It does not estimate healthcare prices, risk, or adequacy of insurance.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path

# Lower bounds for scores 1 through 10, in months of recorded obligations.
SCORE_LOWER_BOUNDS = (0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 9.0, 12.0)


def _amount(value: object, name: str, *, strictly_positive: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a numeric amount")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a numeric amount") from exc
    if not math.isfinite(number) or number < 0 or (strictly_positive and number == 0):
        raise ValueError(f"{name} must be finite and {'positive' if strictly_positive else 'nonnegative'}")
    return number


def score_buffer(current_preparedness_amount: object, monthly_financial_obligations: object) -> dict:
    """Return a fixed 1-10 ordinal rank; it is not a healthcare-adequacy estimate."""
    amount = _amount(current_preparedness_amount, "current_preparedness_amount")
    obligations = _amount(monthly_financial_obligations, "monthly_financial_obligations", strictly_positive=True)
    months = amount / obligations
    if not math.isfinite(months):
        raise ValueError("obligation_buffer_months must be finite")
    score = sum(months >= lower for lower in SCORE_LOWER_BOUNDS)
    if score <= 3:
        band = "1-3"
    elif score <= 6:
        band = "4-6"
    elif score <= 8:
        band = "7-8"
    else:
        band = "9-10"
    return {"score": score, "band": band, "obligation_buffer_months": months}


def score_assessment(row: dict) -> dict:
    """Keep companion fields separate to avoid arbitrary weighting or double counting."""
    result = score_buffer(row.get("current_preparedness_amount"), row.get("monthly_financial_obligations"))
    emergency = row.get("emergency_health_resources")
    if emergency is not None and emergency != "":
        emergency_amount = _amount(emergency, "emergency_health_resources")
        obligations = _amount(row.get("monthly_financial_obligations"),
                              "monthly_financial_obligations", strictly_positive=True)
        resource_months = emergency_amount / obligations
        if not math.isfinite(resource_months):
            raise ValueError("health_resource_obligation_months must be finite")
        result["health_resource_obligation_months"] = resource_months
    else:
        result["health_resource_obligation_months"] = None
    result["healthcare_coverage_status"] = row.get("healthcare_coverage_status") or "unknown"
    result["number_of_dependants"] = row.get("number_of_dependants")
    return result


def summarize_csv(path: Path) -> dict:
    """Audit every snapshot and count score bands, including each user's latest snapshot."""
    all_scores: Counter[int] = Counter()
    latest: dict[str, tuple[datetime, str, int]] = {}
    invalid = 0
    rows = 0
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"reserve_assessment_id", "user_id", "assessed_at",
                    "current_preparedness_amount", "monthly_financial_obligations"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing required columns: {sorted(required - set(reader.fieldnames or []))}")
        for row in reader:
            rows += 1
            try:
                if not row["user_id"] or not row["reserve_assessment_id"]:
                    raise ValueError("Missing assessment identity")
                timestamp = datetime.fromisoformat(row["assessed_at"].replace("Z", "+00:00"))
                if timestamp.tzinfo is not None:
                    timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
                scored = score_assessment(row)
            except (ValueError, OverflowError):
                invalid += 1
                continue
            score = scored["score"]
            all_scores[score] += 1
            key = (timestamp, row["reserve_assessment_id"], score)
            prior = latest.get(row["user_id"])
            if prior is None or key[:2] > prior[:2]:
                latest[row["user_id"]] = key
    latest_scores = Counter(item[2] for item in latest.values())
    return {
        "rows": rows,
        "valid_rows": rows - invalid,
        "invalid_rows": invalid,
        "users_with_valid_assessment": len(latest),
        "all_assessment_score_counts": {str(i): all_scores[i] for i in range(1, 11)},
        "latest_user_score_counts": {str(i): latest_scores[i] for i in range(1, 11)},
        "score_name": "preliminary_obligation_buffer_rank",
        "release_status": "synthetic_engineering_validation_only",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assessments_csv", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize_csv(args.assessments_csv), indent=2))


if __name__ == "__main__":
    main()
