"""Wiring tests that run without TWS or network — safe for CI.

Run:  PYTHONPATH=src /Users/applemacbookpro16/openbb_env/bin/python -m pytest -q
"""
from __future__ import annotations

import asyncio


def test_app_includes_ibkr_and_analytics_routes():
    from obb_ibkr.app import app

    paths = {getattr(r, "path", "") for r in app.routes}
    for expected in (
        "/ibkr/health",
        "/ibkr/account",
        "/ibkr/positions",
        "/ibkr/portfolio",
        "/ibkr/quote",
        "/ibkr/order",
        "/analytics/portfolio",
        "/analytics/compare-quote",
    ):
        assert expected in paths, f"missing route {expected}"


def test_ibkr_status_degrades_without_tws():
    from obb_ibkr.ibkr.client import IBKRClient

    client = IBKRClient()
    status = asyncio.run(client.status())
    # No TWS in the test environment -> must not raise, must report not connected.
    assert status.connected is False
    assert status.error is not None


def test_order_blocked_when_readonly():
    from obb_ibkr.ibkr.client import IBKRClient, IBKRError
    from obb_ibkr.ibkr.models import OrderRequest

    client = IBKRClient()
    req = OrderRequest(symbol="AAPL", action="BUY", quantity=1, confirm=True)
    try:
        asyncio.run(client.place_order(req))
        raised = False
    except IBKRError as exc:
        raised = "READONLY" in str(exc).upper()
    assert raised, "order placement must be blocked while IBKR_READONLY is true"


def test_settings_paper_detection():
    from obb_ibkr.config import Settings

    s = Settings()
    # Default port 7497 is a paper port.
    assert s.ibkr_is_paper is True
