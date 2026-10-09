
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
