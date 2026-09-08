from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.approvals.conditions import conditions_match
from apps.approvals.models import ApprovalRequest, ApprovalWorkflow, ApprovalWorkflowVersion
from apps.approvals.services import create_approval_request
from apps.core.domain_events import DomainEvent, publish
from apps.inventory.models import StockItem, StockLocation
from apps.inventory.services import record_movement
from apps.numbering.services import allocate_company_number
from apps.organization.models import Employee
from apps.rbac.services import has_permission

from .models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequisition,
    PurchaseRequisitionLine,
)

ENTITY_TYPE_BY_MODEL = {
    PurchaseRequisition: "purchase_requisition",
    PurchaseOrder: "purchase_order",
    GoodsReceipt: "goods_receipt",
}
REFERENCE_FIELD_BY_MODEL = {
    PurchaseRequisition: "requisition_number",
    PurchaseOrder: "po_number",
    GoodsReceipt: "grn_number",
}


def _employee(user):
    return Employee.objects.filter(user=user, user__is_active=True).first()


def _require(user, permission, context, message="purchasing action"):
    if not has_permission(user, permission, context):
        raise PermissionDenied(f"You do not have permission to complete this {message}.")


def _event(name, entity, actor, action, summary, *, metadata=None, changes=None):
    employee = _employee(actor)
    entity_type = ENTITY_TYPE_BY_MODEL[type(entity)]
    reference = getattr(entity, REFERENCE_FIELD_BY_MODEL[type(entity)])
    return DomainEvent(
        event_name=name,
        entity_type=entity_type,
        entity_id=entity.pk,
        company_id=entity.company_id,
        actor_user_id=actor.pk,
        actor_employee_id=employee.pk if employee else None,
        action=action,
        module="purchasing",
        summary=summary,
        metadata={"entity_reference": reference, **(metadata or {})},
        changes=changes or {},
    )


def _matching_workflows(entity_type, entity):
    workflows = ApprovalWorkflow.objects.select_related("current_version").filter(
        company=entity.company,
        entity_type=entity_type,
        is_active=True,
        current_version__status=ApprovalWorkflowVersion.Status.ACTIVE,
    )
    return [workflow for workflow in workflows if conditions_match(workflow.current_version, entity)]


# --- Purchase Requisition -------------------------------------------------


@transaction.atomic
def create_purchase_requisition(*, company, actor, data, lines):
    _require(actor, "purchasing.requisition.create", company, "requisition creation")
    if not lines:
        raise ValidationError("Add at least one requested item.")
    requisition_number = allocate_company_number(company=company, code="PR")
    requisition = PurchaseRequisition.objects.create(
        company=company,
        requisition_number=requisition_number,
        created_by=actor,
        **data,
    )
    for index, line in enumerate(lines, start=1):
        PurchaseRequisitionLine.objects.create(requisition=requisition, line_number=index, **line)
    publish(
        _event(
            "purchase_requisition.created",
            requisition,
            actor,
            "CREATE",
            f"{requisition.requisition_number} created",
            metadata={"status": requisition.status},
        )
    )
    return requisition


@transaction.atomic
def submit_purchase_requisition(*, requisition_id, actor, comment=""):
    requisition = PurchaseRequisition.objects.select_for_update(of=("self",)).get(pk=requisition_id)
    _require(actor, "purchasing.requisition.submit", requisition, "requisition submission")
    if requisition.status not in {
        PurchaseRequisition.Status.DRAFT,
        PurchaseRequisition.Status.RETURNED,
    }:
        raise ValidationError("Only a draft requisition can be submitted.")
    if not requisition.lines.exists():
        raise ValidationError("Add at least one requested item before submitting.")
    matches = _matching_workflows("purchase_requisition", requisition)
    if len(matches) > 1:
        raise ValidationError("More than one approval workflow matches this requisition.")
    if matches:
        request = create_approval_request(
            workflow_id=matches[0].pk,
            entity_type="purchase_requisition",
            entity_id=requisition.pk,
            actor=actor,
            submission_comment=comment,
            snapshot_metadata={"requisition_number": requisition.requisition_number},
        )
        requisition.approval_request = request
        requisition.status = PurchaseRequisition.Status.PENDING_APPROVAL
    else:
        requisition.status = PurchaseRequisition.Status.APPROVED
        requisition.approved_by = actor
        requisition.approved_at = timezone.now()
    requisition.save()
    publish(
        _event(
            "purchase_requisition.submitted",
            requisition,
            actor,
            "SUBMIT",
            f"{requisition.requisition_number} submitted",
            metadata={"status": requisition.status},
        )
    )
    return requisition


def sync_purchase_requisition_approval(event):
    if event.entity_type != "approval_request" or event.event_name not in {
        "approval.request_approved",
        "approval.request_rejected",
        "approval.request_returned",
    }:
        return
    approval = ApprovalRequest.objects.filter(
        pk=event.entity_id, entity_type="purchase_requisition"
    ).first()
    if not approval:
        return
    requisition = PurchaseRequisition.objects.filter(pk=approval.entity_id).first()
    if not requisition:
        return
    if approval.status == ApprovalRequest.Status.APPROVED:
        requisition.status = PurchaseRequisition.Status.APPROVED
        requisition.approved_by_id = event.actor_user_id
        requisition.approved_at = timezone.now()
    elif approval.status == ApprovalRequest.Status.RETURNED_FOR_CHANGES:
        requisition.status = PurchaseRequisition.Status.RETURNED
    elif approval.status == ApprovalRequest.Status.REJECTED:
        requisition.status = PurchaseRequisition.Status.REJECTED
    requisition.save()


# --- Purchase Order --------------------------------------------------------


def _recalculate_po(order):
    totals = order.lines.aggregate(
        subtotal=Sum("line_subtotal"), tax=Sum("tax_amount"), total=Sum("total_amount")
    )
    order.subtotal = totals["subtotal"] or Decimal("0")
    order.tax_amount = totals["tax"] or Decimal("0")
    order.grand_total = totals["total"] or Decimal("0")
    order.save(update_fields=["subtotal", "tax_amount", "grand_total", "updated_at"])


@transaction.atomic
def create_purchase_order(*, company, actor, data, lines, requisition_id=None):
    _require(actor, "purchasing.purchase_order.create", company, "Purchase Order creation")
    if not lines:
        raise ValidationError("Add at least one ordered item.")
    requisition = None
    if requisition_id:
        requisition = PurchaseRequisition.objects.select_for_update(of=("self",)).get(
            pk=requisition_id, company=company
        )
        if requisition.status != PurchaseRequisition.Status.APPROVED:
            raise ValidationError("Only an approved requisition can be converted to a Purchase Order.")
    po_number = allocate_company_number(company=company, code="PO")
    order = PurchaseOrder.objects.create(
        company=company,
        po_number=po_number,
        requisition=requisition,
        created_by=actor,
        **data,
    )
    for index, line in enumerate(lines, start=1):
        PurchaseOrderLine.objects.create(order=order, line_number=index, **line)
    _recalculate_po(order)
    if requisition:
        requisition.status = PurchaseRequisition.Status.CONVERTED
        requisition.save(update_fields=["status", "updated_at"])
    publish(
        _event(
            "purchase_order.created",
            order,
            actor,
            "CREATE",
            f"{order.po_number} created",
            metadata={"status": order.status, "grand_total": str(order.grand_total)},
        )
    )
    return order


@transaction.atomic
def submit_purchase_order(*, order_id, actor, comment=""):
    order = PurchaseOrder.objects.select_for_update(of=("self",)).get(pk=order_id)
    _require(actor, "purchasing.purchase_order.submit", order, "Purchase Order submission")
    if order.status != PurchaseOrder.Status.DRAFT:
        raise ValidationError("Only a draft Purchase Order can be submitted.")
    if not order.lines.exists():
        raise ValidationError("Add at least one ordered item before submitting.")
    matches = _matching_workflows("purchase_order", order)
    if len(matches) > 1:
        raise ValidationError("More than one approval workflow matches this Purchase Order.")
    if matches:
        request = create_approval_request(
            workflow_id=matches[0].pk,
            entity_type="purchase_order",
            entity_id=order.pk,
            actor=actor,
            submission_comment=comment,
            snapshot_metadata={"po_number": order.po_number, "grand_total": str(order.grand_total)},
        )
        order.approval_request = request
        order.status = PurchaseOrder.Status.AWAITING_APPROVAL
        order.save(update_fields=["approval_request", "status", "updated_at"])
    else:
        order.status = PurchaseOrder.Status.ORDERED
        order.approved_by = actor
        order.approved_at = timezone.now()
        order.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    publish(
        _event(
            "purchase_order.submitted",
            order,
            actor,
            "SUBMIT",
            f"{order.po_number} submitted",
            metadata={"status": order.status},
        )
    )
    return order


def sync_purchase_order_approval(event):
    if event.entity_type != "approval_request" or event.event_name not in {
        "approval.request_approved",
        "approval.request_rejected",
        "approval.request_returned",
    }:
        return
    approval = ApprovalRequest.objects.filter(pk=event.entity_id, entity_type="purchase_order").first()
    if not approval:
        return
    order = PurchaseOrder.objects.filter(pk=approval.entity_id).first()
    if not order:
        return
    if approval.status == ApprovalRequest.Status.APPROVED:
        order.status = PurchaseOrder.Status.ORDERED
        order.approved_by_id = event.actor_user_id
        order.approved_at = timezone.now()
    elif approval.status == ApprovalRequest.Status.RETURNED_FOR_CHANGES:
        order.status = PurchaseOrder.Status.DRAFT
    elif approval.status == ApprovalRequest.Status.REJECTED:
        order.status = PurchaseOrder.Status.CANCELLED
    order.save()


@transaction.atomic
def cancel_purchase_order(*, order_id, actor, reason):
    order = PurchaseOrder.objects.select_for_update(of=("self",)).get(pk=order_id)
    _require(actor, "purchasing.purchase_order.cancel", order, "Purchase Order cancellation")
    if order.status in {PurchaseOrder.Status.FULLY_RECEIVED, PurchaseOrder.Status.CLOSED}:
        raise ValidationError("A fully received or closed Purchase Order cannot be cancelled.")
    order.status = PurchaseOrder.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    publish(
        _event(
            "purchase_order.cancelled",
            order,
            actor,
            "CANCEL",
            f"{order.po_number} cancelled",
            metadata={"reason": reason},
        )
    )
    return order


@transaction.atomic
def record_purchase_order_payment(*, order_id, actor, amount, payment_status, due_date=None):
    order = PurchaseOrder.objects.select_for_update(of=("self",)).get(pk=order_id)
    _require(actor, "purchasing.purchase_order.record_payment", order, "supplier payment recording")
    if amount < 0:
        raise ValidationError({"amount": "Payment amount cannot be negative."})
    order.paid_amount = order.paid_amount + amount
    order.payment_status = payment_status
    if due_date is not None:
        order.payment_due_date = due_date
    order.save(update_fields=["paid_amount", "payment_status", "payment_due_date", "updated_at"])
    publish(
        _event(
            "purchase_order.payment_recorded",
            order,
            actor,
            "UPDATE",
            f"{order.po_number} payment recorded",
            metadata={"amount": str(amount), "payment_status": order.payment_status},
        )
    )
    return order


# --- Goods Receipt (GRN) ----------------------------------------------------


@transaction.atomic
def create_goods_receipt(*, company, actor, purchase_order_id, data, lines):
    order = PurchaseOrder.objects.select_for_update(of=("self",)).get(pk=purchase_order_id, company=company)
    _require(actor, "purchasing.goods_receipt.create", order, "GRN creation")
    if order.status not in {
        PurchaseOrder.Status.ORDERED,
        PurchaseOrder.Status.PART_RECEIVED,
        PurchaseOrder.Status.DELAYED,
    }:
        raise ValidationError("Only an ordered Purchase Order can receive goods.")
    if not lines:
        raise ValidationError("Record at least one received item.")
    grn_number = allocate_company_number(company=company, code="GRN")
    receipt = GoodsReceipt.objects.create(
        company=company, grn_number=grn_number, purchase_order=order, created_by=actor, **data
    )
    for line in lines:
        order_line = PurchaseOrderLine.objects.select_for_update(of=("self",)).get(
            pk=line["order_line"], order=order
        )
        if line["quantity_received"] > order_line.pending_quantity:
            raise ValidationError(
                f"Line {order_line.line_number}: cannot receive more than the pending quantity "
                f"({order_line.pending_quantity})."
            )
        GoodsReceiptLine.objects.create(
            receipt=receipt,
            order_line=order_line,
            quantity_received=line["quantity_received"],
            condition=line.get("condition", "AVAILABLE"),
        )
    publish(
        _event(
            "goods_receipt.created",
            receipt,
            actor,
            "CREATE",
            f"{receipt.grn_number} created for {order.po_number}",
        )
    )
    return receipt


@transaction.atomic
def confirm_goods_receipt(*, receipt_id, actor, warehouse_location_id=None):
    receipt = (
        GoodsReceipt.objects.select_for_update(of=("self",))
        .select_related("purchase_order")
        .get(pk=receipt_id)
    )
    _require(actor, "purchasing.goods_receipt.confirm", receipt, "GRN confirmation")
    if receipt.status != GoodsReceipt.Status.DRAFT:
        raise ValidationError("Only a draft GRN can be confirmed.")
    order = PurchaseOrder.objects.select_for_update(of=("self",)).get(pk=receipt.purchase_order_id)
    if warehouse_location_id:
        location = StockLocation.objects.get(pk=warehouse_location_id, warehouse=order.warehouse)
    else:
        location, _ = StockLocation.objects.get_or_create(warehouse=order.warehouse, bin_code="")

    for line in receipt.lines.select_related("order_line").select_for_update(of=("self",)):
        order_line = PurchaseOrderLine.objects.select_for_update(of=("self",)).get(pk=line.order_line_id)
        record_movement(
            company=order.company,
            movement_type="INWARD",
            product=order_line.product,
            quantity=line.quantity_received,
            to_location=location,
            to_condition=line.condition or StockItem.Condition.AVAILABLE,
            reference_type="goods_receipt",
            reference_id=receipt.pk,
            reason=f"GRN {receipt.grn_number} against {order.po_number}",
            actor=actor,
        )
        order_line.received_quantity = order_line.received_quantity + line.quantity_received
        order_line.save(update_fields=["received_quantity"])

    receipt.status = GoodsReceipt.Status.CONFIRMED
    receipt.confirmed_by = actor
    receipt.confirmed_at = timezone.now()
    receipt.save(update_fields=["status", "confirmed_by", "confirmed_at", "updated_at"])

    all_lines = list(order.lines.all())
    if all(line.received_quantity >= line.quantity for line in all_lines):
        order.status = PurchaseOrder.Status.FULLY_RECEIVED
    elif any(line.received_quantity > 0 for line in all_lines):
        order.status = PurchaseOrder.Status.PART_RECEIVED
    order.save(update_fields=["status", "updated_at"])

    publish(
        _event(
            "goods_receipt.confirmed",
            receipt,
            actor,
            "STATUS_CHANGE",
            f"{receipt.grn_number} confirmed, stock updated",
            metadata={"purchase_order_status": order.status},
        )
    )
    return receipt
