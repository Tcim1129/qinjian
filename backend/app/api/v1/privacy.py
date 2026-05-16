"""User-facing privacy center routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas import (
    PrivacyAuditEntryResponse,
    PrivacyDeleteRequestResponse,
    PrivacyStatusResponse,
)
from app.services.privacy_audit import log_privacy_event
from app.services.privacy_center import (
    build_privacy_status,
    cancel_privacy_delete_request,
    create_privacy_delete_request,
    list_my_privacy_audit_entries,
)

router = APIRouter(prefix="/privacy", tags=["隐私沙盒"])


@router.get("/status", response_model=PrivacyStatusResponse)
async def get_privacy_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = await build_privacy_status(db, user=user)
    await log_privacy_event(
        db,
        event_type="privacy.status.viewed",
        user_id=user.id,
        entity_type="privacy_status",
        entity_id=user.id,
        payload={
            "delete_status": (
                payload.get("latest_delete_request", {}) or {}
            ).get("status")
        },
        summary="查看了当前隐私保护状态。",
    )
    await db.commit()
    return PrivacyStatusResponse(**payload)


@router.get("/audit/me", response_model=list[PrivacyAuditEntryResponse])
async def get_my_privacy_audit(
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entries = await list_my_privacy_audit_entries(db, user=user, limit=limit)
    return [PrivacyAuditEntryResponse(**entry) for entry in entries]


@router.post("/delete-request", response_model=PrivacyDeleteRequestResponse)
async def request_privacy_delete(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = await create_privacy_delete_request(db, user=user)
    await db.commit()
    return PrivacyDeleteRequestResponse(**payload)


@router.post("/delete-request/cancel", response_model=PrivacyDeleteRequestResponse)
async def cancel_privacy_delete(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = await cancel_privacy_delete_request(db, user=user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return PrivacyDeleteRequestResponse(**payload)
