from django.db import transaction
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from assessments.models import AssessmentSession
from consent.permissions import HasRequiredConsent

from .models import (CognitiveResponse, 
                     CognitiveResult,
                     WellbeingCheckin,
                     ContextRecord)

from .serializers import (CognitiveResponseCreateSerializer, 
                          CognitiveResultSerializer,
                          WellbeingCheckinCreateSerializer,
                          ContextRecordCreateSerializer,
                          WellbeingCheckinSerializer)


class CognitiveResponseCreateView(generics.GenericAPIView):
    serializer_class = CognitiveResponseCreateSerializer
    permission_classes = [
        IsAuthenticated,
        HasRequiredConsent,
    ]
    required_consent_type = "cognitive_assessment"

    def post(self, request, session_id):
        # The session must exist AND belong to the authenticated user.
        try:
            session = AssessmentSession.objects.select_related(
                "assessment_type"
            ).get(
                session_id=session_id,
                user=request.user,
            )
        except AssessmentSession.DoesNotExist:
            return Response(
                {"detail": "Assessment session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Responses can only be submitted while the session is active.
        if session.session_status != "started":
            return Response(
                {
                    "detail":
                    "Responses can only be submitted to a started session."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = serializer.validated_data["task_id"]
        trial_number = serializer.validated_data["trial_number"]

        # The cognitive task must belong to the same assessment type
        # as the current session.
        if task.assessment_type_id != session.assessment_type_id:
            return Response(
                {
                    "detail":
                    "Task does not belong to this assessment type."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # A trial number should occur only once inside a session.
        if CognitiveResponse.objects.filter(
            session=session,
            trial_number=trial_number,
        ).exists():
            return Response(
                {
                    "detail":
                    "This trial number has already been recorded."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            last_response = CognitiveResponse.objects.order_by(
                "-response_id"
            ).first()

            if last_response is None:
                response_id = "RSP00000001"
            else:
                next_number = int(
                    last_response.response_id.replace("RSP", "")
                ) + 1
                response_id = f"RSP{next_number:08d}"

            response = CognitiveResponse.objects.create(
                response_id=response_id,
                session=session,
                task=task,
                trial_number=trial_number,
                stimulus_type=serializer.validated_data[
                    "stimulus_type"
                ],
                response_type=serializer.validated_data[
                    "response_type"
                ],
                is_correct=serializer.validated_data["is_correct"],
                reaction_time_ms=serializer.validated_data[
                    "reaction_time_ms"
                ],
                response_value=serializer.validated_data.get(
                    "response_value"
                ),
                omission=serializer.validated_data["omission"],
                recorded_at=timezone.now(),
            )

        return Response(
            {
                "response_id": response.response_id,
                "session_id": response.session_id,
                "task_id": response.task_id,
                "trial_number": response.trial_number,
                "stimulus_type": response.stimulus_type,
                "response_type": response.response_type,
                "is_correct": response.is_correct,
                "reaction_time_ms": response.reaction_time_ms,
                "response_value": response.response_value,
                "omission": response.omission,
                "recorded_at": response.recorded_at,
            },
            status=status.HTTP_201_CREATED,
        )

class CognitiveResultDetailView(generics.RetrieveAPIView):
    serializer_class = CognitiveResultSerializer
    permission_classes = [
        IsAuthenticated,
        HasRequiredConsent,
    ]
    required_consent_type = "cognitive_assessment"

    lookup_field = "cognitive_result_id"
    lookup_url_kwarg = "cognitive_result_id"

    def get_queryset(self):
        return (
            CognitiveResult.objects
            .filter(user=self.request.user)
            .select_related(
                "assessment_type",
                "session",
            )
        )

class CognitiveResultListView(generics.ListAPIView):
    serializer_class = CognitiveResultSerializer
    permission_classes = [
        IsAuthenticated,
        HasRequiredConsent,
    ]
    required_consent_type = "cognitive_assessment"

    def get_queryset(self):
        queryset = (
            CognitiveResult.objects
            .filter(user=self.request.user)
            .select_related(
                "assessment_type",
                "session",
            )
            .order_by("-calculated_at")
        )

        domain = self.request.query_params.get("domain")
        assessment_type = self.request.query_params.get(
            "assessment_type"
        )

        if domain:
            queryset = queryset.filter(
                assessment_type__cognitive_domain=domain
            )

        if assessment_type:
            queryset = queryset.filter(
                assessment_type__assessment_type_id=assessment_type
            )

        return queryset


class WellbeingCheckinCreateView(generics.GenericAPIView):
    serializer_class = WellbeingCheckinCreateSerializer
    permission_classes = [
        IsAuthenticated,
        HasRequiredConsent,
    ]
    required_consent_type = "wellbeing_data"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            last_checkin = WellbeingCheckin.objects.order_by(
                "-checkin_id"
            ).first()

            if last_checkin is None:
                checkin_id = "WBC00000001"
            else:
                next_number = int(
                    last_checkin.checkin_id.replace("WBC", "")
                ) + 1
                checkin_id = f"WBC{next_number:08d}"

            checkin = WellbeingCheckin.objects.create(
                checkin_id=checkin_id,
                user=request.user,
                recorded_at=timezone.now(),
                mood_level=serializer.validated_data.get(
                    "mood_level"
                ),
                stress_level=serializer.validated_data.get(
                    "stress_level"
                ),
                anxiety_level=serializer.validated_data.get(
                    "anxiety_level"
                ),
                sleep_quality=serializer.validated_data.get(
                    "sleep_quality"
                ),
                sleep_hours=serializer.validated_data.get(
                    "sleep_hours"
                ),
                social_wellbeing=serializer.validated_data.get(
                    "social_wellbeing"
                ),
                perceived_cognitive_change=(
                    serializer.validated_data.get(
                        "perceived_cognitive_change"
                    )
                ),
                completion_status=serializer.validated_data[
                    "completion_status"
                ],
            )

        return Response(
            {
                "checkin_id": checkin.checkin_id,
                "recorded_at": checkin.recorded_at,
                "mood_level": checkin.mood_level,
                "stress_level": checkin.stress_level,
                "anxiety_level": checkin.anxiety_level,
                "sleep_quality": checkin.sleep_quality,
                "sleep_hours": checkin.sleep_hours,
                "social_wellbeing": checkin.social_wellbeing,
                "perceived_cognitive_change":
                    checkin.perceived_cognitive_change,
                "completion_status": checkin.completion_status,
            },
            status=status.HTTP_201_CREATED,
        )

class ContextRecordCreateView(generics.GenericAPIView):
    serializer_class = ContextRecordCreateSerializer
    permission_classes = [
        IsAuthenticated,
        HasRequiredConsent,
    ]
    required_consent_type = "cognitive_assessment"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        related_session = None
        related_session_id = serializer.validated_data.get(
            "related_session_id"
        )

        if related_session_id:
            try:
                related_session = AssessmentSession.objects.get(
                    session_id=related_session_id,
                    user=request.user,
                )
            except AssessmentSession.DoesNotExist:
                return Response(
                    {
                        "detail":
                        "Related assessment session not found."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        with transaction.atomic():
            last_context = ContextRecord.objects.order_by(
                "-context_id"
            ).first()

            if last_context is None:
                context_id = "CTX00000001"
            else:
                next_number = int(
                    last_context.context_id.replace("CTX", "")
                ) + 1
                context_id = f"CTX{next_number:08d}"

            context = ContextRecord.objects.create(
                context_id=context_id,
                user=request.user,
                related_session=related_session,
                recorded_at=timezone.now(),
                context_type=serializer.validated_data[
                    "context_type"
                ],
                context_value=serializer.validated_data[
                    "context_value"
                ],
                source="self_report",
            )

        return Response(
            {
                "context_id": context.context_id,
                "related_session_id":
                    context.related_session_id,
                "recorded_at": context.recorded_at,
                "context_type": context.context_type,
                "context_value": context.context_value,
                "source": context.source,
            },
            status=status.HTTP_201_CREATED,
        )

class WellbeingCheckinListView(generics.ListAPIView):
    serializer_class = WellbeingCheckinSerializer
    permission_classes = [
        IsAuthenticated,
        HasRequiredConsent,
    ]
    required_consent_type = "wellbeing_data"

    def get_queryset(self):
        return (
            WellbeingCheckin.objects
            .filter(user=self.request.user)
            .order_by("-recorded_at")
        )