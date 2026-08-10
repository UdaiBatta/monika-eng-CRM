from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    company_name = serializers.CharField(source="company.name", read_only=True)
    action_label = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "company",
            "company_name",
            "actor_user",
            "actor_employee",
            "actor_name",
            "event_type",
            "module",
            "entity_type",
            "entity_id",
            "entity_reference",
            "action",
            "action_label",
            "occurred_at",
            "source",
            "summary",
            "metadata",
            "changes",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        if obj.actor_employee:
            return obj.actor_employee.display_name
        if obj.actor_user:
            return obj.actor_user.get_full_name() or obj.actor_user.email
        return "System"
