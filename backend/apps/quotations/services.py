from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.approvals.models import ApprovalRequest
from apps.approvals.services import create_approval_request
from apps.core.conflicts import VersionConflict
from apps.core.domain_events import DomainEvent, publish
from apps.crm.models import Customer
from apps.enquiries.models import Enquiry
from apps.estimation.models import CommercialEstimate
from apps.masters.models import Currency
from apps.numbering.services import allocate_company_number
from apps.organization.models import Employee
from apps.rbac.services import has_permission

from .models import (
    CustomerCommercialConfirmation,
    Quotation,
    QuotationCommunication,
    QuotationLine,
    QuotationNegotiation,
    QuotationRevision,
)

EDITABLE_REVISION_FIELDS = {
    "issue_date",
    "valid_until",
    "introduction",
    "scope",
    "inclusions",
    "exclusions",
    "assumptions",
    "payment_terms",
    "delivery_terms",
    "warranty_terms",
    "freight_terms",
    "customer_notes",
}


def _employee(user):
    return Employee.objects.filter(user=user, user__is_active=True).first()


def _require(user, permission, context):
    if not has_permission(user, permission, context):
        raise PermissionDenied("You do not have permission to complete this quotation action.")


def _event(name, quotation, actor, action, summary, *, metadata=None, changes=None):
    employee = _employee(actor)
    return DomainEvent(
        event_name=name,
        entity_type="quotation",
        entity_id=quotation.pk,
        company_id=quotation.company_id,
        actor_user_id=actor.pk,
        actor_employee_id=employee.pk if employee else None,
        action=action,
        module="quotations",
        summary=summary,
        metadata={
            "entity_reference": quotation.quotation_number,
            "quotation_id": str(quotation.pk),
            "customer_id": str(quotation.customer_id),
            "enquiry_id": str(quotation.enquiry_id or ""),
            **(metadata or {}),
        },
        changes=changes or {},
    )


def _line_defaults(line, number):
    return {
        "line_number": number,
        "item_code": line.get("item_code", ""),
        "description": line["description"],
        "quantity": Decimal(str(line["quantity"])),
        "unit_of_measure": line.get("unit_of_measure", "NOS"),
        "unit_price": Decimal(str(line["unit_price"])),
        "discount_percent": Decimal(str(line.get("discount_percent", "0"))),
        "tax_percent": Decimal(str(line.get("tax_percent", "0"))),
        "is_optional": line.get("is_optional", False),
        "notes": line.get("notes", ""),
    }


def _replace_lines(revision, lines):
    if not lines:
        raise ValidationError({"lines": ["Add at least one customer-facing line item."]})
    revision.lines.all().delete()
    for number, line in enumerate(lines, 1):
        QuotationLine.objects.create(revision=revision, **_line_defaults(line, number))
    _recalculate(revision)


def _recalculate(revision):
    totals = revision.lines.filter(is_optional=False).aggregate(
        subtotal=Sum("line_subtotal"),
        discount=Sum("discount_amount"),
        taxable=Sum("taxable_amount"),
        tax=Sum("tax_amount"),
        total=Sum("total_amount"),
    )
    revision.subtotal = totals["subtotal"] or Decimal("0")
    revision.discount_amount = totals["discount"] or Decimal("0")
    revision.taxable_amount = totals["taxable"] or Decimal("0")
    revision.tax_amount = totals["tax"] or Decimal("0")
    revision.grand_total = totals["total"] or Decimal("0")
    revision.save(
        update_fields=[
            "subtotal",
            "discount_amount",
            "taxable_amount",
            "tax_amount",
            "grand_total",
            "updated_at",
        ]
    )


def _approved_estimate(estimate_id, company_id, enquiry_id):
    try:
        return CommercialEstimate.objects.select_related("currency", "enquiry").get(
            pk=estimate_id,
            company_id=company_id,
            enquiry_id=enquiry_id,
            is_current=True,
            status=CommercialEstimate.Status.APPROVED,
        )
    except CommercialEstimate.DoesNotExist as exc:
        raise ValidationError(
            {"estimate_id": ["Choose the approved current estimate for this enquiry."]}
        ) from exc


def _estimate_snapshot(estimate):
    if not estimate:
        return {}
    return {
        "estimate_id": str(estimate.pk),
        "estimate_number": estimate.estimate_number,
        "revision_number": estimate.revision_number,
        "approved_at": estimate.approved_at.isoformat() if estimate.approved_at else None,
        "proposed_selling_price": str(estimate.proposed_selling_price),
        "currency": estimate.currency.code,
    }


def create_quotation(*, actor, data):
    owner = _employee(actor)
    if not owner:
        raise PermissionDenied("Your account is not linked to an active employee.")
    _require(actor, "crm.quotation.create", {"company": owner.company_id})
    path = data["path"]
    if path == Quotation.Path.QUICK:
        _require(actor, "crm.quotation.quick_create", {"company": owner.company_id})
        if not data.get("quick_reason", "").strip():
            raise ValidationError({"quick_reason": ["Explain why this quick quotation is needed."]})
    customer = Customer.objects.filter(pk=data["customer_id"], company_id=owner.company_id).first()
    if not customer:
        raise ValidationError({"customer_id": ["Choose a customer from your company."]})
    enquiry = None
    if data.get("enquiry_id"):
        enquiry = Enquiry.objects.filter(
            pk=data["enquiry_id"], company_id=owner.company_id, customer=customer
        ).first()
        if not enquiry:
            raise ValidationError({"enquiry_id": ["Choose an enquiry for this customer."]})
    estimate = None
    currency = customer.default_currency
    lines = list(data.get("lines", []))
    if path == Quotation.Path.STANDARD:
        if not enquiry:
            raise ValidationError({"enquiry_id": ["Standard quotations require an enquiry."]})
        estimate = _approved_estimate(data.get("estimate_id"), owner.company_id, enquiry.pk)
        currency = estimate.currency
        if not lines:
            lines = [
                {
                    "description": enquiry.subject,
                    "quantity": Decimal("1"),
                    "unit_of_measure": "LOT",
                    "unit_price": estimate.proposed_selling_price,
                    "tax_percent": (
                        customer.default_tax.rate_percent if customer.default_tax_id else Decimal("0")
                    ),
                }
            ]
    elif data.get("currency_id"):
        currency = Currency.objects.filter(pk=data["currency_id"], is_active=True).first()
        if not currency:
            raise ValidationError({"currency_id": ["Choose an active currency."]})
    with transaction.atomic():
        number = allocate_company_number(company=owner.company, code="QUOTATION")
        quotation = Quotation.objects.create(
            company=owner.company,
            quotation_number=number,
            customer=customer,
            customer_contact_id=data.get("customer_contact_id"),
            enquiry=enquiry,
            estimate=estimate,
            path=path,
            quick_reason=data.get("quick_reason", ""),
            owner_id=data.get("owner_id") or owner.pk,
            created_by=actor,
        )
        revision = QuotationRevision.objects.create(
            quotation=quotation,
            revision_number=1,
            currency=currency,
            valid_until=data.get("valid_until"),
            introduction=data.get("introduction", ""),
            scope=data.get("scope", ""),
            payment_terms=data.get("payment_terms", ""),
            delivery_terms=data.get("delivery_terms", ""),
            warranty_terms=data.get("warranty_terms", ""),
            estimate_snapshot=_estimate_snapshot(estimate),
            created_by=actor,
        )
        _replace_lines(revision, lines)
        quotation.current_revision = revision
        quotation.save(update_fields=["current_revision", "updated_at"])
        if enquiry and enquiry.status == Enquiry.Status.ESTIMATION_COMPLETE:
            enquiry.status = Enquiry.Status.QUOTATION_PREPARATION
            enquiry.updated_by = actor
            enquiry.save(update_fields=["status", "updated_by", "updated_at"])
        publish(
            _event(
                "quotation.created",
                quotation,
                actor,
                "CREATE",
                f"Quotation {quotation.quotation_number} created",
                metadata={"status": quotation.status},
            )
        )
        return quotation


def update_revision(*, revision_id, actor, submitted_version, data):
    with transaction.atomic():
        revision = (
            QuotationRevision.objects.select_for_update()
            .select_related("quotation")
            .get(pk=revision_id)
        )
        _require(actor, "crm.quotation.change", revision.quotation)
        if revision.quotation.current_revision_id != revision.pk:
            raise ValidationError("Only the current quotation revision can be edited.")
        if revision.frozen_at or revision.status not in {
            QuotationRevision.Status.DRAFT,
            QuotationRevision.Status.RETURNED,
        }:
            raise ValidationError("This revision is frozen. Create a new revision for changes.")
        if revision.record_version != submitted_version:
            raise VersionConflict(revision.record_version)
        for field in EDITABLE_REVISION_FIELDS:
            if field in data:
                setattr(revision, field, data[field])
        revision.record_version += 1
        revision.save(update_fields=[*EDITABLE_REVISION_FIELDS, "record_version", "updated_at"])
        if "lines" in data:
            _replace_lines(revision, data["lines"])
        publish(
            _event(
                "quotation.updated",
                revision.quotation,
                actor,
                "UPDATE",
                f"Revision {revision.revision_number} updated",
                metadata={"status": revision.status},
            )
        )
        return revision


def finalize_revision(*, revision_id, actor, workflow_id=None, comment=""):
    with transaction.atomic():
        revision = QuotationRevision.objects.select_for_update().select_related("quotation").get(
            pk=revision_id
        )
        quotation = Quotation.objects.select_for_update().get(pk=revision.quotation_id)
        _require(actor, "crm.quotation.finalize", quotation)
        if quotation.current_revision_id != revision.pk or revision.frozen_at:
            raise ValidationError("Finalize the current editable revision.")
        if not revision.lines.exists():
            raise ValidationError("Add at least one quotation line before finalizing.")
        revision.commercial_snapshot = {
            "quotation_number": quotation.quotation_number,
            "revision_number": revision.revision_number,
            "currency": revision.currency.code,
            "grand_total": str(revision.grand_total),
        }
        if workflow_id:
            approval = create_approval_request(
                workflow_id=workflow_id,
                entity_type="quotation_revision",
                entity_id=revision.pk,
                actor=actor,
                submission_comment=comment,
                snapshot_metadata=revision.commercial_snapshot,
            )
            revision.approval_request = approval
            revision.status = QuotationRevision.Status.IN_APPROVAL
            quotation.status = Quotation.Status.IN_APPROVAL
        else:
            revision.status = QuotationRevision.Status.READY_TO_SEND
            quotation.status = Quotation.Status.READY_TO_SEND
        revision.save(
            update_fields=["commercial_snapshot", "approval_request", "status", "updated_at"]
        )
        quotation.save(update_fields=["status", "updated_at"])
        publish(
            _event(
                "quotation.finalized",
                quotation,
                actor,
                "SUBMIT",
                f"Revision {revision.revision_number} finalized",
                metadata={"status": quotation.status},
            )
        )
        return revision


def create_revision(*, quotation_id, actor):
    with transaction.atomic():
        quotation = Quotation.objects.select_for_update().get(pk=quotation_id)
        _require(actor, "crm.quotation.change", quotation)
        source = QuotationRevision.objects.select_for_update().get(pk=quotation.current_revision_id)
        next_number = source.revision_number + 1
        copied_fields = {
            field: getattr(source, field)
            for field in EDITABLE_REVISION_FIELDS
            if field not in {"issue_date"}
        }
        revision = QuotationRevision.objects.create(
            quotation=quotation,
            revision_number=next_number,
            currency=source.currency,
            issue_date=timezone.localdate(),
            estimate_snapshot=source.estimate_snapshot,
            supersedes=source,
            created_by=actor,
            **copied_fields,
        )
        for line in source.lines.order_by("line_number"):
            QuotationLine.objects.create(
                revision=revision,
                line_number=line.line_number,
                item_code=line.item_code,
                description=line.description,
                quantity=line.quantity,
                unit_of_measure=line.unit_of_measure,
                unit_price=line.unit_price,
                discount_percent=line.discount_percent,
                tax_percent=line.tax_percent,
                is_optional=line.is_optional,
                notes=line.notes,
            )
        _recalculate(revision)
        if not source.frozen_at and source.status in {
            QuotationRevision.Status.DRAFT,
            QuotationRevision.Status.RETURNED,
        }:
            source.status = QuotationRevision.Status.SUPERSEDED
            source.save(update_fields=["status", "updated_at"])
        quotation.current_revision = revision
        quotation.status = Quotation.Status.DRAFT
        quotation.save(update_fields=["current_revision", "status", "updated_at"])
        publish(
            _event(
                "quotation.revised",
                quotation,
                actor,
                "VERSION_CREATE",
                f"Revision {next_number} created",
                metadata={"status": quotation.status},
            )
        )
        return revision


def record_communication(*, revision_id, actor, data):
    with transaction.atomic():
        revision = QuotationRevision.objects.select_for_update().select_related("quotation").get(
            pk=revision_id
        )
        quotation = Quotation.objects.select_for_update().get(pk=revision.quotation_id)
        _require(actor, "crm.quotation.send", quotation)
        if data["direction"] == QuotationCommunication.Direction.OUTBOUND:
            if revision.status not in {
                QuotationRevision.Status.READY_TO_SEND,
                QuotationRevision.Status.APPROVED,
                QuotationRevision.Status.SENT,
            }:
                raise ValidationError("Finalize or approve this revision before recording it as sent.")
            if not revision.frozen_at:
                now = timezone.now()
                revision.frozen_at = now
                revision.frozen_reason = "Customer communication recorded"
                revision.sent_at = now
                revision.sent_by = actor
                revision.status = QuotationRevision.Status.SENT
                revision.save(
                    update_fields=[
                        "frozen_at",
                        "frozen_reason",
                        "sent_at",
                        "sent_by",
                        "status",
                        "updated_at",
                    ]
                )
                quotation.status = Quotation.Status.SENT
                quotation.save(update_fields=["status", "updated_at"])
                if quotation.enquiry_id:
                    Enquiry.objects.filter(pk=quotation.enquiry_id).update(
                        status=Enquiry.Status.QUOTATION_SENT, updated_by=actor, updated_at=now
                    )
        communication = QuotationCommunication.objects.create(
            revision=revision,
            channel=data["channel"],
            direction=data["direction"],
            occurred_at=data.get("occurred_at") or timezone.now(),
            contact_id=data.get("contact_id"),
            summary=data["summary"],
            manual_reference=data.get("manual_reference", ""),
            created_by=actor,
        )
        publish(
            _event(
                "quotation.communication_recorded",
                quotation,
                actor,
                "COMMUNICATE",
                f"{communication.get_channel_display()} communication recorded",
                metadata={"status": quotation.status},
            )
        )
        return communication


def record_negotiation(*, quotation_id, actor, data):
    with transaction.atomic():
        quotation = Quotation.objects.select_for_update().get(pk=quotation_id)
        _require(actor, "crm.quotation.negotiate", quotation)
        if quotation.status not in {Quotation.Status.SENT, Quotation.Status.UNDER_NEGOTIATION}:
            raise ValidationError("Record negotiation after the quotation has been sent.")
        follow_up_owner = None
        if data.get("follow_up_owner_id"):
            follow_up_owner = Employee.objects.filter(
                pk=data["follow_up_owner_id"], company_id=quotation.company_id
            ).first()
            if not follow_up_owner:
                raise ValidationError({"follow_up_owner_id": ["Choose an employee from this company."]})
        revision = QuotationRevision.objects.get(pk=quotation.current_revision_id)
        negotiation = QuotationNegotiation.objects.create(
            quotation=quotation,
            revision=revision,
            occurred_at=data.get("occurred_at") or timezone.now(),
            channel=data["channel"],
            summary=data["summary"],
            customer_request=data.get("customer_request", ""),
            our_response=data.get("our_response", ""),
            commercial_impact=data.get("commercial_impact", ""),
            material_change=data.get("material_change", False),
            follow_up_at=data.get("follow_up_at"),
            follow_up_owner=follow_up_owner,
            created_by=actor,
        )
        quotation.status = Quotation.Status.UNDER_NEGOTIATION
        quotation.save(update_fields=["status", "updated_at"])
        if quotation.enquiry_id:
            Enquiry.objects.filter(pk=quotation.enquiry_id).update(
                status=Enquiry.Status.NEGOTIATION, updated_by=actor, updated_at=timezone.now()
            )
        publish(
            _event(
                "quotation.negotiation_recorded",
                quotation,
                actor,
                "NEGOTIATE",
                "Quotation negotiation recorded",
                metadata={"status": quotation.status},
            )
        )
        return negotiation


def confirm_customer(*, quotation_id, actor, data):
    with transaction.atomic():
        quotation = Quotation.objects.select_for_update().get(pk=quotation_id)
        _require(actor, "crm.quotation.confirm", quotation)
        if quotation.status not in {
            Quotation.Status.SENT,
            Quotation.Status.UNDER_NEGOTIATION,
            Quotation.Status.ACCEPTED,
        }:
            raise ValidationError("Record confirmation for a sent quotation.")
        revision = QuotationRevision.objects.get(pk=quotation.current_revision_id)
        confirmation, _created = CustomerCommercialConfirmation.objects.update_or_create(
            quotation=quotation,
            defaults={
                "revision": revision,
                "method": data["method"],
                "confirmed_at": data.get("confirmed_at") or timezone.now(),
                "confirmation_reference": data.get("confirmation_reference", ""),
                "notes": data.get("notes", ""),
                "po_pending": data.get("po_pending", False),
                "po_number": data.get("po_number", ""),
                "po_date": data.get("po_date"),
                "po_document_id": data.get("po_document_id"),
                "confirmed_by": actor,
            },
        )
        quotation.status = Quotation.Status.ACCEPTED
        quotation.save(update_fields=["status", "updated_at"])
        publish(
            _event(
                "quotation.customer_confirmed",
                quotation,
                actor,
                "CONFIRM",
                f"Customer confirmation recorded by {confirmation.get_method_display()}",
                metadata={"status": quotation.status},
            )
        )
        return confirmation


def mark_ready_for_sales_order(*, quotation_id, actor):
    with transaction.atomic():
        quotation = Quotation.objects.select_for_update().get(pk=quotation_id)
        _require(actor, "crm.quotation.ready_for_sales_order", quotation)
        try:
            confirmation = CustomerCommercialConfirmation.objects.select_for_update().get(
                quotation=quotation
            )
        except CustomerCommercialConfirmation.DoesNotExist as exc:
            raise ValidationError("Record customer confirmation first.") from exc
        if confirmation.revision_id != quotation.current_revision_id:
            raise ValidationError("Confirmation must refer to the current quotation revision.")
        now = timezone.now()
        confirmation.ready_for_sales_order_at = now
        confirmation.ready_for_sales_order_by = actor
        confirmation.save(
            update_fields=["ready_for_sales_order_at", "ready_for_sales_order_by", "updated_at"]
        )
        quotation.status = Quotation.Status.READY_FOR_SALES_ORDER
        quotation.save(update_fields=["status", "updated_at"])
        if quotation.enquiry_id:
            Enquiry.objects.filter(pk=quotation.enquiry_id).update(
                status=Enquiry.Status.WON,
                closed_at=now,
                closed_by=actor,
                updated_by=actor,
                updated_at=now,
            )
        publish(
            _event(
                "quotation.ready_for_sales_order",
                quotation,
                actor,
                "HANDOFF",
                "Quotation marked Ready for Sales Order",
                metadata={"status": quotation.status},
            )
        )
        return confirmation


def compare_revisions(quotation):
    revisions = list(quotation.revisions.prefetch_related("lines").order_by("revision_number"))
    comparisons = []
    for previous, current in zip(revisions, revisions[1:], strict=False):
        changes = []
        for field in EDITABLE_REVISION_FIELDS | {"grand_total"}:
            old, new = getattr(previous, field), getattr(current, field)
            if old != new:
                changes.append({"field": field, "from": str(old or ""), "to": str(new or "")})
        previous_lines = {line.line_number: line for line in previous.lines.all()}
        current_lines = {line.line_number: line for line in current.lines.all()}
        for number in sorted(set(previous_lines) | set(current_lines)):
            old, new = previous_lines.get(number), current_lines.get(number)
            if old is None:
                changes.append({"field": f"line_{number}", "from": "", "to": new.description})
            elif new is None:
                changes.append({"field": f"line_{number}", "from": old.description, "to": ""})
            elif (old.description, old.quantity, old.unit_price) != (
                new.description,
                new.quantity,
                new.unit_price,
            ):
                changes.append(
                    {
                        "field": f"line_{number}",
                        "from": f"{old.description} · {old.quantity} × {old.unit_price}",
                        "to": f"{new.description} · {new.quantity} × {new.unit_price}",
                    }
                )
        comparisons.append(
            {
                "from_revision": previous.revision_number,
                "to_revision": current.revision_number,
                "changes": changes,
            }
        )
    return comparisons


def sync_quotation_approval(event):
    if event.entity_type != "approval_request" or event.event_name not in {
        "approval.request_approved",
        "approval.request_rejected",
        "approval.request_returned",
    }:
        return
    approval = ApprovalRequest.objects.filter(pk=event.entity_id).first()
    if not approval or approval.entity_type != "quotation_revision":
        return
    revision = QuotationRevision.objects.select_related("quotation").filter(
        pk=approval.entity_id
    ).first()
    if not revision:
        return
    statuses = {
        ApprovalRequest.Status.APPROVED: (
            QuotationRevision.Status.APPROVED,
            Quotation.Status.APPROVED,
        ),
        ApprovalRequest.Status.REJECTED: (
            QuotationRevision.Status.REJECTED,
            Quotation.Status.REJECTED,
        ),
        ApprovalRequest.Status.RETURNED_FOR_CHANGES: (
            QuotationRevision.Status.RETURNED,
            Quotation.Status.DRAFT,
        ),
    }
    if approval.status not in statuses:
        return
    revision_status, quotation_status = statuses[approval.status]
    QuotationRevision.objects.filter(pk=revision.pk).update(status=revision_status)
    Quotation.objects.filter(pk=revision.quotation_id).update(status=quotation_status)
