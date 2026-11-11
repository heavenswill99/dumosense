import logging

from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import WaitlistRegistration
from .serializers import WaitlistRegistrationSerializer
from .services import send_waitlist_confirmation


logger = logging.getLogger(__name__)


class WaitlistRegistrationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "waitlist"

    def post(self, request, *args, **kwargs):
        serializer = WaitlistRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            if WaitlistRegistration.objects.filter(
                email__iexact=email
            ).exists():
                return Response(
                    {
                        "message": (
                            "This email address is already "
                            "registered for early access."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            with transaction.atomic():
                registration = serializer.save(
                    consent_timestamp=timezone.now(),
                    consent_policy_version="v1",
                )

                registration_id = registration.pk

                transaction.on_commit(
                    lambda: send_waitlist_confirmation(registration_id),
                    robust=True,
                )

        except IntegrityError:
            return Response(
                {
                    "message": (
                        "This email address is already "
                        "registered for early access."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        except DatabaseError:
            logger.exception("Waitlist registration could not be saved.")
            return Response(
                {
                    "message": (
                        "The registration service is temporarily unavailable. "
                        "Please try again."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except Exception:
            logger.exception("Unexpected error during waitlist registration.")
            raise

        return Response(
            {
                "message": "Your DumoSense waitlist registration has been saved.",
                "confirmation_email_status": "processing",
            },
            status=status.HTTP_201_CREATED,
        )