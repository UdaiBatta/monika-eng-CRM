from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel
from apps.masters.models import Currency
from apps.organization.models import Company


class CompanySettings(TimeStampedModel):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name="settings")
    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    country_code = models.CharField(max_length=2, default="IN")
    default_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True)
    financial_year_start_month = models.PositiveSmallIntegerField(
        default=4, validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    date_format = models.CharField(max_length=30, default="DD-MM-YYYY")
    number_format = models.CharField(max_length=30, default="en-IN")
    document_footer = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "company settings"

    def __str__(self):
        return f"Settings · {self.company.name}"


class FeatureFlag(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="feature_flags")
    key = models.CharField(max_length=100)
    description = models.CharField(max_length=250, blank=True)
    is_enabled = models.BooleanField(default=False)

    class Meta:
        ordering = ["company__name", "key"]
        constraints = [models.UniqueConstraint(fields=["company", "key"], name="unique_company_feature_flag")]

    def __str__(self):
        return f"{self.company.code} · {self.key}"
