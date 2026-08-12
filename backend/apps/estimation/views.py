from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.approvals.serializers import ApprovalRequestSerializer
from apps.audit.serializers import AuditEventSerializer
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin
from apps.documents.serializers import DocumentSerializer
from apps.enquiries.serializers import EnquirySerializer

from .models import CommercialEstimate, EstimateCostLine
from .selectors import estimate_workspace_data
from .serializers import (
    CommercialEstimateSerializer,
    CostLineCreateSerializer,
    CostLineWriteSerializer,
    EstimateCostLineSerializer,
    EstimateCreateSerializer,
    EstimateDetailsSerializer,
    EstimateReviseSerializer,
    EstimateSubmitSerializer,
)
from .services import (
    create_cost_line,
    create_estimate,
    delete_cost_line,
    revise_estimate,
    submit_estimate,
    update_cost_line,
    update_estimate,
)


class CommercialEstimateViewSet(
    ScopedQuerysetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = CommercialEstimate.objects.select_related(
        "company",
        "enquiry",
        "enquiry__customer",
        "enquiry__responsible_salesperson",
        "engineering_review",
        "currency",
        "prepared_by",
        "submitted_by",
        "approved_by",
        "approval_request",
        "supersedes",
    ).prefetch_related("cost_lines")
    serializer_class = CommercialEstimateSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "estimation.estimate.view",
        "retrieve": "estimation.estimate.view",
        "workspace": "estimation.estimate.view",
        "revisions": "estimation.estimate.view",
        "create": "estimation.estimate.create",
        "details": "estimation.estimate.edit",
        "submit": "estimation.estimate.submit",
        "revise": "estimation.estimate.revise",
        "default": "estimation.estimate.view",
    }
    search_fields = [
        "estimate_number",
        "enquiry__enquiry_number",
        "enquiry__subject",
        "enquiry__customer__legal_name",
        "enquiry__customer__customer_code",
    ]
    filterset_fields = ["company", "enquiry", "status", "currency", "prepared_by", "is_current"]
    ordering_fields = ["created_at", "updated_at", "estimate_number", "total_cost", "proposed_selling_price"]

    def create(self, request):
        serializer = EstimateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        estimate = create_estimate(actor=request.user, **serializer.validated_data)
        return Response(self.get_serializer(estimate).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"])
    def details(self, request, pk=None):
        serializer = EstimateDetailsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        estimate = update_estimate(
            estimate_id=self.get_object().pk, actor=request.user, data=serializer.validated_data
        )
        return Response(self.get_serializer(estimate).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        serializer = EstimateSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        estimate = submit_estimate(
            estimate_id=self.get_object().pk, actor=request.user, **serializer.validated_data
        )
        return Response(self.get_serializer(estimate).data)

    @action(detail=True, methods=["post"])
    def revise(self, request, pk=None):
        serializer = EstimateReviseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        estimate = revise_estimate(
            estimate_id=self.get_object().pk, actor=request.user, **serializer.validated_data
        )
        return Response(self.get_serializer(estimate).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        estimate = self.get_object()
        revisions = self.get_queryset().filter(enquiry=estimate.enquiry).order_by("-revision_number")
        return Response(self.get_serializer(revisions, many=True).data)

    @action(detail=True, methods=["get"])
    def workspace(self, request, pk=None):
        estimate = self.get_object()
        data = estimate_workspace_data(estimate, request.user)
        return Response(
            {
                "estimate": self.get_serializer(estimate).data,
                "enquiry": EnquirySerializer(estimate.enquiry, context={"request": request}).data,
                "documents": DocumentSerializer(
                    data["documents"], many=True, context={"request": request}
                ).data,
                "approvals": ApprovalRequestSerializer(data["approvals"], many=True).data,
                "timeline": AuditEventSerializer(data["audit_events"], many=True).data,
            }
        )


class EstimateCostLineViewSet(
    ScopedQuerysetMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = EstimateCostLine.objects.select_related(
        "estimate", "estimate__company", "estimate__currency", "estimate__enquiry"
    )
    serializer_class = EstimateCostLineSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "create": "estimation.estimate.edit",
        "partial_update": "estimation.estimate.edit",
        "update": "estimation.estimate.edit",
        "destroy": "estimation.estimate.edit",
        "default": "estimation.estimate.edit",
    }
    company_path = "estimate__company"

    def create(self, request):
        serializer = CostLineCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        estimate_id = serializer.validated_data.pop("estimate_id")
        line = create_cost_line(estimate_id=estimate_id, actor=request.user, data=serializer.validated_data)
        return Response(self.get_serializer(line).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        serializer = CostLineWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        line = update_cost_line(
            line_id=self.get_object().pk, actor=request.user, data=serializer.validated_data
        )
        return Response(self.get_serializer(line).data)

    def update(self, request, pk=None):
        return self.partial_update(request, pk)

    def destroy(self, request, pk=None):
        delete_cost_line(line_id=self.get_object().pk, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
