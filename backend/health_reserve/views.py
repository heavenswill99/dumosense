from uuid import uuid4

from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from consent.permissions import HasRequiredConsent

from .models import HealthReserveAssessment
from .serializers import (
    HealthReserveAssessmentSerializer,
    HealthReserveAssessmentCreateSerializer,
)
from .calculations import calculate_preparedness


# GET: Retrieve the logged-in user's assessment history
class HealthReserveAssessmentListView(generics.ListAPIView):
    serializer_class = HealthReserveAssessmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HealthReserveAssessment.objects.filter(
            user=self.request.user
        ).order_by("-assessed_at")


# POST: Submit a new Health Reserve assessment
class HealthReserveAssessmentCreateView(generics.GenericAPIView):
    serializer_class = HealthReserveAssessmentCreateSerializer

    permission_classes = [
        IsAuthenticated,
        HasRequiredConsent,
    ]

    required_consent_type = "health_reserve_data"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        calculations = calculate_preparedness(
            preparedness_target=data["preparedness_target"],
            available_amount=data["current_preparedness_amount"],
        )

        assessment = HealthReserveAssessment.objects.create(
            reserve_assessment_id=f"HRA{uuid4().hex[:16].upper()}",
            user=request.user,
            assessed_at=timezone.now(),
            healthcare_coverage_status=data["healthcare_coverage_status"],
            estimated_healthcare_exposure=data["estimated_healthcare_exposure"],
            emergency_health_resources=data["emergency_health_resources"],
            monthly_financial_obligations=data["monthly_financial_obligations"],
            number_of_dependants=data["number_of_dependants"],
            current_preparedness_amount=data["current_preparedness_amount"],
            preparedness_target=data["preparedness_target"],
            preparedness_gap=calculations["preparedness_gap"],
            preparedness_ratio=calculations["preparedness_ratio"],
            reserve_status=(
                "target_met"
                if calculations["preparedness_ratio"] >= 1
                else "below_target"
            ),
        )

        return Response(
            HealthReserveAssessmentSerializer(assessment).data,
            status=status.HTTP_201_CREATED,
        )