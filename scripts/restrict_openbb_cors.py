#!/usr/bin/env python
"""One-time setup: restrict OpenBB's system-wide CORS policy.

Why this exists: openbb-api and openbb-mcp both rebuild their CORS
configuration from OpenBB's own system settings
(~/.openbb_platform/system_settings.json, default: allow every origin) and
apply it *after* loading a custom --app, overriding anything this project's
own code (obb_ibkr.app._restrict_cors) configures on the FastAPI app object.
The only way to actually restrict browser origins on those serving paths is
to change OpenBB's own setting — this script does that, merging into any
existing system_settings.json rather than overwriting it.

This is a MACHINE-WIDE OpenBB setting: it affects every OpenBB Platform
API/MCP server this user runs, not just this project. That's why it's a
separate, deliberate step rather than something the serve scripts do
silently. It does not affect this project's API-key check (security.py),
which is enforced independently and is the primary access control.

Usage:
    python scripts/restrict_openbb_cors.py                        # allow no origins
    python scripts/restrict_openbb_cors.py http://localhost:3000  # allow one or more
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SETTINGS_PATH = Path.home() / ".openbb_platform" / "system_settings.json"


def apply(settings_path: Path, allow_origins: list[str]) -> dict:
    data: dict = {}
    if settings_path.exists():
        data = json.loads(settings_path.read_text(encoding="utf-8"))

    data.setdefault("api_settings", {})
    data["api_settings"].setdefault("cors", {})
    data["api_settings"]["cors"]["allow_origins"] = allow_origins

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def main() -> int:
    allow_origins = sys.argv[1:]
    apply(SETTINGS_PATH, allow_origins)
    print(f"Updated {SETTINGS_PATH}")
    print(f"api_settings.cors.allow_origins = {allow_origins!r}")
    print(
        "\nThis is a machine-wide OpenBB setting — it applies to every OpenBB "
        "Platform API/MCP server you run on this machine, not just this project."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
