"""Admin endpoints for privacy audits and deletion governance."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import PrivacyDeletionRequest, RelationshipEvent, User
from app.schemas import (
    AdminPrivacyAuditEntryResponse,
    AdminPrivacyDeleteRequestResponse,
    PrivacyDeleteReviewRequest,
    PrivacyRetentionSweepResponse,
)
from app.services.privacy_audit import list_privacy_events, log_privacy_event, serialize_privacy_audit_entry
from app.services.privacy_retention import (
    execute_privacy_deletion_request,
    process_due_deletion_requests,
    run_privacy_retention_sweep,
)

from .shared import get_admin_user

router = APIRouter(tags=["admin"])


def _serialize_admin_delete_request(
    row: PrivacyDeletionRequest,
    user: User | None,
) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "user_email": user.email if user else None,
        "user_nickname": user.nickname if user else None,
        "status": row.status,
        "requested_at": row.requested_at,
        "scheduled_for": row.scheduled_for,
        "cancelled_at": row.cancelled_at,
        "executed_at": row.executed_at,
        "reviewed_by": row.reviewed_by,
        "review_note": row.review_note,
        "can_cancel": row.status == "pending" and row.cancelled_at is None,
    }


@router.get("/privacy/audits", response_model=list[AdminPrivacyAuditEntryResponse])
async def get_admin_privacy_audits(
    event_type: str | None = None,
    user_id: str | None = None,
    pair_id: str | None = None,
    since: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    del admin_user
    events = await list_privacy_events(
        db,
        user_id=user_id,
        pair_id=pair_id,
        event_type=event_type,
        since=since,
        limit=limit,
    )
    payloads = []
    for event in events:
        item = serialize_privacy_audit_entry(event)
        item.update(
            {
                "user_id": event.user_id,
                "pair_id": event.pair_id,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "source": event.source,
            }
        )
        payloads.append(AdminPrivacyAuditEntryResponse(**item))
    return payloads


@router.get(
    "/privacy/delete-requests",
    response_model=list[AdminPrivacyDeleteRequestResponse],
)
async def get_admin_privacy_delete_requests(
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    del admin_user
    stmt = select(PrivacyDeletionRequest, User).join(
        User, User.id == PrivacyDeletionRequest.user_id
    )
    if status:
        stmt = stmt.where(PrivacyDeletionRequest.status == status)
    stmt = stmt.order_by(desc(PrivacyDeletionRequest.requested_at)).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()
    return [
        AdminPrivacyDeleteRequestResponse(**_serialize_admin_delete_request(row, user))
        for row, user in rows
    ]


@router.post(
    "/privacy/delete-requests/{request_id}/approve",
    response_model=AdminPrivacyDeleteRequestResponse,
)
async def approve_privacy_delete_request(
    request_id: uuid.UUID,
    req: PrivacyDeleteReviewRequest | None = None,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(PrivacyDeletionRequest, request_id)
    if not row:
        raise HTTPException(status_code=404, detail="删除请求不存在")
    if row.status not in {"pending", "manual_review"}:
        raise HTTPException(status_code=400, detail="当前状态不允许执行")

    await execute_privacy_deletion_request(
        db,
        request_row=row,
        reviewer_id=admin_user.id,
        review_note=(req.note if req else None) or "管理员批准后执行。",
    )
    await db.commit()
    user = await db.get(User, row.user_id)
    return AdminPrivacyDeleteRequestResponse(
        **_serialize_admin_delete_request(row, user)
    )


@router.post(
    "/privacy/delete-requests/{request_id}/reject",
    response_model=AdminPrivacyDeleteRequestResponse,
)
async def reject_privacy_delete_request(
    request_id: uuid.UUID,
    req: PrivacyDeleteReviewRequest | None = None,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(PrivacyDeletionRequest, request_id)
    if not row:
        raise HTTPException(status_code=404, detail="删除请求不存在")
    if row.status not in {"pending", "manual_review"}:
        raise HTTPException(status_code=400, detail="当前状态不允许驳回")

    row.status = "rejected"
    row.reviewed_by = admin_user.id
    row.review_note = (req.note if req else None) or "管理员驳回。"
    await db.flush()
    await log_privacy_event(
        db,
        event_type="privacy.delete.rejected",
        user_id=row.user_id,
        entity_type="privacy_delete_request",
        entity_id=row.id,
        payload={"delete_status": row.status},
        summary="管理员驳回了隐私删除请求。",
        source="admin",
    )
    await db.commit()
    user = await db.get(User, row.user_id)
    return AdminPrivacyDeleteRequestResponse(
        **_serialize_admin_delete_request(row, user)
    )


@router.post(
    "/privacy/retention/sweep",
    response_model=PrivacyRetentionSweepResponse,
)
async def admin_run_privacy_retention_sweep(
    dry_run: bool = True,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    retention_summary = await run_privacy_retention_sweep(
        db,
        dry_run=dry_run,
        actor_user_id=admin_user.id,
    )
    due_summary = await process_due_deletion_requests(
        db,
        dry_run=dry_run,
        reviewer_id=admin_user.id,
    )
    if not dry_run:
        await db.commit()

    return PrivacyRetentionSweepResponse(
        **retention_summary,
        due_requests=due_summary["due_requests"],
        executed=due_summary["executed"],
        manual_review=due_summary["manual_review"],
    )
