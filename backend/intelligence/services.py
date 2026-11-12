"""Persistence utilities for MindGuard intelligence outputs."""

from hashlib import sha256


def make_mindguard_insight_id(run_id):
    """Generate a stable, database-compatible insight identifier."""

    if not isinstance(run_id, str) or not run_id:
        raise ValueError("A valid MindGuard run ID is required.")

    return "INS" + sha256(
        run_id.encode("utf-8")
    ).hexdigest()[:17]


def save_mindguard_insight(*, user_id, insight_data):
    """Persist a validated MindGuard run and insight atomically."""
    from django.core.exceptions import ValidationError
    from django.db import transaction
    from django.utils import timezone

    from intelligence.models import IntelligenceRun, Insight

    if not user_id or not isinstance(insight_data, dict):
        raise ValidationError("Invalid MindGuard persistence request.")

    trace = insight_data.get("traceability")
    content = insight_data.get("insight")
    delivery = insight_data.get("delivery")

    if not all(isinstance(item, dict) for item in (trace, content, delivery)):
        raise ValidationError("Incomplete MindGuard insight.")

    if (
        insight_data.get("product_code") != "MINDGUARD"
        or delivery.get("automatic_alert") is not False
        or delivery.get("clinical_claim") is not False
    ):
        raise ValidationError("Unsafe MindGuard insight.")

    run_id = trace.get("run_id")
    model_version = trace.get("model_version")
    insight_type = content.get("insight_type")
    insight_text = content.get("text")

    if (
        not isinstance(run_id, str)
        or not 0 < len(run_id) <= 20
        or not isinstance(model_version, str)
        or not model_version
        or not isinstance(insight_type, str)
        or not insight_type
        or not isinstance(insight_text, str)
        or not insight_text
        or not trace.get("session_id")
    ):
        raise ValidationError("Invalid MindGuard insight fields.")

    insight_id = make_mindguard_insight_id(run_id)

    with transaction.atomic():
        run, _ = IntelligenceRun.objects.get_or_create(
            run_id=run_id,
            defaults={
                "user_id": user_id,
                "product_code": "MINDGUARD",
                "triggered_at": timezone.now(),
                "trigger_type": "assessment_completed",
                "model_or_rule_version": model_version,
                "run_status": "completed",
            },
        )

        if (
            run.user_id != user_id
            or run.product_code != "MINDGUARD"
            or run.model_or_rule_version != model_version
        ):
            raise ValidationError("Conflicting MindGuard intelligence run.")

        insight, _ = Insight.objects.get_or_create(
            insight_id=insight_id,
            defaults={
                "run": run,
                "user_id": user_id,
                "product_code": "MINDGUARD",
                "insight_type": insight_type,
                "insight_text": insight_text,
                "severity_or_priority": content.get("priority"),
                "explanation_text": content.get("explanation"),
                "generated_at": timezone.now(),
            },
        )

        if insight.run_id != run_id or insight.user_id != user_id:
            raise ValidationError("Conflicting MindGuard insight.")

    return insight
