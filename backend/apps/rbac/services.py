from dataclasses import dataclass

from .models import PermissionOverride, RoleAssignment, ScopeType


@dataclass(frozen=True)
class PermissionContext:
    company_id: object = None
    branch_id: object = None
    department_id: object = None
    warehouse_id: object = None
    target_user_id: object = None


def context_from(value, user=None):
    if isinstance(value, PermissionContext):
        return value
    if isinstance(value, dict):

        def identity(name):
            item = value.get(name) or value.get(f"{name}_id")
            return getattr(item, "id", item)

        return PermissionContext(
            identity("company"),
            identity("branch"),
            identity("department"),
            identity("warehouse"),
            identity("target_user"),
        )
    if value is None:
        value = getattr(user, "employee", None)
    if value is None:
        return PermissionContext(target_user_id=getattr(user, "id", None))
    model_name = value._meta.model_name
    employee = getattr(value, "employee", None) if model_name == "user" else None
    role = getattr(value, "role", None)
    requester_employee = getattr(user, "employee", None)
    company_id = value.id if model_name == "company" else getattr(value, "company_id", None)
    company_id = (
        company_id
        or getattr(employee, "company_id", None)
        or getattr(role, "company_id", None)
        or getattr(requester_employee, "company_id", None)
    )
    target_user_id = value.id if model_name == "user" else getattr(value, "user_id", None)
    return PermissionContext(
        company_id=company_id,
        branch_id=(value.id if model_name == "branch" else getattr(value, "branch_id", None))
        or getattr(employee, "branch_id", None)
        or getattr(requester_employee, "branch_id", None),
        department_id=(value.id if model_name == "department" else getattr(value, "department_id", None))
        or getattr(employee, "department_id", None)
        or getattr(requester_employee, "department_id", None),
        warehouse_id=value.id if model_name == "warehouse" else getattr(value, "warehouse_id", None),
        target_user_id=target_user_id,
    )


def _scope_matches(item, context, user):
    if item.scope_type == ScopeType.SELF:
        return context.target_user_id == user.id
    if item.company_id != context.company_id:
        return False
    if item.scope_type == ScopeType.COMPANY:
        return True
    if item.scope_type == ScopeType.BRANCH:
        return item.branch_id == context.branch_id
    if item.scope_type == ScopeType.DEPARTMENT:
        return item.department_id == context.department_id
    if item.scope_type == ScopeType.WAREHOUSE:
        return item.warehouse_id == context.warehouse_id
    return False


def has_permission(user, permission_code, context=None):
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    resolved = context_from(context, user)
    overrides = PermissionOverride.objects.select_related("permission").filter(
        user=user, permission__code=permission_code, permission__is_active=True, is_active=True
    )
    matching = [override for override in overrides if _scope_matches(override, resolved, user)]
    if any(override.effect == PermissionOverride.Effect.DENY for override in matching):
        return False
    if any(override.effect == PermissionOverride.Effect.ALLOW for override in matching):
        return True
    assignments = (
        RoleAssignment.objects.select_related("role")
        .prefetch_related("role__role_permissions__permission")
        .filter(
            user=user,
            is_active=True,
            role__is_active=True,
            role__role_permissions__permission__code=permission_code,
            role__role_permissions__permission__is_active=True,
        )
        .distinct()
    )
    return any(_scope_matches(assignment, resolved, user) for assignment in assignments)


def effective_permission_codes(user, context=None):
    from .models import Permission

    return [
        code
        for code in Permission.objects.filter(is_active=True).values_list("code", flat=True)
        if has_permission(user, code, context)
    ]


def authorized_queryset(user, permission_code, queryset):
    if user.is_superuser:
        return queryset
    allowed_ids = [obj.pk for obj in queryset if has_permission(user, permission_code, obj)]
    return queryset.filter(pk__in=allowed_ids)
