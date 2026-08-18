from rest_framework import serializers

from apps.audit.models import AuditEvent
from apps.documents.models import DocumentLink
from apps.rbac.services import has_permission
from apps.sales.serializers import CustomerPOSerializer, SalesOrderSerializer

from .models import Project, ProjectEngineeringHandoff, ProjectHandoffClarification


class ProjectClarificationSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source="requested_by.email", read_only=True)
    respond_to_name = serializers.CharField(source="respond_to.display_name", read_only=True)
    responded_by_name = serializers.CharField(source="responded_by.email", read_only=True)
    response_document_title = serializers.CharField(source="response_document.title", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ProjectHandoffClarification
        fields = "__all__"
        read_only_fields = [field.name for field in ProjectHandoffClarification._meta.fields]


class ProjectHandoffSerializer(serializers.ModelSerializer):
    assigned_engineer_name = serializers.CharField(source="assigned_engineer.display_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    clarifications = ProjectClarificationSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectEngineeringHandoff
        fields = "__all__"
        read_only_fields = [field.name for field in ProjectEngineeringHandoff._meta.fields]


class ProjectSerializer(serializers.ModelSerializer):
    sales_order_detail = SalesOrderSerializer(source="sales_order", read_only=True)
    customer_po_detail = serializers.SerializerMethodField()
    engineering_handoff = ProjectHandoffSerializer(read_only=True)
    customer_name = serializers.CharField(source="customer.legal_name", read_only=True)
    contact_name = serializers.CharField(source="sales_order.contact.display_name", read_only=True)
    site_name = serializers.CharField(source="site.label", read_only=True)
    sales_owner_name = serializers.CharField(source="sales_owner.display_name", read_only=True)
    project_owner_name = serializers.CharField(source="project_owner.display_name", read_only=True)
    engineering_owner_name = serializers.CharField(source="engineering_owner.display_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    priority_label = serializers.CharField(source="get_priority_display", read_only=True)
    current_commercial_baseline = serializers.CharField(
        source="current_sales_order_revision.__str__", read_only=True
    )
    previous_commercial_baseline = serializers.CharField(
        source="previous_sales_order_revision.__str__", read_only=True
    )
    documents = serializers.SerializerMethodField()
    activity = serializers.SerializerMethodField()
    next_action = serializers.SerializerMethodField()
    open_clarification_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = [field.name for field in Project._meta.fields]

    def get_customer_po_detail(self, instance):
        po = instance.sales_order.customer_purchase_order
        return CustomerPOSerializer(po, context=self.context).data if po else None

    def get_documents(self, instance):
        request = self.context.get("request")
        if not request or not has_permission(request.user, "documents.document.view", instance):
            return []
        links = DocumentLink.objects.filter(
            entity_type="project", entity_id=str(instance.pk), document__status="ACTIVE"
        ).select_related("document__category", "document__current_version")
        return [
            {
                "id": str(link.document_id),
                "title": link.document.title,
                "category": link.document.category.name,
                "relationship": link.relationship_type,
                "filename": (
                    link.document.current_version.safe_display_filename
                    if link.document.current_version_id
                    else ""
                ),
                "updated_at": link.document.updated_at,
            }
            for link in links
        ]

    def get_activity(self, instance):
        request = self.context.get("request")
        if not request or not has_permission(request.user, "audit.event.view", instance):
            return []
        events = AuditEvent.objects.filter(
            company_id=instance.company_id, entity_type="project", entity_id=str(instance.pk)
        ).select_related("actor_employee")[:50]
        return [
            {
                "id": str(event.pk),
                "action": event.action,
                "summary": event.summary,
                "actor": event.actor_employee.display_name if event.actor_employee else "System",
                "occurred_at": event.occurred_at,
            }
            for event in events
        ]

    @staticmethod
    def get_next_action(instance):
        if instance.status == Project.Status.ON_HOLD:
            return "Project is on hold. Resume it when work may continue."
        if instance.status == Project.Status.CANCELLED:
            return "Project is cancelled; its history remains available."
        if instance.commercial_change_pending:
            return "Engineering must review the changed Sales Order revision."
        handoff = getattr(instance, "engineering_handoff", None)
        if not handoff:
            return "Prepare the Engineering handoff."
        return {
            ProjectEngineeringHandoff.Status.DRAFT: "Sales must complete and send the Engineering handoff.",
            ProjectEngineeringHandoff.Status.READY_FOR_ENGINEERING: (
                "Engineering must take ownership and review."
            ),
            ProjectEngineeringHandoff.Status.ENGINEERING_REVIEWING: "Engineering is reviewing the handoff.",
            ProjectEngineeringHandoff.Status.CLARIFICATION_REQUIRED: (
                "Sales must answer the open clarification."
            ),
            ProjectEngineeringHandoff.Status.ACCEPTED: "Project ready for detailed engineering.",
        }[handoff.status]

    @staticmethod
    def get_open_clarification_count(instance):
        handoff = getattr(instance, "engineering_handoff", None)
        return (
            handoff.clarifications.filter(status=ProjectHandoffClarification.Status.OPEN).count()
            if handoff
            else 0
        )


class ProjectCreateInputSerializer(serializers.Serializer):
    project_name = serializers.CharField(max_length=250, required=False, allow_blank=True)
    customer_project_reference = serializers.CharField(max_length=250, required=False, allow_blank=True)
    project_owner_id = serializers.UUIDField(required=False, allow_null=True)
    engineering_owner_id = serializers.UUIDField(required=False, allow_null=True)
    priority = serializers.ChoiceField(choices=Project.Priority.choices, default=Project.Priority.NORMAL)
    planned_start = serializers.DateField(required=False, allow_null=True)
    target_completion = serializers.DateField(required=False, allow_null=True)
    internal_notes = serializers.CharField(required=False, allow_blank=True)


class ProjectUpdateInputSerializer(serializers.Serializer):
    record_version = serializers.IntegerField(min_value=1)
    project_name = serializers.CharField(max_length=250, required=False)
    customer_project_reference = serializers.CharField(max_length=250, required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=Project.Priority.choices, required=False)
    planned_start = serializers.DateField(required=False, allow_null=True)
    target_completion = serializers.DateField(required=False, allow_null=True)
    customer_delivery_commitment = serializers.CharField(required=False, allow_blank=True)
    internal_notes = serializers.CharField(required=False, allow_blank=True)


class HandoffUpdateInputSerializer(serializers.Serializer):
    record_version = serializers.IntegerField(min_value=1)
    project_scope_summary = serializers.CharField(required=False, allow_blank=True)
    technical_requirement_summary = serializers.CharField(required=False, allow_blank=True)
    customer_specifications = serializers.CharField(required=False, allow_blank=True)
    special_commercial_commitments = serializers.CharField(required=False, allow_blank=True)
    technical_assumptions = serializers.CharField(required=False, allow_blank=True)
    open_questions = serializers.CharField(required=False, allow_blank=True)
    sales_notes = serializers.CharField(required=False, allow_blank=True)
    assigned_engineer_id = serializers.UUIDField(required=False, allow_null=True)


class HandoffAssignInputSerializer(serializers.Serializer):
    engineer_id = serializers.UUIDField()


class ClarificationRequestInputSerializer(serializers.Serializer):
    question = serializers.CharField()
    respond_to_id = serializers.UUIDField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)


class ClarificationResponseInputSerializer(serializers.Serializer):
    response = serializers.CharField()
    document_id = serializers.UUIDField(required=False, allow_null=True)


class ProjectReasonInputSerializer(serializers.Serializer):
    reason = serializers.CharField()
