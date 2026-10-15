from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from smart_extractor.schemas import Invoice, LineItem, Receipt


def _item() -> dict[str, Any]:
    return {"description": "Widget", "total": "5.00"}


def _invoice() -> dict[str, Any]:
    return {
        "invoice_number": "INV-1",
        "issue_date": "2026-01-02",
        "vendor_name": "Acme",
        "currency": "USD",
        "line_items": [_item()],
        "total": "5.00",
    }


def _receipt() -> dict[str, Any]:
    return {
        "merchant_name": "Cafe",
        "purchased_at": "2026-01-02T09:30:00",
        "currency": "USD",
        "line_items": [_item()],
        "total": "5.00",
    }


def test_line_item_defaults() -> None:
    item = LineItem.model_validate(_item())
    assert item.quantity == Decimal("1")
    assert item.unit_price is None


def test_line_item_rejects_zero_quantity() -> None:
    with pytest.raises(ValidationError):
        LineItem.model_validate({**_item(), "quantity": 0})


def test_money_is_decimal_not_float() -> None:
    invoice = Invoice.model_validate({**_invoice(), "total": "0.1"})
    assert invoice.total == Decimal("0.1")
    assert isinstance(invoice.total, Decimal)


def test_invoice_parses_and_converts_types() -> None:
    invoice = Invoice.model_validate(_invoice())
    assert invoice.issue_date == date(2026, 1, 2)
    assert invoice.due_date is None


def test_invoice_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        Invoice.model_validate({**_invoice(), "discount": 2})


def test_invoice_requires_line_items() -> None:
    with pytest.raises(ValidationError):
        Invoice.model_validate({**_invoice(), "line_items": []})


def test_invoice_rejects_bad_currency_code() -> None:
    with pytest.raises(ValidationError):
        Invoice.model_validate({**_invoice(), "currency": "US"})


def test_invoice_rejects_negative_total() -> None:
    with pytest.raises(ValidationError):
        Invoice.model_validate({**_invoice(), "total": "-1"})


def test_receipt_parses_datetime() -> None:
    receipt = Receipt.model_validate(_receipt())
    assert receipt.purchased_at == datetime(2026, 1, 2, 9, 30)
    assert receipt.tip is None


def test_receipt_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        Receipt.model_validate({**_receipt(), "invoice_number": "X"})


def test_receipt_requires_merchant() -> None:
    data = _receipt()
    del data["merchant_name"]
    with pytest.raises(ValidationError):
        Receipt.model_validate(data)
