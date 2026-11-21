#!/usr/bin/env bash
# Claude Code "headersHelper" for the MCP server started by scripts/serve_mcp.sh.
#
# Prints the Authorization header for OpenBB 5's MCP server auth, read from
# "server_auth" in ~/.openbb_platform/mcp_settings.json (or the file named by
# OBB_IBKR_MCP_SETTINGS). The password stays in that file (keep it chmod 600);
# it is never copied into Claude Code's configuration. Prints {} when no auth
# is configured, so the header is simply omitted.
set -euo pipefail

SETTINGS="${OBB_IBKR_MCP_SETTINGS:-${HOME}/.openbb_platform/mcp_settings.json}"

exec python3 -I -c '
import base64, json, pathlib, sys
p = pathlib.Path(sys.argv[1])
auth = json.loads(p.read_text(encoding="utf-8")).get("server_auth") if p.exists() else None
if not auth:
    print("{}")
else:
    user, password = auth
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    print(json.dumps({"Authorization": f"Bearer {token}"}))
' "${SETTINGS}"
