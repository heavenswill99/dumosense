import logging
import time
from datetime import timedelta

from django.core.mail import get_connection
from django.core.management.base import BaseCommand
from django.db import DatabaseError, transaction
from django.db.models import Q
from django.utils import timezone

from waitlist.emails import build_confirmation_email
from waitlist.models import WaitlistRegistration

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
RETRY_DELAY = timedelta(minutes=5)
STALE_SENDING_DELAY = timedelta(minutes=15)


class Command(BaseCommand):
    help = "Send pending DumoSense waitlist confirmation emails through Resend."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=25)
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--interval", type=int, default=10)

    def handle(self, *args, **options):
        limit = options["limit"]
        interval = options["interval"]
        if limit < 1:
            raise ValueError("--limit must be greater than zero.")
        if interval < 1:
            raise ValueError("--interval must be greater than zero.")

        while True:
            self.process_pending(limit)
            if not options["watch"]:
                return
            time.sleep(interval)

    def process_pending(self, limit):
        now = timezone.now()
        retry_before = now - RETRY_DELAY
        stale_before = now - STALE_SENDING_DELAY
        eligible = (
            Q(confirmation_email_status="pending")
            | Q(
                confirmation_email_status="failed",
                confirmation_email_attempts__lt=MAX_ATTEMPTS,
                updated_at__lte=retry_before,
            )
            | Q(
                confirmation_email_status="sending",
                updated_at__lte=stale_before,
                confirmation_email_attempts__lt=MAX_ATTEMPTS,
            )
        )

        try:
            with transaction.atomic():
                registrations = list(
                    WaitlistRegistration.objects.select_for_update()
                    .filter(eligible)
                    .order_by("created_at")[:limit]
                )
                for registration in registrations:
                    registration.confirmation_email_status = "sending"
                    registration.confirmation_email_attempts += 1
                    registration.save(
                        update_fields=[
                            "confirmation_email_status",
                            "confirmation_email_attempts",
                            "updated_at",
                        ]
                    )
        except DatabaseError:
            logger.exception("Could not claim pending waitlist confirmation emails.")
            raise

        sent = 0
        failed = 0
        for registration in registrations:
            try:
                message = build_confirmation_email(registration)
                if get_connection().send_messages([message]) != 1:
                    raise RuntimeError("Resend did not accept the confirmation email.")
            except Exception:
                failed += 1
                logger.exception(
                    "Waitlist confirmation email attempt %s failed for registration id=%s.",
                    registration.confirmation_email_attempts,
                    registration.pk,
                )
                registration.confirmation_email_status = "failed"
                try:
                    registration.save(
                        update_fields=["confirmation_email_status", "updated_at"]
                    )
                except DatabaseError:
                    logger.exception(
                        "Could not record email failure for registration id=%s.",
                        registration.pk,
                    )
            else:
                sent += 1
                registration.confirmation_email_status = "sent"
                registration.confirmation_email_sent_at = timezone.now()
                try:
                    registration.save(
                        update_fields=[
                            "confirmation_email_status",
                            "confirmation_email_sent_at",
                            "updated_at",
                        ]
                    )
                except DatabaseError:
                    logger.exception(
                        "Resend accepted email, but its status could not be saved for registration id=%s.",
                        registration.pk,
                    )

        if registrations:
            self.stdout.write(
                f"Processed {len(registrations)} waitlist email(s): "
                f"{sent} sent, {failed} failed."
            )
