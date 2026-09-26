"""Append-only JSON-lines audit trail for order attempts.

Every call to ``IBKRClient.place_order`` logs one line here — whether it was
blocked by a guard (readonly, missing confirm, bad input) or actually
submitted to IBKR. This is the forensic record: "who tried to do what, and
what actually happened", independent of whether the attempt succeeded.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_settings


def log_order_event(event: str, **fields: Any) -> None:
    """Append one audit record. Never raises — auditing must not break trading."""
    try:
        settings = get_settings()
        path = Path(settings.audit_log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **fields,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception:  # noqa: BLE001 - auditing is best-effort, not a trading gate
        pass


def read_recent_events(limit: int = 50) -> list[dict[str, Any]]:
    """Return the most recent audit records, newest first."""
    settings = get_settings()
    path = Path(settings.audit_log_path)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    records.reverse()
    return records
