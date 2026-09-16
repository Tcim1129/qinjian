"""Decision replay admin routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User
from app.services.intervention_evaluation import build_intervention_evaluation
from app.services.relationship_evaluation import replay_evaluation_cases

from .shared import get_admin_user
from ..insights_routes.shared import resolve_scope

router = APIRouter(tags=["admin"])


@router.get("/decision-replay")
async def get_decision_replay(
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    del user, db
    return {"cases": replay_evaluation_cases()}


@router.get("/decision-evaluation")
async def get_decision_evaluation_snapshot(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id,
        mode=mode,
        user=user,
        db=db,
    )
    evaluation = await build_intervention_evaluation(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
    )
    return evaluation or {}
