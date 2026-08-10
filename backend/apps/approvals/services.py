from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.core.domain_events import DomainEvent, publish
from apps.core.entity_registry import entity_company_id, entity_reference, resolve_entity
from apps.rbac.services import has_permission

from .conditions import conditions_match
from .models import (
    ApprovalAssignment,
    ApprovalCondition,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStepDefinition,
    ApprovalStepInstance,
    ApprovalWorkflow,
    ApprovalWorkflowVersion,
)
from .resolvers import resolve_approvers


def display_name(user):
    try:
        return user.employee.display_name
    except Exception:
        return user.get_full_name() or user.email


def actor_employee_id(user):
    try:
        return user.employee.pk
    except Exception:
        return None


def require(user, permission, context):
    if not has_permission(user, permission, context):
        raise PermissionDenied("You do not have permission to complete this approval action.")


def approval_event(name, request, actor, action, summary, *, metadata=None):
    return DomainEvent(
        event_name=name,
        entity_type="approval_request",
        entity_id=request.pk,
        company_id=request.company_id,
        actor_user_id=actor.pk,
        actor_employee_id=actor_employee_id(actor),
        action=action,
        module="approvals",
        summary=summary,
        metadata={
            "entity_reference": str(request),
            "record_reference": request.entity_reference,
            "requester_user_id": str(request.requested_by_id or ""),
            **(metadata or {}),
        },
    )


def workflow_event(name, workflow, actor, action, summary, *, metadata=None):
    return DomainEvent(
        event_name=name,
        entity_type="approval_workflow",
        entity_id=workflow.pk,
        company_id=workflow.company_id,
        actor_user_id=actor.pk,
        actor_employee_id=actor_employee_id(actor),
        action=action,
        module="approvals",
        summary=summary,
        metadata={"entity_reference": str(workflow), **(metadata or {})},
    )


def create_workflow(*, company, code, name, entity_type, actor, description=""):
    require(actor, "approvals.workflow.manage", company)
    with transaction.atomic():
        workflow = ApprovalWorkflow.objects.create(
            company=company,
            code=code,
            name=name,
            description=description,
            entity_type=entity_type,
        )
        ApprovalWorkflowVersion.objects.create(
            workflow=workflow,
            version_number=1,
            created_by=actor,
        )
        publish(
            workflow_event(
                "approval.workflow_created",
                workflow,
                actor,
                "CREATE",
                f"Approval workflow created: {workflow.name}",
                metadata={"version": 1},
            )
        )
        return workflow


def clone_workflow_version(*, workflow_id, actor):
    with transaction.atomic():
        workflow = ApprovalWorkflow.objects.select_for_update().get(pk=workflow_id)
        require(actor, "approvals.workflow.manage", workflow)
        source = workflow.current_version or workflow.versions.order_by("-version_number").first()
        if source is None:
            raise ValidationError("This workflow does not have a version to copy.")
        next_number = (workflow.versions.aggregate(value=Max("version_number"))["value"] or 0) + 1
        target = ApprovalWorkflowVersion.objects.create(
            workflow=workflow,
            version_number=next_number,
            allow_self_approval=source.allow_self_approval,
            effective_from=source.effective_from,
            effective_to=source.effective_to,
            created_by=actor,
        )
        for condition in source.conditions.all():
            ApprovalCondition.objects.create(
                workflow_version=target,
                field=condition.field,
                operator=condition.operator,
                value=condition.value,
            )
        for step in source.steps.order_by("sequence"):
            cloned = ApprovalStepDefinition.objects.create(
                workflow_version=target,
                sequence=step.sequence,
                name=step.name,
                approval_mode=step.approval_mode,
                resolver_type=step.resolver_type,
                required_permission_code=step.required_permission_code,
                scope_logic=step.scope_logic,
                minimum_approvals=step.minimum_approvals,
                allow_reject=step.allow_reject,
                allow_return_for_changes=step.allow_return_for_changes,
                sla_duration=step.sla_duration,
                is_active=step.is_active,
            )
            cloned.specific_users.set(step.specific_users.all())
        publish(
            workflow_event(
                "approval.workflow_version_created",
                workflow,
                actor,
                "VERSION_CREATE",
                f"Version {next_number} created for {workflow.name}",
                metadata={"version": next_number, "source_version": source.version_number},
            )
        )
        return target


def activate_workflow_version(*, version_id, actor):
    with transaction.atomic():
        version = ApprovalWorkflowVersion.objects.select_for_update().select_related("workflow").get(
            pk=version_id
        )
        workflow = ApprovalWorkflow.objects.select_for_update().get(pk=version.workflow_id)
        require(actor, "approvals.workflow.manage", workflow)
        if version.status != ApprovalWorkflowVersion.Status.DRAFT:
            raise ValidationError("Only a draft workflow version can be activated.")
        steps = list(version.steps.filter(is_active=True).order_by("sequence"))
        if not steps:
            raise ValidationError({"steps": ["Add at least one active approval step before activation."]})
        for step in steps:
            step.full_clean()
            if step.resolver_type == ApprovalStepDefinition.ResolverType.SPECIFIC_USERS:
                users = list(step.specific_users.all())
                if len(users) < step.minimum_approvals:
                    raise ValidationError({"steps": [f"Step '{step.name}' needs more approvers."]})
                if any(
                    not getattr(getattr(user, "employee", None), "company_id", None)
                    == workflow.company_id
                    for user in users
                ):
                    raise ValidationError({"steps": [f"Step '{step.name}' contains another-company user."]})
        for condition in version.conditions.all():
            condition.full_clean()
        if workflow.current_version_id:
            ApprovalWorkflowVersion.objects.filter(pk=workflow.current_version_id).update(
                status=ApprovalWorkflowVersion.Status.RETIRED
            )
        version.status = ApprovalWorkflowVersion.Status.ACTIVE
        version.save(update_fields=["status", "updated_at"])
        workflow.current_version = version
        workflow.is_active = True
        workflow.save(update_fields=["current_version", "is_active", "updated_at"])
        publish(
            workflow_event(
                "approval.workflow_activated",
                workflow,
                actor,
                "ACTIVATE",
                f"Version {version.version_number} activated for {workflow.name}",
                metadata={"version": version.version_number},
            )
        )
        return version


def _open_step(step, request, actor):
    now = timezone.now()
    step.status = ApprovalStepInstance.Status.OPEN
    step.opened_at = now
    step.save(update_fields=["status", "opened_at", "updated_at"])
    request.current_step = step
    request.save(update_fields=["current_step", "updated_at"])
    approver_ids = [str(value) for value in step.assignments.values_list("approver_id", flat=True)]
    publish(
        approval_event(
            "approval.step_opened",
            request,
            actor,
            "ASSIGN",
            f"Approval step opened: {step.step_name}",
            metadata={
                "step": step.step_name,
                "step_sequence": step.sequence,
                "approver_user_ids": approver_ids,
            },
        )
    )


def create_approval_request(
    *,
    workflow_id,
    entity_type,
    entity_id,
    actor,
    submission_comment="",
    snapshot_metadata=None,
):
    entity = resolve_entity(entity_type, entity_id, "approvals")
    workflow = ApprovalWorkflow.objects.select_related("current_version", "company").get(pk=workflow_id)
    require(actor, "approvals.request.submit", entity)
    if workflow.company_id != entity_company_id(entity) or workflow.entity_type != entity_type:
        raise ValidationError("The workflow and requested record must have the same company and type.")
    version = workflow.current_version
    now = timezone.now()
    if not workflow.is_active or not version or version.status != ApprovalWorkflowVersion.Status.ACTIVE:
        raise ValidationError("Choose an active approval workflow.")
    if version.effective_from and version.effective_from > now:
        raise ValidationError("This workflow is not effective yet.")
    if version.effective_to and version.effective_to <= now:
        raise ValidationError("This workflow is no longer effective.")
    if not conditions_match(version, entity):
        raise ValidationError("This record does not meet the workflow conditions.")

    with transaction.atomic():
        request = ApprovalRequest.objects.create(
            company=workflow.company,
            workflow_version=version,
            workflow_name=workflow.name,
            workflow_version_number=version.version_number,
            entity_type=entity_type,
            entity_id=str(entity_id),
            entity_reference=entity_reference(entity),
            requested_by=actor,
            requested_by_name=display_name(actor),
            status=ApprovalRequest.Status.IN_PROGRESS,
            submission_comment=submission_comment,
            snapshot_metadata=snapshot_metadata or {},
        )
        instances = []
        for definition in version.steps.filter(is_active=True).order_by("sequence"):
            approvers = resolve_approvers(definition, entity)
            instance = ApprovalStepInstance.objects.create(
                request=request,
                definition=definition,
                sequence=definition.sequence,
                step_name=definition.name,
                approval_mode=definition.approval_mode,
                minimum_approvals=definition.minimum_approvals,
                allow_reject=definition.allow_reject,
                allow_return_for_changes=definition.allow_return_for_changes,
                resolution_metadata={
                    "resolver_type": definition.resolver_type,
                    "permission_code": definition.required_permission_code,
                },
            )
            ApprovalAssignment.objects.bulk_create(
                [
                    ApprovalAssignment(
                        step=instance,
                        approver=approver,
                        approver_name=display_name(approver),
                    )
                    for approver in approvers
                ]
            )
            instances.append(instance)
        if not instances:
            raise ValidationError("The active workflow does not contain approval steps.")
        _open_step(instances[0], request, actor)
        publish(
            approval_event(
                "approval.request_submitted",
                request,
                actor,
                "SUBMIT",
                f"Approval submitted for {request.entity_reference}",
                metadata={
                    "workflow": request.workflow_name,
                    "workflow_version": request.workflow_version_number,
                },
            )
        )
        return request


def _locked_context(request_id, actor, permission):
    try:
        request = (
            ApprovalRequest.objects.select_for_update()
            .select_related("workflow_version")
            .get(pk=request_id)
        )
    except ApprovalRequest.DoesNotExist as exc:
        raise NotFound("Approval request not found.") from exc
    require(actor, permission, request)
    if request.status != ApprovalRequest.Status.IN_PROGRESS or not request.current_step_id:
        raise ValidationError(
            "This approval request is no longer awaiting a decision.",
            code="APPROVAL_ALREADY_DECIDED",
        )
    step = ApprovalStepInstance.objects.select_for_update().get(pk=request.current_step_id)
    try:
        assignment = ApprovalAssignment.objects.select_for_update().get(
            step=step,
            approver=actor,
            status=ApprovalAssignment.Status.PENDING,
        )
    except ApprovalAssignment.DoesNotExist as exc:
        raise PermissionDenied(
            "This approval is not assigned to you.",
            code="APPROVAL_NOT_ASSIGNED",
        ) from exc
    if request.requested_by_id == actor.pk and not request.workflow_version.allow_self_approval:
        raise PermissionDenied(
            "You cannot approve a request you submitted.",
            code="SELF_APPROVAL_NOT_ALLOWED",
        )
    return request, step, assignment


def approve_request(*, request_id, actor, comment=""):
    with transaction.atomic():
        request, step, assignment = _locked_context(
            request_id,
            actor,
            "approvals.request.approve",
        )
        now = timezone.now()
        ApprovalDecision.objects.create(
            step=step,
            assignment=assignment,
            decided_by=actor,
            decided_by_name=display_name(actor),
            decision=ApprovalDecision.Decision.APPROVED,
            comment=comment,
            decided_at=now,
        )
        assignment.status = ApprovalAssignment.Status.APPROVED
        assignment.save(update_fields=["status", "updated_at"])
        approvals = step.assignments.filter(status=ApprovalAssignment.Status.APPROVED).count()
        if approvals >= step.minimum_approvals:
            step.status = ApprovalStepInstance.Status.APPROVED
            step.decided_at = now
            step.save(update_fields=["status", "decided_at", "updated_at"])
            step.assignments.filter(status=ApprovalAssignment.Status.PENDING).update(
                status=ApprovalAssignment.Status.SKIPPED,
                updated_at=now,
            )
            next_step = request.steps.filter(sequence__gt=step.sequence).order_by("sequence").first()
            if next_step:
                _open_step(next_step, request, actor)
            else:
                request.status = ApprovalRequest.Status.APPROVED
                request.completed_at = now
                request.current_step = None
                request.save(
                    update_fields=["status", "completed_at", "current_step", "updated_at"]
                )
        publish(
            approval_event(
                "approval.request_approved"
                if request.status == ApprovalRequest.Status.APPROVED
                else "approval.step_approved",
                request,
                actor,
                "APPROVE",
                f"{step.step_name} approved for {request.entity_reference}",
                metadata={"step": step.step_name, "comment": comment},
            )
        )
        return request


def _terminal_decision(*, request_id, actor, decision, comment):
    if not comment.strip():
        raise ValidationError({"comment": ["Add a comment explaining this decision."]})
    permission = {
        ApprovalDecision.Decision.REJECTED: "approvals.request.reject",
        ApprovalDecision.Decision.RETURNED_FOR_CHANGES: "approvals.request.return",
    }[decision]
    with transaction.atomic():
        request, step, assignment = _locked_context(request_id, actor, permission)
        if decision == ApprovalDecision.Decision.REJECTED and not step.allow_reject:
            raise ValidationError("This workflow step does not allow rejection.")
        if (
            decision == ApprovalDecision.Decision.RETURNED_FOR_CHANGES
            and not step.allow_return_for_changes
        ):
            raise ValidationError("This workflow step does not allow return for changes.")
        now = timezone.now()
        ApprovalDecision.objects.create(
            step=step,
            assignment=assignment,
            decided_by=actor,
            decided_by_name=display_name(actor),
            decision=decision,
            comment=comment,
            decided_at=now,
        )
        assignment.status = decision
        assignment.save(update_fields=["status", "updated_at"])
        step.status = decision
        step.decided_at = now
        step.save(update_fields=["status", "decided_at", "updated_at"])
        step.assignments.filter(status=ApprovalAssignment.Status.PENDING).update(
            status=ApprovalAssignment.Status.SKIPPED,
            updated_at=now,
        )
        request.status = decision
        request.completed_at = now
        request.current_step = None
        request.save(update_fields=["status", "completed_at", "current_step", "updated_at"])
        event_name = (
            "approval.request_rejected"
            if decision == ApprovalDecision.Decision.REJECTED
            else "approval.request_returned"
        )
        action = "REJECT" if decision == ApprovalDecision.Decision.REJECTED else "STATUS_CHANGE"
        publish(
            approval_event(
                event_name,
                request,
                actor,
                action,
                f"{request.entity_reference} {request.get_status_display().lower()}",
                metadata={"step": step.step_name, "comment": comment},
            )
        )
        return request


def reject_request(*, request_id, actor, comment):
    return _terminal_decision(
        request_id=request_id,
        actor=actor,
        decision=ApprovalDecision.Decision.REJECTED,
        comment=comment,
    )


def return_request(*, request_id, actor, comment):
    return _terminal_decision(
        request_id=request_id,
        actor=actor,
        decision=ApprovalDecision.Decision.RETURNED_FOR_CHANGES,
        comment=comment,
    )


def cancel_request(*, request_id, actor, comment=""):
    with transaction.atomic():
        request = ApprovalRequest.objects.select_for_update().get(pk=request_id)
        require(actor, "approvals.request.cancel", request)
        if request.status not in {ApprovalRequest.Status.PENDING, ApprovalRequest.Status.IN_PROGRESS}:
            raise ValidationError(
                "Only a pending approval request can be cancelled.",
                code="INVALID_APPROVAL_TRANSITION",
            )
        now = timezone.now()
        request.steps.filter(
            status__in=[ApprovalStepInstance.Status.WAITING, ApprovalStepInstance.Status.OPEN]
        ).update(status=ApprovalStepInstance.Status.CANCELLED, decided_at=now, updated_at=now)
        ApprovalAssignment.objects.filter(
            step__request=request,
            status=ApprovalAssignment.Status.PENDING,
        ).update(status=ApprovalAssignment.Status.CANCELLED, updated_at=now)
        request.status = ApprovalRequest.Status.CANCELLED
        request.cancelled_at = now
        request.cancelled_by = actor
        request.current_step = None
        request.completed_at = now
        request.save(
            update_fields=[
                "status",
                "cancelled_at",
                "cancelled_by",
                "current_step",
                "completed_at",
                "updated_at",
            ]
        )
        publish(
            approval_event(
                "approval.request_cancelled",
                request,
                actor,
                "CANCEL",
                f"Approval cancelled for {request.entity_reference}",
                metadata={"comment": comment},
            )
        )
        return request
