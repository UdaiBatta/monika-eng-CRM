from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin

from .models import CustomerPurchaseOrder, SalesOrder, SalesOrderRevision
from .serializers import (
    CommentInputSerializer,
    CustomerPOCreateSerializer,
    CustomerPORevisionInputSerializer,
    CustomerPORevisionSerializer,
    CustomerPOSerializer,
    DirectSalesOrderInputSerializer,
    FromQuotationInputSerializer,
    LinkCustomerPOInputSerializer,
    ReasonInputSerializer,
    SalesOrderDraftInputSerializer,
    SalesOrderRevisionSerializer,
    SalesOrderSerializer,
)
from .services import (
    accept_po_variance,
    cancel_sales_order,
    compare_sales_order_revisions,
    create_customer_po_revision,
    create_direct_sales_order,
    create_sales_order_amendment,
    create_sales_order_from_quotation,
    hold_sales_order,
    link_customer_po,
    record_customer_po,
    release_sales_order,
    resume_sales_order,
    review_po_variance,
    submit_sales_order,
    update_sales_order_draft,
)


class CustomerPurchaseOrderViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = CustomerPurchaseOrder.objects.select_related(
        "company",
        "customer",
        "quotation",
        "confirmation",
        "responsible_employee",
        "current_revision__currency",
        "current_revision__supporting_document",
    ).prefetch_related("revisions__currency", "revisions__supporting_document")
    serializer_class = CustomerPOSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "sales.customer_po.view",
        "retrieve": "sales.customer_po.view",
        "create": "sales.customer_po.create",
        "create_revision": "sales.customer_po.revise",
        "review_variance": "sales.customer_po.review_variance",
        "accept_variance": "sales.customer_po.accept_variance",
        "default": "sales.customer_po.view",
    }
    search_fields = ["po_number", "customer__legal_name", "quotation__quotation_number"]
    filterset_fields = ["company", "customer", "quotation", "status", "responsible_employee"]
    ordering_fields = ["created_at", "updated_at", "po_number", "status"]

    def create(self, request, *args, **kwargs):
        serializer = CustomerPOCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        po = record_customer_po(actor=request.user, data=serializer.validated_data)
        return Response(
            CustomerPOSerializer(po, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="create-revision")
    def create_revision(self, request, pk=None):
        serializer = CustomerPORevisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        revision = create_customer_po_revision(
            po_id=self.get_object().pk, actor=request.user, data=serializer.validated_data
        )
        return Response(CustomerPORevisionSerializer(revision).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="review-variance")
    def review_variance(self, request, pk=None):
        revision = review_po_variance(po_id=self.get_object().pk, actor=request.user)
        return Response(CustomerPORevisionSerializer(revision).data)

    @action(detail=True, methods=["post"], url_path="accept-variance")
    def accept_variance(self, request, pk=None):
        serializer = ReasonInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        revision = accept_po_variance(
            po_id=self.get_object().pk,
            actor=request.user,
            reason=serializer.validated_data["reason"],
        )
        return Response(CustomerPORevisionSerializer(revision).data)


class SalesOrderViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = SalesOrder.objects.select_related(
        "company",
        "customer",
        "contact",
        "site",
        "enquiry",
        "accepted_quotation",
        "customer_confirmation",
        "customer_purchase_order__current_revision",
        "responsible_sales_employee",
        "current_revision__currency",
        "project",
    ).prefetch_related("current_revision__lines", "revisions__currency", "revisions__lines")
    serializer_class = SalesOrderSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "sales.sales_order.view",
        "retrieve": "sales.sales_order.view",
        "from_quotation": "sales.sales_order.create",
        "direct": "sales.sales_order.direct_create",
        "update_draft": "sales.sales_order.edit",
        "submit": "sales.sales_order.submit",
        "release": "sales.sales_order.release",
        "create_amendment": "sales.sales_order.revise",
        "compare": "sales.sales_order.view",
        "link_customer_po": "sales.customer_po.link_to_order",
        "create_project": "projects.project.create",
        "hold": "sales.sales_order.hold",
        "resume": "sales.sales_order.resume",
        "cancel": "sales.sales_order.cancel",
        "default": "sales.sales_order.view",
    }
    search_fields = [
        "sales_order_number",
        "customer__legal_name",
        "accepted_quotation__quotation_number",
        "customer_purchase_order__po_number",
    ]
    filterset_fields = [
        "company",
        "customer",
        "accepted_quotation",
        "customer_purchase_order",
        "status",
        "order_mode",
        "responsible_sales_employee",
        "project_required",
        "po_pending",
    ]
    ordering_fields = ["created_at", "updated_at", "sales_order_number", "status"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("queue") == "mine":
            employee = getattr(self.request.user, "employee", None)
            return queryset.filter(responsible_sales_employee=employee) if employee else queryset.none()
        return queryset

    @action(detail=False, methods=["post"], url_path="from-quotation")
    def from_quotation(self, request):
        serializer = FromQuotationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        quotation_id = data.pop("quotation_id")
        order = create_sales_order_from_quotation(quotation_id=quotation_id, actor=request.user, data=data)
        return Response(
            SalesOrderSerializer(order, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def direct(self, request):
        serializer = DirectSalesOrderInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = create_direct_sales_order(actor=request.user, data=serializer.validated_data)
        return Response(
            SalesOrderSerializer(order, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="update-draft")
    def update_draft(self, request, pk=None):
        serializer = SalesOrderDraftInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        record_version = data.pop("record_version")
        revision = update_sales_order_draft(
            revision_id=self.get_object().current_revision_id,
            actor=request.user,
            submitted_version=record_version,
            data=data,
        )
        return Response(SalesOrderRevisionSerializer(revision, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        serializer = CommentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = submit_sales_order(
            order_id=self.get_object().pk,
            actor=request.user,
            comment=serializer.validated_data.get("comment", ""),
        )
        return Response(SalesOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        order = release_sales_order(order_id=self.get_object().pk, actor=request.user)
        return Response(SalesOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="create-amendment")
    def create_amendment(self, request, pk=None):
        serializer = ReasonInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        revision = create_sales_order_amendment(
            order_id=self.get_object().pk,
            actor=request.user,
            reason=serializer.validated_data["reason"],
        )
        return Response(
            SalesOrderRevisionSerializer(revision, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def compare(self, request, pk=None):
        return Response(compare_sales_order_revisions(self.get_object()))

    @action(detail=True, methods=["post"], url_path="link-customer-po")
    def link_customer_po(self, request, pk=None):
        serializer = LinkCustomerPOInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = link_customer_po(
            order_id=self.get_object().pk,
            po_id=serializer.validated_data["customer_po_id"],
            actor=request.user,
        )
        return Response(SalesOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="create-project")
    def create_project(self, request, pk=None):
        from apps.projects.serializers import ProjectCreateInputSerializer, ProjectSerializer
        from apps.projects.services import create_project_from_sales_order

        serializer = ProjectCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = create_project_from_sales_order(
            order_id=self.get_object().pk,
            actor=request.user,
            data=serializer.validated_data,
        )
        return Response(ProjectSerializer(project, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def hold(self, request, pk=None):
        serializer = ReasonInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = hold_sales_order(
            order_id=self.get_object().pk,
            actor=request.user,
            reason=serializer.validated_data["reason"],
        )
        return Response(SalesOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        order = resume_sales_order(order_id=self.get_object().pk, actor=request.user)
        return Response(SalesOrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        serializer = ReasonInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = cancel_sales_order(
            order_id=self.get_object().pk,
            actor=request.user,
            reason=serializer.validated_data["reason"],
        )
        return Response(SalesOrderSerializer(order, context={"request": request}).data)


class SalesOrderRevisionViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = SalesOrderRevision.objects.select_related(
        "sales_order__company", "sales_order__customer", "currency", "approval_request"
    ).prefetch_related("lines")
    serializer_class = SalesOrderRevisionSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {"default": "sales.sales_order.view"}
    filterset_fields = ["sales_order", "status"]
