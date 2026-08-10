from rest_framework import viewsets

from apps.audit.mixins import AuditModelViewSetMixin
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin

from .models import Currency, DeliveryTerm, PaymentTerm, TaxRate, UnitOfMeasure
from .serializers import (
    CurrencySerializer,
    DeliveryTermSerializer,
    PaymentTermSerializer,
    TaxRateSerializer,
    UnitOfMeasureSerializer,
)


class MasterViewSet(AuditModelViewSetMixin, ScopedQuerysetMixin, viewsets.ModelViewSet):
    permission_classes = [HasFoundationPermission]
    permission_map = {"list": "masters.view", "retrieve": "masters.view", "default": "masters.manage"}
    search_fields = ["code", "name"]
    filterset_fields = ["is_active"]
    ordering_fields = ["code", "name", "created_at", "updated_at"]


class CurrencyViewSet(MasterViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer


class UnitOfMeasureViewSet(MasterViewSet):
    queryset = UnitOfMeasure.objects.all()
    serializer_class = UnitOfMeasureSerializer


class TaxRateViewSet(MasterViewSet):
    queryset = TaxRate.objects.select_related("company")
    serializer_class = TaxRateSerializer
    filterset_fields = ["company", "is_active"]


class PaymentTermViewSet(MasterViewSet):
    queryset = PaymentTerm.objects.select_related("company")
    serializer_class = PaymentTermSerializer
    filterset_fields = ["company", "is_active"]


class DeliveryTermViewSet(MasterViewSet):
    queryset = DeliveryTerm.objects.select_related("company")
    serializer_class = DeliveryTermSerializer
    filterset_fields = ["company", "is_active"]
