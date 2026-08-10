from django.contrib import admin

from .models import Document, DocumentCategory, DocumentLink, DocumentVersion


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "company", "is_active", "default_confidential")
    list_filter = ("company", "is_active", "default_confidential")
    search_fields = ("code", "name")


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    fields = (
        "version_number",
        "safe_display_filename",
        "size_bytes",
        "checksum_sha256",
        "scan_status",
        "uploaded_at",
    )
    readonly_fields = fields
    extra = 0
    can_delete = False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "category", "status", "is_confidential", "created_at")
    list_filter = ("company", "category", "status", "is_confidential")
    search_fields = ("document_number", "title", "description")
    readonly_fields = ("current_version", "created_by_name", "created_at", "updated_at")
    inlines = (DocumentVersionInline,)


@admin.register(DocumentLink)
class DocumentLinkAdmin(admin.ModelAdmin):
    list_display = ("document", "entity_type", "entity_reference", "relationship_type", "linked_at")
    list_filter = ("entity_type", "relationship_type")
    search_fields = ("entity_reference", "entity_id", "document__title")
