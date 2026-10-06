"""Central agent integration with authenticated, user-scoped Django ORM data."""
from datetime import datetime, timezone as dt_timezone
from uuid import uuid4

from django.db import transaction
from django.conf import settings
from django.utils import timezone
from events.models import Event

from dumosense_ai.agent import TOOLS, route, run
from dumosense_ai.ollama_model import OllamaExplanationModel
from dumosense_ai.service import compose_insight
from .gateway import health_reserve_state, mindguard_state, require_access
from .models import IntelligenceRun, Insight, Recommendation

READERS = {"MINDGUARD": mindguard_state, "HEALTH_RESERVE": health_reserve_state}


def _id(prefix: str) -> str:
    return prefix + uuid4().hex[:16]


def _observed(record: dict, product: str) -> datetime:
    value = record["index_time" if product == "MINDGUARD" else "assessed_at"]
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_timezone.utc)
    return parsed


@transaction.atomic
def query_agent(*, user, question: str) -> dict:
    """Run one bounded query and atomically persist its traceable product outputs.

    No user ID, consent flag, model choice, or SQL is accepted from the client.
    """
    plan = route(question)
    user_id = user.user_id
    if plan.status != "ready":
        result = run(question, authenticated_user_id=user_id,
                     trusted_access={}, source_records={}, source_runs={})
        return {"status": result["status"], "response": result["response"],
                "products": [], "source_run_ids": []}
    access, records, source_runs = {}, {}, {}
    for tool in plan.tools:
        product = next(code for code, name in TOOLS.items() if name == tool)
        access[product] = require_access(user_id, product)
        record = READERS[product](user_id)
        if record is None:
            return {"status": "insufficient_data", "response": "The requested product state is not available.",
                    "products": [], "source_run_ids": []}
        records[product] = record
        source_runs[product] = {"status": "completed", "run_id": _id("RUN"),
                                "model_version": record["model_version"],
                                "product_code": product}
    local_model = (OllamaExplanationModel()
                   if getattr(settings, "DUMOSENSE_ENABLE_LOCAL_MODEL", False) else None)
    result = run(question, authenticated_user_id=user_id, trusted_access=access,
                 source_records=records, source_runs=source_runs,
                 local_model=local_model)
    if result["status"] not in ("deterministic", "generated"):
        return {"status": result["status"], "response": result["response"],
                "products": [], "source_run_ids": []}
    now = timezone.now()
    for product, record in records.items():
        source = source_runs[product]
        composed = compose_insight(record, product_code=product,
                                   authenticated_user_id=user_id,
                                   consent_verified=True, enrollment_verified=True,
                                   source_run=source)
        IntelligenceRun.objects.create(
            run_id=source["run_id"], user=user, product_code=product,
            triggered_at=now, trigger_type="user_query",
            model_or_rule_version=source["model_version"],
            input_start_date=None, input_end_date=_observed(record, product),
            run_status="completed")
        info = composed["insight"]
        Insight.objects.create(
            insight_id=info["insight_id"], run_id=source["run_id"],
            user=user, product_code=product, insight_type=info["insight_type"],
            insight_text=info["insight_text"],
            severity_or_priority=info["severity_or_priority"],
            explanation_text=info["explanation_text"], generated_at=now)
        action = composed["recommendation"]
        Recommendation.objects.create(
            recommendation_id=action["recommendation_id"],
            insight_id=info["insight_id"], user=user, product_code=product,
            recommendation_type=action["recommendation_type"],
            recommendation_text=action["recommendation_text"],
            priority=action["priority"], created_at=now)
        Event.objects.create(
            event_id=_id("EVT"), user=user, event_type="intelligence_query_completed",
            timestamp=now, source="dumosense_ai",
            related_entity_type="intelligence_run", related_entity_id=source["run_id"],
            metadata={"orchestrator_version": result["plan"]["orchestrator_version"],
                      "intent": result["plan"]["intent"],
                      "called_tools": result["plan"]["called_tools"],
                      "evidence_ids": result["plan"]["evidence_ids"],
                      "policy_status": result["status"]})
    return {"status": result["status"], "response": result["response"],
            "products": list(records),
            "source_run_ids": [source_runs[p]["run_id"] for p in records],
            "release_status": "internal_validation_only"}
