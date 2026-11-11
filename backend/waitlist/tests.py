
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from waitlist.models import WaitlistRegistration


class WaitlistRegistrationTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("waitlist-register")
        self.payload = {
            "full_name": "Test User",
            "email": "waitlist-test@example.com",
            "product_interest": "both",
            "consent_accepted": True,
        }

    def test_successful_registration(self):
        response = self.client.post(
            self.url, self.payload, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            WaitlistRegistration.objects.filter(
                email=self.payload["email"]
            ).exists()
        )

    def test_consent_is_required(self):
        payload = self.payload.copy()
        payload["consent_accepted"] = False

        response = self.client.post(
            self.url, payload, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            WaitlistRegistration.objects.count(), 0
        )

    def test_duplicate_email_is_rejected(self):
        first = self.client.post(
            self.url, self.payload, format="json"
        )
        self.assertEqual(first.status_code, 201, first.data)

        second = self.client.post(
            self.url, self.payload, format="json"
        )
        self.assertEqual(second.status_code, 400)
        self.assertEqual(
            WaitlistRegistration.objects.count(), 1
        )

    def test_product_interest_is_saved(self):
        response = self.client.post(
            self.url, self.payload, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)

        registration = WaitlistRegistration.objects.get(
            email=self.payload["email"]
        )
        self.assertEqual(registration.product_interest, "both")

from django.core import mail
from django.core.management import call_command
from django.test import override_settings


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
)
class WaitlistEmailTests(TestCase):

    def test_confirmation_email_is_sent(self):
        registration = WaitlistRegistration.objects.create(
            full_name="Email Test User",
            email="email-test@example.com",
            product_interest="both",
            consent_accepted=True,
        )

        call_command("send_waitlist_confirmations")

        registration.refresh_from_db()

        self.assertEqual(
            registration.confirmation_email_status,
            "sent"
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(
            registration.email,
            mail.outbox[0].to
        )