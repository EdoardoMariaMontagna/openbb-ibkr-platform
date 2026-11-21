# Deploying to a server: checklist

How to move this platform from a laptop to a server you control. Each item
was checked against both OpenBB 4.7.1 and OpenBB 5.0.0. Where the two lines
differ, the difference is called out.

> **Use OpenBB 5 on a server.** On OpenBB 4.x, `scripts/serve_mcp.sh` refuses
> to start (see [SECURITY.md](../SECURITY.md)), so 4.x is REST-only.

## 1. Host and install

- [ ] A dedicated, non-root user runs the platform, with Python 3.10+ (3.12 tested).
- [ ] A fresh virtualenv with an explicit OpenBB line:
  ```bash
  python3 -m venv ~/obb-venv && source ~/obb-venv/bin/activate
  pip install -e ".[openbb5]"          # REST API + MCP (recommended)
  # pip install -e ".[openbb4]"        # OpenBB 4.7.x, REST API only
  ```
- [ ] Optional, OpenBB 5 only: `pip install -e ".[openbb5,yfinance5]"`. Before
  installing or upgrading it, check where it comes from. `openbb-yfinance` 2.x is
  published from an OpenBB maintainer's personal repository, not from the
  official OpenBB repository. Check the signed provenance on PyPI:
  ```bash
  V=2.1.0; F=openbb_yfinance-$V-py3-none-any.whl
  curl -s https://pypi.org/integrity/openbb-yfinance/$V/$F/provenance \
    | python3 -c 'import json,sys; print({b["publisher"]["repository"] for b in json.load(sys.stdin)["attestation_bundles"]})'
  ```
  Without it, OpenBB 5 uses `nasdaq` (official) as the default quote provider.
- [ ] `PYTHONPATH=src python -m pytest -q` and `PYTHONPATH=src python scripts/smoke_test.py` pass.

## 2. Secrets and configuration

All settings are environment variables, either in `.env` at the project root
(git-ignored) or in your process manager. Keep every secret file `chmod 600`.

- [ ] **Project routes** (`/ibkr/*`, `/analytics/*`): set `OBB_IBKR_API_KEY`
  (`openssl rand -hex 32`). Clients send it as the `X-API-Key` header.
- [ ] **Native OpenBB routes** (`/api/v1/*`) are not covered by the key above.
  - **OpenBB 4.x:** enable OpenBB's own HTTP Basic auth:
    ```bash
    OPENBB_API_AUTH=true
    OPENBB_API_USERNAME=<user>
    OPENBB_API_PASSWORD=<long random password>
    ```
  - **OpenBB 5.0.0: known upstream issue.** `OPENBB_API_AUTH=true` makes the API
    crash at startup (`ValueError: duplicate parameter name:
    '__authenticated_user_settings'`). The cause is `openbb-federal-reserve` 2.0.0,
    which registers the same endpoint function twice. Until that is fixed, leave
    it unset and protect these routes at the network level (section 3).
- [ ] **MCP server auth** (OpenBB 5): set `"server_auth": ["<user>", "<password>"]`
  in `~/.openbb_platform/mcp_settings.json` (`chmod 600`), or
  `OPENBB_MCP_SERVER_AUTH='["user","password"]'`. Clients send
  `Authorization: Bearer base64(user:password)`. `serve_mcp.sh` refuses a
  non-loopback host without it.
- [ ] **MCP to API:** the MCP server calls the API routes in-process for each
  tool. With `OBB_IBKR_API_KEY` set, pass the key along, or every IBKR/analytics
  tool fails with 401:
  ```bash
  OPENBB_MCP_HTTPX_CLIENT_KWARGS='{"headers": {"X-API-Key": "<OBB_IBKR_API_KEY>"}}'
  ```
- [ ] **CORS:** run `python scripts/restrict_openbb_cors.py` once as the
  service user. Upstream OpenBB allows every origin by default on both lines;
  the launchers ignore this project's own CORS setting (see README).
- [ ] **MCP CLI tools** (OpenBB 5): leave `OPENBB_MCP_ENABLE_CLI_TOOLS` unset.
  `serve_mcp.sh` defaults it to `false`. These tools dispatch arbitrary `obb`
  paths and can contact a caller-chosen `server_url`.
- [ ] **Provider API keys** (optional): add them to
  `~/.openbb_platform/user_settings.json` under `"credentials"`, e.g.
  `{"credentials": {"fred_api_key": "..."}}`, then `chmod 600`. Field names are
  the same on both lines. OpenBB 5 ships fewer providers.

## 3. Network exposure

- [ ] Keep both servers bound to `127.0.0.1` (the default) and reach them through
  one of the following. Don't publish the ports directly.
  - an SSH tunnel: `ssh -N -L 6900:127.0.0.1:6900 -L 6901:127.0.0.1:6901 server`;
  - a private network (WireGuard, Tailscale);
  - a TLS reverse proxy (Caddy, nginx) that adds its own authentication.
- [ ] Firewall: only SSH (and the proxy port, if any) are reachable from outside.
- [ ] If you do bind beyond loopback (`OBB_IBKR_HOST` / `OBB_MCP_HOST`), every
  auth layer above must be on: the API key and MCP server auth, plus OpenBB
  Basic auth on 4.x. On OpenBB 5.0.0 the native routes have no working
  in-process auth (see section 2), so **don't bind beyond loopback on 5.0.0**:
  use a tunnel or an authenticating proxy instead.

## 4. IBKR

- [ ] IB Gateway (headless-friendly) runs on the same host. API enabled, trusted IP `127.0.0.1` only.
- [ ] Start on **paper**: `IBKR_PORT=4002` (Gateway paper) and `IBKR_READONLY=true`.
- [ ] Only after verifying behaviour on paper: decide whether `IBKR_READONLY=false`
  is needed. Orders still require `"confirm": true` per request.
- [ ] `OBB_IBKR_AUDIT_LOG` points to a persistent, backed-up path writable only
  by the service user.

## 5. Process supervision (systemd example)

```ini
# /etc/systemd/system/obb-ibkr-api.service
[Unit]
Description=OpenBB + IBKR REST API
After=network-online.target

[Service]
User=obb
WorkingDirectory=/home/obb/openbb-ibkr-platform
EnvironmentFile=/home/obb/openbb-ibkr-platform/.env
Environment=OPENBB_VENV=/home/obb/obb-venv
ExecStart=/home/obb/openbb-ibkr-platform/scripts/serve_api.sh
Restart=on-failure
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/home/obb

[Install]
WantedBy=multi-user.target
```

Use the same unit for MCP, with `ExecStart=.../scripts/serve_mcp.sh`.

## 6. Verify after every deploy

Run these from the server. Each one must fail closed:

```bash
# CORS: no access-control-allow-origin header for a foreign origin
curl -s -o /dev/null -D - -X OPTIONS http://127.0.0.1:6900/ibkr/health \
  -H "Origin: https://example.com" -H "Access-Control-Request-Method: GET" | grep -i allow-origin
# Project routes: 401 without the key
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:6900/ibkr/health
# MCP: 401 without the bearer token
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:6901/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{}'
```

## 7. Keep it maintained

- [ ] `./scripts/audit_deps.sh` after every upgrade (CI runs it on every push, for both OpenBB lines).
- [ ] Before upgrading an OpenBB extension, check its PyPI provenance (section 1),
  above all for packages not published from the official repository.
- [ ] Pin the versions you deployed (`pip freeze > deployed-requirements.txt`) so
  a rebuild is reproducible.
