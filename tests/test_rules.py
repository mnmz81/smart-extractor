from datetime import date
from decimal import Decimal

from smart_extractor.rules import check_document
from smart_extractor.schemas import Invoice, LineItem

TODAY = date(2026, 10, 26)


def _invoice(**overrides: object) -> Invoice:
    base: dict[str, object] = {
        "invoice_number": "INV-1",
        "issue_date": date(2026, 10, 1),
        "due_date": date(2026, 10, 31),
        "vendor_name": "Acme",
        "currency": "USD",
        "line_items": [
            LineItem(
                description="Apple",
                quantity=Decimal("2"),
                unit_price=Decimal("5"),
                total=Decimal("10"),
            )
        ],
        "subtotal": Decimal("10"),
        "tax": Decimal("0.80"),
        "total": Decimal("10.80"),
    }
    return Invoice(**{**base, **overrides})


def test_consistent_invoice_passes() -> None:
    assert check_document(_invoice(), TODAY) == []


def test_totals_that_do_not_add_up_are_reported() -> None:
    errors = check_document(_invoice(total=Decimal("12.00")), TODAY)
    assert len(errors) == 1
    assert "total is 12.00" in errors[0]


def test_one_cent_rounding_is_tolerated() -> None:
    assert check_document(_invoice(total=Decimal("10.81")), TODAY) == []


def test_line_math_and_subtotal_are_checked() -> None:
    bad = LineItem(
        description="Pear", quantity=Decimal("3"), unit_price=Decimal("5"), total=Decimal("10")
    )
    errors = check_document(_invoice(line_items=[bad]), TODAY)
    assert any("Pear" in e for e in errors)


def test_dates_are_checked() -> None:
    errors = check_document(
        _invoice(issue_date=date(2026, 11, 1), due_date=date(2026, 10, 1)), TODAY
    )
    assert any("before issue_date" in e for e in errors)
    assert any("in the future" in e for e in errors)


def test_lowercase_currency_is_reported() -> None:
    assert any("currency" in e for e in check_document(_invoice(currency="usd"), TODAY))


def test_tax_inclusive_total_is_accepted() -> None:
    assert check_document(_invoice(total=Decimal("10.00")), TODAY) == []
