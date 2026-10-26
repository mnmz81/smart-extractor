"""Build the synthetic eval set: PDFs, label JSONs and manifest.csv.

Usage: scripts/generate_dataset.sh [--out data/synthetic] [--n 40] [--seed 0] [--strength 1.0]
"""

import argparse
import csv
import tempfile
from pathlib import Path

from smart_extractor.degrade_scan import png_to_scanned_pdf
from smart_extractor.render import (
    html_to_pdf,
    html_to_png,
    render_invoice_html,
    render_receipt_html,
)
from smart_extractor.schemas import Invoice, Receipt
from smart_extractor.synthetic import Lang, make_invoice, make_receipt

_COLUMNS = ["id", "type", "lang", "source", "medium", "split", "private"]


def generate_dataset(out: Path, n: int, seed: int, strength: float = 1.0) -> None:
    """Document i cycles type and medium, so every combination appears evenly."""
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for i in range(n):
        doc_type = "invoice" if i % 2 == 0 else "receipt"
        lang: Lang = "en"
        medium = "digital" if (i // 4) % 2 == 0 else "scanned"
        doc_id = f"{doc_type[:3]}-{i:04d}"
        doc_seed = seed * 100_000 + i

        label: Invoice | Receipt
        if doc_type == "invoice":
            invoice = make_invoice(doc_seed, lang)
            label, html = invoice, render_invoice_html(invoice, lang)
        else:
            receipt = make_receipt(doc_seed, lang)
            label, html = receipt, render_receipt_html(receipt, lang)

        pdf = out / f"{doc_id}.pdf"
        if medium == "digital":
            html_to_pdf(html, pdf)
        else:
            with tempfile.TemporaryDirectory() as tmp:
                png = Path(tmp) / "page.png"
                html_to_png(html, png)
                png_to_scanned_pdf(png, pdf, doc_seed, strength)
        (out / f"{doc_id}.json").write_text(label.model_dump_json(indent=2), encoding="utf-8")

        rows.append(
            {
                "id": doc_id,
                "type": doc_type,
                "lang": lang,
                "source": "synthetic",
                "medium": medium,
                "split": "test" if i % 5 == 4 else "dev",  # fixed 80/20, never random
                "private": "false",
            }
        )

    with (out / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--n", type=int, default=40)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--strength", type=float, default=1.0, help="scan damage, 1.0 = mild")
    args = parser.parse_args()
    generate_dataset(args.out, args.n, args.seed, args.strength)
    print(f"wrote {args.n} documents to {args.out}")


if __name__ == "__main__":
    main()
