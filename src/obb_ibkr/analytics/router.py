"""FastAPI router for cross-source (IBKR + OpenBB) analytics."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..ibkr.client import IBKRError
from ..security import require_api_key
from . import service

router = APIRouter(prefix="/analytics", tags=["Analytics"], dependencies=[Depends(require_api_key)])


@router.get("/portfolio", summary="IBKR portfolio enriched with OpenBB data")
async def enriched_portfolio(
    provider: str = Query("yfinance", description="OpenBB provider for enrichment"),
):
    """Your live IBKR portfolio joined with OpenBB reference data and weights."""
    try:
        return await service.enrich_portfolio(provider=provider)
    except IBKRError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/compare-quote", summary="IBKR vs OpenBB quote for one symbol")
async def compare_quote(
    symbol: str = Query(..., description="Ticker symbol, e.g. AAPL"),
    provider: str = Query("yfinance", description="OpenBB provider"),
):
    """Compare IBKR's live/delayed quote against an OpenBB provider quote."""
    return await service.compare_quote(symbol, provider=provider)
