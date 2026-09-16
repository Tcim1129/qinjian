"""Retention and deletion governance helpers for the privacy sandbox."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.time import current_local_date, utc_naive_to_local_datetime
from app.models import (
    AgentChatMessage,
    AgentChatSession,
    Checkin,
    Pair,
    PlaybookRun,
    PlaybookTransition,
    PrivacyDeletionRequest,
    RelationshipEvent,
    RelationshipProfileSnapshot,
    Report,
    User,
    UserNotification,
    InterventionPlan,
)
from app.services.privacy_audit import log_privacy_event
from app.services.timeline_archive import (
    RAW_RETENTION_DAYS,
    archive_retention_policy,
    ensure_checkin_archive_fields,
)
from app.services.upload_access import is_local_upload_path, resolve_upload_file_path


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _temp_transcription_dir() -> str:
    return os.path.abspath(settings.PRIVACY_TRANSCRIPTION_TEMP_DIR)


def _safe_remove_local_upload(upload_path: str | None) -> bool:
    if not upload_path or not is_local_upload_path(upload_path):
        return False
    try:
        file_path = resolve_upload_file_path(upload_path)
    except ValueError:
        return False
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False


def _record_checkin_raw_deletion_snapshot(
    checkin: Checkin,
    *,
    reference_now: datetime,
) -> None:
    context = dict(checkin.client_context or {})
    archive_insight = dict((context.get("archive_insight") or {}))
    archive_insight["raw_deletion_snapshot"] = {
        "deleted_at": reference_now.isoformat(),
        "deleted_at_local": (
            utc_naive_to_local_datetime(reference_now).isoformat()
            if utc_naive_to_local_datetime(reference_now)
            else None
        ),
        "timezone": settings.APP_TIMEZONE,
        "policy": archive_retention_policy(),
        "had_raw_content": bool(str(checkin.content or "").strip()),
        "had_image_original": bool(checkin.image_url),
        "had_voice_original": bool(checkin.voice_url),
        "raw_retention_until": (
            checkin.raw_retention_until.isoformat()
            if isinstance(checkin.raw_retention_until, datetime)
            else None
        ),
    }
    context["archive_insight"] = archive_insight
    checkin.client_context = context


async def _user_has_shared_pair_data(db: AsyncSession, user_id: uuid.UUID) -> bool:
    stmt = select(Pair.id).where(
        or_(Pair.user_a_id == user_id, Pair.user_b_id == user_id)
    ).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _collect_private_uploads(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
    uploads: list[str] = []

    user = await db.get(User, user_id)
    if user:
        uploads.extend([user.avatar_url, user.wechat_avatar])

    checkins_result = await db.execute(
        select(Checkin).where(Checkin.user_id == user_id, Checkin.pair_id.is_(None))
    )
    for checkin in checkins_result.scalars().all():
        uploads.extend([checkin.image_url, checkin.voice_url])

    return [path for path in uploads if path]


async def _purge_user_private_data(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, int]:
    counts = {
        "solo_checkins": 0,
        "solo_reports": 0,
        "notifications": 0,
        "agent_sessions": 0,
        "agent_messages": 0,
        "events": 0,
        "snapshots": 0,
        "plans": 0,
        "playbook_runs": 0,
        "playbook_transitions": 0,
        "local_uploads_removed": 0,
    }

    for upload_path in await _collect_private_uploads(db, user_id):
        counts["local_uploads_removed"] += int(_safe_remove_local_upload(upload_path))

    session_ids_result = await db.execute(
        select(AgentChatSession.id).where(
            AgentChatSession.user_id == user_id,
            AgentChatSession.pair_id.is_(None),
        )
    )
    session_ids = list(session_ids_result.scalars().all())

    if session_ids:
        message_delete = await db.execute(
            delete(AgentChatMessage).where(AgentChatMessage.session_id.in_(session_ids))
        )
        counts["agent_messages"] = int(message_delete.rowcount or 0)

    session_delete = await db.execute(
        delete(AgentChatSession).where(
            AgentChatSession.user_id == user_id,
            AgentChatSession.pair_id.is_(None),
        )
    )
    counts["agent_sessions"] = int(session_delete.rowcount or 0)

    checkin_delete = await db.execute(
        delete(Checkin).where(Checkin.user_id == user_id, Checkin.pair_id.is_(None))
    )
    counts["solo_checkins"] = int(checkin_delete.rowcount or 0)

    report_delete = await db.execute(
        delete(Report).where(Report.user_id == user_id, Report.pair_id.is_(None))
    )
    counts["solo_reports"] = int(report_delete.rowcount or 0)

    notification_delete = await db.execute(
        delete(UserNotification).where(UserNotification.user_id == user_id)
    )
    counts["notifications"] = int(notification_delete.rowcount or 0)

    snapshot_delete = await db.execute(
        delete(RelationshipProfileSnapshot).where(
            RelationshipProfileSnapshot.user_id == user_id,
            RelationshipProfileSnapshot.pair_id.is_(None),
        )
    )
    counts["snapshots"] = int(snapshot_delete.rowcount or 0)

    plan_ids_result = await db.execute(
        select(InterventionPlan.id).where(
            InterventionPlan.user_id == user_id,
            InterventionPlan.pair_id.is_(None),
        )
    )
    plan_ids = list(plan_ids_result.scalars().all())
    if plan_ids:
        transition_delete = await db.execute(
            delete(PlaybookTransition).where(PlaybookTransition.plan_id.in_(plan_ids))
        )
        counts["playbook_transitions"] = int(transition_delete.rowcount or 0)
        run_delete = await db.execute(
            delete(PlaybookRun).where(PlaybookRun.plan_id.in_(plan_ids))
        )
        counts["playbook_runs"] = int(run_delete.rowcount or 0)

    plan_delete = await db.execute(
        delete(InterventionPlan).where(
            InterventionPlan.user_id == user_id,
            InterventionPlan.pair_id.is_(None),
        )
    )
    counts["plans"] = int(plan_delete.rowcount or 0)

    event_delete = await db.execute(
        delete(RelationshipEvent).where(
            RelationshipEvent.user_id == user_id,
            RelationshipEvent.pair_id.is_(None),
            ~RelationshipEvent.event_type.like("privacy.%"),
        )
    )
    counts["events"] = int(event_delete.rowcount or 0)

    user = await db.get(User, user_id)
    if user:
        user.email = f"deleted+{user.id.hex[:12]}@deleted.invalid"
        user.phone = None
        user.nickname = "已删除用户"
        user.password_hash = ""
        user.avatar_url = None
        user.wechat_openid = None
        user.wechat_unionid = None
        user.wechat_avatar = None

    return counts


async def execute_privacy_deletion_request(
    db: AsyncSession,
    *,
    request_row: PrivacyDeletionRequest,
    reviewer_id: uuid.UUID | None = None,
    review_note: str | None = None,
) -> dict[str, Any]:
    counts = await _purge_user_private_data(db, user_id=request_row.user_id)
    now = _utcnow()
    request_row.status = "executed"
    request_row.executed_at = now
    request_row.reviewed_by = reviewer_id
    if review_note:
        request_row.review_note = review_note.strip()
    await db.flush()

    await log_privacy_event(
        db,
        event_type="privacy.delete.executed",
        user_id=request_row.user_id,
        entity_type="privacy_delete_request",
        entity_id=request_row.id,
        payload={
            "delete_status": request_row.status,
            "counts": counts,
        },
        summary="已执行私有数据删除和账号匿名化。",
        occurred_at=now,
    )
    return counts


async def process_due_deletion_requests(
    db: AsyncSession,
    *,
    dry_run: bool = False,
    now: datetime | None = None,
    reviewer_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    reference_now = now or _utcnow()
    stmt = (
        select(PrivacyDeletionRequest)
        .where(
            PrivacyDeletionRequest.status == "pending",
            PrivacyDeletionRequest.scheduled_for <= reference_now,
        )
        .order_by(PrivacyDeletionRequest.requested_at.asc())
    )
    result = await db.execute(stmt)
    requests = list(result.scalars().all())

    stats = {
        "due_requests": len(requests),
        "executed": 0,
        "manual_review": 0,
    }

    for row in requests:
        if await _user_has_shared_pair_data(db, row.user_id):
            stats["manual_review"] += 1
            if dry_run:
                continue
            row.status = "manual_review"
            row.reviewed_by = reviewer_id
            row.review_note = "存在共享关系数据，已转入人工复核。"
            await db.flush()
            await log_privacy_event(
                db,
                event_type="privacy.delete.manual_review",
                user_id=row.user_id,
                entity_type="privacy_delete_request",
                entity_id=row.id,
                payload={"delete_status": row.status},
                summary="检测到共享关系数据，删除请求已转入人工复核。",
            )
            continue

        stats["executed"] += 1
        if dry_run:
            continue
        await execute_privacy_deletion_request(
            db,
            request_row=row,
            reviewer_id=reviewer_id,
            review_note="宽限期到期后自动执行。",
        )

    return stats


def _list_stale_temp_files(reference_now: datetime) -> list[Path]:
    root = Path(_temp_transcription_dir())
    if not root.exists():
        return []
    threshold = reference_now - timedelta(
        hours=max(settings.PRIVACY_TEMP_FILE_RETENTION_HOURS, 1)
    )
    stale_files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(
            tzinfo=None
        )
        if modified_at <= threshold:
            stale_files.append(path)
    return stale_files


async def _purge_expired_checkin_raw_data(
    db: AsyncSession,
    *,
    reference_now: datetime,
    dry_run: bool,
) -> dict[str, int]:
    fallback_cutoff_local = current_local_date(reference_now) - timedelta(
        days=RAW_RETENTION_DAYS
    )
    stmt = select(Checkin).where(
        Checkin.raw_deleted_at.is_(None),
        or_(
            Checkin.image_url.is_not(None),
            Checkin.voice_url.is_not(None),
        ),
        or_(
            and_(
                Checkin.raw_retention_until.is_not(None),
                Checkin.raw_retention_until <= reference_now,
            ),
            and_(
                Checkin.raw_retention_until.is_(None),
                Checkin.checkin_date <= fallback_cutoff_local,
            ),
        ),
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    stats = {
        "expired_raw_checkins": len(rows),
        "deleted_raw_uploads": 0,
    }
    if dry_run:
        return stats

    for checkin in rows:
        ensure_checkin_archive_fields(checkin)
        _record_checkin_raw_deletion_snapshot(checkin, reference_now=reference_now)
        stats["deleted_raw_uploads"] += int(_safe_remove_local_upload(checkin.image_url))
        stats["deleted_raw_uploads"] += int(_safe_remove_local_upload(checkin.voice_url))
        checkin.image_url = None
        checkin.voice_url = None
        checkin.raw_deleted_at = reference_now

    return stats


async def run_privacy_retention_sweep(
    db: AsyncSession,
    *,
    dry_run: bool = False,
    now: datetime | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    reference_now = now or _utcnow()
    event_cutoff = reference_now - timedelta(
        days=max(settings.PRIVACY_AUDIT_RETENTION_DAYS, 1)
    )

    event_count_result = await db.execute(
        select(func.count(RelationshipEvent.id)).where(
            RelationshipEvent.event_type.like("privacy.%"),
            RelationshipEvent.occurred_at < event_cutoff,
        )
    )
    expired_event_count = int(event_count_result.scalar_one() or 0)
    stale_temp_files = _list_stale_temp_files(reference_now)
    raw_data_summary = await _purge_expired_checkin_raw_data(
        db,
        reference_now=reference_now,
        dry_run=dry_run,
    )

    summary = {
        "dry_run": dry_run,
        "expired_privacy_events": expired_event_count,
        "stale_temp_files": len(stale_temp_files),
        **raw_data_summary,
    }

    if not dry_run and expired_event_count:
        await db.execute(
            delete(RelationshipEvent).where(
                RelationshipEvent.event_type.like("privacy.%"),
                RelationshipEvent.occurred_at < event_cutoff,
            )
        )

    deleted_temp_files = 0
    if not dry_run:
        for path in stale_temp_files:
            if path.exists():
                path.unlink()
                deleted_temp_files += 1
        summary["stale_temp_files"] = deleted_temp_files

    if not dry_run and actor_user_id:
        await log_privacy_event(
            db,
            event_type="privacy.retention.purged",
            user_id=actor_user_id,
            entity_type="privacy_retention_sweep",
            payload={"counts": summary},
            summary="执行了一次隐私审计与临时文件保留清扫。",
            source="admin",
        )

    return summary
