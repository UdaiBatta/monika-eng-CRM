from apps.audit.models import AuditEvent
from apps.crm.models import CrmActivity
from apps.documents.models import Document
from apps.rbac.services import authorized_queryset, has_permission


def enquiry_workspace_data(enquiry, user):
    activities = CrmActivity.objects.select_related(
        "contact",
        "created_by",
        "created_by__employee",
        "follow_up_owner",
    ).filter(enquiry=enquiry)
    if has_permission(user, "crm.activity.view", enquiry):
        activities = authorized_queryset(user, "crm.activity.view", activities)
    else:
        activities = activities.none()

    documents = Document.objects.filter(
        links__entity_type="enquiry",
        links__entity_id=str(enquiry.pk),
    ).distinct()
    if has_permission(user, "documents.document.view", enquiry):
        documents = authorized_queryset(user, "documents.document.view", documents)
    else:
        documents = documents.none()

    audit_events = AuditEvent.objects.filter(
        company=enquiry.company,
        entity_type="enquiry",
        entity_id=str(enquiry.pk),
    ).order_by("-occurred_at")[:30]
    if not has_permission(user, "audit.event.view", enquiry):
        audit_events = AuditEvent.objects.none()

    return {
        "activities": activities.order_by("-activity_date")[:30],
        "documents": documents.order_by("-created_at")[:20],
        "audit_events": audit_events,
        "next_follow_up": activities.filter(
            activity_type=CrmActivity.ActivityType.FOLLOW_UP,
            status=CrmActivity.Status.OPEN,
        )
        .order_by("next_follow_up_at")
        .first(),
    }
