from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.masters.models import Currency, PaymentTerm, TaxRate
from apps.organization.models import Company, Employee

validate_gstin = RegexValidator(
    regex=r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$",
    message="Enter a valid 15-character GSTIN.",
)
validate_pan = RegexValidator(
    regex=r"^[A-Z]{5}\d{4}[A-Z]$",
    message="Enter a valid 10-character PAN.",
)


class ValidatedModel(TimeStampedModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Customer(ValidatedModel):
    class CustomerType(models.TextChoices):
        ORGANIZATION = "ORGANIZATION", "Organization"
        INDIVIDUAL = "INDIVIDUAL", "Individual"
        GOVERNMENT = "GOVERNMENT", "Government"
        DEALER = "DEALER", "Dealer / channel partner"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PROSPECT = "PROSPECT", "Prospect"
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        BLOCKED = "BLOCKED", "Blocked"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="customers")
    customer_code = models.CharField(max_length=80)
    legal_name = models.CharField(max_length=250)
    trade_name = models.CharField(max_length=250, blank=True)
    customer_type = models.CharField(
        max_length=20,
        choices=CustomerType.choices,
        default=CustomerType.ORGANIZATION,
    )
    gstin = models.CharField(max_length=15, blank=True, validators=[validate_gstin])
    pan = models.CharField(max_length=10, blank=True, validators=[validate_pan])
    cin = models.CharField(max_length=21, blank=True)
    industry = models.CharField(max_length=160, blank=True)
    website = models.URLField(blank=True)
    primary_email = models.EmailField(blank=True)
    primary_phone = models.CharField(max_length=30, blank=True)
    account_manager = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="managed_customers",
        null=True,
        blank=True,
    )
    credit_limit = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    payment_term = models.ForeignKey(
        PaymentTerm,
        on_delete=models.PROTECT,
        related_name="customers",
        null=True,
        blank=True,
    )
    default_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="customers",
    )
    default_tax = models.ForeignKey(
        TaxRate,
        on_delete=models.PROTECT,
        related_name="customers",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROSPECT)
    source = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_customers",
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="updated_customers",
        null=True,
    )

    class Meta:
        ordering = ["legal_name", "customer_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "customer_code"],
                name="unique_company_customer_code",
            ),
            models.UniqueConstraint(
                fields=["company", "gstin"],
                condition=~models.Q(gstin=""),
                name="unique_company_customer_gstin",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"], name="crm_customer_status_idx"),
            models.Index(fields=["company", "legal_name"], name="crm_customer_name_idx"),
            models.Index(fields=["account_manager", "status"], name="crm_customer_owner_idx"),
        ]

    def clean(self):
        errors = {}
        for field in ("account_manager", "payment_term", "default_tax"):
            related = getattr(self, field, None)
            if related and related.company_id != self.company_id:
                errors[field] = f"{field.replace('_', ' ').title()} must belong to the selected company."
        if self.credit_limit is not None and self.credit_limit < 0:
            errors["credit_limit"] = "Credit limit cannot be negative."
        self.gstin = self.gstin.strip().upper()
        self.pan = self.pan.strip().upper()
        self.cin = self.cin.strip().upper()
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.gstin = self.gstin.strip().upper()
        self.pan = self.pan.strip().upper()
        self.cin = self.cin.strip().upper()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer_code} - {self.legal_name}"


class CustomerContact(ValidatedModel):
    class ContactMethod(models.TextChoices):
        PHONE = "PHONE", "Phone"
        EMAIL = "EMAIL", "Email"
        WHATSAPP = "WHATSAPP", "WhatsApp"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="contacts")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=120, blank=True)
    department = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    alternate_phone = models.CharField(max_length=30, blank=True)
    is_primary = models.BooleanField(default=False)
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=ContactMethod.choices,
        blank=True,
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["customer", "-is_primary", "first_name", "last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer"],
                condition=models.Q(is_primary=True, is_active=True),
                name="unique_active_primary_contact",
            )
        ]
        indexes = [models.Index(fields=["customer", "is_active"], name="crm_contact_active_idx")]

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def company(self):
        return self.customer.company

    @property
    def company_id(self):
        return self.customer.company_id

    def clean(self):
        if not self.email and not self.phone:
            raise ValidationError("Add at least an email address or phone number.")

    def __str__(self):
        return f"{self.display_name} - {self.customer.legal_name}"


class CustomerSite(ValidatedModel):
    class AddressType(models.TextChoices):
        BILLING = "BILLING", "Billing"
        SHIPPING = "SHIPPING", "Shipping"
        SITE = "SITE", "Site"
        REGISTERED = "REGISTERED", "Registered"
        OTHER = "OTHER", "Other"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="sites")
    address_type = models.CharField(max_length=20, choices=AddressType.choices)
    label = models.CharField(max_length=160)
    address_line_1 = models.CharField(max_length=250)
    address_line_2 = models.CharField(max_length=250, blank=True)
    city = models.CharField(max_length=120)
    district = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120)
    country = models.CharField(max_length=120, default="India")
    postal_code = models.CharField(max_length=20)
    gstin = models.CharField(max_length=15, blank=True, validators=[validate_gstin])
    contact = models.ForeignKey(
        CustomerContact,
        on_delete=models.PROTECT,
        related_name="sites",
        null=True,
        blank=True,
    )
    phone = models.CharField(max_length=30, blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["customer", "address_type", "-is_default", "label"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "address_type"],
                condition=models.Q(is_default=True, is_active=True),
                name="unique_active_default_site_type",
            )
        ]
        indexes = [models.Index(fields=["customer", "is_active"], name="crm_site_active_idx")]

    @property
    def company(self):
        return self.customer.company

    @property
    def company_id(self):
        return self.customer.company_id

    def clean(self):
        self.gstin = self.gstin.strip().upper()
        if self.contact_id and self.contact.customer_id != self.customer_id:
            raise ValidationError({"contact": "Contact must belong to this customer."})

    def save(self, *args, **kwargs):
        self.gstin = self.gstin.strip().upper()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer.legal_name} - {self.label}"


class CrmActivity(ValidatedModel):
    class ActivityType(models.TextChoices):
        CALL = "CALL", "Call"
        EMAIL = "EMAIL", "Email"
        MEETING = "MEETING", "Meeting"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        SITE_VISIT = "SITE_VISIT", "Site visit"
        NOTE = "NOTE", "Note"
        FOLLOW_UP = "FOLLOW_UP", "Follow-up"
        OTHER = "OTHER", "Other"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="crm_activities")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="activities")
    enquiry = models.ForeignKey(
        "enquiries.Enquiry",
        on_delete=models.PROTECT,
        related_name="activities",
        null=True,
        blank=True,
    )
    contact = models.ForeignKey(
        CustomerContact,
        on_delete=models.PROTECT,
        related_name="activities",
        null=True,
        blank=True,
    )
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    subject = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    activity_date = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="crm_activities",
        null=True,
    )
    next_follow_up_at = models.DateTimeField(null=True, blank=True)
    follow_up_owner = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="crm_follow_ups",
        null=True,
        blank=True,
    )
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="completed_crm_activities",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-activity_date", "-created_at"]
        indexes = [
            models.Index(fields=["company", "-activity_date"], name="crm_activity_company_idx"),
            models.Index(
                fields=["follow_up_owner", "status", "next_follow_up_at"],
                name="crm_followup_queue_idx",
            ),
            models.Index(fields=["customer", "-activity_date"], name="crm_activity_customer_idx"),
        ]

    @property
    def is_overdue(self):
        return bool(
            self.activity_type == self.ActivityType.FOLLOW_UP
            and self.status == self.Status.OPEN
            and self.next_follow_up_at
            and self.next_follow_up_at < timezone.now()
        )

    def clean(self):
        errors = {}
        if self.customer_id and self.customer.company_id != self.company_id:
            errors["customer"] = "Customer must belong to the selected company."
        if self.contact_id and self.contact.customer_id != self.customer_id:
            errors["contact"] = "Contact must belong to this customer."
        if self.enquiry_id and (
            self.enquiry.company_id != self.company_id
            or self.enquiry.customer_id != self.customer_id
        ):
            errors["enquiry"] = "Enquiry must belong to this customer and company."
        if self.follow_up_owner_id and self.follow_up_owner.company_id != self.company_id:
            errors["follow_up_owner"] = "Follow-up owner must belong to the selected company."
        if self.follow_up_owner_id and (
            not self.follow_up_owner.user_id
            or self.follow_up_owner.employment_status != Employee.EmploymentStatus.ACTIVE
            or not self.follow_up_owner.user.is_active
        ):
            errors["follow_up_owner"] = "Assign an active employee with a user account."
        if self.activity_type == self.ActivityType.FOLLOW_UP:
            if not self.next_follow_up_at:
                errors["next_follow_up_at"] = "Add the follow-up due date and time."
            if not self.follow_up_owner_id:
                errors["follow_up_owner"] = "Assign the follow-up to an employee."
        elif self.status == self.Status.OPEN:
            errors["status"] = "Only follow-up activities can remain open."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.subject}"
