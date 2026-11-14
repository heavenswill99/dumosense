"""Synthetic fixtures for the guarded, disposable MindGuard test database."""
from decimal import Decimal
from django.utils import timezone
from accounts.models import User
from assessments.models import AssessmentSession, AssessmentType, CognitiveTask
from consent.models import Consent
from mindguard.models import CognitiveResult


def create_user(suffix):
    return User.objects.create_user(
        user_id="USR" + suffix, email=f"{suffix.lower()}@example.invalid",
        password="SyntheticPassword!41", first_name="Synthetic", last_name="Tester")


def create_consent(user, suffix, *, consent_type="cognitive_assessment"):
    return Consent.objects.create(
        consent_id="CON" + suffix, user=user, consent_type=consent_type,
        purpose="Synthetic MindGuard test", consent_version=Decimal("1.00"),
        status="granted", granted_at=timezone.now())


def create_session(user, consent, assessment_type, suffix, *, minutes_ago=5):
    now = timezone.now()
    return AssessmentSession.objects.create(
        session_id="SES" + suffix, user=user, consent=consent, assessment_type=assessment_type,
        started_at=now - timezone.timedelta(minutes=minutes_ago), completed_at=now,
        session_status="completed", difficulty_level=1, device_type="desktop")


def create_result(session, suffix, *, accuracy="0.85", calculated_at=None):
    return CognitiveResult.objects.create(
        cognitive_result_id="CR" + suffix, session=session, user=session.user,
        assessment_type=session.assessment_type, total_trials=20, correct_responses=17,
        incorrect_responses=3, omissions=0, accuracy_rate=Decimal(accuracy),
        mean_reaction_time_ms=Decimal("650.00"), median_reaction_time_ms=Decimal("630.00"),
        reaction_time_variability_ms=Decimal("50.00"), completion_time_seconds=Decimal("120.00"),
        difficulty_level=1, baseline_difference=Decimal("0.13"),
        previous_session_difference=Decimal("0.07"), calculated_at=calculated_at or timezone.now())


def insight_payload(run_id="MG123456789012345678", session_id="SESPHASE1"):
    return {
        "product_code": "MINDGUARD",
        "traceability": {"run_id": run_id, "session_id": session_id, "model_version": "STAT_ENGINE_MVP_1.0"},
        "insight": {"insight_type": "session_summary", "text": "Accuracy 85.0%; prior median 72.0%.",
                    "explanation": "Historical z score 1.25; reaction time 630 ms.", "priority": "low"},
        "recommendation": {"recommendation_type": "maintain_monitoring",
                           "text": "Review your score of 85 percent.", "priority": "low"},
        "delivery": {"automatic_alert": False, "clinical_claim": False},
    }


class MindGuardFixtureMixin:
    def setUp(self):
        super().setUp()
        self.user = create_user("PHASE1")
        self.other = create_user("OTHER")
        self.consent = create_consent(self.user, "PHASE1")
        self.other_consent = create_consent(self.other, "OTHER")
        self.assessment_type = AssessmentType.objects.create(
            assessment_type_id="ATMEMORY", assessment_name="Memory assessment",
            cognitive_domain="memory", description="Synthetic fixture", active=1)
        self.task = CognitiveTask.objects.create(
            task_id="TASKMEMORY", assessment_type=self.assessment_type,
            task_name="Synthetic task", task_type="symbol", default_difficulty=1, active=1)
        self.session = create_session(self.user, self.consent, self.assessment_type, "PHASE1")
        self.result = create_result(self.session, "PHASE1")
