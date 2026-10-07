from rest_framework import serializers

from .models import Consent


class ConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consent
        fields = [
            "consent_id",
            "consent_type",
            "purpose",
            "consent_version",
            "status",
            "granted_at",
            "withdrawn_at",
        ]
        read_only_fields = fields

class ConsentWithdrawalSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )

class ConsentGrantSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255
    )

class ConsentCreateSerializer(serializers.Serializer):
    consent_type = serializers.CharField(max_length=100)
    purpose = serializers.CharField(max_length=255)
    consent_version = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
    )
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )