"""Profile snapshot insight routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import RelationshipProfileSnapshot, User
from app.schemas import RelationshipProfileSnapshotResponse
from app.services.relationship_intelligence import refresh_profile_snapshot

from .shared import profile_scope_query, resolve_scope

router = APIRouter(tags=["关系智能"])


@router.get(
    "/profile/latest",
    response_model=RelationshipProfileSnapshotResponse | None,
)
async def get_latest_profile(
    pair_id: str | None = None,
    mode: str | None = None,
    window_days: int = 7,
    refresh: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )

    if refresh:
        return await refresh_profile_snapshot(
            db,
            pair_id=pair_scope_id,
            user_id=user_scope_id,
            window_days=window_days,
        )

    result = await db.execute(
        select(RelationshipProfileSnapshot)
        .where(
            *profile_scope_query(pair_scope_id, user_scope_id),
            RelationshipProfileSnapshot.window_days == window_days,
        )
        .order_by(
            RelationshipProfileSnapshot.snapshot_date.desc(),
            RelationshipProfileSnapshot.created_at.desc(),
        )
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if snapshot:
        return snapshot

    return await refresh_profile_snapshot(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        window_days=window_days,
    )


@router.get(
    "/profile/history",
    response_model=list[RelationshipProfileSnapshotResponse],
)
async def get_profile_history(
    pair_id: str | None = None,
    mode: str | None = None,
    window_days: int = 7,
    limit: int = 10,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )

    result = await db.execute(
        select(RelationshipProfileSnapshot)
        .where(
            *profile_scope_query(pair_scope_id, user_scope_id),
            RelationshipProfileSnapshot.window_days == window_days,
        )
        .order_by(
            RelationshipProfileSnapshot.snapshot_date.desc(),
            RelationshipProfileSnapshot.created_at.desc(),
        )
        .limit(limit)
    )
    return result.scalars().all()
