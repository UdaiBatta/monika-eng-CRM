from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

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
