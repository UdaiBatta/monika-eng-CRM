from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.approvals.conditions import conditions_match
from apps.approvals.models import ApprovalRequest, ApprovalWorkflow, ApprovalWorkflowVersion
from apps.approvals.services import create_approval_request
from apps.core.domain_events import DomainEvent, publish
from apps.engineering_reviews.models import EngineeringFeasibilityReview
from apps.engineering_reviews.services import is_ready_for_estimation
from apps.enquiries.models import Enquiry
from apps.enquiries.services import enquiry_event
from apps.masters.models import Currency
from apps.numbering.services import allocate_company_number
from apps.rbac.services import has_permission

from .models import CommercialEstimate, EstimateCostLine

ESTIMATE_ENTITY = "commercial_estimate"
EDITABLE_STATUSES = {
    CommercialEstimate.Status.DRAFT,
    CommercialEstimate.Status.IN_PREPARATION,
    CommercialEstimate.Status.RETURNED_FOR_CHANGES,
}


def _employee_id(user):
    return getattr(getattr(user, "employee", None), "pk", None)


def _require(user, permission, entity):
    if not has_permission(user, permission, entity):
        raise PermissionDenied("You do not have permission to change this commercial estimate.")


def estimate_event(estimate, actor, event_name, action, summary, *, metadata=None, changes=None):
    return DomainEvent(
        event_name=event_name,
        entity_type=ESTIMATE_ENTITY,
        entity_id=estimate.pk,
        company_id=estimate.company_id,
        actor_user_id=actor.pk if actor else None,
        actor_employee_id=_employee_id(actor) if actor else None,
        action=action,
        module="estimation",
        summary=summary,
        changes=changes or {},
        metadata={
            "entity_reference": str(estimate),
            "enquiry_id": str(estimate.enquiry_id),
            "enquiry_number": estimate.enquiry.enquiry_number,
            "customer_id": str(estimate.enquiry.customer_id),
            "estimate_number": estimate.estimate_number,
            "revision_number": estimate.revision_number,
            **(metadata or {}),
        },
    )


def _quantum(estimate):
    return Decimal("1").scaleb(-estimate.currency.decimal_places)


def recalculate_estimate(estimate):
    quantum = _quantum(estimate)
    totals = defaultdict(Decimal)
    total_cost = Decimal("0")
    for line in estimate.cost_lines.all():
        if line.is_optional:
            continue
        totals[line.category] += line.amount
        total_cost += line.amount
    total_cost = total_cost.quantize(quantum, rounding=ROUND_HALF_UP)
    if estimate.pricing_method == CommercialEstimate.PricingMethod.MARKUP:
        price = total_cost * (Decimal("1") + estimate.markup_percent / Decimal("100"))
    elif estimate.pricing_method == CommercialEstimate.PricingMethod.MARGIN:
        if estimate.target_margin_percent >= Decimal("100"):
            raise ValidationError({"target_margin_percent": "Target margin must be below 100%."})
        price = total_cost / (Decimal("1") - estimate.target_margin_percent / Decimal("100"))
    else:
        if estimate.manual_selling_price is None:
            raise ValidationError({"manual_selling_price": "Enter the manual selling price."})
        price = estimate.manual_selling_price
    price = price.quantize(quantum, rounding=ROUND_HALF_UP)
    margin_amount = (price - total_cost).quantize(quantum, rounding=ROUND_HALF_UP)
    margin_percent = (
        (margin_amount / price * Decimal("100")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        if price
        else Decimal("0")
    )
    estimate.total_cost = total_cost
    estimate.proposed_selling_price = price
    estimate.gross_margin_amount = margin_amount
    estimate.gross_margin_percent = margin_percent
    estimate.category_totals = {
        key: str(value.quantize(quantum, rounding=ROUND_HALF_UP)) for key, value in totals.items()
    }
    estimate.save(
        update_fields=[
            "total_cost",
            "proposed_selling_price",
            "gross_margin_amount",
            "gross_margin_percent",
            "category_totals",
            "updated_at",
        ]
    )
    return estimate


def create_estimate(*, enquiry_id, actor, currency_id=None):
    with transaction.atomic():
        enquiry = (
            Enquiry.objects.select_for_update(of=("self",))
            .select_related("company", "customer", "customer__default_currency", "currency")
            .get(pk=enquiry_id)
        )
        _require(actor, "estimation.estimate.create", enquiry)
        existing = enquiry.commercial_estimates.filter(is_current=True).first()
        if existing:
            return existing
        review = (
            EngineeringFeasibilityReview.objects.select_for_update()
            .filter(enquiry=enquiry, is_current=True)
            .first()
        )
        if not is_ready_for_estimation(review):
            raise ValidationError(
                "Complete a current Workshop approval and close its "
                "clarifications before estimation."
            )
        selected_currency_id = currency_id or enquiry.currency_id or enquiry.customer.default_currency_id
        try:
            currency = Currency.objects.get(pk=selected_currency_id, is_active=True)
        except Currency.DoesNotExist as exc:
            raise ValidationError({"currency_id": "Choose an active currency."}) from exc
        estimate = CommercialEstimate.objects.create(
            company=enquiry.company,
            enquiry=enquiry,
            engineering_review=review,
            estimate_number=allocate_company_number(company=enquiry.company, code="ESTIMATE"),
            revision_number=1,
            currency=currency,
            prepared_by=actor,
            created_by=actor,
            updated_by=actor,
            technical_reference_summary=review.technical_summary,
            assumptions=review.assumptions,
            exclusions=review.exclusions,
        )
        old_status = enquiry.status
        enquiry.status = Enquiry.Status.ESTIMATION
        enquiry.updated_by = actor
        enquiry.save(update_fields=["status", "updated_by", "updated_at"])
        publish(
            estimate_event(
                estimate,
                actor,
                "estimation.estimate.created",
                "CREATE",
                f"Commercial estimate created for {enquiry.enquiry_number}",
                changes={"enquiry_status": {"old": old_status, "new": enquiry.status}},
            )
        )
        return estimate


DETAIL_FIELDS = {
    "pricing_method",
    "markup_percent",
    "target_margin_percent",
    "manual_selling_price",
    "assumptions",
    "exclusions",
    "commercial_notes",
    "technical_reference_summary",
}


def update_estimate(*, estimate_id, actor, data):
    with transaction.atomic():
        estimate = (
            CommercialEstimate.objects.select_for_update()
            .select_related("enquiry", "enquiry__customer", "currency")
            .get(pk=estimate_id)
        )
        _require(actor, "estimation.estimate.edit", estimate)
        if estimate.status not in EDITABLE_STATUSES:
            raise ValidationError("Only a draft or returned estimate can be edited.")
        changes = {}
        for field in DETAIL_FIELDS:
            if field in data and getattr(estimate, field) != data[field]:
                changes[field] = {"old": str(getattr(estimate, field) or ""), "new": str(data[field] or "")}
                setattr(estimate, field, data[field])
        estimate.status = CommercialEstimate.Status.IN_PREPARATION
        estimate.updated_by = actor
        estimate.save(update_fields=[*changes.keys(), "status", "updated_by", "updated_at"])
        recalculate_estimate(estimate)
        if changes:
            publish(
                estimate_event(
                    estimate,
                    actor,
                    "estimation.estimate.updated",
                    "UPDATE",
                    f"Estimate details updated for {estimate.estimate_number}",
                    changes=changes,
                )
            )
        return estimate


def create_cost_line(*, estimate_id, actor, data):
    with transaction.atomic():
        estimate = (
            CommercialEstimate.objects.select_for_update()
            .select_related("currency", "enquiry")
            .get(pk=estimate_id)
        )
        _require(actor, "estimation.estimate.edit", estimate)
        if estimate.status not in EDITABLE_STATUSES:
            raise ValidationError("Cost lines are locked for this estimate status.")
        line_number = (estimate.cost_lines.aggregate(value=Max("line_number"))["value"] or 0) + 1
        line = EstimateCostLine.objects.create(estimate=estimate, line_number=line_number, **data)
        estimate.status = CommercialEstimate.Status.IN_PREPARATION
        estimate.updated_by = actor
        estimate.save(update_fields=["status", "updated_by", "updated_at"])
        recalculate_estimate(estimate)
        publish(
            estimate_event(
                estimate,
                actor,
                "estimation.cost_line.created",
                "CREATE",
                f"Cost line {line.line_number} added to {estimate.estimate_number}",
                metadata={"cost_line_id": str(line.pk), "category": line.category},
            )
        )
        return line


def update_cost_line(*, line_id, actor, data):
    with transaction.atomic():
        line = (
            EstimateCostLine.objects.select_for_update()
            .select_related("estimate", "estimate__currency", "estimate__enquiry")
            .get(pk=line_id)
        )
        estimate = CommercialEstimate.objects.select_for_update().get(pk=line.estimate_id)
        _require(actor, "estimation.estimate.edit", estimate)
        if estimate.status not in EDITABLE_STATUSES:
            raise ValidationError("Cost lines are locked for this estimate status.")
        changes = {}
        for field, value in data.items():
            if getattr(line, field) != value:
                changes[field] = {"old": str(getattr(line, field)), "new": str(value)}
                setattr(line, field, value)
        line.save()
        estimate.updated_by = actor
        estimate.save(update_fields=["updated_by", "updated_at"])
        recalculate_estimate(estimate)
        if changes:
            publish(
                estimate_event(
                    estimate,
                    actor,
                    "estimation.cost_line.updated",
                    "UPDATE",
                    f"Cost line {line.line_number} updated in {estimate.estimate_number}",
                    metadata={"cost_line_id": str(line.pk)},
                    changes=changes,
                )
            )
        return line


def delete_cost_line(*, line_id, actor):
    with transaction.atomic():
        line = (
            EstimateCostLine.objects.select_for_update()
            .select_related("estimate", "estimate__currency", "estimate__enquiry")
            .get(pk=line_id)
        )
        estimate = CommercialEstimate.objects.select_for_update().get(pk=line.estimate_id)
        _require(actor, "estimation.estimate.edit", estimate)
        if estimate.status not in EDITABLE_STATUSES:
            raise ValidationError("Cost lines are locked for this estimate status.")
        line_number = line.line_number
        line.delete()
        recalculate_estimate(estimate)
        publish(
            estimate_event(
                estimate,
                actor,
                "estimation.cost_line.deleted",
                "DELETE",
                f"Cost line {line_number} removed from {estimate.estimate_number}",
            )
        )


def _matching_workflow(estimate):
    workflows = ApprovalWorkflow.objects.select_related("current_version").filter(
        company=estimate.company,
        entity_type=ESTIMATE_ENTITY,
        is_active=True,
        current_version__status=ApprovalWorkflowVersion.Status.ACTIVE,
    )
    matches = [workflow for workflow in workflows if conditions_match(workflow.current_version, estimate)]
    if not matches:
        raise ValidationError("Configure an active approval workflow for commercial estimates.")
    if len(matches) > 1:
        raise ValidationError("More than one approval workflow matches this estimate.")
    return matches[0]


def submit_estimate(*, estimate_id, actor, comment=""):
    with transaction.atomic():
        estimate = (
            CommercialEstimate.objects.select_for_update()
            .select_related("company", "enquiry", "enquiry__customer", "currency")
            .prefetch_related("cost_lines")
            .get(pk=estimate_id)
        )
        _require(actor, "estimation.estimate.submit", estimate)
        if estimate.status not in EDITABLE_STATUSES:
            raise ValidationError("Only a draft or returned estimate can be submitted.")
        recalculate_estimate(estimate)
        if not estimate.cost_lines.filter(is_optional=False).exists() or estimate.total_cost <= 0:
            raise ValidationError("Add at least one non-optional cost line with a positive total.")
        if estimate.proposed_selling_price <= 0:
            raise ValidationError("The proposed selling price must be positive.")
        workflow = _matching_workflow(estimate)
        request = create_approval_request(
            workflow_id=workflow.pk,
            entity_type=ESTIMATE_ENTITY,
            entity_id=estimate.pk,
            actor=actor,
            submission_comment=comment,
            snapshot_metadata={
                "estimate_number": estimate.estimate_number,
                "revision_number": estimate.revision_number,
                "currency": estimate.currency.code,
                "total_cost": str(estimate.total_cost),
                "proposed_selling_price": str(estimate.proposed_selling_price),
                "gross_margin_percent": str(estimate.gross_margin_percent),
                "category_totals": estimate.category_totals,
            },
        )
        old_status = estimate.status
        estimate.status = CommercialEstimate.Status.PENDING_APPROVAL
        estimate.approval_request = request
        estimate.submitted_at = timezone.now()
        estimate.submitted_by = actor
        estimate.updated_by = actor
        estimate.save(
            update_fields=[
                "status",
                "approval_request",
                "submitted_at",
                "submitted_by",
                "updated_by",
                "updated_at",
            ]
        )
        publish(
            estimate_event(
                estimate,
                actor,
                "estimation.estimate.submitted",
                "SUBMIT",
                f"{estimate} submitted for approval",
                metadata={"approval_request_id": str(request.pk)},
                changes={"status": {"old": old_status, "new": estimate.status}},
            )
        )
        return estimate


def revise_estimate(*, estimate_id, actor, reason):
    with transaction.atomic():
        previous = (
            CommercialEstimate.objects.select_for_update()
            .select_related("enquiry", "enquiry__customer", "engineering_review", "currency")
            .prefetch_related("cost_lines")
            .get(pk=estimate_id)
        )
        _require(actor, "estimation.estimate.revise", previous)
        if not previous.is_current or previous.status not in {
            CommercialEstimate.Status.APPROVED,
            CommercialEstimate.Status.REJECTED,
            CommercialEstimate.Status.RETURNED_FOR_CHANGES,
        }:
            raise ValidationError("Only the current approved, rejected, or returned estimate can be revised.")
        previous.is_current = False
        previous.status = CommercialEstimate.Status.SUPERSEDED
        previous.updated_by = actor
        previous.save(update_fields=["is_current", "status", "updated_by", "updated_at"])
        revised = CommercialEstimate.objects.create(
            company=previous.company,
            enquiry=previous.enquiry,
            engineering_review=previous.engineering_review,
            estimate_number=previous.estimate_number,
            revision_number=previous.revision_number + 1,
            currency=previous.currency,
            pricing_method=previous.pricing_method,
            markup_percent=previous.markup_percent,
            target_margin_percent=previous.target_margin_percent,
            manual_selling_price=previous.manual_selling_price,
            assumptions=previous.assumptions,
            exclusions=previous.exclusions,
            commercial_notes=previous.commercial_notes,
            technical_reference_summary=previous.technical_reference_summary,
            prepared_by=actor,
            created_by=actor,
            updated_by=actor,
            supersedes=previous,
        )
        EstimateCostLine.objects.bulk_create(
            [
                EstimateCostLine(
                    estimate=revised,
                    line_number=line.line_number,
                    category=line.category,
                    description=line.description,
                    quantity=line.quantity,
                    unit_of_measure=line.unit_of_measure,
                    unit_cost=line.unit_cost,
                    amount=line.amount,
                    source_reference=line.source_reference,
                    notes=line.notes,
                    is_optional=line.is_optional,
                )
                for line in previous.cost_lines.all()
            ]
        )
        recalculate_estimate(revised)
        if revised.enquiry.status == Enquiry.Status.ESTIMATION_COMPLETE:
            old_enquiry_status = revised.enquiry.status
            revised.enquiry.status = Enquiry.Status.ESTIMATION
            revised.enquiry.updated_by = actor
            revised.enquiry.save(update_fields=["status", "updated_by", "updated_at"])
            publish(
                enquiry_event(
                    revised.enquiry,
                    actor,
                    "enquiry.estimation_reopened",
                    "STATUS_CHANGE",
                    f"{revised.enquiry.enquiry_number} returned to estimation for revision",
                    changes={
                        "status": {
                            "old": old_enquiry_status,
                            "new": Enquiry.Status.ESTIMATION,
                        }
                    },
                )
            )
        publish(
            estimate_event(
                revised,
                actor,
                "estimation.estimate.revised",
                "CREATE",
                f"Estimate revision {revised.revision_number} created",
                metadata={"reason": reason, "supersedes_id": str(previous.pk)},
            )
        )
        return revised


def sync_estimate_approval(event):
    mapping = {
        "approval.request_approved": CommercialEstimate.Status.APPROVED,
        "approval.request_rejected": CommercialEstimate.Status.REJECTED,
        "approval.request_returned": CommercialEstimate.Status.RETURNED_FOR_CHANGES,
    }
    target = mapping.get(event.event_name)
    if not target:
        return
    request = ApprovalRequest.objects.filter(pk=event.entity_id, entity_type=ESTIMATE_ENTITY).first()
    if not request:
        return
    with transaction.atomic():
        estimate = (
            CommercialEstimate.objects.select_for_update()
            .select_related("enquiry", "enquiry__customer")
            .get(pk=request.entity_id)
        )
        if estimate.approval_request_id != request.pk:
            return
        old_status = estimate.status
        estimate.status = target
        estimate.updated_by_id = event.actor_user_id
        if target == CommercialEstimate.Status.APPROVED:
            estimate.approved_at = request.completed_at or timezone.now()
            estimate.approved_by_id = event.actor_user_id
        estimate.save()
        actor = User.objects.filter(pk=event.actor_user_id).first()
        if target == CommercialEstimate.Status.APPROVED and estimate.is_current:
            enquiry = Enquiry.objects.select_for_update().get(pk=estimate.enquiry_id)
            old_enquiry_status = enquiry.status
            enquiry.status = Enquiry.Status.ESTIMATION_COMPLETE
            enquiry.updated_by_id = event.actor_user_id
            enquiry.save(update_fields=["status", "updated_by", "updated_at"])
            publish(
                enquiry_event(
                    enquiry,
                    actor,
                    "enquiry.estimation_completed",
                    "STATUS_CHANGE",
                    f"{enquiry.enquiry_number} is ready for quotation",
                    metadata={"estimate_id": str(estimate.pk)},
                    changes={
                        "status": {
                            "old": old_enquiry_status,
                            "new": Enquiry.Status.ESTIMATION_COMPLETE,
                        }
                    },
                )
            )
        publish(
            estimate_event(
                estimate,
                actor,
                f"estimation.estimate.{target.lower()}",
                "APPROVE" if target == CommercialEstimate.Status.APPROVED else "STATUS_CHANGE",
                f"{estimate} {estimate.get_status_display().lower()}",
                changes={"status": {"old": old_status, "new": target}},
            )
        )
