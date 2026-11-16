import logging

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        api_key = getattr(settings, "RESEND_API_KEY", "").strip()
        emails_enabled = getattr(settings, "WAITLIST_EMAILS_ENABLED", False)

        if not emails_enabled or not api_key:
            if self.fail_silently:
                return 0
            logger.warning(
                "Waitlist email delivery is disabled. Set WAITLIST_EMAILS_ENABLED=true and a valid RESEND_API_KEY to enable it."
            )
            return 0

        from_name = getattr(settings, "WAITLIST_FROM_NAME", "DumoSense")
        from_email = getattr(settings, "WAITLIST_FROM_EMAIL", "noreply@dumosense.com")

        sent_count = 0
        for message in email_messages:
            payload = {
                "from": message.from_email or f"{from_name} <{from_email}>",
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
            try:
                response = requests.post(
                    "https://api.resend.com/emails",
                    headers=headers,
                    json=payload,
                    timeout=20,
                )
            except requests.RequestException as exc:
                if self.fail_silently:
                    logger.warning("Resend email request failed for %s: %s", payload.get("to"), exc)
                    continue
                raise RuntimeError(f"Resend email request failed: {exc}")

            if response.status_code in (401, 403):
                logger.warning(
                    "Resend rejected the configured API key; waitlist emails are temporarily disabled."
                )
                if self.fail_silently:
                    return sent_count
                raise RuntimeError(
                    f"Resend email failed: {response.status_code} {response.text}"
                )

            if not 200 <= response.status_code < 300:
                if self.fail_silently:
                    logger.warning(
                        "Resend returned %s for %s: %s",
                        response.status_code,
                        payload.get("to"),
                        response.text,
                    )
                    continue
                raise RuntimeError(f"Resend email failed: {response.status_code} {response.text}")

            sent_count += 1

        return sent_count
