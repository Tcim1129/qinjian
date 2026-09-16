"""应用本地时区工具。"""

from datetime import date, datetime, time, timezone
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


def utc_naive_to_local_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(app_timezone())


def local_datetime_to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=app_timezone())
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def local_date_cutoff_to_utc_naive(local_day: date, *, hour: int) -> datetime:
    bounded_hour = min(max(int(hour), 0), 23)
    local_dt = datetime.combine(local_day, time(bounded_hour, 0, 0), tzinfo=app_timezone())
    return local_datetime_to_utc_naive(local_dt)
