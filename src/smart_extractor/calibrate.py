"""Check what the confidence score is worth: the review-share vs. accuracy curve on a split.

Usage: scripts/calibrate.sh [--data data/synthetic/hard] [--split dev] [--model ID]
       [--concurrency 4]

Runs the validated extractor once per document (paid), so approve large runs first.
"""

import argparse
from pathlib import Path

from smart_extractor.confidence import Signals, confidence
from smart_extractor.dataset import load_manifest
from smart_extractor.metrics import document_passed
from smart_extractor.providers import make_provider
from smart_extractor.run_eval import _DEFAULT_MODEL, evaluate

Point = tuple[float, bool]  # (confidence, document fully correct)


def threshold_curve(points: list[Point]) -> list[tuple[float, float, float]]:
    """Per threshold: (threshold, share auto-approved, accuracy of those).

    A document is auto-approved when its confidence is at least the threshold.
    The rest go to review.
    """
    curve = []
    for t in sorted({c for c, _ in points}):
        approved = [ok for c, ok in points if c >= t]
        curve.append((t, len(approved) / len(points), sum(approved) / len(approved)))
    return curve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--model")
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()
    model = args.model or _DEFAULT_MODEL
    from smart_extractor.llm import make_extractor  # imported here: llm imports run_eval

    signals: dict[str, Signals] = {}
    extractor = make_extractor("validated", model, make_provider(), signals=signals)
    results = evaluate(args.data, args.split, extractor, args.concurrency)
    rows = [r for r in load_manifest(args.data / "manifest.csv") if r.split == args.split]
    # a document with no answer has no signals: confidence 0, it always goes to review
    points = [
        (confidence(signals[r.id]) if r.id in signals else 0.0, document_passed(res))
        for r, res in zip(rows, results, strict=True)
    ]
    print("| threshold | auto-approved | accuracy of auto-approved |")
    print("|---|---|---|")
    for t, share, acc in threshold_curve(points):
        print(f"| {t:.2f} | {share:.0%} | {acc:.0%} |")


if __name__ == "__main__":
    main()
