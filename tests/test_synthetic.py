from decimal import Decimal

import pytest

from smart_extractor.synthetic import Lang, make_invoice, make_receipt


def test_same_seed_same_invoice() -> None:
    assert make_invoice(1) == make_invoice(1)


def test_different_seed_different_invoice() -> None:
    assert make_invoice(1) != make_invoice(2)


@pytest.mark.parametrize("lang", ["en", "he"])
@pytest.mark.parametrize("seed", range(20))
def test_totals_are_consistent(seed: int, lang: Lang) -> None:
    inv = make_invoice(seed, lang)
    assert inv.subtotal == sum((i.total for i in inv.line_items), Decimal("0"))
    assert inv.total == inv.subtotal + inv.tax  # type: ignore[operator]
    for item in inv.line_items:
        assert item.total == (item.quantity * item.unit_price).quantize(Decimal("0.01"))  # type: ignore[operator]


def test_language_sets_currency() -> None:
    assert make_invoice(1, "en").currency == "USD"
    assert make_invoice(1, "he").currency == "ILS"


@pytest.mark.parametrize("lang", ["en", "he"])
@pytest.mark.parametrize("seed", range(20))
def test_receipt_totals_are_consistent(seed: int, lang: Lang) -> None:
    r = make_receipt(seed, lang)
    assert r.subtotal == sum((i.total for i in r.line_items), Decimal("0"))
    assert r.total == r.subtotal + r.tax + (r.tip or Decimal("0"))  # type: ignore[operator]


def test_same_seed_same_receipt() -> None:
    assert make_receipt(1) == make_receipt(1)
