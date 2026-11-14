"""Exercise the active in-process ML service, without obsolete subprocess mocks."""
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from assessments.models import AssessmentType
from config.mindguard_test_runner import MindGuardDatabaseTestCase
from mindguard.models import CognitiveResult
from mindguard.services import build_insight, generate_mindguard_insight
from mindguard.test_support import MindGuardFixtureMixin, create_result, create_session


class MindGuardInsightServiceTests(MindGuardFixtureMixin, MindGuardDatabaseTestCase):
    def generate(self, user=None):
        return generate_mindguard_insight(user=user or self.user, session_id=self.session.pk)

    def test_authentication_required(self):
        with self.assertRaises(PermissionDenied):
            self.generate(AnonymousUser())

    def test_other_user_cannot_process_session(self):
        with self.assertRaises(PermissionDenied):
            self.generate(self.other)

    def test_current_consent_required(self):
        self.consent.status = "withdrawn"
        self.consent.save(update_fields=["status"])
        with self.assertRaises(PermissionDenied):
            self.generate()

    def test_completed_session_and_result_required(self):
        self.session.session_status = "started"
        self.session.save(update_fields=["session_status"])
        with self.assertRaises(PermissionDenied):
            self.generate()
        self.session.session_status = "completed"
        self.session.save(update_fields=["session_status"])
        self.result.delete()
        with self.assertRaises(ValidationError):
            self.generate()

    def test_current_accuracy_validation(self):
        for value in (None, Decimal("-0.01"), Decimal("1.01")):
            with self.subTest(value=value):
                CognitiveResult.objects.filter(pk=self.result.pk).update(accuracy_rate=value)
                with self.assertRaises(ValidationError):
                    self.generate()

    def test_historical_accuracy_validation(self):
        prior = create_session(self.user, self.consent, self.assessment_type, "BADHISTORY", minutes_ago=30)
        create_result(prior, "BADHISTORY", accuracy="1.01",
                      calculated_at=self.session.started_at - timezone.timedelta(minutes=1))
        with self.assertRaises(ValidationError):
            self.generate()

    def test_only_earlier_same_user_same_domain_history_reaches_baseline(self):
        for index, accuracy in enumerate(("0.60", "0.70", "0.80")):
            prior = create_session(self.user, self.consent, self.assessment_type, f"PRIOR{index}", minutes_ago=30)
            create_result(prior, f"PRIOR{index}", accuracy=accuracy,
                          calculated_at=self.session.started_at - timezone.timedelta(minutes=10-index))
        other_session = create_session(self.other, self.other_consent, self.assessment_type, "OTHER")
        create_result(other_session, "OTHER", accuracy="0.01",
                      calculated_at=self.session.started_at - timezone.timedelta(minutes=1))
        other_type = AssessmentType.objects.create(
            assessment_type_id="ATATTENTION", assessment_name="Attention", cognitive_domain="attention", active=1)
        other_domain = create_session(self.user, self.consent, other_type, "DOMAIN")
        create_result(other_domain, "DOMAIN", accuracy="0.02",
                      calculated_at=self.session.started_at - timezone.timedelta(minutes=1))
        late = create_session(self.user, self.consent, self.assessment_type, "LATE")
        create_result(late, "LATE", accuracy="0.03", calculated_at=self.session.started_at)
        with patch("mindguard.services.build_insight", wraps=build_insight) as adapter:
            data = self.generate()
        record = adapter.call_args.args[0]
        self.assertEqual(record["current_performance"]["accuracy"], 0.85)
        self.assertEqual(record["baselines"]["per_domain"]["n_valid"], 3)
        self.assertAlmostEqual(record["baselines"]["per_domain"]["median"], 0.70)
        self.assertIn("85.0%", data["insight"]["text"])  # Internal output intentionally unchanged.
        self.assertIn("70.0%", data["insight"]["text"])
        self.assertFalse(data["delivery"]["clinical_claim"])
        self.assertFalse(data["delivery"]["automatic_alert"])

    def test_generation_is_read_only_and_deterministic(self):
        from intelligence.models import IntelligenceRun, Insight, Recommendation
        self.assertEqual(self.generate(), self.generate())
        self.assertFalse(IntelligenceRun.objects.exists())
        self.assertFalse(Insight.objects.exists())
        self.assertFalse(Recommendation.objects.exists())
        self.result.refresh_from_db()
        self.assertEqual(self.result.accuracy_rate, Decimal("0.85"))
