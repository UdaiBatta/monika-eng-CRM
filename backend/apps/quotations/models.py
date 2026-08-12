from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.approvals.models import ApprovalRequest
from apps.core.models import TimeStampedModel, VersionedModel
from apps.crm.models import Customer, CustomerContact
from apps.documents.models import Document, DocumentCategory
from apps.enquiries.models import Enquiry
from apps.estimation.models import CommercialEstimate
from apps.masters.models import Currency
from apps.organization.models import Company, Employee


class ValidatedModel(TimeStampedModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Quotation(ValidatedModel):
    class Path(models.TextChoices):
        STANDARD = "STANDARD", "Standard quotation"
        QUICK = "QUICK", "Quick quotation"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        IN_APPROVAL = "IN_APPROVAL", "In approval"
        APPROVED = "APPROVED", "Approved"
        READY_TO_SEND = "READY_TO_SEND", "Ready to send"
        SENT = "SENT", "Sent"
        UNDER_NEGOTIATION = "UNDER_NEGOTIATION", "Under negotiation"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"
        READY_FOR_SALES_ORDER = "READY_FOR_SALES_ORDER", "Ready for Sales Order"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="quotations")
    quotation_number = models.CharField(max_length=80)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="quotations")
    customer_contact = models.ForeignKey(
        CustomerContact, on_delete=models.PROTECT, related_name="quotations", null=True, blank=True
    )
    enquiry = models.ForeignKey(
        Enquiry, on_delete=models.PROTECT, related_name="quotations", null=True, blank=True
    )
    estimate = models.ForeignKey(
        CommercialEstimate,
        on_delete=models.PROTECT,
        related_name="quotations",
        null=True,
        blank=True,
    )
    path = models.CharField(max_length=20, choices=Path.choices)
    quick_reason = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    owner = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="owned_quotations")
    current_revision = models.ForeignKey(
        "QuotationRevision",
        on_delete=models.PROTECT,
        related_name="current_for_quotations",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_quotations",
        null=True,
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "quotation_number"], name="unique_company_quotation_number"
            )
        ]
        indexes = [
            models.Index(fields=["company", "status", "-updated_at"], name="quotation_queue_idx"),
            models.Index(fields=["customer", "-created_at"], name="quotation_customer_idx"),
            models.Index(fields=["owner", "status"], name="quotation_owner_idx"),
        ]

    def clean(self):
        errors = {}
        if self.customer_id and self.customer.company_id != self.company_id:
            errors["customer"] = "Customer must belong to this company."
        if self.customer_contact_id and self.customer_contact.customer_id != self.customer_id:
            errors["customer_contact"] = "Contact must belong to this customer."
        if self.enquiry_id and (
            self.enquiry.company_id != self.company_id or self.enquiry.customer_id != self.customer_id
        ):
            errors["enquiry"] = "Enquiry must belong to this customer and company."
        if self.owner_id and self.owner.company_id != self.company_id:
            errors["owner"] = "Owner must belong to this company."
        if self.path == self.Path.QUICK and not self.quick_reason.strip():
            errors["quick_reason"] = "Explain why the quick quotation path is appropriate."
        if self.path == self.Path.STANDARD and not self.estimate_id:
            errors["estimate"] = "Standard quotations require an approved estimate."
        if self.estimate_id and (
            self.estimate.company_id != self.company_id
            or (self.enquiry_id and self.estimate.enquiry_id != self.enquiry_id)
        ):
            errors["estimate"] = "Estimate must belong to this quotation's company and enquiry."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.quotation_number


class QuotationRevision(VersionedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        IN_APPROVAL = "IN_APPROVAL", "In approval"
        APPROVED = "APPROVED", "Approved"
        READY_TO_SEND = "READY_TO_SEND", "Ready to send"
        SENT = "SENT", "Sent"
        SUPERSEDED = "SUPERSEDED", "Superseded"
        RETURNED = "RETURNED", "Returned for changes"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    quotation = models.ForeignKey(Quotation, on_delete=models.PROTECT, related_name="revisions")
    revision_number = models.PositiveIntegerField()
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="quotation_revisions")
    issue_date = models.DateField(default=timezone.localdate)
    valid_until = models.DateField(null=True, blank=True)
    introduction = models.TextField(blank=True)
    scope = models.TextField(blank=True)
    inclusions = models.TextField(blank=True)
    exclusions = models.TextField(blank=True)
    assumptions = models.TextField(blank=True)
    payment_terms = models.TextField(blank=True)
    delivery_terms = models.TextField(blank=True)
    warranty_terms = models.TextField(blank=True)
    freight_terms = models.TextField(blank=True)
    customer_notes = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    discount_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    taxable_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    grand_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    estimate_snapshot = models.JSONField(default=dict, blank=True)
    commercial_snapshot = models.JSONField(default=dict, blank=True)
    frozen_at = models.DateTimeField(null=True, blank=True)
    frozen_reason = models.CharField(max_length=250, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_quotation_revisions",
        null=True,
    )
    approval_request = models.OneToOneField(
        ApprovalRequest,
        on_delete=models.PROTECT,
        related_name="quotation_revision",
        null=True,
        blank=True,
    )
    supersedes = models.OneToOneField(
        "self", on_delete=models.PROTECT, related_name="superseded_by", null=True, blank=True
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="sent_quotation_revisions",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["quotation", "-revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["quotation", "revision_number"], name="unique_quotation_revision"
            ),
            models.CheckConstraint(
                condition=models.Q(revision_number__gt=0), name="positive_quotation_revision"
            ),
            models.CheckConstraint(
                condition=models.Q(grand_total__gte=0), name="nonnegative_quotation_total"
            ),
        ]

    @property
    def company_id(self):
        return self.quotation.company_id

    def __str__(self):
        return f"{self.quotation.quotation_number} / Rev {self.revision_number}"


class QuotationLine(ValidatedModel):
    revision = models.ForeignKey(QuotationRevision, on_delete=models.PROTECT, related_name="lines")
    line_number = models.PositiveIntegerField()
    item_code = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=1000)
    quantity = models.DecimalField(
        max_digits=18, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))]
    )
    unit_of_measure = models.CharField(max_length=40, default="NOS")
    unit_price = models.DecimalField(
        max_digits=18, decimal_places=4, validators=[MinValueValidator(Decimal("0"))]
    )
    discount_percent = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    tax_percent = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    line_subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    discount_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    taxable_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    is_optional = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["line_number"]
        constraints = [
            models.UniqueConstraint(fields=["revision", "line_number"], name="unique_quotation_line"),
            models.CheckConstraint(condition=models.Q(line_number__gt=0), name="positive_quote_line"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="positive_quote_quantity"),
        ]

    @property
    def company_id(self):
        return self.revision.company_id

    def save(self, *args, **kwargs):
        quantum = Decimal("0.01")
        self.line_subtotal = (self.quantity * self.unit_price).quantize(quantum, ROUND_HALF_UP)
        self.discount_amount = (
            self.line_subtotal * self.discount_percent / Decimal("100")
        ).quantize(quantum, ROUND_HALF_UP)
        self.taxable_amount = self.line_subtotal - self.discount_amount
        self.tax_amount = (
            self.taxable_amount * self.tax_percent / Decimal("100")
        ).quantize(quantum, ROUND_HALF_UP)
        self.total_amount = self.taxable_amount + self.tax_amount
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.revision} / {self.line_number}"


class QuotationTemplate(ValidatedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="quotation_templates")
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=180)
    source_document = models.ForeignKey(
        Document, on_delete=models.PROTECT, related_name="quotation_templates"
    )
    output_category = models.ForeignKey(
        DocumentCategory, on_delete=models.PROTECT, related_name="quotation_templates"
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["company", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"], name="unique_quotation_template_code"
            )
        ]

    def clean(self):
        if self.source_document_id and self.source_document.company_id != self.company_id:
            raise ValidationError({"source_document": "Template document must belong to this company."})
        if self.output_category_id and self.output_category.company_id != self.company_id:
            raise ValidationError({"output_category": "Output category must belong to this company."})

    def __str__(self):
        return f"{self.company.code} - {self.name}"


class QuotationTextTemplate(ValidatedModel):
    class Section(models.TextChoices):
        INTRODUCTION = "INTRODUCTION", "Introduction"
        SCOPE = "SCOPE", "Scope"
        INCLUSIONS = "INCLUSIONS", "Inclusions"
        EXCLUSIONS = "EXCLUSIONS", "Exclusions"
        ASSUMPTIONS = "ASSUMPTIONS", "Assumptions"
        PAYMENT = "PAYMENT", "Payment terms"
        DELIVERY = "DELIVERY", "Delivery terms"
        WARRANTY = "WARRANTY", "Warranty terms"
        FREIGHT = "FREIGHT", "Freight terms"

    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name="quotation_text_templates"
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=180)
    section = models.CharField(max_length=30, choices=Section.choices)
    content = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company", "section", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"], name="unique_quote_text_template_code"
            )
        ]


class QuotationGeneratedDocument(TimeStampedModel):
    class Status(models.TextChoices):
        COMPLETE = "COMPLETE", "Word and PDF available"
        WORD_ONLY = "WORD_ONLY", "Word available; PDF failed"

    revision = models.ForeignKey(
        QuotationRevision, on_delete=models.PROTECT, related_name="generated_documents"
    )
    template = models.ForeignKey(
        QuotationTemplate, on_delete=models.PROTECT, related_name="generated_documents"
    )
    docx_document = models.ForeignKey(
        Document, on_delete=models.PROTECT, related_name="generated_quotation_docx"
    )
    pdf_document = models.ForeignKey(
        Document,
        on_delete=models.PROTECT,
        related_name="generated_quotation_pdf",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    context_snapshot = models.JSONField(default=dict)
    pdf_error = models.CharField(max_length=500, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="generated_quotation_documents",
        null=True,
    )

    class Meta:
        ordering = ["-created_at"]

    @property
    def company_id(self):
        return self.revision.company_id


class QuotationCommunication(ValidatedModel):
    class Channel(models.TextChoices):
        PHONE = "PHONE", "Phone"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        EMAIL = "EMAIL", "Email"
        PRINT = "PRINT", "Print / hand delivery"
        IN_PERSON = "IN_PERSON", "In person"
        OTHER = "OTHER", "Other"

    class Direction(models.TextChoices):
        OUTBOUND = "OUTBOUND", "Sent to customer"
        INBOUND = "INBOUND", "Received from customer"

    revision = models.ForeignKey(
        QuotationRevision, on_delete=models.PROTECT, related_name="communications"
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    direction = models.CharField(max_length=20, choices=Direction.choices)
    occurred_at = models.DateTimeField(default=timezone.now)
    contact = models.ForeignKey(
        CustomerContact,
        on_delete=models.PROTECT,
        related_name="quotation_communications",
        null=True,
        blank=True,
    )
    summary = models.TextField()
    manual_reference = models.CharField(max_length=250, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="quotation_communications",
        null=True,
    )

    class Meta:
        ordering = ["-occurred_at"]

    @property
    def company_id(self):
        return self.revision.company_id


class QuotationNegotiation(ValidatedModel):
    quotation = models.ForeignKey(
        Quotation, on_delete=models.PROTECT, related_name="negotiations"
    )
    revision = models.ForeignKey(
        QuotationRevision, on_delete=models.PROTECT, related_name="negotiations"
    )
    occurred_at = models.DateTimeField(default=timezone.now)
    channel = models.CharField(max_length=20, choices=QuotationCommunication.Channel.choices)
    summary = models.TextField()
    customer_request = models.TextField(blank=True)
    our_response = models.TextField(blank=True)
    commercial_impact = models.TextField(blank=True)
    material_change = models.BooleanField(default=False)
    follow_up_at = models.DateTimeField(null=True, blank=True)
    follow_up_owner = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="quotation_negotiations",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="quotation_negotiations",
        null=True,
    )

    class Meta:
        ordering = ["-occurred_at"]

    @property
    def company_id(self):
        return self.quotation.company_id

    def clean(self):
        if self.revision_id and self.revision.quotation_id != self.quotation_id:
            raise ValidationError({"revision": "Revision must belong to this quotation."})
        if self.follow_up_owner_id and self.follow_up_owner.company_id != self.company_id:
            raise ValidationError({"follow_up_owner": "Follow-up owner must belong to this company."})


class CustomerCommercialConfirmation(ValidatedModel):
    class Method(models.TextChoices):
        VERBAL = "VERBAL", "Verbal confirmation"
        WHATSAPP = "WHATSAPP", "WhatsApp confirmation"
        EMAIL = "EMAIL", "Email confirmation"
        PURCHASE_ORDER = "PURCHASE_ORDER", "Purchase order"

    quotation = models.OneToOneField(
        Quotation, on_delete=models.PROTECT, related_name="commercial_confirmation"
    )
    revision = models.ForeignKey(
        QuotationRevision, on_delete=models.PROTECT, related_name="commercial_confirmations"
    )
    method = models.CharField(max_length=30, choices=Method.choices)
    confirmed_at = models.DateTimeField(default=timezone.now)
    confirmation_reference = models.CharField(max_length=250, blank=True)
    notes = models.TextField(blank=True)
    po_pending = models.BooleanField(default=False)
    po_number = models.CharField(max_length=120, blank=True)
    po_date = models.DateField(null=True, blank=True)
    po_document = models.ForeignKey(
        Document,
        on_delete=models.PROTECT,
        related_name="quotation_confirmations",
        null=True,
        blank=True,
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="confirmed_quotations",
        null=True,
    )
    ready_for_sales_order_at = models.DateTimeField(null=True, blank=True)
    ready_for_sales_order_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="sales_order_ready_confirmations",
        null=True,
        blank=True,
    )

    @property
    def company_id(self):
        return self.quotation.company_id

    def clean(self):
        errors = {}
        if self.revision_id and self.revision.quotation_id != self.quotation_id:
            errors["revision"] = "Revision must belong to this quotation."
        if self.po_document_id and self.po_document.company_id != self.company_id:
            errors["po_document"] = "Purchase-order document must belong to this company."
        if self.method == self.Method.PURCHASE_ORDER and not self.po_number.strip():
            errors["po_number"] = "Add the customer's purchase-order number."
        if errors:
            raise ValidationError(errors)
