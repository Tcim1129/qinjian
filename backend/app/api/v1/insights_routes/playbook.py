"""Playbook insight routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas import PlaybookHistoryResponse, RelationshipPlaybookResponse
from app.services.playbook_runtime import (
    get_playbook_history,
    sync_active_playbook_runtime,
)
from app.services.relationship_intelligence import record_relationship_event

from .shared import resolve_scope

router = APIRouter(tags=["关系智能"])


@router.get(
    "/playbook/active",
    response_model=RelationshipPlaybookResponse | None,
)
async def get_active_playbook(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )
    playbook = await sync_active_playbook_runtime(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        viewed=True,
    )
    if not playbook:
        return None

    await record_relationship_event(
        db,
        event_type="playbook.viewed",
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        entity_type="intervention_plan",
        entity_id=playbook["plan_id"],
        payload={
            "plan_type": playbook["plan_type"],
            "active_branch": playbook["active_branch"],
            "current_day": playbook["current_day"],
            "transition_count": playbook.get("transition_count", 0),
        },
    )
    latest_transition = playbook.get("latest_transition")
    if latest_transition and latest_transition.get("is_new"):
        await record_relationship_event(
            db,
            event_type="playbook.transitioned",
            pair_id=pair_scope_id,
            user_id=user_scope_id,
            entity_type="playbook_transition",
            entity_id=latest_transition["id"],
            payload={
                "plan_id": str(playbook["plan_id"]),
                "plan_type": playbook["plan_type"],
                "transition_type": latest_transition["transition_type"],
                "from_branch": latest_transition.get("from_branch"),
                "to_branch": latest_transition["to_branch"],
                "from_day": latest_transition.get("from_day"),
                "to_day": latest_transition["to_day"],
                "trigger_type": latest_transition["trigger_type"],
            },
            idempotency_key=f"playbook-transition:{latest_transition['id']}",
        )
    await db.commit()
    return RelationshipPlaybookResponse(**playbook)


@router.get(
    "/playbook/history",
    response_model=PlaybookHistoryResponse | None,
)
async def get_relationship_playbook_history(
    pair_id: str | None = None,
    mode: str | None = None,
    limit: int = 8,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )
    history = await get_playbook_history(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        limit=limit,
    )
    if not history:
        return None

    await record_relationship_event(
        db,
        event_type="playbook.history_viewed",
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        entity_type="playbook_run",
        entity_id=history["run_id"],
        payload={
            "plan_id": str(history["plan_id"]),
            "transition_count": history["transition_count"],
            "limit": limit,
        },
    )
    await db.commit()
    return PlaybookHistoryResponse(**history)

