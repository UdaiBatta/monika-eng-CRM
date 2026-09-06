from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.concurrency import VersionedUpdateMixin
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin
from apps.core.tabular_imports import TabularImportUploadSerializer

from .imports import import_inventory_records, import_opening_balances
from .models import Product, ProductCategory, StockItem, StockLocation, StockMovement, Supplier
from .serializers import (
    ProductCategorySerializer,
    ProductSerializer,
    RecordMovementSerializer,
    StockItemSerializer,
    StockLocationSerializer,
    StockMovementSerializer,
    SupplierSerializer,
)
from .services import record_movement


class InventoryImportUploadSerializer(TabularImportUploadSerializer):
    pass


def _raise_from_django_validation(exc):
    detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
    raise ValidationError(detail) from exc


class FoundationModelViewSet(VersionedUpdateMixin, ScopedQuerysetMixin, viewsets.ModelViewSet):
    permission_classes = [HasFoundationPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filterset_fields = ["is_active"]
    ordering_fields = ["created_at", "updated_at"]

    @action(detail=False, methods=["post"], url_path="import-history")
    def import_history(self, request):
        upload_serializer = InventoryImportUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        created = import_inventory_records(self, upload_serializer.validated_data["file"])
        return Response({"imported": len(created)}, status=status.HTTP_201_CREATED)


class ProductCategoryViewSet(FoundationModelViewSet):
    queryset = ProductCategory.objects.select_related("company")
    serializer_class = ProductCategorySerializer
    search_fields = ["name", "code"]
    filterset_fields = ["is_active", "company"]
    permission_map = {
        "list": "inventory.product.view",
        "retrieve": "inventory.product.view",
        "default": "inventory.product.manage",
    }


class SupplierViewSet(FoundationModelViewSet):
    queryset = Supplier.objects.select_related("company", "payment_term")
    serializer_class = SupplierSerializer
    search_fields = ["name", "code", "gstin", "phone", "email"]
    filterset_fields = ["is_active", "company"]
    permission_map = {
        "list": "inventory.supplier.view",
        "retrieve": "inventory.supplier.view",
        "default": "inventory.supplier.manage",
    }


class ProductViewSet(FoundationModelViewSet):
    queryset = Product.objects.select_related("company", "category", "default_supplier", "unit_of_measure")
    serializer_class = ProductSerializer
    search_fields = ["internal_code", "brand", "part_number", "description"]
    filterset_fields = ["is_active", "company", "category", "default_supplier"]
    ordering_fields = ["internal_code", "description", "created_at", "updated_at"]
    permission_map = {
        "list": "inventory.product.view",
        "retrieve": "inventory.product.view",
        "default": "inventory.product.manage",
    }

    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        queryset = self.filter_queryset(self.get_queryset()).filter(is_active=True, reorder_level__gt=0)
        rows = []
        for product in queryset:
            available = (
                product.stock_items.filter(condition=StockItem.Condition.AVAILABLE).aggregate(
                    total=Sum("quantity")
                )["total"]
                or 0
            )
            if available <= product.reorder_level:
                rows.append(
                    {
                        "product_id": str(product.pk),
                        "internal_code": product.internal_code,
                        "description": product.description,
                        "available_quantity": str(available),
                        "reorder_level": str(product.reorder_level),
                        "reorder_quantity": str(product.reorder_quantity),
                    }
                )
        return Response(rows)


class StockLocationViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = StockLocation.objects.select_related("warehouse", "warehouse__company")
    serializer_class = StockLocationSerializer
    permission_classes = [HasFoundationPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filterset_fields = ["warehouse"]
    permission_map = {
        "list": "inventory.stock.view",
        "retrieve": "inventory.stock.view",
        "default": "inventory.stock.manage",
    }


class StockItemViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = StockItem.objects.select_related(
        "product", "location", "location__warehouse", "location__warehouse__company"
    )
    serializer_class = StockItemSerializer
    permission_classes = [HasFoundationPermission]
    filterset_fields = ["product", "location", "condition", "location__warehouse"]
    search_fields = ["product__internal_code", "product__description"]
    permission_map = {"list": "inventory.stock.view", "retrieve": "inventory.stock.view"}


class StockMovementViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related(
        "product", "from_location", "to_location", "created_by", "company"
    )
    serializer_class = StockMovementSerializer
    permission_classes = [HasFoundationPermission]
    filterset_fields = ["product", "movement_type", "company", "reference_type", "reference_id"]
    search_fields = ["movement_number", "product__internal_code"]
    ordering_fields = ["created_at"]
    permission_map = {
        "list": "inventory.stock.view",
        "retrieve": "inventory.stock.view",
        "record": "inventory.stock.manage",
        "import_opening_balances_action": "inventory.stock.manage",
    }

    @action(detail=False, methods=["post"], url_path="record")
    def record(self, request):
        serializer = RecordMovementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        product = data["product"]
        try:
            movement = record_movement(
                company=product.company,
                movement_type=data["movement_type"],
                product=product,
                quantity=data["quantity"],
                from_location=data.get("from_location"),
                from_condition=data.get("from_condition", ""),
                to_location=data.get("to_location"),
                to_condition=data.get("to_condition", ""),
                reason=data.get("reason", ""),
                reference_type=data.get("reference_type", ""),
                reference_id=data.get("reference_id"),
                actor=request.user,
            )
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="import-opening-balances")
    def import_opening_balances_action(self, request):
        upload_serializer = InventoryImportUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        try:
            created = import_opening_balances(upload_serializer.validated_data["file"], actor=request.user)
        except DjangoValidationError as exc:
            _raise_from_django_validation(exc)
        return Response({"imported": len(created)}, status=status.HTTP_201_CREATED)
