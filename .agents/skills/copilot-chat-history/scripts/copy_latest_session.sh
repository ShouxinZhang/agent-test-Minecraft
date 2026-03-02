#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
SCRIPT="$ROOT_DIR/.agents/skills/copilot-chat-history/scripts/export_copilot_chat_history.py"

if [[ ! -x "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  else
    echo "python not found: $PYTHON_BIN and no python3 in PATH" >&2
    exit 2
  fi
fi

"$PYTHON_BIN" "$SCRIPT" --latest-session --copy-to-clipboard --write-raw "$@"
