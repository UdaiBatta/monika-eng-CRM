from django.contrib import admin

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

admin.site.register(ApprovalWorkflow)
admin.site.register(ApprovalWorkflowVersion)
admin.site.register(ApprovalStepDefinition)
admin.site.register(ApprovalCondition)


class ApprovalStepInstanceInline(admin.TabularInline):
    model = ApprovalStepInstance
    extra = 0
    can_delete = False
    readonly_fields = (
        "sequence",
        "step_name",
        "status",
        "opened_at",
        "decided_at",
        "resolution_metadata",
    )


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ("entity_reference", "workflow_name", "status", "requested_by_name", "requested_at")
    list_filter = ("company", "status", "entity_type")
    search_fields = ("entity_reference", "workflow_name", "requested_by_name")
    readonly_fields = [field.name for field in ApprovalRequest._meta.fields]
    inlines = (ApprovalStepInstanceInline,)


admin.site.register(ApprovalAssignment)
admin.site.register(ApprovalDecision)
