"""Interaction event routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, validate_pair_access
from app.core.database import get_db
from app.models import User
from app.schemas import UserInteractionEventRequest, UserInteractionEventResponse
from app.services.interaction_events import (
    build_interaction_payload,
    record_user_interaction_event,
)


router = APIRouter(tags=["关系智能"])


@router.post(
    "/interaction-events",
    response_model=UserInteractionEventResponse,
)
async def create_interaction_event(
    payload: UserInteractionEventRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_id = str(payload.pair_id) if payload.pair_id else None
    if pair_id:
        await validate_pair_access(pair_id, user, db, require_active=False)

    event = await record_user_interaction_event(
        db,
        event_type=payload.event_type,
        user_id=user.id,
        pair_id=pair_id,
        session_id=payload.session_id,
        source=payload.source,
        page=payload.page,
        path=payload.path,
        http_method="POST",
        http_status=200,
        target_type=payload.target_type,
        target_id=payload.target_id,
        payload=build_interaction_payload(payload.payload or {}),
    )
    return UserInteractionEventResponse(event_id=event.id, accepted=True)
