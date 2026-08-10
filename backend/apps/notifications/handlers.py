from apps.accounts.models import User

from .models import Notification
from .services import notify


def _user(user_id):
    if not user_id:
        return None
    return User.objects.filter(pk=user_id, is_active=True).first()


def _notify_approvers(event):
    for user_id in event.metadata.get("approver_user_ids", []):
        recipient = _user(user_id)
        if recipient:
            notify(
                recipient=recipient,
                company=event.company_id,
                notification_type="APPROVAL_REQUIRED",
                severity=Notification.Severity.ACTION_REQUIRED,
                title="Needs your approval",
                message=f"{event.metadata.get('record_reference', 'A record')} is ready for your review.",
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                action_url=f"/app/approvals/{event.entity_id}",
                deduplication_key=f"{event.correlation_id}:{user_id}:approval-required",
            )


def _notify_requester(event, *, title, severity):
    user_id = event.metadata.get("requester_user_id")
    recipient = _user(user_id)
    if recipient:
        notify(
            recipient=recipient,
            company=event.company_id,
            notification_type=event.event_name.upper().replace(".", "_"),
            severity=severity,
            title=title,
            message=event.summary,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            action_url=f"/app/approvals/{event.entity_id}",
            deduplication_key=f"{event.correlation_id}:{user_id}:{event.event_name}",
        )


def handle_domain_event(event):
    if event.event_name == "crm.follow_up.assigned":
        recipient = _user(event.metadata.get("recipient_user_id"))
        if recipient:
            notify(
                recipient=recipient,
                company=event.company_id,
                notification_type="FOLLOW_UP_ASSIGNED",
                severity=Notification.Severity.ACTION_REQUIRED,
                title="New follow-up assigned",
                message=event.summary,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                action_url="/app/follow-ups",
                deduplication_key=f"{event.correlation_id}:{recipient.pk}:follow-up-assigned",
            )
    elif event.event_name in {"approval.step_opened", "approval.assignment_reassigned"}:
        _notify_approvers(event)
    elif event.event_name == "approval.request_approved":
        _notify_requester(
            event,
            title="Approval completed",
            severity=Notification.Severity.SUCCESS,
        )
    elif event.event_name == "approval.request_rejected":
        _notify_requester(
            event,
            title="Approval rejected",
            severity=Notification.Severity.WARNING,
        )
    elif event.event_name == "approval.request_returned":
        _notify_requester(
            event,
            title="Returned for changes",
            severity=Notification.Severity.ACTION_REQUIRED,
        )
    elif event.event_name == "approval.request_cancelled":
        _notify_requester(
            event,
            title="Approval cancelled",
            severity=Notification.Severity.INFO,
        )
