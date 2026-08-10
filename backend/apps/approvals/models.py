from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.entity_registry import registered_entity
from apps.core.models import TimeStampedModel
from apps.organization.models import Company


class ApprovalWorkflow(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="approval_workflows")
    code = models.CharField(max_length=60)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    entity_type = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)
    current_version = models.ForeignKey(
        "ApprovalWorkflowVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_for_workflows",
    )

    class Meta:
        ordering = ["company__name", "code"]
        constraints = [
            models.UniqueConstraint(fields=["company", "code"], name="unique_approval_workflow_code")
        ]
        indexes = [
            models.Index(fields=["company", "entity_type", "is_active"], name="approval_workflow_lookup_idx")
        ]

    def clean(self):
        registered_entity(self.entity_type, "approvals")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"


class ApprovalWorkflowVersion(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        RETIRED = "RETIRED", "Retired"

    workflow = models.ForeignKey(ApprovalWorkflow, on_delete=models.PROTECT, related_name="versions")
    version_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    allow_self_approval = models.BooleanField(default=False)
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_to = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="approval_workflow_versions",
    )

    class Meta:
        ordering = ["workflow", "-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "version_number"],
                name="unique_approval_workflow_version",
            ),
            models.CheckConstraint(
                condition=models.Q(version_number__gt=0),
                name="positive_approval_workflow_version",
            ),
        ]

    def clean(self):
        if self.effective_from and self.effective_to and self.effective_to <= self.effective_from:
            raise ValidationError({"effective_to": "Effective-to must be later than effective-from."})
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).first()
            if previous and previous.status != self.Status.DRAFT:
                protected = (
                    "workflow_id",
                    "version_number",
                    "allow_self_approval",
                    "effective_from",
                    "effective_to",
                )
                if any(getattr(previous, field) != getattr(self, field) for field in protected):
                    raise ValidationError("An activated workflow version cannot be changed.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.workflow.code} - Version {self.version_number}"

    @property
    def company_id(self):
        return self.workflow.company_id


class ApprovalStepDefinition(TimeStampedModel):
    class ApprovalMode(models.TextChoices):
        SINGLE = "SINGLE", "Any one approver"
        PARALLEL = "PARALLEL", "Parallel approvals"

    class ResolverType(models.TextChoices):
        PERMISSION = "PERMISSION", "Permission-based"
        SPECIFIC_USERS = "SPECIFIC_USERS", "Specific users"

    workflow_version = models.ForeignKey(
        ApprovalWorkflowVersion,
        on_delete=models.PROTECT,
        related_name="steps",
    )
    sequence = models.PositiveIntegerField()
    name = models.CharField(max_length=180)
    approval_mode = models.CharField(
        max_length=20,
        choices=ApprovalMode.choices,
        default=ApprovalMode.SINGLE,
    )
    resolver_type = models.CharField(max_length=30, choices=ResolverType.choices)
    required_permission_code = models.CharField(max_length=160, blank=True)
    specific_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="specific_approval_steps",
    )
    scope_logic = models.CharField(max_length=30, default="COMPANY")
    minimum_approvals = models.PositiveIntegerField(default=1)
    allow_reject = models.BooleanField(default=True)
    allow_return_for_changes = models.BooleanField(default=True)
    sla_duration = models.DurationField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["workflow_version", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow_version", "sequence"],
                name="unique_approval_step_sequence",
            ),
            models.CheckConstraint(
                condition=models.Q(sequence__gt=0),
                name="positive_approval_step_sequence",
            ),
            models.CheckConstraint(
                condition=models.Q(minimum_approvals__gt=0),
                name="positive_minimum_approvals",
            ),
        ]

    def clean(self):
        errors = {}
        if self.workflow_version_id and self.workflow_version.status != ApprovalWorkflowVersion.Status.DRAFT:
            errors["workflow_version"] = "Only draft workflow versions can be configured."
        if self.resolver_type == self.ResolverType.PERMISSION and not self.required_permission_code:
            errors["required_permission_code"] = "Choose the permission used to resolve approvers."
        if self.resolver_type != self.ResolverType.PERMISSION and self.required_permission_code:
            errors["required_permission_code"] = "Permission is only used by permission-based steps."
        if self.approval_mode == self.ApprovalMode.SINGLE and self.minimum_approvals != 1:
            errors["minimum_approvals"] = "A single-approver step requires one approval."
        if self.scope_logic != "COMPANY":
            errors["scope_logic"] = "Phase 1 supports company-scoped approval resolution."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.workflow_version.status != ApprovalWorkflowVersion.Status.DRAFT:
            raise ValidationError("An activated workflow step cannot be deleted.")
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.sequence}. {self.name}"

    @property
    def company_id(self):
        return self.workflow_version.workflow.company_id


class ApprovalCondition(TimeStampedModel):
    class Operator(models.TextChoices):
        EQ = "EQ", "Equals"
        NE = "NE", "Does not equal"
        GT = "GT", "Greater than"
        GTE = "GTE", "Greater than or equal"
        LT = "LT", "Less than"
        LTE = "LTE", "Less than or equal"
        IN = "IN", "In list"

    workflow_version = models.ForeignKey(
        ApprovalWorkflowVersion,
        on_delete=models.PROTECT,
        related_name="conditions",
    )
    field = models.CharField(max_length=100)
    operator = models.CharField(max_length=10, choices=Operator.choices)
    value = models.JSONField()

    class Meta:
        ordering = ["workflow_version", "created_at"]

    def clean(self):
        if self.workflow_version_id:
            if self.workflow_version.status != ApprovalWorkflowVersion.Status.DRAFT:
                raise ValidationError({"workflow_version": "Only draft versions can be configured."})
            registration = registered_entity(self.workflow_version.workflow.entity_type, "approvals")
            if self.field not in registration.condition_fields:
                raise ValidationError({"field": "This field is not approved for workflow conditions."})
        if self.operator == self.Operator.IN and not isinstance(self.value, list):
            raise ValidationError({"value": "The IN operator requires a list value."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.workflow_version.status != ApprovalWorkflowVersion.Status.DRAFT:
            raise ValidationError("An activated workflow condition cannot be deleted.")
        return super().delete(*args, **kwargs)

    @property
    def company_id(self):
        return self.workflow_version.workflow.company_id


class ApprovalRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        RETURNED_FOR_CHANGES = "RETURNED_FOR_CHANGES", "Returned for changes"
        CANCELLED = "CANCELLED", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="approval_requests")
    workflow_version = models.ForeignKey(
        ApprovalWorkflowVersion,
        on_delete=models.PROTECT,
        related_name="requests",
    )
    workflow_name = models.CharField(max_length=180)
    workflow_version_number = models.PositiveIntegerField()
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=100)
    entity_reference = models.CharField(max_length=250)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="submitted_approval_requests",
    )
    requested_by_name = models.CharField(max_length=200)
    requested_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    current_step = models.ForeignKey(
        "ApprovalStepInstance",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_for_requests",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_approval_requests",
    )
    submission_comment = models.TextField(blank=True)
    snapshot_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["company", "status", "-requested_at"], name="approval_request_queue_idx"),
            models.Index(fields=["entity_type", "entity_id"], name="approval_request_entity_idx"),
            models.Index(fields=["requested_by", "-requested_at"], name="approval_request_submitter_idx"),
        ]

    def __str__(self):
        return f"{self.workflow_name} - {self.entity_reference}"


class ApprovalStepInstance(TimeStampedModel):
    class Status(models.TextChoices):
        WAITING = "WAITING", "Waiting"
        OPEN = "OPEN", "Needs approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        RETURNED_FOR_CHANGES = "RETURNED_FOR_CHANGES", "Returned for changes"
        CANCELLED = "CANCELLED", "Cancelled"

    request = models.ForeignKey(ApprovalRequest, on_delete=models.PROTECT, related_name="steps")
    definition = models.ForeignKey(
        ApprovalStepDefinition,
        on_delete=models.PROTECT,
        related_name="instances",
    )
    sequence = models.PositiveIntegerField()
    step_name = models.CharField(max_length=180)
    approval_mode = models.CharField(max_length=20, choices=ApprovalStepDefinition.ApprovalMode.choices)
    minimum_approvals = models.PositiveIntegerField(default=1)
    allow_reject = models.BooleanField(default=True)
    allow_return_for_changes = models.BooleanField(default=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.WAITING)
    opened_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    resolution_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["request", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["request", "sequence"],
                name="unique_approval_request_step",
            )
        ]

    def __str__(self):
        return f"{self.request} - {self.step_name}"


class ApprovalAssignment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Needs action"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        RETURNED_FOR_CHANGES = "RETURNED_FOR_CHANGES", "Returned for changes"
        SKIPPED = "SKIPPED", "No longer required"
        CANCELLED = "CANCELLED", "Cancelled"

    step = models.ForeignKey(ApprovalStepInstance, on_delete=models.PROTECT, related_name="assignments")
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="approval_assignments",
    )
    approver_name = models.CharField(max_length=200)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ["step", "approver_name"]
        constraints = [
            models.UniqueConstraint(fields=["step", "approver"], name="unique_approval_step_approver")
        ]


class ApprovalDecision(TimeStampedModel):
    class Decision(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        RETURNED_FOR_CHANGES = "RETURNED_FOR_CHANGES", "Returned for changes"

    step = models.ForeignKey(ApprovalStepInstance, on_delete=models.PROTECT, related_name="decisions")
    assignment = models.OneToOneField(
        ApprovalAssignment,
        on_delete=models.PROTECT,
        related_name="decision_record",
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="approval_decisions",
    )
    decided_by_name = models.CharField(max_length=200)
    decision = models.CharField(max_length=30, choices=Decision.choices)
    comment = models.TextField(blank=True)
    decided_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["decided_at"]
