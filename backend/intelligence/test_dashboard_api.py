from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from intelligence.views import DemoStatusView, HomeDashboardView


class DashboardApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            first_name="Ada",
        )

    def test_dashboard_requires_authentication(self):
        request = self.factory.get("/api/v1/home")

        response = HomeDashboardView.as_view()(request)

        self.assertEqual(response.status_code, 401)

    def test_dashboard_returns_explicit_empty_states(self):
        request = self.factory.get("/api/v1/home")
        force_authenticate(request, user=self.user)

        with patch(
            "intelligence.views.MindGuardDataConsent.objects.filter"
        ) as consent_filter:
            consent_filter.return_value.exists.return_value = False
            response = HomeDashboardView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["first_name"], "Ada")
        self.assertEqual(response.data["pattern_state"], "no_data")
        self.assertEqual(response.data["change"]["state"], "no_data")
        self.assertEqual(response.data["insights"]["mindguard"]["count"], 0)
        self.assertFalse(response.data["insights"]["health_reserve"]["assessed"])
        self.assertIsNone(response.data["next_action"])
        self.assertIsNone(response.data["ring"])

    def test_dashboard_queries_only_the_authenticated_users_reflections(self):
        request = self.factory.get("/api/v1/home")
        force_authenticate(request, user=self.user)

        with patch(
            "intelligence.views.MindGuardDataConsent.objects.filter"
        ) as consent_filter, patch(
            "intelligence.views.MindGuardReflection.objects.filter"
        ) as reflection_filter:
            consent_filter.return_value.exists.return_value = True
            reflection_filter.return_value.count.return_value = 0
            response = HomeDashboardView.as_view()(request)

        reflection_filter.assert_called_once_with(user=self.user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["insights"]["mindguard"]["count"], 0)
        self.assertNotIn("recent", response.data["insights"]["mindguard"])

    def test_demo_status_requires_authentication(self):
        request = self.factory.get("/api/v1/demo/status")

        response = DemoStatusView.as_view()(request)

        self.assertEqual(response.status_code, 401)

    def test_demo_status_reports_no_active_demo(self):
        request = self.factory.get("/api/v1/demo/status")
        force_authenticate(request, user=self.user)

        response = DemoStatusView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"demo_mode": None, "demo_eligible": False})
