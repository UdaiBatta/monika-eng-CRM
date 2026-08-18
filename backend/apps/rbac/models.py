from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import VersionedModel
from apps.organization.models import Branch, Company, Department, Warehouse


class Permission(VersionedModel):
    code = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code


class Role(VersionedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="roles")
    code = models.CharField(max_length=60)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    permissions = models.ManyToManyField(Permission, through="RolePermission", related_name="roles")

    class Meta:
        ordering = ["company__name", "name"]
        constraints = [models.UniqueConstraint(fields=["company", "code"], name="unique_role_code")]

    def __str__(self):
        return f"{self.company.code} · {self.name}"


class RolePermission(VersionedModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_permissions")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["role", "permission"], name="unique_role_permission")]


class ScopeType(models.TextChoices):
    COMPANY = "COMPANY", "Company"
    BRANCH = "BRANCH", "Branch"
    DEPARTMENT = "DEPARTMENT", "Department"
    WAREHOUSE = "WAREHOUSE", "Warehouse"
    SELF = "SELF", "Self"


class ScopedModel(VersionedModel):
    scope_type = models.CharField(max_length=20, choices=ScopeType.choices)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        abstract = True

    def clean_scope(self):
        fields = {
            "company": self.company,
            "branch": self.branch,
            "department": self.department,
            "warehouse": self.warehouse,
        }
        if self.scope_type == ScopeType.SELF:
            if any(fields.values()):
                raise ValidationError("SELF scope cannot contain an organization reference.")
            return

        selected_name = self.scope_type.lower()
        if not self.company_id:
            raise ValidationError({"company": "Company is required for organization scopes."})
        if selected_name != "company" and not fields[selected_name]:
            raise ValidationError({selected_name: f"{selected_name.title()} is required for this scope."})
        for name, value in fields.items():
            if name not in {"company", selected_name} and value is not None:
                raise ValidationError({name: f"{name.title()} is not valid for {self.scope_type} scope."})
        selected = fields.get(selected_name)
        if selected_name != "company" and selected and selected.company_id != self.company_id:
            raise ValidationError({selected_name: "The scoped record must belong to the selected company."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class RoleAssignment(ScopedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="role_assignments"
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="assignments")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["user__email", "role__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role", "scope_type", "company", "branch", "department", "warehouse"],
                name="unique_role_assignment_scope",
                nulls_distinct=False,
            )
        ]

    def clean(self):
        self.clean_scope()
        if self.scope_type != ScopeType.SELF and self.role_id and self.role.company_id != self.company_id:
            raise ValidationError({"role": "Role must belong to the scoped company."})


class PermissionOverride(ScopedModel):
    class Effect(models.TextChoices):
        ALLOW = "ALLOW", "Allow"
        DENY = "DENY", "Deny"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="permission_overrides"
    )
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="overrides")
    effect = models.CharField(max_length=10, choices=Effect.choices)
    reason = models.CharField(max_length=250, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["user__email", "permission__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "permission", "scope_type", "company", "branch", "department", "warehouse"],
                name="unique_permission_override_scope",
                nulls_distinct=False,
            )
        ]

    def clean(self):
        self.clean_scope()
