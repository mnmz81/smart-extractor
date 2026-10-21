#!/bin/sh
# Download CORD v2 sample receipts and draft labels.
# Usage: scripts/fetch_public.sh [--out data/public] [--n 10]
cd "$(dirname "$0")/.." && exec scripts/uv.sh run python -m smart_extractor.fetch_public "$@"
