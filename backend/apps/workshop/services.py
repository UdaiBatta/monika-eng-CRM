from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_events import DomainEvent, publish
from apps.inventory.services import record_movement
from apps.numbering.services import allocate_company_number
from apps.organization.models import Employee
from apps.projects.models import Project, ProjectEngineeringHandoff
from apps.rbac.services import has_permission

from .models import PanelJob, PanelJobMaterialLine, PanelJobStageEvent

FORWARD_STAGES = [
    PanelJob.Status.REQUIREMENT_REVIEW,
    PanelJob.Status.MATERIAL_PLANNING,
    PanelJob.Status.READY_FOR_ASSEMBLY,
    PanelJob.Status.ASSEMBLY,
    PanelJob.Status.WIRING,
    PanelJob.Status.TESTING,
    PanelJob.Status.QUALITY_CHECK,
    PanelJob.Status.FITTING_INSTALLATION,
    PanelJob.Status.HANDOVER,
    PanelJob.Status.CLOSED,
]


def _employee(user):
    return Employee.objects.filter(user=user, user__is_active=True).first()


def _require(user, permission, context, message="Panel Job action"):
    if not has_permission(user, permission, context):
        raise PermissionDenied(f"You do not have permission to complete this {message}.")


def _event(name, panel_job, actor, action, summary, *, metadata=None):
    employee = _employee(actor)
    return DomainEvent(
        event_name=name,
        entity_type="panel_job",
        entity_id=panel_job.pk,
        company_id=panel_job.company_id,
        actor_user_id=actor.pk,
        actor_employee_id=employee.pk if employee else None,
        action=action,
        module="workshop",
        summary=summary,
        metadata={"entity_reference": panel_job.panel_job_number, **(metadata or {})},
    )


def _log_stage(panel_job, *, from_status, to_status, actor, notes=""):
    PanelJobStageEvent.objects.create(
        panel_job=panel_job, from_status=from_status, to_status=to_status, actor=actor, notes=notes
    )


@transaction.atomic
def create_panel_job_from_project(*, project_id, actor, data, material_lines=()):
    project = Project.objects.select_for_update(of=("self",)).select_related("engineering_handoff").get(
        pk=project_id
    )
    _require(actor, "workshop.panel_job.create", project, "Panel Job creation")
    if project.status != Project.Status.ENGINEERING_ACCEPTED:
        raise ValidationError("Only a project with an accepted Workshop handoff can start a Panel Job.")
    handoff = getattr(project, "engineering_handoff", None)
    if not handoff or handoff.status != ProjectEngineeringHandoff.Status.ACCEPTED:
        raise ValidationError("The Workshop handoff for this project must be accepted first.")

    panel_job_number = allocate_company_number(company=project.company, code="PANEL")
    panel_job = PanelJob.objects.create(
        company=project.company,
        panel_job_number=panel_job_number,
        project=project,
        created_by=actor,
        **data,
    )
    for index, line in enumerate(material_lines, start=1):
        PanelJobMaterialLine.objects.create(panel_job=panel_job, line_number=index, **line)
    if material_lines:
        panel_job.status = PanelJob.Status.MATERIAL_PLANNING
        panel_job.save(update_fields=["status", "updated_at"])
    _log_stage(panel_job, from_status="", to_status=panel_job.status, actor=actor, notes="Panel Job created")
    publish(
        _event(
            "panel_job.created",
            panel_job,
            actor,
            "CREATE",
            f"{panel_job.panel_job_number} created for {project.project_number}",
        )
    )
    return panel_job


@transaction.atomic
def add_material_line(*, panel_job_id, actor, product, required_quantity, notes=""):
    panel_job = PanelJob.objects.select_for_update(of=("self",)).get(pk=panel_job_id)
    _require(actor, "workshop.panel_job.plan_material", panel_job, "material planning")
    if panel_job.status not in {PanelJob.Status.REQUIREMENT_REVIEW, PanelJob.Status.MATERIAL_PLANNING}:
        raise ValidationError("Material can only be planned before assembly starts.")
    next_line_number = (panel_job.material_lines.count() or 0) + 1
    line = PanelJobMaterialLine.objects.create(
        panel_job=panel_job,
        line_number=next_line_number,
        product=product,
        required_quantity=required_quantity,
        notes=notes,
    )
    if panel_job.status == PanelJob.Status.REQUIREMENT_REVIEW:
        panel_job.status = PanelJob.Status.MATERIAL_PLANNING
        panel_job.save(update_fields=["status", "updated_at"])
    return line


@transaction.atomic
def reserve_panel_job_materials(*, panel_job_id, actor, location):
    panel_job = PanelJob.objects.select_for_update(of=("self",)).get(pk=panel_job_id)
    _require(actor, "workshop.panel_job.reserve_stock", panel_job, "stock reservation")
    if panel_job.status not in {PanelJob.Status.MATERIAL_PLANNING, PanelJob.Status.MATERIAL_SHORTAGE}:
        raise ValidationError("Reserve stock only while planning material for this Panel Job.")
    lines = list(panel_job.material_lines.select_for_update(of=("self",)).select_related("product"))
    if not lines:
        raise ValidationError("Add at least one material line before reserving stock.")
    shortage = False
    for line in lines:
        outstanding = line.required_quantity - line.reserved_quantity
        if outstanding <= 0:
            continue
        available = _available_quantity(line.product, location)
        to_reserve = min(outstanding, available)
        if to_reserve > 0:
            record_movement(
                company=panel_job.company,
                movement_type="RESERVE",
                product=line.product,
                quantity=to_reserve,
                from_location=location,
                from_condition="AVAILABLE",
                to_location=location,
                to_condition="RESERVED",
                reference_type="panel_job",
                reference_id=panel_job.pk,
                reason=f"Reserved for {panel_job.panel_job_number}",
                actor=actor,
            )
            line.reserved_quantity = line.reserved_quantity + to_reserve
            line.save(update_fields=["reserved_quantity"])
        if to_reserve < outstanding:
            shortage = True
    previous_status = panel_job.status
    panel_job.status = PanelJob.Status.MATERIAL_SHORTAGE if shortage else PanelJob.Status.READY_FOR_ASSEMBLY
    panel_job.save(update_fields=["status", "updated_at"])
    if previous_status != panel_job.status:
        _log_stage(panel_job, from_status=previous_status, to_status=panel_job.status, actor=actor)
        publish(
            _event(
                "panel_job.stock_reserved",
                panel_job,
                actor,
                "STATUS_CHANGE",
                f"{panel_job.panel_job_number} stock reservation: {panel_job.get_status_display()}",
            )
        )
    return panel_job


def _available_quantity(product, location):
    from apps.inventory.models import StockItem

    item = StockItem.objects.filter(product=product, location=location, condition="AVAILABLE").first()
    return item.quantity if item else Decimal("0")


ADVANCE_TARGETS = {
    PanelJob.Status.READY_FOR_ASSEMBLY: PanelJob.Status.ASSEMBLY,
    PanelJob.Status.ASSEMBLY: PanelJob.Status.WIRING,
    PanelJob.Status.WIRING: PanelJob.Status.TESTING,
    PanelJob.Status.TESTING: PanelJob.Status.QUALITY_CHECK,
    PanelJob.Status.FITTING_INSTALLATION: PanelJob.Status.HANDOVER,
}
STAGE_PERMISSION = {
    PanelJob.Status.ASSEMBLY: "workshop.panel_job.assemble",
    PanelJob.Status.WIRING: "workshop.panel_job.wire",
    PanelJob.Status.TESTING: "workshop.panel_job.test",
    PanelJob.Status.QUALITY_CHECK: "workshop.panel_job.quality_check",
    PanelJob.Status.HANDOVER: "workshop.panel_job.handover",
}


@transaction.atomic
def advance_panel_job_stage(*, panel_job_id, actor, notes=""):
    panel_job = PanelJob.objects.select_for_update(of=("self",)).get(pk=panel_job_id)
    next_status = ADVANCE_TARGETS.get(panel_job.status)
    if not next_status:
        raise ValidationError(f"Cannot advance a Panel Job from {panel_job.get_status_display()}.")
    permission = STAGE_PERMISSION.get(next_status, "workshop.panel_job.advance")
    _require(actor, permission, panel_job, "Panel Job stage change")
    previous_status = panel_job.status
    panel_job.status = next_status
    panel_job.save(update_fields=["status", "updated_at"])
    _log_stage(panel_job, from_status=previous_status, to_status=next_status, actor=actor, notes=notes)
    publish(
        _event(
            "panel_job.stage_advanced",
            panel_job,
            actor,
            "STATUS_CHANGE",
            f"{panel_job.panel_job_number} moved to {panel_job.get_status_display()}",
        )
    )
    return panel_job


@transaction.atomic
def record_quality_check(*, panel_job_id, actor, passed, notes):
    panel_job = PanelJob.objects.select_for_update(of=("self",)).get(pk=panel_job_id)
    _require(actor, "workshop.panel_job.quality_check", panel_job, "quality check")
    if panel_job.status != PanelJob.Status.QUALITY_CHECK:
        raise ValidationError("Quality check can only be recorded during the Quality Check stage.")
    panel_job.quality_passed = passed
    panel_job.quality_check_notes = notes
    previous_status = panel_job.status
    panel_job.status = (
        PanelJob.Status.FITTING_INSTALLATION if passed else PanelJob.Status.TESTING
    )
    panel_job.save(update_fields=["quality_passed", "quality_check_notes", "status", "updated_at"])
    _log_stage(
        panel_job,
        from_status=previous_status,
        to_status=panel_job.status,
        actor=actor,
        notes=notes,
    )
    result_text = "passed" if passed else "failed, back to Testing"
    publish(
        _event(
            "panel_job.quality_check_recorded",
            panel_job,
            actor,
            "STATUS_CHANGE",
            f"{panel_job.panel_job_number} quality check: {result_text}",
        )
    )
    return panel_job


@transaction.atomic
def record_material_movement(*, panel_job_id, actor, material_line_id, movement_type, quantity, location):
    panel_job = PanelJob.objects.select_for_update(of=("self",)).get(pk=panel_job_id)
    _require(actor, "workshop.panel_job.record_material", panel_job, "material issue/consumption/return")
    line = PanelJobMaterialLine.objects.select_for_update(of=("self",)).get(
        pk=material_line_id, panel_job=panel_job
    )
    if movement_type == "ISSUE":
        record_movement(
            company=panel_job.company,
            movement_type="OUTWARD",
            product=line.product,
            quantity=quantity,
            from_location=location,
            from_condition="RESERVED",
            reference_type="panel_job",
            reference_id=panel_job.pk,
            reason=f"Issued to {panel_job.panel_job_number}",
            actor=actor,
        )
        line.issued_quantity = line.issued_quantity + quantity
        line.reserved_quantity = max(line.reserved_quantity - quantity, Decimal("0"))
        line.save(update_fields=["issued_quantity", "reserved_quantity"])
    elif movement_type == "CONSUME":
        outstanding_issued = line.issued_quantity - line.consumed_quantity - line.returned_quantity
        if quantity > outstanding_issued:
            raise ValidationError(
                f"Only {outstanding_issued} of this material has been issued and not yet "
                "consumed or returned."
            )
        line.consumed_quantity = line.consumed_quantity + quantity
        line.save(update_fields=["consumed_quantity"])
    elif movement_type == "RETURN":
        outstanding_issued = line.issued_quantity - line.consumed_quantity - line.returned_quantity
        if quantity > outstanding_issued:
            raise ValidationError(
                f"Only {outstanding_issued} of this material has been issued and not yet "
                "consumed or returned."
            )
        record_movement(
            company=panel_job.company,
            movement_type="RETURN",
            product=line.product,
            quantity=quantity,
            to_location=location,
            to_condition="AVAILABLE",
            reference_type="panel_job",
            reference_id=panel_job.pk,
            reason=f"Returned from {panel_job.panel_job_number}",
            actor=actor,
        )
        line.returned_quantity = line.returned_quantity + quantity
        line.save(update_fields=["returned_quantity"])
    else:
        raise ValidationError({"movement_type": ["Choose ISSUE, CONSUME, or RETURN."]})
    return line


@transaction.atomic
def handover_panel_job(*, panel_job_id, actor, notes=""):
    panel_job = PanelJob.objects.select_for_update(of=("self",)).get(pk=panel_job_id)
    _require(actor, "workshop.panel_job.handover", panel_job, "Panel Job handover")
    if panel_job.status != PanelJob.Status.HANDOVER:
        raise ValidationError("The Panel Job must reach the Handover stage first.")
    panel_job.status = PanelJob.Status.CLOSED
    panel_job.handover_notes = notes
    panel_job.handed_over_by = actor
    panel_job.handed_over_at = timezone.now()
    panel_job.save(
        update_fields=["status", "handover_notes", "handed_over_by", "handed_over_at", "updated_at"]
    )
    _log_stage(
        panel_job,
        from_status=PanelJob.Status.HANDOVER,
        to_status=PanelJob.Status.CLOSED,
        actor=actor,
        notes=notes,
    )
    publish(
        _event(
            "panel_job.handed_over",
            panel_job,
            actor,
            "STATUS_CHANGE",
            f"{panel_job.panel_job_number} handed over and closed",
        )
    )
    return panel_job


@transaction.atomic
def hold_panel_job(*, panel_job_id, actor, reason):
    panel_job = PanelJob.objects.select_for_update(of=("self",)).get(pk=panel_job_id)
    _require(actor, "workshop.panel_job.hold", panel_job, "Panel Job hold")
    if panel_job.status in {PanelJob.Status.CLOSED, PanelJob.Status.CANCELLED, PanelJob.Status.ON_HOLD}:
        raise ValidationError("This Panel Job cannot be put on hold from its current status.")
    previous_status = panel_job.status
    panel_job.status = PanelJob.Status.ON_HOLD
    panel_job.save(update_fields=["status", "updated_at"])
    _log_stage(panel_job, from_status=previous_status, to_status=panel_job.status, actor=actor, notes=reason)
    publish(
        _event(
            "panel_job.held",
            panel_job,
            actor,
            "STATUS_CHANGE",
            f"{panel_job.panel_job_number} put on hold",
            metadata={"reason": reason, "previous_status": previous_status},
        )
    )
    return panel_job


@transaction.atomic
def resume_panel_job(*, panel_job_id, actor):
    panel_job = PanelJob.objects.select_for_update(of=("self",)).get(pk=panel_job_id)
    _require(actor, "workshop.panel_job.hold", panel_job, "Panel Job resume")
    if panel_job.status != PanelJob.Status.ON_HOLD:
        raise ValidationError("Only a Panel Job on hold can be resumed.")
    last_event = panel_job.stage_events.exclude(to_status=PanelJob.Status.ON_HOLD).first()
    resumed_status = last_event.to_status if last_event else PanelJob.Status.REQUIREMENT_REVIEW
    panel_job.status = resumed_status
    panel_job.save(update_fields=["status", "updated_at"])
    _log_stage(panel_job, from_status=PanelJob.Status.ON_HOLD, to_status=panel_job.status, actor=actor)
    publish(
        _event(
            "panel_job.resumed",
            panel_job,
            actor,
            "STATUS_CHANGE",
            f"{panel_job.panel_job_number} resumed",
        )
    )
    return panel_job


@transaction.atomic
def cancel_panel_job(*, panel_job_id, actor, reason):
    panel_job = PanelJob.objects.select_for_update(of=("self",)).get(pk=panel_job_id)
    _require(actor, "workshop.panel_job.cancel", panel_job, "Panel Job cancellation")
    if panel_job.status in {PanelJob.Status.CLOSED, PanelJob.Status.CANCELLED}:
        raise ValidationError("This Panel Job cannot be cancelled from its current status.")
    previous_status = panel_job.status
    panel_job.status = PanelJob.Status.CANCELLED
    panel_job.save(update_fields=["status", "updated_at"])
    _log_stage(panel_job, from_status=previous_status, to_status=panel_job.status, actor=actor, notes=reason)
    publish(
        _event(
            "panel_job.cancelled",
            panel_job,
            actor,
            "CANCEL",
            f"{panel_job.panel_job_number} cancelled",
            metadata={"reason": reason},
        )
    )
    return panel_job
