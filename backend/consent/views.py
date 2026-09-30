from django.db import transaction
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Consent, ConsentHistory
from .serializers import ConsentSerializer, ConsentWithdrawalSerializer, ConsentGrantSerializer


class ConsentListView(generics.ListAPIView):
    serializer_class = ConsentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Consent.objects.filter(
            user=self.request.user
        ).order_by("granted_at")


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