from decimal import Decimal

from django.db.models import Sum
from rest_framework import serializers

from .models import (
    Product,
    ProductCategory,
    StockItem,
    StockLocation,
    StockMovement,
    Supplier,
)


class FoundationSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        instance = self.instance or self.Meta.model()
        many_to_many_fields = {f.name for f in instance._meta.many_to_many}
        for field, value in attrs.items():
            if field in many_to_many_fields:
                continue
            setattr(instance, field, value)
        instance.full_clean(exclude=many_to_many_fields or None)
        return attrs


class ProductCategorySerializer(FoundationSerializer):
    class Meta:
        model = ProductCategory
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "record_version"]


class SupplierSerializer(FoundationSerializer):
    payment_term_name = serializers.CharField(source="payment_term.name", read_only=True, default="")

    class Meta:
        model = Supplier
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "record_version"]


class ProductSerializer(FoundationSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    default_supplier_name = serializers.CharField(source="default_supplier.name", read_only=True, default="")
    unit_of_measure_code = serializers.CharField(source="unit_of_measure.code", read_only=True)
    available_quantity = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "record_version"]

    def get_available_quantity(self, obj):
        available = obj.stock_items.filter(condition=StockItem.Condition.AVAILABLE)
        total = available.aggregate(total=Sum("quantity"))["total"]
        return str(total or 0)


class StockLocationSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)

    class Meta:
        model = StockLocation
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "record_version"]

    def validate(self, attrs):
        instance = self.instance or StockLocation()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean()
        return attrs


class StockItemSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.internal_code", read_only=True)
    product_description = serializers.CharField(source="product.description", read_only=True)
    location_label = serializers.CharField(source="location.__str__", read_only=True)
    condition_label = serializers.CharField(source="get_condition_display", read_only=True)

    class Meta:
        model = StockItem
        fields = "__all__"
        read_only_fields = [field.name for field in StockItem._meta.fields]


class StockMovementSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.internal_code", read_only=True)
    product_description = serializers.CharField(source="product.description", read_only=True)
    movement_type_label = serializers.CharField(source="get_movement_type_display", read_only=True)
    from_location_label = serializers.CharField(source="from_location.__str__", read_only=True, default="")
    to_location_label = serializers.CharField(source="to_location.__str__", read_only=True, default="")
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True, default="")

    class Meta:
        model = StockMovement
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "movement_number",
            "company",
            "created_by",
        ]


class RecordMovementSerializer(serializers.Serializer):
    movement_type = serializers.ChoiceField(choices=StockMovement.MovementType.choices)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal("0.0001"))
    from_location = serializers.PrimaryKeyRelatedField(
        queryset=StockLocation.objects.all(), required=False, allow_null=True
    )
    from_condition = serializers.ChoiceField(
        choices=StockItem.Condition.choices, required=False, allow_blank=True, default=""
    )
    to_location = serializers.PrimaryKeyRelatedField(
        queryset=StockLocation.objects.all(), required=False, allow_null=True
    )
    to_condition = serializers.ChoiceField(
        choices=StockItem.Condition.choices, required=False, allow_blank=True, default=""
    )
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    reference_type = serializers.CharField(required=False, allow_blank=True, default="")
    reference_id = serializers.UUIDField(required=False, allow_null=True)
