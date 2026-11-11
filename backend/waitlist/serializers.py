from django.utils import timezone
from rest_framework import serializers

from .models import WaitlistRegistration


class WaitlistRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitlistRegistration
        fields = [
            "id",
            "full_name",
            "email",
            "phone_number",
            "city",
            "country",
            "employment_status",
            "occupation",
            "industry",
            "product_interest",
            "interest_reason",
            "testing_interest",
            "consent_accepted",
            "consent_timestamp",
            "consent_policy_version",
            "registration_status",
            "confirmation_email_status",
            "confirmation_email_sent_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "consent_timestamp",
            "consent_policy_version",
            "registration_status",
            "confirmation_email_status",
            "confirmation_email_sent_at",
            "created_at",
            "updated_at",
        ]

    def validate_email(self, value):
        return value.strip().lower()

    def validate_full_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Please enter your full name.")
        return value

    def validate_product_interest(self, value):
        if value not in {"mindguard", "health_reserve", "both"}:
            raise serializers.ValidationError("Choose MindGuard, Health Reserve, or both products.")
        return value

    def validate_employment_status(self, value):
        allowed = {
            "Employed",
            "Self-employed",
            "Business Owner",
            "Student",
            "Retired",
            "Unemployed",
            "Other",
        }
        if value and value not in allowed:
            raise serializers.ValidationError("Choose a valid employment status.")
        return value

    def validate_interest_reason(self, value):
        return value.strip() if value else value

    def validate_phone_number(self, value):
        return value.strip() if value else value

    def validate_city(self, value):
        return value.strip() if value else value

    def validate_country(self, value):
        return value.strip() if value else value

    def validate_occupation(self, value):
        return value.strip() if value else value

    def validate_industry(self, value):
        return value.strip() if value else value

    def validate_testing_interest(self, value):
        allowed = {
            "Yes, I'm interested",
            "Maybe, I'd like more information",
            "No, just keep me updated",
        }
        if value and value not in allowed:
            raise serializers.ValidationError("Choose a valid product testing preference.")
        return value

    def validate(self, attrs):
        if not attrs.get("consent_accepted"):
            raise serializers.ValidationError({"consent_accepted": "Consent is required."})
        return attrs

    def create(self, validated_data):
        validated_data["consent_policy_version"] = validated_data.get("consent_policy_version", "v1")
        validated_data["consent_timestamp"] = validated_data.get("consent_timestamp") or timezone.now()
        return super().create(validated_data)
