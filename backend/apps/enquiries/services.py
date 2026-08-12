from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_events import DomainEvent, publish
from apps.organization.models import Employee
from apps.rbac.services import has_permission

from .models import Enquiry


def _employee_id(user):
    return getattr(getattr(user, "employee", None), "pk", None)


def _require(user, permission, enquiry):
    if not has_permission(user, permission, enquiry):
        raise PermissionDenied("You do not have permission to change this enquiry.")


def enquiry_event(enquiry, actor, event_name, action, summary, *, metadata=None, changes=None):
    return DomainEvent(
        event_name=event_name,
        entity_type="enquiry",
        entity_id=enquiry.pk,
        company_id=enquiry.company_id,
        actor_user_id=actor.pk,
        actor_employee_id=_employee_id(actor),
        action=action,
        module="enquiries",
        summary=summary,
        changes=changes or {},
        metadata={
            "entity_reference": str(enquiry),
            "enquiry_number": enquiry.enquiry_number,
            "customer_id": str(enquiry.customer_id),
            "customer_reference": enquiry.customer.customer_code,
            **(metadata or {}),
        },
    )


def transition_enquiry(*, enquiry_id, actor, target_status, permission, reason="", **details):
    allowed_sources = {
        Enquiry.Status.RECEIVED: {Enquiry.Status.DRAFT},
        Enquiry.Status.UNDER_REVIEW: {Enquiry.Status.RECEIVED},
        Enquiry.Status.ENGINEERING_REVIEW: {
            Enquiry.Status.RECEIVED,
            Enquiry.Status.UNDER_REVIEW,
        },
        Enquiry.Status.ESTIMATION: {Enquiry.Status.ENGINEERING_REVIEW},
        Enquiry.Status.ESTIMATION_COMPLETE: {Enquiry.Status.ESTIMATION},
        Enquiry.Status.QUOTATION_PREPARATION: {Enquiry.Status.ESTIMATION_COMPLETE},
        Enquiry.Status.WON: {Enquiry.Status.QUOTATION_SENT, Enquiry.Status.NEGOTIATION},
        Enquiry.Status.LOST: {
            Enquiry.Status.RECEIVED,
            Enquiry.Status.UNDER_REVIEW,
            Enquiry.Status.ENGINEERING_REVIEW,
            Enquiry.Status.ESTIMATION,
            Enquiry.Status.ESTIMATION_COMPLETE,
            Enquiry.Status.QUOTATION_PREPARATION,
            Enquiry.Status.QUOTATION_SENT,
            Enquiry.Status.NEGOTIATION,
        },
        Enquiry.Status.CANCELLED: {
            Enquiry.Status.DRAFT,
            Enquiry.Status.RECEIVED,
            Enquiry.Status.UNDER_REVIEW,
            Enquiry.Status.ENGINEERING_REVIEW,
            Enquiry.Status.ESTIMATION,
            Enquiry.Status.ESTIMATION_COMPLETE,
            Enquiry.Status.QUOTATION_PREPARATION,
            Enquiry.Status.QUOTATION_SENT,
            Enquiry.Status.NEGOTIATION,
        },
    }
    if target_status in {Enquiry.Status.LOST, Enquiry.Status.CANCELLED} and not reason.strip():
        raise ValidationError({"reason": ["Explain why this enquiry is being closed."]})
    with transaction.atomic():
        enquiry = Enquiry.objects.select_for_update().select_related("customer").get(pk=enquiry_id)
        _require(actor, permission, enquiry)
        if enquiry.status not in allowed_sources[target_status]:
            raise ValidationError(
                f"This enquiry cannot move from {enquiry.get_status_display()} "
                f"to {Enquiry.Status(target_status).label}."
            )
        if target_status == Enquiry.Status.ESTIMATION:
            from apps.engineering_reviews.services import is_ready_for_estimation

            review = enquiry.engineering_reviews.filter(is_current=True).first()
            if not is_ready_for_estimation(review):
                raise ValidationError("The current engineering review is not ready for estimation.")
        old_status = enquiry.status
        enquiry.status = target_status
        enquiry.updated_by = actor
        if target_status == Enquiry.Status.LOST:
            enquiry.lost_reason = reason.strip()
            enquiry.competitor = details.get("competitor", "").strip()
            enquiry.customer_feedback = details.get("customer_feedback", "").strip()
        elif target_status == Enquiry.Status.CANCELLED:
            enquiry.cancellation_reason = reason.strip()
        if target_status in {Enquiry.Status.WON, Enquiry.Status.LOST, Enquiry.Status.CANCELLED}:
            enquiry.closed_at = timezone.now()
            enquiry.closed_by = actor
        enquiry.save()
        if target_status == Enquiry.Status.ENGINEERING_REVIEW:
            from apps.engineering_reviews.services import create_review_for_enquiry

            create_review_for_enquiry(enquiry=enquiry, actor=actor)
        event_name = {
            Enquiry.Status.ENGINEERING_REVIEW: "enquiry.engineering_requested",
            Enquiry.Status.ESTIMATION: "enquiry.estimation_requested",
        }.get(target_status, f"enquiry.{target_status.lower()}")
        publish(
            enquiry_event(
                enquiry,
                actor,
                event_name,
                "STATUS_CHANGE",
                f"{enquiry.enquiry_number} moved to {enquiry.get_status_display()}",
                metadata={"reason": reason.strip(), **details},
                changes={"status": {"old": old_status, "new": target_status}},
            )
        )
        return enquiry


def assign_enquiry(*, enquiry_id, salesperson_id, actor):
    with transaction.atomic():
        enquiry = Enquiry.objects.select_for_update().select_related("customer").get(pk=enquiry_id)
        _require(actor, "enquiry.enquiry.assign", enquiry)
        try:
            salesperson = Employee.objects.select_related("user").get(
                pk=salesperson_id,
                company_id=enquiry.company_id,
                employment_status=Employee.EmploymentStatus.ACTIVE,
                user__is_active=True,
            )
        except Employee.DoesNotExist as exc:
            raise ValidationError("Choose an active salesperson from this company.") from exc
        old_owner = enquiry.responsible_salesperson_id
        enquiry.responsible_salesperson = salesperson
        enquiry.updated_by = actor
        enquiry.save(update_fields=["responsible_salesperson", "updated_by", "updated_at"])
        publish(
            enquiry_event(
                enquiry,
                actor,
                "enquiry.assigned",
                "ASSIGN",
                f"{enquiry.enquiry_number} assigned to {salesperson.display_name}",
                metadata={"recipient_user_id": str(salesperson.user_id)},
                changes={
                    "responsible_salesperson": {
                        "old": str(old_owner or ""),
                        "new": str(salesperson.pk),
                    }
                },
            )
        )
        return enquiry
