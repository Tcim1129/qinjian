"""User-facing privacy center helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import PrivacyDeletionRequest, User
from app.services.privacy_audit import (
    USER_VISIBLE_PRIVACY_EVENT_TYPES,
    list_privacy_events,
    log_privacy_event,
    serialize_privacy_audit_entry,
)


def _coerce_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def serialize_delete_request(
    row: PrivacyDeletionRequest | None,
) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "id": row.id,
        "status": row.status,
        "requested_at": row.requested_at,
        "scheduled_for": row.scheduled_for,
        "cancelled_at": row.cancelled_at,
        "executed_at": row.executed_at,
        "reviewed_by": row.reviewed_by,
        "review_note": row.review_note,
        "can_cancel": row.status == "pending" and row.cancelled_at is None,
    }


async def get_latest_delete_request(
    db: AsyncSession,
    *,
    user_id: str | uuid.UUID,
) -> PrivacyDeletionRequest | None:
    normalized_user_id = _coerce_uuid(user_id)
    stmt = (
        select(PrivacyDeletionRequest)
        .where(PrivacyDeletionRequest.user_id == normalized_user_id)
        .order_by(desc(PrivacyDeletionRequest.requested_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def build_privacy_status(
    db: AsyncSession,
    *,
    user: User,
) -> dict[str, Any]:
    latest_request = await get_latest_delete_request(db, user_id=user.id)
    return {
        "sandbox_enabled": bool(settings.PRIVACY_SANDBOX_ENABLED),
        "log_masking": bool(settings.PRIVACY_MASK_LOGS),
        "llm_redaction": bool(settings.PRIVACY_REDACT_LLM_INPUT),
        "private_upload_access": not bool(settings.UPLOAD_PUBLIC_ACCESS_ENABLED),
        "audit_enabled": bool(settings.PRIVACY_AUDIT_ENABLED),
        "audit_retention_days": int(settings.PRIVACY_AUDIT_RETENTION_DAYS),
        "upload_ticket_ttl_minutes": int(settings.UPLOAD_SIGNED_URL_EXPIRE_MINUTES),
        "delete_grace_days": int(settings.PRIVACY_DELETE_GRACE_DAYS),
        "latest_delete_request": serialize_delete_request(latest_request),
    }


async def list_my_privacy_audit_entries(
    db: AsyncSession,
    *,
    user: User,
    limit: int = 20,
) -> list[dict[str, Any]]:
    events = await list_privacy_events(
        db,
        user_id=user.id,
        limit=max(limit, 1),
    )
    serialized = [
        serialize_privacy_audit_entry(event)
        for event in events
        if event.event_type in USER_VISIBLE_PRIVACY_EVENT_TYPES
    ]
    return serialized[: max(limit, 1)]


async def create_privacy_delete_request(
    db: AsyncSession,
    *,
    user: User,
) -> dict[str, Any]:
    existing = await get_latest_delete_request(db, user_id=user.id)
    if existing and existing.status in {"pending", "manual_review"}:
        return serialize_delete_request(existing)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    row = PrivacyDeletionRequest(
        user_id=user.id,
        status="pending",
        requested_at=now,
        scheduled_for=now + timedelta(days=max(settings.PRIVACY_DELETE_GRACE_DAYS, 1)),
    )
    db.add(row)
    await db.flush()

    await log_privacy_event(
        db,
        event_type="privacy.delete.requested",
        user_id=user.id,
        entity_type="privacy_delete_request",
        entity_id=row.id,
        payload={
            "delete_status": row.status,
            "scheduled_for": row.scheduled_for.isoformat(),
        },
        summary="已发起隐私删除请求，系统进入宽限期。",
    )
    return serialize_delete_request(row)


async def cancel_privacy_delete_request(
    db: AsyncSession,
    *,
    user: User,
) -> dict[str, Any]:
    row = await get_latest_delete_request(db, user_id=user.id)
    if not row or row.status != "pending":
        raise ValueError("当前没有可撤回的删除请求")

    from datetime import datetime, timezone

    row.status = "cancelled"
    row.cancelled_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()

    await log_privacy_event(
        db,
        event_type="privacy.delete.cancelled",
        user_id=user.id,
        entity_type="privacy_delete_request",
        entity_id=row.id,
        payload={"delete_status": row.status},
        summary="已撤回隐私删除请求。",
    )
    return serialize_delete_request(row)
