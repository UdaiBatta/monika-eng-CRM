import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import VersionedModel


def _validate_gstin(value):
    if value and not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", value):
        raise ValidationError("Enter a valid 15-character GSTIN.")


def _validate_pan(value):
    if value and not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", value):
        raise ValidationError("Enter a valid PAN.")


class ValidatedModel(VersionedModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Company(ValidatedModel):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    legal_name = models.CharField(max_length=250, blank=True)
    gstin = models.CharField(max_length=15, blank=True, validators=[_validate_gstin])
    pan = models.CharField(max_length=10, blank=True, validators=[_validate_pan])
    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class Branch(ValidatedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="branches")
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "name"]
        constraints = [models.UniqueConstraint(fields=["company", "code"], name="unique_branch_code")]

    def __str__(self):
        return f"{self.company.code} · {self.name}"


class Department(ValidatedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="departments")
    branch = models.ForeignKey(
        Branch, on_delete=models.PROTECT, related_name="departments", null=True, blank=True
    )
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, related_name="children", null=True, blank=True
    )
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "name"]
        constraints = [models.UniqueConstraint(fields=["company", "code"], name="unique_department_code")]

    def clean(self):
        errors = {}
        if self.branch_id and self.branch.company_id != self.company_id:
            errors["branch"] = "Branch must belong to the selected company."
        if self.parent_id and self.parent.company_id != self.company_id:
            errors["parent"] = "Parent department must belong to the selected company."
        if self.parent_id and self.parent_id == self.id:
            errors["parent"] = "A department cannot be its own parent."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name


class Designation(ValidatedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="designations")
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "name"]
        constraints = [models.UniqueConstraint(fields=["company", "code"], name="unique_designation_code")]

    def __str__(self):
        return self.name


class Warehouse(ValidatedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="warehouses")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="warehouses")
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "name"]
        constraints = [models.UniqueConstraint(fields=["company", "code"], name="unique_warehouse_code")]

    def clean(self):
        if self.branch_id and self.branch.company_id != self.company_id:
            raise ValidationError({"branch": "Branch must belong to the selected company."})

    def __str__(self):
        return self.name


class Employee(ValidatedModel):
    class EmploymentType(models.TextChoices):
        PERMANENT = "PERMANENT", "Permanent"
        CONTRACT = "CONTRACT", "Contract"
        TRAINEE = "TRAINEE", "Trainee"
        CONSULTANT = "CONSULTANT", "Consultant"

    class EmploymentStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        NOTICE = "NOTICE", "Notice period"
        INACTIVE = "INACTIVE", "Inactive"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="employee", null=True, blank=True
    )
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="employees")
    branch = models.ForeignKey(
        Branch, on_delete=models.PROTECT, related_name="employees", null=True, blank=True
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="employees", null=True, blank=True
    )
    designation = models.ForeignKey(
        Designation, on_delete=models.PROTECT, related_name="employees", null=True, blank=True
    )
    reporting_manager = models.ForeignKey(
        "self", on_delete=models.PROTECT, related_name="direct_reports", null=True, blank=True
    )
    employee_code = models.CharField(max_length=30)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    company_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    joining_date = models.DateField()
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices)
    employment_status = models.CharField(
        max_length=20, choices=EmploymentStatus.choices, default=EmploymentStatus.ACTIVE
    )

    class Meta:
        ordering = ["company__name", "employee_code"]
        constraints = [
            models.UniqueConstraint(fields=["company", "employee_code"], name="unique_employee_code")
        ]

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def clean(self):
        errors = {}
        for field in ("branch", "department", "designation", "reporting_manager"):
            related = getattr(self, field, None)
            if related and related.company_id != self.company_id:
                errors[field] = f"{field.replace('_', ' ').title()} must belong to the selected company."
        if self.department_id and self.department.branch_id and self.department.branch_id != self.branch_id:
            errors["department"] = "Department is assigned to a different branch."
        if self.reporting_manager_id and self.reporting_manager_id == self.id:
            errors["reporting_manager"] = "An employee cannot report to themselves."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.employee_code} · {self.display_name}"
