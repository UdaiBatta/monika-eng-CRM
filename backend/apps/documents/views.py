from django.http import FileResponse, HttpResponseRedirect
from django.utils.encoding import escape_uri_path
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.audit.mixins import AuditModelViewSetMixin
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin

from .models import Document, DocumentCategory
from .serializers import (
    DocumentArchiveSerializer,
    DocumentCategorySerializer,
    DocumentLinkCommandSerializer,
    DocumentSerializer,
    DocumentUploadSerializer,
    DocumentVersionSerializer,
    DocumentVersionUploadSerializer,
)
from .services import (
    add_version,
    archive_document,
    link_document,
    prepare_download,
    restore_document,
    unlink_document,
)


class DocumentCategoryViewSet(
    AuditModelViewSetMixin,
    ScopedQuerysetMixin,
    viewsets.ModelViewSet,
):
    queryset = DocumentCategory.objects.select_related("company")
    serializer_class = DocumentCategorySerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "documents.category.view",
        "retrieve": "documents.category.view",
        "default": "documents.category.manage",
    }
    search_fields = ["code", "name", "description"]
    filterset_fields = ["company", "is_active", "default_confidential"]
    ordering_fields = ["code", "name", "created_at", "updated_at"]


class DocumentViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Document.objects.select_related(
        "company",
        "category",
        "created_by",
        "current_version",
        "archived_by",
    ).prefetch_related("versions", "links")
    serializer_class = DocumentSerializer
    permission_classes = [HasFoundationPermission]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    permission_map = {
        "list": "documents.document.view",
        "retrieve": "documents.document.view",
        "create": "documents.document.upload",
        "add_version": "documents.document.version_add",
        "download": "documents.document.download",
        "download_version": "documents.document.download",
        "archive": "documents.document.archive",
        "restore": "documents.document.restore",
        "link": "documents.document.upload",
        "unlink": "documents.document.upload",
        "default": "documents.document.view",
    }
    search_fields = [
        "document_number",
        "title",
        "description",
        "current_version__safe_display_filename",
    ]
    filterset_fields = ["company", "category", "status", "is_confidential"]
    ordering_fields = ["title", "created_at", "updated_at", "archived_at"]

    def create(self, request):
        serializer = DocumentUploadSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        return Response(self.get_serializer(document).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="versions")
    def add_version(self, request, pk=None):
        document = self.get_object()
        serializer = DocumentVersionUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = add_version(
            document_id=document.pk,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(DocumentVersionSerializer(version).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        document = self.get_object()
        storage_backend, version = prepare_download(document=document, actor=request.user)
        return self.download_response(storage_backend, version)

    @action(
        detail=True,
        methods=["get"],
        url_path=r"versions/(?P<version_id>[^/.]+)/download",
    )
    def download_version(self, request, pk=None, version_id=None):
        document = self.get_object()
        storage_backend, version = prepare_download(
            document=document,
            actor=request.user,
            version_id=version_id,
        )
        return self.download_response(storage_backend, version)

    @staticmethod
    def download_response(storage_backend, version):
        signed_url = storage_backend.generate_download_access(version.storage_key)
        if signed_url:
            return HttpResponseRedirect(signed_url)
        response = FileResponse(storage_backend.open(version.storage_key), content_type=version.mime_type)
        response["Content-Disposition"] = (
            f"attachment; filename*=UTF-8''{escape_uri_path(version.safe_display_filename)}"
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        document = self.get_object()
        serializer = DocumentArchiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = archive_document(
            document_id=document.pk,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(self.get_serializer(document).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        document = restore_document(document_id=self.get_object().pk, actor=request.user)
        return Response(self.get_serializer(document).data)

    @action(detail=True, methods=["post"])
    def link(self, request, pk=None):
        document = self.get_object()
        serializer = DocumentLinkCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = link_document(document=document, actor=request.user, **serializer.validated_data)
        return Response({"id": link.pk}, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"links/(?P<link_id>[^/.]+)",
    )
    def unlink(self, request, pk=None, link_id=None):
        link = self.get_object().links.get(pk=link_id)
        unlink_document(link=link, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
