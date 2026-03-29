"""Application-local time helpers for business-date calculations."""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings


def app_timezone():
    timezone_name = str(getattr(settings, "APP_TIMEZONE", "") or "").strip() or "UTC"
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return timezone.utc


def current_local_datetime(now: datetime | None = None) -> datetime:
    target_timezone = app_timezone()
    if now is None:
        return datetime.now(target_timezone)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(target_timezone)


def current_local_date(now: datetime | None = None) -> date:
    return current_local_datetime(now).date()
