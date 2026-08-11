import hashlib

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.crm.models import Customer, CustomerContact
from apps.documents.models import Document
from apps.enquiries.models import Enquiry
from apps.organization.models import Company, Employee


class IntegrationCredential(TimeStampedModel):
    class IntegrationType(models.TextChoices):
        WEBSITE = "WEBSITE", "Website"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="integration_credentials")
    name = models.CharField(max_length=160)
    integration_type = models.CharField(max_length=30, choices=IntegrationType.choices)
    key_id = models.CharField(max_length=100, unique=True)
    secret_hash = models.CharField(max_length=64)
    allowed_source = models.CharField(max_length=250, blank=True)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["company", "name"]
        indexes = [
            models.Index(fields=["company", "integration_type", "is_active"], name="integration_active_idx")
        ]

    @staticmethod
    def hash_secret(secret):
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    def __str__(self):
        return f"{self.company.code} - {self.name}"


class ExternalEnquirySubmission(TimeStampedModel):
    class Channel(models.TextChoices):
        WEBSITE = "WEBSITE", "Website"

    class SourceType(models.TextChoices):
        CONTACT_FORM = "CONTACT_FORM", "Contact form"
        PRODUCT_QUOTE = "PRODUCT_QUOTE", "Product request quote"
        CAMPAIGN = "CAMPAIGN", "Campaign form"

    class SpamStatus(models.TextChoices):
        UNKNOWN = "UNKNOWN", "Not screened"
        LIKELY_VALID = "LIKELY_VALID", "Likely valid"
        SUSPICIOUS = "SUSPICIOUS", "Suspicious"
        SPAM = "SPAM", "Spam"

    class ReviewStatus(models.TextChoices):
        NEW = "NEW", "New"
        NEEDS_REVIEW = "NEEDS_REVIEW", "Needs review"
        POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE", "Possible duplicate"
        ACCEPTED = "ACCEPTED", "Accepted"
        CONVERTED = "CONVERTED", "Converted"
        REJECTED = "REJECTED", "Rejected"
        SPAM = "SPAM", "Spam"

    class DuplicateStatus(models.TextChoices):
        NONE = "NONE", "No likely duplicate"
        POSSIBLE = "POSSIBLE", "Possible duplicate"
        REVIEWED = "REVIEWED", "Reviewed"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="external_enquiries")
    credential = models.ForeignKey(
        IntegrationCredential, on_delete=models.PROTECT, related_name="submissions"
    )
    channel = models.CharField(max_length=30, choices=Channel.choices, default=Channel.WEBSITE)
    source_type = models.CharField(max_length=30, choices=SourceType.choices)
    external_submission_id = models.CharField(max_length=160)
    idempotency_key = models.CharField(max_length=160)
    request_id = models.CharField(max_length=160)
    payload_checksum = models.CharField(max_length=64)
    received_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    person_name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=250, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    normalized_phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=250)
    message = models.TextField()
    product_reference = models.CharField(max_length=160, blank=True)
    product_name = models.CharField(max_length=250, blank=True)
    product_url = models.URLField(blank=True)
    source_page_url = models.URLField(blank=True)
    referrer_url = models.URLField(blank=True)
    utm_source = models.CharField(max_length=160, blank=True)
    utm_medium = models.CharField(max_length=160, blank=True)
    utm_campaign = models.CharField(max_length=160, blank=True)
    utm_term = models.CharField(max_length=160, blank=True)
    utm_content = models.CharField(max_length=160, blank=True)
    remote_ip_hash = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    spam_status = models.CharField(max_length=30, choices=SpamStatus.choices, default=SpamStatus.UNKNOWN)
    spam_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    review_status = models.CharField(max_length=30, choices=ReviewStatus.choices, default=ReviewStatus.NEW)
    duplicate_status = models.CharField(
        max_length=30, choices=DuplicateStatus.choices, default=DuplicateStatus.NONE
    )
    matched_customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="matched_external_enquiries", null=True, blank=True
    )
    matched_contact = models.ForeignKey(
        CustomerContact,
        on_delete=models.PROTECT,
        related_name="matched_external_enquiries",
        null=True,
        blank=True,
    )
    converted_customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="converted_external_enquiries", null=True, blank=True
    )
    converted_contact = models.ForeignKey(
        CustomerContact,
        on_delete=models.PROTECT,
        related_name="converted_external_enquiries",
        null=True,
        blank=True,
    )
    converted_enquiry = models.OneToOneField(
        Enquiry, on_delete=models.PROTECT, related_name="external_submission", null=True, blank=True
    )
    assigned_to = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="assigned_external_enquiries", null=True, blank=True
    )
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_external_enquiries",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    converted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="converted_external_enquiries",
        null=True,
        blank=True,
    )
    converted_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-received_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "channel", "external_submission_id"], name="unique_external_submission"
            ),
            models.UniqueConstraint(
                fields=["credential", "idempotency_key"], name="unique_external_idempotency"
            ),
            models.UniqueConstraint(fields=["credential", "request_id"], name="unique_external_request"),
            models.CheckConstraint(
                condition=(
                    models.Q(review_status="CONVERTED", converted_enquiry__isnull=False)
                    | (models.Q(converted_enquiry__isnull=True) & ~models.Q(review_status="CONVERTED"))
                ),
                name="converted_submission_has_enquiry",
            ),
        ]
        indexes = [
            models.Index(
                fields=["company", "review_status", "-received_at"], name="external_review_queue_idx"
            ),
            models.Index(fields=["company", "email"], name="external_email_idx"),
            models.Index(fields=["company", "normalized_phone"], name="external_phone_idx"),
            models.Index(fields=["external_submission_id"], name="external_submission_idx"),
        ]

    def clean(self):
        errors = {}
        if self.credential_id and self.credential.company_id != self.company_id:
            errors["credential"] = "Integration credential must belong to this company."
        for field in ("matched_customer", "converted_customer", "assigned_to"):
            value = getattr(self, field, None)
            if value and value.company_id != self.company_id:
                errors[field] = f"{field.replace('_', ' ').title()} must belong to this company."
        for field in ("matched_contact", "converted_contact"):
            value = getattr(self, field, None)
            customer = getattr(self, field.replace("contact", "customer"), None)
            if value and value.company_id != self.company_id:
                errors[field] = f"{field.replace('_', ' ').title()} must belong to this company."
            if value and customer and value.customer_id != customer.pk:
                errors[field] = "Contact must belong to the selected customer."
        if self.converted_enquiry_id and self.converted_enquiry.company_id != self.company_id:
            errors["converted_enquiry"] = "Converted enquiry must belong to this company."
        if self.review_status == self.ReviewStatus.CONVERTED and not self.converted_enquiry_id:
            errors["converted_enquiry"] = "A converted submission must link to its CRM enquiry."
        if self.converted_enquiry_id and self.review_status != self.ReviewStatus.CONVERTED:
            errors["review_status"] = "A submission linked to an enquiry must be marked converted."
        if not self.email and not self.phone:
            errors["email"] = "Provide an email address or phone number."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        self.person_name = " ".join(self.person_name.split())
        self.company_name = " ".join(self.company_name.split())
        self.subject = " ".join(self.subject.split())
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.external_submission_id} - {self.company_name or self.person_name}"


class ExternalEnquiryAttachment(TimeStampedModel):
    class ValidationStatus(models.TextChoices):
        ACCEPTED = "ACCEPTED", "Validated"
        REJECTED = "REJECTED", "Rejected"

    class ScanStatus(models.TextChoices):
        NOT_SCANNED = "NOT_SCANNED", "Not scanned"
        PENDING = "PENDING", "Pending scan"
        CLEAN = "CLEAN", "Clean"
        QUARANTINED = "QUARANTINED", "Quarantined"
        FAILED = "FAILED", "Scan failed"

    submission = models.ForeignKey(
        ExternalEnquirySubmission, on_delete=models.PROTECT, related_name="attachments"
    )
    original_filename = models.CharField(max_length=255)
    safe_display_filename = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=500, unique=True)
    mime_type = models.CharField(max_length=120)
    extension = models.CharField(max_length=20)
    size_bytes = models.PositiveBigIntegerField()
    checksum_sha256 = models.CharField(max_length=64)
    validation_status = models.CharField(
        max_length=20, choices=ValidationStatus.choices, default=ValidationStatus.ACCEPTED
    )
    scan_status = models.CharField(max_length=20, choices=ScanStatus.choices, default=ScanStatus.NOT_SCANNED)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    promoted_document = models.OneToOneField(
        Document, on_delete=models.PROTECT, related_name="external_attachment", null=True, blank=True
    )

    class Meta:
        ordering = ["uploaded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "checksum_sha256"], name="unique_external_attachment_checksum"
            )
        ]

    @property
    def company_id(self):
        return self.submission.company_id

    def __str__(self):
        return self.safe_display_filename
