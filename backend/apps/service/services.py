from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_events import DomainEvent, publish
from apps.inventory.services import record_movement
from apps.numbering.services import allocate_company_number
from apps.organization.models import Employee
from apps.rbac.services import has_permission

from .models import ServiceJobLine, ServiceTicket, ServiceTicketStageEvent

VALID_TRANSITIONS = {
    ServiceTicket.Status.NEW: {ServiceTicket.Status.ASSIGNED, ServiceTicket.Status.CANCELLED},
    ServiceTicket.Status.ASSIGNED: {
        ServiceTicket.Status.AWAITING_PARTS,
        ServiceTicket.Status.UNDER_REPAIR,
        ServiceTicket.Status.CANCELLED,
    },
    ServiceTicket.Status.AWAITING_PARTS: {
        ServiceTicket.Status.UNDER_REPAIR,
        ServiceTicket.Status.CANCELLED,
    },
    ServiceTicket.Status.UNDER_REPAIR: {
        ServiceTicket.Status.AWAITING_PARTS,
        ServiceTicket.Status.AWAITING_CUSTOMER_APPROVAL,
        ServiceTicket.Status.READY_FOR_DISPATCH,
        ServiceTicket.Status.CANCELLED,
    },
    ServiceTicket.Status.AWAITING_CUSTOMER_APPROVAL: {
        ServiceTicket.Status.UNDER_REPAIR,
        ServiceTicket.Status.READY_FOR_DISPATCH,
        ServiceTicket.Status.CANCELLED,
    },
    ServiceTicket.Status.READY_FOR_DISPATCH: {ServiceTicket.Status.CLOSED, ServiceTicket.Status.CANCELLED},
}


def _employee(user):
    return Employee.objects.filter(user=user, user__is_active=True).first()


def _require(user, permission, context, message="service action"):
    if not has_permission(user, permission, context):
        raise PermissionDenied(f"You do not have permission to complete this {message}.")


def _event(name, ticket, actor, action, summary, *, metadata=None):
    employee = _employee(actor)
    return DomainEvent(
        event_name=name,
        entity_type="service_ticket",
        entity_id=ticket.pk,
        company_id=ticket.company_id,
        actor_user_id=actor.pk,
        actor_employee_id=employee.pk if employee else None,
        action=action,
        module="service",
        summary=summary,
        metadata={"entity_reference": ticket.ticket_number, **(metadata or {})},
    )


def _log_stage(ticket, *, from_status, to_status, actor, notes=""):
    ServiceTicketStageEvent.objects.create(
        ticket=ticket, from_status=from_status, to_status=to_status, actor=actor, notes=notes
    )


@transaction.atomic
def create_service_ticket(*, company, actor, data):
    _require(actor, "service.ticket.create", company, "Service Ticket creation")
    ticket_number = allocate_company_number(company=company, code="SVC")
    ticket = ServiceTicket.objects.create(
        company=company, ticket_number=ticket_number, created_by=actor, **data
    )
    _log_stage(ticket, from_status="", to_status=ticket.status, actor=actor, notes="Ticket created")
    publish(
        _event("service_ticket.created", ticket, actor, "CREATE", f"{ticket.ticket_number} created")
    )
    return ticket


def _transition(*, ticket, to_status, actor, message, notes=""):
    if to_status not in VALID_TRANSITIONS.get(ticket.status, set()):
        raise ValidationError(
            f"Cannot move {ticket.get_status_display()} to {ServiceTicket.Status(to_status).label}."
        )
    previous_status = ticket.status
    ticket.status = to_status
    update_fields = ["status", "updated_at"]
    if to_status == ServiceTicket.Status.CLOSED:
        ticket.closed_at = timezone.now()
        ticket.closed_by = actor
        update_fields += ["closed_at", "closed_by"]
    ticket.save(update_fields=update_fields)
    _log_stage(ticket, from_status=previous_status, to_status=to_status, actor=actor, notes=notes)
    publish(
        _event(
            "service_ticket.status_changed",
            ticket,
            actor,
            "STATUS_CHANGE",
            f"{ticket.ticket_number} moved to {ticket.get_status_display()}",
            metadata={"notes": notes},
        )
    )
    return ticket


@transaction.atomic
def assign_technician(*, ticket_id, actor, technician_id, scheduled_visit_at=None):
    ticket = ServiceTicket.objects.select_for_update(of=("self",)).get(pk=ticket_id)
    _require(actor, "service.ticket.assign", ticket, "technician assignment")
    technician = Employee.objects.get(pk=technician_id, company=ticket.company)
    ticket.technician = technician
    if scheduled_visit_at is not None:
        ticket.scheduled_visit_at = scheduled_visit_at
    ticket.save(update_fields=["technician", "scheduled_visit_at", "updated_at"])
    if ticket.status == ServiceTicket.Status.NEW:
        return _transition(
            ticket=ticket,
            to_status=ServiceTicket.Status.ASSIGNED,
            actor=actor,
            message="assignment",
            notes=f"Assigned to {technician.display_name}",
        )
    publish(
        _event(
            "service_ticket.technician_assigned",
            ticket,
            actor,
            "ASSIGN",
            f"{ticket.ticket_number} assigned to {technician.display_name}",
        )
    )
    return ticket


@transaction.atomic
def record_diagnosis(*, ticket_id, actor, diagnosis):
    ticket = ServiceTicket.objects.select_for_update(of=("self",)).get(pk=ticket_id)
    _require(actor, "service.ticket.diagnose", ticket, "diagnosis recording")
    ticket.diagnosis = diagnosis
    ticket.save(update_fields=["diagnosis", "updated_at"])
    publish(
        _event(
            "service_ticket.diagnosis_recorded",
            ticket,
            actor,
            "UPDATE",
            f"{ticket.ticket_number} diagnosis recorded",
        )
    )
    return ticket


@transaction.atomic
def add_job_line(*, ticket_id, actor, line_type, description, quantity, unit_price, product=None):
    ticket = ServiceTicket.objects.select_for_update(of=("self",)).get(pk=ticket_id)
    _require(actor, "service.ticket.record_parts_labour", ticket, "parts/labour recording")
    next_line_number = (ticket.job_lines.count() or 0) + 1
    line = ServiceJobLine.objects.create(
        ticket=ticket,
        line_number=next_line_number,
        line_type=line_type,
        product=product,
        description=description,
        quantity=quantity,
        unit_price=unit_price,
    )
    return line


@transaction.atomic
def consume_part(*, ticket_id, actor, job_line_id, location):
    ticket = ServiceTicket.objects.select_for_update(of=("self",)).get(pk=ticket_id)
    _require(actor, "service.ticket.record_parts_labour", ticket, "part consumption")
    line = ServiceJobLine.objects.select_for_update(of=("self",)).get(pk=job_line_id, ticket=ticket)
    if line.line_type != ServiceJobLine.LineType.PART or not line.product_id:
        raise ValidationError("Only part lines with a linked product can be consumed from stock.")
    outstanding = line.quantity - line.consumed_quantity
    if outstanding <= 0:
        raise ValidationError("This part has already been fully consumed.")
    record_movement(
        company=ticket.company,
        movement_type="SERVICE_CONSUMPTION",
        product=line.product,
        quantity=outstanding,
        from_location=location,
        from_condition="AVAILABLE",
        reference_type="service_ticket",
        reference_id=ticket.pk,
        reason=f"Consumed for {ticket.ticket_number}",
        actor=actor,
    )
    line.consumed_quantity = line.quantity
    line.save(update_fields=["consumed_quantity"])
    return line


@transaction.atomic
def link_quotation(*, ticket_id, actor, quotation_id):
    ticket = ServiceTicket.objects.select_for_update(of=("self",)).get(pk=ticket_id)
    _require(actor, "service.ticket.link_quotation", ticket, "quotation linking")
    from apps.quotations.models import Quotation

    quotation = Quotation.objects.get(pk=quotation_id, customer=ticket.customer)
    ticket.quotation = quotation
    ticket.save(update_fields=["quotation", "updated_at"])
    if ticket.status in {ServiceTicket.Status.UNDER_REPAIR, ServiceTicket.Status.ASSIGNED}:
        return _transition(
            ticket=ticket,
            to_status=ServiceTicket.Status.AWAITING_CUSTOMER_APPROVAL,
            actor=actor,
            message="quotation sent",
            notes=f"Quotation {quotation.quotation_number} linked",
        )
    return ticket


@transaction.atomic
def change_status(*, ticket_id, actor, to_status, notes=""):
    ticket = ServiceTicket.objects.select_for_update(of=("self",)).get(pk=ticket_id)
    permission = {
        ServiceTicket.Status.UNDER_REPAIR: "service.ticket.repair",
        ServiceTicket.Status.AWAITING_PARTS: "service.ticket.repair",
        ServiceTicket.Status.READY_FOR_DISPATCH: "service.ticket.dispatch",
        ServiceTicket.Status.CANCELLED: "service.ticket.cancel",
    }.get(to_status, "service.ticket.repair")
    _require(actor, permission, ticket, "Service Ticket status change")
    return _transition(ticket=ticket, to_status=to_status, actor=actor, message="status change", notes=notes)


@transaction.atomic
def dispatch_ticket(*, ticket_id, actor, dispatch_reference, warranty_claim=False):
    ticket = ServiceTicket.objects.select_for_update(of=("self",)).get(pk=ticket_id)
    _require(actor, "service.ticket.dispatch", ticket, "dispatch")
    if ticket.status != ServiceTicket.Status.READY_FOR_DISPATCH:
        raise ValidationError("Only a ticket ready for dispatch can be dispatched.")
    ticket.dispatched_at = timezone.now()
    ticket.dispatch_reference = dispatch_reference
    ticket.warranty_claim = warranty_claim
    ticket.save(update_fields=["dispatched_at", "dispatch_reference", "warranty_claim", "updated_at"])
    publish(
        _event(
            "service_ticket.dispatched",
            ticket,
            actor,
            "UPDATE",
            f"{ticket.ticket_number} dispatched",
            metadata={"dispatch_reference": dispatch_reference, "warranty_claim": warranty_claim},
        )
    )
    return ticket


@transaction.atomic
def close_ticket(*, ticket_id, actor, notes=""):
    ticket = ServiceTicket.objects.select_for_update(of=("self",)).get(pk=ticket_id)
    _require(actor, "service.ticket.close", ticket, "Service Ticket closure")
    return _transition(
        ticket=ticket, to_status=ServiceTicket.Status.CLOSED, actor=actor, message="closure", notes=notes
    )
