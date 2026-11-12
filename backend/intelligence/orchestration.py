
"""Orchestration of MindGuard ML insight generation and persistence."""

from django.core.exceptions import ValidationError

from intelligence.services import save_mindguard_insight
from mindguard.services import generate_mindguard_insight


def process_mindguard_assessment(*, user, session_id):
    """
    Generate and persist an insight for a completed assessment.

    Authentication, assessment ownership, and cognitive consent
    are checked by generate_mindguard_insight().
    """

    # Step 1: Execute the existing validated ML integration.
    insight_data = generate_mindguard_insight(
        user=user,
        session_id=session_id,
    )

    # Step 2: Validate the response before persistence.
    if not isinstance(insight_data, dict):
        raise ValidationError("Invalid MindGuard insight response.")

    trace = insight_data.get("traceability")

    if not isinstance(trace, dict):
        raise ValidationError("Missing MindGuard traceability.")

    if str(trace.get("session_id")) != str(session_id):
        raise ValidationError("MindGuard session mismatch.")

    if insight_data.get("product_code") != "MINDGUARD":
        raise ValidationError("Unexpected MindGuard product.")

    # Step 3: Persist using the authenticated user's ID.
    saved_insight = save_mindguard_insight(
        user_id=user.pk,
        insight_data=insight_data,
    )

    return saved_insight
