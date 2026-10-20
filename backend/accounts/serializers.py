from rest_framework import serializers

from .models import User, UserProfile, ProductEnrollment


import secrets


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


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = [
            "user_id",
            "first_name",
            "last_name",
            "email",
            "password",
        ]
        read_only_fields = ["user_id"]

    def validate_email(self, value):
        email = value.strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return email

    def create(self, validated_data):
        password = validated_data.pop("password")

        # Generate a unique ID within the model's 20-character limit.
        for _ in range(10):
            user_id = "USR" + secrets.token_hex(8).upper()

            if not User.objects.filter(user_id=user_id).exists():
                break
        else:
            raise serializers.ValidationError(
                "Unable to generate a unique user ID."
            )

        return User.objects.create_user(
            user_id=user_id,
            password=password,
            **validated_data
        )


class CurrentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "user_id",
            "first_name",
            "last_name",
            "email",
            "account_status",
        ]
        read_only_fields = fields
