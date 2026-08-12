from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.mixins import AuditModelViewSetMixin
from apps.audit.serializers import AuditEventSerializer
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin
from apps.core.tabular_imports import TabularImportUploadSerializer
from apps.crm.serializers import CrmActivitySerializer
from apps.documents.serializers import DocumentSerializer

from .imports import import_enquiries
from .models import Enquiry, EnquiryItem, EnquiryRequirement
from .selectors import enquiry_workspace_data
from .serializers import (
    EnquiryAssignSerializer,
    EnquiryCloseSerializer,
    EnquiryItemSerializer,
    EnquiryRequirementSerializer,
    EnquirySerializer,
)
from .services import assign_enquiry, transition_enquiry


class EnquiryViewSet(AuditModelViewSetMixin, ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Enquiry.objects.select_related(
        "company",
        "customer",
        "customer_contact",
        "customer_site",
        "responsible_salesperson",
        "responsible_salesperson__user",
        "currency",
        "created_by",
        "updated_by",
    ).prefetch_related("requirements", "items", "activities")
    serializer_class = EnquirySerializer
    permission_classes = [HasFoundationPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    permission_map = {
        "list": "enquiry.enquiry.view",
        "retrieve": "enquiry.enquiry.view",
        "create": "enquiry.enquiry.create",
        "import_history": "enquiry.enquiry.create",
        "update": "enquiry.enquiry.edit",
        "partial_update": "enquiry.enquiry.edit",
        "assign": "enquiry.enquiry.assign",
        "send_to_engineering": "enquiry.enquiry.submit_engineering",
        "mark_won": "enquiry.enquiry.mark_won",
        "mark_lost": "enquiry.enquiry.mark_lost",
        "cancel": "enquiry.enquiry.cancel",
        "workspace": "enquiry.enquiry.view",
        "default": "enquiry.enquiry.edit",
    }

    @action(detail=False, methods=["post"], url_path="import-history")
    def import_history(self, request):
        upload_serializer = TabularImportUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        created = import_enquiries(self, upload_serializer.validated_data["file"])
        return Response({"imported": len(created)}, status=status.HTTP_201_CREATED)
    search_fields = [
        "enquiry_number",
        "subject",
        "customer_reference",
        "customer__customer_code",
        "customer__legal_name",
    ]
    filterset_fields = [
        "company",
        "customer",
        "status",
        "priority",
        "responsible_salesperson",
        "received_date",
        "due_date",
    ]
    ordering_fields = [
        "enquiry_number",
        "received_date",
        "due_date",
        "estimated_value",
        "priority",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        due = self.request.query_params.get("due")
        if due == "overdue":
            queryset = queryset.filter(due_date__lt=timezone.localdate()).exclude(
                status__in=[Enquiry.Status.WON, Enquiry.Status.LOST, Enquiry.Status.CANCELLED]
            )
        elif due == "today":
            queryset = queryset.filter(due_date=timezone.localdate())
        return queryset

    def _transition(self, request, target_status, permission, payload=None):
        enquiry = transition_enquiry(
            enquiry_id=self.get_object().pk,
            actor=request.user,
            target_status=target_status,
            permission=permission,
            **(payload or {}),
        )
        return Response(self.get_serializer(enquiry).data)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        return self._transition(
            request,
            Enquiry.Status.RECEIVED,
            "enquiry.enquiry.edit",
        )

    @action(detail=True, methods=["post"], url_path="start-review")
    def start_review(self, request, pk=None):
        return self._transition(
            request,
            Enquiry.Status.UNDER_REVIEW,
            "enquiry.enquiry.edit",
        )

    @action(detail=True, methods=["post"], url_path="send-to-engineering")
    def send_to_engineering(self, request, pk=None):
        return self._transition(
            request,
            Enquiry.Status.ENGINEERING_REVIEW,
            "enquiry.enquiry.submit_engineering",
        )

    @action(detail=True, methods=["post"], url_path="mark-won")
    def mark_won(self, request, pk=None):
        return self._transition(
            request,
            Enquiry.Status.WON,
            "enquiry.enquiry.mark_won",
        )

    @action(detail=True, methods=["post"], url_path="mark-lost")
    def mark_lost(self, request, pk=None):
        serializer = EnquiryCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._transition(
            request,
            Enquiry.Status.LOST,
            "enquiry.enquiry.mark_lost",
            serializer.validated_data,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        serializer = EnquiryCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._transition(
            request,
            Enquiry.Status.CANCELLED,
            "enquiry.enquiry.cancel",
            {"reason": serializer.validated_data["reason"]},
        )

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        serializer = EnquiryAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enquiry = assign_enquiry(
            enquiry_id=self.get_object().pk,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(self.get_serializer(enquiry).data)

    @action(detail=True, methods=["get"])
    def workspace(self, request, pk=None):
        enquiry = self.get_object()
        data = enquiry_workspace_data(enquiry, request.user)
        activities = list(data["activities"])
        events = list(data["audit_events"])
        timeline = [
            {
                "kind": "CRM_ACTIVITY",
                "occurred_at": activity.activity_date,
                "summary": activity.subject,
                "activity_type": activity.activity_type,
            }
            for activity in activities
        ] + [
            {
                "kind": "BUSINESS_CHANGE",
                "occurred_at": event.occurred_at,
                "summary": event.summary,
                "action": event.action,
                "actor_name": AuditEventSerializer().get_actor_name(event),
            }
            for event in events
        ]
        timeline.sort(key=lambda item: item["occurred_at"], reverse=True)
        from apps.engineering_reviews.serializers import EngineeringReviewSerializer

        engineering_review = enquiry.engineering_reviews.filter(is_current=True).first()
        return Response(
            {
                "enquiry": self.get_serializer(enquiry).data,
                "next_follow_up": CrmActivitySerializer(
                    data["next_follow_up"],
                    context={"request": request},
                ).data
                if data["next_follow_up"]
                else None,
                "activities": CrmActivitySerializer(
                    activities,
                    many=True,
                    context={"request": request},
                ).data,
                "documents": DocumentSerializer(
                    data["documents"],
                    many=True,
                    context={"request": request},
                ).data,
                "timeline": timeline[:40],
                "engineering_review": EngineeringReviewSerializer(
                    engineering_review,
                    context={"request": request},
                ).data
                if engineering_review
                else None,
            }
        )


class EnquiryRequirementViewSet(
    AuditModelViewSetMixin,
    ScopedQuerysetMixin,
    viewsets.ModelViewSet,
):
    queryset = EnquiryRequirement.objects.select_related("enquiry", "enquiry__company")
    serializer_class = EnquiryRequirementSerializer
    permission_classes = [HasFoundationPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    permission_map = {
        "list": "enquiry.enquiry.view",
        "retrieve": "enquiry.enquiry.view",
        "default": "enquiry.enquiry.edit",
    }
    search_fields = ["title", "description", "customer_specification_reference"]
    filterset_fields = ["enquiry", "requirement_type", "is_mandatory"]
    ordering_fields = ["requirement_type", "title", "created_at", "updated_at"]


class EnquiryItemViewSet(
    AuditModelViewSetMixin,
    ScopedQuerysetMixin,
    viewsets.ModelViewSet,
):
    queryset = EnquiryItem.objects.select_related("enquiry", "enquiry__company", "uom")
    serializer_class = EnquiryItemSerializer
    permission_classes = [HasFoundationPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    permission_map = {
        "list": "enquiry.enquiry.view",
        "retrieve": "enquiry.enquiry.view",
        "default": "enquiry.enquiry.edit",
    }
    search_fields = ["description", "customer_reference", "technical_specification"]
    filterset_fields = ["enquiry", "uom", "requested_delivery"]
    ordering_fields = ["line_number", "requested_delivery", "created_at", "updated_at"]
