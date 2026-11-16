from types import SimpleNamespace

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from intelligence.views import AIChatView, AIExplainView


class AIChatApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
        )

    def request_as_user(self, request):
        force_authenticate(request, user=self.user)
        return request

    def test_guest_can_use_chat_for_general_guidance(self):
        request = self.factory.post(
            "/api/v1/ai/chat",
            {"message": "How does Dumosense handle privacy?"},
            format="json",
        )

        response = AIChatView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Dumosense backend", response.data["content"])

    def test_chat_answers_site_questions_without_accessing_personal_records(self):
        request = self.request_as_user(
            self.factory.post(
                "/api/v1/ai/chat",
                {"message": "How do I use the MindGuard check-in?"},
                format="json",
            )
        )

        response = AIChatView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], "assistant")
        self.assertIn("MindGuard", response.data["content"])
        self.assertEqual(response.data["grounded_on"], [])

    def test_chat_handles_medical_advice_requests_safely(self):
        request = self.request_as_user(
            self.factory.post(
                "/api/v1/ai/chat",
                {"message": "Can you diagnose my condition?"},
                format="json",
            )
        )

        response = AIChatView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("can't diagnose", response.data["content"])

    def test_chat_rejects_empty_messages(self):
        request = self.request_as_user(
            self.factory.post(
                "/api/v1/ai/chat",
                {"message": "   "},
                format="json",
            )
        )

        response = AIChatView.as_view()(request)

        self.assertEqual(response.status_code, 400)

    def test_context_explanation_does_not_claim_to_use_personal_data(self):
        request = self.request_as_user(
            self.factory.post(
                "/api/v1/ai/explain",
                {"ref": "mindguard_change"},
                format="json",
            )
        )

        response = AIExplainView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("No personal health data", response.data["sections"]["what_we_observed"])
