"""Loopback-only Ollama explanation adapter for internal laptop validation."""
from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


_CHAT_URL = "http://127.0.0.1:11434/api/chat"


@dataclass(frozen=True)
class OllamaExplanationModel:
    model: str = "medgemma1.5:4b-it-q4_K_M"
    timeout_seconds: int = 180

    def generate(self, context: dict) -> dict:
        """Generate one bounded JSON explanation; agent.validate_generation checks it."""
        if not isinstance(context, dict) or not context.get("states"):
            raise ValueError("A structured product state is required")
        allowed = context.get("allowed_actions", [])
        evidence_ids = [item["source_id"] for item in context.get("evidence", [])]
        schema = {
            "type": "object", "additionalProperties": False,
            "properties": {
                "text": {"type": "string", "maxLength": 1200},
                "action_class": {"type": "string", "enum": allowed},
                "evidence_ids": {"type": "array", "items": {"type": "string", "enum": evidence_ids},
                                 "uniqueItems": True},
            },
            "required": ["text", "action_class", "evidence_ids"],
        }
        instructions = (
            "Explain only the supplied Dumosense product observations. The product "
            "calculations are authoritative; do not recompute them. Do not diagnose, "
            "predict disease, prescribe treatment, promise outcomes, or give financial "
            "advice. State uncertainty plainly. Do not add numbers that are absent from "
            "the states. Evidence IDs must refer only to the supplied approved excerpts; "
            "use an empty list when none are supplied. Return only JSON matching the schema."
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
            "format": schema,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 320, "num_ctx": 2048},
        }
        request = Request(_CHAT_URL, data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.load(response)
            generated = json.loads(result["message"]["content"])
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError,
                KeyError, TypeError) as exc:
            raise ValueError("Local Ollama generation failed") from exc
        if not isinstance(generated, dict):
            raise ValueError("Local Ollama response is not a JSON object")
        return generated
