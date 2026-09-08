import datetime as dt
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import refresh_schedule


TZ = dt.timezone(dt.timedelta(hours=8))


class RefreshScheduleTests(unittest.TestCase):
    def test_refreshed_today_uses_local_calendar_day(self):
        now = dt.datetime(2026, 9, 3, 8, 0, tzinfo=TZ)
        self.assertTrue(refresh_schedule.refreshed_today("2026-09-03", now))
        self.assertFalse(refresh_schedule.refreshed_today("2026-09-02", now))

    def test_next_daily_refresh_is_same_day_before_three(self):
        now = dt.datetime(2026, 9, 3, 2, 30, tzinfo=TZ)
        self.assertEqual(refresh_schedule.seconds_until_daily_refresh(now), 30 * 60)

    def test_next_daily_refresh_is_next_day_after_three(self):
        now = dt.datetime(2026, 9, 3, 8, 0, tzinfo=TZ)
        self.assertEqual(refresh_schedule.seconds_until_daily_refresh(now), 19 * 60 * 60)

    def test_startup_delay_is_fifteen_minutes(self):
        self.assertEqual(refresh_schedule.STARTUP_REFRESH_DELAY_SECONDS, 15 * 60)
