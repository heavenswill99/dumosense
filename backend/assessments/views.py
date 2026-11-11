from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import uuid

from consent.models import Consent
from consent.permissions import HasRequiredConsent

from .models import AssessmentSession
from .serializers import (
    AssessmentSessionCreateSerializer,
    AssessmentSessionSerializer,
)
import statistics
from decimal import Decimal, ROUND_HALF_UP

from mindguard.models import CognitiveResponse, CognitiveResult
from mindguard.serializers import CognitiveResultSerializer


class AssessmentSessionCreateView(generics.GenericAPIView):
    serializer_class = AssessmentSessionCreateSerializer
    permission_classes = [
        IsAuthenticated,
        HasRequiredConsent,
    ]
    required_consent_type = "cognitive_assessment"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assessment_type = serializer.validated_data["assessment_type_id"]
        difficulty_level = serializer.validated_data["difficulty_level"]
        device_type = serializer.validated_data.get("device_type")

        consent = (
            Consent.objects.filter(
                user=request.user,
                consent_type="cognitive_assessment",
                status="granted",
            )
            .order_by("-granted_at")
            .first()
        )

        if consent is None:
            return Response(
                {"detail": "Required consent has not been granted."},
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            session_id = f"SES{uuid.uuid4().hex[:16].upper()}"
           
            session = AssessmentSession.objects.create(
                session_id=session_id,
                user=request.user,
                assessment_type=assessment_type,
                started_at=timezone.now(),
                completed_at=None,
                session_status="started",
                difficulty_level=difficulty_level,
                device_type=device_type,
                consent=consent,
            )

        return Response(
            AssessmentSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )



class AssessmentSessionCompleteView(generics.GenericAPIView):
    permission_classes = [
        IsAuthenticated,
        HasRequiredConsent,
    ]
    required_consent_type = "cognitive_assessment"

    def post(self, request, session_id):
        with transaction.atomic():
            try:
                session = (
                    AssessmentSession.objects
                    .select_for_update()
                    .select_related("assessment_type")
                    .get(
                        session_id=session_id,
                        user=request.user,
                    )
                )
            except AssessmentSession.DoesNotExist:
                return Response(
                    {"detail": "Assessment session not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if session.session_status != "started":
                return Response(
                    {
                        "detail": (
                            "Only a started assessment session "
                            "can be completed."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if CognitiveResult.objects.filter(
                session=session
            ).exists():
                return Response(
                    {
                        "detail": (
                            "A cognitive result already exists "
                            "for this session."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            responses = list(
                CognitiveResponse.objects.filter(
                    session=session
                ).order_by("trial_number")
            )

            if not responses:
                return Response(
                    {
                        "detail": (
                            "Cannot complete a session with "
                            "no cognitive responses."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            total_trials = len(responses)

            omissions = sum(
                1 for response in responses
                if response.omission == 1
            )

            correct_responses = sum(
                1 for response in responses
                if response.omission == 0
                and response.is_correct == 1
            )

            incorrect_responses = sum(
                1 for response in responses
                if response.omission == 0
                and response.is_correct == 0
            )

            accuracy_rate = (
                Decimal(correct_responses)
                / Decimal(total_trials)
            )

            reaction_times = [
                float(response.reaction_time_ms)
                for response in responses
                if response.omission == 0
                and response.reaction_time_ms is not None
            ]

            if reaction_times:
                mean_rt = Decimal(
                    str(statistics.mean(reaction_times))
                )
                median_rt = Decimal(
                    str(statistics.median(reaction_times))
                )
                variability_rt = Decimal(
                    str(statistics.pstdev(reaction_times))
                ) if len(reaction_times) > 1 else Decimal("0")
            else:
                mean_rt = Decimal("0")
                median_rt = Decimal("0")
                variability_rt = Decimal("0")

            completed_at = timezone.now()

            completion_time_seconds = Decimal(
                str(
                    (completed_at - session.started_at)
                    .total_seconds()
                )
            )

            six_dp = Decimal("0.000001")
            two_dp = Decimal("0.01")

            accuracy_rate = accuracy_rate.quantize(
                six_dp, rounding=ROUND_HALF_UP
            )
            mean_rt = mean_rt.quantize(
                two_dp, rounding=ROUND_HALF_UP
            )
            median_rt = median_rt.quantize(
                two_dp, rounding=ROUND_HALF_UP
            )
            variability_rt = variability_rt.quantize(
                two_dp, rounding=ROUND_HALF_UP
            )
            completion_time_seconds = (
                completion_time_seconds.quantize(
                    two_dp, rounding=ROUND_HALF_UP
                )
            )

            cognitive_result_id = (
                f"CR{uuid.uuid4().hex[:16].upper()}"
            )

            result = CognitiveResult.objects.create(
                cognitive_result_id=cognitive_result_id,
                session=session,
                user=request.user,
                assessment_type=session.assessment_type,
                total_trials=total_trials,
                correct_responses=correct_responses,
                incorrect_responses=incorrect_responses,
                omissions=omissions,
                accuracy_rate=accuracy_rate,
                mean_reaction_time_ms=mean_rt,
                median_reaction_time_ms=median_rt,
                reaction_time_variability_ms=variability_rt,
                completion_time_seconds=completion_time_seconds,
                difficulty_level=session.difficulty_level,
                baseline_difference=Decimal("0.000000"),
                previous_session_difference=Decimal("0.000000"),
                calculated_at=completed_at,
            )

            session.completed_at = completed_at
            session.session_status = "completed"
            session.save(
                update_fields=[
                    "completed_at",
                    "session_status",
                ]
            )

        return Response(
            {
                "session_id": session.session_id,
                "session_status": session.session_status,
                "completed_at": session.completed_at,
                "cognitive_result": CognitiveResultSerializer(result).data,
                "longitudinal_scoring_status": "not_implemented",
            },
            status=status.HTTP_201_CREATED,
        )
