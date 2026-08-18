from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel, VersionedModel
from apps.crm.models import Customer, CustomerSite
from apps.documents.models import Document
from apps.organization.models import Company, Employee
from apps.sales.models import CustomerPurchaseOrderRevision, SalesOrder, SalesOrderRevision


class ValidatedModel(TimeStampedModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Project(VersionedModel):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class Status(models.TextChoices):
        NEW = "NEW", "New Project"
        HANDOFF_PENDING = "HANDOFF_PENDING", "Waiting for Engineering"
        ENGINEERING_REVIEW = "ENGINEERING_REVIEW", "Engineering Reviewing"
        ENGINEERING_ACCEPTED = "ENGINEERING_ACCEPTED", "Engineering Accepted"
        ON_HOLD = "ON_HOLD", "On Hold"
        CANCELLED = "CANCELLED", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="projects")
    project_number = models.CharField(max_length=80)
    sales_order = models.OneToOneField(SalesOrder, on_delete=models.PROTECT, related_name="project")
    current_sales_order_revision = models.ForeignKey(
        SalesOrderRevision, on_delete=models.PROTECT, related_name="project_commercial_baselines"
    )
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="projects")
    project_name = models.CharField(max_length=250)
    customer_project_reference = models.CharField(max_length=250, blank=True)
    customer_po_reference = models.CharField(max_length=250, blank=True)
    site = models.ForeignKey(
        CustomerSite, on_delete=models.PROTECT, related_name="projects", null=True, blank=True
    )
    sales_owner = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="sales_projects")
    project_owner = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="owned_projects", null=True, blank=True
    )
    engineering_owner = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="engineering_projects", null=True, blank=True
    )
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=28, choices=Status.choices, default=Status.NEW)
    planned_start = models.DateField(null=True, blank=True)
    target_completion = models.DateField(null=True, blank=True)
    customer_delivery_commitment = models.CharField(max_length=500, blank=True)
    internal_notes = models.TextField(blank=True)
    commercial_change_pending = models.BooleanField(default=False)
    previous_sales_order_revision = models.ForeignKey(
        SalesOrderRevision,
        on_delete=models.PROTECT,
        related_name="previous_project_commercial_baselines",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_projects",
        null=True,
    )

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "project_number"], name="unique_company_project_number"
            )
        ]
        indexes = [
            models.Index(fields=["company", "status", "-updated_at"], name="project_queue_idx"),
            models.Index(fields=["engineering_owner", "status"], name="project_engineering_idx"),
        ]

    def clean(self):
        errors = {}
        if self.sales_order_id and self.sales_order.company_id != self.company_id:
            errors["sales_order"] = "Sales Order must belong to this company."
        if self.current_sales_order_revision_id and (
            self.current_sales_order_revision.sales_order_id != self.sales_order_id
        ):
            errors["current_sales_order_revision"] = "Commercial baseline must belong to this Sales Order."
        if self.customer_id and self.customer.company_id != self.company_id:
            errors["customer"] = "Customer must belong to this company."
        if self.site_id and self.site.customer_id != self.customer_id:
            errors["site"] = "Site must belong to this customer."
        for field in ("sales_owner", "project_owner", "engineering_owner"):
            employee = getattr(self, field, None)
            if employee and employee.company_id != self.company_id:
                errors[field] = f"{field.replace('_', ' ').title()} must belong to this company."
        if errors:
            raise ValidationError(errors)

    @property
    def document_number(self):
        return self.project_number

    def __str__(self):
        return self.project_number


class ProjectEngineeringHandoff(VersionedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Preparing Handoff"
        READY_FOR_ENGINEERING = "READY_FOR_ENGINEERING", "Ready for Engineering"
        ENGINEERING_REVIEWING = "ENGINEERING_REVIEWING", "Engineering Reviewing"
        CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED", "Sales Clarification Needed"
        ACCEPTED = "ACCEPTED", "Engineering Accepted"

    project = models.OneToOneField(Project, on_delete=models.PROTECT, related_name="engineering_handoff")
    project_scope_summary = models.TextField(blank=True)
    technical_requirement_summary = models.TextField(blank=True)
    customer_specifications = models.TextField(blank=True)
    special_commercial_commitments = models.TextField(blank=True)
    technical_assumptions = models.TextField(blank=True)
    open_questions = models.TextField(blank=True)
    sales_notes = models.TextField(blank=True)
    assigned_engineer = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="assigned_project_handoffs", null=True, blank=True
    )
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="submitted_project_handoffs",
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    clarification_requested_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="accepted_project_handoffs",
        null=True,
        blank=True,
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_sales_order_revision = models.ForeignKey(
        SalesOrderRevision,
        on_delete=models.PROTECT,
        related_name="accepted_project_handoffs",
        null=True,
        blank=True,
    )
    accepted_customer_po_revision = models.ForeignKey(
        CustomerPurchaseOrderRevision,
        on_delete=models.PROTECT,
        related_name="accepted_project_handoffs",
        null=True,
        blank=True,
    )
    accepted_snapshot = models.JSONField(default=dict, blank=True)

    @property
    def company_id(self):
        return self.project.company_id

    def clean(self):
        if self.assigned_engineer_id and self.assigned_engineer.company_id != self.company_id:
            raise ValidationError({"assigned_engineer": "Engineer must belong to this company."})

    def __str__(self):
        return f"{self.project.project_number} engineering handoff"


class ProjectHandoffClarification(ValidatedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Waiting for Sales"
        ANSWERED = "ANSWERED", "Answered"
        CLOSED = "CLOSED", "Closed"

    handoff = models.ForeignKey(
        ProjectEngineeringHandoff, on_delete=models.PROTECT, related_name="clarifications"
    )
    question = models.TextField()
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="requested_project_clarifications",
        null=True,
    )
    respond_to = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="project_clarifications_to_answer"
    )
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    response = models.TextField(blank=True)
    response_document = models.ForeignKey(
        Document,
        on_delete=models.PROTECT,
        related_name="project_clarification_responses",
        null=True,
        blank=True,
    )
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="responded_project_clarifications",
        null=True,
        blank=True,
    )
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def company_id(self):
        return self.handoff.company_id

    def clean(self):
        errors = {}
        if self.respond_to_id and self.respond_to.company_id != self.company_id:
            errors["respond_to"] = "Sales employee must belong to this company."
        if self.response_document_id and self.response_document.company_id != self.company_id:
            errors["response_document"] = "Document must belong to this company."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Clarification for {self.handoff.project.project_number}"
