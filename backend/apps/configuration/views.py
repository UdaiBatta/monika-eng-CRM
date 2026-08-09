from rest_framework import viewsets

from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin

from .models import CompanySettings, FeatureFlag
from .serializers import CompanySettingsSerializer, FeatureFlagSerializer


class CompanySettingsViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = CompanySettings.objects.select_related("company", "default_currency")
    serializer_class = CompanySettingsSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "configuration.settings.view",
        "retrieve": "configuration.settings.view",
        "default": "configuration.settings.manage",
    }
    filterset_fields = ["company"]


class FeatureFlagViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = FeatureFlag.objects.select_related("company")
    serializer_class = FeatureFlagSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "configuration.feature_flag.view",
        "retrieve": "configuration.feature_flag.view",
        "default": "configuration.feature_flag.manage",
    }
    search_fields = ["key", "description", "company__name"]
    filterset_fields = ["company", "is_enabled"]
    ordering_fields = ["key", "created_at", "updated_at"]
