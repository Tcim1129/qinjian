"""隐私沙盒服务
提供日志脱敏与网络请求 AI 脱敏保护。
"""

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
CONFIDENTIAL_TOKEN_PATTERN = re.compile(
    r"(?<!\[)\b(?:CANARY_[A-Z0-9_]+|[A-Z0-9_]*SECRET[A-Z0-9_]*|[A-Z0-9_]*TOKEN[A-Z0-9_]*|[A-Z0-9_]*API_KEY[A-Z0-9_]*)\b(?!\])",
    re.IGNORECASE,
)
SECRET_LABEL_PATTERN = re.compile(
    r"(?i)\b(api(?:[_ -]?key)?|secret|token|password|passwd|口令|密钥|凭证)\b\s*[:：]?\s*([A-Za-z0-9][A-Za-z0-9_\-]{3,})"
)
BUSINESS_LABEL_PATTERN = re.compile(
    r"(?i)\b(公司|客户|项目|合同号|工号|学号|内部资料|测试资料|机密|保密)\b\s*[:：]?\s*([A-Za-z0-9][A-Za-z0-9_\-]{3,})"
)


def _extra_sensitive_terms() -> tuple[str, ...]:
    raw = (settings.PRIVACY_EXTRA_SENSITIVE_TERMS or "").replace(";", ",")
    terms = [item.strip() for item in raw.split(",") if item.strip()]
    return tuple(dict.fromkeys(terms))


EXTRA_SENSITIVE_PATTERNS = tuple(
    re.compile(re.escape(term), re.IGNORECASE) for term in _extra_sensitive_terms()
)


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
    redacted = SECRET_LABEL_PATTERN.sub(lambda match: f"{match.group(1)} [SENSITIVE]", redacted)
    redacted = BUSINESS_LABEL_PATTERN.sub(lambda match: f"{match.group(1)} [SENSITIVE]", redacted)
    redacted = CONFIDENTIAL_TOKEN_PATTERN.sub("[CONFIDENTIAL_TOKEN]", redacted)
    for pattern in EXTRA_SENSITIVE_PATTERNS:
        redacted = pattern.sub("[CONFIDENTIAL_TERM]", redacted)
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


def sanitize_event_payload(payload: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    return {
        str(key): _sanitize_event_value(value, key=str(key))
        for key, value in payload.items()
    }


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


def _sanitize_event_value(value: Any, *, key: str | None = None) -> Any:
    if isinstance(value, str):
        if _preserve_event_string(key):
            return value
        return redact_sensitive_text(value)

    if isinstance(value, Mapping):
        return {
            str(item_key): _sanitize_event_value(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [_sanitize_event_value(item, key=key) for item in value]

    return copy.deepcopy(value)


def _preserve_event_string(key: str | None) -> bool:
    normalized = str(key or "").strip().lower()
    if not normalized:
        return False
    if normalized == "url":
        return True
    if normalized in {"id", "ids", "input_hash", "output_hash", "idempotency_key"}:
        return True
    if normalized.endswith("_id") or normalized.endswith("_ids"):
        return True
    return False
