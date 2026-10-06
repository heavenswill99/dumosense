"""User-scoped retrieval of persisted central-agent insights."""
from django.db import transaction
from .gateway import require_access
from .models import Insight, Recommendation

PRODUCTS = ("MINDGUARD", "HEALTH_RESERVE")

@transaction.atomic
def read_insights(*, user, product: str | None = None, limit: int = 10) -> list[dict]:
    if product is not None and product not in PRODUCTS:
        raise ValueError("Unsupported product")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
        raise ValueError("Invalid limit")
    allowed = []
    for code in (product,) if product else PRODUCTS:
        try:
            require_access(user.user_id, code)
        except PermissionError:
            if product:
                raise
        else:
            allowed.append(code)
    if not allowed:
        raise PermissionError("No currently permitted products")
    rows = list(Insight.objects.select_related("run").filter(
        user_id=user.user_id, product_code__in=allowed,
        run__run_status="completed", run__trigger_type="user_query")
        .order_by("-generated_at", "-insight_id")[:limit])
    result = []
    for item in rows:
        recommendation = (Recommendation.objects.filter(
            user_id=user.user_id, insight_id=item.insight_id,
            product_code=item.product_code).order_by("-created_at").first())
        result.append({"insight_id": item.insight_id, "product_code": item.product_code,
                       "insight_type": item.insight_type, "text": item.insight_text,
                       "explanation": item.explanation_text,
                       "generated_at": item.generated_at.isoformat(),
                       "source_run_id": item.run_id,
                       "source_model_version": item.run.model_or_rule_version,
                       "recommendation": ({"type": recommendation.recommendation_type,
                                           "text": recommendation.recommendation_text}
                                          if recommendation else None)})
    return result
