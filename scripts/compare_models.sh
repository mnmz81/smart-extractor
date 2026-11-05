#!/bin/sh
# Run one extractor mode on hard + CORD dev sets for one model; reports go to reports/compare/<label>/<set>.
# Usage: scripts/compare_models.sh <label> <model> [extractor]
label=$1; model=$2; ext=${3:-structured}
cd "$(dirname "$0")/.." || exit 1
for set in hard:data/synthetic/hard cord:data/public; do
  scripts/run_eval.sh --data "${set#*:}" --extractor "$ext" \
    --model "$model" --out "reports/compare/$label/${set%%:*}"
done
