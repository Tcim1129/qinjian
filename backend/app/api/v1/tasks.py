"""每日关系任务接口：基于依恋模式的个性化任务推荐"""

import asyncio
import logging
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, validate_pair_access
from app.models import (
    RelationshipEvent,
    User,
    Pair,
    PairStatus,
    Checkin,
    RelationshipTask,
    TaskStatus,
)
from app.ai.attachment import analyze_attachment_style, generate_combination_tasks
from app.schemas import TaskFeedbackRequest, TaskFeedbackResponse
from app.services.task_adaptation import (
    adapt_daily_tasks,
    build_pair_task_adaptation,
    merge_task_insight,
    personalize_task_payloads,
)
from app.services.task_feedback import get_latest_task_feedback_map
from app.services.relationship_intelligence import (
    record_relationship_event,
    refresh_profile_and_plan,
)

router = APIRouter(prefix="/tasks", tags=["关系任务"])
logger = logging.getLogger(__name__)

# 依恋类型中文映射
ATTACHMENT_LABELS = {
    "secure": "安全型",
    "anxious": "焦虑型",
    "avoidant": "回避型",
    "fearful": "恐惧型",
}


def _task_visible_to_user(task: RelationshipTask, user: User) -> bool:
    return task.user_id is None or str(task.user_id) == str(user.id)


def _ensure_task_operator(task: RelationshipTask, user: User, pair: Pair | None) -> None:
    if not pair or str(user.id) not in (str(pair.user_a_id), str(pair.user_b_id)):
        raise HTTPException(status_code=403, detail="无权操作")
    if task.user_id is not None and str(task.user_id) != str(user.id):
        raise HTTPException(status_code=403, detail="该任务仅限指定用户操作")


@router.get("/daily/{pair_id}")
async def get_daily_tasks(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取今日个性化关系任务（基于依恋类型组合）"""
    pair = await validate_pair_access(pair_id, user, db, require_active=True)
    if not pair.user_b_id:
        raise HTTPException(status_code=400, detail="配对尚未完成")

    today = date.today()

    # 检查今天是否已有任务
    existing = await db.execute(
        select(RelationshipTask).where(
            RelationshipTask.pair_id == pair_id, RelationshipTask.due_date == today
        )
    )
    existing_tasks = existing.scalars().all()
    visible_tasks = [task for task in existing_tasks if _task_visible_to_user(task, user)]
    strategy, scorecard = await build_pair_task_adaptation(
        db,
        pair_id=pair_id,
        user_id=user.id,
    )
    if existing_tasks:
        feedback_map = await get_latest_task_feedback_map(
            db,
            task_ids=[task.id for task in visible_tasks],
            pair_id=pair_id,
            user_id=user.id,
        )
        task_payloads = personalize_task_payloads(
            [
                _task_to_dict(t, feedback=feedback_map.get(str(t.id)))
                for t in visible_tasks
            ],
            strategy,
        )
        return {
            "date": str(today),
            "tasks": task_payloads,
            "combination_insight": merge_task_insight("", strategy),
            "attachment_a": pair.attachment_style_a,
            "attachment_b": pair.attachment_style_b,
            "adaptive_strategy": strategy,
            "plan_scorecard": scorecard,
        }

    # 获取双方依恋类型，若未分析则触发分析
    type_a = pair.attachment_style_a or "secure"
    type_b = pair.attachment_style_b or "secure"

    # 用 AI 生成今日任务
    result = {"combination_insight": ""}
    try:
        result = await asyncio.wait_for(
            generate_combination_tasks(pair.type.value, type_a, type_b),
            timeout=6,
        )
        tasks_data = result.get("tasks", [])
    except asyncio.TimeoutError:
        logger.warning("生成任务超时，使用降级任务 pair_id=%s", pair_id)
        tasks_data = [
            {
                "title": "先对齐今天最重要的一件事",
                "description": "今晚只聊一个最需要被理解的点，先不扩展到第二件事。",
                "target": "both",
                "category": "communication",
            },
        ]
        result = {
            "combination_insight": "今天先把最核心的一点说清楚，比一次聊完所有事更重要。"
        }
    except Exception as e:
        logger.error(f"生成任务失败: {e}")
        tasks_data = [
            {
                "title": "今日互动",
                "description": "花10分钟面对面交流",
                "target": "both",
                "category": "communication",
            },
        ]
    tasks_data = adapt_daily_tasks(tasks_data, strategy)

    # 保存任务到数据库
    saved_tasks = []
    for td in tasks_data:
        task = RelationshipTask(
            pair_id=pair_id,
            user_id=str(pair.user_a_id)
            if td.get("target") == "a"
            else (str(pair.user_b_id) if td.get("target") == "b" else None),
            title=td.get("title", "关系任务"),
            description=td.get("description", ""),
            category=td.get("category", "activity"),
            due_date=today,
        )
        db.add(task)
        saved_tasks.append(task)

    await db.flush()
    await record_relationship_event(
        db,
        event_type="task.generated",
        pair_id=pair_id,
        entity_type="daily_task_batch",
        entity_id=f"{pair_id}:{today.isoformat()}",
        payload={
            "task_count": len(saved_tasks),
            "plan_id": str(scorecard.get("plan_id"))
            if scorecard and scorecard.get("plan_id")
            else None,
            "intensity": strategy.get("intensity"),
            "momentum": strategy.get("momentum"),
            "plan_type": strategy.get("plan_type"),
            "copy_mode": strategy.get("copy_mode"),
            "policy_signature": (
                f"{strategy.get('intensity') or 'steady'}:"
                f"{strategy.get('copy_mode') or 'default'}"
            ),
            "policy_selection_mode": (strategy.get("policy_selection") or {}).get(
                "mode"
            ),
            "policy_selection_auto_applied": bool(
                (strategy.get("policy_selection") or {}).get("auto_applied")
            ),
            "selected_policy_signature": (strategy.get("policy_selection") or {}).get(
                "selected_policy_signature"
            ),
            "policy_schedule_mode": (strategy.get("policy_schedule") or {}).get(
                "schedule_mode"
            ),
            "policy_schedule_label": (strategy.get("policy_schedule") or {}).get(
                "schedule_label"
            ),
            "policy_schedule_checkpoint_date": (
                (strategy.get("policy_schedule") or {}).get("checkpoint_date")
            ),
            "category_copy_modes": {
                category: value.get("copy_mode")
                for category, value in (
                    strategy.get("category_preferences") or {}
                ).items()
                if value.get("copy_mode")
            },
        },
        idempotency_key=f"task-batch:{pair_id}:{today.isoformat()}",
    )
    feedback_map = await get_latest_task_feedback_map(
        db,
        task_ids=[
            task.id for task in saved_tasks if _task_visible_to_user(task, user)
        ],
        pair_id=pair_id,
        user_id=user.id,
    )

    task_payloads = personalize_task_payloads(
        [
            _task_to_dict(t, feedback=feedback_map.get(str(t.id)))
            for t in saved_tasks
            if _task_visible_to_user(t, user)
        ],
        strategy,
    )

    return {
        "date": str(today),
        "tasks": task_payloads,
        "combination_insight": merge_task_insight(
            result.get("combination_insight", ""),
            strategy,
        ),
        "attachment_a": type_a,
        "attachment_b": type_b,
        "adaptive_strategy": strategy,
        "plan_scorecard": scorecard,
    }


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记任务完成"""
    if task_id.startswith("demo-"):
        return {
            "message": "任务已完成 ✅",
            "task": {"id": task_id, "status": "completed"},
        }

    import uuid

    try:
        valid_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的任务ID格式")

    task = await db.get(RelationshipTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 验证用户属于该配对
    pair = await db.get(Pair, str(task.pair_id))
    _ensure_task_operator(task, user, pair)

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
            "due_date": str(task.due_date),
        },
        idempotency_key=f"task:{task.id}:completed",
        occurred_at=task.completed_at,
    )
    await refresh_profile_and_plan(db, pair_id=task.pair_id)
    return {"message": "任务已完成 ✅", "task": _task_to_dict(task)}


@router.post("/{task_id}/feedback", response_model=TaskFeedbackResponse)
async def submit_task_feedback(
    task_id: str,
    req: TaskFeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(RelationshipTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    pair = await db.get(Pair, str(task.pair_id))
    _ensure_task_operator(task, user, pair)
    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="请先完成任务，再提交反馈")

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
        "usefulness_score": req.usefulness_score,
        "friction_score": req.friction_score,
        "note": req.note,
        "title": task.title,
        "category": task.category,
        "due_date": str(task.due_date),
    }
    if feedback_event:
        feedback_event.payload = payload
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
        usefulness_score=req.usefulness_score,
        friction_score=req.friction_score,
        note=req.note,
        submitted_at=feedback_event.occurred_at or submitted_at,
    )


@router.get("/attachment/{pair_id}")
async def get_attachment_analysis(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取双方依恋类型分析结果"""
    pair = await validate_pair_access(pair_id, user, db, require_active=True)

    return {
        "pair_id": pair_id,
        "attachment_a": {
            "type": pair.attachment_style_a or "unknown",
            "label": ATTACHMENT_LABELS.get(pair.attachment_style_a, "未分析"),
        },
        "attachment_b": {
            "type": pair.attachment_style_b or "unknown",
            "label": ATTACHMENT_LABELS.get(pair.attachment_style_b, "未分析"),
        },
        "analyzed_at": str(pair.attachment_analyzed_at)
        if pair.attachment_analyzed_at
        else None,
    }


@router.post("/attachment/{pair_id}/analyze")
async def trigger_attachment_analysis(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """触发依恋类型分析（需至少7天打卡数据）"""
    pair = await validate_pair_access(pair_id, user, db, require_active=True)
    if not pair.user_b_id:
        raise HTTPException(status_code=400, detail="配对尚未完成")

    for uid, side in [(pair.user_a_id, "a"), (pair.user_b_id, "b")]:
        # 获取该用户的打卡数据
        result = await db.execute(
            select(Checkin)
            .where(Checkin.pair_id == pair_id, Checkin.user_id == uid)
            .order_by(Checkin.checkin_date.desc())
            .limit(30)
        )
        checkins = result.scalars().all()

        if len(checkins) < 5:
            continue

        # 提取分析维度
        mood_scores = [c.mood_score for c in checkins if c.mood_score]
        initiative_counts = {"me": 0, "partner": 0, "equal": 0}
        deep_conv_count = 0
        interaction_sum = 0

        for c in checkins:
            if c.interaction_initiative:
                initiative_counts[c.interaction_initiative] = (
                    initiative_counts.get(c.interaction_initiative, 0) + 1
                )
            if c.deep_conversation:
                deep_conv_count += 1
            if c.interaction_freq:
                interaction_sum += c.interaction_freq

        total = len(checkins) or 1
        content_summary = " | ".join(c.content[:30] for c in checkins[:5])

        # AI 分析
        analysis = await analyze_attachment_style(
            mood_scores=mood_scores,
            initiative_counts=initiative_counts,
            deep_conv_rate=deep_conv_count * 100 / total,
            avg_interaction=interaction_sum / total,
            content_summary=content_summary,
        )

        if side == "a":
            pair.attachment_style_a = analysis.get("primary_type", "secure")
        else:
            pair.attachment_style_b = analysis.get("primary_type", "secure")

    pair.attachment_analyzed_at = datetime.now(timezone.utc).replace(tzinfo=None)

    return {
        "message": "依恋类型分析完成",
        "attachment_a": pair.attachment_style_a,
        "attachment_b": pair.attachment_style_b,
    }


def _task_to_dict(task: RelationshipTask, *, feedback: dict | None = None) -> dict:
    return {
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "category": task.category,
        "status": task.status.value,
        "target_user_id": str(task.user_id) if task.user_id else None,
        "due_date": str(task.due_date),
        "completed_at": str(task.completed_at) if task.completed_at else None,
        "feedback": feedback,
        "needs_feedback": bool(task.status == TaskStatus.COMPLETED and not feedback),
    }
