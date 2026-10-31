"""Summarise reports/compare/<label>/<set>/*.md into reports/compare/summary.md and chart.svg.

Usage: python scripts/compare_report.py [reports/compare]
"""

import re
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "reports/compare")
rows = []
for label_dir in sorted(p for p in root.iterdir() if p.is_dir()):
    row = {"model": label_dir.name, "docs": 0, "ok": 0, "cost": 0.0, "cells": [0, 0], "retried": 0}
    for report in label_dir.glob("*/*.md"):
        t = report.read_text()
        m = re.search(r"documents: (\d+) · fully correct: (\d+)", t)
        row["docs"] += int(m[1])
        row["ok"] += int(m[2])
        row["cost"] += float(re.search(r"cost: \$([\d.]+)", t)[1])
        if r := re.search(r"(\d+) of \d+ documents retried", t):
            row["retried"] += int(r[1])
        for f in re.findall(
            r"^\| [\w.]+ \| [\d.]+% \| (\d+) \| (\d+) \| (\d+) \| (\d+) \|", t, re.M
        ):
            c, *bad = map(int, f)
            row["cells"][0] += c
            row["cells"][1] += c + sum(bad)
    rows.append(row)

lines = [
    "| model | docs fully correct | field accuracy | cost | cost / doc |",
    "|---|---|---|---|---|",
]
for r in rows:
    ok, tot = r["ok"], r["docs"]
    acc = r["cells"][0] / r["cells"][1]
    lines.append(
        f"| {r['model']} | {ok}/{tot} ({ok / tot:.0%}) | {acc:.1%} | ${r['cost']:.3f} "
        f"| ${r['cost'] / tot:.4f} |"
    )
(root / "summary.md").write_text("\n".join(lines) + "\n")

bars = "".join(
    f'<rect x="120" y="{20 + i * 40}" width="{300 * r["ok"] / r["docs"]:.0f}" '
    'height="26" fill="#4a7"/>'
    f'<text x="10" y="{38 + i * 40}" font-size="14">{r["model"]}</text>'
    f'<text x="{128 + 300 * r["ok"] / r["docs"]:.0f}" y="{38 + i * 40}" font-size="13">'
    f"{r['ok']}/{r['docs']} · ${r['cost'] / r['docs']:.4f}/doc</text>"
    for i, r in enumerate(rows)
)
h = 40 + 40 * len(rows)
(root / "chart.svg").write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="{h}">{bars}</svg>\n'
)
print("\n".join(lines))
