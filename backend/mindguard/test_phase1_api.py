"""HTTP regressions for ownership, withdrawal and public/internal data separation."""
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from config.mindguard_test_runner import MindGuardDatabaseTestCase
from intelligence.models import IntelligenceRun, Insight, Recommendation
from intelligence.services import save_mindguard_insight
from mindguard.models import CognitiveResponse, CognitiveResult
from mindguard.presentation import PUBLIC_EXPLANATION, PUBLIC_RECOMMENDATION, PUBLIC_SUMMARIES
from mindguard.test_support import MindGuardFixtureMixin, insight_payload

RAW_FIELDS = {
    "total_trials", "correct_responses", "incorrect_responses", "omissions", "accuracy_rate",
    "mean_reaction_time_ms", "median_reaction_time_ms", "reaction_time_variability_ms",
    "completion_time_seconds", "difficulty_level", "baseline_difference", "previous_session_difference",
    "current_performance", "baselines", "accuracy", "z", "median", "n_valid",
}
RESULT_FIELDS = {
    "cognitive_result_id", "session_id", "assessment_type_id", "assessment_name", "cognitive_domain",
    "started_at", "completed_at", "calculated_at",
}


class MindGuardPhaseOneAPITests(MindGuardFixtureMixin, MindGuardDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse("mindguard-insight-list")
        self.generate_url = reverse("mindguard-insight-generate", kwargs={"session_id": self.session.pk})
        self.result_list_url = reverse("cognitive-result-list")
        self.result_url = reverse("cognitive-result-detail", kwargs={"cognitive_result_id": self.result.pk})
        self.complete_url = reverse("assessment-session-complete", kwargs={"session_id": self.session.pk})

    def save_insight(self):
        return save_mindguard_insight(user_id=self.user.pk, insight_data=insight_payload(session_id=self.session.pk))

    def assert_no_metrics(self, value):
        if isinstance(value, dict):
            self.assertFalse(RAW_FIELDS.intersection(value))
            for child in value.values():
                self.assert_no_metrics(child)
        elif isinstance(value, list):
            for child in value:
                self.assert_no_metrics(child)

    def assert_public_copy(self, item):
        self.assertEqual(item["text"], PUBLIC_SUMMARIES[item["insight_type"]])
        self.assertEqual(item["explanation"], PUBLIC_EXPLANATION)
        self.assertEqual(item["priority"], "low")
        for recommendation in item["recommendations"]:
            self.assertEqual(recommendation["text"], PUBLIC_RECOMMENDATION)
            self.assertEqual(recommendation["recommendation_type"], "maintain_monitoring")
            self.assertEqual(recommendation["priority"], "low")

    def test_anonymous_requests_cannot_read_or_process(self):
        self.client.force_authenticate(user=None)
        for method, url in (("get", self.list_url), ("get", self.result_list_url), ("get", self.result_url),
                            ("post", self.generate_url), ("post", self.complete_url)):
            with self.subTest(url=url):
                self.assertEqual(getattr(self.client, method)(url).status_code, 401)

    def test_current_consent_is_required_even_when_no_insights_exist(self):
        self.consent.status = "withdrawn"
        self.consent.save(update_fields=["status"])
        self.assertEqual(self.client.get(self.list_url).status_code, 403)

    def test_absent_consent_is_rejected(self):
        from mindguard.test_support import create_user
        self.client.force_authenticate(user=create_user("NOCONSENT"))
        self.assertEqual(self.client.get(self.list_url).status_code, 403)

    def test_protected_reads_are_not_cacheable_with_or_without_consent(self):
        self.save_insight()
        for expected in (200, 403):
            for url in (self.list_url, self.result_list_url, self.result_url):
                with self.subTest(url=url, expected=expected):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, expected)
                    self.assertIn("no-store", response["Cache-Control"])
                    self.assertIn("private", response["Cache-Control"])
            self.consent.status = "withdrawn"
            self.consent.save(update_fields=["status"])

    def test_withdrawal_via_api_blocks_existing_insights_and_results_and_generation(self):
        saved = self.save_insight()
        self.assertEqual(self.client.get(self.list_url).status_code, 200)
        response = self.client.post(f"/api/v1/consents/{self.consent.pk}/withdraw/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        for method, url in (("get", self.list_url), ("get", self.result_list_url), ("get", self.result_url),
                            ("post", self.generate_url), ("post", self.complete_url)):
            with self.subTest(url=url):
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, 403)
                self.assertNotIn(saved.insight_text, response.content.decode())
        saved.refresh_from_db()
        self.assertIn("85.0%", saved.insight_text)  # Withdrawal does not erase internal analytics.

    def test_wellbeing_consent_does_not_authorize_cognitive_insights(self):
        self.consent.consent_type = "wellbeing_data"
        self.consent.save(update_fields=["consent_type"])
        self.assertEqual(self.client.get(self.list_url).status_code, 403)

    def test_grant_restores_only_safe_own_insights(self):
        self.save_insight()
        self.client.post(f"/api/v1/consents/{self.consent.pk}/withdraw/", {}, format="json")
        self.assertEqual(self.client.get(self.list_url).status_code, 403)
        self.assertEqual(self.client.post(f"/api/v1/consents/{self.consent.pk}/grant/", {}, format="json").status_code, 200)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assert_public_copy(response.json()["results"][0])

    def test_insight_and_recommendation_ownership_and_product_filters(self):
        own = self.save_insight()
        other_data = insight_payload("MGOTHER123", "SESOTHER")
        other = save_mindguard_insight(user_id=self.other.pk, insight_data=other_data)
        Recommendation.objects.create(
            recommendation_id="RECWRONGUSER", insight=own, user=self.other, product_code="MINDGUARD",
            recommendation_type="maintain_monitoring", recommendation_text="Other user's score 99%",
            priority="low", created_at=timezone.now())
        Recommendation.objects.create(
            recommendation_id="RECWRONGPRODUCT", insight=own, user=self.user, product_code="HEALTH_RESERVE",
            recommendation_type="other", recommendation_text="Other product", priority="low", created_at=timezone.now())
        other.run.product_code = "HEALTH_RESERVE"
        other.run.save(update_fields=["product_code"])
        # An own row for another product must also be excluded.
        Insight.objects.create(insight_id="INSOTHERPRODUCT", run=other.run, user=self.user,
            product_code="HEALTH_RESERVE", insight_type="other", insight_text="private", generated_at=timezone.now())
        response = self.client.get(self.list_url).json()
        self.assertEqual(response["count"], 1)
        self.assertEqual(response["results"][0]["insight_id"], own.pk)
        self.assertEqual(len(response["results"][0]["recommendations"]), 1)
        self.client.force_authenticate(user=self.other)
        response = self.client.get(self.list_url).json()
        self.assertNotIn(own.pk, [item["insight_id"] for item in response["results"]])

    def test_legacy_free_text_is_never_forwarded_in_any_feedback_field(self):
        saved = self.save_insight()
        numeric_variants = (
            "Accuracy 85.0%; prior median 72%; z=1.25; 630ms.",
            "Your performance was eighty five percent; your prior baseline was seventy two percent.",
            "Current performance: ８５％. Historical baseline: ٧٢٪.",
        )
        for text in numeric_variants:
            with self.subTest(text=text):
                Insight.objects.filter(pk=saved.pk).update(insight_text=text, explanation_text=text,
                    insight_type=text[:100], severity_or_priority="85%")
                saved.recommendations.update(recommendation_text=text, recommendation_type=text[:100], priority="72%")
                response = self.client.get(self.list_url)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn(text, response.content.decode())
                self.assert_public_copy(response.json()["results"][0])
                self.assert_no_metrics(response.json())
                saved.refresh_from_db()
                self.assertEqual(saved.insight_text, text)
                self.assertEqual(saved.explanation_text, text)
                self.assertEqual(saved.recommendations.get().recommendation_text, text)

    def test_insufficient_history_uses_non_numeric_non_clinical_copy(self):
        saved = self.save_insight()
        saved.insight_type = "insufficient_data"
        saved.save(update_fields=["insight_type"])
        item = self.client.get(self.list_url).json()["results"][0]
        self.assert_public_copy(item)
        self.assertEqual(item["insight_type"], "insufficient_data")

    def test_result_list_and_detail_allowlist_metadata_and_preserve_all_metrics(self):
        before = CognitiveResult.objects.filter(pk=self.result.pk).values().get()
        for url in (self.result_list_url, self.result_url):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assert_no_metrics(body)
            item = body[0] if isinstance(body, list) else body
            self.assertEqual(set(item), RESULT_FIELDS)
        self.assertEqual(before, CognitiveResult.objects.filter(pk=self.result.pk).values().get())

    def test_other_users_result_detail_is_404_and_list_is_empty(self):
        self.client.force_authenticate(user=self.other)
        self.assertEqual(self.client.get(self.result_url).status_code, 404)
        self.assertEqual(self.client.get(self.result_list_url).json(), [])
        self.assertEqual(self.client.post(self.generate_url, {}, format="json").status_code, 403)
        self.assertEqual(self.client.post(self.complete_url, {}, format="json").status_code, 404)

    def test_completion_response_is_safe_while_calculated_metrics_are_persisted(self):
        self.result.delete()
        self.session.session_status = "started"
        self.session.completed_at = None
        self.session.save(update_fields=["session_status", "completed_at"])
        for index, (correct, omission, latency) in enumerate(((1, 0, "600"), (0, 0, "800"), (0, 1, "0"))):
            CognitiveResponse.objects.create(response_id=f"RSP{index}", session=self.session, task=self.task,
                trial_number=index+1, stimulus_type="symbol", response_type="choice", is_correct=correct,
                reaction_time_ms=Decimal(latency), omission=omission, recorded_at=timezone.now())
        response = self.client.post(self.complete_url, {}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assert_no_metrics(response.json())
        self.assertEqual(set(response.json()["cognitive_result"]), RESULT_FIELDS)
        result = CognitiveResult.objects.get(session=self.session)
        self.assertEqual(result.accuracy_rate, Decimal("0.333333"))
        self.assertEqual((result.total_trials, result.correct_responses, result.incorrect_responses, result.omissions), (3, 1, 1, 1))
        self.assertEqual(result.mean_reaction_time_ms, Decimal("700.00"))
        self.assertEqual(result.median_reaction_time_ms, Decimal("700.00"))
        self.assertEqual(result.reaction_time_variability_ms, Decimal("100.00"))
        self.assertEqual(result.baseline_difference, Decimal("0"))
        self.assertFalse(IntelligenceRun.objects.exists())  # Completion semantics unchanged.
        self.assertEqual(self.client.post(self.complete_url, {}, format="json").status_code, 400)
        self.assertEqual(CognitiveResult.objects.filter(session=self.session).count(), 1)

    def test_real_generation_retrieval_and_retry_keep_internal_output_unchanged(self):
        first = self.client.post(self.generate_url, {}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(set(first.json()), {"run_id", "insight_id", "session_id", "status"})
        self.assert_no_metrics(first.json())
        saved = Insight.objects.get(pk=first.json()["insight_id"])
        self.assertIn("85.0%", saved.insight_text)
        before = saved.insight_text
        response = self.client.get(self.list_url)
        self.assert_public_copy(response.json()["results"][0])
        self.assertNotIn("85.0%", response.content.decode())
        self.assertEqual(self.client.post(self.generate_url, {}, format="json").json(), first.json())
        self.assertEqual((IntelligenceRun.objects.count(), Insight.objects.count(), Recommendation.objects.count()), (1, 1, 1))
        saved.refresh_from_db()
        self.assertEqual(saved.insight_text, before)

    def test_pending_worker_payload_cannot_leak_numeric_output(self):
        with patch("mindguard.views.process_mindguard_assessment", return_value={
                "status": "inference_pending", "accuracy": 0.85, "text": "85%", "baselines": {"median": 0.72}}):
            response = self.client.post(self.generate_url, {}, format="json")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"session_id": self.session.pk, "status": "inference_pending"})

    def test_bearer_jwt_authentication_obeys_consent_withdrawal(self):
        self.save_insight()
        self.client.force_authenticate(user=None)
        access = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(self.client.get(self.list_url).status_code, 200)
        self.consent.status = "withdrawn"
        self.consent.save(update_fields=["status"])
        self.assertEqual(self.client.get(self.list_url).status_code, 403)

    def test_cookie_authenticated_retrieval_also_obeys_current_consent(self):
        self.save_insight()
        client = APIClient(enforce_csrf_checks=True)
        client.cookies["dumosense_access"] = str(RefreshToken.for_user(self.user).access_token)
        self.assertEqual(client.get(self.list_url).status_code, 200)
        self.consent.status = "withdrawn"
        self.consent.save(update_fields=["status"])
        self.assertEqual(client.get(self.list_url).status_code, 403)
