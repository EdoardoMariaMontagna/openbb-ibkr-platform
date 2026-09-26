"""Composed FastAPI application: OpenBB Platform API + IBKR + analytics.

Serving targets both use this single app object:

    openbb-api --app obb_ibkr.app:app        # REST API (Swagger at /docs)
    openbb-mcp --app obb_ibkr.app:app        # MCP server for Claude Code

We take OpenBB's own FastAPI app (so all ~280 OpenBB endpoints keep working
exactly as upstream, including its lifespan) and attach our IBKR + analytics
routers to it. That way a single MCP server exposes market data *and* your
live IBKR account as tools.

Two security adjustments are layered on top of OpenBB's defaults, scoped to
this composition:

1. The IBKR/analytics routers require an API key (see security.py). This is
   enforced by our own routers regardless of how the app is served, and is
   the primary access control — verified end-to-end through both openbb-api
   and openbb-mcp.

2. CORS is restricted here via ``_restrict_cors`` — but this only takes full
   effect when this app is served directly (e.g. ``uvicorn obb_ibkr.app:app``).
   Both openbb-api's and openbb-mcp's own launchers unconditionally rebuild
   their CORS middleware from OpenBB's *system-wide* setting
   (``~/.openbb_platform/system_settings.json``, default: allow all origins)
   *after* loading a custom --app, overriding whatever this module configures.
   To actually restrict browser origins when served through those launchers,
   run ``scripts/restrict_openbb_cors.py`` once (see its docstring — it's a
   machine-wide OpenBB setting, not scoped to this project, so it's a
   deliberate opt-in step rather than something applied silently here).
   None of this affects the API-key check above.
"""
from __future__ import annotations

import sys


def _restrict_cors(fastapi_app, allow_origins: list[str]) -> None:
    from starlette.middleware.cors import CORSMiddleware

    # Drop OpenBB's own CORSMiddleware entry and replace it with ours. Safe to
    # do here: this runs at import time, before uvicorn ever serves a request,
    # so the middleware stack hasn't been built yet (add_middleware would
    # otherwise refuse to run after that point). See the module docstring for
    # why this alone isn't sufficient when served via openbb-api/openbb-mcp.
    fastapi_app.user_middleware = [
        m for m in fastapi_app.user_middleware if m.cls is not CORSMiddleware
    ]
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _warn_if_unauthenticated(settings) -> None:
    if settings.api_key:
        return
    print(
        "\n"
        "*** WARNING: OBB_IBKR_API_KEY is not set. /ibkr/* and /analytics/* are  ***\n"
        "*** UNAUTHENTICATED. Fine for local-only use; before exposing this      ***\n"
        "*** server beyond 127.0.0.1, set OBB_IBKR_API_KEY in your .env.         ***\n",
        file=sys.stderr,
    )


def _build_app():
    from .config import get_settings

    # Import OpenBB's REST app; this triggers the (cached) extension build once.
    from openbb_core.api.rest_api import app as openbb_app

    from .analytics.router import router as analytics_router
    from .ibkr.router import router as ibkr_router

    openbb_app.include_router(ibkr_router)
    openbb_app.include_router(analytics_router)

    settings = get_settings()
    _restrict_cors(openbb_app, settings.cors_allow_origins)
    _warn_if_unauthenticated(settings)

    # Light-touch metadata so it's obvious this is the extended platform.
    openbb_app.title = "OpenBB + IBKR Self-Hosted Platform"
    return openbb_app


app = _build_app()
