from datetime import date, datetime, timezone

from app.core.config import settings
from app.core.time import current_local_date


def test_current_local_date_respects_configured_timezone(monkeypatch):
    monkeypatch.setattr(settings, "APP_TIMEZONE", "Asia/Shanghai")

    utc_moment = datetime(2026, 3, 27, 16, 54, 34, tzinfo=timezone.utc)

    assert current_local_date(utc_moment) == date(2026, 3, 28)


def test_current_local_date_falls_back_to_utc_for_invalid_timezone(monkeypatch):
    monkeypatch.setattr(settings, "APP_TIMEZONE", "Invalid/Timezone")

    utc_moment = datetime(2026, 3, 27, 16, 54, 34, tzinfo=timezone.utc)

    assert current_local_date(utc_moment) == date(2026, 3, 27)
