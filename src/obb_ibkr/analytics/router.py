"""FastAPI router for cross-source (IBKR + OpenBB) analytics."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..ibkr.client import IBKRError
from ..security import require_api_key
from . import service

router = APIRouter(prefix="/analytics", tags=["Analytics"], dependencies=[Depends(require_api_key)])


_PROVIDER_HELP = (
    "OpenBB provider. Default: a keyless one (yfinance, or nasdaq on OpenBB 5 "
    "without the openbb-yfinance extension)."
)


@router.get("/portfolio", summary="IBKR portfolio enriched with OpenBB data")
async def enriched_portfolio(
    provider: Optional[str] = Query(None, description=_PROVIDER_HELP),
):
    """Your live IBKR portfolio joined with OpenBB reference data and weights."""
    try:
        return await service.enrich_portfolio(provider=provider)
    except IBKRError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/compare-quote", summary="IBKR vs OpenBB quote for one symbol")
async def compare_quote(
    symbol: str = Query(..., description="Ticker symbol, e.g. AAPL"),
    provider: Optional[str] = Query(None, description=_PROVIDER_HELP),
):
    """Compare IBKR's live/delayed quote against an OpenBB provider quote."""
    return await service.compare_quote(symbol, provider=provider)
