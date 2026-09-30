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