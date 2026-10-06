"""Score the small, checked-in routing smoke corpus; not a deployment validation."""
import json
from pathlib import Path
from dumosense_ai.agent import route

def evaluate(path: Path | None = None) -> dict:
    path = path or Path(__file__).with_name("routing_eval_cases.json")
    cases = json.loads(path.read_text(encoding="utf-8"))
    intents = 0; tools = 0; unnecessary = 0
    for case in cases:
        got = route(case["query"])
        intents += got.intent == case["intent"]
        tools += list(got.tools) == case["tools"]
        unnecessary += len(set(got.tools) - set(case["tools"]))
    return {"cases":len(cases),"intent_accuracy":intents/len(cases),
            "tool_selection_accuracy":tools/len(cases),
            "unnecessary_tool_calls":unnecessary,
            "scope":"checked-in routing smoke corpus only"}

if __name__ == "__main__":
    print(json.dumps(evaluate(),indent=2))
