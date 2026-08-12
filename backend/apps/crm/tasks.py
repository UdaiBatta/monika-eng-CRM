from celery import shared_task
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import CrmActivity


@shared_task
def notify_due_follow_ups():
    """Create one in-app reminder per open follow-up and local calendar day."""
    now = timezone.now()
    local_day = timezone.localdate(now)
    follow_ups = CrmActivity.objects.select_related(
        "company", "customer", "follow_up_owner__user"
    ).filter(
        activity_type=CrmActivity.ActivityType.FOLLOW_UP,
        status=CrmActivity.Status.OPEN,
        next_follow_up_at__date__lte=local_day,
        follow_up_owner__user__is_active=True,
    )
    created = 0
    for follow_up in follow_ups:
        recipient = follow_up.follow_up_owner.user
        overdue = follow_up.next_follow_up_at < now
        notification = notify(
            recipient=recipient,
            company=follow_up.company,
            notification_type="FOLLOW_UP_OVERDUE" if overdue else "FOLLOW_UP_DUE_TODAY",
            severity=(
                Notification.Severity.WARNING if overdue else Notification.Severity.ACTION_REQUIRED
            ),
            title="Follow-up overdue" if overdue else "Follow-up due today",
            message=f"{follow_up.customer.customer_code}: {follow_up.subject}",
            entity=follow_up,
            action_url="/app/follow-ups",
            deduplication_key=f"follow-up:{follow_up.pk}:{local_day}:{'overdue' if overdue else 'today'}",
        )
        created += bool(notification)
    return created
