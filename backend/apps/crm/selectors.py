from django.db.models import Q

from apps.audit.models import AuditEvent
from apps.documents.models import Document
from apps.enquiries.models import Enquiry
from apps.rbac.services import authorized_queryset, has_permission

from .models import CrmActivity


def customer_360_data(customer, user):
    activities = CrmActivity.objects.select_related(
        "contact", "created_by", "created_by__employee", "follow_up_owner"
    ).filter(customer=customer)
    visible_activities = (
        authorized_queryset(user, "crm.activity.view", activities)
        if has_permission(user, "crm.activity.view", customer)
        else activities.none()
    )
    open_follow_ups = visible_activities.filter(
        activity_type=CrmActivity.ActivityType.FOLLOW_UP,
        status=CrmActivity.Status.OPEN,
    ).order_by("next_follow_up_at")
    enquiries = Enquiry.objects.select_related(
        "customer", "responsible_salesperson", "currency"
    ).prefetch_related("requirements", "items", "items__uom").filter(customer=customer)
    if has_permission(user, "enquiry.enquiry.view", customer):
        enquiries = authorized_queryset(user, "enquiry.enquiry.view", enquiries)
    else:
        enquiries = enquiries.none()
    enquiry_ids = [str(item) for item in enquiries.values_list("pk", flat=True)]
    recent_documents = Document.objects.filter(
        Q(links__entity_type="customer", links__entity_id=str(customer.pk))
        | Q(links__entity_type="enquiry", links__entity_id__in=enquiry_ids)
    ).distinct()
    if has_permission(user, "documents.document.view", customer):
        recent_documents = authorized_queryset(
            user, "documents.document.view", recent_documents
        ).order_by("-created_at")[:8]
    else:
        recent_documents = recent_documents.none()
    audit_events = AuditEvent.objects.filter(company=customer.company).filter(
        Q(
            entity_type="customer",
            entity_id=str(customer.pk),
            event_type__startswith="crm.customer",
        )
        | Q(event_type__startswith="enquiry.", metadata__customer_id=str(customer.pk))
    ).order_by("-occurred_at")[:20]
    if not has_permission(user, "audit.event.view", customer):
        audit_events = AuditEvent.objects.none()
    return {
        "recent_activities": visible_activities[:20],
        "open_follow_ups": open_follow_ups[:20],
        "recent_documents": recent_documents,
        "audit_events": audit_events,
        "last_contact": visible_activities.exclude(
            activity_type=CrmActivity.ActivityType.FOLLOW_UP
        ).first(),
        "next_follow_up": open_follow_ups.first(),
        "open_follow_up_count": open_follow_ups.count(),
        "recent_enquiries": enquiries.order_by("-received_date")[:10],
        "open_enquiry_count": enquiries.exclude(
            status__in=[Enquiry.Status.WON, Enquiry.Status.LOST, Enquiry.Status.CANCELLED]
        ).count(),
        "won_enquiry_count": enquiries.filter(status=Enquiry.Status.WON).count(),
        "lost_enquiry_count": enquiries.filter(status=Enquiry.Status.LOST).count(),
    }
