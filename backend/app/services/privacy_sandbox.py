"""Privacy sandbox helpers for log masking and outbound AI redaction."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.core.config import settings

PHONE_PATTERN = re.compile(r"(?<!\d)(1\d{2})\d{4}(\d{4})(?!\d)")
EMAIL_PATTERN = re.compile(r"\b([A-Za-z0-9._%+-])([A-Za-z0-9._%+-]*)(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
LONG_NUMBER_PATTERN = re.compile(r"(?<!\d)\d{15,19}(?!\d)")


def privacy_sandbox_enabled() -> bool:
    return bool(settings.PRIVACY_SANDBOX_ENABLED)


def llm_redaction_enabled() -> bool:
    return privacy_sandbox_enabled() and bool(settings.PRIVACY_REDACT_LLM_INPUT)


def log_masking_enabled() -> bool:
    return privacy_sandbox_enabled() and bool(settings.PRIVACY_MASK_LOGS)


def mask_phone(phone: str | None) -> str:
    if not phone:
        return ""
    normalized = str(phone).strip()
    if len(normalized) < 7:
        return "***"
    return f"{normalized[:3]}****{normalized[-4:]}"


def mask_email(email: str | None) -> str:
    if not email:
        return ""
    value = str(email).strip()
    local, separator, domain = value.partition("@")
    if not separator:
        return "***"
    if len(local) <= 1:
        return f"*{separator}{domain}"
    return f"{local[0]}***{separator}{domain}"


def mask_token(token: str | None) -> str:
    if not token:
        return ""
    value = str(token).strip()
    if len(value) <= 10:
        return "***"
    return f"{value[:6]}...{value[-4:]}"


def redact_sensitive_text(text: str) -> str:
    if not text:
        return text

    redacted = PHONE_PATTERN.sub(r"\1****\2", text)
    redacted = EMAIL_PATTERN.sub(lambda match: f"{match.group(1)}***{match.group(3)}", redacted)
    redacted = UUID_PATTERN.sub("[UUID]", redacted)
    redacted = JWT_PATTERN.sub("[TOKEN]", redacted)
    redacted = LONG_NUMBER_PATTERN.sub("[LONG_NUMBER]", redacted)
    return redacted


def sanitize_log_value(value: str | None, *, kind: str = "text") -> str:
    if not log_masking_enabled():
        return value or ""

    if kind == "phone":
        return mask_phone(value)
    if kind == "email":
        return mask_email(value)
    if kind == "token":
        return mask_token(value)
    return redact_sensitive_text(value or "")


def redact_message_payload(
    messages: Sequence[Mapping[str, Any]],
    *,
    enabled: bool | None = None,
) -> list[dict[str, Any]]:
    should_redact = llm_redaction_enabled() if enabled is None else enabled
    if not should_redact:
        return [copy.deepcopy(dict(message)) for message in messages]

    return [_sanitize_mapping(message) for message in messages]


def _sanitize_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        sanitized[key] = _sanitize_value(value, key=key)
    return sanitized


def _sanitize_value(value: Any, *, key: str | None = None) -> Any:
    if isinstance(value, str):
        if key == "url":
            return value
        return redact_sensitive_text(value)

    if isinstance(value, Mapping):
        return {item_key: _sanitize_value(item_value, key=item_key) for item_key, item_value in value.items()}

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [_sanitize_value(item) for item in value]

    return copy.deepcopy(value)
