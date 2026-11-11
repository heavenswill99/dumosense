
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import F
from django.template.loader import render_to_string
from django.utils import timezone

from .models import WaitlistRegistration

logger = logging.getLogger(__name__)


def send_waitlist_confirmation(registration_id):
    registration = WaitlistRegistration.objects.get(
        pk=registration_id
    )

    if registration.confirmation_email_status == "sent":
        return True

    WaitlistRegistration.objects.filter(
        pk=registration_id
    ).update(
        confirmation_email_attempts=F(
            "confirmation_email_attempts"
        ) + 1
    )

    try:
        html_content = render_to_string(
            "waitlist/welcome_email.html",
            {
                "full_name": registration.full_name,
            },
        )

        plain_text = (
            f"Hello {registration.full_name},\n\n"
            "Thank you for joining the DumoSense early access waitlist!\n\n"
            "We're excited to have you with us. "
            "You'll receive updates as we prepare for launch.\n\n"
            "We'd also love to have you in our community! "
            "Join our Telegram group to stay connected "
            "and be part of the DumoSense journey.\n\n"
            "Join our Telegram community:\n"
            "https://t.me/+IDfUBKdB3utmMGY0\n\n"
            "Best regards,\n"
            "The DumoSense Team\n\n"
            "This is an automated email. Please do not reply."
        )

        email = EmailMultiAlternatives(
            subject="Welcome to the DumoSense Waitlist",
            body=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[registration.email],
        )

        email.attach_alternative(
            html_content,
            "text/html",
        )

        result = email.send(fail_silently=False)

        if result != 1:
            raise RuntimeError(
                "Email backend did not confirm submission."
            )

        WaitlistRegistration.objects.filter(
            pk=registration_id
        ).update(
            confirmation_email_status="sent",
            confirmation_email_sent_at=timezone.now(),
        )

        logger.info(
            "Waitlist confirmation sent for registration %s",
            registration_id,
        )

        return True

    except Exception:
        WaitlistRegistration.objects.filter(
            pk=registration_id
        ).update(
            confirmation_email_status="failed"
        )

        logger.exception(
            "Waitlist confirmation failed for registration %s",
            registration_id,
        )

        return False
