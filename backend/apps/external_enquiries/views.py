import hashlib

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.domain_events import publish
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin

from .authentication import verify_website_request
from .intake import create_submission, enforce_rate_limit, find_submission_candidates
from .models import ExternalEnquirySubmission
from .serializers import (
    ExternalSubmissionSerializer,
    SubmissionAssignSerializer,
    SubmissionConversionSerializer,
    SubmissionDecisionSerializer,
    WebsiteIntakeSerializer,
)
from .services import _event, assign_submission, convert_submission, decide_submission


class PayloadTooLarge(APIException):
    status_code = 413
    default_detail = "The website enquiry payload is too large."
    default_code = "payload_too_large"


class WebsiteEnquiryIntakeView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if len(request.body) > settings.WEBSITE_INTAKE_MAX_PAYLOAD_BYTES:
            raise PayloadTooLarge()
        credential, request_id = verify_website_request(request)
        enforce_rate_limit(credential, request)
        serializer = WebsiteIntakeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        checksum = hashlib.sha256(request.body).hexdigest()
        submission, created = create_submission(
            credential=credential,
            request_id=request_id,
            payload=dict(serializer.validated_data),
            payload_checksum=checksum,
            request=request,
        )
        if created:
            publish(
                _event(
                    "external_enquiry.received",
                    submission,
                    None,
                    "CREATE",
                    f"Website enquiry received from {submission.company_name or submission.person_name}",
                    metadata={"channel": submission.channel, "source_type": submission.source_type},
                )
            )
        return Response(
            {"status": "received", "submission_id": submission.external_submission_id},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ExternalEnquirySubmissionViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ExternalEnquirySubmission.objects.select_related(
        "company",
        "credential",
        "assigned_to",
        "matched_customer",
        "matched_contact",
        "converted_customer",
        "converted_contact",
        "converted_enquiry",
        "reviewed_by",
        "converted_by",
    ).prefetch_related("attachments")
    serializer_class = ExternalSubmissionSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "crm.external_enquiry.view",
        "retrieve": "crm.external_enquiry.view",
        "candidates": "crm.external_enquiry.review",
        "assign": "crm.external_enquiry.assign",
        "convert": "crm.external_enquiry.convert",
        "reject": "crm.external_enquiry.reject",
        "mark_spam": "crm.external_enquiry.mark_spam",
        "restore_for_review": "crm.external_enquiry.review",
        "default": "crm.external_enquiry.view",
    }
    search_fields = ["company_name", "person_name", "email", "phone", "subject", "message", "product_name"]
    filterset_fields = [
        "company",
        "review_status",
        "spam_status",
        "duplicate_status",
        "assigned_to",
        "priority",
        "source_type",
    ]
    ordering_fields = ["received_at", "company_name", "person_name", "priority", "updated_at"]

    @action(detail=True, methods=["get"])
    def candidates(self, request, pk=None):
        return Response(find_submission_candidates(self.get_object()))

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        serializer = SubmissionAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = assign_submission(
            submission_id=self.get_object().pk,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(self.get_serializer(submission).data)

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        serializer = SubmissionConversionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = convert_submission(
            submission_id=self.get_object().pk,
            actor=request.user,
            data=serializer.validated_data,
        )
        return Response(self.get_serializer(submission).data)

    def _decision(self, request, target_status):
        serializer = SubmissionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = decide_submission(
            submission_id=self.get_object().pk,
            actor=request.user,
            target_status=target_status,
            **serializer.validated_data,
        )
        return Response(self.get_serializer(submission).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._decision(request, ExternalEnquirySubmission.ReviewStatus.REJECTED)

    @action(detail=True, methods=["post"], url_path="mark-spam")
    def mark_spam(self, request, pk=None):
        return self._decision(request, ExternalEnquirySubmission.ReviewStatus.SPAM)

    @action(detail=True, methods=["post"], url_path="restore-for-review")
    def restore_for_review(self, request, pk=None):
        return self._decision(request, ExternalEnquirySubmission.ReviewStatus.NEEDS_REVIEW)
