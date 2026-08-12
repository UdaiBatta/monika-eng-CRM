import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from docxtpl import DocxTemplate
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.documents.services import create_document, link_document
from apps.documents.storage import get_storage
from apps.rbac.services import has_permission

from .models import (
    QuotationGeneratedDocument,
    QuotationRevision,
    QuotationTemplate,
)

ALLOWED_TEMPLATE_VARIABLES = {
    "company",
    "customer",
    "quotation",
    "revision",
    "lines",
    "totals",
    "terms",
}


def document_context(revision):
    quotation = revision.quotation
    customer = quotation.customer
    company = quotation.company
    return {
        "company": {
            "name": company.legal_name or company.name,
            "code": company.code,
            "gstin": company.gstin,
            "pan": company.pan,
        },
        "customer": {
            "name": customer.legal_name,
            "code": customer.customer_code,
            "gstin": customer.gstin,
            "email": customer.primary_email,
            "phone": customer.primary_phone,
        },
        "quotation": {
            "number": quotation.quotation_number,
            "path": quotation.get_path_display(),
            "status": quotation.get_status_display(),
        },
        "revision": {
            "number": revision.revision_number,
            "issue_date": revision.issue_date.isoformat(),
            "valid_until": revision.valid_until.isoformat() if revision.valid_until else "",
            "currency": revision.currency.code,
        },
        "lines": [
            {
                "number": line.line_number,
                "item_code": line.item_code,
                "description": line.description,
                "quantity": str(line.quantity),
                "uom": line.unit_of_measure,
                "unit_price": str(line.unit_price),
                "discount_percent": str(line.discount_percent),
                "tax_percent": str(line.tax_percent),
                "total": str(line.total_amount),
                "optional": line.is_optional,
                "notes": line.notes,
            }
            for line in revision.lines.order_by("line_number")
        ],
        "totals": {
            "subtotal": str(revision.subtotal),
            "discount": str(revision.discount_amount),
            "taxable": str(revision.taxable_amount),
            "tax": str(revision.tax_amount),
            "grand_total": str(revision.grand_total),
        },
        "terms": {
            "introduction": revision.introduction,
            "scope": revision.scope,
            "inclusions": revision.inclusions,
            "exclusions": revision.exclusions,
            "assumptions": revision.assumptions,
            "payment": revision.payment_terms,
            "delivery": revision.delivery_terms,
            "warranty": revision.warranty_terms,
            "freight": revision.freight_terms,
            "notes": revision.customer_notes,
        },
    }


def convert_docx_to_pdf(docx_bytes, stem):
    executable = settings.LIBREOFFICE_EXECUTABLE or shutil.which("soffice") or shutil.which("libreoffice")
    if not executable:
        return None, "LibreOffice PDF converter is not installed on this machine."
    with tempfile.TemporaryDirectory(prefix="monika-quotation-") as directory:
        working = Path(directory)
        source = working / f"{stem}.docx"
        source.write_bytes(docx_bytes)
        try:
            completed = subprocess.run(
                [executable, "--headless", "--convert-to", "pdf", "--outdir", str(working), str(source)],
                check=False,
                capture_output=True,
                text=True,
                timeout=settings.QUOTATION_PDF_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return None, f"PDF conversion failed: {exc}"
        target = working / f"{stem}.pdf"
        if completed.returncode or not target.exists():
            detail = (completed.stderr or completed.stdout or "converter returned no PDF").strip()
            return None, f"PDF conversion failed: {detail}"[:500]
        return target.read_bytes(), ""


def generate_documents(*, revision_id, template_id, actor):
    revision = (
        QuotationRevision.objects.select_related(
            "quotation__company", "quotation__customer", "currency"
        )
        .prefetch_related("lines")
        .get(pk=revision_id)
    )
    if not has_permission(actor, "crm.quotation.generate_document", revision.quotation):
        raise PermissionDenied("You do not have permission to generate quotation documents.")
    template_record = QuotationTemplate.objects.select_related(
        "source_document__current_version", "output_category"
    ).get(pk=template_id, company_id=revision.company_id, is_active=True)
    source_version = template_record.source_document.current_version
    if not source_version or source_version.file_extension.lower() != "docx":
        raise ValidationError("The active quotation template must be a DOCX document.")
    storage = get_storage()
    with storage.open(source_version.storage_key) as source:
        docx_template = DocxTemplate(source)
        undeclared = set(docx_template.get_undeclared_template_variables())
        forbidden = undeclared - ALLOWED_TEMPLATE_VARIABLES
        if forbidden:
            raise ValidationError(
                {"template": [f"Unsupported template variables: {', '.join(sorted(forbidden))}"]}
            )
        context = document_context(revision)
        docx_template.render(context, autoescape=True)
        rendered = BytesIO()
        docx_template.save(rendered)
    docx_bytes = rendered.getvalue()
    stem = f"{revision.quotation.quotation_number}-R{revision.revision_number}"
    docx_document = create_document(
        category=template_record.output_category,
        title=f"Quotation {stem} (Word)",
        description="Immutable generated quotation revision",
        file_object=ContentFile(docx_bytes, name=f"{stem}.docx"),
        actor=actor,
    )
    link_document(
        document=docx_document,
        entity_type="quotation",
        entity_id=revision.quotation_id,
        relationship_type="GENERATED_QUOTATION_DOCX",
        actor=actor,
    )
    pdf_bytes, pdf_error = convert_docx_to_pdf(docx_bytes, stem)
    pdf_document = None
    if pdf_bytes:
        pdf_document = create_document(
            category=template_record.output_category,
            title=f"Quotation {stem} (PDF)",
            description="Immutable generated quotation revision",
            file_object=ContentFile(pdf_bytes, name=f"{stem}.pdf"),
            actor=actor,
        )
        link_document(
            document=pdf_document,
            entity_type="quotation",
            entity_id=revision.quotation_id,
            relationship_type="GENERATED_QUOTATION_PDF",
            actor=actor,
        )
    return QuotationGeneratedDocument.objects.create(
        revision=revision,
        template=template_record,
        docx_document=docx_document,
        pdf_document=pdf_document,
        status=(
            QuotationGeneratedDocument.Status.COMPLETE
            if pdf_document
            else QuotationGeneratedDocument.Status.WORD_ONLY
        ),
        context_snapshot=context,
        pdf_error=pdf_error,
        generated_by=actor,
    )
