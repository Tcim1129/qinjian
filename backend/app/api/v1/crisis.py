"""危机预警接口：关系危机分级预警 + 差异化干预方案"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, Pair, PairStatus, Report, ReportType

router = APIRouter(prefix="/crisis", tags=["危机预警"])


@router.get("/status/{pair_id}")
async def get_crisis_status(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前危机等级和干预建议（取最近一份报告的 crisis_level）"""
    # 验证用户属于该配对
    pair = await db.get(Pair, pair_id)
    if not pair or pair.status != PairStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="配对不存在或未激活")
    if str(user.id) not in (str(pair.user_a_id), str(pair.user_b_id)):
        raise HTTPException(status_code=403, detail="无权访问该配对")

    # 取最近一份已完成的报告（优先日报，再取周报/月报）
    result = await db.execute(
        select(Report)
        .where(Report.pair_id == pair_id, Report.content.isnot(None))
        .order_by(desc(Report.created_at))
        .limit(1)
    )
    report = result.scalar_one_or_none()

    if not report or not report.content:
        return {
            "crisis_level": "none",
            "intervention": None,
            "source_report_id": None,
            "source_report_type": None,
            "message": "暂无足够数据生成预警",
        }

    content = report.content
    return {
        "crisis_level": content.get("crisis_level", "none"),
        "intervention": content.get("intervention"),
        "source_report_id": str(report.id),
        "source_report_type": report.type.value,
        "report_date": str(report.report_date),
        "health_score": content.get("health_score") or content.get("overall_health_score"),
    }


@router.get("/history/{pair_id}")
async def get_crisis_history(
    pair_id: str,
    limit: int = 30,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取危机等级历史趋势"""
    pair = await db.get(Pair, pair_id)
    if not pair or pair.status != PairStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="配对不存在或未激活")
    if str(user.id) not in (str(pair.user_a_id), str(pair.user_b_id)):
        raise HTTPException(status_code=403, detail="无权访问该配对")

    result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.content.isnot(None),
            Report.type.in_([ReportType.DAILY, ReportType.WEEKLY]),
        )
        .order_by(desc(Report.created_at))
        .limit(limit)
    )
    reports = result.scalars().all()

    history = []
    for r in reports:
        if r.content:
            history.append({
                "date": str(r.report_date),
                "type": r.type.value,
                "crisis_level": r.content.get("crisis_level", "none"),
                "health_score": r.content.get("health_score") or r.content.get("overall_health_score"),
                "intervention_type": (r.content.get("intervention") or {}).get("type", "none"),
            })

    return {"pair_id": pair_id, "history": history}
