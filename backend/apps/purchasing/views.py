from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin
from apps.inventory.models import Product, Supplier
from apps.masters.models import Currency
from apps.organization.models import Employee, Warehouse

from .models import GoodsReceipt, PurchaseOrder, PurchaseRequisition
from .serializers import (
    CommentInputSerializer,
    GoodsReceiptConfirmInputSerializer,
    GoodsReceiptCreateSerializer,
    GoodsReceiptSerializer,
    PurchaseOrderCreateSerializer,
    PurchaseOrderSerializer,
    PurchaseRequisitionCreateSerializer,
    PurchaseRequisitionSerializer,
    ReasonInputSerializer,
    RecordPaymentInputSerializer,
)
from .services import (
    cancel_purchase_order,
    confirm_goods_receipt,
    create_goods_receipt,
    create_purchase_order,
    create_purchase_requisition,
    record_purchase_order_payment,
    submit_purchase_order,
    submit_purchase_requisition,
)


def _raise_from_django_validation(exc):
    detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
    raise ValidationError(detail) from exc


def _actor_company(user):
    employee = Employee.objects.filter(user=user, user__is_active=True).select_related("company").first()
    if not employee:
        raise ValidationError("Your account is not linked to an active employee.")
    return employee.company


class PurchaseRequisitionViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = PurchaseRequisition.objects.select_related(
        "company", "warehouse", "requested_by", "preferred_supplier"
    ).prefetch_related("lines")
    serializer_class = PurchaseRequisitionSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "purchasing.requisition.view",
        "retrieve": "purchasing.requisition.view",
        "create": "purchasing.requisition.create",
        "submit": "purchasing.requisition.submit",
        "default": "purchasing.requisition.view",
    }
    search_fields = ["requisition_number"]
    filterset_fields = ["company", "status", "warehouse", "requested_by"]
    ordering_fields = ["created_at", "updated_at", "requisition_number"]

    def create(self, request, *args, **kwargs):
        serializer = PurchaseRequisitionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = dict(serializer.validated_data)
        lines = validated.pop("lines")
        company = _actor_company(request.user)
        data = {
            "warehouse": Warehouse.objects.get(pk=validated.pop("warehouse")),
            "requested_by": Employee.objects.get(pk=validated.pop("requested_by")),
            "preferred_supplier": (
                Supplier.objects.get(pk=validated["preferred_supplier"])
                if validated.get("preferred_supplier")
                else None
            ),
            "justification": validated.get("justification", ""),
            "required_by_date": validated.get("required_by_date"),
        }
        resolved_lines = [
            {
                "product": Product.objects.get(pk=line["product"]),
                "quantity": line["quantity"],
                "notes": line.get("notes", ""),
            }
            for line in lines
        ]
        try:
            requisition = create_purchase_requisition(
                company=company, actor=request.user, data=data, lines=resolved_lines
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(
            PurchaseRequisitionSerializer(requisition).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        serializer = CommentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            requisition = submit_purchase_requisition(
                requisition_id=self.get_object().pk,
                actor=request.user,
                comment=serializer.validated_data.get("comment", ""),
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(PurchaseRequisitionSerializer(requisition).data)


class PurchaseOrderViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = PurchaseOrder.objects.select_related(
        "company", "supplier", "warehouse", "requisition", "responsible_employee", "currency"
    ).prefetch_related("lines")
    serializer_class = PurchaseOrderSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "purchasing.purchase_order.view",
        "retrieve": "purchasing.purchase_order.view",
        "create": "purchasing.purchase_order.create",
        "submit": "purchasing.purchase_order.submit",
        "cancel": "purchasing.purchase_order.cancel",
        "record_payment": "purchasing.purchase_order.record_payment",
        "default": "purchasing.purchase_order.view",
    }
    search_fields = ["po_number", "supplier__name"]
    filterset_fields = ["company", "status", "payment_status", "supplier", "warehouse"]
    ordering_fields = ["created_at", "updated_at", "po_number", "status"]

    def create(self, request, *args, **kwargs):
        serializer = PurchaseOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = dict(serializer.validated_data)
        lines = validated.pop("lines")
        company = _actor_company(request.user)
        requisition_id = validated.pop("requisition_id", None)
        data = {
            "supplier": Supplier.objects.get(pk=validated.pop("supplier")),
            "warehouse": Warehouse.objects.get(pk=validated.pop("warehouse")),
            "responsible_employee": Employee.objects.get(pk=validated.pop("responsible_employee")),
            "currency": Currency.objects.get(pk=validated.pop("currency")),
            "order_date": validated.get("order_date") or timezone.localdate(),
            "expected_delivery_date": validated.get("expected_delivery_date"),
            "payment_terms": validated.get("payment_terms", ""),
            "delivery_terms": validated.get("delivery_terms", ""),
            "notes": validated.get("notes", ""),
        }
        resolved_lines = [
            {
                "product": Product.objects.get(pk=line["product"]),
                "description": line.get("description", ""),
                "quantity": line["quantity"],
                "unit_price": line["unit_price"],
                "tax_percent": line.get("tax_percent", 0),
            }
            for line in lines
        ]
        try:
            order = create_purchase_order(
                company=company,
                actor=request.user,
                data=data,
                lines=resolved_lines,
                requisition_id=requisition_id,
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(PurchaseOrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        serializer = CommentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = submit_purchase_order(
                order_id=self.get_object().pk,
                actor=request.user,
                comment=serializer.validated_data.get("comment", ""),
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(PurchaseOrderSerializer(order).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        serializer = ReasonInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = cancel_purchase_order(
                order_id=self.get_object().pk,
                actor=request.user,
                reason=serializer.validated_data["reason"],
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(PurchaseOrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="record-payment")
    def record_payment(self, request, pk=None):
        serializer = RecordPaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = record_purchase_order_payment(
                order_id=self.get_object().pk, actor=request.user, **serializer.validated_data
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(PurchaseOrderSerializer(order).data)


class GoodsReceiptViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = GoodsReceipt.objects.select_related(
        "company", "purchase_order", "received_by"
    ).prefetch_related("lines")
    serializer_class = GoodsReceiptSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "purchasing.goods_receipt.view",
        "retrieve": "purchasing.goods_receipt.view",
        "create": "purchasing.goods_receipt.create",
        "confirm": "purchasing.goods_receipt.confirm",
        "default": "purchasing.goods_receipt.view",
    }
    filterset_fields = ["company", "status", "purchase_order"]
    ordering_fields = ["created_at", "updated_at"]

    def create(self, request, *args, **kwargs):
        purchase_order_id = request.data.get("purchase_order")
        if not purchase_order_id:
            raise ValidationError({"purchase_order": ["This field is required."]})
        serializer = GoodsReceiptCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = dict(serializer.validated_data)
        lines = validated.pop("lines")
        order = PurchaseOrder.objects.get(pk=purchase_order_id)
        data = {
            "received_by": Employee.objects.get(pk=validated.pop("received_by")),
            "received_date": validated.get("received_date") or timezone.localdate(),
            "supplier_reference": validated.get("supplier_reference", ""),
            "notes": validated.get("notes", ""),
        }
        try:
            receipt = create_goods_receipt(
                company=order.company,
                actor=request.user,
                purchase_order_id=purchase_order_id,
                data=data,
                lines=lines,
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(GoodsReceiptSerializer(receipt).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        serializer = GoodsReceiptConfirmInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            receipt = confirm_goods_receipt(
                receipt_id=self.get_object().pk,
                actor=request.user,
                warehouse_location_id=serializer.validated_data.get("warehouse_location_id"),
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(GoodsReceiptSerializer(receipt).data)
