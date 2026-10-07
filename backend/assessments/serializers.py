from rest_framework import serializers

from .models import AssessmentSession, AssessmentType


class AssessmentSessionCreateSerializer(serializers.Serializer):
    assessment_type_id = serializers.CharField(max_length=20)
    difficulty_level = serializers.ChoiceField( choices = [1,2,3,4])
    device_type = serializers.ChoiceField(choices=["mobile", "desktop", "tablet"])

    def validate_assessment_type_id(self, value):
        try:
            assessment_type = AssessmentType.objects.get(
                assessment_type_id=value,
                active=1,
            )
        except AssessmentType.DoesNotExist:
            raise serializers.ValidationError(
                "Active assessment type not found."
            )

        return assessment_type


class AssessmentSessionSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = AssessmentSession
        fields = [
            "session_id",
            "assessment_type_id",
            "assessment_name",
            "cognitive_domain",
            "started_at",
            "completed_at",
            "session_status",
            "difficulty_level",
            "device_type",
        ]
        read_only_fields = fields
# Create your views here.
