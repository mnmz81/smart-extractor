"""Turn a human-reviewed document into a new labeled dataset entry.

Only reviewed documents come back: an auto-approved one was never checked by a person.
They always join the dev split, so the frozen test split keeps the numbers comparable.
"""

import csv
import shutil
import threading
from pathlib import Path

from pydantic import ValidationError

from smart_extractor.metrics import Document
from smart_extractor.schemas import Invoice, Receipt

_COLUMNS = ["id", "type", "lang", "source", "medium", "split", "private"]
_lock = threading.Lock()  # two reviews at once must not interleave the manifest header and rows


def parse_document(raw: str) -> Document:
    """A stored extraction does not say which schema it fits: try invoice, then receipt."""
    try:
        return Invoice.model_validate_json(raw)
    except ValidationError:
        return Receipt.model_validate_json(raw)


def add_label(folder: Path, doc_id: str, doc: Document, upload: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(upload, folder / f"{doc_id}{upload.suffix}")
    (folder / f"{doc_id}.json").write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    manifest = folder / "manifest.csv"
    with _lock, manifest.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_COLUMNS)
        if manifest.stat().st_size == 0:
            writer.writeheader()
        writer.writerow(
            {
                "id": doc_id,
                "type": "invoice" if isinstance(doc, Invoice) else "receipt",
                "lang": "en",
                "source": "private",
                "medium": "digital" if upload.suffix == ".pdf" else "scanned",
                "split": "dev",
                "private": "true",
            }
        )
