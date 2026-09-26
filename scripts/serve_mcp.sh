#!/usr/bin/env bash
# Serve the composed OpenBB + IBKR platform as an MCP server for Claude Code.
# Exposes OpenBB market-data endpoints AND live IBKR account/portfolio as tools.
# Defaults: http://127.0.0.1:6901/mcp
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"
cd "${PROJECT_ROOT}"

# Locate the openbb-mcp CLI: use OPENBB_VENV if set, otherwise assume the
# virtualenv containing OpenBB is already activated (on PATH).
if [[ -n "${OPENBB_VENV:-}" ]]; then
  OPENBB_MCP_BIN="${OPENBB_VENV}/bin/openbb-mcp"
else
  OPENBB_MCP_BIN="$(command -v openbb-mcp || true)"
fi

if [[ -z "${OPENBB_MCP_BIN}" || ! -x "${OPENBB_MCP_BIN}" ]]; then
  echo "error: openbb-mcp not found." >&2
  echo "  Activate your OpenBB virtualenv first, or set OPENBB_VENV=/path/to/venv" >&2
  exit 1
fi

HOST="${OBB_MCP_HOST:-127.0.0.1}"
PORT="${OBB_MCP_PORT:-6901}"

exec "${OPENBB_MCP_BIN}" \
  --app "obb_ibkr.app:app" \
  --host "${HOST}" \
  --port "${PORT}"
