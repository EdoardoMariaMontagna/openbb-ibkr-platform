"""Composed FastAPI application: OpenBB Platform API + IBKR + analytics.

Serving targets both use this single app object:

    openbb-api --app obb_ibkr.app:app        # REST API (Swagger at /docs)
    openbb-mcp --app obb_ibkr.app:app        # MCP server for Claude Code

We take OpenBB's own FastAPI app (so all ~280 OpenBB endpoints keep working
exactly as upstream, including its lifespan and middleware) and attach our
IBKR + analytics routers to it. That way a single MCP server exposes market
data *and* your live IBKR account as tools.
"""
from __future__ import annotations


def _build_app():
    # Import OpenBB's REST app; this triggers the (cached) extension build once.
    from openbb_core.api.rest_api import app as openbb_app

    from .analytics.router import router as analytics_router
    from .ibkr.router import router as ibkr_router

    openbb_app.include_router(ibkr_router)
    openbb_app.include_router(analytics_router)

    # Light-touch metadata so it's obvious this is the extended platform.
    openbb_app.title = "OpenBB + IBKR Self-Hosted Platform"
    return openbb_app


app = _build_app()
