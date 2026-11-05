
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from .views import (
    CognitiveResponseCreateView,
    CognitiveResultListView,
    CognitiveResultDetailView,
    WellbeingCheckinCreateView,
    WellbeingCheckinListView,
    ContextRecordCreateView,
    ContextRecordListView,
)


class MindGuardSecurityTests(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    def test_cognitive_response_requires_authentication(self):
        request = self.factory.post(
            "/api/v1/mindguard/sessions/SES001/responses/",
            {},
            format="json",
        )

        response = CognitiveResponseCreateView.as_view()(
            request, session_id="SES001"
        )

        self.assertEqual(response.status_code, 401)

    def test_cognitive_results_require_authentication(self):
        request = self.factory.get(
            "/api/v1/mindguard/results/"
        )

        response = CognitiveResultListView.as_view()(request)

        self.assertEqual(response.status_code, 401)

    def test_cognitive_result_detail_requires_authentication(self):
        request = self.factory.get(
            "/api/v1/mindguard/results/RES001/"
        )

        response = CognitiveResultDetailView.as_view()(
            request, cognitive_result_id="RES001"
        )

        self.assertEqual(response.status_code, 401)

    def test_wellbeing_checkin_requires_authentication(self):
        request = self.factory.post(
            "/api/v1/mindguard/wellbeing/checkins/",
            {},
            format="json",
        )

        response = WellbeingCheckinCreateView.as_view()(request)

        self.assertEqual(response.status_code, 401)

    def test_wellbeing_history_requires_authentication(self):
        request = self.factory.get(
            "/api/v1/mindguard/wellbeing/history/"
        )

        response = WellbeingCheckinListView.as_view()(request)

        self.assertEqual(response.status_code, 401)

    def test_context_creation_requires_authentication(self):
        request = self.factory.post(
            "/api/v1/mindguard/context/",
            {},
            format="json",
        )

        response = ContextRecordCreateView.as_view()(request)

        self.assertEqual(response.status_code, 401)

    def test_context_history_requires_authentication(self):
        request = self.factory.get(
            "/api/v1/mindguard/context/history/"
        )

        response = ContextRecordListView.as_view()(request)

        self.assertEqual(response.status_code, 401)

    def test_cognitive_results_filtered_by_authenticated_user(self):
        user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            user_id="USR_TEST001",
        )

        request = self.factory.get(
            "/api/v1/mindguard/results/"
        )
        force_authenticate(request, user=user)

        with patch(
            "mindguard.views.HasRequiredConsent.has_permission",
            return_value=True,
        ), patch(
            "mindguard.views.CognitiveResult.objects.filter"
        ) as mock_filter:
            mock_filter.return_value.select_related.return_value.order_by.return_value = []

            response = CognitiveResultListView.as_view()(request)

        mock_filter.assert_called_once_with(user=user)
        self.assertEqual(response.status_code, 200)

    def test_wellbeing_history_filtered_by_authenticated_user(self):
        user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            user_id="USR_TEST001",
        )

        request = self.factory.get(
            "/api/v1/mindguard/wellbeing/history/"
        )
        force_authenticate(request, user=user)

        with patch(
            "mindguard.views.HasRequiredConsent.has_permission",
            return_value=True,
        ), patch(
            "mindguard.views.WellbeingCheckin.objects.filter"
        ) as mock_filter:
            mock_filter.return_value.order_by.return_value = []

            response = WellbeingCheckinListView.as_view()(request)

        mock_filter.assert_called_once_with(user=user)
        self.assertEqual(response.status_code, 200)


class MindGuardInsightServiceTests(SimpleTestCase):
    """Security and integration tests for insight generation."""

    def test_insight_generation_requires_authentication(self):
        from django.core.exceptions import PermissionDenied
        from .services import generate_mindguard_insight

        user = SimpleNamespace(is_authenticated=False)

        with patch(
            "mindguard.services.AssessmentSession.objects.filter"
        ) as mock_sessions, patch(
            "mindguard.services.subprocess.run"
        ) as mock_worker:
            with self.assertRaises(PermissionDenied):
                generate_mindguard_insight(
                    user=user,
                    session_id="SESSION004",
                )

        mock_sessions.assert_not_called()
        mock_worker.assert_not_called()

    def test_insight_generation_rejects_unowned_assessment(self):
        from django.core.exceptions import PermissionDenied
        from .services import generate_mindguard_insight

        user = SimpleNamespace(
            is_authenticated=True,
            pk="USR_TEST001",
        )

        with patch(
            "mindguard.services.AssessmentSession.objects.filter"
        ) as mock_sessions, patch(
            "mindguard.services.Consent.objects.filter"
        ) as mock_consent, patch(
            "mindguard.services.subprocess.run"
        ) as mock_worker:
            mock_sessions.return_value.first.return_value = None

            with self.assertRaises(PermissionDenied):
                generate_mindguard_insight(
                    user=user,
                    session_id="SESSION_OTHER_USER",
                )

        mock_sessions.assert_called_once_with(
            session_id="SESSION_OTHER_USER",
            user=user,
            session_status="completed",
        )
        mock_consent.assert_not_called()
        mock_worker.assert_not_called()

    def test_insight_generation_requires_consent(self):
        from django.core.exceptions import PermissionDenied
        from .services import generate_mindguard_insight

        user = SimpleNamespace(
            is_authenticated=True,
            pk="USR_TEST001",
        )

        session = SimpleNamespace(
            session_id="SESSION004",
        )

        with patch(
            "mindguard.services.AssessmentSession.objects.filter"
        ) as mock_sessions, patch(
            "mindguard.services.Consent.objects.filter"
        ) as mock_consent, patch(
            "mindguard.services.CognitiveResult.objects.filter"
        ) as mock_results, patch(
            "mindguard.services.subprocess.run"
        ) as mock_worker:

            mock_sessions.return_value.first.return_value = session
            mock_consent.return_value.exists.return_value = False

            with self.assertRaises(PermissionDenied):
                generate_mindguard_insight(
                    user=user,
                    session_id="SESSION004",
                )

        mock_consent.assert_called_once_with(
            user=user,
            consent_type="cognitive_assessment",
            status="granted",
        )

        mock_results.assert_not_called()
        mock_worker.assert_not_called()

    def test_historical_assessments_are_filtered_correctly(self):
        from datetime import datetime, timezone
        from django.core.exceptions import ValidationError
        from .services import generate_mindguard_insight

        user = SimpleNamespace(
            is_authenticated=True,
            pk="USR_TEST001",
        )

        started_at = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)

        session = SimpleNamespace(
            session_id="SESSION004",
            started_at=started_at,
            assessment_type=SimpleNamespace(cognitive_domain="memory"),
        )

        result = SimpleNamespace(
            accuracy_rate=0.85,
            calculated_at=datetime(
                2026, 10, 24, 10, 30, tzinfo=timezone.utc
            ),
        )

        with patch(
            "mindguard.services.AssessmentSession.objects.filter"
        ) as mock_sessions, patch(
            "mindguard.services.Consent.objects.filter"
        ) as mock_consent, patch(
            "mindguard.services.CognitiveResult.objects.filter"
        ) as mock_results, patch(
            "mindguard.services.ML_PYTHON"
        ) as mock_python, patch(
            "mindguard.services.ML_WORKER"
        ) as mock_worker_path, patch(
            "mindguard.services.subprocess.run"
        ) as mock_worker:

            mock_sessions.return_value.first.return_value = session
            mock_consent.return_value.exists.return_value = True
            mock_results.return_value.first.return_value = result
            mock_results.return_value.exclude.return_value.order_by.return_value.values.return_value = []

            mock_python.is_file.return_value = True
            mock_worker_path.is_file.return_value = True
            mock_worker.return_value = SimpleNamespace(
                returncode=1,
                stdout="",
            )

            with self.assertRaises(ValidationError):
                generate_mindguard_insight(
                    user=user,
                    session_id="SESSION004",
                )

        history_call = mock_results.call_args_list[1]

        self.assertEqual(
            history_call.kwargs["assessment_type__cognitive_domain"],
            "memory",
        )
        self.assertEqual(
            history_call.kwargs["calculated_at__lt"],
            started_at,
        )
        self.assertEqual(
            history_call.kwargs["session__session_status"],
            "completed",
        )
        self.assertEqual(history_call.kwargs["user"], user)
        self.assertFalse(
            history_call.kwargs["accuracy_rate__isnull"]
        )

    def test_ml_worker_receives_correct_assessment_payload(self):
        import json
        from datetime import datetime, timezone
        from .services import generate_mindguard_insight

        user = SimpleNamespace(
            is_authenticated=True,
            pk="USR_TEST001",
        )

        started_at = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)
        calculated_at = datetime(2026, 10, 24, 10, 30, tzinfo=timezone.utc)
        previous_at = datetime(2026, 10, 20, 9, 0, tzinfo=timezone.utc)

        session = SimpleNamespace(
            session_id="SESSION004",
            started_at=started_at,
            assessment_type=SimpleNamespace(cognitive_domain="memory"),
        )

        result = SimpleNamespace(
            accuracy_rate=0.85,
            calculated_at=calculated_at,
        )

        expected_insight = {
            "delivery": {
                "automatic_alert": False,
                "clinical_claim": False,
            },
            "summary": "Descriptive cognitive performance insight",
        }

        with patch(
            "mindguard.services.AssessmentSession.objects.filter"
        ) as mock_sessions, patch(
            "mindguard.services.Consent.objects.filter"
        ) as mock_consent, patch(
            "mindguard.services.CognitiveResult.objects.filter"
        ) as mock_results, patch(
            "mindguard.services.ML_PYTHON"
        ) as mock_python, patch(
            "mindguard.services.ML_WORKER"
        ) as mock_worker_path, patch(
            "mindguard.services.subprocess.run"
        ) as mock_worker:

            mock_sessions.return_value.first.return_value = session
            mock_consent.return_value.exists.return_value = True
            mock_results.return_value.first.return_value = result

            mock_results.return_value.exclude.return_value.order_by.return_value.values.return_value = [
                {
                    "accuracy_rate": 0.75,
                    "calculated_at": previous_at,
                }
            ]

            mock_python.is_file.return_value = True
            mock_worker_path.is_file.return_value = True

            mock_worker.return_value = SimpleNamespace(
                returncode=0,
                stdout=json.dumps({
                    "success": True,
                    "result": expected_insight,
                }),
            )

            insight = generate_mindguard_insight(
                user=user,
                session_id="SESSION004",
            )

        payload = json.loads(mock_worker.call_args.kwargs["input"])

        self.assertEqual(payload["authenticated_user_id"], "USR_TEST001")
        self.assertTrue(payload["consent_verified"])
        self.assertEqual(payload["record"]["session_id"], "SESSION004")
        self.assertEqual(
            payload["record"]["current_performance"]["accuracy"],
            0.85,
        )
        self.assertEqual(
            payload["record"]["baseline_cutoff"],
            started_at.isoformat(),
        )
        self.assertEqual(
            payload["history"],
            [{
                "accuracy": 0.75,
                "calculated_at": previous_at.isoformat(),
            }],
        )
        self.assertEqual(insight, expected_insight)
        self.assertEqual(mock_worker.call_args.kwargs["timeout"], 30)

    def test_ml_worker_timeout_is_handled_safely(self):
        import subprocess
        from datetime import datetime, timezone
        from django.core.exceptions import ValidationError
        from .services import generate_mindguard_insight

        user = SimpleNamespace(
            is_authenticated=True,
            pk="USR_TEST001",
        )

        session = SimpleNamespace(
            session_id="SESSION004",
            started_at=datetime(
                2026, 10, 24, 10, 0, tzinfo=timezone.utc
            ),
            assessment_type=SimpleNamespace(cognitive_domain="memory"),
        )

        result = SimpleNamespace(
            accuracy_rate=0.85,
            calculated_at=datetime(
                2026, 10, 24, 10, 30, tzinfo=timezone.utc
            ),
        )

        with patch(
            "mindguard.services.AssessmentSession.objects.filter"
        ) as mock_sessions, patch(
            "mindguard.services.Consent.objects.filter"
        ) as mock_consent, patch(
            "mindguard.services.CognitiveResult.objects.filter"
        ) as mock_results, patch(
            "mindguard.services.ML_PYTHON"
        ) as mock_python, patch(
            "mindguard.services.ML_WORKER"
        ) as mock_worker_path, patch(
            "mindguard.services.subprocess.run"
        ) as mock_worker:

            mock_sessions.return_value.first.return_value = session
            mock_consent.return_value.exists.return_value = True
            mock_results.return_value.first.return_value = result
            mock_results.return_value.exclude.return_value.order_by.return_value.values.return_value = []

            mock_python.is_file.return_value = True
            mock_worker_path.is_file.return_value = True

            mock_worker.side_effect = subprocess.TimeoutExpired(
                cmd="mindguard_worker",
                timeout=30,
            )

            with self.assertRaisesMessage(
                ValidationError,
                "MindGuard ML worker could not complete.",
            ):
                generate_mindguard_insight(
                    user=user,
                    session_id="SESSION004",
                )

        mock_worker.assert_called_once()
        self.assertEqual(
            mock_worker.call_args.kwargs["timeout"],
            30,
        )

    def test_unsafe_ml_insight_is_rejected(self):
        import json
        from datetime import datetime, timezone
        from django.core.exceptions import ValidationError
        from .services import generate_mindguard_insight

        user = SimpleNamespace(
            is_authenticated=True,
            pk="USR_TEST001",
        )

        session = SimpleNamespace(
            session_id="SESSION004",
            started_at=datetime(
                2026, 10, 24, 10, 0, tzinfo=timezone.utc
            ),
            assessment_type=SimpleNamespace(cognitive_domain="memory"),
        )

        result = SimpleNamespace(
            accuracy_rate=0.85,
            calculated_at=datetime(
                2026, 10, 24, 10, 30, tzinfo=timezone.utc
            ),
        )

        with patch(
            "mindguard.services.AssessmentSession.objects.filter"
        ) as mock_sessions, patch(
            "mindguard.services.Consent.objects.filter"
        ) as mock_consent, patch(
            "mindguard.services.CognitiveResult.objects.filter"
        ) as mock_results, patch(
            "mindguard.services.ML_PYTHON"
        ) as mock_python, patch(
            "mindguard.services.ML_WORKER"
        ) as mock_worker_path, patch(
            "mindguard.services.subprocess.run"
        ) as mock_worker:

            mock_sessions.return_value.first.return_value = session
            mock_consent.return_value.exists.return_value = True
            mock_results.return_value.first.return_value = result
            mock_results.return_value.exclude.return_value.order_by.return_value.values.return_value = []

            mock_python.is_file.return_value = True
            mock_worker_path.is_file.return_value = True

            mock_worker.return_value = SimpleNamespace(
                returncode=0,
                stdout=json.dumps({
                    "success": True,
                    "result": {
                        "delivery": {
                            "automatic_alert": True,
                            "clinical_claim": False,
                        },
                        "summary": "Unsafe automatic alert",
                    },
                }),
            )

            with self.assertRaisesMessage(
                ValidationError,
                "Unsafe MindGuard insight response.",
            ):
                generate_mindguard_insight(
                    user=user,
                    session_id="SESSION004",
                )

        mock_worker.assert_called_once()

    def test_clinical_ml_claim_is_rejected(self):
        import json
        from datetime import datetime, timezone
        from django.core.exceptions import ValidationError
        from .services import generate_mindguard_insight

        user = SimpleNamespace(
            is_authenticated=True,
            pk="USR_TEST001",
        )

        session = SimpleNamespace(
            session_id="SESSION004",
            started_at=datetime(
                2026, 10, 24, 10, 0, tzinfo=timezone.utc
            ),
            assessment_type=SimpleNamespace(cognitive_domain="memory"),
        )

        result = SimpleNamespace(
            accuracy_rate=0.85,
            calculated_at=datetime(
                2026, 10, 24, 10, 30, tzinfo=timezone.utc
            ),
        )

        with patch(
            "mindguard.services.AssessmentSession.objects.filter"
        ) as mock_sessions, patch(
            "mindguard.services.Consent.objects.filter"
        ) as mock_consent, patch(
            "mindguard.services.CognitiveResult.objects.filter"
        ) as mock_results, patch(
            "mindguard.services.ML_PYTHON"
        ) as mock_python, patch(
            "mindguard.services.ML_WORKER"
        ) as mock_worker_path, patch(
            "mindguard.services.subprocess.run"
        ) as mock_worker:

            mock_sessions.return_value.first.return_value = session
            mock_consent.return_value.exists.return_value = True
            mock_results.return_value.first.return_value = result
            mock_results.return_value.exclude.return_value.order_by.return_value.values.return_value = []

            mock_python.is_file.return_value = True
            mock_worker_path.is_file.return_value = True

            mock_worker.return_value = SimpleNamespace(
                returncode=0,
                stdout=json.dumps({
                    "success": True,
                    "result": {
                        "delivery": {
                            "automatic_alert": False,
                            "clinical_claim": True,
                        },
                        "summary": "Unsafe clinical claim",
                    },
                }),
            )

            with self.assertRaisesMessage(
                ValidationError,
                "Unsafe MindGuard insight response.",
            ):
                generate_mindguard_insight(
                    user=user,
                    session_id="SESSION004",
                )

        mock_worker.assert_called_once()


    def test_invalid_assessment_accuracy_is_rejected(self):
        from django.core.exceptions import ValidationError
        from .services import generate_mindguard_insight

        user = SimpleNamespace(
            is_authenticated=True,
            pk="USR_TEST001",
        )

        session = SimpleNamespace(session_id="SESSION004")
        result = SimpleNamespace(accuracy_rate=85.0)

        with patch(
            "mindguard.services.AssessmentSession.objects.filter"
        ) as mock_sessions, patch(
            "mindguard.services.Consent.objects.filter"
        ) as mock_consent, patch(
            "mindguard.services.CognitiveResult.objects.filter"
        ) as mock_results, patch(
            "mindguard.services.subprocess.run"
        ) as mock_worker:

            mock_sessions.return_value.first.return_value = session
            mock_consent.return_value.exists.return_value = True
            mock_results.return_value.first.return_value = result

            with self.assertRaisesMessage(
                ValidationError,
                "Invalid assessment accuracy.",
            ):
                generate_mindguard_insight(
                    user=user,
                    session_id="SESSION004",
                )

        mock_worker.assert_not_called()
