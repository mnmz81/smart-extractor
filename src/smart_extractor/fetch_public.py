"""Download CORD v2 (CC-BY-4.0, https://huggingface.co/datasets/naver-clova-ix/cord-v2) samples.

Writes cord-NNNN.png and cord-NNNN.draft.json (items and totals; merchant and date missing)
to the output folder. Finish each label with scripts/label_doc.sh.

Usage: scripts/fetch_public.sh [--out data/public] [--n 10]
"""

import argparse
import json
import urllib.request
from decimal import InvalidOperation
from pathlib import Path

import pyarrow.parquet as pq

from smart_extractor.public_cord import draft_receipt

_URL = "https://huggingface.co/api/datasets/naver-clova-ix/cord-v2/parquet/default/test/0.parquet"


def fetch_public(out: Path, n: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    parquet = out / "cord_test.parquet"
    if not parquet.exists():
        urllib.request.urlretrieve(_URL, parquet)
    table = pq.read_table(parquet)

    written = 0
    for i in range(table.num_rows):
        if written == n:
            break
        gt = json.loads(table["ground_truth"][i].as_py())["gt_parse"]
        try:
            draft = draft_receipt(gt)
        except (KeyError, AttributeError, InvalidOperation):
            continue  # shortcut: skip odd CORD layouts, we only need a handful
        doc_id = f"cord-{i:04d}"
        (out / f"{doc_id}.png").write_bytes(table["image"][i].as_py()["bytes"])
        (out / f"{doc_id}.draft.json").write_text(json.dumps(draft, indent=2), encoding="utf-8")
        written += 1
    print(f"wrote {written} drafts to {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/public"))
    parser.add_argument("--n", type=int, default=10)
    args = parser.parse_args()
    fetch_public(args.out, args.n)


if __name__ == "__main__":
    main()
