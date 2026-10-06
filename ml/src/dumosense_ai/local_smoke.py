"""Synthetic local MedGemma smoke test. Never reads user data or the database."""
from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import urlopen

from dumosense_ai.agent import run
from dumosense_ai.ollama_model import OllamaExplanationModel


def main() -> int:
    model = OllamaExplanationModel()
    try:
        with urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as response:
            available = {item["name"] for item in json.load(response)["models"]}
    except (URLError, TimeoutError, OSError, KeyError, ValueError) as exc:
        print(f"Ollama is not reachable on this laptop: {exc}")
        return 2
    if model.model not in available:
        print(f"Model {model.model} is not installed. Download it yourself with:")
        print(f"ollama pull {model.model}")
        return 2

    record = {
        "user_id": "synthetic-user", "run_id": "synthetic-run",
        "model_version": "SYNTHETIC_SMOKE_1", "session_id": "synthetic-session",
        "index_time": "2026-01-10T12:00:00+00:00",
        "current_performance": {"accuracy": 0.8},
        "baselines": {"per_domain": {"n_valid": 0, "median": None,
                                     "ts_max_prior": None}},
    }
    result = run(
        "Explain my memory result", authenticated_user_id="synthetic-user",
        trusted_access={"MINDGUARD": {"consent_verified": True,
                                       "enrollment_verified": True}},
        source_records={"MINDGUARD": record},
        source_runs={"MINDGUARD": {"status": "completed",
                                    "run_id": "synthetic-run",
                                    "model_version": "SYNTHETIC_SMOKE_1",
                                    "product_code": "MINDGUARD"}},
        local_model=model,
    )
    print(json.dumps({"status": result["status"], "response": result["response"],
                      "release_status": result.get("release_status")}, indent=2))
    return 0 if result["status"] == "generated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
