#!/usr/bin/env python3
"""Capture Claude Code's documented statusLine rate-limit snapshot."""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

from runtime_data import app_data_root

SNAPSHOT_PATH = app_data_root() / "claude-code-quota.json"


def _window(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    used, reset = value.get("used_percentage"), value.get("resets_at")
    if not isinstance(used, (int, float)) and not isinstance(reset, (int, float, str)):
        return None
    result: dict[str, Any] = {}
    if isinstance(used, (int, float)):
        result["used_percentage"] = max(0.0, min(100.0, float(used)))
    if isinstance(reset, (int, float, str)):
        result["resets_at"] = reset
    return result


def snapshot_from_statusline(payload: Any) -> dict[str, Any] | None:
    limits = payload.get("rate_limits") if isinstance(payload, dict) else None
    if not isinstance(limits, dict):
        return None
    snapshot = {
        "captured_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "five_hour": _window(limits.get("five_hour")),
        "seven_day": _window(limits.get("seven_day")),
    }
    return snapshot if snapshot["five_hour"] or snapshot["seven_day"] else None


def save_snapshot(snapshot: dict[str, Any], path: Path = SNAPSHOT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def main() -> int:
    try:
        snapshot = snapshot_from_statusline(json.load(sys.stdin))
    except (json.JSONDecodeError, OSError):
        return 0
    if snapshot:
        try:
            save_snapshot(snapshot)
        except OSError:
            pass
        parts = []
        for label, key in (("5h", "five_hour"), ("7d", "seven_day")):
            window = snapshot.get(key)
            if isinstance(window, dict) and isinstance(window.get("used_percentage"), (int, float)):
                parts.append(f"{label} {window['used_percentage']:.0f}% used")
        if parts:
            print(" · ".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
