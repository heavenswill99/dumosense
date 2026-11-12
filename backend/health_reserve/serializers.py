from rest_framework import serializers
from .models import HealthReserveAssessment
from decimal import Decimal


class HealthReserveAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthReserveAssessment

        fields = [
            "reserve_assessment_id",
            "assessed_at",
            "healthcare_coverage_status",
            "estimated_healthcare_exposure",
            "emergency_health_resources",
            "monthly_financial_obligations",
            "number_of_dependants",
            "current_preparedness_amount",
            "preparedness_target",
            "preparedness_gap",
            "preparedness_ratio",
            "reserve_status",
        ]

        read_only_fields = fields

class HealthReserveAssessmentCreateSerializer(serializers.Serializer):
    target_mode = serializers.ChoiceField(
        choices=["manual", "recommended"],
        default="manual",
    )

    healthcare_coverage_status = serializers.CharField(max_length=30)

    estimated_healthcare_exposure = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )

    emergency_health_resources = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )

    monthly_financial_obligations = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )

    number_of_dependants = serializers.IntegerField(min_value=0)

    current_preparedness_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )

    preparedness_target = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )

    def validate(self, attrs):
        mode = attrs["target_mode"]

        if mode == "manual" and "preparedness_target" not in attrs:
            raise serializers.ValidationError({
                "preparedness_target": (
                    "Enter your Health Reserve target."
                )
            })

        if mode == "recommended":
            raise serializers.ValidationError({
                "target_mode": (
                    "Automatic target recommendations are not available yet."
                )
            })

        return attrs