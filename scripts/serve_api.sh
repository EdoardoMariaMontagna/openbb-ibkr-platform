#!/usr/bin/env bash
# Serve the composed OpenBB + IBKR platform as a REST API.
# Swagger docs at http://127.0.0.1:6900/docs
set -euo pipefail

VENV="/Users/applemacbookpro16/openbb_env"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"
cd "${PROJECT_ROOT}"

HOST="${OBB_IBKR_HOST:-127.0.0.1}"
PORT="${OBB_IBKR_PORT:-6900}"

exec "${VENV}/bin/openbb-api" \
  --app "obb_ibkr.app:app" \
  --host "${HOST}" \
  --port "${PORT}" \
  --no-build
