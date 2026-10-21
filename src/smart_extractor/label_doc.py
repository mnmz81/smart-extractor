"""Finish a draft label by hand: look at the image, type the missing fields, validate, save.

Usage: scripts/label_doc.sh DOC_ID [--dir data/public] [--source public] [--lang en]
"""

import argparse
import csv
import json
from pathlib import Path

from smart_extractor.schemas import PartialReceipt

_COLUMNS = ["id", "type", "lang", "source", "medium", "split", "private"]


def label_doc(doc_id: str, folder: Path, source: str, lang: str) -> None:
    draft = json.loads((folder / f"{doc_id}.draft.json").read_text(encoding="utf-8"))
    print(f"Open {folder / f'{doc_id}.png'} and read the receipt.")
    print("Leave a field empty if it is unreadable (blurred, cut off): it is then not scored.")
    draft["merchant_name"] = input("merchant_name: ").strip() or None
    draft["purchased_at"] = input("purchased_at (YYYY-MM-DDTHH:MM:SS): ").strip() or None
    receipt = PartialReceipt.model_validate(draft)  # raises with the failing field if wrong
    (folder / f"{doc_id}.json").write_text(receipt.model_dump_json(indent=2), encoding="utf-8")

    manifest = folder / "manifest.csv"
    is_new = not manifest.exists()
    n = int("".join(c for c in doc_id if c.isdigit()))
    with manifest.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerow(
            {
                "id": doc_id,
                "type": "receipt",
                "lang": lang,
                "source": source,
                "medium": "scanned",
                "split": "test" if n % 5 == 4 else "dev",  # same fixed 80/20 rule as synthetic
                "private": str(source == "private").lower(),
            }
        )
    print(f"saved {doc_id}.json and added it to {manifest}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("doc_id")
    parser.add_argument("--dir", type=Path, default=Path("data/public"))
    parser.add_argument("--source", choices=["public", "private"], default="public")
    parser.add_argument("--lang", choices=["he", "en"], default="en")
    args = parser.parse_args()
    label_doc(args.doc_id, args.dir, args.source, args.lang)


if __name__ == "__main__":
    main()
