
"""Real MindGuard end-to-end integration tests.

Uses the real local ML adapter and disposable SQLite persistence.
No ML or persistence mocks.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied
from config.mindguard_test_runner import MindGuardDatabaseTestCase
from django.utils import timezone

from accounts.models import User
from assessments.models import AssessmentSession, AssessmentType
from consent.models import Consent
from intelligence.models import IntelligenceRun, Insight
from intelligence.orchestration import process_mindguard_assessment
from mindguard.models import CognitiveResult


class MindGuardEndToEndTests(MindGuardDatabaseTestCase):
    databases = {"default"}

    def setUp(self):
        super().setUp()

        now = timezone.now()

        self.user = User(
            user_id="USR_MG_E2E001",
            first_name="MindGuard",
            last_name="Integration",
            email="mindguard-e2e@example.invalid",
            account_status="active",
            is_active=True,
            is_staff=False,
            created_at=now,
            updated_at=now,
        )
        self.user.set_unusable_password()
        self.user.save()

        self.assessment_type = AssessmentType.objects.create(
            assessment_type_id="AT_MG_E2E001",
            assessment_name="MindGuard Memory Test",
            cognitive_domain="memory",
            description="Synthetic integration assessment",
            active=1,
        )

        self.consent = Consent.objects.create(
            consent_id="CON_MG_E2E001",
            user=self.user,
            consent_type="cognitive_assessment",
            purpose="MindGuard cognitive assessment",
            consent_version=Decimal("1.0"),
            status="granted",
            granted_at=now,
        )

        self.session = AssessmentSession.objects.create(
            session_id="SES_MG_E2E001",
            user=self.user,
            assessment_type=self.assessment_type,
            started_at=now - timezone.timedelta(minutes=5),
            completed_at=now,
            session_status="completed",
            difficulty_level=1,
            device_type="web",
            consent=self.consent,
        )

        self.result = CognitiveResult.objects.create(
            cognitive_result_id="CR_MG_E2E001",
            session=self.session,
            user=self.user,
            assessment_type=self.assessment_type,
            total_trials=20,
            correct_responses=17,
            incorrect_responses=3,
            omissions=0,
            accuracy_rate=Decimal("0.85"),
            mean_reaction_time_ms=Decimal("650.0"),
            median_reaction_time_ms=Decimal("630.0"),
            reaction_time_variability_ms=Decimal("50.0"),
            completion_time_seconds=Decimal("120.0"),
            difficulty_level=1,
            calculated_at=now,
        )

    def test_real_local_ml_and_database_persistence(self):
        saved_insight = process_mindguard_assessment(
            user=self.user,
            session_id=self.session.session_id,
        )

        self.assertEqual(
            IntelligenceRun.objects.filter(
                run_id=saved_insight.run_id
            ).count(),
            1,
        )

        self.assertEqual(
            Insight.objects.filter(
                insight_id=saved_insight.insight_id
            ).count(),
            1,
        )

        self.assertEqual(saved_insight.user_id, self.user.pk)
        self.assertEqual(saved_insight.product_code, "MINDGUARD")

        run = IntelligenceRun.objects.get(
            run_id=saved_insight.run_id
        )

        self.assertEqual(run.run_status, "completed")
        self.assertEqual(run.user_id, self.user.pk)

    def test_repeated_processing_does_not_duplicate_records(self):
        first = process_mindguard_assessment(
            user=self.user,
            session_id=self.session.session_id,
        )

        second = process_mindguard_assessment(
            user=self.user,
            session_id=self.session.session_id,
        )

        self.assertEqual(first.insight_id, second.insight_id)

        self.assertEqual(
            IntelligenceRun.objects.filter(
                run_id=first.run_id
            ).count(),
            1,
        )

        self.assertEqual(
            Insight.objects.filter(
                run_id=first.run_id
            ).count(),
            1,
        )

    def test_revoked_consent_blocks_processing(self):
        self.consent.status = "withdrawn"
        self.consent.withdrawn_at = timezone.now()
        self.consent.save()

        with self.assertRaises(PermissionDenied):
            process_mindguard_assessment(
                user=self.user,
                session_id=self.session.session_id,
            )

        self.assertFalse(
            IntelligenceRun.objects.filter(
                user_id=self.user.pk,
                product_code="MINDGUARD",
            ).exists()
        )

        self.assertFalse(
            Insight.objects.filter(
                user_id=self.user.pk,
                product_code="MINDGUARD",
            ).exists()
        )


    def test_authenticated_http_request_runs_local_ml_and_persists(self):
        from django.urls import reverse
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.user)

        url = reverse(
            "mindguard-insight-generate",
            kwargs={"session_id": self.session.session_id},
        )

        response = client.post(url, {}, format="json")

        self.assertEqual(
            response.status_code,
            200,
            getattr(response, "data", None),
        )

        response_data = response.json()

        self.assertEqual(
            response_data["session_id"],
            self.session.session_id,
        )

        self.assertEqual(
            response_data["status"],
            "completed",
        )

        self.assertEqual(
            IntelligenceRun.objects.filter(
                user=self.user,
                product_code="MINDGUARD",
            ).count(),
            1,
        )

        self.assertEqual(
            Insight.objects.filter(
                user=self.user,
                product_code="MINDGUARD",
            ).count(),
            1,
        )
