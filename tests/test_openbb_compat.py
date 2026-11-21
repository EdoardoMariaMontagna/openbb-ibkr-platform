"""Tests for the OpenBB 4.x / 5.x compatibility layer.

``obb`` is replaced by small fakes, so these run without network access and
pass on either OpenBB line.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from obb_ibkr import openbb_compat as compat


class _Recorder:
    """Callable that records its keyword arguments."""

    def __init__(self, tag: str):
        self.tag = tag
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(results=[SimpleNamespace(source=self.tag)])


def _use(monkeypatch, major: int, obb, providers: set[str]):
    monkeypatch.setattr(compat, "openbb_major", lambda: major)
    monkeypatch.setattr(compat, "_obb", lambda: obb)
    monkeypatch.setattr(compat, "installed_providers", lambda: providers)


def test_major_version_matches_installed_core():
    from importlib.metadata import version

    core_major = int(version("openbb-core").split(".")[0])
    assert compat.openbb_major() == (4 if core_major < 2 else 5)


def test_v4_uses_asset_class_namespace_with_provider_argument(monkeypatch):
    quote = _Recorder("v4")
    obb = SimpleNamespace(equity=SimpleNamespace(price=SimpleNamespace(quote=quote)))
    _use(monkeypatch, 4, obb, {"yfinance"})

    res = compat.equity_quote("AAPL")

    assert res.results[0].source == "v4"
    assert quote.calls == [{"symbol": "AAPL", "provider": "yfinance"}]


@pytest.mark.parametrize(
    ("provider", "layout"),
    [
        ("yfinance", ("equity", "price", "quote")),  # yfinance kept the 4.x layout
        ("nasdaq", ("equity", "quote")),  # cboe/nasdaq flattened it
    ],
)
def test_v5_uses_provider_namespace(monkeypatch, provider, layout):
    quote = _Recorder(provider)
    node = quote
    for part in reversed(layout):
        node = SimpleNamespace(**{part: node})
    obb = SimpleNamespace(**{provider: node})
    _use(monkeypatch, 5, obb, {provider})

    res = compat.equity_quote("MSFT", provider)

    assert res.results[0].source == provider
    assert quote.calls == [{"symbol": "MSFT"}]


def test_v5_default_prefers_yfinance_then_nasdaq(monkeypatch):
    _use(monkeypatch, 5, SimpleNamespace(), {"nasdaq", "yfinance", "sec"})
    assert compat.default_quote_provider() == "yfinance"

    _use(monkeypatch, 5, SimpleNamespace(), {"nasdaq", "sec"})
    assert compat.default_quote_provider() == "nasdaq"

    _use(monkeypatch, 5, SimpleNamespace(), {"sec"})
    with pytest.raises(compat.ProviderNotAvailable):
        compat.default_quote_provider()


@pytest.mark.parametrize("bad", ["__class__", "_obb", "../etc", "Yfinance", "a.b", "", "x" * 65])
def test_rejects_malformed_provider_names(monkeypatch, bad):
    # Even if a malformed name were somehow reported as installed, it must never
    # be used as an attribute name on ``obb``.
    _use(monkeypatch, 5, SimpleNamespace(), {bad, "yfinance"})
    with pytest.raises(compat.ProviderNotAvailable):
        compat._validated(bad)


def test_rejects_providers_that_are_not_installed(monkeypatch):
    _use(monkeypatch, 5, SimpleNamespace(), {"yfinance"})
    with pytest.raises(compat.ProviderNotAvailable, match="not installed"):
        compat.equity_quote("AAPL", "fmp")


def test_v5_provider_without_quote_command(monkeypatch):
    _use(monkeypatch, 5, SimpleNamespace(sec=SimpleNamespace()), {"sec"})
    with pytest.raises(compat.ProviderNotAvailable, match="no equity quote"):
        compat.equity_quote("AAPL", "sec")
