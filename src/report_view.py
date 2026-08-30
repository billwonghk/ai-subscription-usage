"""Small, testable helpers for reusing the active browser report page."""

from __future__ import annotations

import time


REPORT_HEARTBEAT_SECONDS = 3.0


def should_open_new_report(last_report_view: float, now: float | None = None) -> bool:
    current = time.monotonic() if now is None else now
    return current - last_report_view > REPORT_HEARTBEAT_SECONDS
