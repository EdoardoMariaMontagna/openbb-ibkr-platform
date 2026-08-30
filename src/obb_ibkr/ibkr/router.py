"""FastAPI router exposing IBKR data and trading endpoints.

Mounted under ``/ibkr``. Every endpoint is also automatically converted into
an MCP tool by ``openbb-mcp`` when the composed app is served, which is what
lets Claude Code read the portfolio and quotes as first-class tools.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from .client import IBKRError, client
from .models import (
    AccountValue,
    ConnectionStatus,
    OrderRequest,
    OrderResult,
    PortfolioItem,
    Position,
    Quote,
)

router = APIRouter(prefix="/ibkr", tags=["IBKR"])


def _guard(exc: IBKRError) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.get("/health", response_model=ConnectionStatus, summary="IBKR connection status")
async def health() -> ConnectionStatus:
    """Return the current IBKR/TWS connection status. Never raises — reports errors inline."""
    return await client.status()


@router.get("/account", response_model=list[AccountValue], summary="Account summary values")
async def account() -> list[AccountValue]:
    """Account summary tags (NetLiquidation, BuyingPower, TotalCashValue, ...)."""
    try:
        return await client.account_summary()
    except IBKRError as exc:
        raise _guard(exc)


@router.get("/positions", response_model=list[Position], summary="Open positions")
async def positions() -> list[Position]:
    """Current open positions across the account."""
    try:
        return await client.positions()
    except IBKRError as exc:
        raise _guard(exc)


@router.get("/portfolio", response_model=list[PortfolioItem], summary="Portfolio with P&L")
async def portfolio() -> list[PortfolioItem]:
    """Portfolio items enriched with market value and realised/unrealised P&L."""
    try:
        return await client.portfolio()
    except IBKRError as exc:
        raise _guard(exc)


@router.get("/quote", response_model=Quote, summary="Real-time / delayed quote")
async def quote(
    symbol: str = Query(..., description="Ticker symbol, e.g. AAPL"),
    sec_type: str = Query("STK", description="STK, CASH, FUT, OPT, ..."),
    exchange: str = Query("SMART"),
    currency: str = Query("USD"),
) -> Quote:
    """Snapshot quote for a symbol via IBKR market data."""
    try:
        return await client.quote(symbol, sec_type, exchange, currency)
    except IBKRError as exc:
        raise _guard(exc)


@router.post("/order", response_model=OrderResult, summary="Place an order (guarded)")
async def order(req: OrderRequest) -> OrderResult:
    """Place an order. Requires IBKR_READONLY=false AND request 'confirm': true."""
    try:
        return await client.place_order(req)
    except IBKRError as exc:
        raise _guard(exc)
