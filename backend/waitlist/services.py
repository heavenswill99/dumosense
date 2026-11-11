import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import F
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
        result = send_mail(
            subject="Welcome to the DumoSense Waitlist!",
            message=(
                f"Hello {registration.full_name},\n\n"
                "Thank you for joining the DumoSense early access waitlist!\n\n"
                "We're excited to have you with us. "
                "You'll receive updates as we prepare for launch.\n\n"
                "Best regards,\n"
                "The DumoSense Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[registration.email],
            fail_silently=False,
        )

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