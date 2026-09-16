"""关系里程碑接口：关键节点专属服务"""

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.time import current_local_date
from app.api.deps import get_current_user, validate_pair_access
from app.models import User, Pair, PairStatus, Milestone, Report, ReportType, ReportStatus
from app.ai.reporter import generate_milestone_report

router = APIRouter(prefix="/milestones", tags=["里程碑"])
logger = logging.getLogger(__name__)


@router.post("/")
async def create_milestone(
    pair_id: uuid.UUID,
    milestone_type: str,  # anniversary / proposal / wedding / friendship_day / custom
    title: str,
    milestone_date: str,  # YYYY-MM-DD
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建关系里程碑"""
    pair = await validate_pair_access(pair_id, user, db, require_active=True)

    from datetime import date
    try:
        m_date = date.fromisoformat(milestone_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式不对，请按 2026-03-21 这样的格式填写")

    milestone = Milestone(
        pair_id=pair.id,
        type=milestone_type,
        title=title,
        date=m_date,
    )
    db.add(milestone)
    await db.flush()

    return {
        "id": str(milestone.id),
        "type": milestone.type,
        "title": milestone.title,
        "date": str(milestone.date),
        "message": "里程碑已创建 🎉",
    }


@router.get("/{pair_id}")
async def get_milestones(
    pair_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取里程碑列表"""
    pair = await validate_pair_access(pair_id, user, db, require_active=True)

    result = await db.execute(
        select(Milestone)
        .where(Milestone.pair_id == pair.id)
        .order_by(Milestone.date.desc())
    )
    milestones = result.scalars().all()

    from datetime import date
    today = current_local_date()

    return [
        {
            "id": str(m.id),
            "type": m.type,
            "title": m.title,
            "date": str(m.date),
            "days_until": (m.date - today).days if m.date >= today else None,
            "days_since": (today - m.date).days if m.date < today else 0,
            "reminder_sent": m.reminder_sent,
        }
        for m in milestones
    ]


@router.post("/{milestone_id}/generate-review")
async def generate_review(
    milestone_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 生成关系成长回顾报告"""
    milestone = await db.get(Milestone, milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="里程碑不存在")

    pair = await validate_pair_access(milestone.pair_id, user, db, require_active=True)

    # 获取该里程碑期间的报告数据
    result = await db.execute(
        select(Report)
        .where(Report.pair_id == milestone.pair_id, Report.content.isnot(None))
        .order_by(desc(Report.created_at))
        .limit(30)
    )
    reports = result.scalars().all()

    report_summaries = []
    for r in reports:
        if r.content:
            report_summaries.append({
                "date": str(r.report_date),
                "health_score": r.content.get("health_score") or r.content.get("overall_health_score"),
                "insight": r.content.get("insight", ""),
            })

    # 生成回顾报告
    try:
        review = await generate_milestone_report(
            pair_type=pair.type.value,
            milestone_type=milestone.type,
            milestone_title=milestone.title,
            report_summaries=report_summaries,
        )
        return {
            "milestone_id": str(milestone.id),
            "review": review,
            "message": "关系成长回顾已生成 🎉",
        }
    except Exception as e:
        logger.error(f"生成里程碑报告失败: {e}")
        raise HTTPException(status_code=500, detail="生成失败，请稍后再试")
