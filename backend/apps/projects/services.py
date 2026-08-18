from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.conflicts import VersionConflict
from apps.core.domain_events import DomainEvent, publish
from apps.documents.models import Document
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.numbering.services import allocate_company_number
from apps.organization.models import Employee
from apps.rbac.services import has_permission
from apps.sales.models import SalesOrder

from .models import Project, ProjectEngineeringHandoff, ProjectHandoffClarification

HANDOFF_FIELDS = {
    "project_scope_summary",
    "technical_requirement_summary",
    "customer_specifications",
    "special_commercial_commitments",
    "technical_assumptions",
    "open_questions",
    "sales_notes",
}


def _employee(user):
    return Employee.objects.filter(user=user, user__is_active=True).first()


def _require(user, permission, context, message="project action"):
    if not has_permission(user, permission, context):
        raise PermissionDenied(f"You do not have permission to complete this {message}.")


def _event(name, project, actor, action, summary, *, metadata=None, changes=None):
    employee = _employee(actor)
    return DomainEvent(
        event_name=name,
        entity_type="project",
        entity_id=project.pk,
        company_id=project.company_id,
        actor_user_id=actor.pk,
        actor_employee_id=employee.pk if employee else None,
        action=action,
        module="projects",
        summary=summary,
        metadata={
            "entity_reference": project.project_number,
            "project_id": str(project.pk),
            "sales_order_id": str(project.sales_order_id),
            "customer_id": str(project.customer_id),
            **(metadata or {}),
        },
        changes=changes or {},
    )


def _default_project_name(order):
    first_line = order.current_revision.lines.order_by("line_number").first()
    scope = first_line.description if first_line else "Customer Order"
    return f"{order.customer.legal_name} — {scope}"[:250]


def _notify_employee(employee, *, project, notification_type, title, message, severity):
    if not employee or not employee.user_id:
        return
    notify(
        recipient=employee.user,
        entity=project,
        notification_type=notification_type,
        title=title,
        message=message,
        severity=severity,
        action_url=f"/app/projects/{project.pk}",
        deduplication_key=f"{project.pk}:{notification_type}:{project.updated_at.isoformat()}",
    )


def create_project_from_sales_order(*, order_id, actor, data=None):
    data = data or {}
    with transaction.atomic():
        order = (
            SalesOrder.objects.select_for_update(of=("self",))
            .select_related(
                "company",
                "customer",
                "contact",
                "site",
                "responsible_sales_employee__user",
                "current_revision",
                "accepted_quotation",
                "customer_purchase_order__current_revision",
            )
            .prefetch_related("current_revision__lines")
            .get(pk=order_id)
        )
        _require(actor, "projects.project.create", order, "Project creation")
        if order.status != SalesOrder.Status.RELEASED:
            raise ValidationError("Release the Sales Order before creating its Project.")
        if not order.project_required:
            raise ValidationError("This Sales Order is marked Project Not Required.")
        project = Project.objects.select_for_update().filter(sales_order=order).first()
        if project:
            if project.current_sales_order_revision_id != order.current_revision_id:
                previous = project.current_sales_order_revision
                project.previous_sales_order_revision = previous
                project.current_sales_order_revision = order.current_revision
                project.commercial_change_pending = True
                project.record_version += 1
                project.save(
                    update_fields=[
                        "previous_sales_order_revision",
                        "current_sales_order_revision",
                        "commercial_change_pending",
                        "record_version",
                        "updated_at",
                    ]
                )
                publish(
                    _event(
                        "project.commercial_baseline_changed",
                        project,
                        actor,
                        "VERSION_CHANGE",
                        (
                            f"Commercial baseline changed from R{previous.revision_number} "
                            f"to R{order.current_revision.revision_number}"
                        ),
                        metadata={
                            "recipient_user_id": str(project.engineering_owner.user_id)
                            if project.engineering_owner_id and project.engineering_owner.user_id
                            else "",
                            "status": project.status,
                        },
                    )
                )
                _notify_employee(
                    project.engineering_owner,
                    project=project,
                    notification_type="PROJECT_COMMERCIAL_CHANGE",
                    title="Sales Order revision needs review",
                    message=f"{project.project_number} now uses {order.current_revision}.",
                    severity=Notification.Severity.ACTION_REQUIRED,
                )
            return project
        project = Project.objects.create(
            company=order.company,
            project_number=allocate_company_number(company=order.company, code="PRJ"),
            sales_order=order,
            current_sales_order_revision=order.current_revision,
            customer=order.customer,
            project_name=data.get("project_name") or _default_project_name(order),
            customer_project_reference=data.get("customer_project_reference", ""),
            customer_po_reference=(
                order.customer_purchase_order.po_number if order.customer_purchase_order_id else "PO Pending"
            ),
            site=order.site,
            sales_owner=order.responsible_sales_employee,
            project_owner_id=data.get("project_owner_id"),
            engineering_owner_id=data.get("engineering_owner_id"),
            priority=data.get("priority", Project.Priority.NORMAL),
            status=Project.Status.HANDOFF_PENDING,
            planned_start=data.get("planned_start"),
            target_completion=data.get("target_completion") or order.current_revision.promised_delivery,
            customer_delivery_commitment=(
                order.current_revision.delivery_terms or str(order.current_revision.promised_delivery or "")
            ),
            internal_notes=data.get("internal_notes", ""),
            created_by=actor,
        )
        ProjectEngineeringHandoff.objects.create(
            project=project,
            project_scope_summary=order.current_revision.scope,
            technical_requirement_summary="\n".join(
                f"{line.quantity:g} {line.unit_of_measure} — {line.description}"
                for line in order.current_revision.lines.all()
            ),
            special_commercial_commitments=order.current_revision.delivery_terms,
            technical_assumptions="",
            sales_notes=order.current_revision.customer_notes,
            assigned_engineer=project.engineering_owner,
        )
        publish(
            _event(
                "project.created",
                project,
                actor,
                "CREATE",
                f"Project {project.project_number} created from {order.sales_order_number}",
                metadata={"status": project.status},
            )
        )
        return project


def update_project(*, project_id, actor, submitted_version, data):
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=project_id)
        _require(actor, "projects.project.edit", project, "Project edit")
        if project.record_version != submitted_version:
            raise VersionConflict(project.record_version)
        for field in (
            "project_name",
            "customer_project_reference",
            "priority",
            "planned_start",
            "target_completion",
            "customer_delivery_commitment",
            "internal_notes",
        ):
            if field in data:
                setattr(project, field, data[field])
        project.record_version += 1
        project.save()
        publish(_event("project.updated", project, actor, "UPDATE", f"{project.project_number} updated"))
        return project


def prepare_engineering_handoff(*, project_id, actor, submitted_version, data):
    with transaction.atomic():
        project = (
            Project.objects.select_for_update(of=("self",))
            .select_related("engineering_handoff")
            .get(pk=project_id)
        )
        _require(actor, "projects.handoff.prepare", project, "Engineering handoff preparation")
        handoff = ProjectEngineeringHandoff.objects.select_for_update().get(project=project)
        if handoff.status not in {
            ProjectEngineeringHandoff.Status.DRAFT,
            ProjectEngineeringHandoff.Status.CLARIFICATION_REQUIRED,
        }:
            raise ValidationError("This handoff is no longer editable by Sales.")
        if handoff.record_version != submitted_version:
            raise VersionConflict(handoff.record_version)
        for field in HANDOFF_FIELDS:
            if field in data:
                setattr(handoff, field, data[field])
        if "assigned_engineer_id" in data:
            engineer = Employee.objects.filter(
                pk=data.get("assigned_engineer_id"),
                company_id=project.company_id,
                employment_status=Employee.EmploymentStatus.ACTIVE,
            ).first()
            if data.get("assigned_engineer_id") and not engineer:
                raise ValidationError(
                    {"assigned_engineer_id": ["Choose an active employee from this company."]}
                )
            handoff.assigned_engineer = engineer
            project.engineering_owner = engineer
            project.save(update_fields=["engineering_owner", "updated_at"])
        handoff.record_version += 1
        handoff.save()
        publish(
            _event(
                "project.handoff_prepared",
                project,
                actor,
                "UPDATE",
                f"Engineering handoff prepared for {project.project_number}",
                metadata={"status": handoff.status},
            )
        )
        return handoff


def submit_engineering_handoff(*, project_id, actor):
    with transaction.atomic():
        project = (
            Project.objects.select_for_update(of=("self",))
            .select_related("engineering_handoff")
            .get(pk=project_id)
        )
        _require(actor, "projects.handoff.submit", project, "Engineering handoff submission")
        handoff = ProjectEngineeringHandoff.objects.select_for_update().get(project=project)
        if handoff.status not in {
            ProjectEngineeringHandoff.Status.DRAFT,
            ProjectEngineeringHandoff.Status.CLARIFICATION_REQUIRED,
        }:
            raise ValidationError("This handoff has already been sent to Engineering.")
        if not handoff.project_scope_summary.strip() or not handoff.technical_requirement_summary.strip():
            raise ValidationError(
                "Add the project scope and technical requirement before sending to Engineering."
            )
        handoff.status = ProjectEngineeringHandoff.Status.READY_FOR_ENGINEERING
        handoff.submitted_by = actor
        handoff.submitted_at = timezone.now()
        handoff.record_version += 1
        handoff.save()
        project.status = Project.Status.HANDOFF_PENDING
        project.save(update_fields=["status", "updated_at"])
        publish(
            _event(
                "project.handoff_submitted",
                project,
                actor,
                "HANDOFF",
                f"{project.project_number} is ready for Engineering",
                metadata={
                    "status": handoff.status,
                    "recipient_user_id": str(handoff.assigned_engineer.user_id)
                    if handoff.assigned_engineer_id and handoff.assigned_engineer.user_id
                    else "",
                },
            )
        )
        _notify_employee(
            handoff.assigned_engineer,
            project=project,
            notification_type="PROJECT_HANDOFF_ASSIGNED",
            title="Project ready for Engineering",
            message=f"{project.project_number} · {project.project_name}",
            severity=Notification.Severity.ACTION_REQUIRED,
        )
        return handoff


def take_engineering_handoff(*, project_id, actor):
    employee = _employee(actor)
    if not employee:
        raise PermissionDenied("Your account is not linked to an active employee.")
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=project_id)
        _require(actor, "projects.handoff.take_ownership", project, "handoff ownership")
        handoff = (
            ProjectEngineeringHandoff.objects.select_for_update(of=("self",))
            .select_related("assigned_engineer")
            .get(project=project)
        )
        if handoff.status not in {
            ProjectEngineeringHandoff.Status.READY_FOR_ENGINEERING,
            ProjectEngineeringHandoff.Status.ENGINEERING_REVIEWING,
        }:
            raise ValidationError("This handoff is not available for Engineering ownership.")
        if handoff.assigned_engineer_id and handoff.assigned_engineer_id != employee.pk:
            raise ValidationError(
                f"This project has just been assigned to {handoff.assigned_engineer.display_name}.",
                code="HANDOFF_ALREADY_ASSIGNED",
            )
        handoff.assigned_engineer = employee
        handoff.status = ProjectEngineeringHandoff.Status.ENGINEERING_REVIEWING
        handoff.record_version += 1
        handoff.save(update_fields=["assigned_engineer", "status", "record_version", "updated_at"])
        project.engineering_owner = employee
        project.status = Project.Status.ENGINEERING_REVIEW
        project.save(update_fields=["engineering_owner", "status", "updated_at"])
        publish(
            _event(
                "project.handoff_taken",
                project,
                actor,
                "ASSIGN",
                f"{employee.display_name} took ownership of {project.project_number}",
                metadata={
                    "status": handoff.status,
                    "recipient_user_id": str(project.sales_owner.user_id or ""),
                },
            )
        )
        return handoff


def assign_engineering_handoff(*, project_id, engineer_id, actor):
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=project_id)
        _require(actor, "projects.handoff.assign", project, "Engineering handoff assignment")
        engineer = Employee.objects.filter(
            pk=engineer_id,
            company_id=project.company_id,
            employment_status=Employee.EmploymentStatus.ACTIVE,
            user__is_active=True,
        ).first()
        if not engineer:
            raise ValidationError({"engineer_id": ["Choose an active employee from this company."]})
        handoff = ProjectEngineeringHandoff.objects.select_for_update().get(project=project)
        handoff.assigned_engineer = engineer
        handoff.record_version += 1
        handoff.save(update_fields=["assigned_engineer", "record_version", "updated_at"])
        project.engineering_owner = engineer
        project.save(update_fields=["engineering_owner", "updated_at"])
        publish(
            _event(
                "project.assigned",
                project,
                actor,
                "ASSIGN",
                f"{project.project_number} assigned to {engineer.display_name}",
                metadata={"recipient_user_id": str(engineer.user_id)},
            )
        )
        _notify_employee(
            engineer,
            project=project,
            notification_type="PROJECT_ASSIGNED",
            title="Project assigned to you",
            message=f"{project.project_number} · {project.project_name}",
            severity=Notification.Severity.ACTION_REQUIRED,
        )
        return handoff


def request_project_clarification(*, project_id, actor, question, due_date=None, respond_to_id=None):
    if not question.strip():
        raise ValidationError({"question": ["Explain what Sales needs to clarify."]})
    with transaction.atomic():
        project = (
            Project.objects.select_for_update(of=("self",))
            .select_related("sales_owner__user")
            .get(pk=project_id)
        )
        _require(actor, "projects.handoff.request_clarification", project, "clarification request")
        handoff = ProjectEngineeringHandoff.objects.select_for_update().get(project=project)
        if handoff.status not in {
            ProjectEngineeringHandoff.Status.READY_FOR_ENGINEERING,
            ProjectEngineeringHandoff.Status.ENGINEERING_REVIEWING,
            ProjectEngineeringHandoff.Status.CLARIFICATION_REQUIRED,
        }:
            raise ValidationError("Engineering cannot request clarification in this handoff state.")
        respond_to = Employee.objects.filter(
            pk=respond_to_id or project.sales_owner_id, company_id=project.company_id
        ).first()
        if not respond_to:
            raise ValidationError({"respond_to_id": ["Choose a Sales employee from this company."]})
        clarification = ProjectHandoffClarification.objects.create(
            handoff=handoff,
            question=question.strip(),
            requested_by=actor,
            respond_to=respond_to,
            due_date=due_date,
        )
        handoff.status = ProjectEngineeringHandoff.Status.CLARIFICATION_REQUIRED
        handoff.clarification_requested_at = timezone.now()
        handoff.record_version += 1
        handoff.save(update_fields=["status", "clarification_requested_at", "record_version", "updated_at"])
        publish(
            _event(
                "project.clarification_requested",
                project,
                actor,
                "REQUEST",
                question.strip(),
                metadata={
                    "status": handoff.status,
                    "recipient_user_id": str(respond_to.user_id or ""),
                },
            )
        )
        _notify_employee(
            respond_to,
            project=project,
            notification_type="PROJECT_CLARIFICATION_REQUIRED",
            title="Engineering needs information",
            message=question.strip(),
            severity=Notification.Severity.ACTION_REQUIRED,
        )
        return clarification


def respond_project_clarification(*, clarification_id, actor, response, document_id=None):
    if not response.strip():
        raise ValidationError({"response": ["Add the information requested by Engineering."]})
    with transaction.atomic():
        clarification = (
            ProjectHandoffClarification.objects.select_for_update(of=("self",))
            .select_related("handoff__project__engineering_owner__user", "respond_to")
            .get(pk=clarification_id)
        )
        project = clarification.handoff.project
        _require(actor, "projects.handoff.respond_clarification", project, "clarification response")
        if clarification.status != ProjectHandoffClarification.Status.OPEN:
            raise ValidationError("This clarification has already been answered.")
        document = None
        if document_id:
            document = Document.objects.filter(pk=document_id, company_id=project.company_id).first()
            if not document:
                raise ValidationError({"document_id": ["Choose a document from this company."]})
        clarification.response = response.strip()
        clarification.response_document = document
        clarification.responded_by = actor
        clarification.responded_at = timezone.now()
        clarification.status = ProjectHandoffClarification.Status.ANSWERED
        clarification.save()
        handoff = clarification.handoff
        if not handoff.clarifications.filter(status=ProjectHandoffClarification.Status.OPEN).exists():
            handoff.status = ProjectEngineeringHandoff.Status.ENGINEERING_REVIEWING
            handoff.record_version += 1
            handoff.save(update_fields=["status", "record_version", "updated_at"])
        publish(
            _event(
                "project.clarification_responded",
                project,
                actor,
                "RESPOND",
                f"Sales responded: {response.strip()}",
                metadata={
                    "status": handoff.status,
                    "recipient_user_id": str(project.engineering_owner.user_id)
                    if project.engineering_owner_id and project.engineering_owner.user_id
                    else "",
                },
            )
        )
        _notify_employee(
            project.engineering_owner,
            project=project,
            notification_type="PROJECT_CLARIFICATION_ANSWERED",
            title="Sales answered your clarification",
            message=response.strip(),
            severity=Notification.Severity.INFO,
        )
        return clarification


def accept_engineering_handoff(*, project_id, actor):
    employee = _employee(actor)
    if not employee:
        raise PermissionDenied("Your account is not linked to an active employee.")
    with transaction.atomic():
        project = (
            Project.objects.select_for_update(of=("self",))
            .select_related(
                "current_sales_order_revision",
                "sales_order__customer_purchase_order__current_revision",
                "sales_owner__user",
            )
            .get(pk=project_id)
        )
        _require(actor, "projects.handoff.accept", project, "Engineering handoff acceptance")
        handoff = ProjectEngineeringHandoff.objects.select_for_update().get(project=project)
        if handoff.status not in {
            ProjectEngineeringHandoff.Status.ENGINEERING_REVIEWING,
            ProjectEngineeringHandoff.Status.READY_FOR_ENGINEERING,
        }:
            raise ValidationError("Resolve Sales clarifications before accepting this handoff.")
        if handoff.assigned_engineer_id and handoff.assigned_engineer_id != employee.pk:
            raise PermissionDenied("This handoff is assigned to another employee.")
        if handoff.clarifications.filter(status=ProjectHandoffClarification.Status.OPEN).exists():
            raise ValidationError("Resolve or answer the open clarification before acceptance.")
        handoff.assigned_engineer = employee
        handoff.status = ProjectEngineeringHandoff.Status.ACCEPTED
        handoff.accepted_by = actor
        handoff.accepted_at = timezone.now()
        handoff.accepted_sales_order_revision = project.current_sales_order_revision
        handoff.accepted_customer_po_revision = (
            project.sales_order.customer_purchase_order.current_revision
            if project.sales_order.customer_purchase_order_id
            else None
        )
        handoff.accepted_snapshot = {
            "project": project.project_number,
            "sales_order": project.sales_order.sales_order_number,
            "sales_order_revision": project.current_sales_order_revision.revision_number,
            "customer_po_revision": (
                handoff.accepted_customer_po_revision.revision_number
                if handoff.accepted_customer_po_revision_id
                else None
            ),
            "scope": handoff.project_scope_summary,
            "technical_requirements": handoff.technical_requirement_summary,
        }
        handoff.record_version += 1
        handoff.save()
        project.engineering_owner = employee
        project.status = Project.Status.ENGINEERING_ACCEPTED
        project.commercial_change_pending = False
        project.record_version += 1
        project.save(
            update_fields=[
                "engineering_owner",
                "status",
                "commercial_change_pending",
                "record_version",
                "updated_at",
            ]
        )
        publish(
            _event(
                "project.handoff_accepted",
                project,
                actor,
                "ACCEPT",
                f"Engineering accepted {project.project_number}",
                metadata={
                    "status": project.status,
                    "recipient_user_id": str(project.sales_owner.user_id or ""),
                },
            )
        )
        return handoff


def acknowledge_commercial_change(*, project_id, actor):
    with transaction.atomic():
        project = (
            Project.objects.select_for_update()
            .select_related("current_sales_order_revision")
            .get(pk=project_id)
        )
        _require(
            actor,
            "projects.handoff.acknowledge_commercial_change",
            project,
            "commercial change acknowledgement",
        )
        if not project.commercial_change_pending:
            return project
        project.commercial_change_pending = False
        project.previous_sales_order_revision = None
        project.record_version += 1
        project.save(
            update_fields=[
                "commercial_change_pending",
                "previous_sales_order_revision",
                "record_version",
                "updated_at",
            ]
        )
        publish(
            _event(
                "project.commercial_change_acknowledged",
                project,
                actor,
                "ACKNOWLEDGE",
                f"Engineering acknowledged {project.current_sales_order_revision}",
                metadata={"status": project.status},
            )
        )
        return project


def hold_project(*, project_id, actor, reason):
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=project_id)
        _require(actor, "projects.project.hold", project, "Project hold")
        if project.status in {Project.Status.ON_HOLD, Project.Status.CANCELLED}:
            raise ValidationError("This Project cannot be put on hold from its current status.")
        previous_status = project.status
        project.status = Project.Status.ON_HOLD
        project.record_version += 1
        project.save(update_fields=["status", "record_version", "updated_at"])
        publish(
            _event(
                "project.held",
                project,
                actor,
                "HOLD",
                f"{project.project_number} was put on hold",
                metadata={"status": project.status, "reason": reason.strip()},
                changes={"status": {"from": previous_status, "to": project.status}},
            )
        )
        return project


def resume_project(*, project_id, actor):
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=project_id)
        _require(actor, "projects.project.hold", project, "Project resume")
        if project.status != Project.Status.ON_HOLD:
            raise ValidationError("Only an On Hold Project can be resumed.")
        handoff = ProjectEngineeringHandoff.objects.filter(project=project).first()
        project.status = {
            ProjectEngineeringHandoff.Status.ACCEPTED: Project.Status.ENGINEERING_ACCEPTED,
            ProjectEngineeringHandoff.Status.ENGINEERING_REVIEWING: Project.Status.ENGINEERING_REVIEW,
            ProjectEngineeringHandoff.Status.CLARIFICATION_REQUIRED: Project.Status.ENGINEERING_REVIEW,
            ProjectEngineeringHandoff.Status.READY_FOR_ENGINEERING: Project.Status.HANDOFF_PENDING,
        }.get(handoff.status if handoff else "", Project.Status.NEW)
        project.record_version += 1
        project.save(update_fields=["status", "record_version", "updated_at"])
        publish(
            _event(
                "project.resumed",
                project,
                actor,
                "RESUME",
                f"{project.project_number} was resumed",
                metadata={"status": project.status},
            )
        )
        return project


def cancel_project(*, project_id, actor, reason):
    with transaction.atomic():
        project = Project.objects.select_for_update().get(pk=project_id)
        _require(actor, "projects.project.cancel", project, "Project cancellation")
        if project.status == Project.Status.CANCELLED:
            return project
        previous_status = project.status
        project.status = Project.Status.CANCELLED
        project.record_version += 1
        project.save(update_fields=["status", "record_version", "updated_at"])
        publish(
            _event(
                "project.cancelled",
                project,
                actor,
                "CANCEL",
                f"{project.project_number} was cancelled",
                metadata={"status": project.status, "reason": reason.strip()},
                changes={"status": {"from": previous_status, "to": project.status}},
            )
        )
        return project
