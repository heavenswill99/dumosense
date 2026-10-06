"""Bounded offline Dumosense orchestrator. No model downloads or database access."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
import json
import re
from dumosense_ai.service import VERSION, compose_insight

TOOLS = {"MINDGUARD": "get_mindguard_state", "HEALTH_RESERVE": "get_health_reserve_state"}
MIND = ("mindguard", "memory", "cognition", "cognitive", "attention", "thinking")
RESERVE = ("health reserve", "reserve", "preparedness", "buffer", "obligation", "savings", "financial")
BOTH = ("overall", "both", "together", "health security")
EMERGENCY = ("suicide", "kill myself", "self harm", "chest pain", "can't breathe", "cannot breathe")

class LocalExplanationModel(Protocol):
    def generate(self, context: dict) -> dict: ...

@dataclass(frozen=True)
class Plan:
    intent: str
    tools: tuple[str, ...]
    status: str = "ready"

def route(query: str) -> Plan:
    if not isinstance(query, str) or not query.strip() or len(query) > 2000:
        raise ValueError("A short question is required")
    q = query.casefold()
    if any(w in q for w in EMERGENCY):
        return Plan("emergency", (), "escalate")
    m, h = any(w in q for w in MIND), any(w in q for w in RESERVE)
    if (m and h) or (any(w in q for w in BOTH) and not (m or h)):
        return Plan("combined", tuple(TOOLS.values()))
    if m:
        return Plan("mindguard", (TOOLS["MINDGUARD"],))
    if h:
        return Plan("health_reserve", (TOOLS["HEALTH_RESERVE"],))
    return Plan("out_of_scope", (), "abstain")

def validate_generation(value: dict, context: dict) -> dict:
    """Narrow schema gate; not a substitute for clinical red-team evaluation."""
    if not isinstance(value, dict) or set(value) != {"text", "action_class", "evidence_ids"}:
        raise ValueError("Invalid explanation schema")
    body = value["text"]
    if not isinstance(body, str) or not body.strip() or len(body) > 1200:
        raise ValueError("Invalid explanation text")
    if value["action_class"] not in context["allowed_actions"]:
        raise ValueError("Unapproved action")
    ids = value["evidence_ids"]
    approved = {item["source_id"] for item in context["evidence"]}
    if not isinstance(ids, list) or len(ids) != len(set(ids)) or not all(isinstance(i,str) and i in approved for i in ids):
        raise ValueError("Unsupported evidence")
    low = body.casefold()
    if any(x in low for x in ("you have dementia", "you have alzheimer", "you have a disease", "guaranteed to cover", "guarantees coverage", "buy this stock", "invest in", "caused your cognitive")):
        raise ValueError("Prohibited claim")
    numbers = set(re.findall(r"(?<![\w])\d+(?:\.\d+)?%?", json.dumps(context["states"])))
    if set(re.findall(r"(?<![\w])\d+(?:\.\d+)?%?", body)) - numbers:
        raise ValueError("Unverified number")
    if any(state["observation"] not in body for state in context["states"]):
        raise ValueError("Requested product observation omitted or altered")
    return value

def run(query: str, *, authenticated_user_id: str, trusted_access: dict,
        source_records: dict, source_runs: dict, evidence: tuple[dict, ...] = (),
        local_model: LocalExplanationModel | None = None) -> dict:
    """Use only approved product tools and compact state from a trusted backend."""
    plan = route(query)
    audit = {"orchestrator_version": VERSION, "intent": plan.intent,
             "planned_tools": list(plan.tools), "called_tools": [], "evidence_ids": []}
    if plan.status != "ready":
        message = ("If this may be an emergency, seek immediate help from local emergency services."
                   if plan.status == "escalate" else "I cannot answer that from the available product data.")
        return {"status": plan.status, "plan": audit, "context": None, "response": message}
    if not authenticated_user_id or not all(isinstance(x, dict) for x in (trusted_access, source_records, source_runs)):
        raise PermissionError("Trusted identity and mappings required")
    states = []
    for tool in plan.tools:
        product = next(p for p, t in TOOLS.items() if t == tool)
        access = trusted_access.get(product, {})
        if access.get("consent_verified") is not True or access.get("enrollment_verified") is not True:
            raise PermissionError(f"Current access not verified for {product}")
        if product not in source_records or product not in source_runs:
            return {"status": "insufficient_data", "plan": audit, "context": None,
                    "response": "The requested product state is not available."}
        state = compose_insight(source_records[product], product_code=product,
                                authenticated_user_id=authenticated_user_id,
                                consent_verified=True, enrollment_verified=True,
                                source_run=source_runs[product])
        states.append({"product_code": product,
                       "source_run_id": state["intelligence_run"]["source_run_id"],
                       "source_record_id": state["insight"]["source_record_id"],
                       "model_version": state["intelligence_run"]["source_model_version"],
                       "observed_at": state["intelligence_run"]["input_end_date"],
                       "insight_type": state["insight"]["insight_type"],
                       "observation": state["insight"]["insight_text"],
                       "uncertainty": state["insight"]["explanation_text"]})
        audit["called_tools"].append(tool)
    selected = []
    for item in evidence[:3]:
        if not isinstance(item, dict) or item.get("approved") is not True or not item.get("source_id"):
            raise ValueError("Unapproved evidence")
        excerpt = item.get("excerpt")
        if not isinstance(excerpt, str) or len(excerpt) > 600:
            raise ValueError("Invalid evidence excerpt")
        selected.append({"source_id": item["source_id"], "excerpt": excerpt})
    audit["evidence_ids"] = [x["source_id"] for x in selected]
    context = {"schema_version": "1.0", "intent": plan.intent, "states": states,
               "evidence": selected, "allowed_actions": ["review_history"],
               "prohibited_claims": ["diagnosis", "causation", "guaranteed outcome", "regulated financial advice"]}
    if local_model is None:
        return {"status": "deterministic", "plan": audit, "context": context,
                "response": " ".join(x["observation"] for x in states),
                "release_status": "internal_validation_only"}
    try:
        generated = validate_generation(local_model.generate(context), context)
    except (ValueError, TypeError, KeyError):
        return {"status": "generation_rejected", "plan": audit, "context": context,
                "response": "I cannot provide a verified explanation right now.",
                "release_status": "internal_validation_only"}
    return {"status": "generated", "plan": audit, "context": context,
            "response": generated["text"], "action_class": generated["action_class"],
            "cited_evidence_ids": generated["evidence_ids"],
            "release_status": "internal_validation_only"}
