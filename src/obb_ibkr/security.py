"""API-key authentication for the IBKR and analytics routers.

OpenBB's own endpoints (market data, fundamentals, ...) are left as upstream
ships them. Everything added by this project — live IBKR account data,
portfolio, and order placement — is the sensitive surface, so it requires a
shared secret sent in the ``X-API-Key`` header once ``OBB_IBKR_API_KEY`` is
configured.

With no key configured (the default, for local single-user use) auth is a
no-op, but every server start prints a visible warning so the gap is never
silent.
"""
from __future__ import annotations

import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from .config import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(provided: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency: enforce the X-API-Key header when one is configured."""
    settings = get_settings()
    if not settings.api_key:
        return  # auth disabled — see the startup warning in app.py
    if not provided or not secrets.compare_digest(provided, settings.api_key):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key. Send it in the 'X-API-Key' header.",
        )
