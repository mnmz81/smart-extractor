import csv
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator


class ManifestRow(BaseModel):
    """One labeled document in the eval set."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: Literal["invoice", "receipt"]
    lang: Literal["he", "en"]
    source: Literal["synthetic", "public", "private"]
    medium: Literal["digital", "scanned"]
    split: Literal["dev", "test"]
    private: bool

    @model_validator(mode="after")
    def private_source_is_flagged(self) -> Self:
        if self.source == "private" and not self.private:
            raise ValueError("documents with source=private must have private=true")
        return self


def load_manifest(path: Path) -> list[ManifestRow]:
    """Read manifest.csv and validate every row; ids must be unique."""
    with path.open(newline="", encoding="utf-8") as f:
        rows = [ManifestRow.model_validate(r) for r in csv.DictReader(f)]
    ids = [r.id for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate ids in manifest")
    return rows
