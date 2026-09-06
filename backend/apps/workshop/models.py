from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel, VersionedModel
from apps.inventory.models import Product
from apps.organization.models import Company, Employee, Warehouse
from apps.projects.models import Project


class ValidatedModel(VersionedModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PanelJob(ValidatedModel):
    class Status(models.TextChoices):
        REQUIREMENT_REVIEW = "REQUIREMENT_REVIEW", "Workshop Review"
        MATERIAL_PLANNING = "MATERIAL_PLANNING", "Material Planning"
        MATERIAL_SHORTAGE = "MATERIAL_SHORTAGE", "Material Shortage"
        READY_FOR_ASSEMBLY = "READY_FOR_ASSEMBLY", "Ready for Assembly"
        ASSEMBLY = "ASSEMBLY", "Assembly"
        WIRING = "WIRING", "Wiring"
        TESTING = "TESTING", "Testing"
        QUALITY_CHECK = "QUALITY_CHECK", "Quality Check"
        FITTING_INSTALLATION = "FITTING_INSTALLATION", "Fitting / Installation"
        HANDOVER = "HANDOVER", "Handover"
        CLOSED = "CLOSED", "Closed"
        ON_HOLD = "ON_HOLD", "On Hold"
        CANCELLED = "CANCELLED", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="panel_jobs")
    panel_job_number = models.CharField(max_length=80)
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="panel_jobs")
    panel_name = models.CharField(max_length=250)
    panel_reference = models.CharField(max_length=250, blank=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="panel_jobs")
    workshop_owner = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="owned_panel_jobs", null=True, blank=True
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.REQUIREMENT_REVIEW)
    requirement_notes = models.TextField(blank=True)
    target_completion = models.DateField(null=True, blank=True)
    quality_check_notes = models.TextField(blank=True)
    quality_passed = models.BooleanField(null=True, blank=True)
    handover_notes = models.TextField(blank=True)
    handed_over_at = models.DateTimeField(null=True, blank=True)
    handed_over_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="handed_over_panel_jobs",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_panel_jobs",
        null=True,
    )

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "panel_job_number"], name="unique_panel_job_number"
            )
        ]
        indexes = [
            models.Index(fields=["company", "status", "-updated_at"], name="panel_job_queue_idx"),
            models.Index(fields=["project"], name="panel_job_project_idx"),
            models.Index(fields=["workshop_owner", "status"], name="panel_job_owner_idx"),
        ]

    def clean(self):
        errors = {}
        if self.project_id and self.project.company_id != self.company_id:
            errors["project"] = "Project must belong to this company."
        if self.warehouse_id and self.warehouse.company_id != self.company_id:
            errors["warehouse"] = "Warehouse must belong to this company."
        if self.workshop_owner_id and self.workshop_owner.company_id != self.company_id:
            errors["workshop_owner"] = "Workshop owner must belong to this company."
        if errors:
            raise ValidationError(errors)

    @property
    def document_number(self):
        return self.panel_job_number

    def __str__(self):
        return self.panel_job_number


class PanelJobMaterialLine(ValidatedModel):
    panel_job = models.ForeignKey(PanelJob, on_delete=models.PROTECT, related_name="material_lines")
    line_number = models.PositiveIntegerField()
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="panel_job_material_lines")
    required_quantity = models.DecimalField(
        max_digits=18, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))]
    )
    reserved_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))
    issued_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))
    consumed_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))
    returned_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))
    notes = models.CharField(max_length=250, blank=True)

    class Meta:
        ordering = ["line_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["panel_job", "line_number"], name="unique_panel_job_material_line"
            ),
            models.CheckConstraint(
                condition=models.Q(line_number__gt=0), name="positive_panel_job_line_number"
            ),
            models.CheckConstraint(
                condition=models.Q(required_quantity__gt=0), name="positive_panel_job_required_quantity"
            ),
        ]

    @property
    def company_id(self):
        return self.panel_job.company_id

    @property
    def shortage_quantity(self):
        shortfall = self.required_quantity - self.reserved_quantity
        return shortfall if shortfall > 0 else Decimal("0")

    def clean(self):
        if self.product_id and self.product.company_id != self.company_id:
            raise ValidationError({"product": "Product must belong to this company."})

    def __str__(self):
        return f"{self.panel_job} / {self.line_number}"


class PanelJobStageEvent(TimeStampedModel):
    """Immutable log of stage transitions (Assembly, Wiring, Testing, ...)."""

    panel_job = models.ForeignKey(PanelJob, on_delete=models.PROTECT, related_name="stage_events")
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24)
    notes = models.TextField(blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="panel_job_stage_events", null=True
    )
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [models.Index(fields=["panel_job", "-occurred_at"], name="panel_job_stage_idx")]

    def __str__(self):
        return f"{self.panel_job} · {self.from_status} → {self.to_status}"
