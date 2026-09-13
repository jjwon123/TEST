#!/usr/bin/env bash
# Cross-platform console launcher. Run with: bash scripts/start_brand_event_console.sh [port]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-5177}"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON_EXE="$ROOT/.venv/bin/python"
elif [[ -n "${PYTHON_BIN:-}" ]]; then
  PYTHON_EXE="$PYTHON_BIN"
else
  PYTHON_EXE="python3"
fi

cd "$ROOT"
echo "Starting Brand Event Console on http://127.0.0.1:$PORT"
exec "$PYTHON_EXE" scripts/console_server.py --port "$PORT"
