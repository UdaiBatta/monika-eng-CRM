from rest_framework import serializers

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    severity_label = serializers.CharField(source="get_severity_display", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "company",
            "notification_type",
            "severity",
            "severity_label",
            "title",
            "message",
            "entity_type",
            "entity_id",
            "action_url",
            "read_at",
            "archived_at",
            "created_at",
        ]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "in_app_enabled",
            "email_enabled",
            "sms_enabled",
            "whatsapp_enabled",
            "push_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email_enabled",
            "sms_enabled",
            "whatsapp_enabled",
            "push_enabled",
            "created_at",
            "updated_at",
        ]
