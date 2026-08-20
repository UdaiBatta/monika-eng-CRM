from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.approvals.conditions import conditions_match
from apps.approvals.models import ApprovalRequest, ApprovalWorkflow, ApprovalWorkflowVersion
from apps.approvals.services import create_approval_request
from apps.core.domain_events import DomainEvent, publish
from apps.enquiries.models import Enquiry
from apps.organization.models import Employee
from apps.rbac.services import has_permission

from .models import EngineeringClarification, EngineeringFeasibilityReview

REVIEW_ENTITY = "engineering_feasibility_review"
UNRESOLVED_CLARIFICATIONS = {
    EngineeringClarification.Status.OPEN,
    EngineeringClarification.Status.RESPONDED,
}
COMPLETED_REVIEW_STATUSES = {
    EngineeringFeasibilityReview.Status.FEASIBLE,
    EngineeringFeasibilityReview.Status.NOT_FEASIBLE,
    EngineeringFeasibilityReview.Status.SUPERSEDED,
    EngineeringFeasibilityReview.Status.CANCELLED,
}


def _employee_id(user):
    return getattr(getattr(user, "employee", None), "pk", None)


def _require(user, permission, entity):
    if not has_permission(user, permission, entity):
        raise PermissionDenied("You do not have permission to change this Workshop Review.")


def review_event(review, actor, event_name, action, summary, *, metadata=None, changes=None):
    return DomainEvent(
        event_name=event_name,
        entity_type=REVIEW_ENTITY,
        entity_id=review.pk,
        company_id=review.company_id,
        actor_user_id=actor.pk,
        actor_employee_id=_employee_id(actor),
        action=action,
        module="engineering",
        summary=summary,
        changes=changes or {},
        metadata={
            "entity_reference": str(review),
            "enquiry_id": str(review.enquiry_id),
            "enquiry_number": review.enquiry.enquiry_number,
            "customer_id": str(review.enquiry.customer_id),
            "customer_reference": review.enquiry.customer.customer_code,
            "revision_number": review.revision_number,
            **(metadata or {}),
        },
    )


def clarification_event(clarification, actor, event_name, action, summary, *, metadata=None, changes=None):
    review = clarification.review
    return DomainEvent(
        event_name=event_name,
        entity_type="engineering_clarification",
        entity_id=clarification.pk,
        company_id=clarification.company_id,
        actor_user_id=actor.pk,
        actor_employee_id=_employee_id(actor),
        action=action,
        module="engineering",
        summary=summary,
        changes=changes or {},
        metadata={
            "entity_reference": str(clarification),
            "review_id": str(review.pk),
            "enquiry_id": str(review.enquiry_id),
            "enquiry_number": review.enquiry.enquiry_number,
            "customer_id": str(review.enquiry.customer_id),
            **(metadata or {}),
        },
    )


def _active_matching_workflows(review):
    workflows = ApprovalWorkflow.objects.select_related("current_version").filter(
        company_id=review.company_id,
        entity_type=REVIEW_ENTITY,
        is_active=True,
        current_version__status=ApprovalWorkflowVersion.Status.ACTIVE,
    )
    return [workflow for workflow in workflows if conditions_match(workflow.current_version, review)]


def approval_state(review):
    workflows = _active_matching_workflows(review)
    requests = ApprovalRequest.objects.filter(entity_type=REVIEW_ENTITY, entity_id=str(review.pk))
    latest = requests.select_related("workflow_version").first()
    if not workflows:
        return {"required": False, "status": "NOT_REQUIRED", "request": latest}
    if len(workflows) > 1:
        return {"required": True, "status": "CONFIGURATION_ERROR", "request": latest}
    return {
        "required": True,
        "status": latest.status if latest else "NOT_SUBMITTED",
        "request": latest,
    }


def is_ready_for_estimation(review):
    if not review or not review.is_current:
        return False
    if review.status != EngineeringFeasibilityReview.Status.FEASIBLE:
        return False
    if review.result not in {
        EngineeringFeasibilityReview.Result.FEASIBLE,
        EngineeringFeasibilityReview.Result.FEASIBLE_WITH_CONDITIONS,
    }:
        return False
    if review.clarifications.filter(status__in=UNRESOLVED_CLARIFICATIONS).exists():
        return False
    approval = approval_state(review)
    return approval["status"] in {"NOT_REQUIRED", ApprovalRequest.Status.APPROVED}


def create_review_for_enquiry(*, enquiry, actor):
    current = enquiry.engineering_reviews.filter(is_current=True).first()
    if current:
        return current
    review = EngineeringFeasibilityReview.objects.create(
        company=enquiry.company,
        enquiry=enquiry,
        revision_number=1,
        created_by=actor,
    )
    publish(
        review_event(
            review,
            actor,
            "engineering.review.created",
            "CREATE",
            f"Workshop Review created for {enquiry.enquiry_number}",
        )
    )
    return review


def assign_review(*, review_id, engineer_id, actor):
    with transaction.atomic():
        review = (
            EngineeringFeasibilityReview.objects.select_for_update()
            .select_related("enquiry", "enquiry__customer")
            .get(pk=review_id)
        )
        _require(actor, "engineering.feasibility.assign", review)
        if review.status in COMPLETED_REVIEW_STATUSES:
            raise ValidationError("A completed Workshop Review cannot be reassigned.")
        try:
            engineer = Employee.objects.select_related("user").get(
                pk=engineer_id,
                company_id=review.company_id,
                employment_status=Employee.EmploymentStatus.ACTIVE,
                user__is_active=True,
            )
        except Employee.DoesNotExist as exc:
            raise ValidationError("Choose an active Workshop employee from this company.") from exc
        previous = review.assigned_engineer_id
        review.assigned_engineer = engineer
        review.save(update_fields=["assigned_engineer", "updated_at"])
        publish(
            review_event(
                review,
                actor,
                "engineering.review.assigned",
                "ASSIGN",
                f"Workshop Review {review.revision_number} assigned to {engineer.display_name}",
                metadata={"recipient_user_id": str(engineer.user_id)},
                changes={"assigned_engineer": {"old": str(previous or ""), "new": str(engineer.pk)}},
            )
        )
        return review


def start_review(*, review_id, actor):
    with transaction.atomic():
        review = (
            EngineeringFeasibilityReview.objects.select_for_update(of=("self",))
            .select_related("enquiry", "enquiry__customer", "assigned_engineer")
            .get(pk=review_id)
        )
        _require(actor, "engineering.feasibility.start", review)
        if review.status != EngineeringFeasibilityReview.Status.PENDING:
            raise ValidationError("Only a pending Workshop Review can be started.")
        if not review.assigned_engineer_id:
            raise ValidationError("Assign a Workshop employee before starting the review.")
        old_status = review.status
        review.status = EngineeringFeasibilityReview.Status.IN_REVIEW
        review.started_at = timezone.now()
        review.started_by = actor
        review.save(update_fields=["status", "started_at", "started_by", "updated_at"])
        publish(
            review_event(
                review,
                actor,
                "engineering.review.started",
                "STATUS_CHANGE",
                f"Workshop Review started for {review.enquiry.enquiry_number}",
                changes={"status": {"old": old_status, "new": review.status}},
            )
        )
        return review


ASSESSMENT_FIELDS = {
    "technical_summary",
    "feasibility_notes",
    "assumptions",
    "exclusions",
    "constraints",
    "risks",
    "special_materials",
    "outsourced_processes",
    "tooling_requirements",
    "testing_requirements",
    "customer_clarification_summary",
    "preliminary_drawing_notes",
    "preliminary_bom_notes",
    "preliminary_routing_notes",
    "engineering_hours",
    "manufacturing_hours",
    "lead_time_days",
}


def update_assessment(*, review_id, actor, data):
    with transaction.atomic():
        review = (
            EngineeringFeasibilityReview.objects.select_for_update()
            .select_related("enquiry", "enquiry__customer")
            .get(pk=review_id)
        )
        _require(actor, "engineering.feasibility.edit", review)
        if review.status not in {
            EngineeringFeasibilityReview.Status.IN_REVIEW,
            EngineeringFeasibilityReview.Status.CLARIFICATION_REQUIRED,
        }:
            raise ValidationError("Only an active Workshop Review can be edited.")
        changes = {}
        for field in ASSESSMENT_FIELDS:
            if field in data:
                old_value = getattr(review, field)
                new_value = data[field]
                if old_value != new_value:
                    setattr(review, field, new_value)
                    changes[field] = {"old": str(old_value or ""), "new": str(new_value or "")}
        review.save(update_fields=[*changes.keys(), "updated_at"])
        if changes:
            publish(
                review_event(
                    review,
                    actor,
                    "engineering.review.assessment_updated",
                    "UPDATE",
                    f"Workshop assessment updated for {review.enquiry.enquiry_number}",
                    changes=changes,
                )
            )
        return review


def request_clarification(*, review_id, actor, subject, question, assigned_to_id, context="", due_at=None):
    with transaction.atomic():
        review = (
            EngineeringFeasibilityReview.objects.select_for_update()
            .select_related("enquiry", "enquiry__customer")
            .get(pk=review_id)
        )
        _require(actor, "engineering.feasibility.request_clarification", review)
        if review.status not in {
            EngineeringFeasibilityReview.Status.IN_REVIEW,
            EngineeringFeasibilityReview.Status.CLARIFICATION_REQUIRED,
        }:
            raise ValidationError("Clarification can only be requested during an active review.")
        try:
            recipient = Employee.objects.select_related("user").get(
                pk=assigned_to_id,
                company_id=review.company_id,
                employment_status=Employee.EmploymentStatus.ACTIVE,
                user__is_active=True,
            )
        except Employee.DoesNotExist as exc:
            raise ValidationError("Choose an active clarification recipient from this company.") from exc
        clarification = EngineeringClarification.objects.create(
            company=review.company,
            review=review,
            subject=subject.strip(),
            question=question.strip(),
            context=context.strip(),
            assigned_to=recipient,
            due_at=due_at,
            requested_by=actor,
            requested_at=timezone.now(),
        )
        old_status = review.status
        review.status = EngineeringFeasibilityReview.Status.CLARIFICATION_REQUIRED
        review.save(update_fields=["status", "updated_at"])
        publish(
            clarification_event(
                clarification,
                actor,
                "engineering.clarification.requested",
                "CREATE",
                f"Clarification requested: {clarification.subject}",
                metadata={"recipient_user_id": str(recipient.user_id)},
                changes={"status": {"old": "", "new": clarification.status}},
            )
        )
        if old_status != review.status:
            publish(
                review_event(
                    review,
                    actor,
                    "engineering.review.clarification_required",
                    "STATUS_CHANGE",
                    f"{review.enquiry.enquiry_number} requires clarification",
                    changes={"status": {"old": old_status, "new": review.status}},
                )
            )
        return clarification


def respond_to_clarification(*, clarification_id, actor, response):
    with transaction.atomic():
        clarification = (
            EngineeringClarification.objects.select_for_update()
            .select_related("review", "review__enquiry", "review__enquiry__customer", "assigned_to")
            .get(pk=clarification_id)
        )
        _require(actor, "engineering.feasibility.respond_clarification", clarification.review)
        if clarification.status != EngineeringClarification.Status.OPEN:
            raise ValidationError("Only an open clarification can be answered.")
        employee = getattr(actor, "employee", None)
        if not actor.is_superuser and (not employee or employee.pk != clarification.assigned_to_id):
            raise PermissionDenied("This clarification is assigned to another employee.")
        clarification.status = EngineeringClarification.Status.RESPONDED
        clarification.response = response.strip()
        clarification.responded_by = actor
        clarification.responded_at = timezone.now()
        clarification.save(update_fields=["status", "response", "responded_by", "responded_at", "updated_at"])
        publish(
            clarification_event(
                clarification,
                actor,
                "engineering.clarification.responded",
                "STATUS_CHANGE",
                f"Clarification answered: {clarification.subject}",
                metadata={"recipient_user_id": str(clarification.requested_by_id or "")},
                changes={
                    "status": {"old": EngineeringClarification.Status.OPEN, "new": clarification.status}
                },
            )
        )
        return clarification


def close_clarification(*, clarification_id, actor, closure_comment=""):
    with transaction.atomic():
        clarification = (
            EngineeringClarification.objects.select_for_update()
            .select_related("review", "review__enquiry", "review__enquiry__customer")
            .get(pk=clarification_id)
        )
        review = EngineeringFeasibilityReview.objects.select_for_update().get(pk=clarification.review_id)
        _require(actor, "engineering.feasibility.edit", review)
        if clarification.status != EngineeringClarification.Status.RESPONDED:
            raise ValidationError("A clarification must be answered before it can be closed.")
        clarification.status = EngineeringClarification.Status.CLOSED
        clarification.closed_by = actor
        clarification.closed_at = timezone.now()
        clarification.closure_comment = closure_comment.strip()
        clarification.save(
            update_fields=["status", "closed_by", "closed_at", "closure_comment", "updated_at"]
        )
        if not review.clarifications.filter(status__in=UNRESOLVED_CLARIFICATIONS).exists():
            review.status = EngineeringFeasibilityReview.Status.IN_REVIEW
            review.save(update_fields=["status", "updated_at"])
        clarification.review = review
        publish(
            clarification_event(
                clarification,
                actor,
                "engineering.clarification.closed",
                "STATUS_CHANGE",
                f"Clarification closed: {clarification.subject}",
                changes={
                    "status": {"old": EngineeringClarification.Status.RESPONDED, "new": clarification.status}
                },
            )
        )
        return clarification


def _submit_configured_approval(review, actor):
    workflows = _active_matching_workflows(review)
    if len(workflows) > 1:
        raise ValidationError(
            "More than one active approval workflow matches this review. Correct the workflow configuration."
        )
    if not workflows:
        return None
    if ApprovalRequest.objects.filter(entity_type=REVIEW_ENTITY, entity_id=str(review.pk)).exists():
        raise ValidationError("An approval request already exists for this review.")
    return create_approval_request(
        workflow_id=workflows[0].pk,
        entity_type=REVIEW_ENTITY,
        entity_id=review.pk,
        actor=actor,
        submission_comment=review.completion_comment,
        snapshot_metadata={
            "enquiry_number": review.enquiry.enquiry_number,
            "revision_number": review.revision_number,
            "result": review.result,
        },
    )


def complete_review(*, review_id, actor, result, completion_comment):
    if result not in {
        EngineeringFeasibilityReview.Result.FEASIBLE,
        EngineeringFeasibilityReview.Result.FEASIBLE_WITH_CONDITIONS,
    }:
        raise ValidationError({"result": ["Choose Feasible or Feasible with conditions."]})
    if not completion_comment.strip():
        raise ValidationError({"completion_comment": ["Add a completion comment."]})
    with transaction.atomic():
        review = (
            EngineeringFeasibilityReview.objects.select_for_update()
            .select_related("enquiry", "enquiry__customer")
            .get(pk=review_id)
        )
        _require(actor, "engineering.feasibility.complete", review)
        if review.status != EngineeringFeasibilityReview.Status.IN_REVIEW:
            raise ValidationError("Only an active review with no outstanding clarification can be completed.")
        if review.clarifications.filter(status__in=UNRESOLVED_CLARIFICATIONS).exists():
            raise ValidationError("Close all Workshop clarifications before completing the review.")
        if not review.technical_summary.strip():
            raise ValidationError(
                {"technical_summary": ["Add the Workshop conclusion before completing the review."]}
            )
        old_status = review.status
        review.status = EngineeringFeasibilityReview.Status.FEASIBLE
        review.result = result
        review.completion_comment = completion_comment.strip()
        review.completed_at = timezone.now()
        review.completed_by = actor
        review.save(
            update_fields=[
                "status",
                "result",
                "completion_comment",
                "completed_at",
                "completed_by",
                "updated_at",
            ]
        )
        approval = _submit_configured_approval(review, actor)
        publish(
            review_event(
                review,
                actor,
                "engineering.review.completed",
                "COMPLETE",
                (
                    f"{review.enquiry.enquiry_number} Workshop Review completed: "
                    f"{review.get_result_display()}"
                ),
                metadata={
                    "recipient_user_id": str(review.enquiry.responsible_salesperson.user_id),
                    "approval_request_id": str(approval.pk) if approval else "",
                },
                changes={
                    "status": {"old": old_status, "new": review.status},
                    "result": {"old": "", "new": result},
                },
            )
        )
        return review


def mark_not_feasible(*, review_id, actor, completion_comment):
    if not completion_comment.strip():
        raise ValidationError(
            {"completion_comment": ["Explain why the Workshop cannot approve the requirement."]}
        )
    with transaction.atomic():
        review = (
            EngineeringFeasibilityReview.objects.select_for_update()
            .select_related("enquiry", "enquiry__customer")
            .get(pk=review_id)
        )
        _require(actor, "engineering.feasibility.mark_not_feasible", review)
        if review.status != EngineeringFeasibilityReview.Status.IN_REVIEW:
            raise ValidationError("Only an active Workshop Review can be marked as cannot approve.")
        if review.clarifications.filter(status__in=UNRESOLVED_CLARIFICATIONS).exists():
            raise ValidationError("Close all Workshop clarifications before completing the review.")
        if not review.technical_summary.strip():
            raise ValidationError(
                {"technical_summary": ["Add the Workshop conclusion before completing the review."]}
            )
        old_status = review.status
        review.status = EngineeringFeasibilityReview.Status.NOT_FEASIBLE
        review.result = EngineeringFeasibilityReview.Result.NOT_FEASIBLE
        review.completion_comment = completion_comment.strip()
        review.completed_at = timezone.now()
        review.completed_by = actor
        review.save(
            update_fields=[
                "status",
                "result",
                "completion_comment",
                "completed_at",
                "completed_by",
                "updated_at",
            ]
        )
        publish(
            review_event(
                review,
                actor,
                "engineering.review.not_feasible",
                "COMPLETE",
                f"Workshop cannot approve {review.enquiry.enquiry_number}",
                metadata={"recipient_user_id": str(review.enquiry.responsible_salesperson.user_id)},
                changes={
                    "status": {"old": old_status, "new": review.status},
                    "result": {"old": "", "new": review.result},
                },
            )
        )
        return review


def reassess_review(*, review_id, actor, reason):
    if not reason.strip():
        raise ValidationError({"reason": ["Explain why reassessment is required."]})
    with transaction.atomic():
        current = (
            EngineeringFeasibilityReview.objects.select_for_update()
            .select_related("enquiry", "enquiry__customer")
            .get(pk=review_id)
        )
        _require(actor, "engineering.feasibility.reassess", current)
        Enquiry.objects.select_for_update().get(pk=current.enquiry_id)
        if not current.is_current or current.status not in {
            EngineeringFeasibilityReview.Status.FEASIBLE,
            EngineeringFeasibilityReview.Status.NOT_FEASIBLE,
        }:
            raise ValidationError("Only the current completed review can be reassessed.")
        old_status = current.status
        current.is_current = False
        current.status = EngineeringFeasibilityReview.Status.SUPERSEDED
        current.save(update_fields=["is_current", "status", "updated_at"])
        review = EngineeringFeasibilityReview.objects.create(
            company=current.company,
            enquiry=current.enquiry,
            revision_number=current.revision_number + 1,
            assigned_engineer=current.assigned_engineer,
            created_by=actor,
            supersedes=current,
        )
        publish(
            review_event(
                current,
                actor,
                "engineering.review.superseded",
                "STATUS_CHANGE",
                f"Workshop Review revision {current.revision_number} superseded",
                metadata={"reason": reason.strip(), "new_review_id": str(review.pk)},
                changes={
                    "status": {"old": old_status, "new": current.status},
                    "is_current": {"old": True, "new": False},
                },
            )
        )
        publish(
            review_event(
                review,
                actor,
                "engineering.review.reassessment_created",
                "CREATE",
                f"Workshop reassessment revision {review.revision_number} created",
                metadata={"reason": reason.strip(), "supersedes_id": str(current.pk)},
            )
        )
        return review
