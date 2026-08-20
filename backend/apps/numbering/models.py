from string import Formatter

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import VersionedModel
from apps.organization.models import Branch, Company

ALLOWED_TEMPLATE_FIELDS = {"company", "branch", "code", "fy", "year", "number"}


def validate_number_template(value):
    fields = {field_name for _, field_name, _, _ in Formatter().parse(value) if field_name}
    unknown = fields - ALLOWED_TEMPLATE_FIELDS
    if unknown:
        raise ValidationError(f"Unknown template fields: {', '.join(sorted(unknown))}")
    if "number" not in fields:
        raise ValidationError("Template must include {number}.")


class DocumentSequence(VersionedModel):
    class ResetBehavior(models.TextChoices):
        NEVER = "NEVER", "Never"
        FINANCIAL_YEAR = "FINANCIAL_YEAR", "Financial year"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="document_sequences")
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="document_sequences", null=True, blank=True
    )
    code = models.CharField(max_length=40)
    financial_year = models.CharField(max_length=9)
    template = models.CharField(
        max_length=160, default="{company}/{code}/{fy}/{number}", validators=[validate_number_template]
    )
    next_number = models.PositiveBigIntegerField(default=1, validators=[MinValueValidator(1)])
    padding = models.PositiveSmallIntegerField(default=5, validators=[MinValueValidator(1)])
    reset_behavior = models.CharField(
        max_length=20, choices=ResetBehavior.choices, default=ResetBehavior.FINANCIAL_YEAR
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "code", "financial_year", "branch__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "branch", "code", "financial_year"],
                name="unique_document_sequence",
                nulls_distinct=False,
            )
        ]

    def clean(self):
        if self.branch_id and self.branch.company_id != self.company_id:
            raise ValidationError({"branch": "Branch must belong to the selected company."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company.code} · {self.code} · {self.financial_year}"
