from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel
from apps.organization.models import Company


class Currency(TimeStampedModel):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=80)
    symbol = models.CharField(max_length=8)
    decimal_places = models.PositiveSmallIntegerField(default=2, validators=[MaxValueValidator(4)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name_plural = "currencies"

    def __str__(self):
        return self.code


class UnitOfMeasure(TimeStampedModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=80)
    category = models.CharField(max_length=80, blank=True)
    decimal_places = models.PositiveSmallIntegerField(default=3, validators=[MaxValueValidator(6)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code


class CompanyMaster(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.code} · {self.name}"


class TaxRate(CompanyMaster):
    rate_percent = models.DecimalField(
        max_digits=7, decimal_places=4, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["company__name", "code", "valid_from"]
        constraints = [
            models.UniqueConstraint(fields=["company", "code", "valid_from"], name="unique_tax_rate_version")
        ]

    def clean(self):
        if self.valid_to and self.valid_to < self.valid_from:
            raise ValidationError({"valid_to": "Valid to date cannot precede valid from date."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PaymentTerm(CompanyMaster):
    due_days = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["company__name", "due_days", "code"]
        constraints = [models.UniqueConstraint(fields=["company", "code"], name="unique_payment_term_code")]


class DeliveryTerm(CompanyMaster):
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["company__name", "code"]
        constraints = [models.UniqueConstraint(fields=["company", "code"], name="unique_delivery_term_code")]
