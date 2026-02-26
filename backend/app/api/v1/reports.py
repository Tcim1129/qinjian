"""报告接口（Phase 2 增强：支持日报/周报/月报 + 趋势查询）"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, Pair, Checkin, Report, ReportType, PairStatus
from app.schemas import ReportResponse
from app.ai.reporter import generate_daily_report, generate_weekly_report, generate_monthly_report

router = APIRouter(prefix="/reports", tags=["报告"])


@router.post("/generate-daily", response_model=ReportResponse)
async def trigger_daily_report(pair_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """手动触发生成今日报告（双方打卡完成后可调用）"""
    today = date.today()

    # 获取今日双方打卡
    result = await db.execute(
        select(Checkin).where(Checkin.pair_id == pair_id, Checkin.checkin_date == today)
    )
    checkins = result.scalars().all()
    if len(checkins) < 2:
        raise HTTPException(status_code=400, detail="需要双方都完成打卡后才能生成报告")

    # 获取配对信息
    result = await db.execute(select(Pair).where(Pair.id == pair_id))
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="配对不存在")

    # 检查是否已生成
    result = await db.execute(
        select(Report).where(Report.pair_id == pair_id, Report.report_date == today, Report.type == ReportType.DAILY)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # 分离双方打卡
    checkin_a = next((c for c in checkins if c.user_id == pair.user_a_id), checkins[0])
    checkin_b = next((c for c in checkins if c.user_id == pair.user_b_id), checkins[-1])

    # 调用 AI 生成报告
    report_content = await generate_daily_report(
        pair_type=pair.type.value,
        content_a=checkin_a.content,
        content_b=checkin_b.content,
    )

    report = Report(
        pair_id=pair_id,
        type=ReportType.DAILY,
        content=report_content,
        health_score=report_content.get("health_score"),
        report_date=today,
    )
    db.add(report)
    await db.flush()
    return report


@router.post("/generate-weekly", response_model=ReportResponse)
async def trigger_weekly_report(pair_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """生成周报（基于过去7天的日报汇总）"""
    today = date.today()
    week_ago = today - timedelta(days=7)

    # 获取配对
    result = await db.execute(select(Pair).where(Pair.id == pair_id))
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="配对不存在")

    # 检查是否已生成本周报告
    result = await db.execute(
        select(Report).where(
            Report.pair_id == pair_id,
            Report.report_date >= week_ago,
            Report.type == ReportType.WEEKLY,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # 获取过去7天的日报
    result = await db.execute(
        select(Report).where(
            Report.pair_id == pair_id,
            Report.report_date >= week_ago,
            Report.type == ReportType.DAILY,
        ).order_by(Report.report_date)
    )
    daily_reports = [r.content for r in result.scalars().all()]

    if len(daily_reports) < 3:
        raise HTTPException(status_code=400, detail="至少需要3天的日报数据才能生成周报")

    report_content = await generate_weekly_report(pair.type.value, daily_reports)

    report = Report(
        pair_id=pair_id,
        type=ReportType.WEEKLY,
        content=report_content,
        health_score=report_content.get("overall_health_score"),
        report_date=today,
    )
    db.add(report)
    await db.flush()
    return report


@router.post("/generate-monthly", response_model=ReportResponse)
async def trigger_monthly_report(pair_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """生成月报（基于过去30天的周报汇总）"""
    today = date.today()
    month_ago = today - timedelta(days=30)

    result = await db.execute(select(Pair).where(Pair.id == pair_id))
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="配对不存在")

    # 获取过去30天的周报
    result = await db.execute(
        select(Report).where(
            Report.pair_id == pair_id,
            Report.report_date >= month_ago,
            Report.type == ReportType.WEEKLY,
        ).order_by(Report.report_date)
    )
    weekly_reports = [r.content for r in result.scalars().all()]

    if len(weekly_reports) < 2:
        raise HTTPException(status_code=400, detail="至少需要2周的数据才能生成月报")

    report_content = await generate_monthly_report(pair.type.value, weekly_reports)

    report = Report(
        pair_id=pair_id,
        type=ReportType.MONTHLY,
        content=report_content,
        health_score=report_content.get("overall_health_score"),
        report_date=today,
    )
    db.add(report)
    await db.flush()
    return report


@router.get("/latest", response_model=ReportResponse | None)
async def get_latest_report(pair_id: str, report_type: str = "daily", user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取最新报告（可按类型筛选）"""
    query = select(Report).where(Report.pair_id == pair_id)
    if report_type in ("daily", "weekly", "monthly"):
        query = query.where(Report.type == ReportType(report_type))
    query = query.order_by(Report.report_date.desc()).limit(1)

    result = await db.execute(query)
    return result.scalar_one_or_none()


@router.get("/history", response_model=list[ReportResponse])
async def get_report_history(
    pair_id: str, report_type: str = "daily", limit: int = 7,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取报告历史"""
    query = select(Report).where(Report.pair_id == pair_id)
    if report_type in ("daily", "weekly", "monthly"):
        query = query.where(Report.type == ReportType(report_type))
    query = query.order_by(Report.report_date.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/trend", response_model=dict)
async def get_health_trend(pair_id: str, days: int = 14, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取健康度趋势数据（用于绘制图表）"""
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(Report.report_date, Report.health_score)
        .where(
            Report.pair_id == pair_id,
            Report.type == ReportType.DAILY,
            Report.report_date >= since,
            Report.health_score.isnot(None),
        )
        .order_by(Report.report_date)
    )

    trend_data = [{"date": str(row[0]), "score": row[1]} for row in result.all()]

    # 计算趋势方向
    if len(trend_data) >= 2:
        recent = [d["score"] for d in trend_data[-3:]]
        older = [d["score"] for d in trend_data[:3]]
        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)
        if avg_recent - avg_older > 5:
            direction = "improving"
        elif avg_older - avg_recent > 5:
            direction = "declining"
        else:
            direction = "stable"
    else:
        direction = "insufficient_data"

    return {"trend": trend_data, "direction": direction, "days": days}
