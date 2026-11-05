"""Local MindGuard insight worker. Not an HTTP endpoint."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine_v3 import compute_baseline_sequence
from insight_adapter import build_insight


def main():
    try:
        request = json.load(sys.stdin)
        record = request["record"]

        if "history" in request:
            history = request["history"]
            values = [item["accuracy"] for item in history]
            timestamps = [item["calculated_at"] for item in history]

            values.append(record["current_performance"]["accuracy"])
            timestamps.append(
                record.get("baseline_cutoff", record["index_time"])
            )

            baseline = compute_baseline_sequence(
                values,
                timestamps,
            )[-1]

            record["baselines"] = {"per_domain": baseline}

        result = build_insight(
            record,
            authenticated_user_id=request["authenticated_user_id"],
            consent_verified=request["consent_verified"],
        )

        print(json.dumps({"success": True, "result": result}))

    except (KeyError, ValueError, PermissionError, TypeError) as exc:
        print(json.dumps({
            "success": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
