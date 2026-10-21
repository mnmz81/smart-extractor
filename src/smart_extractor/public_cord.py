"""Convert CORD v2 ground truth into draft Receipt labels."""

from decimal import Decimal


def parse_price(raw: str) -> Decimal:
    """'46.000' / '-60.000' -> Decimal; rupiah has no minor unit, so separators are thousands."""
    sign = "-" if raw.strip().startswith("-") else ""
    return Decimal(sign + "".join(c for c in raw if c.isdigit()))


def _price(section: dict[str, str], key: str) -> str | None:
    return str(parse_price(section[key])) if key in section else None


def _as_list(value: object) -> list[dict[str, str]]:
    """CORD stores one entry as a dict and several as a list."""
    return [value] if isinstance(value, dict) else list(value)  # type: ignore[call-overload]


def draft_receipt(gt_parse: dict[str, object]) -> dict[str, object]:
    """Items and totals from CORD; merchant_name and purchased_at are left for label_doc.py."""
    sub = gt_parse.get("sub_total", {})
    total = gt_parse["total"]
    assert isinstance(sub, dict) and isinstance(total, dict)
    items = [
        line
        for i in _as_list(gt_parse.get("menu", []))
        for line in (i, *_as_list(i.get("sub", [])))
    ]
    return {
        "currency": "IDR",
        "line_items": [
            {
                "description": i["nm"],
                "quantity": str(parse_price(i.get("cnt", "1"))),
                "total": str(parse_price(i.get("itemsubtotal", i["price"]))),
            }
            for i in items
        ],
        "subtotal": _price(sub, "subtotal_price"),
        "tax": _price(sub, "tax_price"),
        # shortcut: no TOTAL line means the subtotal is the total (holds when there is no tax line)
        "total": _price(total, "total_price") or _price(sub, "subtotal_price"),
    }
