"""Compare extracted values to labels and classify each field."""

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from smart_extractor.normalize import normalize_text
from smart_extractor.schemas import Invoice, LineItem, PartialReceipt, Receipt

Outcome = Literal["correct", "wrong", "missing", "hallucinated", "skipped"]

_QUANTITY_TOLERANCE = Decimal("0.001")


def _outcome[T](label: T | None, extracted: T | None, equal: Callable[[T, T], bool]) -> Outcome:
    """None means 'absent': absent in both is correct, a value where none belongs is invented."""
    if label is None:
        return "correct" if extracted is None else "hallucinated"
    if extracted is None:
        return "missing"
    return "correct" if equal(label, extracted) else "wrong"


def compare_text(label: str | None, extracted: str | None) -> Outcome:
    return _outcome(label, extracted, lambda a, b: normalize_text(a) == normalize_text(b))


def compare_money(label: Decimal | None, extracted: Decimal | None) -> Outcome:
    return _outcome(label, extracted, lambda a, b: a == b)


def compare_quantity(label: Decimal | None, extracted: Decimal | None) -> Outcome:
    return _outcome(label, extracted, lambda a, b: abs(a - b) <= _QUANTITY_TOLERANCE)


def _day(value: date) -> date:
    return value.date() if isinstance(value, datetime) else value  # datetime is a date subclass


def compare_date(label: date | None, extracted: date | None) -> Outcome:
    # shortcut: date only, receipts often print no time; compare time too when the eval needs it
    return _outcome(label, extracted, lambda a, b: _day(a) == _day(b))


def match_line_items(
    labels: list[LineItem], extracted: list[LineItem]
) -> list[tuple[LineItem | None, LineItem | None]]:
    """Pair items by normalized description; leftovers pair with None (missing / hallucinated)."""
    # shortcut: exact description match only, so a typo becomes missing + hallucinated;
    # add fuzzy matching if the eval shows it
    pool = list(extracted)
    pairs: list[tuple[LineItem | None, LineItem | None]] = []
    for label in labels:
        key = normalize_text(label.description)
        hit = next((i for i, e in enumerate(pool) if normalize_text(e.description) == key), None)
        pairs.append((label, pool.pop(hit) if hit is not None else None))
    pairs.extend((None, leftover) for leftover in pool)
    return pairs


Document = Invoice | Receipt | PartialReceipt

_TEXT_FIELDS = {
    "invoice_number",
    "vendor_name",
    "customer_name",
    "merchant_name",
    "currency",
    "payment_method",
}
_MONEY_FIELDS = {"subtotal", "tax", "tip", "total"}
_DATE_FIELDS = {"issue_date", "due_date", "purchased_at"}
# A PartialReceipt label is None here when the source is unreadable: nothing to score against.
_UNREADABLE_IN_PARTIAL = {"merchant_name", "purchased_at"}


def _compare_field(name: str, label: Document, extracted: Document) -> Outcome:
    a, b = getattr(label, name), getattr(extracted, name, None)
    if isinstance(label, PartialReceipt) and name in _UNREADABLE_IN_PARTIAL and a is None:
        return "skipped"
    if name in _TEXT_FIELDS:
        return compare_text(a, b)
    if name in _MONEY_FIELDS:
        return compare_money(a, b)
    return compare_date(a, b)


def _compare_line_items(label: Document, extracted: Document) -> list[tuple[str, Outcome]]:
    results: list[tuple[str, Outcome]] = []
    for want, got in match_line_items(label.line_items, extracted.line_items):
        if got is None:
            results.append(("line_items.item", "missing"))
        elif want is None:
            results.append(("line_items.item", "hallucinated"))
        else:
            results.append(("line_items.quantity", compare_quantity(want.quantity, got.quantity)))
            results.append(
                ("line_items.unit_price", compare_money(want.unit_price, got.unit_price))
            )
            results.append(("line_items.total", compare_money(want.total, got.total)))
    return results


def compare_document(label: Document, extracted: Document) -> list[tuple[str, Outcome]]:
    """One (field, outcome) per scored field; line items add one entry per matched sub-field."""
    names = _TEXT_FIELDS | _MONEY_FIELDS | _DATE_FIELDS
    results = [(n, _compare_field(n, label, extracted)) for n in sorted(names) if hasattr(label, n)]
    return results + _compare_line_items(label, extracted)
