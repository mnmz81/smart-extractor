#!/bin/sh
# Finish a draft label by hand (merchant, date), validate it and add it to the manifest.
# Usage: scripts/label_doc.sh DOC_ID [--dir data/public] [--source public] [--lang en]
cd "$(dirname "$0")/.." && exec scripts/uv.sh run python -m smart_extractor.label_doc "$@"
