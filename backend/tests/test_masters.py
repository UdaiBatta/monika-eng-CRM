import pytest

from apps.core.entity_registry import entity_key
from apps.masters.models import Currency, DeliveryTerm, PaymentTerm, TaxRate, UnitOfMeasure


@pytest.mark.parametrize(
    ("instance", "expected"),
    (
        (Currency(), "currency"),
        (UnitOfMeasure(), "unit_of_measure"),
        (TaxRate(), "tax_rate"),
        (PaymentTerm(), "payment_term"),
        (DeliveryTerm(), "delivery_term"),
    ),
)
def test_master_records_are_registered_for_audit(instance, expected):
    assert entity_key(instance) == expected
