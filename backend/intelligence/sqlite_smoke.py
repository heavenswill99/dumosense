"""Disposable ORM smoke for the central agent; never connects to live MySQL.

Run from backend/ with the local venv: python intelligence/sqlite_smoke.py
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
import config.settings as project_settings
project_settings.DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
import django
django.setup()

from datetime import timedelta
from decimal import Decimal
from django.db import connection
from django.utils import timezone
from accounts.models import User, ProductEnrollment
from consent.models import Consent
from assessments.models import AssessmentType, AssessmentSession
from mindguard.models import CognitiveResult
from health_reserve.models import HealthReserveAssessment
from intelligence.models import IntelligenceRun, Insight, Recommendation
from intelligence.services import query_agent
from intelligence.reads import read_insights
from events.models import Event


def main() -> None:
    tables = [User, Consent, ProductEnrollment, AssessmentType, AssessmentSession,
              CognitiveResult, HealthReserveAssessment, IntelligenceRun, Insight,
              Recommendation, Event]
    with connection.schema_editor() as editor:
        for model in tables:
            editor.create_model(model)
    now = timezone.now()
    user = User.objects.create(user_id="U1", email="u1@example.test", first_name="A",
                               last_name="B", account_status="active", is_active=True)
    for index, product in enumerate(("MINDGUARD", "HEALTH_RESERVE")):
        ProductEnrollment.objects.create(enrollment_id=f"E{index}", user=user,
            product_code=product, enrollment_status="active",
            enrolled_at=now-timedelta(days=100), discontinued_at=None)
    consents = {}
    for index, consent_type in enumerate(("product_data_processing", "cognitive_assessment",
                                          "health_reserve_data")):
        consents[consent_type] = Consent.objects.create(
            consent_id=f"C{index}", user=user, consent_type=consent_type,
            purpose="test", consent_version=Decimal("1.00"), status="granted",
            granted_at=now-timedelta(days=100), withdrawn_at=None)
    assessment_type = AssessmentType.objects.create(
        assessment_type_id="A1", assessment_name="Attention", cognitive_domain="attention", active=1)
    session = AssessmentSession.objects.create(
        session_id="S1", user=user, assessment_type=assessment_type,
        started_at=now-timedelta(days=1), completed_at=now-timedelta(days=1),
        session_status="completed", difficulty_level=1,
        consent=consents["cognitive_assessment"])
    CognitiveResult.objects.create(
        cognitive_result_id="R1", session=session, user=user, assessment_type=assessment_type,
        total_trials=10, correct_responses=8, incorrect_responses=2,
        omissions=0, accuracy_rate=Decimal("0.8"), calculated_at=now-timedelta(days=1))
    HealthReserveAssessment.objects.create(
        reserve_assessment_id="H1", user=user, assessed_at=now-timedelta(days=1),
        healthcare_coverage_status="partial", estimated_healthcare_exposure=Decimal("0"),
        emergency_health_resources=Decimal("100"), monthly_financial_obligations=Decimal("100"),
        number_of_dependants=0, current_preparedness_amount=Decimal("300"),
        preparedness_target=Decimal("0"), preparedness_gap=Decimal("0"),
        preparedness_ratio=Decimal("0"), reserve_status="unknown")
    result = query_agent(user=user, question="How am I doing overall?")
    assert result["status"] == "deterministic" and len(result["products"]) == 2
    counts = [model.objects.count() for model in (IntelligenceRun, Insight, Recommendation, Event)]
    assert counts == [2, 2, 2, 2], counts
    assert len(read_insights(user=user)) == 2
    reserve_consent = consents["health_reserve_data"]
    reserve_consent.status = "withdrawn"
    reserve_consent.withdrawn_at = now
    reserve_consent.save(update_fields=["status", "withdrawn_at"])
    remaining = read_insights(user=user)
    assert len(remaining) == 1 and remaining[0]["product_code"] == "MINDGUARD"
    try:
        read_insights(user=user, product="HEALTH_RESERVE")
    except PermissionError:
        pass
    else:
        raise AssertionError("Withdrawn reserve consent must block retrieval")
    print({"status": "passed", "database": "disposable SQLite memory",
           "runs_insights_recommendations_events": counts,
           "withdrawn_product_hidden": True})


if __name__ == "__main__":
    main()
