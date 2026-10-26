from collections import Counter
from datetime import date, datetime
from decimal import Decimal

from smart_extractor.metrics import (
    Outcome,
    accuracy,
    compare_date,
    compare_document,
    compare_money,
    compare_quantity,
    compare_text,
    count_outcomes,
    document_passed,
    match_line_items,
)
from smart_extractor.schemas import Invoice, LineItem, PartialReceipt, Receipt


def test_outcome_classification() -> None:
    assert compare_text("Acme", "acme ") == "correct"
    assert compare_text("Acme", "Beta") == "wrong"
    assert compare_text("Acme", None) == "missing"
    assert compare_text(None, "Acme") == "hallucinated"
    assert compare_text(None, None) == "correct"


def test_money_is_exact() -> None:
    assert compare_money(Decimal("10.00"), Decimal("10")) == "correct"
    assert compare_money(Decimal("10.00"), Decimal("10.01")) == "wrong"


def test_quantity_has_tolerance() -> None:
    assert compare_quantity(Decimal("1.5"), Decimal("1.5004")) == "correct"
    assert compare_quantity(Decimal("1.5"), Decimal("2")) == "wrong"


def test_date_ignores_time() -> None:
    assert compare_date(datetime(2024, 3, 1, 9, 0), datetime(2024, 3, 1, 18, 30)) == "correct"
    assert compare_date(datetime(2024, 3, 1), datetime(2024, 3, 2)) == "wrong"


def test_date_accepts_plain_dates() -> None:
    assert compare_date(date(2024, 3, 1), date(2024, 3, 1)) == "correct"
    assert compare_date(date(2024, 3, 1), datetime(2024, 3, 1, 9, 0)) == "correct"


def _item(description: str) -> LineItem:
    return LineItem(description=description, total=Decimal("1"))


def test_match_line_items_ignores_order_and_flags_leftovers() -> None:
    a, b, c = _item("Apple"), _item("Bread"), _item("Cola")
    pairs = match_line_items([a, b], [_item("bread "), c])
    assert [(x and x.description, y and y.description) for x, y in pairs] == [
        ("Apple", None),
        ("Bread", "bread "),
        (None, "Cola"),
    ]


def _invoice(**overrides: object) -> Invoice:
    base: dict[str, object] = {
        "invoice_number": "INV-1",
        "issue_date": date(2024, 3, 1),
        "vendor_name": "Acme",
        "currency": "USD",
        "line_items": [_item("Apple"), _item("Bread")],
        "total": Decimal("2"),
    }
    return Invoice(**{**base, **overrides})


def test_compare_document_classifies_fields_and_items() -> None:
    label = _invoice(customer_name="Beta")
    extracted = _invoice(vendor_name="Other", line_items=[_item("Apple"), _item("Cola")])
    outcomes = dict(compare_document(label, extracted))
    assert outcomes["invoice_number"] == "correct"
    assert outcomes["vendor_name"] == "wrong"
    assert outcomes["customer_name"] == "missing"
    assert outcomes["due_date"] == "correct"  # absent in both
    assert ("line_items.item", "missing") in compare_document(label, extracted)
    assert ("line_items.item", "hallucinated") in compare_document(label, extracted)


def test_partial_receipt_skips_unreadable_fields() -> None:
    items = [_item("Apple")]
    label = PartialReceipt(currency="USD", line_items=items, total=Decimal("1"))
    extracted = Receipt(
        currency="USD",
        line_items=items,
        total=Decimal("1"),
        merchant_name="Shop",
        purchased_at=datetime(2024, 3, 1, 9, 0),
    )
    outcomes = dict(compare_document(label, extracted))
    assert outcomes["merchant_name"] == "skipped"
    assert outcomes["purchased_at"] == "skipped"
    assert outcomes["total"] == "correct"


def test_aggregation_ignores_skipped() -> None:
    docs: list[list[tuple[str, Outcome]]] = [
        [("total", "correct"), ("merchant_name", "skipped")],
        [("total", "wrong"), ("merchant_name", "correct")],
    ]
    counts = count_outcomes(docs)
    assert accuracy(counts["total"]) == 0.5
    assert accuracy(counts["merchant_name"]) == 1.0  # the skipped one is not scored
    assert accuracy(Counter({"skipped": 2})) is None
    assert document_passed(docs[0])
    assert not document_passed(docs[1])
