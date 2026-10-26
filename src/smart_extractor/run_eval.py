"""Run an extractor over a labeled dataset and write a per-field accuracy report.

Usage: scripts/run_eval.sh [--data data/synthetic] [--split dev] [--out reports]
       [--extractor baseline|naive|structured|validated|vision]
       [--provider claude|gemini] [--model ID]

naive, structured, validated and vision call a paid LLM API once per digital document.
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
from smart_extractor.pricing import cost_usd
from smart_extractor.providers import Usage, make_provider
from smart_extractor.retry import RetryStats
from smart_extractor.schemas import Invoice, PartialReceipt, Receipt

_DEFAULT_MODELS = {"claude": "claude-haiku-5-5", "gemini": "gemini-3.8-flash"}

Extractor = Callable[[Path, ManifestRow], Document | None]


def empty_extractor(doc: Path, row: ManifestRow) -> None:
    """Baseline: extracts nothing, so every labeled field scores as missing."""
    return None


def load_label(data: Path, row: ManifestRow) -> Document:
    """Own labels are scored strictly. Public ones are only partly labeled (None = not labeled)."""
    raw = (data / f"{row.id}.json").read_text(encoding="utf-8")
    if row.type == "invoice":
        return Invoice.model_validate_json(raw)
    model = PartialReceipt if row.source == "public" else Receipt
    return model.model_validate_json(raw)


def _doc_path(data: Path, row: ManifestRow) -> Path:
    """Synthetic documents are PDFs, public ones are page photos."""
    png = data / f"{row.id}.png"
    return png if png.exists() else data / f"{row.id}.pdf"


def evaluate(data: Path, split: str, extractor: Extractor) -> list[Results]:
    rows = [r for r in load_manifest(data / "manifest.csv") if r.split == split]
    return [compare_document(load_label(data, r), extractor(_doc_path(data, r), r)) for r in rows]


def render_report(
    name: str,
    split: str,
    all_results: list[Results],
    model: str | None = None,
    usage: Usage | None = None,
    stats: RetryStats | None = None,
) -> str:
    counts = count_outcomes(all_results)
    passed = sum(document_passed(r) for r in all_results)
    lines = [
        f"# Eval run: {name}",
        "",
        f"Split: {split} · documents: {len(all_results)} · fully correct: {passed}",
    ]
    if usage is not None and model is not None:
        cost = cost_usd(model, usage)
        shown = "unknown price" if cost is None else f"${cost:.4f}"
        lines.append(
            f"Model: {model} · API calls: {usage.calls} · tokens in/out: "
            f"{usage.input_tokens}/{usage.output_tokens} · cost: {shown}"
        )
    if stats is not None and stats.documents:
        lines.append(
            f"Retries: {stats.retries} extra calls, {stats.retried} of {stats.documents} documents "
            f"retried, {stats.unresolved} still broken at the end"
        )
    lines += [
        "",
        "| field | accuracy | correct | wrong | missing | hallucinated | skipped |",
        "|---|---|---|---|---|---|---|",
    ]
    for field in sorted(counts):
        c = counts[field]
        acc = accuracy(c)
        shown_acc = "n/a" if acc is None else f"{acc:.1%}"
        lines.append(
            f"| {field} | {shown_acc} | {c['correct']} | {c['wrong']} | {c['missing']} "
            f"| {c['hallucinated']} | {c['skipped']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--out", type=Path, default=Path("reports"))
    parser.add_argument(
        "--extractor",
        choices=["baseline", "naive", "structured", "validated", "vision"],
        default="baseline",
    )
    parser.add_argument("--provider", choices=["claude", "gemini"], default="claude")
    parser.add_argument("--model", help="default: haiku for claude, gemini-3.8-flash for gemini")
    args = parser.parse_args()
    model = args.model or _DEFAULT_MODELS[args.provider]
    extractor: Extractor = empty_extractor
    usage: Usage | None = None
    stats = RetryStats()
    if args.extractor != "baseline":
        from smart_extractor.llm import make_extractor  # imported here: llm imports this module

        provider = make_provider(args.provider)
        usage = provider.usage
        extractor = make_extractor(args.extractor, model, provider, stats)
    name = f"{args.extractor}-{datetime.now():%Y%m%d-%H%M%S}"
    results = evaluate(args.data, args.split, extractor)
    report = render_report(name, args.split, results, model, usage, stats)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"{name}.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
