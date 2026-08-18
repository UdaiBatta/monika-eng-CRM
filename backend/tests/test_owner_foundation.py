from datetime import date

import pytest

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.configuration.models import FeatureFlag
from apps.external_enquiries.models import ExternalEnquirySubmission
from apps.organization.models import Employee
from apps.rbac.models import (
    Permission,
    PermissionOverride,
    Role,
    RoleAssignment,
    RolePermission,
    ScopeType,
)
from apps.rbac.services import explain_permission


@pytest.mark.django_db
def test_foundation_record_rejects_stale_admin_save(api_client, company):
    admin = User.objects.create_superuser(email="owner-version@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)

    first = api_client.patch(
        f"/api/v1/companies/{company.pk}/",
        {"name": "First saved name", "record_version": company.record_version},
        format="json",
    )
    stale = api_client.patch(
        f"/api/v1/companies/{company.pk}/",
        {"name": "Stale overwrite", "record_version": company.record_version},
        format="json",
    )

    assert first.status_code == 200
    assert first.data["record_version"] == 2
    assert stale.status_code == 409
    company.refresh_from_db()
    assert company.name == "First saved name"


@pytest.mark.django_db
def test_role_manager_cannot_grant_permission_they_do_not_hold(api_client, company, user, employee):
    manage_roles = Permission.objects.get(code="rbac.role.manage")
    owner_permission = Permission.objects.get(code="system.owner_control.manage")
    manager = Role.objects.create(company=company, code="ROLE-MANAGER", name="Role manager")
    RolePermission.objects.create(role=manager, permission=manage_roles)
    RoleAssignment.objects.create(
        user=user,
        role=manager,
        scope_type=ScopeType.COMPANY,
        company=company,
    )
    api_client.force_authenticate(user)

    response = api_client.post(
        "/api/v1/roles/",
        {
            "company": str(company.pk),
            "code": "SELF-OWNER",
            "name": "Self promoted owner",
            "permission_ids": [str(owner_permission.pk)],
        },
        format="json",
    )

    assert response.status_code == 403
    assert not Role.objects.filter(code="SELF-OWNER").exists()


@pytest.mark.django_db
def test_access_explanation_shows_deny_override_precedence(company, user, employee):
    permission = Permission.objects.get(code="organization.employee.view")
    role = Role.objects.create(company=company, code="PEOPLE", name="People viewer")
    RolePermission.objects.create(role=role, permission=permission)
    RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.COMPANY,
        company=company,
    )
    PermissionOverride.objects.create(
        user=user,
        permission=permission,
        effect=PermissionOverride.Effect.DENY,
        reason="Temporary separation of duties",
        scope_type=ScopeType.COMPANY,
        company=company,
    )

    explanation = explain_permission(user, permission.code, company)

    assert explanation["allowed"] is False
    assert explanation["reason"] == "Denied by a direct Deny override. Deny takes priority."
    assert explanation["overrides"][0]["reason"] == "Temporary separation of duties"


@pytest.mark.django_db
def test_final_business_owner_account_cannot_be_disabled(api_client, company, user, employee):
    owner_permission = Permission.objects.get(code="system.owner_control.manage")
    owner_role = Role.objects.create(company=company, code="OWNER", name="Business Owner")
    RolePermission.objects.create(role=owner_role, permission=owner_permission)
    RoleAssignment.objects.create(
        user=user,
        role=owner_role,
        scope_type=ScopeType.COMPANY,
        company=company,
    )
    admin = User.objects.create_superuser(email="system-owner@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)

    response = api_client.post(
        f"/api/v1/users/{user.pk}/deactivate/",
        {"reason": "Account no longer required"},
        format="json",
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.is_active is True


@pytest.mark.django_db
def test_owner_overview_reports_real_company_counts(api_client, company, employee):
    admin = User.objects.create_superuser(email="overview-owner@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)

    response = api_client.get(f"/api/v1/owner/?company={company.pk}")

    assert response.status_code == 200
    assert response.data["company"]["name"] == company.name
    assert response.data["people"]["active_employees"] == 1
    assert response.data["work"]["open"] == 0


@pytest.mark.django_db
def test_owner_feature_change_is_versioned_and_audited(api_client, company):
    admin = User.objects.create_superuser(email="feature-owner@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)
    flag = FeatureFlag.objects.get(company=company, key="quick_quotation")

    response = api_client.post(
        "/api/v1/owner/change-feature/",
        {
            "company": str(company.pk),
            "key": "quick_quotation",
            "is_enabled": False,
            "reason": "Use the approved estimate route while pricing is reviewed",
            "record_version": flag.record_version,
        },
        format="json",
    )

    assert response.status_code == 200
    flag.refresh_from_db()
    assert flag.is_enabled is False
    assert flag.record_version == 2
    assert AuditEvent.objects.filter(entity_type="feature_flag", action="DEACTIVATE").exists()


@pytest.mark.django_db
def test_owner_reassigns_open_work_once(api_client, company, employee):
    replacement_user = User.objects.create_user(
        email="replacement@example.test", password="SafePassword-2741"
    )
    replacement = Employee.objects.create(
        user=replacement_user,
        company=company,
        employee_code="ME-TEST-002",
        first_name="Replacement",
        joining_date=date(2026, 1, 2),
        employment_type=Employee.EmploymentType.PERMANENT,
    )
    submission = ExternalEnquirySubmission.objects.create(
        company=company,
        channel=ExternalEnquirySubmission.Channel.MANUAL,
        source_type=ExternalEnquirySubmission.SourceType.MANUAL_ENTRY,
        external_submission_id="MANUAL-OWNER-1",
        person_name="Customer",
        subject="Control panel enquiry",
        message="Please quote",
        assigned_to=employee,
    )
    admin = User.objects.create_superuser(email="work-owner@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)
    payload = {
        "company": str(company.pk),
        "work_type": "incoming_enquiry",
        "record_id": str(submission.pk),
        "employee_id": str(replacement.pk),
        "reason": "Covering the Sales queue during planned leave",
    }

    first = api_client.post("/api/v1/owner/reassign-work/", payload, format="json")
    second = api_client.post("/api/v1/owner/reassign-work/", payload, format="json")

    assert first.status_code == 200
    assert first.data["reassigned"] == 1
    assert second.status_code == 200
    assert second.data["reassigned"] == 0
    submission.refresh_from_db()
    assert submission.assigned_to == replacement
    assert AuditEvent.objects.filter(entity_id=str(submission.pk), action="ASSIGN").count() == 1
