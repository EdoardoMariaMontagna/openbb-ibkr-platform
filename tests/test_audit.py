"""Audit-trail tests: every order attempt (blocked or submitted) is logged."""
from __future__ import annotations

import asyncio
import json
import os


def test_blocked_order_is_audited():
    from obb_ibkr.ibkr.client import IBKRClient, IBKRError
    from obb_ibkr.ibkr.models import OrderRequest

    client = IBKRClient()
    req = OrderRequest(symbol="AAPL", action="BUY", quantity=1, confirm=True)
    try:
        asyncio.run(client.place_order(req))
        raised = False
    except IBKRError:
        raised = True
    assert raised, "readonly guard should still block the order"

    log_path = os.environ["OBB_IBKR_AUDIT_LOG"]
    with open(log_path, encoding="utf-8") as f:
        lines = [line for line in f.read().splitlines() if line.strip()]
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "blocked"
    assert record["reason"] == "readonly"
    assert record["symbol"] == "AAPL"
    assert record["action"] == "BUY"


def test_read_recent_events_returns_newest_first():
    from obb_ibkr.audit import log_order_event, read_recent_events

    log_order_event("blocked", reason="readonly", symbol="AAA")
    log_order_event("blocked", reason="not_confirmed", symbol="BBB")

    events = read_recent_events(limit=10)
    assert [e["symbol"] for e in events] == ["BBB", "AAA"]


def test_read_recent_events_empty_when_no_log_yet():
    from obb_ibkr.audit import read_recent_events

    assert read_recent_events() == []
