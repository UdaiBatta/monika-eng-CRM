import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.organization.models import Branch, Company
from apps.rbac.models import Permission, PermissionOverride, Role, RoleAssignment, RolePermission, ScopeType
from apps.rbac.services import effective_permission_codes, has_permission


def grant(role_company, user, code, scope_type=ScopeType.COMPANY, **scope):
    permission, _ = Permission.objects.get_or_create(code=code, defaults={"name": code})
    role = Role.objects.create(
        company=role_company,
        code=f"ROLE-{Role.objects.count()}",
        name=f"Role {Role.objects.count()}",
    )
    RolePermission.objects.create(role=role, permission=permission)
    assignment = RoleAssignment(user=user, role=role, scope_type=scope_type, **scope)
    assignment.save()
    return permission, role, assignment


@pytest.mark.django_db
def test_permissions_aggregate_across_roles(user, employee, company):
    grant(company, user, "organization.employee.view", company=company)
    grant(company, user, "organization.employee.manage", company=company)
    assert set(effective_permission_codes(user)) >= {
        "organization.employee.view",
        "organization.employee.manage",
    }


@pytest.mark.django_db
def test_explicit_deny_overrides_role_allow(user, employee, company):
    permission, _, _ = grant(company, user, "organization.employee.view", company=company)
    PermissionOverride.objects.create(
        user=user,
        permission=permission,
        effect=PermissionOverride.Effect.DENY,
        scope_type=ScopeType.COMPANY,
        company=company,
        reason="Separation of duties",
    )
    assert has_permission(user, permission.code, employee) is False


@pytest.mark.django_db
def test_branch_scope_does_not_leak(user, employee, company):
    allowed_branch = employee.branch
    other_branch = Branch.objects.create(company=company, name="Mumbai", code="MUM")
    permission, _, _ = grant(
        company,
        user,
        "organization.branch.view",
        scope_type=ScopeType.BRANCH,
        company=company,
        branch=allowed_branch,
    )
    assert has_permission(user, permission.code, allowed_branch)
    assert not has_permission(user, permission.code, other_branch)


@pytest.mark.django_db
def test_self_scope_only_matches_requesting_user(user):
    company = Company.objects.create(name="Self Company", code="SELF")
    permission, _, _ = grant(company, user, "accounts.user.view", scope_type=ScopeType.SELF)
    other = User.objects.create_user(email="other@example.test", password="OtherPassword-2741")
    assert has_permission(user, permission.code, user)
    assert not has_permission(user, permission.code, other)


@pytest.mark.django_db
def test_assignment_rejects_cross_company_scope(user):
    first = Company.objects.create(name="First", code="RBFIRST")
    second = Company.objects.create(name="Second", code="RBSECOND")
    role = Role.objects.create(company=first, code="MGR", name="Manager")
    assignment = RoleAssignment(user=user, role=role, scope_type=ScopeType.COMPANY, company=second)
    with pytest.raises(ValidationError, match="Role must belong"):
        assignment.save()


@pytest.mark.django_db
def test_api_returns_403_without_business_permission(api_client, user, employee):
    api_client.force_authenticate(user)
    response = api_client.get("/api/v1/employees/")
    assert response.status_code == 403
    assert response.data["error"]["status"] == 403
