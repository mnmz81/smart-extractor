#!/bin/sh
# Run the eval harness and write reports/<run>.md.
# Usage: scripts/run_eval.sh [--data data/synthetic] [--split dev] [--out reports]
cd "$(dirname "$0")/.." && exec scripts/uv.sh run python -m smart_extractor.run_eval "$@"
