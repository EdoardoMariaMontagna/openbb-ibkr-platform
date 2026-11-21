# OpenBB + IBKR — Self-Hosted Data-Analysis Platform

A self-hosted financial data-analysis platform that combines the
[OpenBB Platform](https://github.com/OpenBB-finance/OpenBB) (market data,
fundamentals, economy, news from dozens of providers) with your **live Interactive
Brokers (IBKR / TWS)** account, exposed through a single FastAPI application
that runs both as a **REST API** and as an **MCP server for Claude Code**.

```
                 +------------------------------------------+
                 |        obb_ibkr.app:app  (FastAPI)        |
                 |                                           |
   OpenBB  ------|  /api/v1/...   (280 OpenBB endpoints)     |
                 |  /ibkr/...     (account, portfolio, quote)|---+
   IBKR/TWS -----|  /analytics/.. (OpenBB x IBKR joins)      |   |
   (ib_async)    +------------------------------------------+   |
                        |                        |              |
                 openbb-api  -> REST/Swagger     |       openbb-mcp -> Claude Code
                 http://...:6900/docs            |       http://...:6901/mcp
```

The same app object serves both surfaces, so **every endpoint — including your
live IBKR portfolio — automatically becomes an MCP tool** that Claude Code can
call.

## OpenBB versions

The same codebase runs on both OpenBB release lines:

| | OpenBB 4.7.x (`openbb-core` 1.x) | OpenBB 5.x (`openbb-core` 2.x) |
|---|---|---|
| Install | `pip install -e ".[openbb4]"` | `pip install -e ".[openbb5]"` |
| REST API (`serve_api.sh`) | ✅ | ✅ |
| MCP server (`serve_mcp.sh`) | ⛔ refused by default ([why](SECURITY.md#known-upstream-issues)) | ✅ with server auth |
| Default quote provider | `yfinance` | `yfinance` if installed (`.[yfinance5]`), else `nasdaq` |

OpenBB 5 regrouped its commands by provider (`obb.equity.price.quote(provider="x")`
became `obb.x.equity...`). All calls from this project go through
[`openbb_compat.py`](src/obb_ibkr/openbb_compat.py), which detects the installed
line. CI runs the full test suite against both.

**Releases:** [`v.2026-09-27`](../../releases/tag/v.2026-09-27) preserves the
original OpenBB-4-only architecture. Later releases carry the dual-version code.

## Layout

```
src/obb_ibkr/
  config.py            # env-based settings (IBKR, security, audit log)
  app.py               # composed FastAPI app: OpenBB API + IBKR + analytics routers
  openbb_compat.py     # OpenBB 4.x / 5.x compatibility layer (all obb calls go here)
  security.py          # API-key auth dependency for /ibkr and /analytics
  audit.py             # append-only JSON-lines audit trail for order attempts
  ibkr/
    client.py          # async ib_async wrapper (shared connection, guarded orders)
    router.py          # /ibkr/* endpoints
    models.py          # JSON-friendly pydantic response models
  analytics/
    service.py         # cross-source logic (IBKR portfolio x OpenBB reference)
    router.py          # /analytics/* endpoints
scripts/
  serve_api.sh              # run the REST API
  serve_mcp.sh               # run the MCP server for Claude Code (with safety checks)
  mcp_auth_header.sh         # Claude Code headersHelper: MCP bearer token from mcp_settings.json
  smoke_test.py               # offline wiring check (no TWS needed)
  audit_deps.sh                # run pip-audit against installed dependencies
  restrict_openbb_cors.py       # one-time setup: restrict OpenBB's system-wide CORS
.github/workflows/ci.yml   # pytest + smoke test + dependency audit, for OpenBB 4 and 5
tests/                      # pytest suite (wiring, security, audit log, compat, MCP guard)
docs/DEPLOYMENT.md          # server deployment checklist
.mcp.json                    # Claude Code MCP server config
.env.example                  # copy to .env and edit
```

## Prerequisites

- **Python 3.10+** and a virtual environment with the [OpenBB
  Platform](https://github.com/OpenBB-finance/OpenBB) 4.7.x or 5.x. The extras
  below install the right OpenBB packages, plus `ib_async`.
- For any `/ibkr/*` data: **TWS or IB Gateway running locally** with the API
  enabled (*Configure -> API -> Settings -> Enable ActiveX and Socket Clients*,
  and add `127.0.0.1` as a trusted IP). Everything else (OpenBB, the OpenBB
  side of `/analytics`) works without it.

## Setup

```bash
git clone https://github.com/<your-account>/openbb-ibkr-platform.git
cd openbb-ibkr-platform

python3 -m venv .venv                # or reuse an existing OpenBB virtualenv
source .venv/bin/activate
pip install -e ".[openbb5]"           # or ".[openbb4]"; add ",dev" for pytest + pip-audit
# optional on OpenBB 5: ".[openbb5,yfinance5]". Note that openbb-yfinance 2.x is
# published from an OpenBB maintainer's personal repo, not the official one.

cp .env.example .env
# then at minimum: set OBB_IBKR_API_KEY (openssl rand -hex 32) before exposing
# this beyond 127.0.0.1, and edit IBKR_PORT / IBKR_READONLY as needed.
```

## Run

With the virtualenv from Setup **activated**, the scripts find `openbb-api` /
`openbb-mcp` on `PATH` automatically. If you keep OpenBB in a separate venv
instead, point the scripts at it with `OPENBB_VENV=/path/to/venv` (no need to
activate it).

**REST API** (Swagger UI at http://127.0.0.1:6900/docs):

```bash
./scripts/serve_api.sh
# or, without activating: OPENBB_VENV=/path/to/venv ./scripts/serve_api.sh
```

**MCP server for Claude Code** (http://127.0.0.1:6901/mcp, OpenBB 5):

```bash
./scripts/serve_mcp.sh
```

Before starting, the script checks that it's running on OpenBB 5 (it refuses
4.x), keeps OpenBB's `openbb-cli` dispatcher tools off, and refuses a
non-loopback host unless MCP server auth is configured. To require a password
even locally, put `"server_auth": ["<user>", "<password>"]` in
`~/.openbb_platform/mcp_settings.json` and `chmod 600` it.

The repo ships `.mcp.json`, so Claude Code picks the server up when started in
this folder. Its `headersHelper` (`scripts/mcp_auth_header.sh`) reads the
password from that file on every connection, so it is never copied into Claude
Code's own config.

## Endpoints

| Endpoint | What it does |
|---|---|
| `GET /ibkr/health` | IBKR connection status (never errors — reports inline) |
| `GET /ibkr/account` | Account summary (NetLiquidation, BuyingPower, ...) |
| `GET /ibkr/positions` | Open positions |
| `GET /ibkr/portfolio` | Positions with market value + realised/unrealised P&L |
| `GET /ibkr/quote?symbol=AAPL` | IBKR snapshot quote |
| `POST /ibkr/order` | Place an order (**guarded**, see Security) |
| `GET /ibkr/audit-log?limit=50` | Recent order attempts, blocked or submitted |
| `GET /analytics/portfolio` | IBKR portfolio joined with OpenBB reference + weights |
| `GET /analytics/compare-quote?symbol=AAPL` | IBKR quote vs OpenBB quote side-by-side |

`provider` is optional on both analytics routes (default: a keyless provider,
see [OpenBB versions](#openbb-versions)), and only installed providers are accepted.

Plus every native OpenBB endpoint under `/api/v1/...` (about 270 on 4.7.1, 1,180+
on 5.0 with its default providers). These are unauthenticated, exactly as
upstream OpenBB ships them: only the routes added by this project are behind
the API key below.

## Security

This platform touches a real brokerage account, so beyond the license, three
things are hardened specifically:

**1. API-key authentication on `/ibkr/*` and `/analytics/*`.** Set
`OBB_IBKR_API_KEY` in `.env` (generate one with `openssl rand -hex 32`) and
send it as the `X-API-Key` header on every request to those routes. With no
key set (the default), auth is a no-op for local single-user use, but every
server start prints a loud warning so the gap is never silent. This is the
primary access control and is enforced by this project's own code regardless
of how the app is served.

**2. Restricted CORS — with a caveat.** By default no browser origin is
allowed to call this API cross-origin (`OBB_IBKR_CORS_ORIGINS` is empty).
However, both `openbb-api` and `openbb-mcp`'s own launchers rebuild their CORS
policy from OpenBB's *system-wide* setting
(`~/.openbb_platform/system_settings.json`, which defaults to allowing every
origin) and apply it **after** loading this project's app, overriding what
this project configures. To actually restrict browser origins when served
through those launchers, run this once:

```bash
python scripts/restrict_openbb_cors.py                        # allow no origins
python scripts/restrict_openbb_cors.py http://localhost:3000  # allow specific ones
```

This is a machine-wide OpenBB setting (affects every OpenBB server you run on
this machine), which is why it's a deliberate opt-in step rather than
something the serve scripts do silently. It does **not** affect the API-key
check above — a browser without the key gets a 401 regardless of CORS.

**3. Every order attempt is audited.** `place_order` logs one JSON line to
`OBB_IBKR_AUDIT_LOG` (default `logs/orders_audit.jsonl`, git-ignored) for
every attempt — blocked or submitted — with the reason, symbol, action,
quantity, and (if submitted) the IBKR order ID and status. Read it back via
`GET /ibkr/audit-log?limit=50` (also behind the API key) or by tailing the
file directly.

**Order placement is also disabled by default and double-guarded**,
independent of the above:

1. `IBKR_READONLY=true` (default) blocks **all** orders at the client level.
2. Even with `IBKR_READONLY=false`, each `POST /ibkr/order` must set
   `"confirm": true` to actually transmit.

Start on a **paper account** (port `7497`) and confirm behaviour before ever
pointing at a live port. `.env` is git-ignored so credentials/keys never commit.

**Dependency scanning.** `pip-audit` (part of the `[dev]` extras) scans for
known CVEs in installed dependencies:

```bash
./scripts/audit_deps.sh
```

It also runs in CI on every push (`.github/workflows/ci.yml`), non-blocking
for now since some current findings sit in OpenBB's own transitive dependency
tree rather than in code this project controls — visible and tracked rather
than silently ignored.

**MCP server.** `scripts/serve_mcp.sh` won't serve MCP on OpenBB 4.x, keeps
OpenBB 5's `openbb-cli` dispatcher tools disabled, and won't bind beyond
loopback without MCP server auth. See [SECURITY.md](SECURITY.md#known-upstream-issues).

**Deploying to a server?** Follow [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

**Found a vulnerability?** See [SECURITY.md](SECURITY.md) for how to report
it privately, and this project's disclosure policy.

## Test

With the virtualenv activated (any OpenBB line; CI runs both):

```bash
PYTHONPATH=src python scripts/smoke_test.py   # offline wiring check, no TWS needed
PYTHONPATH=src python -m pytest -q             # unit tests (needs `pip install -e ".[dev]"`)
./scripts/audit_deps.sh                         # dependency CVE scan
```

## Roadmap ideas

- Historical bars from IBKR (`reqHistoricalData`) joined with OpenBB technicals.
- Risk/exposure analytics across the enriched portfolio (sector/currency).
- Streaming quotes via websockets.
- Optional web dashboard (currently headless: API + MCP only).

## License

[GNU AGPL-3.0-only](LICENSE). Chosen to match the [OpenBB
Platform](https://github.com/OpenBB-finance/OpenBB)'s own license — this
project extends OpenBB's code in-process, so it inherits AGPL's copyleft — and
because the AGPL closes the "SaaS loophole" that plain GPL leaves open: if you
run a modified version of this platform as a network service (locally or on a
server), you must make the corresponding source available to its users, not
just to people who receive a distributed copy. This keeps the project free
and open, whether it's used on a laptop or deployed on a server.
