#!/usr/bin/env bash
# Serve the composed OpenBB + IBKR platform as an MCP server for Claude Code.
# Exposes OpenBB market-data endpoints AND live IBKR account/portfolio as tools.
# Defaults: http://127.0.0.1:6901/mcp
#
# Safety checks before starting (see SECURITY.md and docs/DEPLOYMENT.md):
#   - OpenBB 4.x (openbb-core 1.x): refused by default. Its openbb-mcp-server
#     (<= 1.4.1) registers a file-writing MCP tool without path validation.
#     OBB_IBKR_ALLOW_LEGACY_MCP=1 overrides this, but only on a loopback host.
#   - OpenBB 5.x: the openbb-cli dispatcher tools are disabled unless
#     OPENBB_MCP_ENABLE_CLI_TOOLS is set explicitly. A non-loopback host is
#     refused unless MCP server auth is configured (OPENBB_MCP_SERVER_AUTH or
#     "server_auth" in ~/.openbb_platform/mcp_settings.json).
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

# The python next to openbb-mcp belongs to the same virtualenv.
PYTHON_BIN="$(dirname "${OPENBB_MCP_BIN}")/python"
CORE_MAJOR="$("${PYTHON_BIN}" -c \
  'from importlib.metadata import version; print(version("openbb-core").split(".")[0])')"

case "${HOST}" in
  127.0.0.1 | localhost | ::1) LOOPBACK=1 ;;
  *) LOOPBACK=0 ;;
esac

if [[ "${CORE_MAJOR}" -lt 2 ]]; then
  if [[ "${OBB_IBKR_ALLOW_LEGACY_MCP:-}" != "1" ]]; then
    echo "error: refusing to start the MCP server on OpenBB 4.x (openbb-core ${CORE_MAJOR}.x)." >&2
    echo "  openbb-mcp-server <= 1.4.1 has a known file-write issue in its install_skill tool." >&2
    echo "  Use OpenBB 5 (pip install -e \".[openbb5]\"); see SECURITY.md." >&2
    echo "  To run it anyway on 127.0.0.1 only: OBB_IBKR_ALLOW_LEGACY_MCP=1" >&2
    exit 1
  fi
  if [[ "${LOOPBACK}" != "1" ]]; then
    echo "error: OBB_IBKR_ALLOW_LEGACY_MCP only allows a loopback host, not '${HOST}'." >&2
    exit 1
  fi
  echo "WARNING: serving MCP on OpenBB 4.x (known install_skill issue), loopback only." >&2
else
  export OPENBB_MCP_ENABLE_CLI_TOOLS="${OPENBB_MCP_ENABLE_CLI_TOOLS:-false}"

  if ! "${PYTHON_BIN}" -c '
import json, os, pathlib, sys
p = pathlib.Path.home() / ".openbb_platform" / "mcp_settings.json"
cfg = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
sys.exit(0 if os.environ.get("OPENBB_MCP_SERVER_AUTH") or cfg.get("server_auth") else 1)
'; then
    if [[ "${LOOPBACK}" != "1" ]]; then
      echo "error: refusing to serve MCP on '${HOST}' without server auth." >&2
      echo "  Set OPENBB_MCP_SERVER_AUTH='[\"user\",\"password\"]' or \"server_auth\" in" >&2
      echo "  ~/.openbb_platform/mcp_settings.json (see docs/DEPLOYMENT.md)." >&2
      exit 1
    fi
    echo "WARNING: MCP server auth is not configured (fine on 127.0.0.1 only)." >&2
  fi
fi

exec "${OPENBB_MCP_BIN}" \
  --app "obb_ibkr.app:app" \
  --host "${HOST}" \
  --port "${PORT}"
