"""No-database contract tests for the central ORM orchestration boundary."""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from intelligence.services import query_agent
from intelligence.gateway import require_access
from intelligence.views import query, insights, latest_insight
from intelligence.reads import read_insights


def mind_record():
    return {"user_id": "u", "run_id": None, "session_id": "s",
            "model_version": "MG_DB_DESCRIPTIVE_1.0",
            "index_time": "2026-01-10T12:00:00+00:00",
            "current_performance": {"accuracy": 0.8},
            "baselines": {"per_domain": {"n_valid": 0, "median": None,
                                          "ts_max_prior": None}}}


def reserve_record():
    return {"user_id": "u", "reserve_assessment_id": "h",
            "model_version": "HR_BUFFER_BASELINE_1.0",
            "assessed_at": "2026-01-10T12:00:00+00:00",
            "score": 6, "obligation_buffer_months": 3.0,
            "prior_assessment_count": 0, "prior_median_buffer_months": None,
            "delta_from_prior_median_months": None}


class CentralServiceTest(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(user_id="u")
        self.access = patch("intelligence.services.require_access", return_value={
            "consent_verified": True, "enrollment_verified": True})
        self.run_write = patch("intelligence.services.IntelligenceRun.objects.create")
        self.insight_write = patch("intelligence.services.Insight.objects.create")
        self.action_write = patch("intelligence.services.Recommendation.objects.create")
        self.event_write = patch("intelligence.services.Event.objects.create")

    def test_mindguard_queries_only_mindguard_and_persists_lineage(self):
        with self.access as access, self.run_write as runs, self.insight_write as insights, self.action_write as actions, self.event_write as events, patch("intelligence.services.READERS", {"MINDGUARD": lambda _: mind_record()}):
            out = query_agent.__wrapped__(user=self.user, question="my memory")
        self.assertEqual(out["status"], "deterministic")
        self.assertEqual(out["products"], ["MINDGUARD"])
        access.assert_called_once_with("u", "MINDGUARD")
        runs.assert_called_once(); insights.assert_called_once(); actions.assert_called_once(); events.assert_called_once()
        self.assertEqual(insights.call_args.kwargs["run_id"], runs.call_args.kwargs["run_id"])
        self.assertEqual(actions.call_args.kwargs["insight_id"], insights.call_args.kwargs["insight_id"])

    def test_combined_keeps_two_product_records(self):
        with self.access as access, self.run_write as runs, self.insight_write as insights, self.action_write as actions, self.event_write as events, patch("intelligence.services.READERS", {"MINDGUARD": lambda _: mind_record(),
                                                     "HEALTH_RESERVE": lambda _: reserve_record()}):
            out = query_agent.__wrapped__(user=self.user, question="overall")
        self.assertEqual(out["products"], ["MINDGUARD", "HEALTH_RESERVE"])
        self.assertEqual(access.call_count, 2)
        self.assertEqual(runs.call_count, 2)
        self.assertEqual(insights.call_count, 2)
        self.assertEqual(actions.call_count, 2)
        self.assertEqual(events.call_count, 2)

    def test_denied_access_never_reads_or_writes(self):
        with patch("intelligence.services.require_access", side_effect=PermissionError), self.run_write as runs, patch("intelligence.services.READERS") as readers:
            with self.assertRaises(PermissionError):
                query_agent.__wrapped__(user=self.user, question="my memory")
        readers["MINDGUARD"].assert_not_called()
        runs.assert_not_called()

    def test_missing_state_never_writes(self):
        with self.access, self.run_write as runs, patch("intelligence.services.READERS", {"MINDGUARD": lambda _: None}):
            out = query_agent.__wrapped__(user=self.user, question="my memory")
        self.assertEqual(out["status"], "insufficient_data")
        runs.assert_not_called()

    def test_emergency_bypasses_product_data(self):
        with patch("intelligence.services.require_access") as access, self.run_write as runs:
            out = query_agent.__wrapped__(user=self.user, question="I can't breathe")
        self.assertEqual(out["status"], "escalate")
        access.assert_not_called(); runs.assert_not_called()

    @override_settings(DUMOSENSE_ENABLE_LOCAL_MODEL=True)
    def test_local_model_is_opt_in_and_keeps_the_existing_policy_gate(self):
        model_output = {"text": "Review your recorded result.",
                        "action_class": "review_history", "evidence_ids": []}
        with self.access, self.run_write, self.insight_write, self.action_write, \
             self.event_write, patch("intelligence.services.READERS", \
                                    {"MINDGUARD": lambda _: mind_record()}), \
             patch("intelligence.services.OllamaExplanationModel") as model:
            model.return_value.generate.return_value = model_output
            out = query_agent.__wrapped__(user=self.user, question="my memory")
        self.assertEqual(out["status"], "generated")
        self.assertEqual(out["release_status"], "internal_validation_only")
        model.return_value.generate.assert_called_once()


@override_settings(DUMOSENSE_ENABLE_INTELLIGENCE_QUERY=True)
class QueryEndpointTest(SimpleTestCase):
    def test_endpoint_uses_authenticated_user_only(self):
        user = SimpleNamespace(user_id="u", is_authenticated=True)
        request = APIRequestFactory().post("/api/v1/intelligence/query/",
                                           {"question": "my memory", "user_id": "other",
                                            "consent_verified": True}, format="json")
        force_authenticate(request, user=user)
        with patch("intelligence.views.query_agent", return_value={"status": "deterministic", "response": "ok"}) as service:
            response = query(request)
        self.assertEqual(response.status_code, 200)
        self.assertIs(service.call_args.kwargs["user"], user)
        self.assertEqual(service.call_args.kwargs["question"], "my memory")

    @override_settings(DUMOSENSE_ENABLE_INTELLIGENCE_QUERY=False)
    def test_disabled_by_default(self):
        request = APIRequestFactory().post("/api/v1/intelligence/query/",
                                           {"question": "my memory"}, format="json")
        force_authenticate(request, user=SimpleNamespace(user_id="u", is_authenticated=True))
        self.assertEqual(query(request).status_code, 503)

    def test_unauthenticated_request_rejected(self):
        request = APIRequestFactory().post("/api/v1/intelligence/query/",
                                           {"question": "my memory"}, format="json")
        response = query(request)
        self.assertIn(response.status_code, (401, 403))


class AccessGatewayTest(SimpleTestCase):
    def test_requires_core_and_product_consent(self):
        with patch("intelligence.gateway.User.objects") as users, \
             patch("intelligence.gateway.ProductEnrollment.objects") as enrollments, \
             patch("intelligence.gateway.Consent.objects") as consents:
            users.select_for_update.return_value.filter.return_value.exists.return_value = True
            enrollments.select_for_update.return_value.filter.return_value.exists.return_value = True
            consents.select_for_update.return_value.filter.return_value.exists.return_value = True
            self.assertEqual(require_access("u", "HEALTH_RESERVE"),
                             {"consent_verified": True, "enrollment_verified": True})
        asked = [call.kwargs["consent_type"] for call in
                 consents.select_for_update.return_value.filter.call_args_list]
        self.assertEqual(asked, ["product_data_processing", "health_reserve_data"])

    def test_denies_missing_product_consent(self):
        with patch("intelligence.gateway.User.objects") as users, \
             patch("intelligence.gateway.ProductEnrollment.objects") as enrollments, \
             patch("intelligence.gateway.Consent.objects") as consents:
            users.select_for_update.return_value.filter.return_value.exists.return_value = True
            enrollments.select_for_update.return_value.filter.return_value.exists.return_value = True
            consents.select_for_update.return_value.filter.return_value.exists.side_effect = [True, False]
            with self.assertRaises(PermissionError):
                require_access("u", "MINDGUARD")


class InsightReadTest(SimpleTestCase):
    def test_specific_product_rechecks_access_and_scopes_user(self):
        user = SimpleNamespace(user_id="u")
        with patch("intelligence.reads.require_access", return_value={}) as access, \
             patch("intelligence.reads.Insight.objects") as objects:
            objects.select_related.return_value.filter.return_value.order_by.return_value.__getitem__.return_value = []
            result = read_insights.__wrapped__(user=user, product="MINDGUARD", limit=5)
        self.assertEqual(result, [])
        access.assert_called_once_with("u", "MINDGUARD")
        self.assertEqual(objects.select_related.return_value.filter.call_args.kwargs["user_id"], "u")
        self.assertEqual(objects.select_related.return_value.filter.call_args.kwargs["product_code__in"], ["MINDGUARD"])

    def test_denied_product_returns_no_rows(self):
        with patch("intelligence.reads.require_access", side_effect=PermissionError), \
             patch("intelligence.reads.Insight.objects") as objects:
            with self.assertRaises(PermissionError):
                read_insights.__wrapped__(user=SimpleNamespace(user_id="u"), product="HEALTH_RESERVE")
        objects.select_related.assert_not_called()

    @override_settings(DUMOSENSE_ENABLE_INTELLIGENCE_QUERY=True)
    def test_get_endpoint_uses_authenticated_user(self):
        user = SimpleNamespace(user_id="u", is_authenticated=True)
        request = APIRequestFactory().get("/api/v1/insights/?product=MINDGUARD&limit=5")
        force_authenticate(request, user=user)
        with patch("intelligence.views.read_insights", return_value=[]) as read:
            response = insights(request)
        self.assertEqual(response.status_code, 200)
        self.assertIs(read.call_args.kwargs["user"], user)
        self.assertEqual(read.call_args.kwargs["product"], "MINDGUARD")

    @override_settings(DUMOSENSE_ENABLE_INTELLIGENCE_QUERY=True)
    def test_latest_returns_none_when_no_insight(self):
        user = SimpleNamespace(user_id="u", is_authenticated=True)
        request = APIRequestFactory().get("/api/v1/insights/latest/")
        force_authenticate(request, user=user)
        with patch("intelligence.views.read_insights", return_value=[]):
            response = latest_insight(request)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["insight"])
