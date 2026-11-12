
"""Tests for MindGuard orchestration."""

from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from intelligence.orchestration import process_mindguard_assessment


class MindGuardOrchestrationTests(SimpleTestCase):

    def setUp(self):
        self.user = SimpleNamespace(pk="USR_TEST001")
        self.session_id = "SES00000001"

        self.insight_data = {
            "product_code": "MINDGUARD",
            "traceability": {
                "run_id": "MG123456789012345678",
                "session_id": self.session_id,
                "model_version": "STAT_ENGINE_MVP_1.0",
            },
            "insight": {
                "insight_type": "session_summary",
                "text": "Descriptive assessment summary.",
            },
            "delivery": {
                "automatic_alert": False,
                "clinical_claim": False,
            },
        }

    @patch("intelligence.orchestration.save_mindguard_insight")
    @patch("intelligence.orchestration.generate_mindguard_insight")
    def test_successful_orchestration(self, mock_generate, mock_save):
        mock_generate.return_value = self.insight_data
        mock_save.return_value = SimpleNamespace(insight_id="INS_TEST001")

        result = process_mindguard_assessment(
            user=self.user,
            session_id=self.session_id,
        )

        mock_generate.assert_called_once_with(
            user=self.user,
            session_id=self.session_id,
        )
        mock_save.assert_called_once_with(
            user_id=self.user.pk,
            insight_data=self.insight_data,
        )
        self.assertEqual(result.insight_id, "INS_TEST001")

    @patch("intelligence.orchestration.save_mindguard_insight")
    @patch("intelligence.orchestration.generate_mindguard_insight")
    def test_session_mismatch_rejected(self, mock_generate, mock_save):
        invalid = dict(self.insight_data)
        invalid["traceability"] = {
            **self.insight_data["traceability"],
            "session_id": "ANOTHER_SESSION",
        }
        mock_generate.return_value = invalid

        with self.assertRaises(ValidationError):
            process_mindguard_assessment(
                user=self.user,
                session_id=self.session_id,
            )

        mock_save.assert_not_called()

    @patch("intelligence.orchestration.save_mindguard_insight")
    @patch("intelligence.orchestration.generate_mindguard_insight")
    def test_invalid_product_rejected(self, mock_generate, mock_save):
        mock_generate.return_value = {
            **self.insight_data,
            "product_code": "OTHER_PRODUCT",
        }

        with self.assertRaises(ValidationError):
            process_mindguard_assessment(
                user=self.user,
                session_id=self.session_id,
            )

        mock_save.assert_not_called()
