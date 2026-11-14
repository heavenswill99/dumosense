"""Approved public feedback, separate from immutable analytics/ML output.

Never forward persisted prose here: legacy text, explanations, recommendations
and future model output can contain scores even when they contain no digits.
Use an explicit copy catalogue instead of trying to scrub numbers with regexes.
"""

PUBLIC_EXPLANATION = (
    "This is an assessment record, not a medical assessment or diagnosis."
)
PUBLIC_RECOMMENDATION = "Continue your usual assessment schedule."
PUBLIC_SUMMARIES = {
    "session_summary": "Your assessment has been recorded.",
    "insufficient_data": (
        "Your assessment has been recorded. More assessment history is needed "
        "before a comparison can be offered."
    ),
}


def public_insight(insight, *, user_id):
    """Allowlist metadata and approved copy; do not mutate the persisted row."""
    insight_type = insight.insight_type
    if insight_type not in PUBLIC_SUMMARIES:
        insight_type = "session_summary"
    recommendations = [
        {
            "recommendation_id": rec.recommendation_id,
            "recommendation_type": "maintain_monitoring",
            "text": PUBLIC_RECOMMENDATION,
            "priority": "low",
        }
        for rec in insight.recommendations.all()
        if rec.user_id == user_id and rec.product_code == "MINDGUARD"
    ]
    return {
        "insight_id": insight.insight_id,
        "run_id": insight.run_id,
        "insight_type": insight_type,
        "text": PUBLIC_SUMMARIES[insight_type],
        "priority": "low",
        "explanation": PUBLIC_EXPLANATION,
        "generated_at": insight.generated_at,
        "model_or_rule_version": insight.run.model_or_rule_version,
        "recommendations": recommendations,
    }
