"""Run an extractor over a labeled dataset and write a per-field accuracy report.

Usage: scripts/run_eval.sh [--data data/synthetic] [--split dev] [--out reports]
"""

import argparse
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from smart_extractor.dataset import ManifestRow, load_manifest
from smart_extractor.metrics import (
    Document,
    Results,
    accuracy,
    compare_document,
    count_outcomes,
    document_passed,
)
from smart_extractor.schemas import Invoice, PartialReceipt

Extractor = Callable[[Path, ManifestRow], Document | None]


def empty_extractor(doc: Path, row: ManifestRow) -> None:
    """Baseline: extracts nothing, so every labeled field scores as missing."""
    return None


def load_label(data: Path, row: ManifestRow) -> Document:
    model = Invoice if row.type == "invoice" else PartialReceipt
    return model.model_validate_json((data / f"{row.id}.json").read_text(encoding="utf-8"))


def evaluate(data: Path, split: str, extractor: Extractor) -> list[Results]:
    rows = [r for r in load_manifest(data / "manifest.csv") if r.split == split]
    return [compare_document(load_label(data, r), extractor(data / f"{r.id}.pdf", r)) for r in rows]


def render_report(name: str, split: str, all_results: list[Results]) -> str:
    counts = count_outcomes(all_results)
    passed = sum(document_passed(r) for r in all_results)
    lines = [
        f"# Eval run: {name}",
        "",
        f"Split: {split} · documents: {len(all_results)} · fully correct: {passed}",
        "",
        "| field | accuracy | correct | wrong | missing | hallucinated | skipped |",
        "|---|---|---|---|---|---|---|",
    ]
    for field in sorted(counts):
        c = counts[field]
        acc = accuracy(c)
        shown = "n/a" if acc is None else f"{acc:.1%}"
        lines.append(
            f"| {field} | {shown} | {c['correct']} | {c['wrong']} | {c['missing']} "
            f"| {c['hallucinated']} | {c['skipped']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--out", type=Path, default=Path("reports"))
    args = parser.parse_args()
    name = f"baseline-{datetime.now():%Y%m%d-%H%M%S}"
    report = render_report(name, args.split, evaluate(args.data, args.split, empty_extractor))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"{name}.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
