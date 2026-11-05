#!/bin/sh
# Print the review-share vs. accuracy curve for the confidence score (paid: one LLM run).
# Usage: scripts/calibrate.sh --data data/synthetic/hard [--split dev]
cd "$(dirname "$0")/.." && exec scripts/uv.sh run python -m smart_extractor.calibrate "$@"
