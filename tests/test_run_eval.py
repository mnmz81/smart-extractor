from datetime import date
from decimal import Decimal
from pathlib import Path

from smart_extractor.run_eval import empty_extractor, evaluate, render_report
from smart_extractor.schemas import Invoice, LineItem


def _write_dataset(tmp_path: Path) -> None:
    (tmp_path / "manifest.csv").write_text(
        "id,type,lang,source,medium,split,private\n"
        "inv-1,invoice,en,synthetic,digital,dev,false\n"
        "inv-2,invoice,en,synthetic,digital,test,false\n",
        encoding="utf-8",
    )
    label = Invoice(
        invoice_number="INV-1",
        issue_date=date(2024, 3, 1),
        vendor_name="Acme",
        currency="USD",
        line_items=[LineItem(description="Apple", total=Decimal("1"))],
        total=Decimal("1"),
    )
    for doc_id in ("inv-1", "inv-2"):
        (tmp_path / f"{doc_id}.json").write_text(label.model_dump_json(), encoding="utf-8")


def test_baseline_scores_zero_on_dev_split(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    results = evaluate(tmp_path, "dev", empty_extractor)
    assert len(results) == 1  # the test-split row is not run
    outcomes = dict(results[0])
    assert outcomes["vendor_name"] == "missing"
    assert outcomes["due_date"] == "correct"  # absent in label and extraction


def test_report_lists_fields(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    report = render_report("t", "dev", evaluate(tmp_path, "dev", empty_extractor))
    assert "documents: 1 · fully correct: 0" in report
    assert "| vendor_name | 0.0% |" in report
