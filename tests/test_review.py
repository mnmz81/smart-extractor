from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from smart_extractor.review import connect, enqueue, pending, resolve
from smart_extractor.schemas import Invoice, LineItem


def _invoice(vendor: str = "Acme") -> Invoice:
    return Invoice(
        invoice_number="INV-1",
        issue_date=date(2024, 3, 1),
        vendor_name=vendor,
        currency="USD",
        line_items=[LineItem(description="Apple", total=Decimal("1"))],
        total=Decimal("1"),
    )


def test_pending_lists_least_confident_first(tmp_path: Path) -> None:
    conn = connect(tmp_path / "q.sqlite")
    enqueue(conn, "a", _invoice(), 0.9)
    enqueue(conn, "b", _invoice(), 0.3)
    assert [r["doc_id"] for r in pending(conn)] == ["b", "a"]


def test_resolved_items_leave_the_queue(tmp_path: Path) -> None:
    conn = connect(tmp_path / "q.sqlite")
    first = enqueue(conn, "a", _invoice(), 0.5)
    second = enqueue(conn, "b", _invoice(), 0.6)
    resolve(conn, first)
    resolve(conn, second, corrected=_invoice("Fixed Ltd"))
    assert pending(conn) == []
    row = conn.execute("SELECT status, corrected FROM review WHERE id = ?", (second,)).fetchone()
    assert row["status"] == "corrected"
    assert "Fixed Ltd" in row["corrected"]


def test_resolving_twice_or_unknown_id_fails(tmp_path: Path) -> None:
    conn = connect(tmp_path / "q.sqlite")
    item = enqueue(conn, "a", _invoice(), 0.5)
    resolve(conn, item)
    with pytest.raises(LookupError):
        resolve(conn, item)
    with pytest.raises(LookupError):
        resolve(conn, 999)
