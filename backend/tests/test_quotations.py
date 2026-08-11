from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from io import BytesIO
from threading import Barrier

import pytest
from django.core.files.base import ContentFile
from django.db import close_old_connections
from django.utils import timezone
from docx import Document as WordDocument
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.core.conflicts import VersionConflict
from apps.crm.models import Customer
from apps.documents.models import DocumentCategory
from apps.documents.services import create_document
from apps.engineering_reviews.models import EngineeringFeasibilityReview
from apps.enquiries.models import Enquiry
from apps.estimation.models import CommercialEstimate
from apps.masters.models import Currency
from apps.numbering.models import DocumentSequence
from apps.numbering.services import financial_year_label
from apps.quotations.documents import document_context, generate_documents
from apps.quotations.models import (
    CustomerCommercialConfirmation,
    Quotation,
    QuotationGeneratedDocument,
    QuotationTemplate,
)
from apps.quotations.services import create_quotation, update_revision
from apps.rbac.models import Permission, Role, RoleAssignment, RolePermission, ScopeType


@pytest.fixture
def quotation_context(company, employee, user):
    currency = Currency.objects.get_or_create(
        code="INR",
        defaults={"name": "Indian Rupee", "symbol": "INR", "decimal_places": 2},
    )[0]
    customer = Customer.objects.create(
        company=company,
        customer_code="CUST-QUOTE-001",
        legal_name="Quotation Customer Pvt. Ltd.",
        default_currency=currency,
        status=Customer.Status.ACTIVE,
        created_by=user,
        updated_by=user,
    )
    enquiry = Enquiry.objects.create(
        company=company,
        enquiry_number="ENQ-QUOTE-001",
        customer=customer,
        subject="MCC control panel supply",
        responsible_salesperson=employee,
        status=Enquiry.Status.ESTIMATION_COMPLETE,
        created_by=user,
        updated_by=user,
    )
    review = EngineeringFeasibilityReview.objects.create(
        company=company,
        enquiry=enquiry,
        status=EngineeringFeasibilityReview.Status.FEASIBLE,
        result=EngineeringFeasibilityReview.Result.FEASIBLE,
        completed_at=timezone.now(),
        completed_by=user,
        created_by=user,
    )
    estimate = CommercialEstimate.objects.create(
        company=company,
        enquiry=enquiry,
        engineering_review=review,
        estimate_number="EST-QUOTE-001",
        revision_number=1,
        is_current=True,
        status=CommercialEstimate.Status.APPROVED,
        currency=currency,
        proposed_selling_price=Decimal("100000"),
        prepared_by=user,
        created_by=user,
        updated_by=user,
        approved_at=timezone.now(),
        approved_by=user,
    )
    DocumentSequence.objects.create(
        company=company,
        code="QUOTATION",
        financial_year=financial_year_label(company),
        template="QTN-2026-{number}",
        padding=4,
    )
    return {
        "currency": currency,
        "customer": customer,
        "enquiry": enquiry,
        "estimate": estimate,
    }


def _make_superuser(user):
    user.is_superuser = True
    user.is_staff = True
    user.save(update_fields=["is_superuser", "is_staff"])


def _quick_payload(context):
    return {
        "path": "QUICK",
        "customer_id": str(context["customer"].pk),
        "enquiry_id": str(context["enquiry"].pk),
        "quick_reason": "Customer needs a budgetary quotation today.",
        "lines": [
            {
                "description": "Budgetary MCC panel supply",
                "quantity": "1",
                "unit_of_measure": "LOT",
                "unit_price": "85000",
                "tax_percent": "18",
            }
        ],
    }


@pytest.mark.django_db
def test_standard_quote_uses_approved_estimate_and_handles_conflict(
    api_client, user, quotation_context
):
    _make_superuser(user)
    api_client.force_authenticate(user)
    created = api_client.post(
        "/api/v1/quotations/",
        {
            "path": "STANDARD",
            "customer_id": str(quotation_context["customer"].pk),
            "enquiry_id": str(quotation_context["enquiry"].pk),
            "estimate_id": str(quotation_context["estimate"].pk),
        },
        format="json",
    )

    assert created.status_code == 201, created.data
    revision = created.data["current_revision"]
    assert revision["grand_total"] == "100000.00"
    assert "total_cost" not in revision["estimate_snapshot"]
    revision_id = revision["id"]

    first = api_client.post(
        f"/api/v1/quotation-revisions/{revision_id}/update-draft/",
        {"record_version": 1, "scope": "Panel supply, testing and FAT."},
        format="json",
    )
    stale = api_client.post(
        f"/api/v1/quotation-revisions/{revision_id}/update-draft/",
        {"record_version": 1, "scope": "Stale browser edit."},
        format="json",
    )

    assert first.status_code == 200, first.data
    assert first.data["record_version"] == 2
    assert stale.status_code == 409
    assert stale.data["error"]["code"] == "version_conflict"


@pytest.mark.django_db
def test_sent_quote_freezes_revision_then_negotiates_revises_and_compares(
    api_client, user, quotation_context
):
    _make_superuser(user)
    api_client.force_authenticate(user)
    created = api_client.post("/api/v1/quotations/", _quick_payload(quotation_context), format="json")
    quote_id = created.data["id"]
    revision_id = created.data["current_revision"]["id"]
    finalized = api_client.post(f"/api/v1/quotation-revisions/{revision_id}/finalize/", {})
    sent = api_client.post(
        f"/api/v1/quotation-revisions/{revision_id}/communication/",
        {
            "channel": "WHATSAPP",
            "direction": "OUTBOUND",
            "summary": "Quotation PDF shared manually on WhatsApp.",
        },
        format="json",
    )
    frozen_edit = api_client.post(
        f"/api/v1/quotation-revisions/{revision_id}/update-draft/",
        {"record_version": 1, "scope": "Should not save."},
        format="json",
    )
    negotiated = api_client.post(
        f"/api/v1/quotations/{quote_id}/negotiation/",
        {
            "channel": "PHONE",
            "summary": "Customer requested a revised price.",
            "commercial_impact": "Price and delivery change",
            "material_change": True,
        },
        format="json",
    )
    revised = api_client.post(f"/api/v1/quotations/{quote_id}/revise/", {})
    compare = api_client.get(f"/api/v1/quotations/{quote_id}/compare/")

    assert finalized.data["status"] == "READY_TO_SEND"
    assert sent.status_code == 201
    assert frozen_edit.status_code == 400
    assert negotiated.status_code == 201
    assert negotiated.data["material_change"] is True
    assert revised.status_code == 201
    assert revised.data["revision_number"] == 2
    assert len(compare.data) == 1


@pytest.mark.django_db
def test_informal_confirmation_and_po_pending_stop_at_ready_for_sales_order(
    api_client, user, quotation_context
):
    _make_superuser(user)
    api_client.force_authenticate(user)
    created = api_client.post("/api/v1/quotations/", _quick_payload(quotation_context), format="json")
    quote_id = created.data["id"]
    revision_id = created.data["current_revision"]["id"]
    api_client.post(f"/api/v1/quotation-revisions/{revision_id}/finalize/", {})
    api_client.post(
        f"/api/v1/quotation-revisions/{revision_id}/communication/",
        {
            "channel": "PHONE",
            "direction": "OUTBOUND",
            "summary": "Quote discussed and sent to the customer.",
        },
        format="json",
    )
    confirmed = api_client.post(
        f"/api/v1/quotations/{quote_id}/confirm/",
        {
            "method": "VERBAL",
            "confirmation_reference": "Call with purchase manager",
            "po_pending": True,
        },
        format="json",
    )
    ready = api_client.post(f"/api/v1/quotations/{quote_id}/ready-for-sales-order/", {})

    assert confirmed.status_code == 200
    assert confirmed.data["po_pending"] is True
    assert ready.status_code == 200
    quote = Quotation.objects.get(pk=quote_id)
    assert quote.status == Quotation.Status.READY_FOR_SALES_ORDER
    assert CustomerCommercialConfirmation.objects.get(quotation=quote).ready_for_sales_order_at


@pytest.mark.django_db
def test_quick_quote_requires_specific_permission(api_client, user, quotation_context):
    create_permission = Permission.objects.get(code="crm.quotation.create")
    role = Role.objects.create(company=user.employee.company, code="QUOTE-CREATE", name="Quote creator")
    RolePermission.objects.create(role=role, permission=create_permission)
    RoleAssignment.objects.create(
        user=user,
        role=role,
        scope_type=ScopeType.COMPANY,
        company=user.employee.company,
    )
    api_client.force_authenticate(user)
    response = api_client.post("/api/v1/quotations/", _quick_payload(quotation_context), format="json")
    assert response.status_code == 403


def _word_template_bytes(text):
    document = WordDocument()
    document.add_paragraph(text)
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


@pytest.mark.django_db
def test_docx_generation_uses_whitelist_and_pdf_failure_is_graceful(
    monkeypatch, settings, tmp_path, user, quotation_context
):
    _make_superuser(user)
    settings.LOCAL_PRIVATE_STORAGE_ROOT = tmp_path
    quotation = create_quotation(actor=user, data=_quick_payload(quotation_context))
    category = DocumentCategory.objects.create(
        company=user.employee.company,
        code="QUOTATION",
        name="Quotation outputs",
        allowed_extensions=["docx", "pdf"],
    )
    source = create_document(
        category=category,
        title="Controlled quotation template",
        file_object=ContentFile(
            _word_template_bytes(
                "Quotation {{ quotation.number }} for {{ customer.name }}: {{ totals.grand_total }}"
            ),
            name="quotation-template.docx",
        ),
        actor=user,
    )
    template = QuotationTemplate.objects.create(
        company=user.employee.company,
        code="DEFAULT",
        name="Default quotation",
        source_document=source,
        output_category=category,
    )
    monkeypatch.setattr(
        "apps.quotations.documents.convert_docx_to_pdf",
        lambda _bytes, _stem: (None, "LibreOffice unavailable for test"),
    )
    generated = generate_documents(
        revision_id=quotation.current_revision_id, template_id=template.pk, actor=user
    )

    assert generated.status == QuotationGeneratedDocument.Status.WORD_ONLY
    assert generated.docx_document.current_version.file_extension == "docx"
    assert generated.pdf_document is None
    assert "LibreOffice" in generated.pdf_error
    context = document_context(quotation.current_revision)
    assert "estimate" not in context
    assert "total_cost" not in str(context)

    monkeypatch.setattr(
        "apps.quotations.documents.convert_docx_to_pdf",
        lambda _bytes, _stem: (b"%PDF-1.4\nquotation", ""),
    )
    complete = generate_documents(
        revision_id=quotation.current_revision_id, template_id=template.pk, actor=user
    )
    assert complete.status == QuotationGeneratedDocument.Status.COMPLETE
    assert complete.pdf_document.current_version.file_extension == "pdf"
    assert complete.docx_document_id != generated.docx_document_id

    forbidden_source = create_document(
        category=category,
        title="Unsafe quotation template",
        file_object=ContentFile(
            _word_template_bytes("Internal cost {{ estimate.total_cost }}"),
            name="unsafe-template.docx",
        ),
        actor=user,
    )
    forbidden = QuotationTemplate.objects.create(
        company=user.employee.company,
        code="UNSAFE",
        name="Unsafe template",
        source_document=forbidden_source,
        output_category=category,
    )
    with pytest.raises(ValidationError, match="Unsupported template variables"):
        generate_documents(
            revision_id=quotation.current_revision_id,
            template_id=forbidden.pk,
            actor=user,
        )


@pytest.mark.django_db(transaction=True)
def test_postgres_concurrent_edits_yield_one_success_and_one_conflict(user, quotation_context):
    _make_superuser(user)
    quotation = create_quotation(actor=user, data=_quick_payload(quotation_context))
    revision_id = quotation.current_revision_id
    barrier = Barrier(2)

    def edit(scope):
        close_old_connections()
        actor = User.objects.get(pk=user.pk)
        barrier.wait()
        try:
            update_revision(
                revision_id=revision_id,
                actor=actor,
                submitted_version=1,
                data={"scope": scope},
            )
            return "saved"
        except VersionConflict:
            return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(edit, ["First edit", "Second edit"]))

    assert sorted(outcomes) == ["conflict", "saved"]
