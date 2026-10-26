from pathlib import Path

import pytest
from pydantic import ValidationError

from smart_extractor.dataset import ManifestRow, load_manifest

HEADER = "id,type,lang,source,medium,split,private\n"


def _row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "inv-001",
        "type": "invoice",
        "lang": "en",
        "source": "synthetic",
        "medium": "digital",
        "split": "dev",
        "private": False,
    }
    return {**base, **overrides}


def test_row_valid() -> None:
    assert ManifestRow.model_validate(_row()).split == "dev"


def test_row_rejects_unknown_split() -> None:
    with pytest.raises(ValidationError):
        ManifestRow.model_validate(_row(split="train"))


def test_private_source_must_be_flagged() -> None:
    with pytest.raises(ValidationError):
        ManifestRow.model_validate(_row(source="private", private=False))


def test_load_manifest_parses_csv_bool(tmp_path: Path) -> None:
    f = tmp_path / "manifest.csv"
    f.write_text(HEADER + "inv-001,invoice,en,private,scanned,test,true\n", encoding="utf-8")
    rows = load_manifest(f)
    assert rows[0].private is True
    assert rows[0].lang == "en"


def test_load_manifest_rejects_duplicate_ids(tmp_path: Path) -> None:
    f = tmp_path / "manifest.csv"
    line = "inv-001,invoice,en,synthetic,digital,dev,false\n"
    f.write_text(HEADER + line + line, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_manifest(f)
