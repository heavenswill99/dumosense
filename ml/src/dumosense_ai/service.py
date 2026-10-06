"""Compose traceable MVP insights from completed, product-specific baseline records.

The backend must establish identity, current consent, enrollment, and trusted run
metadata. This module does not call an LLM, database, or notification service.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import math

VERSION = "DUMOSENSE_INSIGHT_1.0"
PRODUCTS = {"MINDGUARD", "HEALTH_RESERVE"}


def _time(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing {field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid {field}") from exc
    # The existing synthetic Health Reserve source stores UTC as naive DATETIME.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _number(value: object, field: str, *, low: float = 0, high: float | None = None) -> float:
    if isinstance(value, bool):
        raise ValueError(f"Invalid {field}")
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid {field}") from exc
    if not math.isfinite(result) or result < low or (high is not None and result > high):
        raise ValueError(f"Invalid {field}")
    return result


def _mindguard(record: dict) -> tuple[str, str, str, str, str, str]:
    record_id = record.get("session_id")
    if not isinstance(record_id, str) or not record_id:
        raise ValueError("Missing session_id")
    current = record.get("current_performance")
    if not isinstance(current, dict):
        raise ValueError("Missing current_performance")
    accuracy = _number(current.get("accuracy"), "accuracy", high=1)
    baseline = record.get("baselines", {}).get("per_domain")
    if not isinstance(baseline, dict):
        raise ValueError("Missing per-domain baseline")
    prior_value = _number(baseline.get("n_valid"), "baseline count")
    if not prior_value.is_integer():
        raise ValueError("Baseline count must be an integer")
    prior = int(prior_value)
    if prior >= 3 and baseline.get("median") is not None:
        median = _number(baseline["median"], "baseline median", high=1)
        prior_end = baseline.get("ts_max_prior")
        if not prior_end or _time(prior_end, "history_end") >= _time(record.get("index_time"), "index_time"):
            raise ValueError("Baseline must end before current session")
        text = (f"This session accuracy was {accuracy:.1%}. Your prior same-domain median "
                f"was {median:.1%} across {prior} sessions.")
        kind = "session_comparison"
    else:
        prior_end = None
        text = (f"This session accuracy was {accuracy:.1%}. A same-domain comparison "
                "is not available yet.")
        kind = "session_summary"
    return record_id, record.get("index_time"), kind, text, ("Accuracy is the fraction of correct responses in this session. "
            "The comparison is descriptive and does not detect a medical condition."), prior_end


def _reserve(record: dict) -> tuple[str, str, str, str, str, str | None]:
    record_id = record.get("reserve_assessment_id")
    if not isinstance(record_id, str) or not record_id:
        raise ValueError("Missing reserve_assessment_id")
    score = _number(record.get("score"), "score", low=1, high=10)
    if not score.is_integer():
        raise ValueError("Score must be an integer")
    months = _number(record.get("obligation_buffer_months"), "obligation_buffer_months")
    # Verify the displayed score against the fixed baseline formula, without
    # treating this financial-buffer rank as treatment affordability.
    from dumosense_ai.score_adapter import SCORE_LOWER_BOUNDS
    if int(score) != sum(months >= bound for bound in SCORE_LOWER_BOUNDS):
        raise ValueError("Score and buffer months disagree")
    count_value = _number(record.get("prior_assessment_count"), "prior_assessment_count")
    if not count_value.is_integer():
        raise ValueError("Prior assessment count must be an integer")
    count = int(count_value)
    text = (f"Your recorded preparedness amount equals {months:.1f} months of "
            f"recorded financial obligations. Buffer rank: {int(score)} of 10.")
    if count >= 3:
        if record.get("prior_median_buffer_months") is None or record.get("delta_from_prior_median_months") is None:
            raise ValueError("Missing available baseline")
        median = _number(record["prior_median_buffer_months"], "prior median")
        delta = _number(abs(float(record.get("delta_from_prior_median_months"))), "prior delta")
        if not math.isclose(abs(months - median), delta, abs_tol=1e-8, rel_tol=0):
            raise ValueError("Prior median and delta disagree")
        text += f" Your prior median was {median:.1f} months across {count} earlier assessments."
        kind = "buffer_comparison"
    else:
        if record.get("prior_median_buffer_months") is not None:
            raise ValueError("Baseline reported with insufficient history")
        text += " A personal comparison is not available yet."
        kind = "buffer_summary"
    return (record_id, record.get("assessed_at"), kind, text,
            "This is a descriptive obligation-buffer rank, not an estimate of healthcare costs or affordability.", None)


def compose_insight(record: dict, *, product_code: str, authenticated_user_id: str,
                    consent_verified: bool, enrollment_verified: bool,
                    source_run: dict) -> dict:
    """Return a DB-ready, non-alert insight payload from a trusted completed run.

    Boolean verification flags may only come from the authenticated backend,
    never directly from an HTTP request body.
    """
    if product_code not in PRODUCTS:
        raise ValueError("Unsupported product")
    if not isinstance(record, dict) or not authenticated_user_id or record.get("user_id") != authenticated_user_id:
        raise PermissionError("Record does not belong to the authenticated user")
    if consent_verified is not True or enrollment_verified is not True:
        raise PermissionError("Current consent and active enrollment required")
    if not isinstance(source_run, dict) or source_run.get("status") != "completed":
        raise ValueError("A completed trusted source run is required")
    run_id = source_run.get("run_id")
    version = source_run.get("model_version")
    if not isinstance(run_id, str) or not run_id or not isinstance(version, str) or not version:
        raise ValueError("Missing source run provenance")
    if source_run.get("product_code") != product_code or record.get("model_version") != version:
        raise ValueError("Source run product or model version mismatch")
    if record.get("run_id") is not None and record["run_id"] != run_id:
        raise ValueError("Record belongs to a different run")
    builder = _mindguard if product_code == "MINDGUARD" else _reserve
    record_id, observed_at, kind, text, explanation, prior_end = builder(record)
    observed = _time(observed_at, "observed_at")
    if prior_end is not None and _time(prior_end, "history_end") >= observed:
        raise ValueError("Future history is not allowed")
    # Provenance metadata is internal: the caller must bind source_run to a
    # verified artifact/database row before publishing this payload.
    key = "|".join((VERSION, product_code, authenticated_user_id, run_id, record_id))
    insight_id = "INS" + sha256(key.encode()).hexdigest()[:16]
    return {
        "product_code": product_code,
        "intelligence_run": {"source_run_id": run_id, "user_id": authenticated_user_id,
                             "product_code": product_code, "source_model_version": version,
                             "composition_version": VERSION, "input_end_date": observed.isoformat(),
                             "run_status": "completed"},
        "insight": {"insight_id": insight_id, "source_record_id": record_id,
                    "insight_type": kind, "insight_text": text,
                    "severity_or_priority": "low", "explanation_text": explanation},
        "recommendation": {"recommendation_id": "REC" + sha256((key + "|view").encode()).hexdigest()[:16],
                           "insight_id": insight_id, "recommendation_type": "review_history",
                           "recommendation_text": "You can review your recorded history in the app.",
                           "priority": "low"},
        "delivery": {"automatic_alert": False, "clinical_claim": False,
                     "external_notification": False},
    }
