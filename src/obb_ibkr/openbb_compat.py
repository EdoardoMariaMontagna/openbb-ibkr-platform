"""Compatibility layer between OpenBB Platform 4.x and 5.x.

This project supports both release lines from a single codebase:

- **OpenBB 4.x** (``openbb-core`` 1.x): commands are grouped by asset class and
  take a ``provider=`` argument, e.g. ``obb.equity.price.quote(..., provider="yfinance")``.
- **OpenBB 5.x** (``openbb-core`` 2.x): commands are grouped by *provider*, e.g.
  ``obb.yfinance.equity.price.quote(...)`` or ``obb.nasdaq.equity.quote(...)``.
  Many providers (including yfinance) are no longer part of the official
  OpenBB monorepo and must be installed separately.

Everything in this project that calls into ``obb`` goes through this module,
so the rest of the code never needs to know which line is installed.
"""
from __future__ import annotations

import re
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from typing import Any

# Keyless default provider for each line. On 5.x yfinance is preferred when the
# (separately installed) openbb-yfinance extension is present; otherwise fall
# back to Nasdaq, which ships with the official ``openbb`` package.
_V4_DEFAULT_PROVIDER = "yfinance"
_V5_DEFAULT_PROVIDERS = ("yfinance", "nasdaq")

# Provider names are used to look up an attribute on ``obb`` (5.x), and they can
# arrive straight from an HTTP query string, so they're checked against both a
# strict pattern and the set of providers OpenBB actually reports as installed.
_PROVIDER_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")

# 5.x quote command paths under ``obb.<provider>``, in lookup order. Providers
# don't agree on the layout (yfinance kept ``equity.price.quote``; cboe and
# nasdaq use ``equity.quote``).
_V5_QUOTE_PATHS = (("equity", "price", "quote"), ("equity", "quote"))


class ProviderNotAvailable(ValueError):
    """Raised when a provider is unknown, not installed, or has no such command."""


@lru_cache(maxsize=1)
def openbb_major() -> int:
    """Return the installed OpenBB Platform major version (4 or 5).

    Derived from ``openbb-core`` (1.x -> 4, 2.x -> 5) rather than the ``openbb``
    meta-package, which a minimal server install may not include.
    """
    try:
        core_major = int(version("openbb-core").split(".")[0])
    except PackageNotFoundError as exc:  # pragma: no cover - OpenBB is a hard dependency
        raise RuntimeError("openbb-core is not installed") from exc
    return 4 if core_major < 2 else 5


def _obb():
    from openbb import obb

    return obb


def installed_providers() -> set[str]:
    """Names of the OpenBB data providers installed in this environment."""
    return set(_obb().coverage.providers)


def default_quote_provider() -> str:
    """Keyless provider used when the caller doesn't pick one."""
    if openbb_major() < 5:
        return _V4_DEFAULT_PROVIDER
    available = installed_providers()
    for name in _V5_DEFAULT_PROVIDERS:
        if name in available:
            return name
    raise ProviderNotAvailable(
        f"none of the default providers {_V5_DEFAULT_PROVIDERS} is installed"
    )


def _validated(provider: str) -> str:
    if not _PROVIDER_NAME.fullmatch(provider or ""):
        raise ProviderNotAvailable(f"invalid provider name: {provider!r}")
    if provider not in installed_providers():
        raise ProviderNotAvailable(f"provider {provider!r} is not installed")
    return provider


def resolve_provider(provider: str | None) -> str:
    """Return a validated provider name, falling back to the default."""
    return _validated(provider) if provider else default_quote_provider()


def equity_quote(symbol: str, provider: str | None = None) -> Any:
    """Equity quote via OpenBB, on either release line. Returns the OBBject."""
    name = resolve_provider(provider)
    obb = _obb()
    if openbb_major() < 5:
        return obb.equity.price.quote(symbol=symbol, provider=name)

    namespace = getattr(obb, name)
    for path in _V5_QUOTE_PATHS:
        node = namespace
        try:
            for part in path:
                node = getattr(node, part)
        except AttributeError:
            continue
        return node(symbol=symbol)
    raise ProviderNotAvailable(f"provider {name!r} has no equity quote command")
