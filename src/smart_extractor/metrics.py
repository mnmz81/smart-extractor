"""Compare extracted values to labels and classify each field."""

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Literal

from smart_extractor.normalize import normalize_text

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


def compare_date(label: datetime | None, extracted: datetime | None) -> Outcome:
    # shortcut: date only, receipts often print no time; compare time too when the eval needs it
    return _outcome(label, extracted, lambda a, b: a.date() == b.date())
