from decimal import Decimal

from rest_framework import serializers

from apps.rbac.services import has_permission

from .models import CommercialEstimate, EstimateCostLine


class EstimateCostLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstimateCostLine
        fields = "__all__"
        read_only_fields = [field.name for field in EstimateCostLine._meta.fields]


class CommercialEstimateSerializer(serializers.ModelSerializer):
    enquiry_number = serializers.CharField(source="enquiry.enquiry_number", read_only=True)
    enquiry_subject = serializers.CharField(source="enquiry.subject", read_only=True)
    customer_id = serializers.UUIDField(source="enquiry.customer_id", read_only=True)
    customer_code = serializers.CharField(source="enquiry.customer.customer_code", read_only=True)
    customer_name = serializers.CharField(source="enquiry.customer.legal_name", read_only=True)
    sales_owner_name = serializers.CharField(
        source="enquiry.responsible_salesperson.display_name", read_only=True
    )
    engineering_review_revision = serializers.IntegerField(
        source="engineering_review.revision_number", read_only=True
    )
    currency_code = serializers.CharField(source="currency.code", read_only=True)
    currency_symbol = serializers.CharField(source="currency.symbol", read_only=True)
    prepared_by_name = serializers.SerializerMethodField()
    submitted_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    approval_status = serializers.CharField(source="approval_request.status", read_only=True)
    cost_lines = EstimateCostLineSerializer(many=True, read_only=True)

    class Meta:
        model = CommercialEstimate
        fields = "__all__"
        read_only_fields = [field.name for field in CommercialEstimate._meta.fields]

    def _name(self, user):
        if not user:
            return ""
        employee = getattr(user, "employee", None)
        return employee.display_name if employee else user.email

    def get_prepared_by_name(self, obj):
        return self._name(obj.prepared_by)

    def get_submitted_by_name(self, obj):
        return self._name(obj.submitted_by)

    def get_approved_by_name(self, obj):
        return self._name(obj.approved_by)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request and not has_permission(request.user, "estimation.estimate.view_cost", instance):
            for field in ("cost_lines", "category_totals", "total_cost"):
                data.pop(field, None)
        if request and not has_permission(request.user, "estimation.estimate.view_margin", instance):
            for field in (
                "pricing_method",
                "markup_percent",
                "target_margin_percent",
                "manual_selling_price",
                "proposed_selling_price",
                "gross_margin_amount",
                "gross_margin_percent",
            ):
                data.pop(field, None)
        return data


class EstimateCreateSerializer(serializers.Serializer):
    enquiry_id = serializers.UUIDField()
    currency_id = serializers.UUIDField(required=False)


class EstimateDetailsSerializer(serializers.Serializer):
    pricing_method = serializers.ChoiceField(choices=CommercialEstimate.PricingMethod.choices, required=False)
    markup_percent = serializers.DecimalField(max_digits=7, decimal_places=4, min_value=0, required=False)
    target_margin_percent = serializers.DecimalField(
        max_digits=7,
        decimal_places=4,
        min_value=Decimal("0"),
        max_value=Decimal("99.9999"),
        required=False,
    )
    manual_selling_price = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    assumptions = serializers.CharField(required=False, allow_blank=True)
    exclusions = serializers.CharField(required=False, allow_blank=True)
    commercial_notes = serializers.CharField(required=False, allow_blank=True)
    technical_reference_summary = serializers.CharField(required=False, allow_blank=True)


class CostLineWriteSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=EstimateCostLine.Category.choices, required=False)
    description = serializers.CharField(max_length=500, required=False)
    quantity = serializers.DecimalField(
        max_digits=18, decimal_places=4, min_value=Decimal("0.0001"), required=False
    )
    unit_of_measure = serializers.CharField(max_length=40, required=False)
    unit_cost = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=0, required=False)
    source_reference = serializers.CharField(max_length=250, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    is_optional = serializers.BooleanField(required=False)


class CostLineCreateSerializer(CostLineWriteSerializer):
    estimate_id = serializers.UUIDField()
    category = serializers.ChoiceField(choices=EstimateCostLine.Category.choices)
    description = serializers.CharField(max_length=500)
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal("0.0001"))
    unit_cost = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=0)


class EstimateSubmitSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True)


class EstimateReviseSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)
