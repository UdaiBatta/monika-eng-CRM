from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel, VersionedModel
from apps.masters.models import PaymentTerm, UnitOfMeasure
from apps.organization.models import Company, Warehouse


class ValidatedModel(VersionedModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ProductCategory(ValidatedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="product_categories")
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["company", "code"], name="unique_product_category_code")
        ]

    def __str__(self):
        return self.name


class Supplier(ValidatedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="suppliers")
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=200)
    gstin = models.CharField(max_length=15, blank=True)
    contact_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    payment_term = models.ForeignKey(
        PaymentTerm, on_delete=models.PROTECT, related_name="suppliers", null=True, blank=True
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "name"]
        constraints = [models.UniqueConstraint(fields=["company", "code"], name="unique_supplier_code")]

    def clean(self):
        if self.payment_term_id and self.payment_term.company_id != self.company_id:
            raise ValidationError({"payment_term": "Payment term must belong to this company."})

    def __str__(self):
        return self.name


class Product(ValidatedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="products")
    category = models.ForeignKey(
        ProductCategory, on_delete=models.PROTECT, related_name="products", null=True, blank=True
    )
    default_supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="products", null=True, blank=True
    )
    unit_of_measure = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name="products")
    alternates = models.ManyToManyField("self", blank=True)
    internal_code = models.CharField(max_length=40)
    brand = models.CharField(max_length=120, blank=True)
    part_number = models.CharField(max_length=120, blank=True)
    description = models.CharField(max_length=500)
    specification = models.TextField(blank=True)
    warranty_months = models.PositiveIntegerField(default=0)
    reorder_level = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))
    reorder_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "description"]
        constraints = [
            models.UniqueConstraint(fields=["company", "internal_code"], name="unique_product_internal_code")
        ]
        indexes = [
            models.Index(fields=["company", "brand", "part_number"], name="product_brand_part_idx"),
        ]

    def clean(self):
        errors = {}
        if self.category_id and self.category.company_id != self.company_id:
            errors["category"] = "Category must belong to this company."
        if self.default_supplier_id and self.default_supplier.company_id != self.company_id:
            errors["default_supplier"] = "Supplier must belong to this company."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.internal_code} · {self.description}"


class StockLocation(ValidatedModel):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="stock_locations")
    bin_code = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["warehouse__name", "bin_code"]
        constraints = [
            models.UniqueConstraint(fields=["warehouse", "bin_code"], name="unique_stock_location_bin")
        ]

    @property
    def company_id(self):
        return self.warehouse.company_id

    def __str__(self):
        return f"{self.warehouse.name} · {self.bin_code}" if self.bin_code else self.warehouse.name


class StockItem(TimeStampedModel):
    class Condition(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        RESERVED = "RESERVED", "Reserved"
        DAMAGED = "DAMAGED", "Damaged"
        REPAIR_HELD = "REPAIR_HELD", "Repair-held"
        DEMO = "DEMO", "Demo"
        IN_TRANSIT = "IN_TRANSIT", "In-transit"

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_items")
    location = models.ForeignKey(StockLocation, on_delete=models.PROTECT, related_name="stock_items")
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.AVAILABLE)
    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))

    class Meta:
        ordering = ["product__description", "location__warehouse__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "location", "condition"], name="unique_stock_item_balance"
            ),
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name="nonnegative_stock_quantity"),
        ]

    def __str__(self):
        return f"{self.product.internal_code} @ {self.location} [{self.condition}] = {self.quantity}"


class StockMovement(TimeStampedModel):
    class MovementType(models.TextChoices):
        INWARD = "INWARD", "Inward"
        OUTWARD = "OUTWARD", "Outward"
        RESERVE = "RESERVE", "Reserve"
        RELEASE_RESERVE = "RELEASE_RESERVE", "Release Reservation"
        RETURN = "RETURN", "Return"
        TRANSFER = "TRANSFER", "Transfer"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        PANEL_CONSUMPTION = "PANEL_CONSUMPTION", "Panel Consumption"
        SERVICE_CONSUMPTION = "SERVICE_CONSUMPTION", "Service Consumption"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="stock_movements")
    movement_number = models.CharField(max_length=80)
    movement_type = models.CharField(max_length=24, choices=MovementType.choices)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_movements")
    quantity = models.DecimalField(
        max_digits=18, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))]
    )
    from_location = models.ForeignKey(
        StockLocation, on_delete=models.PROTECT, related_name="movements_from", null=True, blank=True
    )
    from_condition = models.CharField(max_length=20, choices=StockItem.Condition.choices, blank=True)
    to_location = models.ForeignKey(
        StockLocation, on_delete=models.PROTECT, related_name="movements_to", null=True, blank=True
    )
    to_condition = models.CharField(max_length=20, choices=StockItem.Condition.choices, blank=True)
    reference_type = models.CharField(max_length=60, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)
    reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="stock_movements", null=True
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "movement_number"], name="unique_stock_movement_number"
            )
        ]
        indexes = [
            models.Index(fields=["company", "movement_type", "-created_at"], name="stock_movement_queue_idx"),
            models.Index(fields=["product", "-created_at"], name="stock_movement_product_idx"),
            models.Index(fields=["reference_type", "reference_id"], name="stock_movement_reference_idx"),
        ]

    def __str__(self):
        return self.movement_number
