"""Safety-related insight routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas import SafetyStatusResponse
from app.services.relationship_intelligence import record_relationship_event
from app.services.safety_summary import build_safety_status

from .shared import resolve_scope

router = APIRouter(tags=["关系智能"])


@router.get(
    "/safety/status",
    response_model=SafetyStatusResponse,
)
async def get_safety_status(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )
    payload = await build_safety_status(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
    )

    await record_relationship_event(
        db,
        event_type="safety.status_viewed",
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        entity_type="safety_status",
        entity_id=f"{pair_scope_id or user_scope_id}",
        payload={"risk_level": payload.get("risk_level")},
    )
    await db.commit()
    return SafetyStatusResponse(**payload)

