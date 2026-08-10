from rest_framework import serializers

from .models import CompanySettings, FeatureFlag


class CompanySettingsSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    currency_code = serializers.CharField(source="default_currency.code", read_only=True)

    class Meta:
        model = CompanySettings
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class FeatureFlagSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = FeatureFlag
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
