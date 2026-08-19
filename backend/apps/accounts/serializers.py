from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "record_version",
            "password",
            "last_login",
            "date_joined",
        ]
        read_only_fields = ["id", "is_active", "is_staff", "record_version", "last_login", "date_joined"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=["password"])
        return instance


class UserDeactivateSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3, max_length=500)
    open_work_action = serializers.ChoiceField(
        choices=["LEAVE_TEMPORARILY", "REASSIGN"], required=False
    )
    replacement_employee_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if attrs.get("open_work_action") == "REASSIGN" and not attrs.get("replacement_employee_id"):
            raise serializers.ValidationError(
                {"replacement_employee_id": "Choose who will receive the open work."}
            )
        return attrs

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(trim_whitespace=False)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(trim_whitespace=False, validators=[validate_password])
