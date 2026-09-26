"""Pydantic response models for IBKR endpoints.

These are intentionally simple, JSON-friendly shapes derived from the richer
`ib_async` dataclasses so the REST/MCP surface stays stable and self-documenting.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ConnectionStatus(BaseModel):
    connected: bool
    host: str
    port: int
    client_id: int
    is_paper: bool
    server_version: Optional[int] = None
    accounts: list[str] = Field(default_factory=list)
    readonly: bool = True
    error: Optional[str] = None


class AccountValue(BaseModel):
    account: str
    tag: str
    value: str
    currency: str = ""


class Position(BaseModel):
    account: str
    symbol: str
    sec_type: str
    exchange: str = ""
    currency: str = ""
    position: float
    avg_cost: float
    con_id: int = 0


class PortfolioItem(BaseModel):
    account: str
    symbol: str
    sec_type: str
    position: float
    market_price: float
    market_value: float
    average_cost: float
    unrealized_pnl: float
    realized_pnl: float
    currency: str = ""
    con_id: int = 0


class Quote(BaseModel):
    symbol: str
    sec_type: str
    exchange: str = ""
    currency: str = ""
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    market_data_type: int = 3
    con_id: int = 0


class OrderRequest(BaseModel):
    symbol: str
    action: str = Field(description="BUY or SELL")
    quantity: float = Field(gt=0)
    order_type: str = Field(default="MKT", description="MKT or LMT")
    limit_price: Optional[float] = Field(default=None, description="Required for LMT orders")
    sec_type: str = "STK"
    exchange: str = "SMART"
    currency: str = "USD"
    confirm: bool = Field(default=False, description="Must be true to actually transmit the order")


class OrderResult(BaseModel):
    submitted: bool
    order_id: Optional[int] = None
    status: str = ""
    symbol: str = ""
    action: str = ""
    quantity: float = 0
    filled: float = 0
    avg_fill_price: Optional[float] = None
    message: str = ""


class AuditEvent(BaseModel):
    """One line of the order audit trail. Shape varies by event type, so extra
    fields (reason, order_id, status, ...) are allowed through as-is."""

    model_config = ConfigDict(extra="allow")

    ts: str
    event: str
