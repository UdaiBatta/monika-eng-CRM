import uuid

import pytest
from django.db import transaction

from apps.approvals.models import ApprovalRequest
from apps.approvals.services import approve_request
from apps.core.domain_events import DomainEvent, publish
from apps.notifications.handlers import handle_domain_event
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.services import notify
from apps.organization.models import Employee

from .test_approvals import drawing, grant, make_employee_user, submit, workflow


@pytest.mark.django_db
def test_notification_service_creates_isolated_deduplicated_inbox(
    company,
    branch,
    department,
    user,
    employee,
):
    first = notify(
        recipient=user,
        company=company,
        notification_type="TEST",
        title="Test notification",
        message="A safe in-app notification.",
        severity=Notification.Severity.INFO,
        action_url="/app/documents",
        deduplication_key="test-one",
    )
    repeated = notify(
        recipient=user,
        company=company,
        notification_type="TEST",
        title="Repeated notification",
        message="This retry must not create another row.",
        deduplication_key="test-one",
    )
    inactive = make_employee_user(company, branch, department, 60)
    inactive.is_active = False
    inactive.save(update_fields=["is_active"])

    assert first.pk == repeated.pk
    assert Notification.objects.filter(recipient_user=user).count() == 1
    assert notify(
        recipient=inactive,
        company=company,
        notification_type="TEST",
        title="No delivery",
        message="Inactive recipients do not receive interactive notifications.",
    ) is None


@pytest.mark.django_db
def test_notification_api_read_unread_read_all_archive_and_recipient_isolation(
    api_client,
    company,
    branch,
    department,
    user,
    employee,
):
    grant(
        user,
        company,
        "notifications.notification.view",
        "notifications.notification.manage_preferences",
    )
    other = make_employee_user(company, branch, department, 61)
    own = notify(
        recipient=user,
        company=company,
        notification_type="OWN",
        title="Your notification",
        message="Visible only to you.",
    )
    another = notify(
        recipient=user,
        company=company,
        notification_type="OWN_TWO",
        title="Second notification",
        message="Also yours.",
    )
    hidden = notify(
        recipient=other,
        company=company,
        notification_type="HIDDEN",
        title="Another inbox",
        message="Must remain private.",
    )
    api_client.force_authenticate(user)

    listing = api_client.get("/api/v1/notifications/")
    assert listing.status_code == 200
    assert {item["id"] for item in listing.data["results"]} == {str(own.pk), str(another.pk)}
    assert api_client.get("/api/v1/notifications/unread-count/").data == {"count": 2}
    assert api_client.post(f"/api/v1/notifications/{hidden.pk}/read/").status_code == 404

    assert api_client.post(f"/api/v1/notifications/{own.pk}/read/").status_code == 200
    assert api_client.get("/api/v1/notifications/unread-count/").data == {"count": 1}
    assert api_client.post(f"/api/v1/notifications/{own.pk}/unread/").status_code == 200
    assert api_client.post("/api/v1/notifications/read-all/").data == {"updated": 2}
    assert api_client.post(f"/api/v1/notifications/{own.pk}/archive/").status_code == 204
    assert [item["id"] for item in api_client.get("/api/v1/notifications/").data["results"]] == [
        str(another.pk)
    ]

    preference = api_client.patch(
        "/api/v1/notification-preferences/me/",
        {"in_app_enabled": False},
        format="json",
    )
    assert preference.status_code == 200
    assert preference.data["in_app_enabled"] is False


@pytest.mark.django_db
def test_event_handler_deduplicates_retries(company, user, employee):
    event = DomainEvent(
        event_name="approval.step_opened",
        entity_type="approval_request",
        entity_id=uuid.uuid4(),
        company_id=company.pk,
        actor_user_id=user.pk,
        action="ASSIGN",
        summary="Approval step opened",
        metadata={
            "approver_user_ids": [str(user.pk)],
            "record_reference": "DRAW-001",
        },
        correlation_id=uuid.uuid4(),
    )
    handle_domain_event(event)
    handle_domain_event(event)
    assert Notification.objects.filter(recipient_user=user).count() == 1


@pytest.mark.django_db(transaction=True)
def test_notifications_are_created_after_commit_and_not_after_rollback(company, user, employee):
    committed = DomainEvent(
        event_name="approval.step_opened",
        entity_type="approval_request",
        entity_id=uuid.uuid4(),
        company_id=company.pk,
        action="ASSIGN",
        summary="Committed approval",
        metadata={"approver_user_ids": [str(user.pk)], "record_reference": "COMMITTED"},
    )
    with transaction.atomic():
        publish(committed)
        assert not Notification.objects.filter(message__contains="COMMITTED").exists()
    assert Notification.objects.filter(message__contains="COMMITTED").exists()

    rolled_back = DomainEvent(
        event_name="approval.step_opened",
        entity_type="approval_request",
        entity_id=uuid.uuid4(),
        company_id=company.pk,
        action="ASSIGN",
        summary="Rolled back approval",
        metadata={"approver_user_ids": [str(user.pk)], "record_reference": "ROLLED-BACK"},
    )
    with pytest.raises(RuntimeError, match="rollback"):
        with transaction.atomic():
            publish(rolled_back)
            raise RuntimeError("force rollback")
    assert not Notification.objects.filter(message__contains="ROLLED-BACK").exists()


@pytest.mark.django_db(transaction=True)
def test_approval_audit_and_notification_integration(company, branch, department, tmp_path):
    from apps.accounts.models import User

    requester = User.objects.create_superuser(
        email="notification-requester@example.test",
        password="SafePassword-2741",
    )
    approver = make_employee_user(company, branch, department, 62)
    grant(approver, company, "approvals.request.approve")
    item = workflow(company, requester, [approver])
    request = submit(item, drawing(company, requester, tmp_path), requester)

    approver_notification = Notification.objects.get(
        recipient_user=approver,
        notification_type="APPROVAL_REQUIRED",
    )
    assert approver_notification.entity_id == str(request.pk)

    completed = approve_request(request_id=request.pk, actor=approver, comment="Approved")
    assert completed.status == ApprovalRequest.Status.APPROVED
    requester_notification = Notification.objects.get(
        recipient_user=requester,
        notification_type="APPROVAL_REQUEST_APPROVED",
    )
    assert requester_notification.entity_id == str(request.pk)
    assert completed.steps.get().decisions.get().decided_by == approver
    assert NotificationPreference.objects.filter(user=requester).exists()


@pytest.mark.django_db
def test_inactive_employee_history_is_preserved(company, user, employee):
    notification = notify(
        recipient=user,
        company=company,
        notification_type="HISTORY",
        title="Historical notification",
        message="This remains after employee deactivation.",
    )
    employee.employment_status = Employee.EmploymentStatus.INACTIVE
    employee.save(update_fields=["employment_status", "updated_at"])
    notification.refresh_from_db()
    assert notification.recipient_employee == employee
