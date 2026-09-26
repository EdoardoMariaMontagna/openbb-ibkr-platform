"""Security tests: API-key auth on /ibkr and /analytics, and CORS restriction.

Run without TWS or network — auth is enforced by a FastAPI dependency that
runs before any route handler, so a 401 never touches IBKR or OpenBB.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from obb_ibkr.app import app

client = TestClient(app)


def test_no_auth_required_when_key_unset(monkeypatch):
    monkeypatch.delenv("OBB_IBKR_API_KEY", raising=False)
    resp = client.get("/ibkr/health")
    assert resp.status_code == 200


def test_missing_header_rejected_when_key_set(monkeypatch):
    monkeypatch.setenv("OBB_IBKR_API_KEY", "s3cret")
    resp = client.get("/ibkr/health")
    assert resp.status_code == 401


def test_wrong_key_rejected(monkeypatch):
    monkeypatch.setenv("OBB_IBKR_API_KEY", "s3cret")
    resp = client.get("/ibkr/health", headers={"X-API-Key": "nope"})
    assert resp.status_code == 401


def test_correct_key_accepted(monkeypatch):
    monkeypatch.setenv("OBB_IBKR_API_KEY", "s3cret")
    resp = client.get("/ibkr/health", headers={"X-API-Key": "s3cret"})
    assert resp.status_code == 200


def test_analytics_router_also_protected(monkeypatch):
    monkeypatch.setenv("OBB_IBKR_API_KEY", "s3cret")
    # Auth runs before the handler, so this 401s without ever calling OpenBB/IBKR.
    resp = client.get("/analytics/compare-quote", params={"symbol": "AAPL"})
    assert resp.status_code == 401


def test_native_openbb_routes_unaffected_by_our_auth():
    # We only guard the routers we added; OpenBB's own surface (and its
    # generated OpenAPI schema) must keep working exactly as upstream.
    resp = client.get("/openapi.json")
    assert resp.status_code == 200


def test_cors_restricted_by_default():
    """Unit-tests `_restrict_cors` in isolation. Note: openbb-api/openbb-mcp's
    own launchers rebuild CORS from OpenBB's system-wide settings *after*
    loading a custom --app, which overrides this — see app.py's module
    docstring and scripts/restrict_openbb_cors.py for the full picture."""
    from starlette.applications import Starlette
    from starlette.middleware.cors import CORSMiddleware

    from obb_ibkr.app import _restrict_cors

    dummy = Starlette()
    dummy.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )

    _restrict_cors(dummy, allow_origins=["https://example.com"])

    cors_entries = [m for m in dummy.user_middleware if m.cls is CORSMiddleware]
    assert len(cors_entries) == 1, "expected exactly one CORS middleware after restriction"
    assert cors_entries[0].kwargs["allow_origins"] == ["https://example.com"]
