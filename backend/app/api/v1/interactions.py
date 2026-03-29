"""用户交互事件接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_current_user
from app.core.database import get_db
from app.models import User, UserInteractionEvent
from app.schemas import (
    InteractionEventBatchRequest,
    InteractionEventBatchResponse,
    InteractionEventResponse,
)
from app.services.interaction_events import record_user_interaction_event

router = APIRouter(prefix="/interactions", tags=["交互日志"])


@router.post(
    "/events",
    response_model=InteractionEventBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="批量记录用户交互事件",
)
async def capture_interaction_events(
    req: InteractionEventBatchRequest,
    request: Request,
    user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    accepted = 0
    fallback_session_id = request.headers.get("x-qj-session-id") or None

    for item in req.events:
        await record_user_interaction_event(
            db,
            user=user,
            pair_id=item.pair_id,
            session_id=item.session_id or fallback_session_id,
            source=item.source,
            event_type=item.event_type,
            page=item.page,
            path=item.path,
            target_type=item.target_type,
            target_id=item.target_id,
            payload=item.payload,
            occurred_at=item.occurred_at,
        )
        accepted += 1

    await db.flush()
    return InteractionEventBatchResponse(accepted=accepted)


@router.get(
    "/me",
    response_model=list[InteractionEventResponse],
    summary="读取当前用户最近的交互事件",
)
async def get_my_interaction_events(
    limit: int = Query(default=50, ge=1, le=100),
    source: str | None = Query(default=None, max_length=20),
    event_type: str | None = Query(default=None, max_length=80),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(UserInteractionEvent)
        .where(UserInteractionEvent.user_id == user.id)
        .order_by(
            UserInteractionEvent.occurred_at.desc(),
            UserInteractionEvent.created_at.desc(),
        )
        .limit(limit)
    )

    if source:
        stmt = stmt.where(UserInteractionEvent.source == source)
    if event_type:
        stmt = stmt.where(UserInteractionEvent.event_type == event_type)

    result = await db.execute(stmt)
    return result.scalars().all()
