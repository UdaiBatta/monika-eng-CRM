from rest_framework import serializers

from .models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequisition,
    PurchaseRequisitionLine,
)


class PurchaseRequisitionLineSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.internal_code", read_only=True)
    product_description = serializers.CharField(source="product.description", read_only=True)

    class Meta:
        model = PurchaseRequisitionLine
        fields = "__all__"
        read_only_fields = [field.name for field in PurchaseRequisitionLine._meta.fields]


class PurchaseRequisitionLineInputSerializer(serializers.Serializer):
    product = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class PurchaseRequisitionCreateSerializer(serializers.Serializer):
    warehouse = serializers.UUIDField()
    requested_by = serializers.UUIDField()
    preferred_supplier = serializers.UUIDField(required=False, allow_null=True)
    justification = serializers.CharField(required=False, allow_blank=True, default="")
    required_by_date = serializers.DateField(required=False, allow_null=True)
    lines = PurchaseRequisitionLineInputSerializer(many=True)


class PurchaseRequisitionSerializer(serializers.ModelSerializer):
    lines = PurchaseRequisitionLineSerializer(many=True, read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    requested_by_name = serializers.CharField(source="requested_by.display_name", read_only=True)
    preferred_supplier_name = serializers.CharField(
        source="preferred_supplier.name", read_only=True, default=""
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PurchaseRequisition
        fields = "__all__"
        read_only_fields = [field.name for field in PurchaseRequisition._meta.fields]


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.internal_code", read_only=True)
    product_description = serializers.CharField(source="product.description", read_only=True)
    pending_quantity = serializers.DecimalField(max_digits=18, decimal_places=4, read_only=True)

    class Meta:
        model = PurchaseOrderLine
        fields = "__all__"
        read_only_fields = [field.name for field in PurchaseOrderLine._meta.fields]


class PurchaseOrderLineInputSerializer(serializers.Serializer):
    product = serializers.UUIDField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=0)
    unit_price = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=0)
    tax_percent = serializers.DecimalField(max_digits=7, decimal_places=4, required=False, default=0)


class PurchaseOrderCreateSerializer(serializers.Serializer):
    supplier = serializers.UUIDField()
    warehouse = serializers.UUIDField()
    responsible_employee = serializers.UUIDField()
    currency = serializers.UUIDField()
    requisition_id = serializers.UUIDField(required=False, allow_null=True)
    order_date = serializers.DateField(required=False)
    expected_delivery_date = serializers.DateField(required=False, allow_null=True)
    payment_terms = serializers.CharField(required=False, allow_blank=True, default="")
    delivery_terms = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    lines = PurchaseOrderLineInputSerializer(many=True)


class PurchaseOrderSerializer(serializers.ModelSerializer):
    lines = PurchaseOrderLineSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    responsible_name = serializers.CharField(source="responsible_employee.display_name", read_only=True)
    currency_code = serializers.CharField(source="currency.code", read_only=True)
    requisition_number = serializers.CharField(
        source="requisition.requisition_number", read_only=True, default=""
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    payment_status_label = serializers.CharField(source="get_payment_status_display", read_only=True)
    balance_due = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = "__all__"
        read_only_fields = [field.name for field in PurchaseOrder._meta.fields]


class GoodsReceiptLineSerializer(serializers.ModelSerializer):
    order_line_number = serializers.IntegerField(source="order_line.line_number", read_only=True)
    product_code = serializers.CharField(source="order_line.product.internal_code", read_only=True)

    class Meta:
        model = GoodsReceiptLine
        fields = "__all__"
        read_only_fields = [field.name for field in GoodsReceiptLine._meta.fields]


class GoodsReceiptLineInputSerializer(serializers.Serializer):
    order_line = serializers.UUIDField()
    quantity_received = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=0)
    condition = serializers.CharField(required=False, default="AVAILABLE")


class GoodsReceiptCreateSerializer(serializers.Serializer):
    received_by = serializers.UUIDField()
    received_date = serializers.DateField(required=False)
    supplier_reference = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    lines = GoodsReceiptLineInputSerializer(many=True)


class GoodsReceiptConfirmInputSerializer(serializers.Serializer):
    warehouse_location_id = serializers.UUIDField(required=False, allow_null=True)


class GoodsReceiptSerializer(serializers.ModelSerializer):
    lines = GoodsReceiptLineSerializer(many=True, read_only=True)
    purchase_order_number = serializers.CharField(source="purchase_order.po_number", read_only=True)
    received_by_name = serializers.CharField(source="received_by.display_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = "__all__"
        read_only_fields = [field.name for field in GoodsReceipt._meta.fields]


class ReasonInputSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3, max_length=500)


class CommentInputSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class RecordPaymentInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=0)
    payment_status = serializers.ChoiceField(choices=PurchaseOrder.PaymentStatus.choices)
    due_date = serializers.DateField(required=False, allow_null=True)
