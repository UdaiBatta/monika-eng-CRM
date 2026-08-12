import uuid
from types import SimpleNamespace

from django.core.files import File
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.core.domain_events import DomainEvent, publish
from apps.crm.models import CrmActivity, Customer, CustomerContact
from apps.crm.serializers import CrmActivitySerializer, CustomerContactSerializer, CustomerSerializer
from apps.documents.models import Document, DocumentCategory, DocumentLink, DocumentVersion
from apps.documents.storage import get_storage
from apps.enquiries.serializers import EnquirySerializer
from apps.organization.models import Employee
from apps.rbac.services import has_permission

from .intake import find_submission_candidates, normalize_phone
from .models import (
    ExternalEnquiryAttachment,
    ExternalEnquirySubmission,
    IncomingEnquirySourceEvent,
)


def _employee_id(user):
    return getattr(getattr(user, "employee", None), "pk", None)


def _require(user, permission, submission):
    if not has_permission(user, permission, submission):
        raise PermissionDenied("You do not have permission to manage this incoming enquiry.")


def _event(name, submission, actor, action, summary, *, metadata=None, changes=None):
    return DomainEvent(
        event_name=name,
        entity_type="external_enquiry_submission",
        entity_id=submission.pk,
        company_id=submission.company_id,
        actor_user_id=actor.pk if actor else None,
        actor_employee_id=_employee_id(actor) if actor else None,
        action=action,
        module="external_enquiries",
        summary=summary,
        metadata={
            "entity_reference": str(submission),
            "external_submission_id": submission.external_submission_id,
            **(metadata or {}),
        },
        changes=changes or {},
    )


SOURCE_TYPES = {
    ExternalEnquirySubmission.Channel.TRADEINDIA: ExternalEnquirySubmission.SourceType.MARKETPLACE,
    ExternalEnquirySubmission.Channel.WHATSAPP: ExternalEnquirySubmission.SourceType.CHAT,
    ExternalEnquirySubmission.Channel.PHONE: ExternalEnquirySubmission.SourceType.PHONE_CALL,
    ExternalEnquirySubmission.Channel.EMAIL: ExternalEnquirySubmission.SourceType.EMAIL_MESSAGE,
    ExternalEnquirySubmission.Channel.IN_PERSON: ExternalEnquirySubmission.SourceType.IN_PERSON,
    ExternalEnquirySubmission.Channel.MANUAL: ExternalEnquirySubmission.SourceType.MANUAL_ENTRY,
    ExternalEnquirySubmission.Channel.OTHER: ExternalEnquirySubmission.SourceType.OTHER,
}


def create_manual_submission(*, actor, data):
    employee = Employee.objects.filter(user=actor, user__is_active=True).first()
    if not employee or not has_permission(
        actor, "crm.external_enquiry.review", {"company": employee.company_id}
    ):
        raise PermissionDenied("You do not have permission to capture incoming enquiries.")
    assigned_to = None
    if data.get("assigned_to_id"):
        assigned_to = Employee.objects.filter(
            pk=data["assigned_to_id"],
            company_id=employee.company_id,
            employment_status=Employee.EmploymentStatus.ACTIVE,
            user__is_active=True,
        ).first()
        if not assigned_to:
            raise ValidationError("Choose an active employee from this company.")
    historical_received_at = data.get("received_at")
    with transaction.atomic():
        reference = data.get("source_reference", "").strip()
        submission = ExternalEnquirySubmission.objects.create(
            company_id=employee.company_id,
            channel=data["channel"],
            source_type=SOURCE_TYPES[data["channel"]],
            external_submission_id=reference or f"IN-{uuid.uuid4().hex[:12].upper()}",
            received_at=historical_received_at or timezone.now(),
            person_name=data["person_name"],
            company_name=data.get("company_name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            normalized_phone=normalize_phone(data.get("phone", "")),
            subject=data["subject"],
            message=data["message"],
            review_status=ExternalEnquirySubmission.ReviewStatus.NEEDS_REVIEW,
            spam_status=ExternalEnquirySubmission.SpamStatus.LIKELY_VALID,
            assigned_to=assigned_to,
            priority=data["priority"],
            captured_by=actor,
        )
        IncomingEnquirySourceEvent.objects.create(
            submission=submission,
            channel=submission.channel,
            source_reference=reference,
            original_message=submission.message,
            captured_by=actor,
            metadata=(
                {
                    "historical_import": True,
                    "received_at": submission.received_at.isoformat(),
                }
                if historical_received_at
                else {}
            ),
        )
        matches = find_submission_candidates(submission)
        if matches["customers"] or matches["contacts"]:
            submission.duplicate_status = ExternalEnquirySubmission.DuplicateStatus.POSSIBLE
            submission.review_status = ExternalEnquirySubmission.ReviewStatus.POSSIBLE_DUPLICATE
            submission.save(update_fields=["duplicate_status", "review_status", "updated_at"])
        publish(
            _event(
                "external_enquiry.received",
                submission,
                actor,
                "CREATE",
                f"{submission.get_channel_display()} enquiry captured",
                metadata={
                    "channel": submission.channel,
                    "source_type": submission.source_type,
                    "recipient_user_id": str(assigned_to.user_id) if assigned_to else None,
                },
            )
        )
        return submission


def take_ownership(*, submission_id, actor):
    employee = Employee.objects.filter(user=actor, user__is_active=True).first()
    if not employee:
        raise PermissionDenied("Your account is not linked to an active employee.")
    return assign_submission(
        submission_id=submission_id,
        employee_id=employee.pk,
        actor=actor,
    )


def assign_submission(*, submission_id, employee_id, actor, priority=None):
    with transaction.atomic():
        submission = ExternalEnquirySubmission.objects.select_for_update().get(pk=submission_id)
        _require(actor, "crm.external_enquiry.assign", submission)
        if submission.review_status in {
            ExternalEnquirySubmission.ReviewStatus.CONVERTED,
            ExternalEnquirySubmission.ReviewStatus.REJECTED,
            ExternalEnquirySubmission.ReviewStatus.SPAM,
        }:
            raise ValidationError("This incoming enquiry is no longer available for assignment.")
        try:
            employee = Employee.objects.select_related("user").get(
                pk=employee_id,
                company_id=submission.company_id,
                employment_status=Employee.EmploymentStatus.ACTIVE,
                user__is_active=True,
            )
        except Employee.DoesNotExist as exc:
            raise ValidationError("Choose an active employee from this company.") from exc
        previous = submission.assigned_to_id
        submission.assigned_to = employee
        if priority:
            submission.priority = priority
        submission.review_status = ExternalEnquirySubmission.ReviewStatus.NEEDS_REVIEW
        submission.save(update_fields=["assigned_to", "priority", "review_status", "updated_at"])
        publish(
            _event(
                "external_enquiry.assigned",
                submission,
                actor,
                "ASSIGN",
                f"Incoming enquiry assigned to {employee.display_name}",
                metadata={"recipient_user_id": str(employee.user_id)},
                changes={"assigned_to": {"old": str(previous or ""), "new": str(employee.pk)}},
            )
        )
        return submission


def decide_submission(*, submission_id, actor, target_status, reason):
    permissions = {
        ExternalEnquirySubmission.ReviewStatus.REJECTED: "crm.external_enquiry.reject",
        ExternalEnquirySubmission.ReviewStatus.SPAM: "crm.external_enquiry.mark_spam",
        ExternalEnquirySubmission.ReviewStatus.NEEDS_REVIEW: "crm.external_enquiry.review",
    }
    with transaction.atomic():
        submission = ExternalEnquirySubmission.objects.select_for_update().get(pk=submission_id)
        _require(actor, permissions[target_status], submission)
        if submission.review_status == ExternalEnquirySubmission.ReviewStatus.CONVERTED:
            raise ValidationError("A converted incoming enquiry cannot be changed.")
        old_status = submission.review_status
        if target_status == ExternalEnquirySubmission.ReviewStatus.SPAM:
            submission.spam_status = ExternalEnquirySubmission.SpamStatus.SPAM
        elif target_status == ExternalEnquirySubmission.ReviewStatus.NEEDS_REVIEW:
            submission.spam_status = ExternalEnquirySubmission.SpamStatus.UNKNOWN
        submission.review_status = target_status
        submission.rejection_reason = (
            reason.strip() if target_status != ExternalEnquirySubmission.ReviewStatus.NEEDS_REVIEW else ""
        )
        submission.reviewed_by = actor
        submission.reviewed_at = timezone.now()
        submission.save()
        publish(
            _event(
                f"external_enquiry.{target_status.lower()}",
                submission,
                actor,
                "STATUS_CHANGE",
                f"Incoming enquiry marked {submission.get_review_status_display().lower()}",
                metadata={"reason": reason.strip()},
                changes={"review_status": {"old": old_status, "new": target_status}},
            )
        )
        return submission


def _audit_created(instance, actor):
    record_event(
        actor=actor,
        company=instance.company,
        action=AuditEvent.Action.CREATE,
        entity=instance,
        summary=f"{instance._meta.verbose_name.title()} created: {instance}",
    )


def _create_customer(submission, data, actor, request_context):
    serializer = CustomerSerializer(
        data={
            **data,
            "company": str(submission.company_id),
            "source": submission.get_channel_display(),
        },
        context={"request": request_context},
    )
    serializer.is_valid(raise_exception=True)
    customer = serializer.save()
    _audit_created(customer, actor)
    return customer


def _create_contact(customer, data, actor, request_context):
    serializer = CustomerContactSerializer(
        data={**data, "customer": str(customer.pk)},
        context={"request": request_context},
    )
    serializer.is_valid(raise_exception=True)
    contact = serializer.save()
    _audit_created(contact, actor)
    return contact


def _create_enquiry(submission, customer, contact, employee, priority, actor, request_context):
    product = ""
    if submission.product_name or submission.product_reference:
        product = f"\n\nSource product: {submission.product_name or submission.product_reference}"
        if submission.product_reference:
            product += f" ({submission.product_reference})"
        if submission.product_url:
            product += f"\nProduct page: {submission.product_url}"
    serializer = EnquirySerializer(
        data={
            "customer": str(customer.pk),
            "customer_contact": str(contact.pk),
            "source": submission.get_channel_display(),
            "received_date": timezone.localtime(submission.received_at).date().isoformat(),
            "customer_reference": submission.external_submission_id,
            "subject": submission.subject,
            "description": f"{submission.message}{product}",
            "priority": priority,
            "responsible_salesperson": str(employee.pk),
        },
        context={"request": request_context},
    )
    serializer.is_valid(raise_exception=True)
    enquiry = serializer.save()
    _audit_created(enquiry, actor)
    return enquiry


def _promote_attachment(attachment, category, enquiry, actor, stored_keys):
    if category.company_id != enquiry.company_id or not category.is_active:
        raise ValidationError("Choose an active document category from this company.")
    if not has_permission(actor, "documents.document.upload", enquiry):
        raise PermissionDenied("You do not have permission to promote incoming enquiry attachments.")
    storage = get_storage()
    document_id, version_id = uuid.uuid4(), uuid.uuid4()
    key = f"company/{enquiry.company_id}/documents/{document_id}/{version_id}"
    with storage.open(attachment.storage_key) as source:
        storage.store(File(source, name=attachment.safe_display_filename), key, attachment.mime_type)
    stored_keys.append(key)
    document = Document.objects.create(
        id=document_id,
        company=enquiry.company,
        title=f"Incoming enquiry - {attachment.safe_display_filename}",
        description=f"Promoted from source submission {attachment.submission.external_submission_id}",
        category=category,
        created_by=actor,
        created_by_name=getattr(getattr(actor, "employee", None), "display_name", actor.email),
        is_confidential=category.default_confidential,
    )
    version = DocumentVersion.objects.create(
        id=version_id,
        document=document,
        version_number=1,
        original_filename=attachment.original_filename,
        safe_display_filename=attachment.safe_display_filename,
        storage_key=key,
        mime_type=attachment.mime_type,
        file_extension=attachment.extension,
        size_bytes=attachment.size_bytes,
        checksum_sha256=attachment.checksum_sha256,
        uploaded_by=actor,
        uploaded_by_name=getattr(getattr(actor, "employee", None), "display_name", actor.email),
        scan_status=(
            DocumentVersion.ScanStatus.CLEAN
            if attachment.scan_status == ExternalEnquiryAttachment.ScanStatus.CLEAN
            else DocumentVersion.ScanStatus.NOT_SCANNED
        ),
    )
    document.current_version = version
    document.save(update_fields=["current_version", "updated_at"])
    DocumentLink.objects.create(
        document=document,
        entity_type="enquiry",
        entity_id=str(enquiry.pk),
        entity_reference=str(enquiry),
        relationship_type="CUSTOMER_RFQ",
        linked_by=actor,
    )
    attachment.promoted_document = document
    attachment.save(update_fields=["promoted_document", "updated_at"])
    _audit_created(document, actor)
    return document


def convert_submission(*, submission_id, actor, data):
    stored_keys = []
    storage = get_storage()
    request_context = SimpleNamespace(user=actor)
    try:
        with transaction.atomic():
            submission = (
                ExternalEnquirySubmission.objects.select_for_update()
                .select_related("company")
                .prefetch_related("attachments")
                .get(pk=submission_id)
            )
            _require(actor, "crm.external_enquiry.convert", submission)
            if submission.review_status == ExternalEnquirySubmission.ReviewStatus.CONVERTED:
                raise ValidationError("This incoming enquiry has already been converted.")
            if submission.review_status in {
                ExternalEnquirySubmission.ReviewStatus.REJECTED,
                ExternalEnquirySubmission.ReviewStatus.SPAM,
            }:
                raise ValidationError("Restore this incoming enquiry for review before converting it.")
            try:
                employee = Employee.objects.select_related("user").get(
                    pk=data["responsible_salesperson_id"],
                    company_id=submission.company_id,
                    employment_status=Employee.EmploymentStatus.ACTIVE,
                    user__is_active=True,
                )
            except Employee.DoesNotExist as exc:
                raise ValidationError("Choose an active responsible employee from this company.") from exc

            if data.get("customer_id"):
                customer = Customer.objects.select_for_update().get(
                    pk=data["customer_id"], company_id=submission.company_id
                )
                if not has_permission(actor, "crm.customer.view", customer):
                    raise PermissionDenied("You cannot use this customer.")
            else:
                customer = _create_customer(submission, data["new_customer"], actor, request_context)

            if data.get("contact_id"):
                contact = CustomerContact.objects.select_for_update().get(
                    pk=data["contact_id"], customer=customer
                )
                if not has_permission(actor, "crm.contact.view", contact):
                    raise PermissionDenied("You cannot use this contact.")
            else:
                contact = _create_contact(customer, data["new_contact"], actor, request_context)

            enquiry = _create_enquiry(
                submission,
                customer,
                contact,
                employee,
                data["priority"],
                actor,
                request_context,
            )
            attachments = list(submission.attachments.filter(promoted_document__isnull=True))
            if attachments:
                if not data.get("document_category_id"):
                    raise ValidationError("Choose a document category for the incoming attachments.")
                category = DocumentCategory.objects.get(
                    pk=data["document_category_id"], company_id=submission.company_id
                )
                for attachment in attachments:
                    _promote_attachment(attachment, category, enquiry, actor, stored_keys)

            if data.get("follow_up_at"):
                follow_up = CrmActivitySerializer(
                    data={
                        "customer": str(customer.pk),
                        "contact": str(contact.pk),
                        "enquiry": str(enquiry.pk),
                        "activity_type": CrmActivity.ActivityType.FOLLOW_UP,
                        "subject": f"Follow up incoming enquiry {enquiry.enquiry_number}",
                        "next_follow_up_at": data["follow_up_at"],
                        "follow_up_owner": str(employee.pk),
                        "priority": data["priority"],
                    },
                    context={"request": request_context},
                )
                follow_up.is_valid(raise_exception=True)
                activity = follow_up.save()
                _audit_created(activity, actor)

            old_status = submission.review_status
            submission.review_status = ExternalEnquirySubmission.ReviewStatus.CONVERTED
            submission.duplicate_status = ExternalEnquirySubmission.DuplicateStatus.REVIEWED
            submission.matched_customer = customer
            submission.matched_contact = contact
            submission.converted_customer = customer
            submission.converted_contact = contact
            submission.converted_enquiry = enquiry
            submission.assigned_to = employee
            submission.reviewed_by = actor
            submission.reviewed_at = timezone.now()
            submission.converted_by = actor
            submission.converted_at = timezone.now()
            submission.save()
            publish(
                _event(
                    "external_enquiry.converted",
                    submission,
                    actor,
                    "CONVERT",
                    f"Incoming enquiry converted to {enquiry.enquiry_number}",
                    metadata={
                        "enquiry_id": str(enquiry.pk),
                        "customer_id": str(customer.pk),
                        "recipient_user_id": str(employee.user_id),
                    },
                    changes={"review_status": {"old": old_status, "new": submission.review_status}},
                )
            )
            return submission
    except Exception:
        for key in stored_keys:
            storage.delete(key)
        raise
