from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin

from .models import DocumentSequence
from .serializers import DocumentSequenceSerializer
from .services import preview_number


class DocumentSequenceViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = DocumentSequence.objects.select_related("company", "branch")
    serializer_class = DocumentSequenceSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "numbering.sequence.view",
        "retrieve": "numbering.sequence.view",
        "preview": "numbering.sequence.view",
        "default": "numbering.sequence.manage",
    }
    search_fields = ["code", "company__name", "branch__name", "financial_year"]
    filterset_fields = ["company", "branch", "financial_year", "is_active"]
    ordering_fields = ["code", "financial_year", "next_number", "created_at"]

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        sequence = self.get_object()
        return Response({"preview": preview_number(sequence), "next_number": sequence.next_number})
