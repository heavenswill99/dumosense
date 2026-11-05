"""Tests for MindGuard intelligence persistence."""

from hashlib import sha256

from django.test import SimpleTestCase
from intelligence.services import make_mindguard_insight_id


class MindGuardPersistenceTests(SimpleTestCase):

    def test_insight_id_is_deterministic_and_fits_database(self):
        run_id = "MG" + sha256(
            "SES00000001|STAT_ENGINE_MVP_1.0".encode()
        ).hexdigest()[:18]

        first = make_mindguard_insight_id(run_id)
        retry = make_mindguard_insight_id(run_id)

        self.assertEqual(first, retry)
        self.assertEqual(len(first), 20)
        self.assertTrue(first.startswith("INS"))

    def test_insight_id_rejects_invalid_run_ids(self):
        invalid_values = [None, "", 123, [], {}]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    make_mindguard_insight_id(value)

    def test_persistence_uses_atomic_transaction(self):
        """Persistence must save the run and insight atomically."""
        from unittest.mock import MagicMock, patch

        from intelligence.services import save_mindguard_insight

        run_id = "MG123456789012345678"
        user_id = "USR_TEST001"

        insight_data = {
            "traceability": {
                "run_id": run_id,
                "model_version": "STAT_ENGINE_MVP_1.0",
                "session_id": "SES00000001",
            },
            "product_code": "MINDGUARD",
            "insight": {
                "insight_type": "session_summary",
                "text": "Descriptive assessment summary.",
                "explanation": "Not a medical assessment.",
                "priority": "low",
            },
            "delivery": {
                "automatic_alert": False,
                "clinical_claim": False,
            },
        }

        mock_run = MagicMock()
        mock_run.user_id = user_id
        mock_run.product_code = "MINDGUARD"
        mock_run.model_or_rule_version = "STAT_ENGINE_MVP_1.0"

        mock_insight = MagicMock()
        mock_insight.run_id = run_id
        mock_insight.user_id = user_id

        with patch("django.db.transaction.atomic") as mock_atomic, \
            patch("intelligence.models.IntelligenceRun.objects.get_or_create") as mock_run_create, \
            patch("intelligence.models.Insight.objects.get_or_create") as mock_insight_create:

            mock_run_create.return_value = (mock_run, True)
            mock_insight_create.return_value = (mock_insight, True)

            result = save_mindguard_insight(
                user_id=user_id,
                insight_data=insight_data,
            )

            mock_atomic.assert_called_once_with()
            mock_run_create.assert_called_once()
            mock_insight_create.assert_called_once()

            self.assertIs(result, mock_insight)


from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone

from accounts.models import User
from intelligence.models import IntelligenceRun, Insight
from intelligence.services import save_mindguard_insight


from django.test import TestCase


class MindGuardDatabaseIntegrationTests(TestCase):
    """
    Real MySQL persistence tests using transactional isolation.

    Must run exclusively against test_dumosense_dev.
    """

    databases = {"default"}

    def setUp(self):
        super().setUp()

        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            active_db = cursor.fetchone()[0]

        if active_db != "test_dumosense_dev":
            raise RuntimeError(
                f"SAFETY STOP: Unexpected database {active_db}"
            )

        self.user = User(
            user_id="USR_MG_TEST001",
            first_name="MindGuard",
            last_name="Test",
            email="mindguard-test@example.invalid",
            account_status="active",
            is_active=True,
            is_staff=False,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        self.user.set_unusable_password()
        self.user.save()

        self.run_id = "MG123456789012345678"

        self.insight_data = {
            "product_code": "MINDGUARD",
            "traceability": {
                "run_id": self.run_id,
                "model_version": "STAT_ENGINE_MVP_1.0",
                "session_id": "SES00000001",
            },
            "insight": {
                "insight_type": "session_summary",
                "text": "Descriptive assessment summary.",
                "explanation": "Not a medical assessment.",
                "priority": "low",
            },
            "delivery": {
                "automatic_alert": False,
                "clinical_claim": False,
            },
        }

    def test_real_database_insert(self):
        insight = save_mindguard_insight(
            user_id=self.user.user_id,
            insight_data=self.insight_data,
        )

        self.assertEqual(
            IntelligenceRun.objects.filter(run_id=self.run_id).count(),
            1,
        )
        self.assertEqual(
            Insight.objects.filter(insight_id=insight.insight_id).count(),
            1,
        )
        self.assertEqual(insight.user_id, self.user.user_id)

    def test_idempotent_persistence(self):
        first = save_mindguard_insight(
            user_id=self.user.user_id,
            insight_data=self.insight_data,
        )
        second = save_mindguard_insight(
            user_id=self.user.user_id,
            insight_data=self.insight_data,
        )

        self.assertEqual(first.insight_id, second.insight_id)
        self.assertEqual(
            IntelligenceRun.objects.filter(run_id=self.run_id).count(),
            1,
        )
        self.assertEqual(
            Insight.objects.filter(run_id=self.run_id).count(),
            1,
        )

    def test_transaction_rolls_back_on_insight_failure(self):
        # Verify that the run does not already exist.
        self.assertFalse(
            IntelligenceRun.objects.filter(run_id=self.run_id).exists()
        )

        with patch(
            "intelligence.models.Insight.objects.get_or_create",
            side_effect=ValidationError("Simulated insight failure"),
        ):
            with self.assertRaises(ValidationError):
                save_mindguard_insight(
                    user_id=self.user.user_id,
                    insight_data=self.insight_data,
                )

        # The new run must have been rolled back.
        self.assertFalse(
            IntelligenceRun.objects.filter(run_id=self.run_id).exists()
        )
        self.assertFalse(
            Insight.objects.filter(run_id=self.run_id).exists()
        )