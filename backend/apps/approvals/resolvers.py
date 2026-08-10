from rest_framework.exceptions import ValidationError

from apps.rbac.services import has_permission

from .models import ApprovalStepDefinition


def _company_user(user, company_id):
    try:
        return user.employee.company_id == company_id
    except Exception:
        return False


def resolve_approvers(step, entity):
    company_id = step.workflow_version.workflow.company_id
    if step.resolver_type == ApprovalStepDefinition.ResolverType.PERMISSION:
        from apps.accounts.models import User

        users = User.objects.filter(
            is_active=True,
            employee__company_id=company_id,
        ).select_related("employee")
        approvers = [
            user for user in users if has_permission(user, step.required_permission_code, entity)
        ]
    elif step.resolver_type == ApprovalStepDefinition.ResolverType.SPECIFIC_USERS:
        approvers = [
            user
            for user in step.specific_users.filter(is_active=True).select_related("employee")
            if _company_user(user, company_id)
        ]
    else:  # protected by model choices, retained as a safe resolver boundary
        approvers = []
    approvers = list({user.pk: user for user in approvers}.values())
    if len(approvers) < step.minimum_approvals:
        raise ValidationError(
            {"approvers": [f"Step '{step.name}' does not resolve enough active company approvers."]}
        )
    return approvers
