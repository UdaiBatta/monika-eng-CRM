# Document Management

Status: implementation and automated verification complete on 2026-08-10; final signed-in browser acceptance pending.

## Purpose and boundaries

The `documents` Django app is the single private file service for future CRM, Engineering, Procurement, Quality, Service and other modules. It stores controlled metadata separately from file bytes and links records through the validated entity registry. It is not drawing management: drawing release, revision approval and engineering ownership remain later business-module work.

## Data and services

- `DocumentCategory` defines company policy, allowed extensions, size limits and default confidentiality.
- `Document` owns the business identity, current version, archive state and creator snapshots.
- `DocumentVersion` is append-only file history with an independent storage key, SHA-256 checksum, detected type, size, uploader snapshot and future malware-scan state.
- `DocumentLink` relates a document to an explicitly registered ERP record without unrestricted generic foreign keys.
- `create_document`, `add_version`, `prepare_download`, `archive_document`, `restore_document`, `link_document` and `unlink_document` are the authoritative command services.

Storage is selected with `DOCUMENT_STORAGE_BACKEND`. Development uses `LocalPrivateStorageBackend`; files are outside the public web tree and only stream through an authenticated, authorized API. `S3CompatibleStorageBackend` is ready for Cloudflare R2 configuration through `R2_ENDPOINT_URL`, `R2_BUCKET_NAME`, credentials and region. Physical keys use UUIDs, not filenames or customer names.

## API and permissions

The versioned routes include document/category list and detail, multipart upload, version upload, current and historical version download, archive, restore, link and unlink. Relevant permissions are `documents.document.view`, `.upload`, `.version_add`, `.download`, `.archive`, `.restore`, plus `documents.category.view` and `.manage`.

Every object query remains company/scope filtered. A guessed UUID is not sufficient. Download authorization is rechecked by the backend; no public local media URL is returned. Upload validation combines size, extension, filename normalization, detected signature/MIME policy and category rules. The browser `accept` filter is convenience only and is not trusted.

## Failure and recovery policy

File writes and database creation are coordinated explicitly. A failed database operation cleans up a newly stored object where possible; a storage failure does not create a valid document version. Normal employees archive/restore and never hard-delete. Database backup alone is incomplete: PostgreSQL metadata and the corresponding private object store must be restored together.

## Known limitations

Malware scanning is not claimed in Phase 1. The UI states “Not malware scanned,” and the lifecycle is ready for a future scanner/quarantine worker. R2 credentials, production lifecycle/versioning and backup policy remain deployment decisions. Browser preview is not forced; authorized download is always available.
