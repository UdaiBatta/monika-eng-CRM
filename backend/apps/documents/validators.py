import hashlib
import re
import zipfile
from dataclasses import dataclass
from pathlib import PurePath

from django.conf import settings
from rest_framework.exceptions import ValidationError


@dataclass(frozen=True)
class ValidatedUpload:
    original_filename: str
    safe_display_filename: str
    extension: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str


MIME_BY_EXTENSION = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "csv": "text/csv",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _safe_filename(name):
    normalized = name.replace("\\", "/")
    if not name or PurePath(normalized).name != normalized or "\x00" in normalized:
        raise ValidationError({"file": ["The filename is not safe. Please rename the file and try again."]})
    cleaned = re.sub(r"[^A-Za-z0-9._() -]", "_", normalized).strip(" .")
    if not cleaned:
        raise ValidationError({"file": ["The filename is not valid."]})
    return cleaned[:255]


def _detect_mime(file_object, extension):
    file_object.seek(0)
    header = file_object.read(8192)
    file_object.seek(0)
    if extension == "pdf" and header.startswith(b"%PDF-"):
        return MIME_BY_EXTENSION[extension]
    if extension == "png" and header.startswith(b"\x89PNG\r\n\x1a\n"):
        return MIME_BY_EXTENSION[extension]
    if extension in {"jpg", "jpeg"} and header.startswith(b"\xff\xd8\xff"):
        return MIME_BY_EXTENSION[extension]
    if extension == "csv":
        try:
            header.decode("utf-8-sig")
            return MIME_BY_EXTENSION[extension]
        except UnicodeDecodeError:
            return None
    if extension in {"docx", "xlsx"} and zipfile.is_zipfile(file_object):
        file_object.seek(0)
        with zipfile.ZipFile(file_object) as archive:
            names = set(archive.namelist())
        file_object.seek(0)
        if extension == "docx" and any(name.startswith("word/") for name in names):
            return MIME_BY_EXTENSION[extension]
        if extension == "xlsx" and any(name.startswith("xl/") for name in names):
            return MIME_BY_EXTENSION[extension]
    return None


def validate_upload(file_object, category):
    original = str(file_object.name)
    safe_name = _safe_filename(original)
    extension = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    allowed = set(category.allowed_extensions or settings.DOCUMENT_ALLOWED_EXTENSIONS)
    if extension not in allowed or extension not in MIME_BY_EXTENSION:
        raise ValidationError(
            {"file": [f"Files of type .{extension or 'unknown'} are not allowed for this category."]},
            code="DOCUMENT_TYPE_NOT_ALLOWED",
        )
    maximum = (category.max_upload_size_mb or settings.DOCUMENT_MAX_UPLOAD_SIZE_MB) * 1024 * 1024
    if file_object.size > maximum:
        raise ValidationError(
            {"file": [f"This file is too large. The maximum size is {maximum // (1024 * 1024)} MB."]},
            code="DOCUMENT_TOO_LARGE",
        )
    detected_mime = _detect_mime(file_object, extension)
    if not detected_mime:
        raise ValidationError(
            {"file": ["The file content does not match its file type."]},
            code="DOCUMENT_TYPE_NOT_ALLOWED",
        )
    digest = hashlib.sha256()
    file_object.seek(0)
    chunks = getattr(file_object, "chunks", None)
    for chunk in chunks() if chunks else iter(lambda: file_object.read(1024 * 1024), b""):
        digest.update(chunk)
    file_object.seek(0)
    return ValidatedUpload(
        original_filename=original[:255],
        safe_display_filename=safe_name,
        extension=extension,
        mime_type=detected_mime,
        size_bytes=file_object.size,
        checksum_sha256=digest.hexdigest(),
    )
