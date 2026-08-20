from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.approvals.models import ApprovalRequest
from apps.core.models import TimeStampedModel, VersionedModel
from apps.crm.models import Customer, CustomerContact, CustomerSite
from apps.documents.models import Document
from apps.enquiries.models import Enquiry
from apps.masters.models import Currency
from apps.organization.models import Company, Employee
from apps.quotations.models import CustomerCommercialConfirmation, Quotation, QuotationRevision


class ValidatedModel(TimeStampedModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class CustomerPurchaseOrder(ValidatedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DIFFERENCE_REVIEW = "DIFFERENCE_REVIEW", "Differences Need Review"
        ACCEPTED_WITH_DIFFERENCES = "ACCEPTED_WITH_DIFFERENCES", "Accepted with Differences"
        SUPERSEDED = "SUPERSEDED", "Superseded"
        CANCELLED = "CANCELLED", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="customer_purchase_orders")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="purchase_orders")
    po_number = models.CharField(max_length=120)
    current_revision = models.ForeignKey(
        "CustomerPurchaseOrderRevision",
        on_delete=models.PROTECT,
        related_name="current_for_purchase_orders",
        null=True,
        blank=True,
    )
    quotation = models.ForeignKey(
        Quotation, on_delete=models.PROTECT, related_name="customer_purchase_orders", null=True, blank=True
    )
    confirmation = models.ForeignKey(
        CustomerCommercialConfirmation,
        on_delete=models.PROTECT,
        related_name="customer_purchase_orders",
        null=True,
        blank=True,
    )
    responsible_employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="responsible_customer_purchase_orders"
    )
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_customer_purchase_orders",
        null=True,
    )

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "customer", "po_number"],
                name="unique_customer_po_number",
            )
        ]
        indexes = [
            models.Index(fields=["company", "status", "-updated_at"], name="customer_po_queue_idx"),
            models.Index(fields=["customer", "po_number"], name="customer_po_lookup_idx"),
        ]

    def clean(self):
        errors = {}
        if self.customer_id and self.customer.company_id != self.company_id:
            errors["customer"] = "Customer must belong to this company."
        if self.quotation_id and (
            self.quotation.company_id != self.company_id or self.quotation.customer_id != self.customer_id
        ):
            errors["quotation"] = "Quotation must belong to this customer and company."
        if self.confirmation_id and self.confirmation.quotation.customer_id != self.customer_id:
            errors["confirmation"] = "Confirmation must belong to this customer."
        if self.responsible_employee_id and self.responsible_employee.company_id != self.company_id:
            errors["responsible_employee"] = "Responsible employee must belong to this company."
        if errors:
            raise ValidationError(errors)

    @property
    def document_number(self):
        return self.po_number

    def __str__(self):
        return self.po_number


class CustomerPurchaseOrderRevision(VersionedModel):
    class MatchStatus(models.TextChoices):
        NOT_REVIEWED = "NOT_REVIEWED", "Not Reviewed"
        MATCHES = "MATCHES", "Matches Quotation"
        DIFFERENCES = "DIFFERENCES", "Differences Need Review"
        ACCEPTED_DIFFERENCES = "ACCEPTED_DIFFERENCES", "Accepted with Differences"

    customer_purchase_order = models.ForeignKey(
        CustomerPurchaseOrder, on_delete=models.PROTECT, related_name="revisions"
    )
    revision_number = models.PositiveIntegerField()
    customer_revision_reference = models.CharField(max_length=120, blank=True)
    po_date = models.DateField()
    received_date = models.DateField(default=timezone.localdate)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="customer_po_revisions")
    stated_total = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    tax_information = models.JSONField(default=dict, blank=True)
    line_snapshot = models.JSONField(default=list, blank=True)
    delivery_information = models.TextField(blank=True)
    payment_terms = models.TextField(blank=True)
    warranty_terms = models.TextField(blank=True)
    customer_reference = models.CharField(max_length=250, blank=True)
    notes = models.TextField(blank=True)
    supporting_document = models.ForeignKey(
        Document,
        on_delete=models.PROTECT,
        related_name="customer_po_revisions",
        null=True,
        blank=True,
    )
    match_status = models.CharField(
        max_length=32, choices=MatchStatus.choices, default=MatchStatus.NOT_REVIEWED
    )
    variance_snapshot = models.JSONField(default=list, blank=True)
    supersedes = models.OneToOneField(
        "self", on_delete=models.PROTECT, related_name="superseded_by", null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_customer_po_revisions",
        null=True,
    )

    class Meta:
        ordering = ["customer_purchase_order", "-revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer_purchase_order", "revision_number"], name="unique_customer_po_revision"
            ),
            models.CheckConstraint(
                condition=models.Q(revision_number__gt=0), name="positive_customer_po_revision"
            ),
            models.CheckConstraint(
                condition=models.Q(stated_total__isnull=True) | models.Q(stated_total__gte=0),
                name="nonnegative_customer_po_total",
            ),
        ]

    @property
    def company_id(self):
        return self.customer_purchase_order.company_id

    def clean(self):
        allowed_currency_ids = {self.customer_purchase_order.customer.default_currency_id}
        if (
            self.customer_purchase_order.quotation_id
            and self.customer_purchase_order.quotation.current_revision_id
        ):
            allowed_currency_ids.add(self.customer_purchase_order.quotation.current_revision.currency_id)
        if self.currency_id and self.currency_id not in allowed_currency_ids:
            raise ValidationError({"currency": "Use the customer's or linked quotation's currency."})
        if self.supporting_document_id and self.supporting_document.company_id != self.company_id:
            raise ValidationError({"supporting_document": "Document must belong to this company."})

    def __str__(self):
        return f"{self.customer_purchase_order.po_number} / Rev {self.revision_number}"


class SalesOrder(ValidatedModel):
    class Mode(models.TextChoices):
        QUOTATION_BASED = "QUOTATION_BASED", "Quotation Based"
        DIRECT = "DIRECT", "Direct Sales Order"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Waiting for Approval"
        APPROVED = "APPROVED", "Approved"
        RELEASED = "RELEASED", "Released for Execution"
        ON_HOLD = "ON_HOLD", "On Hold"
        CANCELLED = "CANCELLED", "Cancelled"
        SUPERSEDED = "SUPERSEDED", "Replaced by New Revision"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="sales_orders")
    financial_year = models.CharField(max_length=12)
    sales_order_number = models.CharField(max_length=80)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="sales_orders")
    contact = models.ForeignKey(
        CustomerContact, on_delete=models.PROTECT, related_name="sales_orders", null=True, blank=True
    )
    site = models.ForeignKey(
        CustomerSite, on_delete=models.PROTECT, related_name="sales_orders", null=True, blank=True
    )
    enquiry = models.ForeignKey(
        Enquiry, on_delete=models.PROTECT, related_name="sales_orders", null=True, blank=True
    )
    accepted_quotation = models.OneToOneField(
        Quotation, on_delete=models.PROTECT, related_name="sales_order", null=True, blank=True
    )
    customer_confirmation = models.ForeignKey(
        CustomerCommercialConfirmation,
        on_delete=models.PROTECT,
        related_name="sales_orders",
        null=True,
        blank=True,
    )
    customer_purchase_order = models.ForeignKey(
        CustomerPurchaseOrder,
        on_delete=models.PROTECT,
        related_name="sales_orders",
        null=True,
        blank=True,
    )
    order_mode = models.CharField(max_length=24, choices=Mode.choices)
    current_revision = models.ForeignKey(
        "SalesOrderRevision",
        on_delete=models.PROTECT,
        related_name="current_for_sales_orders",
        null=True,
        blank=True,
    )
    responsible_sales_employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="responsible_sales_orders"
    )
    project_required = models.BooleanField(default=True)
    po_pending = models.BooleanField(default=False)
    direct_reason = models.CharField(max_length=80, blank=True)
    direct_reason_notes = models.TextField(blank=True)
    confirmation_channel = models.CharField(max_length=40, blank=True)
    confirmation_reference = models.CharField(max_length=250, blank=True)
    confirmation_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=28, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_sales_orders",
        null=True,
    )

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "sales_order_number"], name="unique_company_sales_order_number"
            )
        ]
        indexes = [
            models.Index(fields=["company", "status", "-updated_at"], name="sales_order_queue_idx"),
            models.Index(fields=["customer", "-created_at"], name="sales_order_customer_idx"),
            models.Index(fields=["responsible_sales_employee", "status"], name="sales_order_owner_idx"),
        ]

    def clean(self):
        errors = {}
        if self.customer_id and self.customer.company_id != self.company_id:
            errors["customer"] = "Customer must belong to this company."
        for field in ("contact", "site"):
            related = getattr(self, field, None)
            if related and related.customer_id != self.customer_id:
                errors[field] = f"{field.title()} must belong to this customer."
        if self.enquiry_id and (
            self.enquiry.company_id != self.company_id or self.enquiry.customer_id != self.customer_id
        ):
            errors["enquiry"] = "Enquiry must belong to this customer and company."
        if self.accepted_quotation_id and (
            self.accepted_quotation.company_id != self.company_id
            or self.accepted_quotation.customer_id != self.customer_id
        ):
            errors["accepted_quotation"] = "Quotation must belong to this customer and company."
        if self.customer_purchase_order_id and self.customer_purchase_order.customer_id != self.customer_id:
            errors["customer_purchase_order"] = "Customer PO must belong to this customer."
        if (
            self.responsible_sales_employee_id
            and self.responsible_sales_employee.company_id != self.company_id
        ):
            errors["responsible_sales_employee"] = "Responsible employee must belong to this company."
        if self.order_mode == self.Mode.QUOTATION_BASED and not self.accepted_quotation_id:
            errors["accepted_quotation"] = "Quotation-based orders require an accepted quotation."
        if self.order_mode == self.Mode.DIRECT and not self.direct_reason.strip():
            errors["direct_reason"] = "Choose a reason for this Direct Sales Order."
        if not self.po_pending and not self.customer_purchase_order_id and self.status != self.Status.DRAFT:
            errors["po_pending"] = "Link the Customer PO or mark it pending."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.sales_order_number


class SalesOrderRevision(VersionedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Waiting for Approval"
        APPROVED = "APPROVED", "Approved"
        RELEASED = "RELEASED", "Released for Execution"
        RETURNED = "RETURNED", "Returned for Changes"
        SUPERSEDED = "SUPERSEDED", "Replaced by New Revision"
        CANCELLED = "CANCELLED", "Cancelled"

    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name="revisions")
    revision_number = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=28, choices=Status.choices, default=Status.DRAFT)
    source_quotation_revision = models.ForeignKey(
        QuotationRevision,
        on_delete=models.PROTECT,
        related_name="sales_order_revisions",
        null=True,
        blank=True,
    )
    source_customer_po_revision = models.ForeignKey(
        CustomerPurchaseOrderRevision,
        on_delete=models.PROTECT,
        related_name="sales_order_revisions",
        null=True,
        blank=True,
    )
    customer_reference = models.CharField(max_length=250, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="sales_order_revisions")
    order_date = models.DateField(default=timezone.localdate)
    requested_delivery = models.DateField(null=True, blank=True)
    promised_delivery = models.DateField(null=True, blank=True)
    payment_terms = models.TextField(blank=True)
    delivery_terms = models.TextField(blank=True)
    warranty_terms = models.TextField(blank=True)
    freight_terms = models.TextField(blank=True)
    installation_terms = models.TextField(blank=True)
    scope = models.TextField(blank=True)
    exclusions = models.TextField(blank=True)
    customer_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    discount_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    taxable_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    grand_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    commercial_snapshot = models.JSONField(default=dict, blank=True)
    po_snapshot = models.JSONField(default=dict, blank=True)
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="prepared_sales_order_revisions",
        null=True,
    )
    approval_request = models.OneToOneField(
        ApprovalRequest,
        on_delete=models.PROTECT,
        related_name="sales_order_revision",
        null=True,
        blank=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_sales_order_revisions",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="released_sales_order_revisions",
        null=True,
        blank=True,
    )
    released_at = models.DateTimeField(null=True, blank=True)
    revision_reason = models.CharField(max_length=500, blank=True)
    supersedes = models.OneToOneField(
        "self", on_delete=models.PROTECT, related_name="superseded_by", null=True, blank=True
    )

    class Meta:
        ordering = ["sales_order", "-revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["sales_order", "revision_number"], name="unique_sales_order_revision"
            ),
            models.CheckConstraint(
                condition=models.Q(grand_total__gte=0), name="nonnegative_sales_order_total"
            ),
        ]

    @property
    def company_id(self):
        return self.sales_order.company_id

    def clean(self):
        allowed_currency_ids = {self.sales_order.customer.default_currency_id}
        if self.source_quotation_revision_id:
            allowed_currency_ids.add(self.source_quotation_revision.currency_id)
        if self.source_customer_po_revision_id:
            allowed_currency_ids.add(self.source_customer_po_revision.currency_id)
        if self.currency_id and self.currency_id not in allowed_currency_ids:
            raise ValidationError({"currency": "Use the customer's linked commercial currency."})
        if self.source_quotation_revision_id and (
            self.source_quotation_revision.quotation_id != self.sales_order.accepted_quotation_id
        ):
            raise ValidationError(
                {"source_quotation_revision": "Quotation revision does not match this order."}
            )

    def __str__(self):
        return f"{self.sales_order.sales_order_number} / R{self.revision_number}"


class SalesOrderLine(ValidatedModel):
    revision = models.ForeignKey(SalesOrderRevision, on_delete=models.PROTECT, related_name="lines")
    line_number = models.PositiveIntegerField()
    quotation_line_id = models.UUIDField(null=True, blank=True)
    customer_po_line_reference = models.CharField(max_length=120, blank=True)
    description = models.CharField(max_length=1000)
    long_description = models.TextField(blank=True)
    customer_item_reference = models.CharField(max_length=120, blank=True)
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
    requested_delivery_date = models.DateField(null=True, blank=True)
    promised_delivery_date = models.DateField(null=True, blank=True)
    delivery_text = models.CharField(max_length=250, blank=True)
    customer_visible_note = models.TextField(blank=True)
    internal_note = models.TextField(blank=True)
    project_scope_category = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["line_number"]
        constraints = [
            models.UniqueConstraint(fields=["revision", "line_number"], name="unique_sales_order_line"),
            models.CheckConstraint(condition=models.Q(line_number__gt=0), name="positive_sales_order_line"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="positive_sales_order_quantity"),
        ]

    @property
    def company_id(self):
        return self.revision.company_id

    def save(self, *args, **kwargs):
        quantum = Decimal("0.01")
        self.line_subtotal = (self.quantity * self.unit_price).quantize(quantum, ROUND_HALF_UP)
        self.discount_amount = (self.line_subtotal * self.discount_percent / Decimal("100")).quantize(
            quantum, ROUND_HALF_UP
        )
        self.taxable_amount = self.line_subtotal - self.discount_amount
        self.tax_amount = (self.taxable_amount * self.tax_percent / Decimal("100")).quantize(
            quantum, ROUND_HALF_UP
        )
        self.total_amount = self.taxable_amount + self.tax_amount
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.revision} / {self.line_number}"
