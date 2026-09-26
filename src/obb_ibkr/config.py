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


def _get_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings:
    """Runtime settings, re-read from the environment on every instantiation.

    IBKR defaults target a local TWS / IB Gateway paper-trading session
    (port 7497). Live trading uses 7496 for TWS and 4001 for IB Gateway.
    """

    def __init__(self) -> None:
        # --- IBKR / TWS connection ---------------------------------------
        self.ibkr_host: str = os.getenv("IBKR_HOST", "127.0.0.1")
        self.ibkr_port: int = int(os.getenv("IBKR_PORT", "7497"))  # 7497 paper TWS
        self.ibkr_client_id: int = int(os.getenv("IBKR_CLIENT_ID", "1"))
        self.ibkr_connect_timeout: float = float(os.getenv("IBKR_CONNECT_TIMEOUT", "8"))
        self.ibkr_account: str = os.getenv("IBKR_ACCOUNT", "")  # optional explicit account id
        self.ibkr_readonly: bool = _get_bool("IBKR_READONLY", True)  # block orders by default

        # --- Market data ---------------------------------------------------
        # IBKR market data types: 1=live, 2=frozen, 3=delayed, 4=delayed-frozen.
        self.ibkr_market_data_type: int = int(os.getenv("IBKR_MARKET_DATA_TYPE", "3"))

        # --- Server ----------------------------------------------------------
        self.host: str = os.getenv("OBB_IBKR_HOST", "127.0.0.1")
        self.port: int = int(os.getenv("OBB_IBKR_PORT", "6900"))

        # --- Security --------------------------------------------------------
        # Shared secret required (via the "X-API-Key" header) to call /ibkr/* and
        # /analytics/*. Empty string disables auth (local/dev default) but every
        # server startup logs a loud warning in that case.
        self.api_key: str = os.getenv("OBB_IBKR_API_KEY", "")
        # Browser origins allowed to call the API cross-origin. Empty by default:
        # this platform has no built-in web UI, so no origin needs to be trusted
        # until you build one and add it here explicitly.
        self.cors_allow_origins: list[str] = _get_list("OBB_IBKR_CORS_ORIGINS", "")
        # Append-only JSON-lines audit trail of every order attempt (blocked or
        # submitted). Path is resolved relative to the current working directory.
        self.audit_log_path: str = os.getenv("OBB_IBKR_AUDIT_LOG", "logs/orders_audit.jsonl")

    @property
    def ibkr_is_paper(self) -> bool:
        return self.ibkr_port in {7497, 4002}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
