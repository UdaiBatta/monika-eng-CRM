from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import close_old_connections, connections

from apps.numbering.models import DocumentSequence
from apps.numbering.services import allocate_number, financial_year_label, preview_number


@pytest.fixture
def sequence(company):
    return DocumentSequence.objects.create(
        company=company,
        code="ENQ",
        financial_year="2026-27",
        template="{company}/{code}/{fy}/{number}",
        next_number=1,
        padding=4,
    )


@pytest.mark.django_db
def test_preview_does_not_consume_number(sequence):
    assert preview_number(sequence) == "METEST/ENQ/2026-27/0001"
    sequence.refresh_from_db()
    assert sequence.next_number == 1


@pytest.mark.django_db
def test_financial_year_uses_company_start_month(company):
    from datetime import date

    assert financial_year_label(company, date(2026, 3, 31)) == "2025-26"
    assert financial_year_label(company, date(2026, 4, 1)) == "2026-27"


@pytest.mark.django_db(transaction=True)
def test_concurrent_allocations_are_unique_and_gap_free(sequence):
    def allocate(_):
        close_old_connections()
        try:
            return allocate_number(sequence.pk)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(allocate, range(16)))

    assert len(values) == len(set(values)) == 16
    assert sorted(int(value.rsplit("/", 1)[1]) for value in values) == list(range(1, 17))
    sequence.refresh_from_db()
    assert sequence.next_number == 17
