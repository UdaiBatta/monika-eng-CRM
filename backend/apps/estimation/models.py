from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.approvals.models import ApprovalRequest
from apps.core.models import TimeStampedModel
from apps.engineering_reviews.models import EngineeringFeasibilityReview
from apps.enquiries.models import Enquiry
from apps.masters.models import Currency
from apps.organization.models import Company


class ValidatedModel(TimeStampedModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class CommercialEstimate(ValidatedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        IN_PREPARATION = "IN_PREPARATION", "In preparation"
        READY_FOR_REVIEW = "READY_FOR_REVIEW", "Ready for review"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending approval"
        APPROVED = "APPROVED", "Approved"
        RETURNED_FOR_CHANGES = "RETURNED_FOR_CHANGES", "Returned for changes"
        REJECTED = "REJECTED", "Rejected"
        SUPERSEDED = "SUPERSEDED", "Superseded"
        CANCELLED = "CANCELLED", "Cancelled"

    class PricingMethod(models.TextChoices):
        MARKUP = "MARKUP", "Cost plus markup"
        MARGIN = "MARGIN", "Target gross margin"
        MANUAL = "MANUAL", "Manual selling price"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="commercial_estimates")
    enquiry = models.ForeignKey(Enquiry, on_delete=models.PROTECT, related_name="commercial_estimates")
    engineering_review = models.ForeignKey(
        EngineeringFeasibilityReview,
        on_delete=models.PROTECT,
        related_name="commercial_estimates",
    )
    estimate_number = models.CharField(max_length=80)
    revision_number = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="commercial_estimates")
    pricing_method = models.CharField(
        max_length=20, choices=PricingMethod.choices, default=PricingMethod.MARKUP
    )
    markup_percent = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("999.9999"))],
    )
    target_margin_percent = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("99.9999"))],
    )
    manual_selling_price = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    total_cost = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    proposed_selling_price = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    gross_margin_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    gross_margin_percent = models.DecimalField(max_digits=9, decimal_places=4, default=Decimal("0"))
    category_totals = models.JSONField(default=dict, blank=True)
    assumptions = models.TextField(blank=True)
    exclusions = models.TextField(blank=True)
    commercial_notes = models.TextField(blank=True)
    technical_reference_summary = models.TextField(blank=True)
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="prepared_commercial_estimates",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_commercial_estimates",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="updated_commercial_estimates",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_commercial_estimates",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_commercial_estimates",
    )
    approval_request = models.OneToOneField(
        ApprovalRequest,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="commercial_estimate",
    )
    supersedes = models.OneToOneField(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="superseded_by"
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "estimate_number", "revision_number"],
                name="unique_estimate_revision",
            ),
            models.UniqueConstraint(
                fields=["enquiry"],
                condition=models.Q(is_current=True),
                name="unique_current_estimate",
            ),
            models.CheckConstraint(
                condition=models.Q(revision_number__gt=0), name="positive_estimate_revision"
            ),
            models.CheckConstraint(condition=models.Q(total_cost__gte=0), name="nonnegative_estimate_cost"),
            models.CheckConstraint(
                condition=models.Q(proposed_selling_price__gte=0),
                name="nonnegative_estimate_price",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status", "-created_at"], name="estimate_queue_idx"),
            models.Index(fields=["enquiry", "-revision_number"], name="estimate_revision_idx"),
            models.Index(fields=["prepared_by", "status"], name="estimate_preparer_idx"),
        ]

    def clean(self):
        errors = {}
        if self.enquiry_id and self.enquiry.company_id != self.company_id:
            errors["enquiry"] = "Enquiry must belong to the selected company."
        if self.engineering_review_id:
            if self.engineering_review.company_id != self.company_id:
                errors["engineering_review"] = "Engineering review must belong to this company."
            elif self.engineering_review.enquiry_id != self.enquiry_id:
                errors["engineering_review"] = "Engineering review must belong to this enquiry."
        if self.supersedes_id:
            if self.supersedes.enquiry_id != self.enquiry_id:
                errors["supersedes"] = "A revision can only supersede an estimate for the same enquiry."
            elif self.supersedes.revision_number >= self.revision_number:
                errors["supersedes"] = "The superseded estimate must be an earlier revision."
        if self.pricing_method == self.PricingMethod.MANUAL and self.manual_selling_price is None:
            errors["manual_selling_price"] = "Enter the manual selling price."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.estimate_number} / Rev {self.revision_number}"


class EstimateCostLine(ValidatedModel):
    class Category(models.TextChoices):
        MATERIAL = "MATERIAL", "Material"
        LABOUR = "LABOUR", "Labour"
        MACHINE = "MACHINE", "Machine"
        SUBCONTRACT = "SUBCONTRACT", "Subcontract"
        ENGINEERING = "ENGINEERING", "Engineering"
        OVERHEAD = "OVERHEAD", "Overhead"
        PACKING = "PACKING", "Packing"
        FREIGHT = "FREIGHT", "Freight"
        INSTALLATION = "INSTALLATION", "Installation"
        TRAVEL = "TRAVEL", "Travel"
        OTHER = "OTHER", "Other"
        CONTINGENCY = "CONTINGENCY", "Contingency"

    estimate = models.ForeignKey(CommercialEstimate, on_delete=models.PROTECT, related_name="cost_lines")
    line_number = models.PositiveIntegerField()
    category = models.CharField(max_length=24, choices=Category.choices)
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(
        max_digits=18, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))]
    )
    unit_of_measure = models.CharField(max_length=40, default="NOS")
    unit_cost = models.DecimalField(
        max_digits=18, decimal_places=4, validators=[MinValueValidator(Decimal("0"))]
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    source_reference = models.CharField(max_length=250, blank=True)
    notes = models.TextField(blank=True)
    is_optional = models.BooleanField(default=False)

    class Meta:
        ordering = ["line_number"]
        constraints = [
            models.UniqueConstraint(fields=["estimate", "line_number"], name="unique_estimate_line"),
            models.CheckConstraint(condition=models.Q(line_number__gt=0), name="positive_estimate_line"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="positive_estimate_quantity"),
            models.CheckConstraint(
                condition=models.Q(unit_cost__gte=0), name="nonnegative_estimate_unit_cost"
            ),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="nonnegative_estimate_amount"),
        ]
        indexes = [models.Index(fields=["estimate", "category"], name="estimate_line_category_idx")]

    def save(self, *args, **kwargs):
        places = self.estimate.currency.decimal_places if self.estimate_id else 2
        quantum = Decimal("1").scaleb(-places)
        self.amount = (self.quantity * self.unit_cost).quantize(quantum, rounding=ROUND_HALF_UP)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.estimate} / {self.line_number} - {self.description}"
