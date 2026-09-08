"""Local-calendar scheduling helpers for the desktop report refresh."""

from __future__ import annotations

import datetime as dt


DAILY_REFRESH_HOUR = 3
STARTUP_REFRESH_DELAY_SECONDS = 15 * 60


def _local_datetime(value: dt.datetime | None = None) -> dt.datetime:
    if value is None:
        return dt.datetime.now().astimezone()
    return value if value.tzinfo is not None else value.astimezone()


def local_day(value: dt.datetime | None = None) -> str:
    return _local_datetime(value).date().isoformat()


def refreshed_today(last_successful_day: object, now: dt.datetime | None = None) -> bool:
    return isinstance(last_successful_day, str) and last_successful_day == local_day(now)


def seconds_until_daily_refresh(now: dt.datetime | None = None) -> float:
    current = _local_datetime(now)
    target = current.replace(hour=DAILY_REFRESH_HOUR, minute=0, second=0, microsecond=0)
    if target <= current:
        target += dt.timedelta(days=1)
    return max(1.0, (target - current).total_seconds())
