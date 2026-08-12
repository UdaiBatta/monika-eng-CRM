from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import DocumentSequence


def financial_year_label(company, value=None):
    value = value or date.today()
    settings = getattr(company, "settings", None)
    start_month = settings.financial_year_start_month if settings else 4
    start_year = value.year if value.month >= start_month else value.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def _render(sequence, number):
    return sequence.template.format(
        company=sequence.company.code,
        branch=sequence.branch.code if sequence.branch else "",
        code=sequence.code,
        fy=sequence.financial_year,
        year=sequence.financial_year[:4],
        number=str(number).zfill(sequence.padding),
    )


def preview_number(sequence):
    return _render(sequence, sequence.next_number)


@transaction.atomic
def allocate_number(sequence_id):
    sequence = DocumentSequence.objects.select_for_update().get(pk=sequence_id, is_active=True)
    allocated = _render(sequence, sequence.next_number)
    sequence.next_number += 1
    sequence.save(update_fields=["next_number", "updated_at"])
    return allocated


def allocate_company_number(*, company, code, branch=None, on_date=None):
    """Allocate from the active company/FY sequence for a business document type."""
    financial_year = financial_year_label(company, on_date)
    try:
        sequence = DocumentSequence.objects.only("id").get(
            company=company,
            branch=branch,
            code=code,
            financial_year=financial_year,
            is_active=True,
        )
    except DocumentSequence.DoesNotExist as exc:
        raise ValidationError(
            {"numbering": f"Configure an active {code} sequence for {financial_year}."}
        ) from exc
    return allocate_number(sequence.pk)
