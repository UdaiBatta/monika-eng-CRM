from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from apps.audit.mixins import AuditModelViewSetMixin
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin
from apps.organization.models import Company
from apps.rbac.services import has_permission

from .models import Customer, CustomerContact, CustomerSite
from .serializers import (
    CustomerContactSerializer,
    CustomerDuplicateCheckSerializer,
    CustomerSerializer,
    CustomerSiteSerializer,
    CustomerStatusCommandSerializer,
)
from .services import change_customer_status, find_customer_duplicates


class CustomerViewSet(AuditModelViewSetMixin, ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.select_related(
        "company",
        "account_manager",
        "payment_term",
        "default_currency",
        "default_tax",
    ).prefetch_related("contacts", "sites")
    serializer_class = CustomerSerializer
    permission_classes = [HasFoundationPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    permission_map = {
        "list": "crm.customer.view",
        "retrieve": "crm.customer.view",
        "create": "crm.customer.create",
        "update": "crm.customer.edit",
        "partial_update": "crm.customer.edit",
        "duplicate_check": "crm.customer.create",
        "activate": "crm.customer.edit",
        "deactivate": "crm.customer.deactivate",
        "block": "crm.customer.block",
        "default": "crm.customer.view",
    }
    search_fields = [
        "customer_code",
        "legal_name",
        "trade_name",
        "gstin",
        "pan",
        "primary_email",
        "primary_phone",
        "contacts__first_name",
        "contacts__last_name",
    ]
    filterset_fields = ["company", "status", "customer_type", "account_manager", "industry"]
    ordering_fields = ["customer_code", "legal_name", "status", "created_at", "updated_at"]

    @action(detail=False, methods=["get"], url_path="duplicate-check")
    def duplicate_check(self, request):
        serializer = CustomerDuplicateCheckSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        try:
            company = Company.objects.get(pk=serializer.validated_data.pop("company"))
        except Company.DoesNotExist as exc:
            raise NotFound("Company not found.") from exc
        if not has_permission(request.user, "crm.customer.create", company):
            raise PermissionDenied("You cannot check customer records for this company.")
        matches = find_customer_duplicates(company=company, **serializer.validated_data)
        return Response({"possible_matches": matches})

    def _change_status(self, request, target_status, permission):
        serializer = CustomerStatusCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = change_customer_status(
            customer_id=self.get_object().pk,
            actor=request.user,
            target_status=target_status,
            permission=permission,
            **serializer.validated_data,
        )
        return Response(self.get_serializer(customer).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        return self._change_status(request, Customer.Status.ACTIVE, "crm.customer.edit")

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        return self._change_status(request, Customer.Status.INACTIVE, "crm.customer.deactivate")

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        return self._change_status(request, Customer.Status.BLOCKED, "crm.customer.block")


class CustomerContactViewSet(
    AuditModelViewSetMixin,
    ScopedQuerysetMixin,
    viewsets.ModelViewSet,
):
    queryset = CustomerContact.objects.select_related("customer", "customer__company")
    serializer_class = CustomerContactSerializer
    permission_classes = [HasFoundationPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    permission_map = {
        "list": "crm.contact.view",
        "retrieve": "crm.contact.view",
        "create": "crm.contact.create",
        "default": "crm.contact.edit",
    }
    search_fields = ["first_name", "last_name", "email", "phone", "customer__legal_name"]
    filterset_fields = ["customer", "is_primary", "is_active", "preferred_contact_method"]
    ordering_fields = ["first_name", "last_name", "created_at", "updated_at"]


class CustomerSiteViewSet(
    AuditModelViewSetMixin,
    ScopedQuerysetMixin,
    viewsets.ModelViewSet,
):
    queryset = CustomerSite.objects.select_related("customer", "customer__company", "contact")
    serializer_class = CustomerSiteSerializer
    permission_classes = [HasFoundationPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    permission_map = {
        "list": "crm.customer.view",
        "retrieve": "crm.customer.view",
        "create": "crm.customer.edit",
        "default": "crm.customer.edit",
    }
    search_fields = ["label", "city", "state", "postal_code", "customer__legal_name"]
    filterset_fields = ["customer", "address_type", "is_default", "is_active"]
    ordering_fields = ["label", "city", "address_type", "created_at", "updated_at"]
