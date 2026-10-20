#!/bin/sh
# Generate the synthetic eval set (PDFs, label JSONs, manifest.csv).
# Usage: scripts/generate_dataset.sh [--out data/synthetic] [--n 40] [--seed 0]
cd "$(dirname "$0")/.." && exec scripts/uv.sh run python -m smart_extractor.generate "$@"
