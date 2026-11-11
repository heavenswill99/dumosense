import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        api_key = getattr(settings, "RESEND_API_KEY", "")
        if not api_key:
            raise RuntimeError("RESEND_API_KEY is not configured.")

        from_name = getattr(settings, "WAITLIST_FROM_NAME", "DumoSense")
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "hello@dumosense.com")

        sent_count = 0
        for message in email_messages:
            payload = {
                "from": f"{from_name} <{from_email}>",
                "to": list(message.to),
                "subject": message.subject,
                "html": message.alternatives[0][0] if message.alternatives else message.body,
                "text": message.body,
            }
            if getattr(message, "cc", None):
                payload["cc"] = list(message.cc)
            if getattr(message, "bcc", None):
                payload["bcc"] = list(message.bcc)
            attachments = getattr(message, "resend_attachments", None)
            if attachments:
                payload["attachments"] = attachments
            idempotency_key = getattr(message, "resend_idempotency_key", None)

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            if idempotency_key:
                headers["Idempotency-Key"] = idempotency_key
            response = requests.post(
                "https://api.resend.com/emails",
                headers=headers,
                json=payload,
                timeout=20,
            )

            if not 200 <= response.status_code < 300:
                if self.fail_silently:
                    continue
                raise RuntimeError(f"Resend email failed: {response.status_code} {response.text}")

            sent_count += 1

        return sent_count
