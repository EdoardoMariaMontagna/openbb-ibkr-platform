"""Async IBKR client wrapper around ib_async.

A single shared `IB` connection is kept for the life of the process and
(re)connected lazily on first use. Everything is async so it composes with
FastAPI/uvicorn's event loop. Nothing here runs until an endpoint is called,
so importing this module never requires TWS to be running.

Order placement is guarded twice: the global ``IBKR_READONLY`` setting must be
false *and* the individual request must set ``confirm=true``. This keeps the
default posture safe for a data-analysis platform.
"""
from __future__ import annotations

import asyncio
import math
from typing import Optional

from ..config import get_settings
from .models import (
    AccountValue,
    ConnectionStatus,
    OrderRequest,
    OrderResult,
    PortfolioItem,
    Position,
    Quote,
)


def _clean(value) -> Optional[float]:
    """IBKR uses NaN / -1 as 'no data' sentinels; normalise to None."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or f == -1:
        return None
    return f


class IBKRError(RuntimeError):
    """Raised for connection or request failures, carrying a user-facing message."""


class IBKRClient:
    def __init__(self) -> None:
        self._ib = None  # lazily created ib_async.IB
        self._lock = asyncio.Lock()

    # -- connection ---------------------------------------------------------
    def _new_ib(self):
        from ib_async import IB  # imported lazily to keep module import cheap

        return IB()

    async def connect(self):
        settings = get_settings()
        async with self._lock:
            if self._ib is not None and self._ib.isConnected():
                return self._ib
            if self._ib is None:
                self._ib = self._new_ib()
            try:
                await self._ib.connectAsync(
                    host=settings.ibkr_host,
                    port=settings.ibkr_port,
                    clientId=settings.ibkr_client_id,
                    timeout=settings.ibkr_connect_timeout,
                    readonly=settings.ibkr_readonly,
                )
                self._ib.reqMarketDataType(settings.ibkr_market_data_type)
            except Exception as exc:  # noqa: BLE001 - surface a clean message
                raise IBKRError(
                    f"Could not connect to IBKR at {settings.ibkr_host}:{settings.ibkr_port} "
                    f"(clientId={settings.ibkr_client_id}). Is TWS/IB Gateway running and API "
                    f"enabled? Original error: {exc}"
                ) from exc
            return self._ib

    async def ensure(self):
        if self._ib is not None and self._ib.isConnected():
            return self._ib
        return await self.connect()

    async def disconnect(self) -> None:
        if self._ib is not None and self._ib.isConnected():
            self._ib.disconnect()

    def _account(self, ib) -> str:
        settings = get_settings()
        if settings.ibkr_account:
            return settings.ibkr_account
        accounts = ib.managedAccounts()
        return accounts[0] if accounts else ""

    # -- read operations ----------------------------------------------------
    async def status(self) -> ConnectionStatus:
        settings = get_settings()
        try:
            ib = await self.ensure()
        except IBKRError as exc:
            return ConnectionStatus(
                connected=False,
                host=settings.ibkr_host,
                port=settings.ibkr_port,
                client_id=settings.ibkr_client_id,
                is_paper=settings.ibkr_is_paper,
                readonly=settings.ibkr_readonly,
                error=str(exc),
            )
        return ConnectionStatus(
            connected=ib.isConnected(),
            host=settings.ibkr_host,
            port=settings.ibkr_port,
            client_id=settings.ibkr_client_id,
            is_paper=settings.ibkr_is_paper,
            server_version=ib.client.serverVersion() if ib.isConnected() else None,
            accounts=list(ib.managedAccounts()),
            readonly=settings.ibkr_readonly,
        )

    async def account_summary(self) -> list[AccountValue]:
        ib = await self.ensure()
        rows = await ib.accountSummaryAsync(self._account(ib) or "All")
        return [
            AccountValue(account=r.account, tag=r.tag, value=r.value, currency=r.currency)
            for r in rows
        ]

    async def positions(self) -> list[Position]:
        ib = await self.ensure()
        rows = await ib.reqPositionsAsync()
        out: list[Position] = []
        for p in rows:
            c = p.contract
            out.append(
                Position(
                    account=p.account,
                    symbol=c.symbol,
                    sec_type=c.secType,
                    exchange=c.exchange or c.primaryExchange or "",
                    currency=c.currency or "",
                    position=float(p.position),
                    avg_cost=float(p.avgCost),
                    con_id=c.conId or 0,
                )
            )
        return out

    async def portfolio(self) -> list[PortfolioItem]:
        ib = await self.ensure()
        account = self._account(ib)
        # Subscribe to account updates so portfolio() is populated with P&L.
        await ib.reqAccountUpdatesAsync(account)
        items = ib.portfolio(account) if account else ib.portfolio()
        out: list[PortfolioItem] = []
        for it in items:
            c = it.contract
            out.append(
                PortfolioItem(
                    account=it.account,
                    symbol=c.symbol,
                    sec_type=c.secType,
                    position=float(it.position),
                    market_price=float(it.marketPrice),
                    market_value=float(it.marketValue),
                    average_cost=float(it.averageCost),
                    unrealized_pnl=float(it.unrealizedPNL),
                    realized_pnl=float(it.realizedPNL),
                    currency=c.currency or "",
                    con_id=c.conId or 0,
                )
            )
        return out

    def _build_contract(
        self, symbol: str, sec_type: str = "STK", exchange: str = "SMART", currency: str = "USD"
    ):
        from ib_async import Contract

        return Contract(
            symbol=symbol.upper(),
            secType=sec_type.upper(),
            exchange=exchange.upper(),
            currency=currency.upper(),
        )

    async def quote(
        self,
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> Quote:
        settings = get_settings()
        ib = await self.ensure()
        contract = self._build_contract(symbol, sec_type, exchange, currency)
        qualified = await ib.qualifyContractsAsync(contract)
        if not qualified:
            raise IBKRError(f"Could not qualify contract for symbol '{symbol}'.")
        contract = qualified[0]
        tickers = await ib.reqTickersAsync(contract)
        if not tickers:
            raise IBKRError(f"No market data returned for '{symbol}'.")
        t = tickers[0]
        return Quote(
            symbol=contract.symbol,
            sec_type=contract.secType,
            exchange=contract.exchange or contract.primaryExchange or "",
            currency=contract.currency or "",
            bid=_clean(t.bid),
            ask=_clean(t.ask),
            last=_clean(t.last) or _clean(t.marketPrice()),
            close=_clean(t.close),
            volume=_clean(t.volume),
            market_data_type=settings.ibkr_market_data_type,
            con_id=contract.conId or 0,
        )

    # -- write operations (guarded) ----------------------------------------
    async def place_order(self, req: OrderRequest) -> OrderResult:
        settings = get_settings()
        if settings.ibkr_readonly:
            raise IBKRError(
                "Order placement is disabled: IBKR_READONLY is true. Set IBKR_READONLY=false "
                "to enable trading (paper account strongly recommended first)."
            )
        if not req.confirm:
            raise IBKRError("Order not transmitted: set 'confirm': true to actually place the order.")
        action = req.action.upper()
        if action not in {"BUY", "SELL"}:
            raise IBKRError("action must be 'BUY' or 'SELL'.")

        from ib_async import LimitOrder, MarketOrder

        ib = await self.ensure()
        contract = self._build_contract(req.symbol, req.sec_type, req.exchange, req.currency)
        qualified = await ib.qualifyContractsAsync(contract)
        if not qualified:
            raise IBKRError(f"Could not qualify contract for symbol '{req.symbol}'.")
        contract = qualified[0]

        order_type = req.order_type.upper()
        if order_type == "LMT":
            if req.limit_price is None:
                raise IBKRError("limit_price is required for LMT orders.")
            order = LimitOrder(action, req.quantity, req.limit_price)
        elif order_type == "MKT":
            order = MarketOrder(action, req.quantity)
        else:
            raise IBKRError("order_type must be 'MKT' or 'LMT'.")

        trade = ib.placeOrder(contract, order)
        # Give IBKR a moment to acknowledge; don't block indefinitely on fills.
        for _ in range(20):
            await asyncio.sleep(0.1)
            if trade.orderStatus.status in {
                "Submitted",
                "Filled",
                "Cancelled",
                "ApiCancelled",
                "PreSubmitted",
            }:
                break
        st = trade.orderStatus
        return OrderResult(
            submitted=True,
            order_id=trade.order.orderId,
            status=st.status,
            symbol=contract.symbol,
            action=action,
            quantity=req.quantity,
            filled=float(st.filled or 0),
            avg_fill_price=_clean(st.avgFillPrice),
            message=f"Order {st.status} on {'paper' if settings.ibkr_is_paper else 'LIVE'} account.",
        )


# Process-wide singleton used by the router and analytics service.
client = IBKRClient()
