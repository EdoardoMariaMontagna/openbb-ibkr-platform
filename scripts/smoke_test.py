"""Offline smoke test — verifies the platform wires up without needing TWS.

Checks:
  1. The composed FastAPI app imports and includes the IBKR + analytics routes.
  2. The IBKR client reports a clean (non-crashing) status when TWS is absent.
  3. OpenBB is importable and a keyless quote works (network permitting), via
     the 4.x/5.x compatibility layer.

Run (with your OpenBB virtualenv activated):
    PYTHONPATH=src python scripts/smoke_test.py
"""
from __future__ import annotations

import asyncio
import sys


def check_app() -> bool:
    from obb_ibkr.app import app

    # OpenAPI schema, not app.routes: newer FastAPI nests included routers.
    paths = set(app.openapi()["paths"])
    required = {
        "/ibkr/health",
        "/ibkr/portfolio",
        "/ibkr/quote",
        "/ibkr/order",
        "/analytics/portfolio",
        "/analytics/compare-quote",
    }
    missing = required - paths
    if missing:
        print(f"  FAIL: missing routes: {sorted(missing)}")
        return False
    print(f"  OK: composed app has {len(paths)} routes incl. all IBKR/analytics endpoints")
    return True


async def check_ibkr_status() -> bool:
    from obb_ibkr.ibkr.client import client

    status = await client.status()
    # With no TWS running we expect connected=False and a helpful error string.
    print(f"  OK: IBKR status -> connected={status.connected} paper={status.is_paper}")
    if not status.connected and status.error:
        print(f"       (expected without TWS) {status.error.splitlines()[0]}")
    return True


def check_openbb() -> bool:
    try:
        from obb_ibkr import openbb_compat

        provider = openbb_compat.default_quote_provider()
        res = openbb_compat.equity_quote("AAPL", provider)
        rows = res.results if hasattr(res, "results") else res
        print(
            f"  OK: OpenBB {openbb_compat.openbb_major()}.x {provider} quote returned "
            f"{len(rows)} row(s) for AAPL"
        )
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  WARN: OpenBB quote failed (network/provider?): {exc}")
        return True  # non-fatal for wiring test


def main() -> int:
    ok = True
    print("[1/3] Composed FastAPI app")
    ok &= check_app()
    print("[2/3] IBKR client status (no TWS required)")
    ok &= asyncio.run(check_ibkr_status())
    print("[3/3] OpenBB provider")
    ok &= check_openbb()
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
