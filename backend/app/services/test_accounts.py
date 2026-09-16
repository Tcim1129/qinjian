"""Helpers for explicitly relaxed test accounts."""

from __future__ import annotations

from typing import Any

from app.core.config import settings


def relaxed_test_account_emails(*, settings_obj: Any = settings) -> set[str]:
    raw = str(getattr(settings_obj, "RELAXED_TEST_ACCOUNT_EMAILS", "") or "")
    normalized = raw.replace(";", ",").replace("\n", ",")
    return {
        item.strip().lower()
        for item in normalized.split(",")
        if item.strip()
    }


def is_relaxed_test_account(user: Any, *, settings_obj: Any = settings) -> bool:
    email = str(getattr(user, "email", "") or "").strip().lower()
    return bool(email and email in relaxed_test_account_emails(settings_obj=settings_obj))
