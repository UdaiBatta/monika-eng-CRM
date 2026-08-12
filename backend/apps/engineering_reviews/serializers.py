from rest_framework import serializers

from .models import EngineeringClarification, EngineeringFeasibilityReview
from .services import approval_state, is_ready_for_estimation


class EngineeringClarificationSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source="assigned_to.display_name", read_only=True)
    requested_by_name = serializers.SerializerMethodField()
    responded_by_name = serializers.SerializerMethodField()
    closed_by_name = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = EngineeringClarification
        fields = "__all__"
        read_only_fields = [field.name for field in EngineeringClarification._meta.fields]

    def _name(self, user):
        if not user:
            return ""
        employee = getattr(user, "employee", None)
        return employee.display_name if employee else user.email

    def get_requested_by_name(self, obj):
        return self._name(obj.requested_by)

    def get_responded_by_name(self, obj):
        return self._name(obj.responded_by)

    def get_closed_by_name(self, obj):
        return self._name(obj.closed_by)

    def get_is_overdue(self, obj):
        from django.utils import timezone

        return bool(
            obj.status == EngineeringClarification.Status.OPEN and obj.due_at and obj.due_at < timezone.now()
        )


class EngineeringReviewSerializer(serializers.ModelSerializer):
    enquiry_number = serializers.CharField(source="enquiry.enquiry_number", read_only=True)
    enquiry_subject = serializers.CharField(source="enquiry.subject", read_only=True)
    customer_id = serializers.UUIDField(source="enquiry.customer_id", read_only=True)
    customer_code = serializers.CharField(source="enquiry.customer.customer_code", read_only=True)
    customer_name = serializers.CharField(source="enquiry.customer.legal_name", read_only=True)
    due_date = serializers.DateField(source="enquiry.due_date", read_only=True)
    priority = serializers.CharField(source="enquiry.priority", read_only=True)
    sales_owner_name = serializers.CharField(
        source="enquiry.responsible_salesperson.display_name", read_only=True
    )
    assigned_engineer_name = serializers.CharField(source="assigned_engineer.display_name", read_only=True)
    started_by_name = serializers.SerializerMethodField()
    completed_by_name = serializers.SerializerMethodField()
    open_clarifications = serializers.SerializerMethodField()
    ready_for_estimation = serializers.SerializerMethodField()
    approval = serializers.SerializerMethodField()
    clarifications = EngineeringClarificationSerializer(many=True, read_only=True)

    class Meta:
        model = EngineeringFeasibilityReview
        fields = "__all__"
        read_only_fields = [field.name for field in EngineeringFeasibilityReview._meta.fields]

    def _name(self, user):
        if not user:
            return ""
        employee = getattr(user, "employee", None)
        return employee.display_name if employee else user.email

    def get_started_by_name(self, obj):
        return self._name(obj.started_by)

    def get_completed_by_name(self, obj):
        return self._name(obj.completed_by)

    def get_open_clarifications(self, obj):
        return obj.clarifications.filter(
            status__in=[EngineeringClarification.Status.OPEN, EngineeringClarification.Status.RESPONDED]
        ).count()

    def get_ready_for_estimation(self, obj):
        return is_ready_for_estimation(obj)

    def get_approval(self, obj):
        state = approval_state(obj)
        request = state["request"]
        return {
            "required": state["required"],
            "status": state["status"],
            "request_id": str(request.pk) if request else None,
            "workflow_name": request.workflow_name if request else "",
        }


class EngineeringAssessmentSerializer(serializers.Serializer):
    technical_summary = serializers.CharField(required=False, allow_blank=True)
    feasibility_notes = serializers.CharField(required=False, allow_blank=True)
    assumptions = serializers.CharField(required=False, allow_blank=True)
    exclusions = serializers.CharField(required=False, allow_blank=True)
    constraints = serializers.CharField(required=False, allow_blank=True)
    risks = serializers.CharField(required=False, allow_blank=True)
    special_materials = serializers.CharField(required=False, allow_blank=True)
    outsourced_processes = serializers.CharField(required=False, allow_blank=True)
    tooling_requirements = serializers.CharField(required=False, allow_blank=True)
    testing_requirements = serializers.CharField(required=False, allow_blank=True)
    customer_clarification_summary = serializers.CharField(required=False, allow_blank=True)
    preliminary_drawing_notes = serializers.CharField(required=False, allow_blank=True)
    preliminary_bom_notes = serializers.CharField(required=False, allow_blank=True)
    preliminary_routing_notes = serializers.CharField(required=False, allow_blank=True)
    engineering_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    manufacturing_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    lead_time_days = serializers.IntegerField(required=False, allow_null=True, min_value=0)


class ReviewAssignSerializer(serializers.Serializer):
    engineer_id = serializers.UUIDField()


class ClarificationRequestSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=250)
    question = serializers.CharField()
    context = serializers.CharField(required=False, allow_blank=True)
    assigned_to_id = serializers.UUIDField()
    due_at = serializers.DateTimeField(required=False, allow_null=True)


class ClarificationResponseSerializer(serializers.Serializer):
    response = serializers.CharField()


class ClarificationCloseSerializer(serializers.Serializer):
    closure_comment = serializers.CharField(required=False, allow_blank=True)


class ReviewCompleteSerializer(serializers.Serializer):
    result = serializers.ChoiceField(
        choices=[
            EngineeringFeasibilityReview.Result.FEASIBLE,
            EngineeringFeasibilityReview.Result.FEASIBLE_WITH_CONDITIONS,
        ]
    )
    completion_comment = serializers.CharField()


class ReviewNotFeasibleSerializer(serializers.Serializer):
    completion_comment = serializers.CharField()


class ReviewReassessSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)
