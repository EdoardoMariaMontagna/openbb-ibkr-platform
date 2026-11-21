"""Tests for the safety checks in scripts/serve_mcp.sh.

A fake virtualenv provides a ``python`` that reports a chosen openbb-core
major version / auth state and an ``openbb-mcp`` that only echoes how it was
launched, so no real server is ever started.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "serve_mcp.sh"

_FAKE_PYTHON = """#!/bin/sh
case "$*" in
  *openbb-core*) echo "$FAKE_CORE_MAJOR" ;;
  *server_auth*) exit "${FAKE_AUTH_EXIT:-1}" ;;
esac
"""
_FAKE_MCP = """#!/bin/sh
echo "STARTED $* CLI=${OPENBB_MCP_ENABLE_CLI_TOOLS:-unset}"
"""


@pytest.fixture()
def fake_venv(tmp_path):
    bin_dir = tmp_path / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    for name, body in (("python", _FAKE_PYTHON), ("openbb-mcp", _FAKE_MCP)):
        path = bin_dir / name
        path.write_text(body)
        path.chmod(0o755)
    return tmp_path / "venv"


def _run(fake_venv, core_major: int, host: str = "127.0.0.1", auth: bool = False, **extra):
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(fake_venv),
        "OPENBB_VENV": str(fake_venv),
        "FAKE_CORE_MAJOR": str(core_major),
        "FAKE_AUTH_EXIT": "0" if auth else "1",
        "OBB_MCP_HOST": host,
        **extra,
    }
    return subprocess.run(["bash", str(_SCRIPT)], env=env, capture_output=True, text=True)


def test_openbb4_refused_by_default(fake_venv):
    res = _run(fake_venv, core_major=1)
    assert res.returncode == 1
    assert "refusing" in res.stderr
    assert "STARTED" not in res.stdout


def test_openbb4_override_allows_loopback_only(fake_venv):
    ok = _run(fake_venv, core_major=1, OBB_IBKR_ALLOW_LEGACY_MCP="1")
    assert ok.returncode == 0 and "STARTED" in ok.stdout
    assert "WARNING" in ok.stderr

    remote = _run(fake_venv, core_major=1, host="0.0.0.0", OBB_IBKR_ALLOW_LEGACY_MCP="1")
    assert remote.returncode == 1
    assert "STARTED" not in remote.stdout


def test_openbb5_disables_cli_tools_by_default(fake_venv):
    res = _run(fake_venv, core_major=2)
    assert res.returncode == 0
    assert "CLI=false" in res.stdout
    assert "auth is not configured" in res.stderr


def test_openbb5_respects_explicit_cli_tools_setting(fake_venv):
    res = _run(fake_venv, core_major=2, OPENBB_MCP_ENABLE_CLI_TOOLS="true")
    assert "CLI=true" in res.stdout


def test_openbb5_non_loopback_requires_auth(fake_venv):
    refused = _run(fake_venv, core_major=2, host="0.0.0.0")
    assert refused.returncode == 1
    assert "without server auth" in refused.stderr

    allowed = _run(fake_venv, core_major=2, host="0.0.0.0", auth=True)
    assert allowed.returncode == 0
    assert "--host 0.0.0.0" in allowed.stdout
