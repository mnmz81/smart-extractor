from pathlib import Path

from smart_extractor.dataset import load_manifest
from smart_extractor.generate import generate_dataset
from smart_extractor.schemas import Invoice, Receipt


def test_generate_dataset_is_consistent(tmp_path: Path) -> None:
    generate_dataset(tmp_path, n=10, seed=0)
    rows = load_manifest(tmp_path / "manifest.csv")
    assert len(rows) == 10
    assert {r.medium for r in rows} == {"digital", "scanned"}
    assert {r.lang for r in rows} == {"en"}
    assert {r.type for r in rows} == {"invoice", "receipt"}
    assert sum(r.split == "test" for r in rows) == 2
    for r in rows:
        assert (tmp_path / f"{r.id}.pdf").read_bytes().startswith(b"%PDF")
        label = (tmp_path / f"{r.id}.json").read_text(encoding="utf-8")
        (Invoice if r.type == "invoice" else Receipt).model_validate_json(label)
