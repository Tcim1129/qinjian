"""Runtime helpers for persisted relationship playbooks."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PlaybookRun, PlaybookTransition
from app.services.relationship_playbook import BRANCH_LABELS, build_relationship_playbook


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _scope_filters(
    model,
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
):
    if pair_id:
        return [
            model.pair_id == pair_id,
            getattr(model, "user_id", None).is_(None)
            if hasattr(model, "user_id")
            else True,
        ]
    return [
        model.user_id == user_id,
        model.pair_id.is_(None),
    ]


def _trigger_type_for_branch(branch_code: str) -> str:
    return {
        "stabilize": "risk_guardrail",
        "reduce_load": "friction_backoff",
        "steady": "plan_followthrough",
        "deepen": "momentum_upgrade",
    }.get(branch_code, "plan_followthrough")


def _transition_trigger_type(playbook: dict, transition_type: str) -> str:
    if transition_type == "initialized":
        return "run_started"
    if "branch_changed" in transition_type:
        return _trigger_type_for_branch(str(playbook.get("active_branch") or "steady"))
    return "schedule_progress"


def _transition_summary(
    *,
    playbook: dict,
    transition_type: str,
    previous_branch: str | None,
    previous_day: int | None,
) -> str:
    current_day = int(playbook.get("current_day") or 1)
    branch_label = str(
        playbook.get("active_branch_label")
        or BRANCH_LABELS.get(str(playbook.get("active_branch") or "steady"), "推进中")
    )
    branch_reason = str(playbook.get("branch_reason") or "").strip()

    if transition_type == "initialized":
        return f"剧本已启动，当前进入第 {current_day} 天，先按“{branch_label}”推进。"
    if transition_type == "branch_changed_day_advanced":
        return (
            f"剧本推进到第 {current_day} 天，并切到“{branch_label}”。"
            f"{(' ' + branch_reason) if branch_reason else ''}"
        ).strip()
    if transition_type == "branch_changed":
        previous_label = BRANCH_LABELS.get(str(previous_branch or ""), "上一分支")
        return (
            f"剧本从“{previous_label}”切到“{branch_label}”。"
            f"{(' ' + branch_reason) if branch_reason else ''}"
        ).strip()
    if transition_type == "day_advanced":
        return (
            f"剧本推进到第 {current_day} 天，继续按“{branch_label}”执行。"
            if previous_day
            else f"剧本推进到第 {current_day} 天。"
        )
    return branch_reason or f"剧本保持在“{branch_label}”分支。"


def _serialize_transition(
    transition: PlaybookTransition | None,
    *,
    is_new: bool = False,
) -> dict | None:
    if not transition:
        return None
    return {
        "id": transition.id,
        "transition_type": transition.transition_type,
        "trigger_type": transition.trigger_type,
        "trigger_summary": transition.trigger_summary,
        "from_day": transition.from_day,
        "to_day": transition.to_day,
        "from_branch": transition.from_branch,
        "from_branch_label": (
            BRANCH_LABELS.get(transition.from_branch)
            if transition.from_branch
            else None
        ),
        "to_branch": transition.to_branch,
        "to_branch_label": BRANCH_LABELS.get(transition.to_branch, transition.to_branch),
        "created_at": transition.created_at,
        "is_new": is_new,
    }


async def _get_latest_transition(
    db: AsyncSession, *, run_id: uuid.UUID
) -> PlaybookTransition | None:
    result = await db.execute(
        select(PlaybookTransition)
        .where(PlaybookTransition.run_id == run_id)
        .order_by(desc(PlaybookTransition.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_active_run(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> PlaybookRun | None:
    result = await db.execute(
        select(PlaybookRun)
        .where(
            *_scope_filters(PlaybookRun, pair_id=pair_id, user_id=user_id),
            PlaybookRun.status == "active",
        )
        .order_by(desc(PlaybookRun.updated_at), desc(PlaybookRun.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _close_superseded_runs(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    current_plan_id: uuid.UUID,
    synced_at: datetime,
) -> None:
    result = await db.execute(
        select(PlaybookRun).where(
            *_scope_filters(PlaybookRun, pair_id=pair_id, user_id=user_id),
            PlaybookRun.status == "active",
            PlaybookRun.plan_id != current_plan_id,
        )
    )
    for run in result.scalars().all():
        run.status = "superseded"
        run.last_synced_at = synced_at


async def sync_active_playbook_runtime(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
    viewed: bool = False,
) -> dict | None:
    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    if (normalized_pair_id is None) == (normalized_user_id is None):
        raise ValueError("sync_active_playbook_runtime requires exactly one scope")

    playbook = await build_relationship_playbook(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
    )
    if not playbook:
        return None

    now = _utcnow()
    await _close_superseded_runs(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
        current_plan_id=playbook["plan_id"],
        synced_at=now,
    )
    run_result = await db.execute(
        select(PlaybookRun).where(PlaybookRun.plan_id == playbook["plan_id"]).limit(1)
    )
    run = run_result.scalar_one_or_none()
    latest_transition: PlaybookTransition | None = None
    is_new_transition = False

    if not run:
        run = PlaybookRun(
            plan_id=playbook["plan_id"],
            pair_id=playbook.get("pair_id"),
            user_id=playbook.get("user_id"),
            plan_type=playbook["plan_type"],
            status="active",
            current_day=playbook["current_day"],
            active_branch=playbook["active_branch"],
            branch_reason=playbook.get("branch_reason"),
            branch_started_at=now,
            last_synced_at=now,
            last_viewed_at=now if viewed else None,
            transition_count=1,
        )
        db.add(run)
        await db.flush()

        latest_transition = PlaybookTransition(
            run_id=run.id,
            plan_id=playbook["plan_id"],
            pair_id=playbook.get("pair_id"),
            user_id=playbook.get("user_id"),
            transition_type="initialized",
            trigger_type="run_started",
            trigger_summary=_transition_summary(
                playbook=playbook,
                transition_type="initialized",
                previous_branch=None,
                previous_day=None,
            ),
            from_day=None,
            to_day=playbook["current_day"],
            from_branch=None,
            to_branch=playbook["active_branch"],
        )
        db.add(latest_transition)
        is_new_transition = True
    else:
        previous_branch = run.active_branch
        previous_day = run.current_day
        transition_type: str | None = None

        branch_changed = previous_branch != playbook["active_branch"]
        day_changed = previous_day != playbook["current_day"]

        if branch_changed and day_changed:
            transition_type = "branch_changed_day_advanced"
        elif branch_changed:
            transition_type = "branch_changed"
        elif day_changed:
            transition_type = "day_advanced"

        run.status = "active"
        run.current_day = playbook["current_day"]
        run.active_branch = playbook["active_branch"]
        run.branch_reason = playbook.get("branch_reason")
        run.last_synced_at = now
        if viewed:
            run.last_viewed_at = now
        if branch_changed or not run.branch_started_at:
            run.branch_started_at = now

        if transition_type:
            run.transition_count = int(run.transition_count or 0) + 1
            latest_transition = PlaybookTransition(
                run_id=run.id,
                plan_id=playbook["plan_id"],
                pair_id=playbook.get("pair_id"),
                user_id=playbook.get("user_id"),
                transition_type=transition_type,
                trigger_type=_transition_trigger_type(playbook, transition_type),
                trigger_summary=_transition_summary(
                    playbook=playbook,
                    transition_type=transition_type,
                    previous_branch=previous_branch,
                    previous_day=previous_day,
                ),
                from_day=previous_day,
                to_day=playbook["current_day"],
                from_branch=previous_branch,
                to_branch=playbook["active_branch"],
            )
            db.add(latest_transition)
            is_new_transition = True

    await db.flush()
    if not latest_transition:
        latest_transition = await _get_latest_transition(db, run_id=run.id)

    enriched_playbook = dict(playbook)
    enriched_playbook.update(
        {
            "run_id": run.id,
            "run_status": run.status,
            "branch_started_at": run.branch_started_at,
            "last_synced_at": run.last_synced_at,
            "last_viewed_at": run.last_viewed_at,
            "transition_count": int(run.transition_count or 0),
            "latest_transition": _serialize_transition(
                latest_transition,
                is_new=is_new_transition,
            ),
        }
    )
    return enriched_playbook


async def get_playbook_history(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
    limit: int = 8,
) -> dict | None:
    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    if (normalized_pair_id is None) == (normalized_user_id is None):
        raise ValueError("get_playbook_history requires exactly one scope")

    playbook = await sync_active_playbook_runtime(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
        viewed=False,
    )
    if not playbook:
        return None

    run = await _get_active_run(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
    )
    if not run:
        return None

    transitions_result = await db.execute(
        select(PlaybookTransition)
        .where(PlaybookTransition.run_id == run.id)
        .order_by(desc(PlaybookTransition.created_at))
        .limit(limit)
    )
    transitions = transitions_result.scalars().all()

    return {
        "run_id": run.id,
        "plan_id": playbook["plan_id"],
        "plan_type": playbook["plan_type"],
        "run_status": run.status,
        "active_branch": playbook["active_branch"],
        "active_branch_label": playbook["active_branch_label"],
        "current_day": playbook["current_day"],
        "transition_count": int(run.transition_count or 0),
        "transitions": [
            _serialize_transition(transition, is_new=False) for transition in transitions
        ],
    }
