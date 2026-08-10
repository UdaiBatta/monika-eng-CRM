from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel
from apps.organization.models import Company


class DocumentCategory(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="document_categories")
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    default_confidential = models.BooleanField(default=False)
    allowed_extensions = models.JSONField(default=list, blank=True)
    max_upload_size_mb = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["company__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["company", "code"], name="unique_document_category_code")
        ]
        indexes = [models.Index(fields=["company", "is_active"], name="doc_category_company_idx")]

    def clean(self):
        normalized = []
        for extension in self.allowed_extensions:
            value = str(extension).lower().lstrip(".")
            if not value.isalnum():
                raise ValidationError(
                    {"allowed_extensions": "Use simple file extensions such as pdf or xlsx."}
                )
            normalized.append(value)
        self.allowed_extensions = sorted(set(normalized))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company.code} - {self.name}"


class Document(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ARCHIVED = "ARCHIVED", "Archived"

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="documents")
    document_number = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    category = models.ForeignKey(DocumentCategory, on_delete=models.PROTECT, related_name="documents")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_documents"
    )
    created_by_name = models.CharField(max_length=200)
    is_confidential = models.BooleanField(default=False)
    current_version = models.ForeignKey(
        "DocumentVersion", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="archived_documents",
    )
    archive_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "-created_at"], name="document_company_time_idx"),
            models.Index(fields=["category", "status"], name="document_category_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "document_number"],
                condition=~models.Q(document_number=""),
                name="unique_company_document_number",
            )
        ]

    def clean(self):
        if self.category_id and self.category.company_id != self.company_id:
            raise ValidationError({"category": "Document category must belong to the selected company."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.document_number or self.title


class DocumentVersion(TimeStampedModel):
    class ScanStatus(models.TextChoices):
        NOT_SCANNED = "NOT_SCANNED", "Not scanned"
        PENDING_SCAN = "PENDING_SCAN", "Pending scan"
        CLEAN = "CLEAN", "Clean"
        QUARANTINED = "QUARANTINED", "Quarantined"
        FAILED_SCAN = "FAILED_SCAN", "Scan failed"

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    original_filename = models.CharField(max_length=255)
    safe_display_filename = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=500, unique=True)
    mime_type = models.CharField(max_length=120)
    file_extension = models.CharField(max_length=20)
    size_bytes = models.PositiveBigIntegerField()
    checksum_sha256 = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="document_versions"
    )
    uploaded_by_name = models.CharField(max_length=200)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    scan_status = models.CharField(
        max_length=20, choices=ScanStatus.choices, default=ScanStatus.NOT_SCANNED
    )

    class Meta:
        ordering = ["-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version_number"], name="unique_document_version_number"
            ),
            models.CheckConstraint(
                condition=models.Q(version_number__gt=0),
                name="positive_document_version",
            ),
        ]
        indexes = [models.Index(fields=["document", "-version_number"], name="document_version_idx")]

    @property
    def company_id(self):
        return self.document.company_id

    def __str__(self):
        return f"{self.document} - Version {self.version_number}"


class DocumentLink(TimeStampedModel):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="links")
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=100)
    entity_reference = models.CharField(max_length=250, blank=True)
    relationship_type = models.CharField(max_length=80, default="RELATED")
    linked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="document_links"
    )
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-linked_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "entity_type", "entity_id", "relationship_type"],
                name="unique_document_entity_link",
            )
        ]
        indexes = [models.Index(fields=["entity_type", "entity_id"], name="document_link_entity_idx")]

    @property
    def company_id(self):
        return self.document.company_id

    def __str__(self):
        return f"{self.document} - {self.entity_reference or self.entity_id}"
