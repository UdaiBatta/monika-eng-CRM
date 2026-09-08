from decimal import Decimal

from rest_framework import serializers

from apps.rbac.services import has_permission

from .models import (
    CustomerPurchaseOrder,
    CustomerPurchaseOrderRevision,
    SalesOrder,
    SalesOrderLine,
    SalesOrderRevision,
)


class CustomerPORevisionSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source="currency.code", read_only=True)
    match_status_label = serializers.CharField(source="get_match_status_display", read_only=True)
    document_title = serializers.CharField(source="supporting_document.title", read_only=True)

    class Meta:
        model = CustomerPurchaseOrderRevision
        fields = "__all__"
        read_only_fields = [field.name for field in CustomerPurchaseOrderRevision._meta.fields]


class CustomerPOSerializer(serializers.ModelSerializer):
    current_revision = CustomerPORevisionSerializer(read_only=True)
    revisions = CustomerPORevisionSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.legal_name", read_only=True)
    quotation_number = serializers.CharField(source="quotation.quotation_number", read_only=True)
    responsible_name = serializers.CharField(source="responsible_employee.display_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = CustomerPurchaseOrder
        fields = "__all__"
        read_only_fields = [field.name for field in CustomerPurchaseOrder._meta.fields]


class CustomerPOCreateSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    po_number = serializers.CharField(max_length=120)
    po_date = serializers.DateField()
    received_date = serializers.DateField(required=False)
    quotation_id = serializers.UUIDField(required=False, allow_null=True)
    responsible_employee_id = serializers.UUIDField(required=False, allow_null=True)
    currency_id = serializers.UUIDField(required=False, allow_null=True)
    stated_total = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True
    )
    supporting_document_id = serializers.UUIDField(required=False, allow_null=True)
    customer_revision_reference = serializers.CharField(max_length=120, required=False, allow_blank=True)
    tax_information = serializers.JSONField(required=False)
    line_snapshot = serializers.ListField(child=serializers.DictField(), required=False)
    delivery_information = serializers.CharField(required=False, allow_blank=True)
    payment_terms = serializers.CharField(required=False, allow_blank=True)
    warranty_terms = serializers.CharField(required=False, allow_blank=True)
    customer_reference = serializers.CharField(max_length=250, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class CustomerPORevisionInputSerializer(serializers.Serializer):
    customer_revision_reference = serializers.CharField(max_length=120, required=False, allow_blank=True)
    po_date = serializers.DateField(required=False)
    received_date = serializers.DateField(required=False)
    currency_id = serializers.UUIDField(required=False)
    stated_total = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True
    )
    supporting_document_id = serializers.UUIDField(required=False, allow_null=True)
    tax_information = serializers.JSONField(required=False)
    line_snapshot = serializers.ListField(child=serializers.DictField(), required=False)
    delivery_information = serializers.CharField(required=False, allow_blank=True)
    payment_terms = serializers.CharField(required=False, allow_blank=True)
    warranty_terms = serializers.CharField(required=False, allow_blank=True)
    customer_reference = serializers.CharField(max_length=250, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class SalesOrderLineInputSerializer(serializers.Serializer):
    quotation_line_id = serializers.UUIDField(required=False, allow_null=True)
    customer_po_line_reference = serializers.CharField(max_length=120, required=False, allow_blank=True)
    description = serializers.CharField(max_length=1000)
    long_description = serializers.CharField(required=False, allow_blank=True)
    customer_item_reference = serializers.CharField(max_length=120, required=False, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal("0.0001"))
    unit_of_measure = serializers.CharField(max_length=40, default="NOS")
    unit_price = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal("0"))
    discount_percent = serializers.DecimalField(
        max_digits=7, decimal_places=4, min_value=0, max_value=100, default=0
    )
    tax_percent = serializers.DecimalField(
        max_digits=7, decimal_places=4, min_value=0, max_value=100, default=0
    )
    requested_delivery_date = serializers.DateField(required=False, allow_null=True)
    promised_delivery_date = serializers.DateField(required=False, allow_null=True)
    delivery_text = serializers.CharField(max_length=250, required=False, allow_blank=True)
    customer_visible_note = serializers.CharField(required=False, allow_blank=True)
    internal_note = serializers.CharField(required=False, allow_blank=True)
    project_scope_category = serializers.CharField(max_length=120, required=False, allow_blank=True)


class SalesOrderLineSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.internal_code", read_only=True, default="")

    class Meta:
        model = SalesOrderLine
        fields = "__all__"
        read_only_fields = [field.name for field in SalesOrderLine._meta.fields]


class SalesOrderRevisionSerializer(serializers.ModelSerializer):
    lines = SalesOrderLineSerializer(many=True, read_only=True)
    currency_code = serializers.CharField(source="currency.code", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SalesOrderRevision
        fields = "__all__"
        read_only_fields = [field.name for field in SalesOrderRevision._meta.fields]

    def to_representation(self, instance):
        result = super().to_representation(instance)
        request = self.context.get("request")
        if not request or not has_permission(
            request.user, "sales.sales_order.view_internal_notes", instance.sales_order
        ):
            result.pop("internal_notes", None)
            for line in result.get("lines", []):
                line.pop("internal_note", None)
        return result


class SalesOrderSerializer(serializers.ModelSerializer):
    current_revision = SalesOrderRevisionSerializer(read_only=True)
    revisions = SalesOrderRevisionSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.legal_name", read_only=True)
    contact_name = serializers.CharField(source="contact.display_name", read_only=True)
    site_name = serializers.CharField(source="site.label", read_only=True)
    quotation_number = serializers.CharField(source="accepted_quotation.quotation_number", read_only=True)
    customer_po_number = serializers.CharField(source="customer_purchase_order.po_number", read_only=True)
    responsible_name = serializers.CharField(source="responsible_sales_employee.display_name", read_only=True)
    project_id = serializers.SerializerMethodField()
    project_number = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    order_mode_label = serializers.CharField(source="get_order_mode_display", read_only=True)

    class Meta:
        model = SalesOrder
        fields = "__all__"
        read_only_fields = [field.name for field in SalesOrder._meta.fields]

    @staticmethod
    def get_project_id(instance):
        project = getattr(instance, "project", None)
        return str(project.pk) if project else None

    @staticmethod
    def get_project_number(instance):
        project = getattr(instance, "project", None)
        return project.project_number if project else ""


class FromQuotationInputSerializer(serializers.Serializer):
    quotation_id = serializers.UUIDField()
    site_id = serializers.UUIDField(required=False, allow_null=True)
    responsible_sales_employee_id = serializers.UUIDField(required=False, allow_null=True)
    project_required = serializers.BooleanField(default=True)
    requested_delivery = serializers.DateField(required=False, allow_null=True)
    promised_delivery = serializers.DateField(required=False, allow_null=True)
    internal_notes = serializers.CharField(required=False, allow_blank=True)


class DirectSalesOrderInputSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    contact_id = serializers.UUIDField(required=False, allow_null=True)
    site_id = serializers.UUIDField(required=False, allow_null=True)
    enquiry_id = serializers.UUIDField(required=False, allow_null=True)
    currency_id = serializers.UUIDField()
    subject = serializers.CharField(max_length=250, required=False, allow_blank=True)
    requirement = serializers.CharField(required=False, allow_blank=True)
    confirmation_channel = serializers.CharField(max_length=40)
    confirmation_reference = serializers.CharField(max_length=250, required=False, allow_blank=True)
    confirmation_date = serializers.DateField(required=False)
    direct_reason = serializers.ChoiceField(
        choices=[
            "REPEAT_ORDER",
            "EXISTING_RATE",
            "SPARE_REPLACEMENT",
            "EMERGENCY_REQUIREMENT",
            "MANAGEMENT_INSTRUCTION",
            "CUSTOMER_REQUESTED_DIRECT",
            "OTHER",
        ]
    )
    direct_reason_notes = serializers.CharField(required=False, allow_blank=True)
    po_pending = serializers.BooleanField(default=True)
    project_required = serializers.BooleanField(default=True)
    requested_delivery = serializers.DateField(required=False, allow_null=True)
    promised_delivery = serializers.DateField(required=False, allow_null=True)
    payment_terms = serializers.CharField(required=False, allow_blank=True)
    delivery_terms = serializers.CharField(required=False, allow_blank=True)
    warranty_terms = serializers.CharField(required=False, allow_blank=True)
    freight_terms = serializers.CharField(required=False, allow_blank=True)
    installation_terms = serializers.CharField(required=False, allow_blank=True)
    scope = serializers.CharField(required=False, allow_blank=True)
    exclusions = serializers.CharField(required=False, allow_blank=True)
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    internal_notes = serializers.CharField(required=False, allow_blank=True)
    lines = SalesOrderLineInputSerializer(many=True, min_length=1)


class SalesOrderDraftInputSerializer(serializers.Serializer):
    record_version = serializers.IntegerField(min_value=1)
    currency_id = serializers.UUIDField(required=False)
    customer_reference = serializers.CharField(max_length=250, required=False, allow_blank=True)
    order_date = serializers.DateField(required=False)
    requested_delivery = serializers.DateField(required=False, allow_null=True)
    promised_delivery = serializers.DateField(required=False, allow_null=True)
    payment_terms = serializers.CharField(required=False, allow_blank=True)
    delivery_terms = serializers.CharField(required=False, allow_blank=True)
    warranty_terms = serializers.CharField(required=False, allow_blank=True)
    freight_terms = serializers.CharField(required=False, allow_blank=True)
    installation_terms = serializers.CharField(required=False, allow_blank=True)
    scope = serializers.CharField(required=False, allow_blank=True)
    exclusions = serializers.CharField(required=False, allow_blank=True)
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    internal_notes = serializers.CharField(required=False, allow_blank=True)
    lines = SalesOrderLineInputSerializer(many=True, min_length=1, required=False)


class CommentInputSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True)


class ReasonInputSerializer(serializers.Serializer):
    reason = serializers.CharField()


class LinkCustomerPOInputSerializer(serializers.Serializer):
    customer_po_id = serializers.UUIDField()
