from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.approvals.serializers import ApprovalRequestSerializer
from apps.audit.serializers import AuditEventSerializer
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin
from apps.documents.serializers import DocumentSerializer
from apps.enquiries.serializers import EnquirySerializer

from .models import EngineeringClarification, EngineeringFeasibilityReview
from .selectors import review_workspace_data
from .serializers import (
    ClarificationCloseSerializer,
    ClarificationRequestSerializer,
    ClarificationResponseSerializer,
    EngineeringAssessmentSerializer,
    EngineeringClarificationSerializer,
    EngineeringReviewSerializer,
    ReviewAssignSerializer,
    ReviewCompleteSerializer,
    ReviewNotFeasibleSerializer,
    ReviewReassessSerializer,
)
from .services import (
    assign_review,
    close_clarification,
    complete_review,
    mark_not_feasible,
    reassess_review,
    request_clarification,
    respond_to_clarification,
    start_review,
    update_assessment,
)


class EngineeringReviewViewSet(
    ScopedQuerysetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = EngineeringFeasibilityReview.objects.select_related(
        "company",
        "enquiry",
        "enquiry__customer",
        "enquiry__responsible_salesperson",
        "assigned_engineer",
        "assigned_engineer__user",
        "started_by",
        "completed_by",
        "supersedes",
    ).prefetch_related("clarifications", "clarifications__assigned_to")
    serializer_class = EngineeringReviewSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "engineering.feasibility.view",
        "retrieve": "engineering.feasibility.view",
        "workspace": "engineering.feasibility.view",
        "revisions": "engineering.feasibility.view",
        "assign": "engineering.feasibility.assign",
        "start": "engineering.feasibility.start",
        "assessment": "engineering.feasibility.edit",
        "request_clarification": "engineering.feasibility.request_clarification",
        "complete": "engineering.feasibility.complete",
        "mark_not_feasible": "engineering.feasibility.mark_not_feasible",
        "reassess": "engineering.feasibility.reassess",
        "default": "engineering.feasibility.view",
    }
    search_fields = [
        "enquiry__enquiry_number",
        "enquiry__subject",
        "enquiry__customer__legal_name",
        "enquiry__customer__customer_code",
    ]
    filterset_fields = ["company", "enquiry", "status", "result", "assigned_engineer", "is_current"]
    ordering_fields = ["created_at", "updated_at", "enquiry__due_date", "revision_number", "completed_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queue = self.request.query_params.get("queue")
        employee = getattr(self.request.user, "employee", None)
        if queue == "unassigned":
            queryset = queryset.filter(
                is_current=True,
                assigned_engineer__isnull=True,
                status=EngineeringFeasibilityReview.Status.PENDING,
            )
        elif queue == "mine":
            queryset = (
                queryset.filter(is_current=True, assigned_engineer=employee) if employee else queryset.none()
            )
        elif queue == "in_review":
            queryset = queryset.filter(is_current=True, status=EngineeringFeasibilityReview.Status.IN_REVIEW)
        elif queue == "clarification":
            queryset = queryset.filter(
                is_current=True, status=EngineeringFeasibilityReview.Status.CLARIFICATION_REQUIRED
            )
        elif queue == "completed":
            queryset = queryset.filter(
                status__in=[
                    EngineeringFeasibilityReview.Status.FEASIBLE,
                    EngineeringFeasibilityReview.Status.NOT_FEASIBLE,
                    EngineeringFeasibilityReview.Status.SUPERSEDED,
                ]
            )
        if self.request.query_params.get("current", "").lower() == "true":
            queryset = queryset.filter(is_current=True)
        return queryset

    def _serialize(self, review):
        return Response(self.get_serializer(review).data)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        serializer = ReviewAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._serialize(
            assign_review(review_id=self.get_object().pk, actor=request.user, **serializer.validated_data)
        )

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        return self._serialize(start_review(review_id=self.get_object().pk, actor=request.user))

    @action(detail=True, methods=["patch"])
    def assessment(self, request, pk=None):
        serializer = EngineeringAssessmentSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return self._serialize(
            update_assessment(
                review_id=self.get_object().pk, actor=request.user, data=serializer.validated_data
            )
        )

    @action(detail=True, methods=["post"], url_path="request-clarification")
    def request_clarification(self, request, pk=None):
        serializer = ClarificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clarification = request_clarification(
            review_id=self.get_object().pk, actor=request.user, **serializer.validated_data
        )
        return Response(EngineeringClarificationSerializer(clarification).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        serializer = ReviewCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._serialize(
            complete_review(review_id=self.get_object().pk, actor=request.user, **serializer.validated_data)
        )

    @action(detail=True, methods=["post"], url_path="mark-not-feasible")
    def mark_not_feasible(self, request, pk=None):
        serializer = ReviewNotFeasibleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._serialize(
            mark_not_feasible(review_id=self.get_object().pk, actor=request.user, **serializer.validated_data)
        )

    @action(detail=True, methods=["post"])
    def reassess(self, request, pk=None):
        serializer = ReviewReassessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._serialize(
            reassess_review(review_id=self.get_object().pk, actor=request.user, **serializer.validated_data)
        )

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        review = self.get_object()
        revisions = self.get_queryset().filter(enquiry=review.enquiry).order_by("-revision_number")
        return Response(self.get_serializer(revisions, many=True).data)

    @action(detail=True, methods=["get"])
    def workspace(self, request, pk=None):
        review = self.get_object()
        data = review_workspace_data(review, request.user)
        return Response(
            {
                "review": self.get_serializer(review).data,
                "enquiry": EnquirySerializer(review.enquiry, context={"request": request}).data,
                "documents": DocumentSerializer(
                    data["documents"], many=True, context={"request": request}
                ).data,
                "approvals": ApprovalRequestSerializer(data["approvals"], many=True).data,
                "timeline": AuditEventSerializer(data["audit_events"], many=True).data,
            }
        )


class EngineeringClarificationViewSet(
    ScopedQuerysetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = EngineeringClarification.objects.select_related(
        "company",
        "review",
        "review__enquiry",
        "review__enquiry__customer",
        "assigned_to",
        "requested_by",
        "responded_by",
        "closed_by",
    )
    serializer_class = EngineeringClarificationSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "engineering.feasibility.view",
        "retrieve": "engineering.feasibility.view",
        "respond": "engineering.feasibility.respond_clarification",
        "close": "engineering.feasibility.edit",
        "default": "engineering.feasibility.view",
    }
    search_fields = ["subject", "question", "response", "review__enquiry__enquiry_number"]
    filterset_fields = ["company", "review", "status", "assigned_to"]
    ordering_fields = ["requested_at", "due_at", "responded_at", "closed_at"]

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        serializer = ClarificationResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clarification = respond_to_clarification(
            clarification_id=self.get_object().pk, actor=request.user, **serializer.validated_data
        )
        return Response(self.get_serializer(clarification).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        serializer = ClarificationCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clarification = close_clarification(
            clarification_id=self.get_object().pk, actor=request.user, **serializer.validated_data
        )
        return Response(self.get_serializer(clarification).data)
