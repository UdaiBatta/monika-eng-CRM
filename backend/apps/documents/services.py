import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.domain_events import DomainEvent, publish
from apps.core.entity_registry import entity_company_id, entity_reference, resolve_entity
from apps.rbac.services import has_permission

from .models import Document, DocumentLink, DocumentVersion
from .storage import get_storage
from .validators import validate_upload


def _display_name(user):
    try:
        return user.employee.display_name
    except Exception:
        return user.get_full_name() or user.email


def _actor_employee_id(user):
    try:
        return user.employee.id
    except Exception:
        return None


def _require(user, permission, context):
    if not has_permission(user, permission, context):
        raise ValidationError(
            "You do not have permission to complete this document action.",
            code="DOCUMENT_ACCESS_DENIED",
        )


def _event(name, document, actor, action, summary, *, metadata=None, changes=None):
    return DomainEvent(
        event_name=name,
        entity_type="document",
        entity_id=document.pk,
        company_id=document.company_id,
        actor_user_id=actor.pk,
        actor_employee_id=_actor_employee_id(actor),
        action=action,
        module="documents",
        summary=summary,
        metadata={"entity_reference": str(document), **(metadata or {})},
        changes=changes or {},
    )


def create_document(*, category, title, file_object, actor, description="", notes="", is_confidential=None):
    _require(actor, "documents.document.upload", category.company)
    if not category.is_active:
        raise ValidationError({"category": ["Choose an active document category."]})
    validated = validate_upload(file_object, category)
    document_id, version_id = uuid.uuid4(), uuid.uuid4()
    key = f"company/{category.company_id}/documents/{document_id}/{version_id}"
    storage = get_storage()
    storage.store(file_object, key, validated.mime_type)
    try:
        with transaction.atomic():
            document = Document.objects.create(
                id=document_id,
                company=category.company,
                title=title,
                description=description,
                category=category,
                created_by=actor,
                created_by_name=_display_name(actor),
                is_confidential=category.default_confidential if is_confidential is None else is_confidential,
            )
            version = DocumentVersion.objects.create(
                id=version_id,
                document=document,
                version_number=1,
                original_filename=validated.original_filename,
                safe_display_filename=validated.safe_display_filename,
                storage_key=key,
                mime_type=validated.mime_type,
                file_extension=validated.extension,
                size_bytes=validated.size_bytes,
                checksum_sha256=validated.checksum_sha256,
                uploaded_by=actor,
                uploaded_by_name=_display_name(actor),
                notes=notes,
            )
            document.current_version = version
            document.save(update_fields=["current_version", "updated_at"])
            publish(
                _event(
                    "document.uploaded",
                    document,
                    actor,
                    "UPLOAD",
                    f"Document uploaded: {document.title}",
                    metadata={"version": 1, "filename": version.safe_display_filename},
                )
            )
            return document
    except Exception:
        storage.delete(key)
        raise


def prepare_download(*, document, actor):
    _require(actor, "documents.document.download", document)
    version = document.current_version
    if version is None:
        raise ValidationError("This document does not have a downloadable version.")
    storage = get_storage()
    if not storage.exists(version.storage_key):
        raise ValidationError("The stored document file is unavailable.", code="DOCUMENT_FILE_MISSING")
    with transaction.atomic():
        publish(
            _event(
                "document.downloaded",
                document,
                actor,
                "DOWNLOAD",
                f"Document downloaded: {document.title}",
                metadata={
                    "version": version.version_number,
                    "filename": version.safe_display_filename,
                },
            )
        )
    return storage, version


def add_version(*, document_id, file_object, actor, notes=""):
    document = Document.objects.select_related("company", "category").get(pk=document_id)
    _require(actor, "documents.document.version_add", document)
    if document.status == Document.Status.ARCHIVED:
        raise ValidationError("Restore this document before adding a newer version.")
    validated = validate_upload(file_object, document.category)
    version_id = uuid.uuid4()
    key = f"company/{document.company_id}/documents/{document.pk}/{version_id}"
    storage = get_storage()
    storage.store(file_object, key, validated.mime_type)
    try:
        with transaction.atomic():
            locked = Document.objects.select_for_update().select_related("category").get(pk=document_id)
            next_version = (locked.versions.aggregate(value=Max("version_number"))["value"] or 0) + 1
            version = DocumentVersion.objects.create(
                id=version_id,
                document=locked,
                version_number=next_version,
                original_filename=validated.original_filename,
                safe_display_filename=validated.safe_display_filename,
                storage_key=key,
                mime_type=validated.mime_type,
                file_extension=validated.extension,
                size_bytes=validated.size_bytes,
                checksum_sha256=validated.checksum_sha256,
                uploaded_by=actor,
                uploaded_by_name=_display_name(actor),
                notes=notes,
            )
            locked.current_version = version
            locked.save(update_fields=["current_version", "updated_at"])
            publish(
                _event(
                    "document.version_added",
                    locked,
                    actor,
                    "VERSION_CREATE",
                    f"Version {next_version} added to {locked.title}",
                    metadata={"version": next_version, "filename": version.safe_display_filename},
                )
            )
            return version
    except Exception:
        storage.delete(key)
        raise


def archive_document(*, document_id, actor, reason):
    with transaction.atomic():
        document = Document.objects.select_for_update().get(pk=document_id)
        _require(actor, "documents.document.archive", document)
        if document.status == Document.Status.ARCHIVED:
            return document
        document.status = Document.Status.ARCHIVED
        document.archived_at = timezone.now()
        document.archived_by = actor
        document.archive_reason = reason
        document.save(
            update_fields=["status", "archived_at", "archived_by", "archive_reason", "updated_at"]
        )
        publish(
            _event("document.archived", document, actor, "ARCHIVE", f"Document archived: {document.title}")
        )
        return document


def restore_document(*, document_id, actor):
    with transaction.atomic():
        document = Document.objects.select_for_update().get(pk=document_id)
        _require(actor, "documents.document.restore", document)
        if document.status == Document.Status.ACTIVE:
            return document
        document.status = Document.Status.ACTIVE
        document.archived_at = None
        document.archived_by = None
        document.archive_reason = ""
        document.save(
            update_fields=["status", "archived_at", "archived_by", "archive_reason", "updated_at"]
        )
        publish(
            _event("document.restored", document, actor, "RESTORE", f"Document restored: {document.title}")
        )
        return document


def link_document(*, document, entity_type, entity_id, relationship_type, actor):
    _require(actor, "documents.document.upload", document)
    try:
        entity = resolve_entity(entity_type, entity_id, "documents")
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc
    if entity_company_id(entity) != document.company_id:
        raise ValidationError({"entity_id": ["The related record must belong to the document company."]})
    link, created = DocumentLink.objects.get_or_create(
        document=document,
        entity_type=entity_type,
        entity_id=str(entity_id),
        relationship_type=relationship_type,
        defaults={"entity_reference": entity_reference(entity), "linked_by": actor},
    )
    if created:
        publish(
            _event(
                "document.linked",
                document,
                actor,
                "ASSIGN",
                f"Document linked to {link.entity_reference}",
                metadata={"related_type": entity_type, "related_id": str(entity_id)},
            )
        )
    return link


def unlink_document(*, link, actor):
    document = link.document
    _require(actor, "documents.document.upload", document)
    reference = link.entity_reference
    link.delete()
    publish(
        _event(
            "document.unlinked",
            document,
            actor,
            "UNASSIGN",
            f"Document unlinked from {reference}",
        )
    )
