from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.crm.models import Customer, CustomerContact, CustomerSite
from apps.masters.models import Currency, UnitOfMeasure
from apps.organization.models import Company, Employee


class ValidatedModel(TimeStampedModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Enquiry(ValidatedModel):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        RECEIVED = "RECEIVED", "Received"
        UNDER_REVIEW = "UNDER_REVIEW", "Under review"
        ENGINEERING_REVIEW = "ENGINEERING_REVIEW", "Engineering review"
        ESTIMATION = "ESTIMATION", "Estimation"
        ESTIMATION_COMPLETE = "ESTIMATION_COMPLETE", "Estimation complete"
        QUOTATION_PREPARATION = "QUOTATION_PREPARATION", "Quotation preparation"
        QUOTATION_SENT = "QUOTATION_SENT", "Quotation sent"
        NEGOTIATION = "NEGOTIATION", "Negotiation"
        WON = "WON", "Won"
        LOST = "LOST", "Lost"
        CANCELLED = "CANCELLED", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="enquiries")
    enquiry_number = models.CharField(max_length=80)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="enquiries")
    customer_contact = models.ForeignKey(
        CustomerContact,
        on_delete=models.PROTECT,
        related_name="enquiries",
        null=True,
        blank=True,
    )
    customer_site = models.ForeignKey(
        CustomerSite,
        on_delete=models.PROTECT,
        related_name="enquiries",
        null=True,
        blank=True,
    )
    source = models.CharField(max_length=160, blank=True)
    received_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)
    customer_reference = models.CharField(max_length=160, blank=True)
    subject = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    responsible_salesperson = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="sales_enquiries",
    )
    estimated_value = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="enquiries",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    lost_reason = models.CharField(max_length=500, blank=True)
    cancellation_reason = models.CharField(max_length=500, blank=True)
    competitor = models.CharField(max_length=250, blank=True)
    customer_feedback = models.TextField(blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="closed_enquiries",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_enquiries",
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="updated_enquiries",
        null=True,
    )

    class Meta:
        ordering = ["-received_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "enquiry_number"],
                name="unique_company_enquiry_number",
            )
        ]
        indexes = [
            models.Index(fields=["company", "status", "-received_date"], name="enquiry_stage_idx"),
            models.Index(fields=["customer", "status"], name="enquiry_customer_idx"),
            models.Index(fields=["responsible_salesperson", "status"], name="enquiry_owner_idx"),
            models.Index(fields=["company", "due_date"], name="enquiry_due_idx"),
        ]

    @property
    def is_overdue(self):
        return bool(
            self.due_date
            and self.due_date < timezone.localdate()
            and self.status not in {self.Status.WON, self.Status.LOST, self.Status.CANCELLED}
        )

    def clean(self):
        errors = {}
        if self.customer_id and self.customer.company_id != self.company_id:
            errors["customer"] = "Customer must belong to the selected company."
        if self.customer_contact_id and self.customer_contact.customer_id != self.customer_id:
            errors["customer_contact"] = "Contact must belong to this customer."
        if self.customer_site_id and self.customer_site.customer_id != self.customer_id:
            errors["customer_site"] = "Site must belong to this customer."
        if (
            self.responsible_salesperson_id
            and self.responsible_salesperson.company_id != self.company_id
        ):
            errors["responsible_salesperson"] = "Salesperson must belong to the selected company."
        if self.responsible_salesperson_id and (
            self.responsible_salesperson.employment_status != Employee.EmploymentStatus.ACTIVE
            or not self.responsible_salesperson.user_id
            or not self.responsible_salesperson.user.is_active
        ):
            errors["responsible_salesperson"] = "Assign an active salesperson with a user account."
        if self.estimated_value is not None and self.estimated_value < 0:
            errors["estimated_value"] = "Estimated value cannot be negative."
        if self.estimated_value is not None and not self.currency_id:
            errors["currency"] = "Choose a currency for the estimated value."
        if self.due_date and self.due_date < self.received_date:
            errors["due_date"] = "Due date cannot be before the received date."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.enquiry_number} - {self.subject}"


class EnquiryRequirement(ValidatedModel):
    class RequirementType(models.TextChoices):
        TECHNICAL = "TECHNICAL", "Technical"
        COMMERCIAL = "COMMERCIAL", "Commercial"
        DELIVERY = "DELIVERY", "Delivery"
        COMPLIANCE = "COMPLIANCE", "Compliance"
        OTHER = "OTHER", "Other"

    enquiry = models.ForeignKey(Enquiry, on_delete=models.PROTECT, related_name="requirements")
    requirement_type = models.CharField(max_length=20, choices=RequirementType.choices)
    title = models.CharField(max_length=250)
    description = models.TextField()
    is_mandatory = models.BooleanField(default=True)
    customer_specification_reference = models.CharField(max_length=250, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["enquiry", "requirement_type", "title"]
        indexes = [models.Index(fields=["enquiry", "requirement_type"], name="enquiry_requirement_idx")]

    @property
    def company(self):
        return self.enquiry.company

    @property
    def company_id(self):
        return self.enquiry.company_id

    def __str__(self):
        return self.title


class EnquiryItem(ValidatedModel):
    enquiry = models.ForeignKey(Enquiry, on_delete=models.PROTECT, related_name="items")
    line_number = models.PositiveIntegerField()
    description = models.CharField(max_length=500)
    customer_reference = models.CharField(max_length=160, blank=True)
    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name="enquiry_items")
    technical_specification = models.TextField(blank=True)
    requested_delivery = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["enquiry", "line_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["enquiry", "line_number"],
                name="unique_enquiry_item_line",
            ),
            models.CheckConstraint(
                condition=models.Q(line_number__gt=0),
                name="positive_enquiry_item_line",
            ),
        ]
        indexes = [models.Index(fields=["enquiry", "line_number"], name="enquiry_item_line_idx")]

    @property
    def company(self):
        return self.enquiry.company

    @property
    def company_id(self):
        return self.enquiry.company_id

    def __str__(self):
        return f"{self.enquiry.enquiry_number} / {self.line_number}"
