"""每日关系任务接口：基于依恋模式的个性化任务推荐"""

import logging
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, validate_pair_access
from app.models import (
    User, Pair, PairStatus, Checkin, RelationshipTask, TaskStatus,
)
from app.ai.attachment import analyze_attachment_style, generate_combination_tasks

router = APIRouter(prefix="/tasks", tags=["关系任务"])
logger = logging.getLogger(__name__)

# 依恋类型中文映射
ATTACHMENT_LABELS = {
    "secure": "安全型",
    "anxious": "焦虑型",
    "avoidant": "回避型",
    "fearful": "恐惧型",
}


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
        select(RelationshipTask)
        .where(RelationshipTask.pair_id == pair_id, RelationshipTask.due_date == today)
    )
    existing_tasks = existing.scalars().all()
    if existing_tasks:
        return {
            "date": str(today),
            "tasks": [_task_to_dict(t) for t in existing_tasks],
            "attachment_a": pair.attachment_style_a,
            "attachment_b": pair.attachment_style_b,
        }

    # 获取双方依恋类型，若未分析则触发分析
    type_a = pair.attachment_style_a or "secure"
    type_b = pair.attachment_style_b or "secure"

    # 用 AI 生成今日任务
    try:
        result = await generate_combination_tasks(pair.type.value, type_a, type_b)
        tasks_data = result.get("tasks", [])
    except Exception as e:
        logger.error(f"生成任务失败: {e}")
        tasks_data = [
            {"title": "今日互动", "description": "花10分钟面对面交流", "target": "both", "category": "communication"},
        ]

    # 保存任务到数据库
    saved_tasks = []
    for td in tasks_data[:3]:
        task = RelationshipTask(
            pair_id=pair_id,
            user_id=str(pair.user_a_id) if td.get("target") == "a" else (
                str(pair.user_b_id) if td.get("target") == "b" else None
            ),
            title=td.get("title", "关系任务"),
            description=td.get("description", ""),
            category=td.get("category", "activity"),
            due_date=today,
        )
        db.add(task)
        saved_tasks.append(task)

    await db.flush()

    return {
        "date": str(today),
        "tasks": [_task_to_dict(t) for t in saved_tasks],
        "combination_insight": result.get("combination_insight", ""),
        "attachment_a": type_a,
        "attachment_b": type_b,
    }


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记任务完成"""
    if task_id.startswith("demo-"):
        return {"message": "任务已完成 ✅", "task": {"id": task_id, "status": "completed"}}

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
    if str(user.id) not in (str(pair.user_a_id), str(pair.user_b_id)):
        raise HTTPException(status_code=403, detail="无权操作")

    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    return {"message": "任务已完成 ✅", "task": _task_to_dict(task)}


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
        "analyzed_at": str(pair.attachment_analyzed_at) if pair.attachment_analyzed_at else None,
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
                initiative_counts[c.interaction_initiative] = initiative_counts.get(c.interaction_initiative, 0) + 1
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


def _task_to_dict(task: RelationshipTask) -> dict:
    return {
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "category": task.category,
        "status": task.status.value,
        "target_user_id": str(task.user_id) if task.user_id else None,
        "due_date": str(task.due_date),
        "completed_at": str(task.completed_at) if task.completed_at else None,
    }
