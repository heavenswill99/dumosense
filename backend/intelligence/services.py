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
    """Persist a MindGuard run, insight and recommendation atomically."""
    from django.core.exceptions import ValidationError
    from django.db import transaction
    from django.utils import timezone

    from intelligence.models import IntelligenceRun, Insight, Recommendation

    if not user_id or not isinstance(insight_data, dict):
        raise ValidationError("Invalid MindGuard persistence request.")

    trace = insight_data.get("traceability")
    content = insight_data.get("insight")
    recommendation_data = insight_data.get("recommendation")
    delivery = insight_data.get("delivery")

    if not all(
        isinstance(item, dict)
        for item in (trace, content, recommendation_data, delivery)
    ):
        raise ValidationError("Incomplete MindGuard output.")

    if (
        insight_data.get("product_code") != "MINDGUARD"
        or delivery.get("automatic_alert") is not False
        or delivery.get("clinical_claim") is not False
    ):
        raise ValidationError("Unsafe MindGuard output.")

    run_id = trace.get("run_id")
    model_version = trace.get("model_version")
    session_id = trace.get("session_id")
    insight_type = content.get("insight_type")
    insight_text = content.get("text")
    recommendation_type = recommendation_data.get("recommendation_type")
    recommendation_text = recommendation_data.get("text")

    required_strings = (
        run_id, model_version, session_id,
        insight_type, insight_text,
        recommendation_type, recommendation_text,
    )

    if any(not isinstance(value, str) or not value.strip()
           for value in required_strings):
        raise ValidationError("Missing MindGuard output fields.")

    if len(run_id) > 20:
        raise ValidationError("MindGuard run ID exceeds database limit.")

    if len(model_version) > 100:
        raise ValidationError("Model version exceeds database limit.")

    if len(insight_type) > 100 or len(recommendation_type) > 100:
        raise ValidationError("MindGuard output type exceeds database limit.")

    if len(session_id) > 20:
        raise ValidationError("Invalid assessment session ID.")

    if content.get("priority") not in ("low",):
        raise ValidationError("Unsupported insight priority.")

    if recommendation_data.get("priority") not in ("low",):
        raise ValidationError("Unsupported recommendation priority.")

    insight_id = make_mindguard_insight_id(run_id)

    recommendation_id = (
        "REC" + sha256(
            f"{run_id}|recommendation".encode("utf-8")
        ).hexdigest()[:17]
    )

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
            or run.trigger_type != "assessment_completed"
            or run.run_status != "completed"
        ):
            raise ValidationError("Conflicting MindGuard run.")

        insight, _ = Insight.objects.get_or_create(
            insight_id=insight_id,
            defaults={
                "run": run,
                "user_id": user_id,
                "product_code": "MINDGUARD",
                "insight_type": insight_type,
                "insight_text": insight_text,
                "severity_or_priority": content["priority"],
                "explanation_text": content.get("explanation"),
                "generated_at": timezone.now(),
            },
        )

        if (
            insight.run_id != run_id
            or insight.user_id != user_id
            or insight.product_code != "MINDGUARD"
            or insight.insight_type != insight_type
            or insight.insight_text != insight_text
            or insight.severity_or_priority != content["priority"]
            or insight.explanation_text != content.get("explanation")
        ):
            raise ValidationError("Conflicting MindGuard insight.")

        recommendation, _ = Recommendation.objects.get_or_create(
            recommendation_id=recommendation_id,
            defaults={
                "insight": insight,
                "user_id": user_id,
                "product_code": "MINDGUARD",
                "recommendation_type": recommendation_type,
                "recommendation_text": recommendation_text,
                "priority": recommendation_data["priority"],
                "created_at": timezone.now(),
            },
        )

        if (
            recommendation.insight_id != insight_id
            or recommendation.user_id != user_id
            or recommendation.product_code != "MINDGUARD"
            or recommendation.recommendation_type != recommendation_type
            or recommendation.recommendation_text != recommendation_text
            or recommendation.priority != recommendation_data["priority"]
        ):
            raise ValidationError("Conflicting MindGuard recommendation.")

    return insight
