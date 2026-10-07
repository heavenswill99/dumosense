from django.db import transaction
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import HasRequiredConsent

from .models import Consent, ConsentHistory
from .serializers import ConsentSerializer, ConsentWithdrawalSerializer, ConsentGrantSerializer, ConsentCreateSerializer


class ConsentListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ConsentCreateSerializer
        return ConsentSerializer

    def get_queryset(self):
        return Consent.objects.filter(
            user=self.request.user
        ).order_by("granted_at")

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        consent_type = serializer.validated_data["consent_type"]
        purpose = serializer.validated_data["purpose"]
        consent_version = serializer.validated_data["consent_version"]
        reason = serializer.validated_data.get("reason", "")

        existing_consent = Consent.objects.filter(
            user=request.user,
            consent_type=consent_type,
        ).first()

        if existing_consent:
            return Response(
                {
                    "detail": (
                        "A consent record for this consent type already exists. "
                        "Use the grant or withdraw endpoint to change its status."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            granted_at = timezone.now()

            last_consent = Consent.objects.order_by(
                "-consent_id"
            ).first()

            if last_consent is None:
                consent_id = "CON00000001"
            else:
                next_number = int(
                    last_consent.consent_id.replace("CON", "")
                ) + 1
                consent_id = f"CON{next_number:08d}"

            consent = Consent.objects.create(
                consent_id=consent_id,
                user=request.user,
                consent_type=consent_type,
                purpose=purpose,
                consent_version=consent_version,
                status="granted",
                granted_at=granted_at,
                withdrawn_at=None,
            )

            last_history = ConsentHistory.objects.order_by(
                "-consent_history_id"
            ).first()

            if last_history is None:
                history_id = "CH00000001"
            else:
                next_history_number = int(
                    last_history.consent_history_id.replace("CH", "")
                ) + 1
                history_id = f"CH{next_history_number:08d}"

            ConsentHistory.objects.create(
                consent_history_id=history_id,
                consent=consent,
                user=request.user,
                previous_status=None,
                new_status="granted",
                changed_at=granted_at,
                reason=reason or None,
            )

        return Response(
            ConsentSerializer(consent).data,
            status=status.HTTP_201_CREATED,
        )


class ConsentWithdrawView(generics.GenericAPIView):
    serializer_class = ConsentWithdrawalSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, consent_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            consent = Consent.objects.get(
                consent_id=consent_id,
                user=request.user,
            )
        except Consent.DoesNotExist:
            return Response(
                {"detail": "Consent record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if consent.status == "withdrawn":
            return Response(
                {"detail": "Consent has already been withdrawn."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = serializer.validated_data.get("reason", "")

        with transaction.atomic():
            previous_status = consent.status

            consent.status = "withdrawn"
            consent.withdrawn_at = timezone.now()
            consent.save(
                update_fields=["status", "withdrawn_at"]
            )

            ConsentHistory.objects.create(
                consent_history_id=self._next_history_id(),
                consent=consent,
                user=request.user,
                previous_status=previous_status,
                new_status="withdrawn",
                changed_at=consent.withdrawn_at,
                reason=reason or None,
            )

        return Response(
            ConsentSerializer(consent).data,
            status=status.HTTP_200_OK,
        )

    def _next_history_id(self):
        last_history = ConsentHistory.objects.order_by(
            "-consent_history_id"
        ).first()

        if last_history is None:
            return "CH00000001"

        next_number = int(
            last_history.consent_history_id.replace("CH", "")
        ) + 1

        return f"CH{next_number:08d}"

class ConsentGrantView(generics.GenericAPIView):
    serializer_class = ConsentGrantSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, consent_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            consent = Consent.objects.get(
                consent_id=consent_id,
                user=request.user,
            )
        except Consent.DoesNotExist:
            return Response(
                {"detail": "Consent record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if consent.status == "granted":
            return Response(
                {"detail": "Consent is already granted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = serializer.validated_data.get("reason", "")

        with transaction.atomic():
            previous_status = consent.status
            changed_at = timezone.now()

            consent.status = "granted"
            consent.granted_at = changed_at
            consent.withdrawn_at = None
            consent.save(
                update_fields=[
                    "status",
                    "granted_at",
                    "withdrawn_at",
                ]
            )

            ConsentHistory.objects.create(
                consent_history_id=self._next_history_id(),
                consent=consent,
                user=request.user,
                previous_status=previous_status,
                new_status="granted",
                changed_at=changed_at,
                reason=reason or None,
            )

        return Response(
            ConsentSerializer(consent).data,
            status=status.HTTP_200_OK,
        )

    def _next_history_id(self):
        last_history = ConsentHistory.objects.order_by(
            "-consent_history_id"
        ).first()

        if last_history is None:
            return "CH00000001"

        next_number = int(
            last_history.consent_history_id.replace("CH", "")
        ) + 1

        return f"CH{next_number:08d}"

