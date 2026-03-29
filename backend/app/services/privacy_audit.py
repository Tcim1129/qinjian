"""Privacy audit helpers built on top of the relationship event stream."""

from __future__ import annotations

import hashlib
import json
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import RelationshipEvent
from app.services.privacy_sandbox import redact_sensitive_text
from app.services.relationship_intelligence import record_relationship_event

_PRIVACY_AUDIT_CONTEXT: ContextVar[dict[str, Any]] = ContextVar(
    "privacy_audit_context", default={}
)

PRIVACY_EVENT_LABELS = {
    "privacy.ai.chat.logged": "记录了一次 AI 文本调用",
    "privacy.ai.transcription.logged": "记录了一次语音转录调用",
    "privacy.upload.created": "保存了一份私有上传文件",
    "privacy.upload.access_denied": "拦截了一次超出范围的文件访问",
    "privacy.status.viewed": "查看了隐私保护状态",
    "privacy.delete.requested": "发起了删除请求",
    "privacy.delete.cancelled": "撤回了删除请求",
    "privacy.delete.executed": "执行了隐私删除流程",
    "privacy.delete.manual_review": "删除请求进入人工复核",
    "privacy.delete.rejected": "删除请求被驳回",
    "privacy.retention.purged": "执行了一次隐私保留清扫",
}

USER_VISIBLE_PRIVACY_EVENT_TYPES = {
    "privacy.ai.chat.logged",
    "privacy.ai.transcription.logged",
    "privacy.upload.created",
    "privacy.status.viewed",
    "privacy.delete.requested",
    "privacy.delete.cancelled",
    "privacy.delete.executed",
    "privacy.delete.manual_review",
    "privacy.delete.rejected",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def privacy_audit_enabled() -> bool:
    return bool(settings.PRIVACY_SANDBOX_ENABLED and settings.PRIVACY_AUDIT_ENABLED)


def _normalize_uuid_str(value: str | uuid.UUID | None) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _truncate_text(text: str | None, limit: int | None = None) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    max_chars = limit or settings.PRIVACY_AUDIT_SUMMARY_CHARS
    if len(raw) <= max_chars:
        return raw
    return f"{raw[: max_chars - 1]}…"


def _hash_value(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _flatten_message_content(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        items: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and item.get("text"):
                    items.append(str(item.get("text")))
                elif "content" in item:
                    items.extend(_flatten_message_content(item.get("content")))
            elif isinstance(item, str):
                items.append(item)
        return items
    if isinstance(content, dict):
        return _flatten_message_content(content.get("content"))
    return []


def summarize_messages_redacted(messages: list[dict]) -> str:
    parts: list[str] = []
    for message in messages or []:
        role = str(message.get("role") or "unknown")
        texts = _flatten_message_content(message.get("content"))
        if not texts:
            continue
        summary = _truncate_text(redact_sensitive_text(" ".join(texts)))
        if summary:
            parts.append(f"{role}: {summary}")
    return _truncate_text(" | ".join(parts))


def summarize_text_redacted(value: Any) -> str:
    if value is None:
        return ""
    return _truncate_text(redact_sensitive_text(str(value)))


def count_redaction_hits(raw_value: Any, redacted_value: Any) -> int:
    try:
        raw_serialized = json.dumps(raw_value, ensure_ascii=False, sort_keys=True, default=str)
        redacted_serialized = json.dumps(
            redacted_value, ensure_ascii=False, sort_keys=True, default=str
        )
    except TypeError:
        raw_serialized = str(raw_value)
        redacted_serialized = str(redacted_value)
    return 0 if raw_serialized == redacted_serialized else 1


@contextmanager
def privacy_audit_scope(**context: Any):
    current = dict(_PRIVACY_AUDIT_CONTEXT.get() or {})
    current.update({key: value for key, value in context.items() if value is not None})
    token = _PRIVACY_AUDIT_CONTEXT.set(current)
    try:
        yield current
    finally:
        _PRIVACY_AUDIT_CONTEXT.reset(token)


def get_privacy_audit_context() -> dict[str, Any]:
    return dict(_PRIVACY_AUDIT_CONTEXT.get() or {})


async def log_privacy_event(
    db: AsyncSession | None,
    *,
    event_type: str,
    user_id: str | uuid.UUID | None,
    pair_id: str | uuid.UUID | None = None,
    entity_type: str = "privacy_event",
    entity_id: str | uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    summary: str | None = None,
    source: str = "privacy",
    occurred_at: datetime | None = None,
) -> RelationshipEvent | None:
    if not db or not privacy_audit_enabled():
        return None

    normalized_payload = dict(payload or {})
    normalized_payload.setdefault(
        "event_label", PRIVACY_EVENT_LABELS.get(event_type, event_type)
    )
    if summary:
        normalized_payload["summary"] = _truncate_text(summary)

    return await record_relationship_event(
        db,
        event_type=event_type,
        pair_id=pair_id,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=normalized_payload,
        source=source,
        occurred_at=occurred_at or _utcnow(),
    )


async def log_privacy_ai_chat(
    db: AsyncSession | None,
    *,
    model: str,
    provider: str,
    run_type: str,
    scope: str,
    user_id: str | uuid.UUID | None,
    pair_id: str | uuid.UUID | None = None,
    raw_messages: list[dict],
    redacted_messages: list[dict],
    raw_output: Any = None,
    latency_ms: int | None = None,
    status: str = "completed",
    error_code: str | None = None,
) -> RelationshipEvent | None:
    if not db or not privacy_audit_enabled():
        return None

    payload = {
        "scope": scope,
        "user_id": _normalize_uuid_str(user_id),
        "pair_id": _normalize_uuid_str(pair_id),
        "run_type": run_type,
        "provider": provider,
        "model": model,
        "redaction_enabled": bool(settings.PRIVACY_REDACT_LLM_INPUT),
        "redaction_hits": count_redaction_hits(raw_messages, redacted_messages),
        "input_hash": _hash_value(raw_messages),
        "output_hash": _hash_value(raw_output) if raw_output not in (None, "") else None,
        "input_summary_redacted": summarize_messages_redacted(redacted_messages),
        "output_summary_redacted": summarize_text_redacted(raw_output),
        "latency_ms": latency_ms,
        "status": status,
        "error_code": error_code,
    }
    summary = (
        f"{run_type} 使用 {model} 完成一次 {status} 调用"
        if status == "completed"
        else f"{run_type} 使用 {model} 调用失败"
    )
    return await log_privacy_event(
        db,
        event_type="privacy.ai.chat.logged",
        user_id=user_id,
        pair_id=pair_id,
        entity_type="privacy_ai_chat",
        payload=payload,
        summary=summary,
    )


async def log_privacy_transcription(
    db: AsyncSession | None,
    *,
    scope: str,
    user_id: str | uuid.UUID | None,
    pair_id: str | uuid.UUID | None = None,
    provider: str,
    model: str,
    file_name: str,
    raw_output: str | None,
    latency_ms: int | None = None,
    status: str = "completed",
    error_code: str | None = None,
) -> RelationshipEvent | None:
    if not db or not privacy_audit_enabled():
        return None

    payload = {
        "scope": scope,
        "user_id": _normalize_uuid_str(user_id),
        "pair_id": _normalize_uuid_str(pair_id),
        "run_type": "transcription",
        "provider": provider,
        "model": model,
        "redaction_enabled": bool(settings.PRIVACY_REDACT_LLM_INPUT),
        "redaction_hits": count_redaction_hits(raw_output or "", summarize_text_redacted(raw_output)),
        "input_hash": _hash_value({"file_name": file_name}),
        "output_hash": _hash_value(raw_output) if raw_output not in (None, "") else None,
        "input_summary_redacted": summarize_text_redacted(file_name),
        "output_summary_redacted": summarize_text_redacted(raw_output),
        "latency_ms": latency_ms,
        "status": status,
        "error_code": error_code,
    }
    return await log_privacy_event(
        db,
        event_type="privacy.ai.transcription.logged",
        user_id=user_id,
        pair_id=pair_id,
        entity_type="privacy_ai_transcription",
        payload=payload,
        summary=f"语音转录 {status}",
    )


def serialize_privacy_audit_entry(event: RelationshipEvent) -> dict[str, Any]:
    payload = dict(event.payload or {})
    return {
        "event_id": event.id,
        "event_type": event.event_type,
        "event_label": payload.get("event_label")
        or PRIVACY_EVENT_LABELS.get(event.event_type, event.event_type),
        "summary": payload.get("summary") or "",
        "occurred_at": event.occurred_at,
        "meta": {
            "status": payload.get("status"),
            "scope": payload.get("scope"),
            "model": payload.get("model"),
            "provider": payload.get("provider"),
            "latency_ms": payload.get("latency_ms"),
            "scheduled_for": payload.get("scheduled_for"),
            "delete_status": payload.get("delete_status"),
            "counts": payload.get("counts"),
        },
    }


async def list_privacy_events(
    db: AsyncSession,
    *,
    user_id: str | uuid.UUID | None = None,
    pair_id: str | uuid.UUID | None = None,
    event_type: str | None = None,
    since: datetime | None = None,
    limit: int = 20,
) -> list[RelationshipEvent]:
    stmt = select(RelationshipEvent).where(RelationshipEvent.event_type.like("privacy.%"))
    if user_id not in (None, ""):
        stmt = stmt.where(RelationshipEvent.user_id == user_id)
    if pair_id not in (None, ""):
        stmt = stmt.where(RelationshipEvent.pair_id == pair_id)
    if event_type:
        stmt = stmt.where(RelationshipEvent.event_type == event_type)
    if since:
        stmt = stmt.where(RelationshipEvent.occurred_at >= since)
    stmt = stmt.order_by(desc(RelationshipEvent.occurred_at)).limit(max(limit, 1))
    result = await db.execute(stmt)
    return list(result.scalars().all())
