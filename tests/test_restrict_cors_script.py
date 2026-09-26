"""Tests for scripts/restrict_openbb_cors.py's JSON-merge logic.

Runs against a temp file — never touches the real
~/.openbb_platform/system_settings.json.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "restrict_openbb_cors.py"
_spec = importlib.util.spec_from_file_location("restrict_openbb_cors", _SCRIPT_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]


def test_creates_new_settings_file(tmp_path):
    path = tmp_path / "system_settings.json"
    data = _mod.apply(path, ["http://localhost:3000"])

    assert path.exists()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == data
    assert data["api_settings"]["cors"]["allow_origins"] == ["http://localhost:3000"]


def test_merges_without_clobbering_other_settings(tmp_path):
    path = tmp_path / "system_settings.json"
    path.write_text(
        json.dumps({"debug_mode": True, "api_settings": {"title": "My API"}}),
        encoding="utf-8",
    )

    data = _mod.apply(path, [])

    assert data["debug_mode"] is True
    assert data["api_settings"]["title"] == "My API"
    assert data["api_settings"]["cors"]["allow_origins"] == []


def test_empty_origins_means_none_allowed(tmp_path):
    path = tmp_path / "system_settings.json"
    data = _mod.apply(path, [])
    assert data["api_settings"]["cors"]["allow_origins"] == []
