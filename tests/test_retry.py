from datetime import date
from decimal import Decimal

from smart_extractor.metrics import Document
from smart_extractor.retry import extract_with_retry
from smart_extractor.schemas import Invoice, LineItem


def _invoice(total: str) -> Invoice:
    return Invoice(
        invoice_number="INV-1",
        issue_date=date(2024, 3, 1),
        vendor_name="Acme",
        currency="USD",
        line_items=[LineItem(description="Apple", total=Decimal("10"))],
        subtotal=Decimal("10"),
        tax=Decimal("1"),
        total=Decimal(total),
    )


def test_valid_first_answer_is_not_retried() -> None:
    result = extract_with_retry(lambda previous, errors: _invoice("11"))
    assert result.retries == 0
    assert result.errors == []


def test_errors_are_sent_back_and_second_answer_passes() -> None:
    seen: list[list[str]] = []
    answers = iter([_invoice("99"), _invoice("11")])

    def attempt(previous: Document | None, errors: list[str]) -> Document | None:
        seen.append(errors)
        return next(answers)

    result = extract_with_retry(attempt)
    assert result.retries == 1
    assert result.errors == []
    assert seen[0] == [] and "total is 99" in seen[1][0]


def test_gives_up_after_max_retries_and_keeps_last_answer() -> None:
    calls: list[int] = []

    def attempt(previous: Document | None, errors: list[str]) -> Document | None:
        calls.append(1)
        return _invoice("99")

    result = extract_with_retry(attempt, max_retries=2)
    assert len(calls) == 3
    assert result.retries == 2
    assert result.errors  # still broken
    assert result.document is not None


def test_none_answer_stops_without_retry() -> None:
    result = extract_with_retry(lambda previous, errors: None)
    assert result.document is None
    assert result.retries == 0
