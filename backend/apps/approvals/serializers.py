from rest_framework import serializers

from apps.accounts.models import User

from .models import (
    ApprovalAssignment,
    ApprovalCondition,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStepDefinition,
    ApprovalStepInstance,
    ApprovalWorkflow,
    ApprovalWorkflowVersion,
)
from .services import create_approval_request, create_workflow


class ApprovalConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalCondition
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance or ApprovalCondition()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean()
        return attrs


class ApprovalStepDefinitionSerializer(serializers.ModelSerializer):
    specific_users = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        many=True,
        required=False,
    )

    class Meta:
        model = ApprovalStepDefinition
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        users = attrs.get("specific_users")
        version = attrs.get("workflow_version") or getattr(self.instance, "workflow_version", None)
        if users is not None and version is not None:
            invalid = [
                user.email
                for user in users
                if getattr(getattr(user, "employee", None), "company_id", None)
                != version.workflow.company_id
            ]
            if invalid:
                raise serializers.ValidationError(
                    {"specific_users": ["Every approver must be an employee of the workflow company."]}
                )
        instance = self.instance or ApprovalStepDefinition()
        for field, value in attrs.items():
            if field != "specific_users":
                setattr(instance, field, value)
        instance.full_clean()
        return attrs


class ApprovalWorkflowVersionSerializer(serializers.ModelSerializer):
    steps = ApprovalStepDefinitionSerializer(many=True, read_only=True)
    conditions = ApprovalConditionSerializer(many=True, read_only=True)
    workflow_name = serializers.CharField(source="workflow.name", read_only=True)

    class Meta:
        model = ApprovalWorkflowVersion
        fields = "__all__"
        read_only_fields = [
            "id",
            "workflow",
            "version_number",
            "status",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        instance = self.instance
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean()
        return attrs


class ApprovalWorkflowSerializer(serializers.ModelSerializer):
    current_version_number = serializers.IntegerField(
        source="current_version.version_number",
        read_only=True,
    )
    versions = ApprovalWorkflowVersionSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalWorkflow
        fields = "__all__"
        read_only_fields = ["id", "current_version", "created_at", "updated_at"]

    def create(self, validated_data):
        return create_workflow(actor=self.context["request"].user, **validated_data)


class ApprovalDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalDecision
        fields = "__all__"
        read_only_fields = fields


class ApprovalAssignmentSerializer(serializers.ModelSerializer):
    decision_record = ApprovalDecisionSerializer(read_only=True)

    class Meta:
        model = ApprovalAssignment
        fields = "__all__"
        read_only_fields = fields


class ApprovalStepInstanceSerializer(serializers.ModelSerializer):
    assignments = ApprovalAssignmentSerializer(many=True, read_only=True)
    decisions = ApprovalDecisionSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalStepInstance
        fields = "__all__"
        read_only_fields = fields


class ApprovalRequestSerializer(serializers.ModelSerializer):
    steps = ApprovalStepInstanceSerializer(many=True, read_only=True)
    requested_by_email = serializers.EmailField(source="requested_by.email", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    current_step_name = serializers.CharField(source="current_step.step_name", read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = "__all__"
        read_only_fields = fields


class ApprovalRequestCreateSerializer(serializers.Serializer):
    workflow_id = serializers.UUIDField()
    entity_type = serializers.CharField(max_length=80)
    entity_id = serializers.CharField(max_length=100)
    submission_comment = serializers.CharField(required=False, allow_blank=True)
    snapshot_metadata = serializers.JSONField(required=False)

    def create(self, validated_data):
        return create_approval_request(actor=self.context["request"].user, **validated_data)


class ApprovalDecisionCommandSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True)


class ApprovalRequiredCommentSerializer(serializers.Serializer):
    comment = serializers.CharField()


class ApprovalCancelSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True)
