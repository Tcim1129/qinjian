"""User interaction event persistence helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserInteractionEvent
from app.services.behavior_judgement import apply_judgement_to_payload
from app.services.privacy_sandbox import sanitize_event_payload


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def build_interaction_payload(
    payload: dict[str, Any] | None = None,
    *,
    text: str | None = None,
    risk_level: Any = None,
    sentiment_hint: Any = None,
    judgement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return apply_judgement_to_payload(
        payload,
        text=text,
        risk_level=risk_level,
        sentiment_hint=sentiment_hint,
        judgement=judgement,
    )


async def record_user_interaction_event(
    db: AsyncSession,
    *,
    event_type: str,
    user_id: str | uuid.UUID | None = None,
    pair_id: str | uuid.UUID | None = None,
    session_id: str | None = None,
    source: str = "client",
    page: str | None = None,
    path: str | None = None,
    http_method: str | None = None,
    http_status: int | None = None,
    target_type: str | None = None,
    target_id: str | uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> UserInteractionEvent:
    event = UserInteractionEvent(
        user_id=_normalize_uuid(user_id),
        pair_id=_normalize_uuid(pair_id),
        session_id=(str(session_id).strip() or None) if session_id else None,
        source=str(source or "client")[:20],
        event_type=str(event_type or "unknown")[:80],
        page=(str(page).strip() or None)[:80] if page else None,
        path=(str(path).strip() or None)[:255] if path else None,
        http_method=(str(http_method).strip().upper() or None)[:12]
        if http_method
        else None,
        http_status=http_status,
        target_type=(str(target_type).strip() or None)[:50] if target_type else None,
        target_id=(str(target_id).strip() or None)[:80] if target_id else None,
        payload=sanitize_event_payload(payload),
        occurred_at=occurred_at or _utcnow(),
    )
    db.add(event)
    await db.flush()
    return event
