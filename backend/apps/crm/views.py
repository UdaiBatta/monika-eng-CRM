from django.db.models import Max
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from apps.audit.mixins import AuditModelViewSetMixin
from apps.audit.serializers import AuditEventSerializer
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin
from apps.documents.serializers import DocumentSerializer
from apps.organization.models import Company
from apps.rbac.services import has_permission

from .models import CrmActivity, Customer, CustomerContact, CustomerSite
from .selectors import customer_360_data
from .serializers import (
    CrmActivitySerializer,
    CustomerContactSerializer,
    CustomerDuplicateCheckSerializer,
    CustomerSerializer,
    CustomerSiteSerializer,
    CustomerStatusCommandSerializer,
)
from .services import change_activity_status, change_customer_status, find_customer_duplicates


class CustomerViewSet(AuditModelViewSetMixin, ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = (
        Customer.objects.select_related(
            "company",
            "account_manager",
            "payment_term",
            "default_currency",
            "default_tax",
        )
        .prefetch_related("contacts", "sites")
        .annotate(last_activity_at=Max("activities__activity_date"))
        .order_by("legal_name", "customer_code")
    )
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
        "customer_360": "crm.customer.view",
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

    @action(detail=True, methods=["get"], url_path="360")
    def customer_360(self, request, pk=None):
        from apps.enquiries.serializers import EnquirySerializer

        customer = self.get_object()
        data = customer_360_data(customer, request.user)
        activity_serializer = CrmActivitySerializer(
            context={"request": request},
        )
        activity_timeline = [
            {
                "kind": "CRM_ACTIVITY",
                "occurred_at": activity.activity_date,
                "summary": activity.subject,
                "activity_type": activity.activity_type,
                "actor_name": activity_serializer.get_created_by_name(activity),
            }
            for activity in data["recent_activities"]
        ]
        audit_timeline = [
            {
                "kind": "BUSINESS_CHANGE",
                "occurred_at": event.occurred_at,
                "summary": event.summary,
                "action": event.action,
                "actor_name": AuditEventSerializer().get_actor_name(event),
            }
            for event in data["audit_events"]
        ]
        timeline = sorted(
            activity_timeline + audit_timeline,
            key=lambda item: item["occurred_at"],
            reverse=True,
        )[:30]
        return Response(
            {
                "customer": self.get_serializer(customer).data,
                "overview": {
                    "open_follow_ups": data["open_follow_up_count"],
                    "open_enquiries": data["open_enquiry_count"],
                    "won_enquiries": data["won_enquiry_count"],
                    "lost_enquiries": data["lost_enquiry_count"],
                    "last_contact": CrmActivitySerializer(
                        data["last_contact"], context={"request": request}
                    ).data
                    if data["last_contact"]
                    else None,
                    "next_follow_up": CrmActivitySerializer(
                        data["next_follow_up"], context={"request": request}
                    ).data
                    if data["next_follow_up"]
                    else None,
                },
                "recent_activities": CrmActivitySerializer(
                    data["recent_activities"], many=True, context={"request": request}
                ).data,
                "open_follow_ups": CrmActivitySerializer(
                    data["open_follow_ups"], many=True, context={"request": request}
                ).data,
                "recent_enquiries": EnquirySerializer(
                    data["recent_enquiries"],
                    many=True,
                    context={"request": request},
                ).data,
                "recent_documents": DocumentSerializer(
                    data["recent_documents"], many=True, context={"request": request}
                ).data,
                "timeline": timeline,
            }
        )


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


class CrmActivityViewSet(
    AuditModelViewSetMixin,
    ScopedQuerysetMixin,
    viewsets.ModelViewSet,
):
    queryset = CrmActivity.objects.select_related(
        "company",
        "customer",
        "contact",
        "created_by",
        "created_by__employee",
        "follow_up_owner",
        "follow_up_owner__user",
        "completed_by",
    )
    serializer_class = CrmActivitySerializer
    permission_classes = [HasFoundationPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    permission_map = {
        "list": "crm.activity.view",
        "retrieve": "crm.activity.view",
        "create": "crm.activity.create",
        "update": "crm.activity.edit",
        "partial_update": "crm.activity.edit",
        "complete": "crm.activity.complete",
        "cancel": "crm.activity.edit",
        "default": "crm.activity.view",
    }
    search_fields = ["subject", "description", "customer__legal_name", "customer__customer_code"]
    filterset_fields = [
        "company",
        "customer",
        "contact",
        "activity_type",
        "status",
        "priority",
        "follow_up_owner",
    ]
    ordering_fields = ["activity_date", "next_follow_up_at", "priority", "created_at", "updated_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get("mine", "").lower() == "true":
            employee = getattr(self.request.user, "employee", None)
            return queryset.filter(follow_up_owner=employee) if employee else queryset.none()
        return queryset

    def _change_status(self, request, target_status):
        activity = change_activity_status(
            activity_id=self.get_object().pk,
            actor=request.user,
            target_status=target_status,
        )
        return Response(self.get_serializer(activity).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._change_status(request, CrmActivity.Status.COMPLETED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._change_status(request, CrmActivity.Status.CANCELLED)
