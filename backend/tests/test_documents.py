import threading
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connections
from django.test import override_settings
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.documents.models import Document, DocumentCategory, DocumentVersion
from apps.documents.services import (
    add_version,
    archive_document,
    create_document,
    link_document,
    restore_document,
)
from apps.organization.models import Company
from apps.rbac.models import Permission, Role, RoleAssignment, RolePermission, ScopeType


def pdf(name="drawing.pdf", marker=b"one"):
    return SimpleUploadedFile(name, b"%PDF-1.4\n" + marker, content_type="application/pdf")


class UnsafeUpload(BytesIO):
    name = "../drawing.pdf"
    size = 12

    def chunks(self):
        yield self.read()


def category(company, **overrides):
    values = {
        "company": company,
        "code": f"DRAW-{DocumentCategory.objects.count()}",
        "name": "Engineering Drawings",
        "allowed_extensions": ["pdf"],
    }
    values.update(overrides)
    return DocumentCategory.objects.create(**values)


def grant(user, company, *codes):
    role = Role.objects.create(
        company=company,
        code=f"DOC-{Role.objects.count()}",
        name="Document user",
    )
    for code in codes:
        permission, _ = Permission.objects.get_or_create(code=code, defaults={"name": code})
        RolePermission.objects.create(role=role, permission=permission)
    RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.COMPANY,
        company=company,
    )


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(
        email="documents-admin@example.test",
        password="SafePassword-2741",
    )


@pytest.mark.django_db
def test_upload_creates_private_version_checksum_and_audit(company, admin, tmp_path):
    document_category = category(company)
    with override_settings(LOCAL_PRIVATE_STORAGE_ROOT=tmp_path):
        document = create_document(
            category=document_category,
            title="GA Drawing",
            file_object=pdf(),
            actor=admin,
        )

    version = document.current_version
    assert document.versions.count() == 1
    assert version.version_number == 1
    assert version.scan_status == DocumentVersion.ScanStatus.NOT_SCANNED
    assert version.checksum_sha256
    assert (tmp_path / version.storage_key).is_file()
    assert AuditEvent.objects.filter(
        entity_type="document",
        entity_id=str(document.pk),
        event_type="document.uploaded",
    ).exists()


@pytest.mark.django_db
def test_new_version_preserves_history_and_archive_restore(company, admin, tmp_path):
    document_category = category(company)
    with override_settings(LOCAL_PRIVATE_STORAGE_ROOT=tmp_path):
        document = create_document(
            category=document_category,
            title="Wiring Diagram",
            file_object=pdf(marker=b"v1"),
            actor=admin,
        )
        first_id = document.current_version_id
        second = add_version(
            document_id=document.pk,
            file_object=pdf(marker=b"v2"),
            actor=admin,
            notes="Approved revision",
        )
        archived = archive_document(document_id=document.pk, actor=admin, reason="Superseded")
        restored = restore_document(document_id=document.pk, actor=admin)

    document.refresh_from_db()
    assert second.version_number == 2
    assert document.versions.count() == 2
    assert document.versions.filter(pk=first_id).exists()
    assert archived.status == Document.Status.ARCHIVED
    assert restored.status == Document.Status.ACTIVE
    assert set(
        AuditEvent.objects.filter(entity_id=str(document.pk)).values_list("event_type", flat=True)
    ) >= {
        "document.version_added",
        "document.archived",
        "document.restored",
    }


@pytest.mark.django_db(transaction=True)
def test_simultaneous_versions_are_serialized_on_postgresql(company, tmp_path):
    admin = User.objects.create_superuser(
        email="concurrency-admin@example.test",
        password="SafePassword-2741",
    )
    document_category = category(company)
    with override_settings(LOCAL_PRIVATE_STORAGE_ROOT=tmp_path):
        document = create_document(
            category=document_category,
            title="Concurrent Drawing",
            file_object=pdf(marker=b"v1"),
            actor=admin,
        )
        barrier = threading.Barrier(2)
        errors = []

        def worker(number):
            close_old_connections()
            try:
                actor = User.objects.get(pk=admin.pk)
                barrier.wait(timeout=5)
                add_version(
                    document_id=document.pk,
                    file_object=pdf(name=f"drawing-{number}.pdf", marker=str(number).encode()),
                    actor=actor,
                )
            except Exception as exc:  # pragma: no cover - asserted below
                errors.append(exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=worker, args=(number,)) for number in (2, 3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

    assert errors == []
    assert set(document.versions.values_list("version_number", flat=True)) == {1, 2, 3}


@pytest.mark.django_db
def test_upload_rejects_disguised_oversize_and_unsafe_files(company, admin, tmp_path):
    document_category = category(company, max_upload_size_mb=1)
    with override_settings(LOCAL_PRIVATE_STORAGE_ROOT=tmp_path):
        with pytest.raises(ValidationError, match="does not match"):
            create_document(
                category=document_category,
                title="Disguised executable",
                file_object=SimpleUploadedFile("bad.pdf", b"MZ-not-a-pdf"),
                actor=admin,
            )
        with pytest.raises(ValidationError, match="too large"):
            create_document(
                category=document_category,
                title="Oversized drawing",
                file_object=SimpleUploadedFile("large.pdf", b"%PDF-" + b"x" * (1024 * 1024)),
                actor=admin,
            )
        unsafe = UnsafeUpload(b"%PDF-1.4\nxx")
        with pytest.raises(ValidationError, match="not safe"):
            create_document(
                category=document_category,
                title="Unsafe filename",
                file_object=unsafe,
                actor=admin,
            )


@pytest.mark.django_db
def test_document_api_download_is_scoped_and_audited(api_client, company, user, employee, admin, tmp_path):
    other_company = Company.objects.create(name="Other Engineering", code="OTHER-DOC")
    own_category = category(company)
    other_category = category(other_company)
    with override_settings(LOCAL_PRIVATE_STORAGE_ROOT=tmp_path):
        own = create_document(
            category=own_category,
            title="Own drawing",
            file_object=pdf(name="own.pdf"),
            actor=admin,
        )
        hidden = create_document(
            category=other_category,
            title="Hidden drawing",
            file_object=pdf(name="hidden.pdf"),
            actor=admin,
        )
        grant(
            user,
            company,
            "documents.document.view",
            "documents.document.download",
        )
        api_client.force_authenticate(user)

        listing = api_client.get("/api/v1/documents/")
        assert listing.status_code == 200
        assert [item["id"] for item in listing.data["results"]] == [str(own.pk)]
        assert api_client.get(f"/api/v1/documents/{hidden.pk}/download/").status_code == 404

        response = api_client.get(f"/api/v1/documents/{own.pk}/download/")
        assert response.status_code == 200
        assert response["Content-Disposition"].endswith("own.pdf")
        b"".join(response.streaming_content)
        assert AuditEvent.objects.filter(
            entity_id=str(own.pk),
            event_type="document.downloaded",
            actor_user=user,
        ).exists()
        response.close()


@pytest.mark.django_db
def test_document_link_rejects_cross_company_entity(company, admin, tmp_path):
    other_company = Company.objects.create(name="Link Other", code="LINK-OTHER")
    with override_settings(LOCAL_PRIVATE_STORAGE_ROOT=tmp_path):
        source = create_document(
            category=category(company),
            title="Source",
            file_object=pdf(name="source.pdf"),
            actor=admin,
        )
        target = create_document(
            category=category(other_company),
            title="Target",
            file_object=pdf(name="target.pdf"),
            actor=admin,
        )
        with pytest.raises(ValidationError, match="must belong"):
            link_document(
                document=source,
                entity_type="document",
                entity_id=target.pk,
                relationship_type="REFERENCE",
                actor=admin,
            )
