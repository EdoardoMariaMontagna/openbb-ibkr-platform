"""Central configuration for the self-hosted OpenBB + IBKR platform.

All settings are read from environment variables (optionally from a `.env`
file at the project root). Nothing here requires TWS to be running — the
IBKR values are only used when an IBKR endpoint is actually called.
"""
from __future__ import annotations

import os
from functools import lru_cache

try:
    # Loads a .env file from the current working directory / project root if present.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Runtime settings, resolved once and cached.

    IBKR defaults target a local TWS / IB Gateway paper-trading session
    (port 7497). Live trading uses 7496 for TWS and 4001 for IB Gateway.
    """

    # --- IBKR / TWS connection -------------------------------------------------
    ibkr_host: str = os.getenv("IBKR_HOST", "127.0.0.1")
    ibkr_port: int = int(os.getenv("IBKR_PORT", "7497"))  # 7497 paper TWS
    ibkr_client_id: int = int(os.getenv("IBKR_CLIENT_ID", "1"))
    ibkr_connect_timeout: float = float(os.getenv("IBKR_CONNECT_TIMEOUT", "8"))
    ibkr_account: str = os.getenv("IBKR_ACCOUNT", "")  # optional explicit account id
    ibkr_readonly: bool = _get_bool("IBKR_READONLY", True)  # block order placement by default

    # --- Market data ----------------------------------------------------------
    # IBKR market data types: 1=live, 2=frozen, 3=delayed, 4=delayed-frozen.
    ibkr_market_data_type: int = int(os.getenv("IBKR_MARKET_DATA_TYPE", "3"))

    # --- Server ---------------------------------------------------------------
    host: str = os.getenv("OBB_IBKR_HOST", "127.0.0.1")
    port: int = int(os.getenv("OBB_IBKR_PORT", "6900"))

    @property
    def ibkr_is_paper(self) -> bool:
        return self.ibkr_port in {7497, 4002}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
