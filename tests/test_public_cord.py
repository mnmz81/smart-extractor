from decimal import Decimal
from typing import cast

import pytest

from smart_extractor.public_cord import draft_receipt, parse_price


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("46000", 46000), ("46.000", 46000), ("1,500", 1500), ("-60.000", -60000)],
)
def test_parse_price(raw: str, expected: int) -> None:
    assert parse_price(raw) == Decimal(expected)


def test_draft_receipt_includes_sub_items_and_falls_back_to_subtotal() -> None:
    gt = {
        "menu": {"nm": "Latte", "price": "45,455", "sub": [{"nm": "Oat milk", "price": "0"}]},
        "sub_total": {"subtotal_price": "45,455"},
        "total": {"cashprice": "50000"},
    }
    draft = draft_receipt(gt)
    items = cast(list[dict[str, str]], draft["line_items"])
    assert [i["description"] for i in items] == ["Latte", "Oat milk"]
    assert draft["total"] == "45455"
