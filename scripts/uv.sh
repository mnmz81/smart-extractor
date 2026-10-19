#!/bin/sh
# Run uv even when ~/.local/bin is missing from PATH (e.g. git hooks, IDE shells).
# Usage: scripts/uv.sh run pytest
PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:$PATH" exec uv "$@"
