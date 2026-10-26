"""Compare extracted values to labels and classify each field."""

from collections import Counter
from collections.abc import Callable, Iterable
from datetime import date, datetime
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Literal

from smart_extractor.normalize import normalize_text
from smart_extractor.schemas import Invoice, LineItem, PartialReceipt, Receipt

Outcome = Literal["correct", "wrong", "missing", "hallucinated", "skipped"]

_QUANTITY_TOLERANCE = Decimal("0.001")
_MIN_SIMILARITY = 0.8  # description match ratio for pairing items that differ slightly


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


def _similarity(a: LineItem, b: LineItem) -> float:
    return SequenceMatcher(
        None, normalize_text(a.description), normalize_text(b.description)
    ).ratio()


def match_line_items(
    labels: list[LineItem], extracted: list[LineItem]
) -> list[tuple[LineItem | None, LineItem | None]]:
    """Pair items by description: exact (normalized) first, then close matches.

    Leftovers pair with None (missing / hallucinated).
    """
    pool = list(extracted)
    partners: list[LineItem | None] = [None] * len(labels)
    for n, label in enumerate(labels):
        key = normalize_text(label.description)
        hit = next((i for i, e in enumerate(pool) if normalize_text(e.description) == key), None)
        if hit is not None:
            partners[n] = pool.pop(hit)
    for n, label in enumerate(labels):  # a typo or a stray "1 " prefix is not two errors
        if partners[n] is not None:
            continue
        best = max(pool, key=lambda e: _similarity(label, e), default=None)
        if best is not None and _similarity(label, best) >= _MIN_SIMILARITY:
            pool.remove(best)
            partners[n] = best
    pairs: list[tuple[LineItem | None, LineItem | None]] = list(zip(labels, partners, strict=True))
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


def _compare_field(name: str, label: Document, extracted: Document | None) -> Outcome:
    a, b = getattr(label, name), getattr(extracted, name, None)
    if isinstance(label, PartialReceipt) and a is None:  # not labeled: nothing to score against
        return "skipped"
    if name in _TEXT_FIELDS:
        return compare_text(a, b)
    if name in _MONEY_FIELDS:
        return compare_money(a, b)
    return compare_date(a, b)


def _compare_line_items(label: Document, extracted: Document | None) -> list[tuple[str, Outcome]]:
    results: list[tuple[str, Outcome]] = []
    for want, got in match_line_items(label.line_items, extracted.line_items if extracted else []):
        if got is None:
            results.append(("line_items.item", "missing"))
        elif want is None:
            results.append(("line_items.item", "hallucinated"))
        else:
            results.append(("line_items.item", "correct"))
            results.append(("line_items.quantity", compare_quantity(want.quantity, got.quantity)))
            unit_price = (
                "skipped"
                if isinstance(label, PartialReceipt) and want.unit_price is None
                else compare_money(want.unit_price, got.unit_price)
            )
            results.append(("line_items.unit_price", unit_price))
            results.append(("line_items.total", compare_money(want.total, got.total)))
    return results


def compare_document(label: Document, extracted: Document | None) -> list[tuple[str, Outcome]]:
    """One (field, outcome) per scored field, line items add one per sub-field.

    extracted=None means the extractor produced nothing: every labeled field is missing.
    """
    names = _TEXT_FIELDS | _MONEY_FIELDS | _DATE_FIELDS
    results = [(n, _compare_field(n, label, extracted)) for n in sorted(names) if hasattr(label, n)]
    return results + _compare_line_items(label, extracted)


Results = list[tuple[str, Outcome]]


def count_outcomes(documents: Iterable[Results]) -> dict[str, Counter[Outcome]]:
    """Per field, how many times each outcome occurred across all documents."""
    counts: dict[str, Counter[Outcome]] = {}
    for results in documents:
        for field, outcome in results:
            counts.setdefault(field, Counter())[outcome] += 1
    return counts


def accuracy(counts: Counter[Outcome]) -> float | None:
    """Share of scored comparisons that are correct, skipped ones excluded; None if none scored."""
    scored = counts.total() - counts["skipped"]
    return counts["correct"] / scored if scored else None


def document_passed(results: Results) -> bool:
    """A document passes only if every scored field is correct."""
    return all(outcome in ("correct", "skipped") for _, outcome in results)
