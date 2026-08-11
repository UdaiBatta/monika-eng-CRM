import hashlib

from django.conf import settings
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.domain_events import publish
from apps.core.permissions import HasFoundationPermission, ScopedQuerysetMixin

from .authentication import verify_website_request
from .imports import parse_historical_enquiries
from .intake import create_submission, enforce_rate_limit, find_submission_candidates
from .models import ExternalEnquirySubmission
from .serializers import (
    ExternalSubmissionSerializer,
    HistoricalIncomingEnquiryImportSerializer,
    HistoricalIncomingEnquiryRowSerializer,
    ManualIncomingEnquirySerializer,
    SubmissionAssignSerializer,
    SubmissionConversionSerializer,
    SubmissionDecisionSerializer,
    WebsiteIntakeSerializer,
)
from .services import (
    _event,
    assign_submission,
    convert_submission,
    create_manual_submission,
    decide_submission,
    take_ownership,
)


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
    ).prefetch_related("attachments", "source_history")
    serializer_class = ExternalSubmissionSerializer
    permission_classes = [HasFoundationPermission]
    permission_map = {
        "list": "crm.external_enquiry.view",
        "retrieve": "crm.external_enquiry.view",
        "candidates": "crm.external_enquiry.review",
        "assign": "crm.external_enquiry.assign",
        "take_ownership": "crm.external_enquiry.assign",
        "manual_capture": "crm.external_enquiry.review",
        "import_history": "crm.external_enquiry.review",
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
        "channel",
    ]
    ordering_fields = ["received_at", "company_name", "person_name", "priority", "updated_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queue = self.request.query_params.get("queue")
        employee = getattr(self.request.user, "employee", None)
        if queue == "mine":
            return queryset.filter(assigned_to=employee) if employee else queryset.none()
        if queue == "unassigned":
            return queryset.filter(assigned_to__isnull=True)
        return queryset

    @action(detail=False, methods=["post"], url_path="manual-capture")
    def manual_capture(self, request):
        serializer = ManualIncomingEnquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = create_manual_submission(actor=request.user, data=serializer.validated_data)
        return Response(self.get_serializer(submission).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="import-history")
    def import_history(self, request):
        upload_serializer = HistoricalIncomingEnquiryImportSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        rows = parse_historical_enquiries(upload_serializer.validated_data["file"])

        validated_rows = []
        errors = []
        seen_references = set()
        for row_number, row in enumerate(rows, start=2):
            row_serializer = HistoricalIncomingEnquiryRowSerializer(data=row)
            if not row_serializer.is_valid():
                errors.append({"row": row_number, "errors": row_serializer.errors})
                continue
            data = row_serializer.validated_data
            reference = data.get("source_reference", "").strip()
            key = (data["channel"], reference)
            if reference and key in seen_references:
                errors.append({"row": row_number, "errors": {"source_reference": ["Duplicate in file."]}})
                continue
            if reference:
                seen_references.add(key)
            validated_rows.append((row_number, data))

        employee = getattr(request.user, "employee", None)
        if employee and seen_references:
            existing = set(
                ExternalEnquirySubmission.objects.filter(
                    company_id=employee.company_id,
                    external_submission_id__in=[reference for _, reference in seen_references],
                ).values_list("channel", "external_submission_id")
            )
            for row_number, data in validated_rows:
                reference = data.get("source_reference", "").strip()
                if reference and (data["channel"], reference) in existing:
                    errors.append(
                        {
                            "row": row_number,
                            "errors": {"source_reference": ["Already exists for this source."]},
                        }
                    )

        if errors:
            raise ValidationError({"rows": errors})

        with transaction.atomic():
            created = [
                create_manual_submission(actor=request.user, data=data)
                for _, data in validated_rows
            ]
        return Response(
            {
                "imported": len(created),
                "possible_duplicates": sum(
                    item.duplicate_status == ExternalEnquirySubmission.DuplicateStatus.POSSIBLE
                    for item in created
                ),
            },
            status=status.HTTP_201_CREATED,
        )

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

    @action(detail=True, methods=["post"], url_path="take-ownership")
    def take_ownership(self, request, pk=None):
        submission = take_ownership(submission_id=self.get_object().pk, actor=request.user)
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
