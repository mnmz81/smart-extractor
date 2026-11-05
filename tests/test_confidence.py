from datetime import date
from decimal import Decimal

from smart_extractor.confidence import Signals, confidence, missing_share
from smart_extractor.schemas import Invoice, LineItem


def test_clean_extraction_is_fully_confident() -> None:
    assert confidence(Signals(retries=0, errors=0, vision=False, missing=0)) == 1.0


def test_each_signal_lowers_confidence() -> None:
    clean = Signals(0, 0, False, 0)
    assert confidence(Signals(1, 0, False, 0)) < confidence(clean)
    assert confidence(Signals(0, 1, False, 0)) < confidence(Signals(1, 0, False, 0))
    assert confidence(Signals(0, 0, True, 0)) < confidence(clean)
    assert confidence(Signals(0, 0, False, 0.5)) < confidence(clean)


def test_confidence_never_goes_below_zero() -> None:
    assert confidence(Signals(3, 5, True, 1.0)) == 0.0


def test_missing_share_counts_empty_top_level_fields() -> None:
    invoice = Invoice(
        invoice_number="INV-1",
        issue_date=date(2024, 3, 1),
        vendor_name="Acme",
        currency="USD",
        line_items=[LineItem(description="Apple", total=Decimal("1"))],
        total=Decimal("1"),
    )
    assert 0 < missing_share(invoice) < 1
