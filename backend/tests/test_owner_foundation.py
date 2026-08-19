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


@pytest.mark.django_db
def test_owner_created_user_password_is_hashed_and_blank_edit_keeps_it(api_client, company):
    admin = User.objects.create_superuser(email="account-owner@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)

    created = api_client.post(
        "/api/v1/users/",
        {"email": "new-sales@example.test", "password": "DifferentSafePassword-2741"},
        format="json",
    )

    assert created.status_code == 201
    account = User.objects.get(email="new-sales@example.test")
    assert account.check_password("DifferentSafePassword-2741")
    updated = api_client.patch(
        f"/api/v1/users/{account.pk}/",
        {"first_name": "New", "record_version": account.record_version},
        format="json",
    )
    assert updated.status_code == 200
    account.refresh_from_db()
    assert account.check_password("DifferentSafePassword-2741")


@pytest.mark.django_db
def test_unavailable_feature_cannot_be_enabled(api_client, company):
    admin = User.objects.create_superuser(email="feature-guard@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)

    response = api_client.post(
        "/api/v1/owner/change-feature/",
        {
            "company": str(company.pk),
            "key": "inventory_transactions",
            "is_enabled": True,
            "reason": "Attempt to enable planned stock ledger",
        },
        format="json",
    )

    assert response.status_code == 400
    assert not FeatureFlag.objects.filter(company=company, key="inventory_transactions").exists()


@pytest.mark.django_db
def test_bulk_reassignment_is_atomic(api_client, company, employee):
    replacement_user = User.objects.create_user(
        email="atomic-replacement@example.test", password="SafePassword-2741"
    )
    replacement = Employee.objects.create(
        user=replacement_user,
        company=company,
        employee_code="ME-TEST-003",
        first_name="Atomic",
        joining_date=date(2026, 1, 3),
        employment_type=Employee.EmploymentType.PERMANENT,
    )
    submission = ExternalEnquirySubmission.objects.create(
        company=company,
        channel=ExternalEnquirySubmission.Channel.MANUAL,
        source_type=ExternalEnquirySubmission.SourceType.MANUAL_ENTRY,
        external_submission_id="MANUAL-OWNER-ATOMIC",
        person_name="Customer",
        subject="Atomic reassignment enquiry",
        message="Please quote",
        assigned_to=employee,
    )
    admin = User.objects.create_superuser(email="atomic-owner@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)

    response = api_client.post(
        "/api/v1/owner/reassign-work/",
        {
            "company": str(company.pk),
            "items": [
                {"work_type": "incoming_enquiry", "id": str(submission.pk)},
                {"work_type": "incoming_enquiry", "id": "00000000-0000-0000-0000-000000000001"},
            ],
            "employee_id": str(replacement.pk),
            "reason": "Atomic batch safety test",
        },
        format="json",
    )

    assert response.status_code == 400
    submission.refresh_from_db()
    assert submission.assigned_to == employee
    assert not AuditEvent.objects.filter(entity_id=str(submission.pk), action="ASSIGN").exists()


@pytest.mark.django_db
def test_data_quality_endpoint_reports_inactive_owner_work(api_client, company, employee):
    employee.user.is_active = False
    employee.user.save(update_fields=["is_active"])
    ExternalEnquirySubmission.objects.create(
        company=company,
        channel=ExternalEnquirySubmission.Channel.MANUAL,
        source_type=ExternalEnquirySubmission.SourceType.MANUAL_ENTRY,
        external_submission_id="MANUAL-INACTIVE-OWNER",
        person_name="Customer",
        subject="Uncovered enquiry",
        message="Please quote",
        assigned_to=employee,
    )
    admin = User.objects.create_superuser(email="quality-owner@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)

    response = api_client.get(f"/api/v1/owner/data-quality/?company={company.pk}")

    assert response.status_code == 200
    issue = next(item for item in response.data["issues"] if item["type"] == "open_work_inactive_employee")
    assert issue["count"] == 1


@pytest.mark.django_db
def test_employee_disable_reassigns_work_and_reactivation_is_audited(api_client, company, employee):
    replacement_user = User.objects.create_user(
        email="continuity-replacement@example.test", password="SafePassword-2741"
    )
    replacement = Employee.objects.create(
        user=replacement_user,
        company=company,
        employee_code="ME-TEST-004",
        first_name="Continuity",
        joining_date=date(2026, 1, 4),
        employment_type=Employee.EmploymentType.PERMANENT,
    )
    submission = ExternalEnquirySubmission.objects.create(
        company=company,
        channel=ExternalEnquirySubmission.Channel.MANUAL,
        source_type=ExternalEnquirySubmission.SourceType.MANUAL_ENTRY,
        external_submission_id="MANUAL-DEACTIVATE-OWNER",
        person_name="Customer",
        subject="Continuity enquiry",
        message="Please quote",
        assigned_to=employee,
    )
    admin = User.objects.create_superuser(email="continuity-owner@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)

    disabled = api_client.post(
        f"/api/v1/employees/{employee.pk}/deactivate/",
        {
            "reason": "Employee transferred out of Sales",
            "open_work_action": "REASSIGN",
            "replacement_employee_id": str(replacement.pk),
        },
        format="json",
    )

    assert disabled.status_code == 200
    employee.refresh_from_db()
    employee.user.refresh_from_db()
    submission.refresh_from_db()
    assert employee.employment_status == Employee.EmploymentStatus.INACTIVE
    assert employee.user.is_active is False
    assert submission.assigned_to == replacement

    activated = api_client.post(
        f"/api/v1/employees/{employee.pk}/activate/",
        {"reason": "Employee returned to active employment", "enable_login": True},
        format="json",
    )

    assert activated.status_code == 200
    employee.refresh_from_db()
    employee.user.refresh_from_db()
    assert employee.employment_status == Employee.EmploymentStatus.ACTIVE
    assert employee.user.is_active is True
    assert AuditEvent.objects.filter(entity_id=str(employee.pk), action="DEACTIVATE").exists()
    assert AuditEvent.objects.filter(entity_id=str(employee.pk), action="ACTIVATE").exists()
