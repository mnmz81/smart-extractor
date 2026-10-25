from datetime import datetime
from decimal import Decimal

from smart_extractor.metrics import compare_date, compare_money, compare_quantity, compare_text


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
