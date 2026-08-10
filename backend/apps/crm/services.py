import re
from difflib import SequenceMatcher

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_events import DomainEvent, publish
from apps.rbac.services import has_permission

from .models import Customer


def _normalized_name(value):
    words = re.sub(r"[^a-z0-9 ]", " ", value.lower()).split()
    aliases = {"private": "pvt", "limited": "ltd"}
    return " ".join(aliases.get(word, word) for word in words)


def _employee_id(user):
    return getattr(getattr(user, "employee", None), "pk", None)


def _require(user, permission, customer):
    if not has_permission(user, permission, customer):
        raise PermissionDenied("You do not have permission to change this customer.")


def find_customer_duplicates(
    *, company, legal_name="", gstin="", pan="", email="", phone="", exclude_id=None
):
    """Return explainable possible matches; never merge records automatically."""
    candidates = Customer.objects.filter(company=company)
    if exclude_id:
        candidates = candidates.exclude(pk=exclude_id)
    normalized_name = _normalized_name(legal_name)
    matches = []
    for customer in candidates.only(
        "id", "customer_code", "legal_name", "gstin", "pan", "primary_email", "primary_phone", "status"
    )[:500]:
        reasons = []
        if gstin and customer.gstin == gstin.strip().upper():
            reasons.append("GSTIN matches")
        if pan and customer.pan == pan.strip().upper():
            reasons.append("PAN matches")
        if email and customer.primary_email.lower() == email.strip().lower():
            reasons.append("Email matches")
        if phone and customer.primary_phone == phone.strip():
            reasons.append("Phone matches")
        candidate_name = _normalized_name(customer.legal_name)
        if normalized_name and SequenceMatcher(None, normalized_name, candidate_name).ratio() >= 0.86:
            reasons.append("Legal name is similar")
        if reasons:
            matches.append(
                {
                    "id": str(customer.pk),
                    "customer_code": customer.customer_code,
                    "legal_name": customer.legal_name,
                    "status": customer.status,
                    "reasons": reasons,
                }
            )
    return matches


def _status_event(customer, actor, old_status, reason):
    return DomainEvent(
        event_name="crm.customer.status_changed",
        entity_type="customer",
        entity_id=customer.pk,
        company_id=customer.company_id,
        actor_user_id=actor.pk,
        actor_employee_id=_employee_id(actor),
        action="STATUS_CHANGE",
        module="crm",
        summary=(
            f"{customer.customer_code} changed from "
            f"{Customer.Status(old_status).label} to {customer.get_status_display()}"
        ),
        changes={"status": {"old": old_status, "new": customer.status}},
        metadata={"entity_reference": str(customer), "reason": reason},
    )


def change_customer_status(*, customer_id, actor, target_status, permission, reason=""):
    allowed = {
        Customer.Status.PROSPECT: {Customer.Status.ACTIVE, Customer.Status.INACTIVE, Customer.Status.BLOCKED},
        Customer.Status.ACTIVE: {Customer.Status.INACTIVE, Customer.Status.BLOCKED},
        Customer.Status.INACTIVE: {Customer.Status.ACTIVE, Customer.Status.BLOCKED},
        Customer.Status.BLOCKED: {Customer.Status.ACTIVE, Customer.Status.INACTIVE},
    }
    if target_status != Customer.Status.ACTIVE and not reason.strip():
        raise ValidationError({"reason": ["Explain why this customer status is changing."]})
    with transaction.atomic():
        customer = Customer.objects.select_for_update().get(pk=customer_id)
        _require(actor, permission, customer)
        old_status = customer.status
        if target_status == old_status:
            return customer
        if target_status not in allowed[old_status]:
            raise ValidationError("This customer status change is not allowed.")
        customer.status = target_status
        customer.updated_by = actor
        customer.save(update_fields=["status", "updated_by", "updated_at"])
        publish(_status_event(customer, actor, old_status, reason.strip()))
        return customer
