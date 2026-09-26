# OpenBB + IBKR — Self-Hosted Data-Analysis Platform

A self-hosted financial data-analysis platform that combines the
[OpenBB Platform](https://github.com/OpenBB-finance/OpenBB) (market data,
fundamentals, economy, news across ~50 providers) with your **live Interactive
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

## Layout

```
src/obb_ibkr/
  config.py            # env-based settings (IBKR host/port, readonly, market data type)
  app.py               # composed FastAPI app: OpenBB API + IBKR + analytics routers
  ibkr/
    client.py          # async ib_async wrapper (shared connection, guarded orders)
    router.py          # /ibkr/* endpoints
    models.py          # JSON-friendly pydantic response models
  analytics/
    service.py         # cross-source logic (IBKR portfolio x OpenBB reference)
    router.py          # /analytics/* endpoints
scripts/
  serve_api.sh         # run the REST API
  serve_mcp.sh         # run the MCP server for Claude Code
  smoke_test.py        # offline wiring check (no TWS needed)
tests/test_wiring.py   # pytest wiring/safety tests
.mcp.json              # Claude Code MCP server config
.env.example           # copy to .env and edit
```

## Prerequisites

- **Python 3.10+** and a virtual environment with the [OpenBB
  Platform](https://github.com/OpenBB-finance/OpenBB) installed (`pip install
  openbb`), plus FastAPI/uvicorn (pulled in by OpenBB) and `ib_async`.
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
pip install openbb ib_async
pip install -e .

cp .env.example .env                 # then edit IBKR_PORT / IBKR_READONLY as needed
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

**MCP server for Claude Code** (http://127.0.0.1:6901/mcp):

```bash
./scripts/serve_mcp.sh
```

Then register it with Claude Code (the repo already ships `.mcp.json`):

```bash
claude mcp add --transport http openbb-ibkr http://127.0.0.1:6901/mcp
```

## Endpoints

| Endpoint | What it does |
|---|---|
| `GET /ibkr/health` | IBKR connection status (never errors — reports inline) |
| `GET /ibkr/account` | Account summary (NetLiquidation, BuyingPower, ...) |
| `GET /ibkr/positions` | Open positions |
| `GET /ibkr/portfolio` | Positions with market value + realised/unrealised P&L |
| `GET /ibkr/quote?symbol=AAPL` | IBKR snapshot quote |
| `POST /ibkr/order` | Place an order (**guarded**, see Safety) |
| `GET /analytics/portfolio` | IBKR portfolio joined with OpenBB reference + weights |
| `GET /analytics/compare-quote?symbol=AAPL` | IBKR quote vs OpenBB quote side-by-side |

Plus all ~280 native OpenBB endpoints under `/api/v1/...`.

## Safety

Order placement is disabled by default and double-guarded:

1. `IBKR_READONLY=true` (default) blocks **all** orders at the client level.
2. Even with `IBKR_READONLY=false`, each `POST /ibkr/order` must set
   `"confirm": true` to actually transmit.

Start on a **paper account** (port `7497`) and confirm behaviour before ever
pointing at a live port. `.env` is git-ignored so credentials/keys never commit.

## Test

With the virtualenv activated:

```bash
PYTHONPATH=src python scripts/smoke_test.py   # offline wiring check, no TWS needed
PYTHONPATH=src python -m pytest -q             # unit tests
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
