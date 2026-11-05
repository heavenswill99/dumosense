
from unittest.mock import patch

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.test import SimpleTestCase
from django.urls import reverse

from rest_framework.test import APIClient

from accounts.models import User


class MindGuardInsightAPITests(SimpleTestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse(
            "mindguard-insight-generate",
            kwargs={"session_id": "SES_MG_E2E001"},
        )

    def make_user(self):
        return User(
            user_id="USR_MG_API001",
            email="mindguard-api@example.invalid",
            is_active=True,
        )

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertIn(response.status_code, (401, 403))

    @patch("mindguard.views.process_mindguard_assessment")
    def test_authenticated_request_returns_insight(self, mock_process):
        user = self.make_user()
        self.client.force_authenticate(user=user)

        mock_process.return_value = type(
            "MockInsight",
            (),
            {
                "run_id": "MG123456789",
                "insight_id": "INS123456789",
            },
        )()

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["insight_id"],
            "INS123456789",
        )

        mock_process.assert_called_once_with(
            user=user,
            session_id="SES_MG_E2E001",
        )

    @patch("mindguard.views.process_mindguard_assessment")
    def test_unowned_assessment_is_rejected(self, mock_process):
        self.client.force_authenticate(user=self.make_user())
        mock_process.side_effect = PermissionDenied()

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, 403)

    @patch("mindguard.views.process_mindguard_assessment")
    def test_invalid_assessment_is_rejected(self, mock_process):
        self.client.force_authenticate(user=self.make_user())
        mock_process.side_effect = ValidationError(
            "Invalid assessment."
        )

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, 400)
