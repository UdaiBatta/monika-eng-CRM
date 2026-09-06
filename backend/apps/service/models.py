from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel, VersionedModel
from apps.crm.models import Customer, CustomerContact, CustomerSite
from apps.inventory.models import Product
from apps.organization.models import Company, Employee


class ValidatedModel(VersionedModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Equipment(ValidatedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="service_equipment")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="equipment")
    site = models.ForeignKey(
        CustomerSite, on_delete=models.PROTECT, related_name="equipment", null=True, blank=True
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="customer_equipment", null=True, blank=True
    )
    equipment_name = models.CharField(max_length=250)
    make_model = models.CharField(max_length=250, blank=True)
    serial_number = models.CharField(max_length=120, blank=True)
    installation_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["customer__legal_name", "equipment_name"]
        indexes = [
            models.Index(fields=["company", "customer"], name="equipment_customer_idx"),
            models.Index(fields=["serial_number"], name="equipment_serial_idx"),
        ]

    @property
    def under_warranty(self):
        return bool(self.warranty_expiry and self.warranty_expiry >= timezone.localdate())

    def clean(self):
        errors = {}
        if self.customer_id and self.customer.company_id != self.company_id:
            errors["customer"] = "Customer must belong to this company."
        if self.site_id and self.site.customer_id != self.customer_id:
            errors["site"] = "Site must belong to this customer."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.equipment_name} ({self.serial_number})" if self.serial_number else self.equipment_name


class ServiceTicket(ValidatedModel):
    class Source(models.TextChoices):
        WEBSITE = "WEBSITE", "Website"
        INDIAMART = "INDIAMART", "IndiaMART"
        TRADEINDIA = "TRADEINDIA", "TradeIndia"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        EMAIL = "EMAIL", "Email"
        CALL = "CALL", "Call"
        WALK_IN = "WALK_IN", "Walk-in"
        REFERRAL = "REFERRAL", "Referral"
        MANUAL = "MANUAL", "Manual"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        ASSIGNED = "ASSIGNED", "Assigned"
        AWAITING_PARTS = "AWAITING_PARTS", "Awaiting Parts"
        UNDER_REPAIR = "UNDER_REPAIR", "Under Repair"
        AWAITING_CUSTOMER_APPROVAL = "AWAITING_CUSTOMER_APPROVAL", "Awaiting Customer Approval"
        READY_FOR_DISPATCH = "READY_FOR_DISPATCH", "Ready for Dispatch"
        CLOSED = "CLOSED", "Closed"
        CANCELLED = "CANCELLED", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="service_tickets")
    ticket_number = models.CharField(max_length=80)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="service_tickets")
    contact = models.ForeignKey(
        CustomerContact, on_delete=models.PROTECT, related_name="service_tickets", null=True, blank=True
    )
    equipment = models.ForeignKey(
        Equipment, on_delete=models.PROTECT, related_name="service_tickets", null=True, blank=True
    )
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    complaint = models.TextField()
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.NEW)
    technician = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="assigned_service_tickets", null=True, blank=True
    )
    scheduled_visit_at = models.DateTimeField(null=True, blank=True)
    diagnosis = models.TextField(blank=True)
    quotation = models.ForeignKey(
        "quotations.Quotation",
        on_delete=models.PROTECT,
        related_name="service_tickets",
        null=True,
        blank=True,
    )
    repair_notes = models.TextField(blank=True)
    warranty_claim = models.BooleanField(default=False)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    dispatch_reference = models.CharField(max_length=250, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="closed_service_tickets",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_service_tickets",
        null=True,
    )

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "ticket_number"], name="unique_service_ticket_number")
        ]
        indexes = [
            models.Index(fields=["company", "status", "-updated_at"], name="service_ticket_queue_idx"),
            models.Index(fields=["technician", "status"], name="service_ticket_technician_idx"),
            models.Index(fields=["customer", "-created_at"], name="service_ticket_customer_idx"),
        ]

    def clean(self):
        errors = {}
        if self.customer_id and self.customer.company_id != self.company_id:
            errors["customer"] = "Customer must belong to this company."
        if self.contact_id and self.contact.customer_id != self.customer_id:
            errors["contact"] = "Contact must belong to this customer."
        if self.equipment_id and self.equipment.customer_id != self.customer_id:
            errors["equipment"] = "Equipment must belong to this customer."
        if self.technician_id and self.technician.company_id != self.company_id:
            errors["technician"] = "Technician must belong to this company."
        if self.quotation_id and self.quotation.customer_id != self.customer_id:
            errors["quotation"] = "Quotation must belong to this customer."
        if errors:
            raise ValidationError(errors)

    @property
    def document_number(self):
        return self.ticket_number

    def __str__(self):
        return self.ticket_number


class ServiceJobLine(ValidatedModel):
    class LineType(models.TextChoices):
        PART = "PART", "Part"
        LABOUR = "LABOUR", "Labour"

    ticket = models.ForeignKey(ServiceTicket, on_delete=models.PROTECT, related_name="job_lines")
    line_number = models.PositiveIntegerField()
    line_type = models.CharField(max_length=10, choices=LineType.choices)
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="service_job_lines", null=True, blank=True
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    unit_price = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0"), validators=[MinValueValidator(Decimal("0"))]
    )
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    consumed_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))

    class Meta:
        ordering = ["line_number"]
        constraints = [
            models.UniqueConstraint(fields=["ticket", "line_number"], name="unique_service_job_line"),
            models.CheckConstraint(
                condition=models.Q(line_number__gt=0), name="positive_service_line_number"
            ),
        ]

    @property
    def company_id(self):
        return self.ticket.company_id

    def clean(self):
        errors = {}
        if self.line_type == self.LineType.PART and not self.product_id:
            errors["product"] = "Choose the product used for this part line."
        if self.product_id and self.product.company_id != self.company_id:
            errors["product"] = "Product must belong to this company."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        quantum = Decimal("0.01")
        self.total_amount = (self.quantity * self.unit_price).quantize(quantum, ROUND_HALF_UP)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket} / {self.line_number}"


class ServiceTicketStageEvent(TimeStampedModel):
    """Immutable log of Service Ticket status transitions."""

    ticket = models.ForeignKey(ServiceTicket, on_delete=models.PROTECT, related_name="stage_events")
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32)
    notes = models.TextField(blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="service_ticket_stage_events",
        null=True,
    )
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [models.Index(fields=["ticket", "-occurred_at"], name="service_ticket_stage_idx")]

    def __str__(self):
        return f"{self.ticket} · {self.from_status} → {self.to_status}"
