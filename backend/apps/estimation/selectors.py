from django.db.models import Q

from apps.approvals.models import ApprovalRequest
from apps.audit.models import AuditEvent
from apps.documents.models import Document
from apps.rbac.services import authorized_queryset, has_permission


def estimate_workspace_data(estimate, user):
    enquiry = estimate.enquiry
    documents = Document.objects.filter(
        Q(links__entity_type="commercial_estimate", links__entity_id=str(estimate.pk))
        | Q(links__entity_type="enquiry", links__entity_id=str(enquiry.pk))
        | Q(
            links__entity_type="engineering_feasibility_review",
            links__entity_id=str(estimate.engineering_review_id),
        )
    ).distinct()
    if has_permission(user, "documents.document.view", estimate):
        documents = authorized_queryset(user, "documents.document.view", documents).order_by("-created_at")[
            :30
        ]
    else:
        documents = documents.none()
    events = AuditEvent.objects.filter(
        company=estimate.company,
        entity_type="commercial_estimate",
        entity_id=str(estimate.pk),
    ).order_by("-occurred_at")[:50]
    if not has_permission(user, "audit.event.view", estimate):
        events = AuditEvent.objects.none()
    approvals = ApprovalRequest.objects.filter(
        entity_type="commercial_estimate", entity_id=str(estimate.pk)
    ).select_related("workflow_version", "current_step")
    return {"documents": documents, "audit_events": events, "approvals": approvals}
