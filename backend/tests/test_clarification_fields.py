import pytest

from app.errors import ApplicationError
from app.services.clarification_fields import validate_confirmations


def test_employee_fields_are_validated_and_trimmed():
    assert validate_confirmations(
        ["vendor", "receipt_date", "total"],
        {"vendor": " Toko Sinar Jaya ", "receipt_date": "2026-01-01", "total": "75000"},
    ) == {"vendor": "Toko Sinar Jaya", "receipt_date": "2026-01-01", "total": "75000"}


@pytest.mark.parametrize("values", [
    {}, {"vendor": ""}, {"vendor": "Toko", "total": "100"},
])
def test_confirmation_requires_exact_requested_fields(values):
    with pytest.raises(ApplicationError):
        validate_confirmations(["vendor"], values)


@pytest.mark.parametrize("field,value", [
    ("receipt_date", "10 Nov 2026"), ("receipt_date", "2999-01-01"),
    ("total", "75.000,00"), ("total", "NaN"), ("total", "-1"),
    ("currency", "USD"), ("category", "unknown"),
])
def test_invalid_confirmations_are_rejected(field, value):
    with pytest.raises(ApplicationError):
        validate_confirmations([field], {field: value})
