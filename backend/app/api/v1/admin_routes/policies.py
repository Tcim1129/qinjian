"""Policy publishing admin routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import InterventionPolicyLibrary, RelationshipEvent, User
from app.schemas import (
    PolicyAuditEntryResponse,
    PolicyLibraryCreateRequest,
    PolicyLibraryItemResponse,
    PolicyLibraryReorderRequest,
    PolicyLibraryRollbackRequest,
    PolicyLibraryToggleRequest,
    PolicyLibraryUpdateRequest,
)

from .shared import (
    apply_policy_snapshot,
    ensure_policy_library_ready,
    get_admin_user,
    get_policy_row_or_404,
    normalize_policy_id,
    normalize_policy_payload,
    record_policy_audit_event,
    serialize_policy_audit_event,
    serialize_policy_row,
    snapshot_policy_row,
)

router = APIRouter(tags=["admin"])


@router.get("/policies", response_model=list[PolicyLibraryItemResponse])
async def list_admin_policies(
    plan_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_policy_library_ready(db)

    query = select(InterventionPolicyLibrary).order_by(
        InterventionPolicyLibrary.sort_order.asc(),
        InterventionPolicyLibrary.policy_id.asc(),
    )
    if plan_type:
        query = query.where(InterventionPolicyLibrary.plan_type == plan_type)
    if status_filter:
        query = query.where(InterventionPolicyLibrary.status == status_filter)

    result = await db.execute(query)
    return [serialize_policy_row(row) for row in result.scalars().all()]


@router.post("/policies", response_model=PolicyLibraryItemResponse, status_code=201)
async def create_admin_policy(
    payload: PolicyLibraryCreateRequest,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_policy_library_ready(db)
    policy_id = normalize_policy_id(payload.policy_id)
    existing = await db.execute(
        select(InterventionPolicyLibrary.id).where(
            InterventionPolicyLibrary.policy_id == policy_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="policy_id already exists.")

    normalized = normalize_policy_payload(payload.model_dump(), partial=False)
    max_sort_order = await db.execute(
        select(func.max(InterventionPolicyLibrary.sort_order))
    )
    current_max = max_sort_order.scalar_one()
    next_sort_order = int(current_max) + 1 if current_max is not None else 0

    row = InterventionPolicyLibrary(
        policy_id=policy_id,
        plan_type=normalized["plan_type"],
        title=normalized["title"],
        summary=normalized["summary"],
        branch=normalized["branch"],
        branch_label=normalized["branch_label"],
        intensity=normalized["intensity"],
        intensity_label=normalized["intensity_label"],
        copy_mode=normalized.get("copy_mode"),
        copy_mode_label=normalized.get("copy_mode_label"),
        when_to_use=normalized["when_to_use"],
        success_marker=normalized["success_marker"],
        guardrail=normalized["guardrail"],
        version=normalized["version"],
        status=normalized["status"],
        source="admin",
        sort_order=next_sort_order,
        metadata_json=normalized.get("metadata_json"),
    )
    db.add(row)
    await db.flush()
    await record_policy_audit_event(
        db,
        row=row,
        actor=admin_user,
        event_type="admin.policy.created",
        after=snapshot_policy_row(row),
    )
    return serialize_policy_row(row)


@router.patch("/policies/{policy_id}", response_model=PolicyLibraryItemResponse)
async def update_admin_policy(
    policy_id: str,
    payload: PolicyLibraryUpdateRequest,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_policy_library_ready(db)
    row = await get_policy_row_or_404(db, policy_id)
    updates = normalize_policy_payload(
        payload.model_dump(exclude_unset=True),
        partial=True,
    )
    if not updates:
        return serialize_policy_row(row)

    before = snapshot_policy_row(row)
    for field, value in updates.items():
        setattr(row, field, value)
    await db.flush()
    await record_policy_audit_event(
        db,
        row=row,
        actor=admin_user,
        event_type="admin.policy.updated",
        before=before,
        after=snapshot_policy_row(row),
    )
    return serialize_policy_row(row)


@router.post("/policies/{policy_id}/toggle", response_model=PolicyLibraryItemResponse)
async def toggle_admin_policy(
    policy_id: str,
    payload: PolicyLibraryToggleRequest,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_policy_library_ready(db)
    row = await get_policy_row_or_404(db, policy_id)
    next_status = payload.status or ("inactive" if row.status == "active" else "active")
    before = snapshot_policy_row(row)
    row.status = next_status
    await db.flush()
    await record_policy_audit_event(
        db,
        row=row,
        actor=admin_user,
        event_type="admin.policy.toggled",
        before=before,
        after=snapshot_policy_row(row),
    )
    return serialize_policy_row(row)


@router.get("/policies/{policy_id}/audit", response_model=list[PolicyAuditEntryResponse])
async def get_admin_policy_audit(
    policy_id: str,
    limit: int = Query(default=12, ge=1, le=40),
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_policy_library_ready(db)
    row = await get_policy_row_or_404(db, policy_id)
    result = await db.execute(
        select(RelationshipEvent)
        .where(
            RelationshipEvent.entity_type == "intervention_policy",
            RelationshipEvent.entity_id == str(row.id),
            RelationshipEvent.event_type.like("admin.policy.%"),
        )
        .order_by(
            RelationshipEvent.occurred_at.desc(),
            RelationshipEvent.created_at.desc(),
        )
        .limit(limit)
    )
    return [serialize_policy_audit_event(event) for event in result.scalars().all()]


@router.post("/policies/{policy_id}/rollback", response_model=PolicyLibraryItemResponse)
async def rollback_admin_policy(
    policy_id: str,
    payload: PolicyLibraryRollbackRequest,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_policy_library_ready(db)
    row = await get_policy_row_or_404(db, policy_id)
    result = await db.execute(
        select(RelationshipEvent).where(
            RelationshipEvent.id == payload.target_event_id,
            RelationshipEvent.entity_type == "intervention_policy",
            RelationshipEvent.entity_id == str(row.id),
            RelationshipEvent.event_type.like("admin.policy.%"),
        )
    )
    target_event = result.scalar_one_or_none()
    if not target_event:
        raise HTTPException(status_code=404, detail="Audit event not found.")

    target_snapshot = dict((target_event.payload or {}).get("after") or {})
    if not target_snapshot:
        raise HTTPException(
            status_code=400,
            detail="Selected audit event cannot be restored.",
        )

    before = snapshot_policy_row(row)
    reorder_result = await db.execute(
        select(InterventionPolicyLibrary).order_by(
            InterventionPolicyLibrary.sort_order.asc(),
            InterventionPolicyLibrary.policy_id.asc(),
        )
    )
    ordered_rows = list(reorder_result.scalars().all())
    before_by_id = {policy.policy_id: snapshot_policy_row(policy) for policy in ordered_rows}
    desired_sort_order = int(target_snapshot.get("sort_order") or row.sort_order or 0)

    apply_policy_snapshot(row, target_snapshot)
    reordered_rows = [policy for policy in ordered_rows if policy.id != row.id]
    desired_sort_order = max(0, min(desired_sort_order, len(reordered_rows)))
    reordered_rows.insert(desired_sort_order, row)
    for sort_order, policy in enumerate(reordered_rows):
        policy.sort_order = sort_order
    await db.flush()
    after = snapshot_policy_row(row)
    if before == after:
        raise HTTPException(
            status_code=400,
            detail="Policy already matches the selected version.",
        )

    await record_policy_audit_event(
        db,
        row=row,
        actor=admin_user,
        event_type="admin.policy.rolled_back",
        before=before,
        after=after,
        note=payload.note,
        meta={
            "rollback_target_event_id": str(target_event.id),
            "rollback_target_event_type": target_event.event_type,
            "rollback_target_occurred_at": target_event.occurred_at,
        },
    )

    for policy in reordered_rows:
        if policy.id == row.id:
            continue
        policy_before = before_by_id.get(policy.policy_id)
        policy_after = snapshot_policy_row(policy)
        if policy_before and policy_before.get("sort_order") == policy_after.get("sort_order"):
            continue
        await record_policy_audit_event(
            db,
            row=policy,
            actor=admin_user,
            event_type="admin.policy.reordered",
            before=policy_before,
            after=policy_after,
            note="由其他策略的历史回滚触发顺序调整。",
            meta={
                "trigger": "rollback",
                "rollback_target_event_id": str(target_event.id),
                "rollback_target_policy_id": row.policy_id,
            },
        )
    return serialize_policy_row(row)


@router.post("/policies/reorder", response_model=list[PolicyLibraryItemResponse])
async def reorder_admin_policies(
    payload: PolicyLibraryReorderRequest,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_policy_library_ready(db)
    requested_ids = [policy_id.strip() for policy_id in payload.policy_ids if policy_id.strip()]
    if not requested_ids:
        raise HTTPException(status_code=400, detail="policy_ids cannot be empty.")

    result = await db.execute(
        select(InterventionPolicyLibrary).order_by(
            InterventionPolicyLibrary.sort_order.asc(),
            InterventionPolicyLibrary.policy_id.asc(),
        )
    )
    rows = list(result.scalars().all())
    row_by_id = {row.policy_id: row for row in rows}

    missing_ids = [policy_id for policy_id in requested_ids if policy_id not in row_by_id]
    if missing_ids:
        joined = ", ".join(missing_ids)
        raise HTTPException(status_code=404, detail=f"Unknown policy_ids: {joined}")

    ordered_rows: list[InterventionPolicyLibrary] = []
    seen_ids: set[str] = set()
    for requested_id in requested_ids:
        ordered_rows.append(row_by_id[requested_id])
        seen_ids.add(requested_id)
    ordered_rows.extend(row for row in rows if row.policy_id not in seen_ids)

    before_by_id = {row.policy_id: snapshot_policy_row(row) for row in ordered_rows}
    for sort_order, row in enumerate(ordered_rows):
        row.sort_order = sort_order

    await db.flush()
    for row in ordered_rows:
        before = before_by_id.get(row.policy_id)
        after = snapshot_policy_row(row)
        if before and before.get("sort_order") == after.get("sort_order"):
            continue
        await record_policy_audit_event(
            db,
            row=row,
            actor=admin_user,
            event_type="admin.policy.reordered",
            before=before,
            after=after,
            meta={"requested_policy_ids": requested_ids},
        )
    return [serialize_policy_row(row) for row in ordered_rows]
