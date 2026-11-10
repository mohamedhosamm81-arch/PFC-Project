"""Pure business-time and attendance-grace tests (no database required)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import app.core.time as time_module
from app.core.time import (
    as_utc,
    default_scheduled_start,
    facility_tz,
    local_day_bounds,
    to_utc_naive,
)
from app.services.session_service import compute_lateness


def test_to_utc_naive_converts_aware_values_and_drops_microseconds():
    aware = datetime(2026, 1, 15, 12, 30, 45, 123456, tzinfo=timezone(timedelta(hours=2)))
    assert to_utc_naive(aware) == datetime(2026, 1, 15, 10, 30, 45)


def test_to_utc_naive_preserves_naive_wall_clock():
    naive = datetime(2026, 1, 15, 12, 30, 45, 999999)
    assert to_utc_naive(naive) == datetime(2026, 1, 15, 12, 30, 45)


def test_as_utc_marks_naive_values_as_utc():
    value = as_utc(datetime(2026, 1, 15, 10, 0))
    assert value.tzinfo is timezone.utc
    assert value.hour == 10


def test_local_day_bounds_are_utc_and_one_day_long():
    start, end = local_day_bounds(date(2026, 1, 15))
    assert start.tzinfo is None and end.tzinfo is None
    assert end - start == timedelta(days=1)
    expected_start = (
        datetime(2026, 1, 15, tzinfo=facility_tz())
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )
    assert start == expected_start


def test_default_scheduled_start_uses_the_configured_default_shift():
    scheduled = default_scheduled_start(time(8, 0))
    # Stored as naive UTC; converting back to facility time must be 08:00.
    local = as_utc(scheduled).astimezone(facility_tz())
    assert (local.hour, local.minute) == (8, 0)


def test_default_scheduled_start_handles_a_night_shift(monkeypatch):
    # Clocking in at 02:00 belongs to the previous day's 22:00 shift.
    monkeypatch.setattr(
        time_module,
        "facility_now",
        lambda: datetime(2026, 1, 15, 2, 0, tzinfo=facility_tz()),
    )
    scheduled = default_scheduled_start(time(22, 0))
    local = as_utc(scheduled).astimezone(facility_tz())
    assert local == datetime(2026, 1, 14, 22, 0, tzinfo=facility_tz())


def test_lateness_is_zero_within_the_grace_period():
    scheduled = datetime(2026, 1, 15, 8, 0)
    assert compute_lateness(scheduled + timedelta(minutes=15), scheduled) == (0, False)
    assert compute_lateness(scheduled - timedelta(minutes=5), scheduled) == (0, False)


def test_lateness_only_counts_minutes_beyond_grace():
    scheduled = datetime(2026, 1, 15, 8, 0)
    minutes, is_late = compute_lateness(scheduled + timedelta(minutes=37), scheduled)
    assert (minutes, is_late) == (22, True)


def test_custom_grace_override_is_respected():
    scheduled = datetime(2026, 1, 15, 8, 0)
    assert compute_lateness(
        scheduled + timedelta(minutes=10), scheduled, grace_minutes=0
    ) == (10, True)
