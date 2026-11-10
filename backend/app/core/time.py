"""UTC storage helpers and facility-local business-day calculations."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings

UTC = timezone.utc


def utcnow() -> datetime:
    """Return naive UTC, which is what MySQL DATETIME columns store."""
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


def to_utc_naive(value: datetime) -> datetime:
    """Normalise an aware or naive datetime into naive UTC for persistence."""
    if value.tzinfo is None:
        return value.replace(microsecond=0)
    return value.astimezone(UTC).replace(tzinfo=None, microsecond=0)


def as_utc(value: datetime) -> datetime:
    """Return an aware UTC datetime for comparisons or serialisation."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def facility_tz() -> ZoneInfo:
    return ZoneInfo(settings.facility_timezone)


def facility_now() -> datetime:
    return datetime.now(facility_tz()).replace(microsecond=0)


def facility_today() -> date:
    return facility_now().date()


def local_day_bounds(day: date) -> tuple[datetime, datetime]:
    """Return [start, end) for a facility-local calendar day as naive UTC."""
    zone = facility_tz()
    start_local = datetime.combine(day, time.min, tzinfo=zone)
    end_local = start_local + timedelta(days=1)
    return to_utc_naive(start_local), to_utc_naive(end_local)


def default_scheduled_start(shift_start: time) -> datetime:
    """Build the current shift's scheduled start in local time and return UTC.

    If today's occurrence is still more than half a day away, the employee is
    assumed to be clocking in for the previous day's night shift. Without this
    adjustment a 22:00 shift clocked in at 02:00 would look 20 hours early and
    never accrue lateness.
    """
    local_now = facility_now()
    scheduled_local = datetime.combine(local_now.date(), shift_start, tzinfo=facility_tz())
    if scheduled_local - local_now > timedelta(hours=12):
        scheduled_local -= timedelta(days=1)
    return to_utc_naive(scheduled_local)


def isoformat_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return as_utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")
