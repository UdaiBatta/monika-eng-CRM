from django.db.models import Q

from apps.approvals.models import ApprovalRequest
from apps.audit.models import AuditEvent
from apps.documents.models import Document
from apps.rbac.services import authorized_queryset, has_permission


def review_workspace_data(review, user):
    enquiry = review.enquiry
    documents = Document.objects.filter(
        Q(links__entity_type="engineering_feasibility_review", links__entity_id=str(review.pk))
        | Q(links__entity_type="enquiry", links__entity_id=str(enquiry.pk))
    ).distinct()
    if has_permission(user, "documents.document.view", review):
        documents = authorized_queryset(user, "documents.document.view", documents).order_by("-created_at")[
            :30
        ]
    else:
        documents = documents.none()
    clarification_ids = review.clarifications.values_list("pk", flat=True)
    events = (
        AuditEvent.objects.filter(company=review.company)
        .filter(
            Q(entity_type="engineering_feasibility_review", entity_id=str(review.pk))
            | Q(
                entity_type="engineering_clarification",
                entity_id__in=[str(value) for value in clarification_ids],
            )
        )
        .order_by("-occurred_at")[:50]
    )
    if not has_permission(user, "audit.event.view", review):
        events = AuditEvent.objects.none()
    approvals = ApprovalRequest.objects.filter(
        entity_type="engineering_feasibility_review",
        entity_id=str(review.pk),
    ).select_related("workflow_version", "current_step")
    return {"documents": documents, "audit_events": events, "approvals": approvals}
