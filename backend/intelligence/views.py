from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .chatbot import answer_chat_message
from mindguard.models import MindGuardDataConsent, MindGuardReflection


class HomeDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        has_mindguard_consent = MindGuardDataConsent.objects.filter(
            user=request.user,
            granted=True,
        ).exists()

        if has_mindguard_consent:
            reflections = MindGuardReflection.objects.filter(
                user=request.user
            )
            mindguard_count = reflections.count()
        else:
            mindguard_count = 0

        return Response(
            {
                "first_name": request.user.first_name,
                "pattern_state": (
                    "insufficient" if mindguard_count else "no_data"
                ),
                "progress": {
                    "understanding": 0,
                    "preparedness": 0,
                    "action": 0,
                },
                "change": {"state": "no_data"},
                "insights": {
                    "mindguard": {
                        "state": (
                            "insufficient" if mindguard_count else "no_data"
                        ),
                        "count": mindguard_count,
                    },
                    "health_reserve": {
                        "assessed": False,
                        "state": "no_data",
                        "gap": 0,
                        "progress": 0,
                    },
                },
                "next_action": None,
                "ring": None,
            }
        )


class DemoStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"demo_mode": None, "demo_eligible": False})


class AIChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(
        max_length=2000,
        min_length=1,
        trim_whitespace=True,
    )


class AIChatView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AIChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {
                "role": "assistant",
                "content": answer_chat_message(
                    serializer.validated_data["message"]
                ),
                "grounded_on": [],
            }
        )


class AIExplainRequestSerializer(serializers.Serializer):
    ref = serializers.ChoiceField(
        choices=["mindguard_change", "pattern", "reserve_gap"]
    )


class AIExplainView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AIExplainRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ref = serializer.validated_data["ref"]

        if ref == "reserve_gap":
            next_step = (
                "Open Health Reserve to review the planning inputs and "
                "estimates. They are not financial advice."
            )
        else:
            next_step = (
                "Open MindGuard to complete a reflection. This chat does not "
                "analyze your saved responses."
            )

        return Response(
            {
                "epistemic": "UNKNOWN",
                "sections": {
                    "what_we_observed": (
                        "No personal health data was accessed for this response."
                    ),
                    "what_changed": (
                        "This chat does not calculate personal changes or trends."
                    ),
                    "what_it_may_mean": (
                        "This is general product guidance, not a personal assessment."
                    ),
                    "what_we_dont_know": (
                        "Your saved records and individual answers are not "
                        "available to this chat."
                    ),
                    "what_you_can_do_next": next_step,
                },
                "provenance": (
                    f"General guidance for {ref.replace('_', ' ')}; no personal "
                    "records were used."
                ),
            }
        )
