from rest_framework import serializers

from .models import User, UserProfile, ProductEnrollment


class UserProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source="user.user_id", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "profile_id",
            "user_id",
            "first_name",
            "last_name",
            "email",
            "date_of_birth",
            "age_group",
            "sex",
            "country",
            "state_or_region",
            "profile_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

class ProductEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductEnrollment
        fields = [
            "enrollment_id",
            "product_code",
            "enrollment_status",
            "enrolled_at",
            "discontinued_at",
        ]
        read_only_fields = fields