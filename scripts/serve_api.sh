#!/usr/bin/env bash
# Serve the composed OpenBB + IBKR platform as a REST API.
# Swagger docs at http://<host>:<port>/docs (defaults: 127.0.0.1:6900)
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"
cd "${PROJECT_ROOT}"

# Locate the openbb-api CLI: use OPENBB_VENV if set, otherwise assume the
# virtualenv containing OpenBB is already activated (on PATH).
if [[ -n "${OPENBB_VENV:-}" ]]; then
  OPENBB_API_BIN="${OPENBB_VENV}/bin/openbb-api"
else
  OPENBB_API_BIN="$(command -v openbb-api || true)"
fi

if [[ -z "${OPENBB_API_BIN}" || ! -x "${OPENBB_API_BIN}" ]]; then
  echo "error: openbb-api not found." >&2
  echo "  Activate your OpenBB virtualenv first, or set OPENBB_VENV=/path/to/venv" >&2
  exit 1
fi

HOST="${OBB_IBKR_HOST:-127.0.0.1}"
PORT="${OBB_IBKR_PORT:-6900}"

exec "${OPENBB_API_BIN}" \
  --app "obb_ibkr.app:app" \
  --host "${HOST}" \
  --port "${PORT}" \
  --no-build
