import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.organization.models import Company
from apps.rbac.models import Permission, Role, RoleAssignment, RolePermission, ScopeType


@pytest.mark.django_db
def test_audit_event_is_immutable(company, user, employee):
    event = record_event(
        actor=user,
        company=company,
        action=AuditEvent.Action.UPDATE,
        entity=employee,
        summary="Employee updated",
    )
    event.summary = "Rewritten"
    with pytest.raises(ValidationError, match="cannot be changed"):
        event.save()
    with pytest.raises(ValidationError, match="cannot be deleted"):
        event.delete()
    with pytest.raises(ValidationError, match="cannot be changed"):
        AuditEvent.objects.filter(pk=event.pk).update(summary="Rewritten")


@pytest.mark.django_db
def test_audit_redacts_sensitive_values(company, user, employee):
    event = record_event(
        actor=user,
        company=company,
        action=AuditEvent.Action.UPDATE,
        entity=employee,
        summary="Security settings updated",
        changes={"password": {"old": "secret-one", "new": "secret-two"}, "phone": {"new": "1"}},
        metadata={"api_key": "hidden", "reason": "test"},
    )
    assert event.changes["password"] == "[REDACTED]"
    assert event.metadata["api_key"] == "[REDACTED]"
    assert event.metadata["reason"] == "test"


@pytest.mark.django_db
def test_foundation_update_creates_audit_event(api_client, company):
    admin = User.objects.create_superuser(email="audit-admin@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)
    response = api_client.patch(
        f"/api/v1/companies/{company.pk}/",
        {"name": "Updated Company", "record_version": company.record_version},
        format="json",
    )
    assert response.status_code == 200
    event = AuditEvent.objects.get(entity_type="company", entity_id=str(company.pk), action="UPDATE")
    assert event.changes["name"] == {"old": "Monika Engineers Test", "new": "Updated Company"}


@pytest.mark.django_db
def test_audit_api_is_read_only_and_company_scoped(api_client, company, user, employee):
    permission = Permission.objects.get(code="audit.event.view")
    role = Role.objects.create(company=company, code="AUDITOR", name="Auditor")
    RolePermission.objects.create(role=role, permission=permission)
    RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.COMPANY,
        company=company,
    )
    own = record_event(
        actor=user,
        company=company,
        action=AuditEvent.Action.CREATE,
        entity=employee,
        summary="Visible activity",
    )
    other_company = Company.objects.create(name="Other Company", code="OTHER-AUDIT")
    record_event(
        company=other_company,
        action=AuditEvent.Action.CREATE,
        entity=other_company,
        summary="Hidden activity",
    )

    api_client.force_authenticate(user)
    response = api_client.get("/api/v1/audit/events/")
    assert response.status_code == 200
    assert [item["id"] for item in response.data["results"]] == [str(own.id)]
    update = api_client.patch(
        f"/api/v1/audit/events/{own.pk}/", {"summary": "No"}, format="json"
    )
    assert update.status_code == 405
    assert api_client.delete(f"/api/v1/audit/events/{own.pk}/").status_code == 405


@pytest.mark.django_db
def test_entity_timeline_requires_registered_type(api_client, company):
    admin = User.objects.create_superuser(email="timeline-admin@example.test", password="SafePassword-2741")
    api_client.force_authenticate(admin)
    response = api_client.get(f"/api/v1/audit/events/entities/unregistered/{company.pk}/")
    assert response.status_code == 400
