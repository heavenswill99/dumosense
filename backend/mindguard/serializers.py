from rest_framework import serializers

from .models import (CognitiveTask, 
                     CognitiveResult, 
                     WellbeingCheckin,
                     ContextRecord)


class CognitiveResponseCreateSerializer(serializers.Serializer):
    task_id = serializers.CharField(max_length=20)
    trial_number = serializers.IntegerField(min_value=1)

    stimulus_type = serializers.ChoiceField(
        choices=["sequence", "symbol", "visual", "word"]
    )

    response_type = serializers.ChoiceField(
        choices=["choice", "tap", "typed"]
    )

    is_correct = serializers.ChoiceField(
        choices=[0, 1]
    )

    reaction_time_ms = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
    )

    response_value = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    omission = serializers.ChoiceField(
        choices=[0, 1]
    )

    def validate_task_id(self, value):
        try:
            return CognitiveTask.objects.get(
                task_id=value,
                active=1,
            )
        except CognitiveTask.DoesNotExist:
            raise serializers.ValidationError(
                "Active cognitive task not found."
            )


class CognitiveResultSerializer(serializers.ModelSerializer):
    assessment_type_id = serializers.CharField(
        source="assessment_type.assessment_type_id",
        read_only=True,
    )

    assessment_name = serializers.CharField(
        source="assessment_type.assessment_name",
        read_only=True,
    )

    cognitive_domain = serializers.CharField(
        source="assessment_type.cognitive_domain",
        read_only=True,
    )

    session_id = serializers.CharField(
        source="session.session_id",
        read_only=True,
    )

    started_at = serializers.DateTimeField(
        source="session.started_at",
        read_only=True,
    )

    completed_at = serializers.DateTimeField(
        source="session.completed_at",
        read_only=True,
    )

    class Meta:
        model = CognitiveResult
        fields = [
            "cognitive_result_id",
            "session_id",
            "assessment_type_id",
            "assessment_name",
            "cognitive_domain",
            "started_at",
            "completed_at",
            "total_trials",
            "correct_responses",
            "incorrect_responses",
            "omissions",
            "accuracy_rate",
            "mean_reaction_time_ms",
            "median_reaction_time_ms",
            "reaction_time_variability_ms",
            "completion_time_seconds",
            "difficulty_level",
            "baseline_difference",
            "previous_session_difference",
            "calculated_at",
        ]
        read_only_fields = fields

class WellbeingCheckinCreateSerializer(serializers.Serializer):
    mood_level = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=1,
        max_value=5,
        required=False,
        allow_null=True,
    )

    stress_level = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=1,
        max_value=5,
        required=False,
        allow_null=True,
    )

    anxiety_level = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=1,
        max_value=5,
        required=False,
        allow_null=True,
    )

    sleep_quality = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=1,
        max_value=5,
        required=False,
        allow_null=True,
    )

    sleep_hours = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=0,
        max_value=24,
        required=False,
        allow_null=True,
    )

    social_wellbeing = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=1,
        max_value=5,
        required=False,
        allow_null=True,
    )

    perceived_cognitive_change = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=1,
        max_value=5,
        required=False,
        allow_null=True,
    )

    completion_status = serializers.ChoiceField(
        choices=["partial", "completed"]
    )

class ContextRecordCreateSerializer(serializers.Serializer):
    related_session_id = serializers.CharField(
        max_length=20,
        required=False,
        allow_null=True,
    )

    context_type = serializers.ChoiceField(
        choices=[
            "illness_self_report",
            "lifestyle_change",
            "major_life_event",
            "medication_change_self_report",
            "none",
            "sleep",
            "stress",
            "travel",
            "workload",
        ]
    )

    context_value = serializers.CharField(
        max_length=255
    )

    def validate(self, attrs):
        context_type = attrs["context_type"]
        context_value = attrs["context_value"]

        allowed_values = {
            "illness_self_report": [
                "temporary_unwell",
            ],
            "lifestyle_change": [
                "routine_change",
            ],
            "major_life_event": [
                "self_reported_event",
            ],
            "medication_change_self_report": [
                "self_reported_change",
            ],
            "none": [
                "none",
            ],
            "sleep": [
                "poor",
                "fair",
                "good",
            ],
            "stress": [
                "low",
                "moderate",
                "high",
            ],
            "travel": [
                "recent_travel",
            ],
            "workload": [
                "normal",
                "high",
            ],
        }

        if context_value not in allowed_values[context_type]:
            raise serializers.ValidationError(
                {
                    "context_value":
                        f"Invalid value for context type "
                        f"'{context_type}'."
                }
            )

        return attrs

class WellbeingCheckinSerializer(serializers.ModelSerializer):
    class Meta:
        model = WellbeingCheckin
        fields = [
            "checkin_id",
            "recorded_at",
            "mood_level",
            "stress_level",
            "anxiety_level",
            "sleep_quality",
            "sleep_hours",
            "social_wellbeing",
            "perceived_cognitive_change",
            "completion_status",
        ]
        read_only_fields = fields


class ContextRecordSerializer(serializers.ModelSerializer):
    related_session_id = serializers.CharField(
        source="related_session.session_id",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ContextRecord

        fields = [
            "context_id",
            "related_session_id",
            "recorded_at",
            "context_type",
            "context_value",
            "source",
        ]

        read_only_fields = fields