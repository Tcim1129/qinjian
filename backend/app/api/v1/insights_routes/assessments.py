"""Weekly assessment insight routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas import (
    WeeklyAssessmentLatestResponse,
    WeeklyAssessmentSubmitRequest,
    WeeklyAssessmentTrendResponse,
)
from app.services.weekly_assessments import (
    get_latest_weekly_assessment,
    get_weekly_assessment_trend,
    submit_weekly_assessment,
)

from .shared import resolve_scope

router = APIRouter(tags=["关系智能"])


@router.post(
    "/assessments/weekly",
    response_model=WeeklyAssessmentLatestResponse,
)
async def submit_weekly_assessment_entry(
    req: WeeklyAssessmentSubmitRequest,
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )
    payload = await submit_weekly_assessment(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        answers=[item.model_dump() for item in req.answers],
        submitted_at=req.submitted_at,
    )
    return WeeklyAssessmentLatestResponse(**payload)


@router.get(
    "/assessments/latest",
    response_model=WeeklyAssessmentLatestResponse | None,
)
async def get_latest_weekly_assessment_entry(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )
    payload = await get_latest_weekly_assessment(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
    )
    if not payload:
        return None
    return WeeklyAssessmentLatestResponse(**payload)


@router.get(
    "/assessments/trend",
    response_model=WeeklyAssessmentTrendResponse,
)
async def get_weekly_assessment_trend_entry(
    pair_id: str | None = None,
    mode: str | None = None,
    limit: int = 4,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )
    payload = await get_weekly_assessment_trend(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        limit=limit,
    )
    return WeeklyAssessmentTrendResponse(**payload)

