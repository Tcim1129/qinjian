"""用户交互事件采集与存储。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Pair, User, UserInteractionEvent

MAX_SERIALIZED_PAYLOAD_CHARS = 4000


def parse_uuid(value: Any) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if value in (None, ""):
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def clean_text(value: Any, *, max_length: int) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text[:max_length]


def normalize_payload(payload: Any) -> dict | None:
    if payload is None:
        return None
    if not isinstance(payload, (dict, list, str, int, float, bool)):
        return {"preview": clean_text(payload, max_length=MAX_SERIALIZED_PAYLOAD_CHARS)}

    serialized = json.dumps(payload, ensure_ascii=False, default=str)
    if len(serialized) <= MAX_SERIALIZED_PAYLOAD_CHARS:
        if isinstance(payload, dict):
            return payload
        return {"value": payload}

    return {
        "truncated": True,
        "preview": serialized[:MAX_SERIALIZED_PAYLOAD_CHARS],
    }


async def _resolve_user_id(
    db: AsyncSession,
    *,
    user: User | None = None,
    user_id: str | uuid.UUID | None = None,
) -> uuid.UUID | None:
    if user is not None:
        return user.id

    normalized_user_id = parse_uuid(user_id)
    if not normalized_user_id:
        return None

    exists = await db.scalar(select(User.id).where(User.id == normalized_user_id))
    return normalized_user_id if exists else None


async def _resolve_pair_id(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> uuid.UUID | None:
    normalized_pair_id = parse_uuid(pair_id)
    if not normalized_pair_id:
        return None

    stmt = select(Pair.id).where(Pair.id == normalized_pair_id)
    if user_id is not None:
        stmt = stmt.where(
            or_(Pair.user_a_id == user_id, Pair.user_b_id == user_id)
        )

    exists = await db.scalar(stmt)
    return normalized_pair_id if exists else None


async def record_user_interaction_event(
    db: AsyncSession,
    *,
    user: User | None = None,
    user_id: str | uuid.UUID | None = None,
    pair_id: str | uuid.UUID | None = None,
    session_id: str | None = None,
    source: str = "web",
    event_type: str,
    page: str | None = None,
    path: str | None = None,
    http_method: str | None = None,
    http_status: int | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    payload: dict | list | str | int | float | bool | None = None,
    occurred_at: datetime | None = None,
) -> UserInteractionEvent:
    resolved_user_id = await _resolve_user_id(db, user=user, user_id=user_id)
    resolved_pair_id = await _resolve_pair_id(
        db,
        pair_id=pair_id,
        user_id=resolved_user_id,
    )

    event = UserInteractionEvent(
        user_id=resolved_user_id,
        pair_id=resolved_pair_id,
        session_id=clean_text(session_id, max_length=80),
        source=clean_text(source, max_length=20) or "web",
        event_type=clean_text(event_type, max_length=80) or "unknown",
        page=clean_text(page, max_length=80),
        path=clean_text(path, max_length=255),
        http_method=clean_text(http_method, max_length=12),
        http_status=http_status,
        target_type=clean_text(target_type, max_length=50),
        target_id=clean_text(target_id, max_length=80),
        payload=normalize_payload(payload),
        occurred_at=occurred_at
        or datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(event)
    return event
