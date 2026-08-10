from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.entity_registry import entity_company_id, entity_key

from .models import Notification, NotificationPreference


def _employee(user):
    try:
        return user.employee
    except Exception:
        return None


def _name(user, employee):
    return employee.display_name if employee else user.get_full_name() or user.email


def notify(
    *,
    recipient,
    notification_type,
    title,
    message,
    company=None,
    entity=None,
    entity_type="",
    entity_id="",
    severity=Notification.Severity.INFO,
    action_url="",
    deduplication_key="",
):
    if not recipient.is_active:
        return None
    employee = _employee(recipient)
    resolved_company_id = getattr(company, "pk", company)
    if entity is not None:
        entity_type = entity_key(entity)
        entity_id = entity.pk
        resolved_company_id = resolved_company_id or entity_company_id(entity)
    resolved_company_id = resolved_company_id or getattr(employee, "company_id", None)
    if not resolved_company_id:
        raise ValidationError("A company is required for an in-app notification.")
    if employee and employee.company_id != resolved_company_id:
        raise ValidationError("Notification recipient and related record must use the same company.")
    if not employee and not recipient.is_superuser:
        raise ValidationError("The notification recipient must have an employee company assignment.")
    preference, _ = NotificationPreference.objects.get_or_create(user=recipient)
    if not preference.in_app_enabled:
        return None
    values = {
        "company_id": resolved_company_id,
        "recipient_employee": employee,
        "recipient_name": _name(recipient, employee),
        "notification_type": notification_type,
        "severity": severity,
        "title": title,
        "message": message,
        "entity_type": entity_type,
        "entity_id": str(entity_id or ""),
        "action_url": action_url,
    }
    if deduplication_key:
        notification, _ = Notification.objects.get_or_create(
            recipient_user=recipient,
            deduplication_key=deduplication_key,
            defaults=values,
        )
        return notification
    return Notification.objects.create(recipient_user=recipient, **values)


def _own(notification_id, user, *, lock=False):
    queryset = Notification.objects.select_for_update() if lock else Notification.objects
    try:
        return queryset.get(pk=notification_id, recipient_user=user)
    except Notification.DoesNotExist as exc:
        raise PermissionDenied("This notification is not available to you.") from exc


def mark_read(*, notification_id, user):
    with transaction.atomic():
        notification = _own(notification_id, user, lock=True)
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at", "updated_at"])
        return notification


def mark_unread(*, notification_id, user):
    with transaction.atomic():
        notification = _own(notification_id, user, lock=True)
        if notification.read_at is not None:
            notification.read_at = None
            notification.save(update_fields=["read_at", "updated_at"])
        return notification


def archive_notification(*, notification_id, user):
    with transaction.atomic():
        notification = _own(notification_id, user, lock=True)
        if notification.archived_at is None:
            notification.archived_at = timezone.now()
            notification.save(update_fields=["archived_at", "updated_at"])
        return notification


def mark_all_read(*, user):
    now = timezone.now()
    return Notification.objects.filter(
        recipient_user=user,
        archived_at__isnull=True,
        read_at__isnull=True,
    ).update(read_at=now, updated_at=now)
