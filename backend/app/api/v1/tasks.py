"""每日关系任务接口：支持今天/明天双层 AI 任务规划。"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.attachment import analyze_attachment_style
from app.api.deps import get_current_user, validate_pair_access
from app.core.database import get_db
from app.core.time import current_local_date
from app.models import (
    Checkin,
    Pair,
    PairStatus,
    RelationshipEvent,
    RelationshipTask,
    TaskStatus,
    User,
)
from app.schemas import (
    TaskCreateRequest,
    TaskFeedbackRequest,
    TaskFeedbackResponse,
    TaskResultRequest,
    TaskUpdateRequest,
)
from app.services.display_labels import status_label, task_category_label
from app.services.privacy_sandbox import sanitize_event_payload
from app.services.relationship_intelligence import (
    record_relationship_event,
    refresh_profile_and_plan,
)
from app.services.request_cooldown_store import consume_request_cooldown
from app.services.test_accounts import is_relaxed_test_account
from app.services.task_adaptation import (
    build_daily_pack_label,
    build_daily_task_note,
    clamp_daily_note_length,
    build_pair_task_adaptation,
    build_simple_daily_tasks,
    personalize_task_payloads,
)
from app.services.task_feedback import get_latest_task_feedback_map
from app.services.task_planner import (
    MAX_MANUAL_TASKS_PER_DATE,
    TaskPlannerError,
    build_encouragement_copy,
    build_planning_note,
    generate_ai_task_pack,
    generate_ai_task_refresh,
    get_task_batch_event,
    mark_tomorrow_plan_viewed,
    normalize_task_importance_level,
    resolve_date_scope,
    resolve_effective_task_planner_settings,
    sort_tasks_by_status_and_importance,
)

router = APIRouter(prefix="/tasks", tags=["关系任务"])
logger = logging.getLogger(__name__)

ATTACHMENT_ANALYSIS_WINDOW_SECONDS = 60
ATTACHMENT_ANALYSIS_MAX_ATTEMPTS = 2
ATTACHMENT_ANALYSIS_MIN_CHECKINS = 5
TASK_REFRESH_WINDOW_SECONDS = 60
TASK_REFRESH_MAX_ATTEMPTS = 2

ATTACHMENT_LABELS = {
    "secure": "安全型",
    "anxious": "焦虑型",
    "avoidant": "回避型",
    "fearful": "恐惧型",
}


def _attachment_item(
    attachment_type: str | None,
    *,
    confidence: float | None = None,
    analysis: str | None = None,
    growth_suggestion: str | None = None,
) -> dict:
    normalized_type = str(attachment_type or "unknown").strip().lower() or "unknown"
    payload = {
        "type": normalized_type,
        "label": ATTACHMENT_LABELS.get(normalized_type, "未分析"),
    }
    if confidence is not None:
        payload["confidence"] = confidence
    if analysis:
        payload["analysis"] = analysis
    if growth_suggestion:
        payload["growth_suggestion"] = growth_suggestion
    return payload


async def _analyze_attachment_from_checkins(
    checkins: list[Checkin],
    *,
    min_checkins: int = ATTACHMENT_ANALYSIS_MIN_CHECKINS,
) -> dict | None:
    if len(checkins) < max(0, min_checkins):
        return None

    mood_scores = [c.mood_score for c in checkins if c.mood_score is not None]
    initiative_counts = {"me": 0, "partner": 0, "equal": 0}
    deep_conv_count = 0
    interaction_sum = 0

    for checkin in checkins:
        if checkin.interaction_initiative:
            initiative_counts[checkin.interaction_initiative] = (
                initiative_counts.get(checkin.interaction_initiative, 0) + 1
            )
        if checkin.deep_conversation:
            deep_conv_count += 1
        if checkin.interaction_freq:
            interaction_sum += checkin.interaction_freq

    total = len(checkins) or 1
    content_summary = " | ".join(checkin.content[:30] for checkin in checkins[:5])
    if not content_summary:
        content_summary = "测试账号样本不足，先生成一版可用于功能验证的参考分析。"
    return await analyze_attachment_style(
        mood_scores=mood_scores,
        initiative_counts=initiative_counts,
        deep_conv_rate=deep_conv_count * 100 / total,
        avg_interaction=interaction_sum / total,
        content_summary=content_summary,
    )


def _serialize_pair_attachment_response(pair: Pair, user: User) -> dict:
    is_user_a = str(user.id) == str(pair.user_a_id)
    my_type = pair.attachment_style_a if is_user_a else pair.attachment_style_b
    partner_type = pair.attachment_style_b if is_user_a else pair.attachment_style_a

    return {
        "scope": "pair",
        "pair_id": str(pair.id),
        "attachment_a": _attachment_item(pair.attachment_style_a),
        "attachment_b": _attachment_item(pair.attachment_style_b),
        "my_attachment": _attachment_item(my_type),
        "partner_attachment": _attachment_item(partner_type),
        "analyzed_at": (
            str(pair.attachment_analyzed_at) if pair.attachment_analyzed_at else None
        ),
    }


async def _get_latest_solo_attachment_event(
    db: AsyncSession,
    user_id: uuid.UUID,
):
    result = await db.execute(
        select(RelationshipEvent)
        .where(
            RelationshipEvent.user_id == user_id,
            RelationshipEvent.pair_id.is_(None),
            RelationshipEvent.event_type == "attachment.analyzed",
        )
        .order_by(
            RelationshipEvent.occurred_at.desc(),
            RelationshipEvent.created_at.desc(),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


def _serialize_solo_attachment_response(event: RelationshipEvent | None) -> dict:
    payload = event.payload if event else {}
    my_attachment = payload.get("my_attachment") or _attachment_item("unknown")
    return {
        "scope": "solo",
        "pair_id": None,
        "my_attachment": my_attachment,
        "partner_attachment": None,
        "analyzed_at": (
            (event.occurred_at.isoformat() if event and event.occurred_at else None)
            or payload.get("analyzed_at")
        ),
    }


def _fallback_daily_strategy() -> dict:
    return {
        "intensity": "steady",
        "label": "稳定版",
        "momentum": "none",
        "task_limit": 5,
        "plan_type": None,
        "reason": "当前还没有稳定的任务策略，先按默认节奏给出轻量安排。",
        "support_message": "先保持稳定记录和轻量互动。",
    }


def _fallback_daily_pack(
    strategy: dict,
    *,
    effective_settings: dict[str, object],
    date_scope: str,
) -> dict:
    tasks = build_simple_daily_tasks(strategy)
    if not tasks:
        tasks = [
            {
                "title": "先完成一条轻量记录",
                "description": "用一句话写下今天关系里最值得留意的变化。",
                "category": "reflection",
            },
            {
                "title": "发起一次低压力连接",
                "description": "找一个不容易引发争执的话题，保持十分钟轻量互动。",
                "category": "connection",
            },
            {
                "title": "留一句后续复盘",
                "description": "记录今天哪种表达方式更容易被听见。",
                "category": "reflection",
            },
        ]
    return {
        "tasks": tasks,
        "daily_note": build_daily_task_note(strategy, randomize=True),
        "planning_note": build_planning_note(
            strategy=strategy,
            effective_settings=effective_settings,
        ),
        "daily_pack_label": build_daily_pack_label(strategy),
        "date_scope": date_scope,
    }


def _as_uuid(
    value: uuid.UUID | str,
    *,
    detail: str,
    status_code: int,
) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status_code, detail=detail) from exc


def _task_visible_to_user(task: RelationshipTask, user: User) -> bool:
    return task.user_id is None or str(task.user_id) == str(user.id)


def _ensure_task_operator(task: RelationshipTask, user: User, pair: Pair | None) -> None:
    if not pair or str(user.id) not in (str(pair.user_a_id), str(pair.user_b_id)):
        raise HTTPException(status_code=403, detail="无权操作")
    if task.user_id is not None and str(task.user_id) != str(user.id):
        raise HTTPException(status_code=403, detail="该任务仅限指定用户操作")


def _task_source(task: RelationshipTask) -> str:
    return str(getattr(task, "source", "") or "system").strip().lower() or "system"


def _task_target_scope(task: RelationshipTask) -> str:
    return "both" if task.user_id is None else "self"


def _sort_tasks_for_display(tasks: list[RelationshipTask]) -> list[RelationshipTask]:
    return sort_tasks_by_status_and_importance(tasks)


def _resolve_manual_task_target_user_id(
    target_scope: str,
    user: User,
    pair: Pair,
) -> uuid.UUID | None:
    normalized_scope = str(target_scope or "self").strip().lower()
    if normalized_scope == "both":
        return None
    if normalized_scope == "self":
        return user.id
    raise HTTPException(
        status_code=400,
        detail="当前版本暂不支持直接给对方单独布置任务",
    )


async def _load_task_strategy(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> tuple[dict, dict | None]:
    try:
        return await build_pair_task_adaptation(
            db,
            pair_id=pair_id,
            user_id=user_id,
        )
    except Exception:
        logger.exception(
            "Failed to build daily task adaptation strategy",
            extra={"pair_id": str(pair_id), "user_id": str(user_id) if user_id else None},
        )
        return _fallback_daily_strategy(), None


async def _count_manual_tasks_for_date(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    for_date: date,
    exclude_task_id: uuid.UUID | None = None,
) -> int:
    result = await db.execute(
        select(RelationshipTask).where(
            RelationshipTask.pair_id == pair_id,
            RelationshipTask.due_date == for_date,
            RelationshipTask.source == "manual",
        )
    )
    tasks = result.scalars().all()
    if exclude_task_id:
        tasks = [task for task in tasks if str(task.id) != str(exclude_task_id)]
    return len(tasks)


async def _ensure_manual_task_capacity(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    for_date: date,
    exclude_task_id: uuid.UUID | None = None,
) -> None:
    count = await _count_manual_tasks_for_date(
        db,
        pair_id=pair_id,
        for_date=for_date,
        exclude_task_id=exclude_task_id,
    )
    if count >= MAX_MANUAL_TASKS_PER_DATE:
        raise HTTPException(
            status_code=400,
            detail=f"这一天的手动任务最多 {MAX_MANUAL_TASKS_PER_DATE} 条",
        )


def _task_layer_metadata(
    *,
    batch_event: RelationshipEvent | None,
    strategy: dict,
    effective_settings: dict[str, object],
    date_scope: str,
) -> tuple[str, str, str]:
    payload = batch_event.payload if batch_event and isinstance(batch_event.payload, dict) else {}
    daily_note = str(payload.get("daily_note") or "").strip() or build_daily_task_note(
        strategy, randomize=True
    )
    daily_note = clamp_daily_note_length(daily_note)
    daily_pack_label = str(payload.get("daily_pack_label") or "").strip() or build_daily_pack_label(
        strategy
    )
    planning_note = str(payload.get("planning_note") or "").strip()
    if not planning_note:
        planning_note = build_planning_note(
            strategy=strategy,
            effective_settings=effective_settings,
        )
    if date_scope == "tomorrow":
        daily_note = planning_note
    return daily_note, daily_pack_label, planning_note


def _task_to_dict(
    task: RelationshipTask,
    *,
    viewer: User | None = None,
    feedback: dict | None = None,
) -> dict:
    source = _task_source(task)
    importance_level = normalize_task_importance_level(
        getattr(task, "importance_level", "medium")
    )
    editable = bool(
        source == "manual"
        and task.status == TaskStatus.PENDING
        and viewer
        and getattr(task, "created_by_user_id", None)
        and str(getattr(task, "created_by_user_id")) == str(viewer.id)
    )
    return {
        "id": str(task.id),
        "pair_id": (
            str(getattr(task, "pair_id", None))
            if getattr(task, "pair_id", None)
            else None
        ),
        "user_id": str(getattr(task, "user_id", None))
        if getattr(task, "user_id", None)
        else None,
        "title": task.title,
        "description": task.description,
        "category": task.category,
        "category_label": task_category_label(task.category),
        "source": source,
        "is_manual": source == "manual",
        "status": task.status.value,
        "status_label": status_label(task.status.value),
        "importance_level": importance_level,
        "refreshable": bool(source == "system" and task.status == TaskStatus.PENDING),
        "editable": editable,
        "importance_adjustable": bool(task.status == TaskStatus.PENDING),
        "target_user_id": str(task.user_id) if task.user_id else None,
        "target_scope": _task_target_scope(task),
        "created_by_user_id": (
            str(getattr(task, "created_by_user_id", None))
            if getattr(task, "created_by_user_id", None)
            else None
        ),
        "parent_task_id": (
            str(getattr(task, "parent_task_id", None))
            if getattr(task, "parent_task_id", None)
            else None
        ),
        "due_date": str(task.due_date),
        "completed_at": str(task.completed_at) if task.completed_at else None,
        "feedback": feedback,
        "needs_feedback": bool(task.status == TaskStatus.COMPLETED and not feedback),
    }


@router.get("/daily/{pair_id}")
async def get_daily_tasks(
    pair_id: uuid.UUID,
    for_date: date | None = Query(default=None),
    date_scope: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair = await validate_pair_access(pair_id, user, db, require_active=True)
    if not pair.user_b_id:
        raise HTTPException(status_code=400, detail="配对尚未完成")

    requested_date_scope = str(date_scope or "").strip().lower()
    if requested_date_scope and requested_date_scope not in {"today", "tomorrow"}:
        raise HTTPException(status_code=400, detail="安排范围只能是 today 或 tomorrow")
    today = current_local_date()
    if for_date:
        target_date = for_date
    elif requested_date_scope == "tomorrow":
        target_date = today + timedelta(days=1)
    else:
        target_date = today
    resolved_date_scope = resolve_date_scope(target_date)
    if requested_date_scope and requested_date_scope != resolved_date_scope:
        raise HTTPException(status_code=400, detail="日期和安排范围不一致")
    effective_settings = resolve_effective_task_planner_settings(
        user.product_prefs,
        pair.task_planner_settings,
    )

    existing_result = await db.execute(
        select(RelationshipTask).where(
            RelationshipTask.pair_id == pair.id,
            RelationshipTask.due_date == target_date,
        )
    )
    existing_tasks = existing_result.scalars().all()
    strategy, scorecard = await _load_task_strategy(
        db,
        pair_id=pair.id,
        user_id=user.id,
    )

    system_tasks = [task for task in existing_tasks if _task_source(task) == "system"]
    if not system_tasks:
        try:
            pack = await generate_ai_task_pack(
                db,
                pair=pair,
                for_date=target_date,
                strategy=strategy,
                scorecard=scorecard,
                effective_settings=effective_settings,
                user_id=user.id,
            )
        except TaskPlannerError as exc:
            logger.warning(
                "Falling back to simple daily tasks after planner failure",
                extra={"pair_id": str(pair.id), "for_date": target_date.isoformat()},
                exc_info=exc,
            )
            pack = _fallback_daily_pack(
                strategy,
                effective_settings=effective_settings,
                date_scope=resolved_date_scope,
            )

        generated_tasks: list[RelationshipTask] = []
        for item in pack["tasks"]:
            task = RelationshipTask(
                pair_id=pair.id,
                user_id=None,
                title=item["title"],
                description=item["description"],
                category=item["category"],
                source="system",
                due_date=target_date,
            )
            db.add(task)
            generated_tasks.append(task)
        await db.flush()

        await record_relationship_event(
            db,
            event_type="task.generated",
            pair_id=pair.id,
            user_id=user.id,
            entity_type="daily_task_batch",
            entity_id=f"{pair.id}:{target_date.isoformat()}",
            payload={
                "for_date": target_date.isoformat(),
                "date_scope": pack.get("date_scope") or resolved_date_scope,
                "task_count": len(generated_tasks),
                "daily_note": pack.get("daily_note"),
                "planning_note": pack.get("planning_note"),
                "daily_pack_label": pack.get("daily_pack_label"),
                "plan_id": str(scorecard.get("plan_id"))
                if scorecard and scorecard.get("plan_id")
                else None,
                "intensity": strategy.get("intensity"),
                "momentum": strategy.get("momentum"),
                "plan_type": strategy.get("plan_type"),
                "effective_settings": effective_settings,
                "task_ids": [str(task.id) for task in generated_tasks],
            },
            idempotency_key=f"task-batch:{pair.id}:{target_date.isoformat()}",
        )
        existing_tasks = existing_tasks + generated_tasks

    if resolved_date_scope == "tomorrow":
        await mark_tomorrow_plan_viewed(
            db,
            pair_id=pair.id,
            user_id=user.id,
            for_date=target_date,
        )

    visible_tasks = [
        task for task in existing_tasks if _task_visible_to_user(task, user)
    ]
    visible_tasks = _sort_tasks_for_display(visible_tasks)
    feedback_map = await get_latest_task_feedback_map(
        db,
        task_ids=[task.id for task in visible_tasks],
        pair_id=pair.id,
        user_id=user.id,
    )
    task_payloads = personalize_task_payloads(
        [
            _task_to_dict(task, viewer=user, feedback=feedback_map.get(str(task.id)))
            for task in visible_tasks
        ],
        strategy,
    )

    manual_task_count = len(
        [task for task in existing_tasks if _task_source(task) == "manual"]
    )
    batch_event = await get_task_batch_event(db, pair_id=pair.id, for_date=target_date)
    daily_note, daily_pack_label, planning_note = _task_layer_metadata(
        batch_event=batch_event,
        strategy=strategy,
        effective_settings=effective_settings,
        date_scope=resolved_date_scope,
    )
    completed_count = sum(1 for task in visible_tasks if task.status == TaskStatus.COMPLETED)
    remaining_count = max(0, len(visible_tasks) - completed_count)

    return {
        "date": str(target_date),
        "for_date": str(target_date),
        "date_scope": resolved_date_scope,
        "tasks": task_payloads,
        "daily_note": daily_note,
        "daily_pack_label": daily_pack_label,
        "planning_note": planning_note if resolved_date_scope == "tomorrow" else None,
        "encouragement_copy": (
            build_encouragement_copy(
                completed_count=completed_count,
                remaining_count=remaining_count,
            )
            if resolved_date_scope == "today"
            else None
        ),
        "manual_task_count": manual_task_count,
        "manual_task_limit": MAX_MANUAL_TASKS_PER_DATE,
        "manual_task_limit_reached": manual_task_count >= MAX_MANUAL_TASKS_PER_DATE,
        "effective_settings": effective_settings,
        "combination_insight": daily_note,
        "attachment_a": pair.attachment_style_a,
        "attachment_b": pair.attachment_style_b,
        "adaptive_strategy": strategy,
        "plan_scorecard": scorecard,
    }


@router.post("/manual/{pair_id}")
async def create_manual_task(
    pair_id: uuid.UUID,
    req: TaskCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair = await validate_pair_access(pair_id, user, db, require_active=True)
    if pair.status != PairStatus.ACTIVE or not pair.user_b_id:
        raise HTTPException(status_code=400, detail="配对尚未完成")

    parent_task = None
    if req.parent_task_id:
        parent_task = await db.get(RelationshipTask, req.parent_task_id)
        if not parent_task or str(parent_task.pair_id) != str(pair.id):
            raise HTTPException(status_code=404, detail="父任务不存在")

    resolved_due_date = req.due_date or (
        parent_task.due_date if parent_task else current_local_date()
    )
    await _ensure_manual_task_capacity(
        db,
        pair_id=pair.id,
        for_date=resolved_due_date,
    )
    target_user_id = _resolve_manual_task_target_user_id(req.target_scope, user, pair)
    title = req.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="任务标题不能为空")

    task = RelationshipTask(
        pair_id=pair.id,
        user_id=target_user_id,
        created_by_user_id=user.id,
        parent_task_id=parent_task.id if parent_task else None,
        title=title,
        description=req.description.strip(),
        category=req.category.strip().lower() or "activity",
        importance_level=normalize_task_importance_level(req.importance_level),
        due_date=resolved_due_date,
        source="manual",
    )
    db.add(task)
    await db.flush()

    await record_relationship_event(
        db,
        event_type="task.generated",
        pair_id=pair.id,
        user_id=user.id,
        entity_type="relationship_task",
        entity_id=task.id,
        payload={
            "source": "manual",
            "title": task.title,
            "category": task.category,
            "importance_level": normalize_task_importance_level(task.importance_level),
            "due_date": str(task.due_date),
            "target_scope": req.target_scope,
            "parent_task_id": str(task.parent_task_id) if task.parent_task_id else None,
        },
        idempotency_key=f"manual-task:{task.id}",
    )
    await refresh_profile_and_plan(db, pair_id=pair.id)
    return {"message": "任务已创建", "task": _task_to_dict(task, viewer=user)}


@router.patch("/{task_id}")
async def update_task(
    task_id: str,
    req: TaskUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task_uuid = _as_uuid(task_id, detail="无效的任务ID格式", status_code=400)
    task = await db.get(RelationshipTask, task_uuid)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    pair = await db.get(Pair, task.pair_id)
    _ensure_task_operator(task, user, pair)
    if task.status != TaskStatus.PENDING:
        raise HTTPException(status_code=400, detail="只有未完成任务才能调整")

    source = _task_source(task)
    original_importance = normalize_task_importance_level(task.importance_level)
    target_due_date = req.due_date or task.due_date

    if source == "system":
        if any(
            value is not None
            for value in [
                req.title,
                req.description,
                req.category,
                req.target_scope,
                req.due_date,
            ]
        ):
            raise HTTPException(status_code=400, detail="系统任务只支持调整重要度")
        if req.importance_level is None:
            return {"message": "任务未变更", "task": _task_to_dict(task, viewer=user)}

        task.importance_level = normalize_task_importance_level(req.importance_level)
        await db.flush()
        if normalize_task_importance_level(task.importance_level) != original_importance:
            await record_relationship_event(
                db,
                event_type="task.importance_changed",
                pair_id=task.pair_id,
                user_id=user.id,
                entity_type="relationship_task",
                entity_id=task.id,
                payload={
                    "for_date": task.due_date.isoformat(),
                    "old_importance_level": original_importance,
                    "new_importance_level": normalize_task_importance_level(
                        task.importance_level
                    ),
                },
            )
        return {"message": "任务优先级已更新", "task": _task_to_dict(task, viewer=user)}

    if not getattr(task, "created_by_user_id", None) or str(task.created_by_user_id) != str(
        user.id
    ):
        raise HTTPException(status_code=403, detail="只有创建者可以编辑这条手动任务")

    await _ensure_manual_task_capacity(
        db,
        pair_id=task.pair_id,
        for_date=target_due_date,
        exclude_task_id=task.id,
    )

    if req.title is not None:
        title = req.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="任务标题不能为空")
        task.title = title
    if req.description is not None:
        task.description = req.description.strip()
    if req.category is not None:
        task.category = req.category.strip().lower() or "activity"
    if req.target_scope is not None:
        task.user_id = _resolve_manual_task_target_user_id(req.target_scope, user, pair)
    if req.due_date is not None:
        task.due_date = req.due_date
    if req.importance_level is not None:
        task.importance_level = normalize_task_importance_level(req.importance_level)

    await db.flush()
    await record_relationship_event(
        db,
        event_type="task.updated",
        pair_id=task.pair_id,
        user_id=user.id,
        entity_type="relationship_task",
        entity_id=task.id,
        payload={
            "for_date": task.due_date.isoformat(),
            "source": source,
            "importance_level": normalize_task_importance_level(task.importance_level),
        },
    )
    if normalize_task_importance_level(task.importance_level) != original_importance:
        await record_relationship_event(
            db,
            event_type="task.importance_changed",
            pair_id=task.pair_id,
            user_id=user.id,
            entity_type="relationship_task",
            entity_id=task.id,
            payload={
                "for_date": task.due_date.isoformat(),
                "old_importance_level": original_importance,
                "new_importance_level": normalize_task_importance_level(
                    task.importance_level
                ),
            },
        )
    await refresh_profile_and_plan(db, pair_id=task.pair_id)
    return {"message": "任务已更新", "task": _task_to_dict(task, viewer=user)}


@router.post("/{task_id}/refresh")
async def refresh_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task_uuid = _as_uuid(task_id, detail="无效的任务ID格式", status_code=400)
    task = await db.get(RelationshipTask, task_uuid)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    pair = await db.get(Pair, task.pair_id)
    _ensure_task_operator(task, user, pair)
    if _task_source(task) != "system":
        raise HTTPException(status_code=400, detail="只有系统任务支持单条刷新")
    if task.status != TaskStatus.PENDING:
        raise HTTPException(status_code=400, detail="已完成任务不能刷新")
    await consume_request_cooldown(
        bucket="task-refresh",
        scope_key=f"{user.id}:{task.pair_id}",
        window_seconds=TASK_REFRESH_WINDOW_SECONDS,
        max_attempts=TASK_REFRESH_MAX_ATTEMPTS,
        limit_message="任务更换得有点频繁了",
        bypass=is_relaxed_test_account(user),
    )

    siblings_result = await db.execute(
        select(RelationshipTask).where(
            RelationshipTask.pair_id == task.pair_id,
            RelationshipTask.due_date == task.due_date,
            RelationshipTask.source == "system",
        )
    )
    siblings = siblings_result.scalars().all()
    strategy, _scorecard = await _load_task_strategy(
        db,
        pair_id=task.pair_id,
        user_id=user.id,
    )

    original_payload = {
        "title": task.title,
        "description": task.description,
        "category": task.category,
    }
    try:
        replacement = await generate_ai_task_refresh(
            db,
            pair=pair,
            task=task,
            siblings=siblings,
            strategy=strategy,
            user_id=user.id,
        )
    except TaskPlannerError as exc:
        raise HTTPException(status_code=503, detail="AI 刷新失败，请稍后重试") from exc

    task.title = replacement["title"]
    task.description = replacement["description"]
    task.category = replacement["category"]
    await db.flush()

    await record_relationship_event(
        db,
        event_type="task.refreshed",
        pair_id=task.pair_id,
        user_id=user.id,
        entity_type="relationship_task",
        entity_id=task.id,
        payload={
            "for_date": task.due_date.isoformat(),
            "old": original_payload,
            "new": replacement,
        },
    )
    return {
        "message": "这条任务已经换好了",
        "for_date": task.due_date.isoformat(),
        "date_scope": resolve_date_scope(task.due_date),
        "task": _task_to_dict(task, viewer=user),
    }


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if task_id.startswith("demo-"):
        return {
            "message": "任务已完成 ✅",
            "task": {"id": task_id, "status": "completed"},
        }

    valid_uuid = _as_uuid(task_id, detail="无效的任务ID格式", status_code=400)
    task = await db.get(RelationshipTask, valid_uuid)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    pair = await db.get(Pair, task.pair_id)
    _ensure_task_operator(task, user, pair)

    if task.due_date and task.due_date > current_local_date():
        raise HTTPException(status_code=400, detail="还没到计划日期，先不用标记完成")
    if task.status == TaskStatus.COMPLETED:
        return {"task": _task_to_dict(task, viewer=user)}
    if task.status == TaskStatus.SKIPPED:
        raise HTTPException(status_code=400, detail="已跳过的安排不能标记完成")
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()

    await record_relationship_event(
        db,
        event_type="task.completed",
        pair_id=task.pair_id,
        user_id=user.id,
        entity_type="relationship_task",
        entity_id=task.id,
        payload={
            "category": task.category,
            "title": task.title,
            "importance_level": normalize_task_importance_level(task.importance_level),
            "due_date": str(task.due_date),
        },
        idempotency_key=f"task:{task.id}:completed:{task.completed_at.isoformat()}",
        occurred_at=task.completed_at,
    )
    await refresh_profile_and_plan(db, pair_id=task.pair_id)
    return {"message": "任务已完成 ✅", "task": _task_to_dict(task, viewer=user)}


@router.post("/{task_id}/reopen")
async def reopen_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task_uuid = _as_uuid(task_id, detail="无效的任务ID格式", status_code=400)
    task = await db.get(RelationshipTask, task_uuid)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    pair = await db.get(Pair, task.pair_id)
    _ensure_task_operator(task, user, pair)
    if task.status == TaskStatus.SKIPPED:
        raise HTTPException(status_code=400, detail="已取消的安排不能修改结果")
    if task.status == TaskStatus.COMPLETED:
        task.status = TaskStatus.PENDING
        task.completed_at = None
        await db.flush()
        await record_relationship_event(
            db, event_type="task.reopened", pair_id=task.pair_id, user_id=user.id,
            entity_type="relationship_task", entity_id=task.id,
            payload={"title": task.title, "due_date": str(task.due_date)},
        )
        await refresh_profile_and_plan(db, pair_id=task.pair_id)
    return {"task": _task_to_dict(task, viewer=user)}


@router.post("/{task_id}/feedback", response_model=TaskFeedbackResponse)
async def submit_task_feedback(
    task_id: str,
    req: TaskFeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task_uuid = _as_uuid(task_id, detail="无效的任务ID格式", status_code=400)
    task = await db.get(RelationshipTask, task_uuid)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    pair = await db.get(Pair, task.pair_id)
    _ensure_task_operator(task, user, pair)
    if task.due_date and task.due_date > current_local_date():
        raise HTTPException(status_code=400, detail="这件事还没到计划日期，先不用反馈")
    if task.status != TaskStatus.COMPLETED and not (
        task.status == TaskStatus.PENDING and req.outcome in {'not_yet', 'difficult'}
    ):
        raise HTTPException(status_code=400, detail="请先完成任务，再提交反馈")
    if task.status == TaskStatus.COMPLETED and req.outcome == 'not_yet':
        raise HTTPException(status_code=400, detail="这件事已标为完成，请选择实际结果")

    result = await db.execute(
        select(RelationshipEvent)
        .where(
            RelationshipEvent.event_type == "task.feedback_submitted",
            RelationshipEvent.entity_type == "relationship_task",
            RelationshipEvent.entity_id == str(task.id),
            RelationshipEvent.user_id == user.id,
        )
        .order_by(
            RelationshipEvent.occurred_at.desc(),
            RelationshipEvent.created_at.desc(),
        )
        .limit(1)
    )
    feedback_event = result.scalar_one_or_none()
    submitted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    payload = {
        "outcome": req.outcome,
        "usefulness_score": req.usefulness_score,
        "friction_score": req.friction_score,
        "relationship_shift_score": req.relationship_shift_score,
        "note": req.note,
        "title": task.title,
        "category": task.category,
        "importance_level": normalize_task_importance_level(task.importance_level),
        "due_date": str(task.due_date),
    }
    if feedback_event:
        feedback_event.payload = sanitize_event_payload(payload)
        feedback_event.occurred_at = submitted_at
    else:
        feedback_event = await record_relationship_event(
            db,
            event_type="task.feedback_submitted",
            pair_id=task.pair_id,
            user_id=user.id,
            entity_type="relationship_task",
            entity_id=task.id,
            payload=payload,
            occurred_at=submitted_at,
        )

    await db.flush()
    await refresh_profile_and_plan(db, pair_id=task.pair_id)

    return TaskFeedbackResponse(
        task_id=task.id,
        outcome=req.outcome,
        usefulness_score=req.usefulness_score,
        friction_score=req.friction_score,
        relationship_shift_score=req.relationship_shift_score,
        note=req.note,
        submitted_at=feedback_event.occurred_at or submitted_at,
    )


@router.post("/{task_id}/result")
async def save_task_result(
    task_id: str,
    req: TaskResultRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task_uuid = _as_uuid(task_id, detail="无效的任务ID格式", status_code=400)
    task = await db.get(RelationshipTask, task_uuid, with_for_update=True, populate_existing=True)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    pair = await db.get(Pair, task.pair_id)
    _ensure_task_operator(task, user, pair)
    if task.status == TaskStatus.SKIPPED:
        raise HTTPException(status_code=400, detail="已取消的安排不能修改结果")
    if task.due_date and task.due_date > current_local_date():
        raise HTTPException(status_code=400, detail="还没到计划日期，先不用填写结果")

    # Completion and feedback either both persist or both roll back.
    async with db.begin_nested():
        if req.status == 'completed':
            await complete_task(task_id, user, db)
        else:
            await reopen_task(task_id, user, db)
        if req.feedback is not None:
            feedback = (await submit_task_feedback(task_id, req.feedback, user, db)).model_dump(mode='json')
        else:
            # Keep only an audit marker, not a second copy of cleared private text.
            events = (await db.execute(select(RelationshipEvent).where(
                RelationshipEvent.event_type == 'task.feedback_submitted',
                RelationshipEvent.entity_type == 'relationship_task',
                RelationshipEvent.entity_id == str(task.id),
                RelationshipEvent.pair_id == task.pair_id,
                RelationshipEvent.user_id == user.id,
            ))).scalars().all()
            for event in events:
                event.event_type = 'task.feedback_cleared'
                event.payload = {'summary': '这条安排的反馈已清除'}
            await db.flush()
            if events:
                await refresh_profile_and_plan(db, pair_id=task.pair_id)
            feedback = None
        return {'task': _task_to_dict(task, viewer=user, feedback=feedback)}


@router.get("/attachment/{pair_id}")
async def get_attachment_analysis(
    pair_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair = await validate_pair_access(pair_id, user, db, require_active=True)
    return _serialize_pair_attachment_response(pair, user)


@router.get("/attachment")
async def get_solo_attachment_analysis(
    mode: str = Query(default="pair"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if str(mode or "").strip().lower() != "solo":
        raise HTTPException(status_code=400, detail="当前只支持 mode=solo")

    latest_event = await _get_latest_solo_attachment_event(db, user.id)
    return _serialize_solo_attachment_response(latest_event)


@router.post("/attachment/{pair_id}/analyze")
async def trigger_attachment_analysis(
    pair_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair = await validate_pair_access(pair_id, user, db, require_active=True)
    if not pair.user_b_id:
        raise HTTPException(status_code=400, detail="配对尚未完成")
    relaxed_test_account = is_relaxed_test_account(user)
    await consume_request_cooldown(
        bucket="attachment-analysis",
        scope_key=f"{user.id}:{pair.id}",
        window_seconds=ATTACHMENT_ANALYSIS_WINDOW_SECONDS,
        max_attempts=ATTACHMENT_ANALYSIS_MAX_ATTEMPTS,
        limit_message="依恋分析得有点频繁了",
        bypass=relaxed_test_account,
    )

    for uid, side in [(pair.user_a_id, "a"), (pair.user_b_id, "b")]:
        result = await db.execute(
            select(Checkin)
            .where(Checkin.pair_id == pair.id, Checkin.user_id == uid)
            .order_by(Checkin.checkin_date.desc())
            .limit(30)
        )
        checkins = result.scalars().all()
        analysis = await _analyze_attachment_from_checkins(
            checkins,
            min_checkins=0 if relaxed_test_account else ATTACHMENT_ANALYSIS_MIN_CHECKINS,
        )
        if not analysis:
            continue

        if side == "a":
            pair.attachment_style_a = analysis.get("primary_type", "secure")
        else:
            pair.attachment_style_b = analysis.get("primary_type", "secure")

    pair.attachment_analyzed_at = datetime.now(timezone.utc).replace(tzinfo=None)

    return {
        "message": "依恋类型分析完成",
        **_serialize_pair_attachment_response(pair, user),
    }


@router.post("/attachment/analyze")
async def trigger_solo_attachment_analysis(
    mode: str = Query(default="pair"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if str(mode or "").strip().lower() != "solo":
        raise HTTPException(status_code=400, detail="当前只支持 mode=solo")
    relaxed_test_account = is_relaxed_test_account(user)
    await consume_request_cooldown(
        bucket="attachment-analysis",
        scope_key=f"{user.id}:solo",
        window_seconds=ATTACHMENT_ANALYSIS_WINDOW_SECONDS,
        max_attempts=ATTACHMENT_ANALYSIS_MAX_ATTEMPTS,
        limit_message="依恋分析得有点频繁了",
        bypass=relaxed_test_account,
    )

    result = await db.execute(
        select(Checkin)
        .where(Checkin.user_id == user.id, Checkin.pair_id.is_(None))
        .order_by(Checkin.checkin_date.desc(), Checkin.created_at.desc())
        .limit(30)
    )
    checkins = result.scalars().all()
    analysis = await _analyze_attachment_from_checkins(
        checkins,
        min_checkins=0 if relaxed_test_account else ATTACHMENT_ANALYSIS_MIN_CHECKINS,
    )
    if not analysis:
        raise HTTPException(status_code=400, detail="至少完成 5 条单人记录后再来分析依恋倾向。")

    my_attachment = _attachment_item(
        analysis.get("primary_type"),
        confidence=analysis.get("confidence"),
        analysis=analysis.get("analysis"),
        growth_suggestion=analysis.get("growth_suggestion"),
    )
    event = await record_relationship_event(
        db,
        event_type="attachment.analyzed",
        user_id=user.id,
        entity_type="attachment_style",
        entity_id=f"solo:{user.id}",
        payload={
            "scope": "solo",
            "sample_size": len(checkins),
            "my_attachment": my_attachment,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await refresh_profile_and_plan(db, user_id=user.id)
    await db.flush()
    return {
        "message": "依恋倾向分析完成",
        **_serialize_solo_attachment_response(event),
    }
