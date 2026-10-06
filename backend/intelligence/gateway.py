"""Typed Django ORM gateway for the central Dumosense agent.

All selectors require the authenticated user ID. No LLM sees a QuerySet or SQL.
"""
from datetime import timedelta
from statistics import median

from accounts.models import ProductEnrollment, User
from consent.models import Consent
from health_reserve.models import HealthReserveAssessment
from mindguard.models import CognitiveResult
from dumosense_ai.score_adapter import score_buffer

PRODUCT_CONSENT = {"MINDGUARD": "cognitive_assessment",
                   "HEALTH_RESERVE": "health_reserve_data"}


def require_access(user_id: str, product: str) -> dict:
    """Check active account, enrollment and both core/product consent at request time."""
    if product not in PRODUCT_CONSENT:
        raise ValueError("Unsupported product")
    if not User.objects.select_for_update().filter(user_id=user_id, account_status="active", is_active=True).exists():
        raise PermissionError("Account is not active")
    if not ProductEnrollment.objects.select_for_update().filter(user_id=user_id, product_code=product,
                                            enrollment_status="active",
                                            discontinued_at__isnull=True).exists():
        raise PermissionError("Product enrollment is not active")
    for consent_type in ("product_data_processing", PRODUCT_CONSENT[product]):
        if not Consent.objects.select_for_update().filter(user_id=user_id, consent_type=consent_type,
                                      status="granted", withdrawn_at__isnull=True).exists():
            raise PermissionError(f"Current {consent_type} consent required")
    return {"consent_verified": True, "enrollment_verified": True}


def mindguard_state(user_id: str) -> dict | None:
    """Read current completed result and strictly earlier same-domain history."""
    current = (CognitiveResult.objects.select_related("assessment_type", "session")
               .filter(user_id=user_id, session__session_status="completed",
                       accuracy_rate__isnull=False)
               .order_by("-calculated_at", "-cognitive_result_id").first())
    if current is None:
        return None
    domain = current.assessment_type.cognitive_domain
    prior = list(CognitiveResult.objects.filter(
        user_id=user_id, assessment_type__cognitive_domain=domain,
        session__session_status="completed", accuracy_rate__isnull=False,
        calculated_at__lt=current.calculated_at,
        calculated_at__gte=current.calculated_at - timedelta(days=365))
        .order_by("-calculated_at", "-cognitive_result_id")
        .values("accuracy_rate", "calculated_at")[:5])
    values = [float(row["accuracy_rate"]) for row in prior]
    baseline = median(values) if len(values) >= 3 else None
    latest_prior = prior[0]["calculated_at"].isoformat() if baseline is not None else None
    return {"user_id": user_id, "run_id": None,
            "session_id": current.session_id,
            "model_version": "MG_DB_DESCRIPTIVE_1.0",
            "index_time": current.calculated_at.isoformat(),
            "current_performance": {"accuracy": float(current.accuracy_rate)},
            "baselines": {"per_domain": {"n_valid": len(prior), "median": baseline,
                                          "ts_max_prior": latest_prior}}}


def health_reserve_state(user_id: str) -> dict | None:
    """Use the shared fixed score and last five strictly earlier snapshots."""
    current = (HealthReserveAssessment.objects.filter(user_id=user_id)
               .order_by("-assessed_at", "-reserve_assessment_id").first())
    if current is None:
        return None
    scored = score_buffer(current.current_preparedness_amount,
                          current.monthly_financial_obligations)
    prior = list(HealthReserveAssessment.objects.filter(
        user_id=user_id, assessed_at__lt=current.assessed_at,
        assessed_at__gte=current.assessed_at - timedelta(days=365))
        .order_by("-assessed_at", "-reserve_assessment_id")
        .values("current_preparedness_amount", "monthly_financial_obligations")[:5])
    months = [score_buffer(row["current_preparedness_amount"],
                           row["monthly_financial_obligations"])["obligation_buffer_months"]
              for row in prior]
    prior_median = median(months) if len(months) >= 3 else None
    return {"user_id": user_id, "reserve_assessment_id": current.reserve_assessment_id,
            "model_version": "HR_BUFFER_BASELINE_1.0",
            "assessed_at": current.assessed_at.isoformat(),
            "score": scored["score"],
            "obligation_buffer_months": scored["obligation_buffer_months"],
            "prior_assessment_count": len(prior),
            "prior_median_buffer_months": prior_median,
            "delta_from_prior_median_months":
                scored["obligation_buffer_months"] - prior_median if prior_median is not None else None}
