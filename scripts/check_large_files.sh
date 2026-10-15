#!/usr/bin/env bash
# Usage: scripts/check_large_files.sh FILE...
# Pre-commit hook: fail if any given file is larger than 1 MB (keeps PDFs/datasets out of git by accident).
status=0
for f in "$@"; do
  if [ "$(wc -c < "$f")" -gt 1048576 ]; then
    echo "File over 1MB: $f"
    status=1
  fi
done
exit $status
