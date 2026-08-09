from rest_framework import serializers

from .models import Currency, DeliveryTerm, PaymentTerm, TaxRate, UnitOfMeasure


class FoundationMasterSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        instance = self.instance or self.Meta.model()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean()
        return attrs


class CurrencySerializer(FoundationMasterSerializer):
    class Meta:
        model = Currency
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class UnitOfMeasureSerializer(FoundationMasterSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class TaxRateSerializer(FoundationMasterSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = TaxRate
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class PaymentTermSerializer(FoundationMasterSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = PaymentTerm
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class DeliveryTermSerializer(FoundationMasterSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = DeliveryTerm
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
