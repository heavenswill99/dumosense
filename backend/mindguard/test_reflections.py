from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from mindguard.models import MindGuardDataConsent, MindGuardReflection
from mindguard.serializers import WELLBEING_REFLECTION_QUESTIONS


class MindGuardReflectionApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            user_id="USRREFLECTION001",
            first_name="MindGuard",
            last_name="Tester",
            email="mindguard-reflection@example.invalid",
            password="StrongPassword123!",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.consent_url = reverse("mindguard-data-consent")
        self.reflection_url = reverse(
            "mindguard-reflection-create",
            kwargs={"reflection_type": "wellbeing_checkin"},
        )
        self.payload = {
            "answers": [
                {"question": question, "value": index}
                for index, question in enumerate(
                    WELLBEING_REFLECTION_QUESTIONS,
                    start=1,
                )
            ],
            "question_set_version": "v1",
            "timestamp": "2026-11-15T00:10:24.165Z",
        }

    def test_reflection_requires_explicit_consent(self):
        response = self.client.post(
            self.reflection_url,
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(MindGuardReflection.objects.count(), 0)

    def test_consent_and_reflection_are_persisted_for_the_user(self):
        consent = self.client.post(
            self.consent_url,
            {"accepted": True},
            format="json",
        )
        response = self.client.post(
            self.reflection_url,
            self.payload,
            format="json",
        )

        self.assertEqual(consent.status_code, 201)
        self.assertEqual(response.status_code, 201)
        reflection = MindGuardReflection.objects.get()
        self.assertEqual(reflection.user, self.user)
        self.assertEqual(reflection.answers, self.payload["answers"])
        self.assertEqual(reflection.question_set_version, "v1")
        self.assertNotIn("answers", response.data)
        self.assertTrue(
            MindGuardDataConsent.objects.filter(
                user=self.user,
                granted=True,
            ).exists()
        )
        dashboard = self.client.get(reverse("home-dashboard"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data["insights"]["mindguard"]["count"], 1)
        self.assertNotIn("recent", dashboard.data["insights"]["mindguard"])

    def test_reflection_rejects_unknown_questions(self):
        self.client.post(
            self.consent_url,
            {"accepted": True},
            format="json",
        )
        invalid_payload = {
            **self.payload,
            "answers": [
                {"question": "Unrecognized question", "value": 3},
                *self.payload["answers"][1:],
            ],
        }

        response = self.client.post(
            self.reflection_url,
            invalid_payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(MindGuardReflection.objects.count(), 0)
