from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel
from apps.enquiries.models import Enquiry
from apps.organization.models import Company, Employee


class ValidatedModel(TimeStampedModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class EngineeringFeasibilityReview(ValidatedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_REVIEW = "IN_REVIEW", "In review"
        CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED", "Clarification required"
        FEASIBLE = "FEASIBLE", "Feasible"
        NOT_FEASIBLE = "NOT_FEASIBLE", "Not feasible"
        CANCELLED = "CANCELLED", "Cancelled"
        SUPERSEDED = "SUPERSEDED", "Superseded"

    class Result(models.TextChoices):
        FEASIBLE = "FEASIBLE", "Feasible"
        FEASIBLE_WITH_CONDITIONS = "FEASIBLE_WITH_CONDITIONS", "Feasible with conditions"
        NOT_FEASIBLE = "NOT_FEASIBLE", "Not feasible"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="engineering_reviews")
    enquiry = models.ForeignKey(Enquiry, on_delete=models.PROTECT, related_name="engineering_reviews")
    revision_number = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    assigned_engineer = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="engineering_feasibility_reviews",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_engineering_reviews",
        null=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="started_engineering_reviews",
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="completed_engineering_reviews",
        null=True,
        blank=True,
    )
    result = models.CharField(max_length=32, choices=Result.choices, blank=True)
    technical_summary = models.TextField(blank=True)
    feasibility_notes = models.TextField(blank=True)
    assumptions = models.TextField(blank=True)
    exclusions = models.TextField(blank=True)
    constraints = models.TextField(blank=True)
    risks = models.TextField(blank=True)
    special_materials = models.TextField(blank=True)
    outsourced_processes = models.TextField(blank=True)
    tooling_requirements = models.TextField(blank=True)
    testing_requirements = models.TextField(blank=True)
    customer_clarification_summary = models.TextField(blank=True)
    preliminary_drawing_notes = models.TextField(blank=True)
    preliminary_bom_notes = models.TextField(blank=True)
    preliminary_routing_notes = models.TextField(blank=True)
    engineering_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("999999.99"))],
    )
    manufacturing_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("999999.99"))],
    )
    lead_time_days = models.PositiveIntegerField(null=True, blank=True)
    completion_comment = models.TextField(blank=True)
    supersedes = models.OneToOneField(
        "self", on_delete=models.PROTECT, related_name="superseded_by", null=True, blank=True
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["enquiry", "revision_number"], name="unique_engineering_review_revision"
            ),
            models.UniqueConstraint(
                fields=["enquiry"],
                condition=models.Q(is_current=True),
                name="unique_current_engineering_review",
            ),
            models.CheckConstraint(
                condition=models.Q(revision_number__gt=0), name="positive_engineering_review_revision"
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status", "-created_at"], name="eng_review_queue_idx"),
            models.Index(fields=["assigned_engineer", "status"], name="eng_review_owner_idx"),
            models.Index(fields=["enquiry", "-revision_number"], name="eng_review_revision_idx"),
        ]

    def clean(self):
        errors = {}
        if self.enquiry_id and self.enquiry.company_id != self.company_id:
            errors["enquiry"] = "Enquiry must belong to the selected company."
        if self.assigned_engineer_id:
            if self.assigned_engineer.company_id != self.company_id:
                errors["assigned_engineer"] = "Engineer must belong to the selected company."
            elif (
                self.assigned_engineer.employment_status != Employee.EmploymentStatus.ACTIVE
                or not self.assigned_engineer.user_id
                or not self.assigned_engineer.user.is_active
            ):
                errors["assigned_engineer"] = "Assign an active engineer with a user account."
        if self.supersedes_id:
            if self.supersedes.enquiry_id != self.enquiry_id:
                errors["supersedes"] = "A review can only supersede an earlier revision of the same enquiry."
            elif self.supersedes.revision_number >= self.revision_number:
                errors["supersedes"] = "The superseded review must be an earlier revision."
        if self.completed_at and not self.completed_by_id:
            errors["completed_by"] = "Completed reviews must record who completed them."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.enquiry.enquiry_number} / Engineering Rev {self.revision_number}"


class EngineeringClarification(ValidatedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        RESPONDED = "RESPONDED", "Responded"
        CLOSED = "CLOSED", "Closed"
        CANCELLED = "CANCELLED", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="engineering_clarifications")
    review = models.ForeignKey(
        EngineeringFeasibilityReview, on_delete=models.PROTECT, related_name="clarifications"
    )
    subject = models.CharField(max_length=250)
    question = models.TextField()
    context = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    assigned_to = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="engineering_clarifications"
    )
    due_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="requested_engineering_clarifications",
        null=True,
    )
    requested_at = models.DateTimeField()
    response = models.TextField(blank=True)
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="responded_engineering_clarifications",
        null=True,
        blank=True,
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="closed_engineering_clarifications",
        null=True,
        blank=True,
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closure_comment = models.TextField(blank=True)

    class Meta:
        ordering = ["status", "due_at", "created_at"]
        indexes = [
            models.Index(fields=["review", "status"], name="eng_clarification_review_idx"),
            models.Index(fields=["assigned_to", "status", "due_at"], name="eng_clarification_owner_idx"),
        ]

    def clean(self):
        errors = {}
        if self.review_id and self.review.company_id != self.company_id:
            errors["review"] = "Review must belong to the selected company."
        if self.assigned_to_id:
            if self.assigned_to.company_id != self.company_id:
                errors["assigned_to"] = "Recipient must belong to the selected company."
            elif (
                self.assigned_to.employment_status != Employee.EmploymentStatus.ACTIVE
                or not self.assigned_to.user_id
                or not self.assigned_to.user.is_active
            ):
                errors["assigned_to"] = "Assign an active employee with a user account."
        if errors:
            raise ValidationError(errors)

    @property
    def enquiry(self):
        return self.review.enquiry

    def __str__(self):
        return f"{self.review} / {self.subject}"
