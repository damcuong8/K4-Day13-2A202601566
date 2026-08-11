from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

STATE = {
    "rag_slow": False,
    "tool_fail": False,
    "cost_spike": False,
}

AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl"))


def _write_audit_log(action: str, incident_name: str) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    audit_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "audit_event",
        "action": action,
        "incident_name": incident_name,
        "service": os.getenv("APP_NAME", "day13-observability-lab"),
        "env": os.getenv("APP_ENV", "dev"),
    }
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")


def enable(name: str) -> None:
    if name not in STATE:
        raise KeyError(f"Unknown incident: {name}")
    STATE[name] = True
    _write_audit_log("enable_incident", name)


def disable(name: str) -> None:
    if name not in STATE:
        raise KeyError(f"Unknown incident: {name}")
    STATE[name] = False
    _write_audit_log("disable_incident", name)


def status() -> dict[str, bool]:
    return dict(STATE)
