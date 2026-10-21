import json
from pathlib import Path

import pytest

from smart_extractor.dataset import load_manifest
from smart_extractor.label_doc import label_doc


def test_label_doc_writes_label_and_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = {
        "currency": "IDR",
        "line_items": [{"description": "Tea", "quantity": "1", "total": "5000"}],
        "subtotal": None,
        "tax": None,
        "total": "5000",
    }
    (tmp_path / "cord-0004.draft.json").write_text(json.dumps(draft), encoding="utf-8")
    answers = iter(["Warung Test", "2024-03-01T12:30:00"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    label_doc("cord-0004", tmp_path, "public", "en")

    saved = json.loads((tmp_path / "cord-0004.json").read_text(encoding="utf-8"))
    assert saved["merchant_name"] == "Warung Test"
    row = load_manifest(tmp_path / "manifest.csv")[0]
    assert (row.id, row.source, row.split, row.private) == ("cord-0004", "public", "test", False)


def test_label_doc_allows_unreadable_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = {
        "currency": "IDR",
        "line_items": [{"description": "Tea", "quantity": "1", "total": "5000"}],
        "total": "5000",
    }
    (tmp_path / "cord-0001.draft.json").write_text(json.dumps(draft), encoding="utf-8")
    answers = iter(["", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    label_doc("cord-0001", tmp_path, "public", "en")

    saved = json.loads((tmp_path / "cord-0001.json").read_text(encoding="utf-8"))
    assert saved["merchant_name"] is None and saved["purchased_at"] is None
