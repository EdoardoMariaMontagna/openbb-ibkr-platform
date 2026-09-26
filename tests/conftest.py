"""Shared pytest fixtures.

Settings are re-read from the environment on every ``Settings()`` call, but
``get_settings()`` caches the *result* for the process lifetime. Tests that
change env vars (via monkeypatch) must clear that cache, or they'll observe
whatever the first caller happened to see.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from obb_ibkr.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _default_audit_log_to_tmp(tmp_path, monkeypatch):
    """Keep the audit trail out of the real project directory during tests."""
    monkeypatch.setenv("OBB_IBKR_AUDIT_LOG", str(tmp_path / "orders_audit.jsonl"))
