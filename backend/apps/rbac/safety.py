from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User

from .services import has_permission

OWNER_PERMISSION = "system.owner_control.manage"


def role_grants_owner(role):
    return role.permissions.filter(code=OWNER_PERMISSION, is_active=True).exists()


def active_business_owners(company):
    users = User.objects.filter(is_active=True, employee__company=company).distinct()
    return [user for user in users if has_permission(user, OWNER_PERMISSION, company)]


def ensure_owner_continuity(company, *, previously_had_owner):
    if previously_had_owner and not active_business_owners(company):
        raise ValidationError(
            "This change would remove the final business Owner. Give Owner access to another "
            "active account first."
        )


def ensure_actor_can_grant(actor, permissions, company):
    if actor is None or actor.is_superuser:
        return
    missing = [
        permission.code
        for permission in permissions
        if not has_permission(actor, permission.code, company)
    ]
    if missing:
        raise PermissionDenied(
            "You cannot grant access that you do not already hold: " + ", ".join(sorted(missing))
        )
