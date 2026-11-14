"""Persistence tests on the disposable database, with complete current fixtures."""
from copy import deepcopy
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from config.mindguard_test_runner import MindGuardDatabaseTestCase
from intelligence.models import IntelligenceRun, Insight, Recommendation
from intelligence.services import make_mindguard_insight_id, save_mindguard_insight
from mindguard.test_support import create_user, insight_payload


class MindGuardPersistenceTests(SimpleTestCase):
    def test_insight_id_is_deterministic_and_fits_database(self):
        first = make_mindguard_insight_id("MG123456789012345678")
        self.assertEqual(first, make_mindguard_insight_id("MG123456789012345678"))
        self.assertEqual(len(first), 20)
        self.assertTrue(first.startswith("INS"))

    def test_insight_id_rejects_invalid_run_ids(self):
        for value in (None, "", 123, []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                make_mindguard_insight_id(value)


class MindGuardDatabaseIntegrationTests(MindGuardDatabaseTestCase):
    def setUp(self):
        self.user = create_user("PERSIST")
        self.data = insight_payload()

    def save(self, data=None, user=None):
        return save_mindguard_insight(user_id=(user or self.user).pk, insight_data=data or self.data)

    def test_real_insert_preserves_internal_numeric_content(self):
        saved = self.save()
        saved.refresh_from_db()
        self.assertEqual(saved.insight_text, self.data["insight"]["text"])
        self.assertEqual(saved.explanation_text, self.data["insight"]["explanation"])
        self.assertEqual(saved.recommendations.get().recommendation_text, self.data["recommendation"]["text"])
        self.assertEqual(IntelligenceRun.objects.count(), 1)
        self.assertEqual(Insight.objects.count(), 1)
        self.assertEqual(Recommendation.objects.count(), 1)

    def test_idempotent_persistence_includes_recommendations(self):
        first, second = self.save(), self.save()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(IntelligenceRun.objects.count(), 1)
        self.assertEqual(Insight.objects.count(), 1)
        self.assertEqual(Recommendation.objects.count(), 1)

    def test_transaction_rolls_back_on_insight_failure(self):
        with patch("intelligence.models.Insight.objects.get_or_create", side_effect=ValidationError("test")):
            with self.assertRaises(ValidationError):
                self.save()
        self.assertFalse(IntelligenceRun.objects.exists())
        self.assertFalse(Insight.objects.exists())
        self.assertFalse(Recommendation.objects.exists())

    def test_transaction_rolls_back_on_recommendation_failure(self):
        with patch("intelligence.models.Recommendation.objects.get_or_create", side_effect=ValidationError("test")):
            with self.assertRaises(ValidationError):
                self.save()
        self.assertFalse(IntelligenceRun.objects.exists())
        self.assertFalse(Insight.objects.exists())
        self.assertFalse(Recommendation.objects.exists())

    def test_same_run_with_changed_text_is_rejected_without_overwrite(self):
        first = self.save()
        changed = deepcopy(self.data)
        changed["insight"]["text"] = "Changed content"
        with self.assertRaises(ValidationError):
            self.save(changed)
        first.refresh_from_db()
        self.assertEqual(first.insight_text, self.data["insight"]["text"])
        self.assertEqual(Insight.objects.count(), 1)

    def test_cross_user_run_collision_is_rejected(self):
        self.save()
        with self.assertRaises(ValidationError):
            self.save(user=create_user("OTHER"))
        self.assertEqual(IntelligenceRun.objects.get().user_id, self.user.pk)

    def test_unsafe_delivery_and_missing_recommendations_are_rejected(self):
        for field in ("clinical_claim", "automatic_alert"):
            data = deepcopy(self.data)
            data["delivery"][field] = True
            with self.assertRaises(ValidationError):
                self.save(data)
        data = deepcopy(self.data)
        del data["recommendation"]
        with self.assertRaises(ValidationError):
            self.save(data)
        self.assertFalse(IntelligenceRun.objects.exists())
