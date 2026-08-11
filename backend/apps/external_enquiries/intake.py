import base64
import hashlib
import hmac
import re
import uuid
from types import SimpleNamespace

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework.exceptions import APIException, Throttled

from apps.crm.models import CustomerContact
from apps.crm.services import find_customer_duplicates
from apps.documents.storage import get_storage
from apps.documents.validators import validate_upload

from .models import ExternalEnquiryAttachment, ExternalEnquirySubmission


class IntakeConflict(APIException):
    status_code = 409
    default_detail = "This submission identifier was already used for different content."
    default_code = "external_submission_conflict"


def normalize_phone(value):
    digits = re.sub(r"\D", "", value or "")
    if len(digits) > 10 and digits.startswith("91"):
        digits = digits[2:]
    return digits[-10:]


def remote_ip_hash(request):
    address = request.META.get("REMOTE_ADDR", "")
    if not address:
        return ""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        address.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def enforce_rate_limit(credential, request):
    bucket = int(request.headers.get("X-Timestamp", "0") or 0) // 60
    key = f"website-intake:{credential.pk}:{remote_ip_hash(request)}:{bucket}"
    if cache.add(key, 1, timeout=90):
        return
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=90)
        count = 1
    if count > settings.WEBSITE_INTAKE_RATE_LIMIT_PER_MINUTE:
        raise Throttled(detail="Website enquiry rate limit reached. Please retry shortly.")


def classify_spam(payload):
    if payload.get("honeypot", "").strip():
        return ExternalEnquirySubmission.SpamStatus.SPAM
    text = f"{payload.get('subject', '')} {payload.get('message', '')}".lower()
    url_count = len(re.findall(r"https?://|www\.", text))
    repeated = bool(re.search(r"(.)\1{19,}", text))
    if payload.get("captcha_verified") is False or url_count > 5 or repeated:
        return ExternalEnquirySubmission.SpamStatus.SUSPICIOUS
    return ExternalEnquirySubmission.SpamStatus.LIKELY_VALID


def find_submission_candidates(submission):
    customers = {
        item["id"]: item
        for item in find_customer_duplicates(
            company=submission.company,
            legal_name=submission.company_name,
            email=submission.email,
            phone=submission.phone,
        )
    }
    contact_query = Q()
    if submission.email:
        contact_query |= Q(email__iexact=submission.email)
    contacts = []
    if submission.normalized_phone or submission.email:
        for contact in (
            CustomerContact.objects.select_related("customer")
            .filter(
                customer__company=submission.company,
            )
            .filter(contact_query if submission.email else Q())[:500]
        ):
            reasons = []
            if submission.email and contact.email.lower() == submission.email:
                reasons.append("Email matches")
            if submission.normalized_phone and normalize_phone(contact.phone) == submission.normalized_phone:
                reasons.append("Phone matches")
            if not reasons:
                continue
            contacts.append(
                {
                    "id": str(contact.pk),
                    "display_name": contact.display_name,
                    "customer_id": str(contact.customer_id),
                    "customer_code": contact.customer.customer_code,
                    "customer_name": contact.customer.legal_name,
                    "reasons": reasons,
                }
            )
            customer = customers.setdefault(
                str(contact.customer_id),
                {
                    "id": str(contact.customer_id),
                    "customer_code": contact.customer.customer_code,
                    "legal_name": contact.customer.legal_name,
                    "status": contact.customer.status,
                    "reasons": [],
                },
            )
            for reason in reasons:
                contact_reason = f"Contact {reason.lower()}"
                if contact_reason not in customer["reasons"]:
                    customer["reasons"].append(contact_reason)
    return {"customers": list(customers.values()), "contacts": contacts}


def _existing_submission(credential, payload):
    return (
        ExternalEnquirySubmission.objects.filter(credential=credential)
        .filter(
            Q(idempotency_key=payload["idempotency_key"]) | Q(external_submission_id=payload["submission_id"])
        )
        .first()
    )


def _idempotent(existing, payload_checksum):
    if existing.payload_checksum != payload_checksum:
        raise IntakeConflict()
    return existing, False


def create_submission(*, credential, request_id, payload, payload_checksum, request):
    existing = _existing_submission(credential, payload)
    if existing:
        return _idempotent(existing, payload_checksum)

    attachment_payloads = payload.pop("attachments", [])
    category = SimpleNamespace(
        allowed_extensions=settings.WEBSITE_INTAKE_ALLOWED_EXTENSIONS,
        max_upload_size_mb=settings.WEBSITE_INTAKE_ATTACHMENT_MAX_MB,
    )
    validated_attachments = []
    for item in attachment_payloads:
        content = ContentFile(base64.b64decode(item["content_base64"]), name=item["filename"])
        validated_attachments.append((content, validate_upload(content, category)))

    stored_keys = []
    storage = get_storage()
    submission_id = uuid.uuid4()
    spam_status = classify_spam(payload)
    review_status = (
        ExternalEnquirySubmission.ReviewStatus.SPAM
        if spam_status == ExternalEnquirySubmission.SpamStatus.SPAM
        else ExternalEnquirySubmission.ReviewStatus.NEW
    )
    try:
        with transaction.atomic():
            submission = ExternalEnquirySubmission.objects.create(
                id=submission_id,
                company=credential.company,
                credential=credential,
                channel=ExternalEnquirySubmission.Channel.WEBSITE,
                source_type=payload["source_type"],
                external_submission_id=payload["submission_id"],
                idempotency_key=payload["idempotency_key"],
                request_id=request_id,
                payload_checksum=payload_checksum,
                submitted_at=payload.get("submitted_at"),
                person_name=payload["name"],
                company_name=payload.get("company", ""),
                email=payload.get("email", ""),
                phone=payload.get("phone", ""),
                normalized_phone=normalize_phone(payload.get("phone", "")),
                subject=payload["subject"],
                message=payload["message"],
                product_reference=payload.get("product_reference", ""),
                product_name=payload.get("product_name", ""),
                product_url=payload.get("product_url", ""),
                source_page_url=payload.get("page_url", ""),
                referrer_url=payload.get("referrer_url", ""),
                utm_source=payload.get("utm_source", ""),
                utm_medium=payload.get("utm_medium", ""),
                utm_campaign=payload.get("utm_campaign", ""),
                utm_term=payload.get("utm_term", ""),
                utm_content=payload.get("utm_content", ""),
                remote_ip_hash=remote_ip_hash(request),
                user_agent=request.headers.get("User-Agent", "")[:500],
                spam_status=spam_status,
                review_status=review_status,
            )
            for content, validated in validated_attachments:
                attachment_id = uuid.uuid4()
                key = f"company/{credential.company_id}/external-enquiries/{submission_id}/{attachment_id}"
                storage.store(content, key, validated.mime_type)
                stored_keys.append(key)
                ExternalEnquiryAttachment.objects.create(
                    id=attachment_id,
                    submission=submission,
                    original_filename=validated.original_filename,
                    safe_display_filename=validated.safe_display_filename,
                    storage_key=key,
                    mime_type=validated.mime_type,
                    extension=validated.extension,
                    size_bytes=validated.size_bytes,
                    checksum_sha256=validated.checksum_sha256,
                )
            matches = find_submission_candidates(submission)
            if matches["customers"] or matches["contacts"]:
                submission.duplicate_status = ExternalEnquirySubmission.DuplicateStatus.POSSIBLE
                if submission.review_status != ExternalEnquirySubmission.ReviewStatus.SPAM:
                    submission.review_status = ExternalEnquirySubmission.ReviewStatus.POSSIBLE_DUPLICATE
                submission.save(update_fields=["duplicate_status", "review_status", "updated_at"])
            return submission, True
    except IntegrityError:
        for key in stored_keys:
            storage.delete(key)
        existing = _existing_submission(credential, payload)
        if existing:
            return _idempotent(existing, payload_checksum)
        raise
    except Exception:
        for key in stored_keys:
            storage.delete(key)
        raise
