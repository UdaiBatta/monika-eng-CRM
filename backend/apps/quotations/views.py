from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.mixins import AuditModelViewSetMixin
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin

from .documents import generate_documents
from .models import Quotation, QuotationRevision, QuotationTemplate, QuotationTextTemplate
from .serializers import (
    CommunicationInputSerializer,
    ConfirmationInputSerializer,
    CustomerConfirmationSerializer,
    FinalizeRevisionSerializer,
    GeneratedDocumentSerializer,
    GenerateDocumentInputSerializer,
    NegotiationInputSerializer,
    QuotationCommunicationSerializer,
    QuotationCreateSerializer,
    QuotationNegotiationSerializer,
    QuotationRevisionSerializer,
    QuotationSerializer,
    QuotationTemplateSerializer,
    QuotationTextTemplateSerializer,
    RevisionUpdateSerializer,
)
from .services import (
    compare_revisions,
    confirm_customer,
    create_quotation,
    create_revision,
    finalize_revision,
    mark_ready_for_sales_order,
    record_communication,
    record_negotiation,
    update_revision,
)


class QuotationViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Quotation.objects.select_related(
        "company",
        "customer",
        "customer_contact",
        "enquiry",
        "estimate",
        "owner",
        "current_revision__currency",
    ).prefetch_related(
        "current_revision__lines",
        "current_revision__communications",
        "current_revision__negotiations",
        "current_revision__generated_documents__docx_document",
        "current_revision__generated_documents__pdf_document",
        "revisions",
    )
    serializer_class = QuotationSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "crm.quotation.view",
        "retrieve": "crm.quotation.view",
        "create": "crm.quotation.create",
        "revise": "crm.quotation.change",
        "compare": "crm.quotation.view",
        "negotiation": "crm.quotation.negotiate",
        "confirm": "crm.quotation.confirm",
        "ready_for_sales_order": "crm.quotation.ready_for_sales_order",
        "default": "crm.quotation.view",
    }
    search_fields = [
        "quotation_number",
        "customer__legal_name",
        "customer__customer_code",
        "enquiry__enquiry_number",
    ]
    filterset_fields = ["company", "status", "path", "customer", "enquiry", "owner"]
    ordering_fields = ["created_at", "updated_at", "quotation_number", "status"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("queue") == "mine":
            employee = getattr(self.request.user, "employee", None)
            return queryset.filter(owner=employee) if employee else queryset.none()
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = QuotationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quotation = create_quotation(actor=request.user, data=serializer.validated_data)
        return Response(
            QuotationSerializer(quotation, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def revise(self, request, pk=None):
        revision = create_revision(quotation_id=self.get_object().pk, actor=request.user)
        return Response(QuotationRevisionSerializer(revision).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def compare(self, request, pk=None):
        return Response(compare_revisions(self.get_object()))

    @action(detail=True, methods=["post"])
    def negotiation(self, request, pk=None):
        serializer = NegotiationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        negotiation = record_negotiation(
            quotation_id=self.get_object().pk,
            actor=request.user,
            data=serializer.validated_data,
        )
        return Response(
            QuotationNegotiationSerializer(negotiation).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        serializer = ConfirmationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        confirmation = confirm_customer(
            quotation_id=self.get_object().pk,
            actor=request.user,
            data=serializer.validated_data,
        )
        return Response(CustomerConfirmationSerializer(confirmation).data)

    @action(detail=True, methods=["post"], url_path="ready-for-sales-order")
    def ready_for_sales_order(self, request, pk=None):
        confirmation = mark_ready_for_sales_order(
            quotation_id=self.get_object().pk, actor=request.user
        )
        return Response(CustomerConfirmationSerializer(confirmation).data)


class QuotationRevisionViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = QuotationRevision.objects.select_related(
        "quotation__company", "quotation__customer", "currency", "approval_request"
    ).prefetch_related(
        "lines",
        "communications",
        "negotiations",
        "generated_documents__docx_document",
        "generated_documents__pdf_document",
    )
    serializer_class = QuotationRevisionSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "crm.quotation.view",
        "retrieve": "crm.quotation.view",
        "update_draft": "crm.quotation.change",
        "finalize": "crm.quotation.finalize",
        "communication": "crm.quotation.send",
        "generate_documents": "crm.quotation.generate_document",
        "default": "crm.quotation.view",
    }
    filterset_fields = ["quotation", "status"]

    @action(detail=True, methods=["post"], url_path="update-draft")
    def update_draft(self, request, pk=None):
        serializer = RevisionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        submitted_version = data.pop("record_version")
        revision = update_revision(
            revision_id=self.get_object().pk,
            actor=request.user,
            submitted_version=submitted_version,
            data=data,
        )
        return Response(QuotationRevisionSerializer(revision).data)

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        serializer = FinalizeRevisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        revision = finalize_revision(
            revision_id=self.get_object().pk,
            actor=request.user,
            workflow_id=serializer.validated_data.get("workflow_id"),
            comment=serializer.validated_data.get("comment", ""),
        )
        return Response(QuotationRevisionSerializer(revision).data)

    @action(detail=True, methods=["post"])
    def communication(self, request, pk=None):
        serializer = CommunicationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        communication = record_communication(
            revision_id=self.get_object().pk,
            actor=request.user,
            data=serializer.validated_data,
        )
        return Response(
            QuotationCommunicationSerializer(communication).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="generate-documents")
    def generate_documents(self, request, pk=None):
        serializer = GenerateDocumentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        generated = generate_documents(
            revision_id=self.get_object().pk,
            template_id=serializer.validated_data["template_id"],
            actor=request.user,
        )
        return Response(GeneratedDocumentSerializer(generated).data, status=status.HTTP_201_CREATED)


class QuotationTemplateViewSet(
    AuditModelViewSetMixin, ScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = QuotationTemplate.objects.select_related(
        "company", "source_document", "output_category"
    )
    serializer_class = QuotationTemplateSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "crm.quotation.view",
        "retrieve": "crm.quotation.view",
        "default": "crm.quotation.template_manage",
    }
    filterset_fields = ["company", "is_active"]


class QuotationTextTemplateViewSet(
    AuditModelViewSetMixin, ScopedQuerysetMixin, viewsets.ModelViewSet
):
    queryset = QuotationTextTemplate.objects.select_related("company")
    serializer_class = QuotationTextTemplateSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "crm.quotation.view",
        "retrieve": "crm.quotation.view",
        "default": "crm.quotation.template_manage",
    }
    filterset_fields = ["company", "section", "is_active"]
