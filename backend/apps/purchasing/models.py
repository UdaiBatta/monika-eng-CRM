from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.approvals.models import ApprovalRequest
from apps.core.models import TimeStampedModel
from apps.inventory.models import Product, Supplier
from apps.masters.models import Currency
from apps.organization.models import Company, Employee, Warehouse


class ValidatedModel(TimeStampedModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PurchaseRequisition(ValidatedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Awaiting Approval"
        APPROVED = "APPROVED", "Approved"
        RETURNED = "RETURNED", "Returned for Changes"
        REJECTED = "REJECTED", "Rejected"
        CONVERTED = "CONVERTED", "Converted to Purchase Order"
        CANCELLED = "CANCELLED", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="purchase_requisitions")
    requisition_number = models.CharField(max_length=80)
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name="purchase_requisitions"
    )
    requested_by = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="purchase_requisitions")
    preferred_supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="purchase_requisitions", null=True, blank=True
    )
    justification = models.TextField(blank=True)
    required_by_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    approval_request = models.OneToOneField(
        ApprovalRequest, on_delete=models.PROTECT, related_name="purchase_requisition", null=True, blank=True
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_purchase_requisitions",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_purchase_requisitions",
        null=True,
    )

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "requisition_number"], name="unique_purchase_requisition_number"
            )
        ]
        indexes = [
            models.Index(fields=["company", "status", "-updated_at"], name="pr_queue_idx"),
        ]

    def clean(self):
        errors = {}
        if self.warehouse_id and self.warehouse.company_id != self.company_id:
            errors["warehouse"] = "Warehouse must belong to this company."
        if self.requested_by_id and self.requested_by.company_id != self.company_id:
            errors["requested_by"] = "Requested-by employee must belong to this company."
        if self.preferred_supplier_id and self.preferred_supplier.company_id != self.company_id:
            errors["preferred_supplier"] = "Supplier must belong to this company."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.requisition_number


class PurchaseRequisitionLine(ValidatedModel):
    requisition = models.ForeignKey(PurchaseRequisition, on_delete=models.PROTECT, related_name="lines")
    line_number = models.PositiveIntegerField()
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="requisition_lines")
    quantity = models.DecimalField(
        max_digits=18, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))]
    )
    notes = models.CharField(max_length=250, blank=True)

    class Meta:
        ordering = ["line_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["requisition", "line_number"], name="unique_purchase_requisition_line"
            ),
            models.CheckConstraint(condition=models.Q(line_number__gt=0), name="positive_pr_line_number"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="positive_pr_line_quantity"),
        ]

    @property
    def company_id(self):
        return self.requisition.company_id

    def clean(self):
        if self.product_id and self.product.company_id != self.company_id:
            raise ValidationError({"product": "Product must belong to this company."})

    def __str__(self):
        return f"{self.requisition} / {self.line_number}"


class PurchaseOrder(ValidatedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        AWAITING_APPROVAL = "AWAITING_APPROVAL", "Awaiting Approval"
        ORDERED = "ORDERED", "Ordered"
        PART_RECEIVED = "PART_RECEIVED", "Part Received"
        FULLY_RECEIVED = "FULLY_RECEIVED", "Fully Received"
        DELAYED = "DELAYED", "Delayed"
        CANCELLED = "CANCELLED", "Cancelled"
        CLOSED = "CLOSED", "Closed"

    class PaymentStatus(models.TextChoices):
        NOT_DUE = "NOT_DUE", "Not Due"
        PART_PAID = "PART_PAID", "Part Paid"
        PAID = "PAID", "Paid"
        OVERDUE = "OVERDUE", "Overdue"
        ON_HOLD = "ON_HOLD", "On Hold"
        DISPUTED = "DISPUTED", "Disputed"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="purchase_orders")
    po_number = models.CharField(max_length=80)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="purchase_orders")
    requisition = models.ForeignKey(
        PurchaseRequisition, on_delete=models.PROTECT, related_name="purchase_orders", null=True, blank=True
    )
    responsible_employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="responsible_purchase_orders"
    )
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="purchase_orders")
    order_date = models.DateField(default=timezone.localdate)
    expected_delivery_date = models.DateField(null=True, blank=True)
    payment_terms = models.TextField(blank=True)
    delivery_terms = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    grand_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    invoiced_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    paid_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    payment_due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.NOT_DUE
    )
    approval_request = models.OneToOneField(
        ApprovalRequest, on_delete=models.PROTECT, related_name="purchase_order", null=True, blank=True
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_purchase_orders",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_purchase_orders",
        null=True,
    )

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "po_number"], name="unique_purchase_order_number"),
            models.CheckConstraint(condition=models.Q(grand_total__gte=0), name="nonnegative_po_total"),
        ]
        indexes = [
            models.Index(fields=["company", "status", "-updated_at"], name="po_queue_idx"),
            models.Index(fields=["supplier", "-created_at"], name="po_supplier_idx"),
            models.Index(fields=["payment_status", "payment_due_date"], name="po_payment_idx"),
        ]

    def clean(self):
        errors = {}
        if self.supplier_id and self.supplier.company_id != self.company_id:
            errors["supplier"] = "Supplier must belong to this company."
        if self.warehouse_id and self.warehouse.company_id != self.company_id:
            errors["warehouse"] = "Warehouse must belong to this company."
        if self.requisition_id and self.requisition.company_id != self.company_id:
            errors["requisition"] = "Requisition must belong to this company."
        if (
            self.responsible_employee_id
            and self.responsible_employee.company_id != self.company_id
        ):
            errors["responsible_employee"] = "Responsible employee must belong to this company."
        if errors:
            raise ValidationError(errors)

    @property
    def balance_due(self):
        return self.grand_total - self.paid_amount

    def __str__(self):
        return self.po_number


class PurchaseOrderLine(ValidatedModel):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="lines")
    line_number = models.PositiveIntegerField()
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="purchase_order_lines")
    description = models.CharField(max_length=500, blank=True)
    quantity = models.DecimalField(
        max_digits=18, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))]
    )
    unit_price = models.DecimalField(
        max_digits=18, decimal_places=4, validators=[MinValueValidator(Decimal("0"))]
    )
    tax_percent = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal("0"))
    line_subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    received_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))

    class Meta:
        ordering = ["line_number"]
        constraints = [
            models.UniqueConstraint(fields=["order", "line_number"], name="unique_purchase_order_line"),
            models.CheckConstraint(condition=models.Q(line_number__gt=0), name="positive_po_line_number"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="positive_po_line_quantity"),
        ]

    @property
    def company_id(self):
        return self.order.company_id

    @property
    def pending_quantity(self):
        return self.quantity - self.received_quantity

    def clean(self):
        if self.product_id and self.product.company_id != self.company_id:
            raise ValidationError({"product": "Product must belong to this company."})

    def save(self, *args, **kwargs):
        quantum = Decimal("0.01")
        self.line_subtotal = (self.quantity * self.unit_price).quantize(quantum, ROUND_HALF_UP)
        self.tax_amount = (self.line_subtotal * self.tax_percent / Decimal("100")).quantize(
            quantum, ROUND_HALF_UP
        )
        self.total_amount = self.line_subtotal + self.tax_amount
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order} / {self.line_number}"


class GoodsReceipt(ValidatedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="goods_receipts")
    grn_number = models.CharField(max_length=80)
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.PROTECT, related_name="goods_receipts"
    )
    received_by = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="goods_receipts")
    received_date = models.DateField(default=timezone.localdate)
    supplier_reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="confirmed_goods_receipts",
        null=True,
        blank=True,
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_goods_receipts",
        null=True,
    )

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "grn_number"], name="unique_grn_number")
        ]
        indexes = [
            models.Index(fields=["purchase_order", "-created_at"], name="grn_po_idx"),
        ]

    def clean(self):
        if self.purchase_order_id and self.purchase_order.company_id != self.company_id:
            raise ValidationError({"purchase_order": "Purchase Order must belong to this company."})
        if self.received_by_id and self.received_by.company_id != self.company_id:
            raise ValidationError({"received_by": "Received-by employee must belong to this company."})

    def __str__(self):
        return self.grn_number


class GoodsReceiptLine(ValidatedModel):
    receipt = models.ForeignKey(GoodsReceipt, on_delete=models.PROTECT, related_name="lines")
    order_line = models.ForeignKey(
        PurchaseOrderLine, on_delete=models.PROTECT, related_name="receipt_lines"
    )
    quantity_received = models.DecimalField(
        max_digits=18, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))]
    )
    condition = models.CharField(max_length=20, default="AVAILABLE")

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["receipt", "order_line"], name="unique_grn_line_per_po_line")
        ]

    @property
    def company_id(self):
        return self.receipt.company_id

    def clean(self):
        if self.order_line_id and self.order_line.order_id != self.receipt.purchase_order_id:
            raise ValidationError({"order_line": "Line must belong to the receipt's Purchase Order."})

    def __str__(self):
        return f"{self.receipt} / {self.order_line.line_number}"
