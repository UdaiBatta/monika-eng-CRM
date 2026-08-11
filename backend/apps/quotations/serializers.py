from decimal import Decimal

from rest_framework import serializers

from .models import (
    CustomerCommercialConfirmation,
    Quotation,
    QuotationCommunication,
    QuotationGeneratedDocument,
    QuotationLine,
    QuotationNegotiation,
    QuotationRevision,
    QuotationTemplate,
    QuotationTextTemplate,
)


class QuotationLineInputSerializer(serializers.Serializer):
    item_code = serializers.CharField(max_length=100, required=False, allow_blank=True)
    description = serializers.CharField(max_length=1000)
    quantity = serializers.DecimalField(
        max_digits=18, decimal_places=4, min_value=Decimal("0.0001")
    )
    unit_of_measure = serializers.CharField(max_length=40, default="NOS")
    unit_price = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal("0"))
    discount_percent = serializers.DecimalField(
        max_digits=7, decimal_places=4, min_value=0, max_value=100, default=0
    )
    tax_percent = serializers.DecimalField(
        max_digits=7, decimal_places=4, min_value=0, max_value=100, default=0
    )
    is_optional = serializers.BooleanField(default=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class QuotationLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationLine
        fields = "__all__"
        read_only_fields = [field.name for field in QuotationLine._meta.fields]


class QuotationCommunicationSerializer(serializers.ModelSerializer):
    channel_label = serializers.CharField(source="get_channel_display", read_only=True)

    class Meta:
        model = QuotationCommunication
        fields = "__all__"
        read_only_fields = [field.name for field in QuotationCommunication._meta.fields]


class QuotationNegotiationSerializer(serializers.ModelSerializer):
    channel_label = serializers.CharField(source="get_channel_display", read_only=True)

    class Meta:
        model = QuotationNegotiation
        fields = "__all__"
        read_only_fields = [field.name for field in QuotationNegotiation._meta.fields]


class GeneratedDocumentSerializer(serializers.ModelSerializer):
    docx_title = serializers.CharField(source="docx_document.title", read_only=True)
    pdf_title = serializers.CharField(source="pdf_document.title", read_only=True)

    class Meta:
        model = QuotationGeneratedDocument
        fields = "__all__"
        read_only_fields = [field.name for field in QuotationGeneratedDocument._meta.fields]


class QuotationRevisionSerializer(serializers.ModelSerializer):
    lines = QuotationLineSerializer(many=True, read_only=True)
    communications = QuotationCommunicationSerializer(many=True, read_only=True)
    negotiations = QuotationNegotiationSerializer(many=True, read_only=True)
    generated_documents = GeneratedDocumentSerializer(many=True, read_only=True)
    currency_code = serializers.CharField(source="currency.code", read_only=True)

    class Meta:
        model = QuotationRevision
        fields = "__all__"
        read_only_fields = [field.name for field in QuotationRevision._meta.fields]


class CustomerConfirmationSerializer(serializers.ModelSerializer):
    method_label = serializers.CharField(source="get_method_display", read_only=True)

    class Meta:
        model = CustomerCommercialConfirmation
        fields = "__all__"
        read_only_fields = [field.name for field in CustomerCommercialConfirmation._meta.fields]


class QuotationSerializer(serializers.ModelSerializer):
    current_revision = QuotationRevisionSerializer(read_only=True)
    customer_name = serializers.CharField(source="customer.legal_name", read_only=True)
    customer_code = serializers.CharField(source="customer.customer_code", read_only=True)
    enquiry_number = serializers.CharField(source="enquiry.enquiry_number", read_only=True)
    estimate_number = serializers.CharField(source="estimate.estimate_number", read_only=True)
    owner_name = serializers.CharField(source="owner.display_name", read_only=True)
    commercial_confirmation = CustomerConfirmationSerializer(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    path_label = serializers.CharField(source="get_path_display", read_only=True)

    class Meta:
        model = Quotation
        fields = "__all__"
        read_only_fields = [field.name for field in Quotation._meta.fields]


class QuotationCreateSerializer(serializers.Serializer):
    path = serializers.ChoiceField(choices=Quotation.Path.choices)
    customer_id = serializers.UUIDField()
    customer_contact_id = serializers.UUIDField(required=False, allow_null=True)
    enquiry_id = serializers.UUIDField(required=False, allow_null=True)
    estimate_id = serializers.UUIDField(required=False, allow_null=True)
    owner_id = serializers.UUIDField(required=False, allow_null=True)
    currency_id = serializers.UUIDField(required=False, allow_null=True)
    quick_reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    valid_until = serializers.DateField(required=False, allow_null=True)
    introduction = serializers.CharField(required=False, allow_blank=True)
    scope = serializers.CharField(required=False, allow_blank=True)
    payment_terms = serializers.CharField(required=False, allow_blank=True)
    delivery_terms = serializers.CharField(required=False, allow_blank=True)
    warranty_terms = serializers.CharField(required=False, allow_blank=True)
    lines = QuotationLineInputSerializer(many=True, required=False)


class RevisionUpdateSerializer(serializers.Serializer):
    record_version = serializers.IntegerField(min_value=1)
    issue_date = serializers.DateField(required=False)
    valid_until = serializers.DateField(required=False, allow_null=True)
    introduction = serializers.CharField(required=False, allow_blank=True)
    scope = serializers.CharField(required=False, allow_blank=True)
    inclusions = serializers.CharField(required=False, allow_blank=True)
    exclusions = serializers.CharField(required=False, allow_blank=True)
    assumptions = serializers.CharField(required=False, allow_blank=True)
    payment_terms = serializers.CharField(required=False, allow_blank=True)
    delivery_terms = serializers.CharField(required=False, allow_blank=True)
    warranty_terms = serializers.CharField(required=False, allow_blank=True)
    freight_terms = serializers.CharField(required=False, allow_blank=True)
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    lines = QuotationLineInputSerializer(many=True, required=False)


class FinalizeRevisionSerializer(serializers.Serializer):
    workflow_id = serializers.UUIDField(required=False, allow_null=True)
    comment = serializers.CharField(required=False, allow_blank=True)


class CommunicationInputSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=QuotationCommunication.Channel.choices)
    direction = serializers.ChoiceField(choices=QuotationCommunication.Direction.choices)
    occurred_at = serializers.DateTimeField(required=False)
    contact_id = serializers.UUIDField(required=False, allow_null=True)
    summary = serializers.CharField()
    manual_reference = serializers.CharField(max_length=250, required=False, allow_blank=True)


class NegotiationInputSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=QuotationCommunication.Channel.choices)
    occurred_at = serializers.DateTimeField(required=False)
    summary = serializers.CharField()
    customer_request = serializers.CharField(required=False, allow_blank=True)
    our_response = serializers.CharField(required=False, allow_blank=True)
    commercial_impact = serializers.CharField(required=False, allow_blank=True)
    material_change = serializers.BooleanField(default=False)
    follow_up_at = serializers.DateTimeField(required=False, allow_null=True)
    follow_up_owner_id = serializers.UUIDField(required=False, allow_null=True)


class ConfirmationInputSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=CustomerCommercialConfirmation.Method.choices)
    confirmed_at = serializers.DateTimeField(required=False)
    confirmation_reference = serializers.CharField(max_length=250, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    po_pending = serializers.BooleanField(default=False)
    po_number = serializers.CharField(max_length=120, required=False, allow_blank=True)
    po_date = serializers.DateField(required=False, allow_null=True)
    po_document_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs["method"] == CustomerCommercialConfirmation.Method.PURCHASE_ORDER and not attrs.get(
            "po_number", ""
        ).strip():
            raise serializers.ValidationError("Add the customer's purchase-order number.")
        return attrs


class GenerateDocumentInputSerializer(serializers.Serializer):
    template_id = serializers.UUIDField()


class QuotationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationTemplate
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class QuotationTextTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationTextTemplate
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
