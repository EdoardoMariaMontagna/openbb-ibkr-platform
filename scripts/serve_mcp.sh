#!/usr/bin/env bash
# Serve the composed OpenBB + IBKR platform as an MCP server for Claude Code.
# Exposes OpenBB market-data endpoints AND live IBKR account/portfolio as tools.
set -euo pipefail

VENV="/Users/applemacbookpro16/openbb_env"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"
cd "${PROJECT_ROOT}"

HOST="${OBB_MCP_HOST:-127.0.0.1}"
PORT="${OBB_MCP_PORT:-6901}"

exec "${VENV}/bin/openbb-mcp" \
  --app "obb_ibkr.app:app" \
  --host "${HOST}" \
  --port "${PORT}"
