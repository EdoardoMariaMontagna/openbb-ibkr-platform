"""Cross-source analytics that combine live IBKR account data with OpenBB.

This is the core value of the platform: your *actual* IBKR positions enriched
with OpenBB's fundamentals, quotes and news — the kind of joined view Claude
Code can then reason over via MCP.

OpenBB calls default to the ``yfinance`` provider, which needs no API key.
Swap the provider (fmp, intrinio, tiingo, ...) once keys are configured.
"""
from __future__ import annotations

from typing import Any, Optional

from ..ibkr.client import IBKRError, client


def _obb():
    from openbb import obb

    return obb


async def _openbb_quote(symbol: str, provider: str = "yfinance") -> Optional[dict[str, Any]]:
    """Best-effort OpenBB quote; returns None if the provider/symbol fails."""
    try:
        obb = _obb()
        res = obb.equity.price.quote(symbol=symbol, provider=provider)
        rows = res.results if hasattr(res, "results") else res
        if not rows:
            return None
        row = rows[0]
        return row.model_dump() if hasattr(row, "model_dump") else dict(row)
    except Exception:  # noqa: BLE001 - enrichment is optional, never fatal
        return None


async def enrich_portfolio(provider: str = "yfinance") -> dict[str, Any]:
    """Return IBKR portfolio joined with OpenBB reference data per symbol.

    For every equity position we attach the OpenBB quote so you can compare
    IBKR's mark against an independent source and pull in name/exchange/etc.
    """
    portfolio = await client.portfolio()

    enriched: list[dict[str, Any]] = []
    total_market_value = 0.0
    total_unrealized = 0.0
    for item in portfolio:
        row = item.model_dump()
        total_market_value += item.market_value
        total_unrealized += item.unrealized_pnl
        if item.sec_type == "STK":
            obb_quote = await _openbb_quote(item.symbol, provider=provider)
            if obb_quote:
                row["openbb"] = {
                    "name": obb_quote.get("name"),
                    "last_price": obb_quote.get("last_price") or obb_quote.get("close"),
                    "change_percent": obb_quote.get("change_percent"),
                    "market_cap": obb_quote.get("market_cap"),
                    "provider": provider,
                }
        enriched.append(row)

    weights = []
    if total_market_value:
        for row in enriched:
            weights.append(
                {
                    "symbol": row["symbol"],
                    "weight_pct": round(100.0 * row["market_value"] / total_market_value, 4),
                }
            )

    return {
        "as_of_source": "IBKR portfolio + OpenBB reference",
        "provider": provider,
        "totals": {
            "market_value": round(total_market_value, 2),
            "unrealized_pnl": round(total_unrealized, 2),
            "positions": len(enriched),
        },
        "weights": weights,
        "positions": enriched,
    }


async def compare_quote(symbol: str, provider: str = "yfinance") -> dict[str, Any]:
    """Side-by-side IBKR live quote vs OpenBB quote for one symbol."""
    ibkr_quote = None
    ibkr_error = None
    try:
        ibkr_quote = (await client.quote(symbol)).model_dump()
    except IBKRError as exc:
        ibkr_error = str(exc)

    obb_quote = await _openbb_quote(symbol, provider=provider)

    spread = None
    if ibkr_quote and obb_quote:
        ib_last = ibkr_quote.get("last")
        obb_last = obb_quote.get("last_price") or obb_quote.get("close")
        if ib_last and obb_last:
            spread = round(ib_last - float(obb_last), 4)

    return {
        "symbol": symbol.upper(),
        "ibkr": ibkr_quote,
        "ibkr_error": ibkr_error,
        "openbb": obb_quote,
        "openbb_provider": provider,
        "ibkr_minus_openbb": spread,
    }
