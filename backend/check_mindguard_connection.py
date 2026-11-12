import os
import django
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from mindguard.services import generate_mindguard_insight

def dt(day, hour=10):
    return datetime(2026, 10, day, hour, tzinfo=timezone.utc)

user = MagicMock()
user.is_authenticated = True
user.pk = "TEST001"

session = MagicMock()
session.session_id = "SESSION004"
session.started_at = dt(27)
session.assessment_type.cognitive_domain = "memory"

result = MagicMock()
result.accuracy_rate = 0.85
result.calculated_at = dt(27, 12)

history = [
    {"accuracy_rate": 0.70, "calculated_at": dt(20)},
    {"accuracy_rate": 0.75, "calculated_at": dt(22)},
    {"accuracy_rate": 0.80, "calculated_at": dt(24)},
]

with (
    patch("mindguard.services.AssessmentSession.objects.filter") as sessions,
    patch("mindguard.services.Consent.objects.filter") as consents,
    patch("mindguard.services.CognitiveResult.objects.filter") as results,
):
    sessions.return_value.first.return_value = session
    consents.return_value.exists.return_value = True

    results.return_value.first.return_value = result
    results.return_value.exclude.return_value.order_by.return_value.values.return_value = history

    insight = generate_mindguard_insight(
        user=user,
        session_id="SESSION004",
    )

    text = insight["insight"]["text"]

    assert "85.0%" in text
    assert "75.0%" in text
    assert "3 sessions" in text
    assert insight["delivery"]["automatic_alert"] is False

    history_query = results.call_args_list[1].kwargs
    assert history_query["user"] is user
    assert history_query["assessment_type__cognitive_domain"] == "memory"
    assert history_query["session__session_status"] == "completed"
    assert history_query["calculated_at__lt"] == session.started_at

    print("PASS: Django-to-ML historical integration")
    print("Product:", insight["product_code"])
    print("Insight:", text)
    print("Session:", insight["traceability"]["session_id"])
    print("History end:", insight["traceability"]["history_end"])
    print("Automatic alert:", insight["delivery"]["automatic_alert"])
