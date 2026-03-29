"""报告接口（Phase 2 增强：支持日报/周报/月报 + 趋势查询）"""

import uuid
import logging
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import desc, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, async_session
from app.api.deps import get_current_user
from app.models import User, Pair, Checkin, Report, ReportType, PairStatus, ReportStatus
from app.schemas import ReportResponse
from app.ai.reporter import (
    generate_daily_report,
    generate_weekly_report,
    generate_monthly_report,
    generate_solo_report,
)
from app.services.relationship_intelligence import (
    record_relationship_event,
    refresh_profile_and_plan,
)
from app.services.safety_summary import build_safety_status
from app.services.privacy_audit import privacy_audit_scope

router = APIRouter(prefix="/reports", tags=["报告"])
logger = logging.getLogger(__name__)


async def _get_authorized_pair(
    db: AsyncSession,
    pair_id: str,
    user: User,
    *,
    require_active: bool,
) -> Pair:
    result = await db.execute(select(Pair).where(Pair.id == pair_id))
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="配对不存在")
    if str(user.id) not in (str(pair.user_a_id), str(pair.user_b_id)):
        raise HTTPException(status_code=403, detail="无权访问该配对数据")
    if require_active and pair.status != PairStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="配对不存在或未激活")
    return pair


async def _process_daily_report(
    report_id: uuid.UUID, pair_id: str, pair_type: str, content_a: str, content_b: str
):
    from app.services.crisis_processor import process_crisis_from_report

    async with async_session() as db:
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            return

        try:
            if pair_type == "solo":
                with privacy_audit_scope(
                    db=db,
                    user_id=report.user_id,
                    scope="solo",
                    run_type="solo_daily_report",
                ):
                    report_content = await generate_solo_report(
                        pair_type="solo", content=content_a
                    )
                report.content = report_content
                report.health_score = report_content.get("health_score")
                report.status = ReportStatus.COMPLETED
                await record_relationship_event(
                    db,
                    event_type="report.completed",
                    user_id=report.user_id,
                    entity_type="report",
                    entity_id=report.id,
                    payload={
                        "report_type": report.type.value,
                        "health_score": report.health_score,
                        "crisis_level": (report.content or {}).get("crisis_level"),
                    },
                    idempotency_key=f"report:{report.id}:completed",
                )
                await refresh_profile_and_plan(db, user_id=report.user_id)
                await db.commit()
                return

            with privacy_audit_scope(
                db=db,
                pair_id=report.pair_id,
                scope="pair",
                run_type="daily_report",
            ):
                report_content = await generate_daily_report(
                    pair_type=pair_type,
                    content_a=content_a,
                    content_b=content_b,
                )
            report.content = report_content
            report.health_score = report_content.get("health_score")
            report.status = ReportStatus.COMPLETED

            pair = await db.get(Pair, pair_id)
            if pair:
                await process_crisis_from_report(db, report, pair)

            await record_relationship_event(
                db,
                event_type="report.completed",
                pair_id=report.pair_id,
                entity_type="report",
                entity_id=report.id,
                payload={
                    "report_type": report.type.value,
                    "health_score": report.health_score,
                    "crisis_level": (report.content or {}).get("crisis_level"),
                },
                idempotency_key=f"report:{report.id}:completed",
            )
            await refresh_profile_and_plan(db, pair_id=report.pair_id)

            await db.commit()
        except Exception as e:
            logger.error(f"Daily report generation failed for {report_id}: {str(e)}")
            report.status = ReportStatus.FAILED
            await db.commit()


async def _process_weekly_report(
    report_id: uuid.UUID, pair_id: str, pair_type: str, daily_reports: list
):
    from app.services.crisis_processor import process_crisis_from_report

    async with async_session() as db:
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            return

        try:
            with privacy_audit_scope(
                db=db,
                pair_id=report.pair_id,
                scope="pair",
                run_type="weekly_report",
            ):
                report_content = await generate_weekly_report(pair_type, daily_reports)
            report.content = report_content
            report.health_score = report_content.get("overall_health_score")
            report.status = ReportStatus.COMPLETED

            pair = await db.get(Pair, pair_id)
            if pair:
                await process_crisis_from_report(db, report, pair)

            await record_relationship_event(
                db,
                event_type="report.completed",
                pair_id=report.pair_id,
                entity_type="report",
                entity_id=report.id,
                payload={
                    "report_type": report.type.value,
                    "health_score": report.health_score,
                    "crisis_level": (report.content or {}).get("crisis_level"),
                },
                idempotency_key=f"report:{report.id}:completed",
            )
            await refresh_profile_and_plan(db, pair_id=report.pair_id)

            await db.commit()
        except Exception as e:
            logger.error(f"Weekly report generation failed for {report_id}: {str(e)}")
            report.status = ReportStatus.FAILED
            await db.commit()


async def _process_monthly_report(
    report_id: uuid.UUID, pair_id: str, pair_type: str, weekly_reports: list
):
    from app.services.crisis_processor import process_crisis_from_report

    async with async_session() as db:
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            return

        try:
            with privacy_audit_scope(
                db=db,
                pair_id=report.pair_id,
                scope="pair",
                run_type="monthly_report",
            ):
                report_content = await generate_monthly_report(pair_type, weekly_reports)
            report.content = report_content
            report.health_score = report_content.get("overall_health_score")
            report.status = ReportStatus.COMPLETED

            pair = await db.get(Pair, pair_id)
            if pair:
                await process_crisis_from_report(db, report, pair)

            await record_relationship_event(
                db,
                event_type="report.completed",
                pair_id=report.pair_id,
                entity_type="report",
                entity_id=report.id,
                payload={
                    "report_type": report.type.value,
                    "health_score": report.health_score,
                    "crisis_level": (report.content or {}).get("crisis_level"),
                },
                idempotency_key=f"report:{report.id}:completed",
            )
            await refresh_profile_and_plan(db, pair_id=report.pair_id)

            await db.commit()
        except Exception as e:
            logger.error(f"Monthly report generation failed for {report_id}: {str(e)}")
            report.status = ReportStatus.FAILED
            await db.commit()


@router.post("/generate-daily", response_model=ReportResponse)
async def trigger_daily_report(
    background_tasks: BackgroundTasks,
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """手动触发生成今日报告（异步，使用后台任务以防阻塞）"""
    today = date.today()
    is_solo = mode == "solo"

    if is_solo:
        result = await db.execute(
            select(Checkin).where(
                Checkin.user_id == user.id,
                Checkin.pair_id.is_(None),
                Checkin.checkin_date == today,
            )
        )
        checkin = result.scalar_one_or_none()
        if not checkin:
            raise HTTPException(status_code=400, detail="今天尚未打卡")

        result = await db.execute(
            select(Report)
            .where(
                Report.user_id == user.id,
                Report.report_date == today,
                Report.type == ReportType.SOLO,
            )
            .order_by(desc(Report.created_at))
            .limit(1)
        )
        existing = result.scalars().first()
        if existing:
            return existing

        report = Report(
            user_id=user.id,
            pair_id=None,
            type=ReportType.SOLO,
            status=ReportStatus.PENDING,
            content=None,
            health_score=None,
            report_date=today,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        if background_tasks:
            background_tasks.add_task(
                _process_daily_report, report.id, "solo", "solo", checkin.content, ""
            )
        return report

    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")

    pair = await _get_authorized_pair(db, pair_id, user, require_active=True)

    result = await db.execute(
        select(Checkin).where(Checkin.pair_id == pair_id, Checkin.checkin_date == today)
    )
    checkins = result.scalars().all()
    if len(checkins) < 2:
        raise HTTPException(status_code=400, detail="需要双方都完成打卡后才能生成报告")
    result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.report_date == today,
            Report.type == ReportType.DAILY,
        )
        .order_by(desc(Report.created_at))
        .limit(1)
    )
    existing = result.scalars().first()
    if existing:
        if existing.status == ReportStatus.FAILED:
            await db.delete(existing)
            await db.flush()
        else:
            return existing

    checkin_a = next((c for c in checkins if c.user_id == pair.user_a_id), checkins[0])
    checkin_b = next((c for c in checkins if c.user_id == pair.user_b_id), checkins[-1])

    report = Report(
        pair_id=pair_id,
        type=ReportType.DAILY,
        status=ReportStatus.PENDING,
        content=None,
        health_score=None,
        report_date=today,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    if background_tasks:
        background_tasks.add_task(
            _process_daily_report,
            report.id,
            pair_id,
            pair.type.value,
            checkin_a.content,
            checkin_b.content,
        )

    return report


@router.post("/generate-weekly", response_model=ReportResponse)
async def trigger_weekly_report(
    background_tasks: BackgroundTasks,
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成周报（基于过去7天的日报汇总，异步后台任务）"""
    today = date.today()
    if mode == "solo":
        raise HTTPException(status_code=400, detail="单人模式不支持周报")
    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")
    week_ago = today - timedelta(days=7)

    pair = await _get_authorized_pair(db, pair_id, user, require_active=True)

    result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.report_date >= week_ago,
            Report.type == ReportType.WEEKLY,
        )
        .order_by(desc(Report.created_at))
        .limit(1)
    )
    existing = result.scalars().first()
    if existing:
        if existing.status == ReportStatus.FAILED:
            await db.delete(existing)
            await db.flush()
        else:
            return existing

    result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.report_date >= week_ago,
            Report.type == ReportType.DAILY,
            Report.status == ReportStatus.COMPLETED,
        )
        .order_by(Report.report_date)
    )
    daily_reports = [r.content for r in result.scalars().all() if r.content]

    if len(daily_reports) < 3:
        raise HTTPException(
            status_code=400, detail="至少需要3天的完整日报数据才能生成周报"
        )

    report = Report(
        pair_id=pair_id,
        type=ReportType.WEEKLY,
        status=ReportStatus.PENDING,
        content=None,
        health_score=None,
        report_date=today,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    if background_tasks:
        background_tasks.add_task(
            _process_weekly_report, report.id, pair_id, pair.type.value, daily_reports
        )

    return report


@router.post("/generate-monthly", response_model=ReportResponse)
async def trigger_monthly_report(
    background_tasks: BackgroundTasks,
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成月报（基于过去30天的周报汇总，异步后台任务）"""
    today = date.today()
    if mode == "solo":
        raise HTTPException(status_code=400, detail="单人模式不支持月报")
    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")
    month_ago = today - timedelta(days=30)

    pair = await _get_authorized_pair(db, pair_id, user, require_active=True)

    result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.report_date >= month_ago,
            Report.type == ReportType.MONTHLY,
        )
        .order_by(desc(Report.created_at))
        .limit(1)
    )
    existing = result.scalars().first()
    if existing:
        if existing.status == ReportStatus.FAILED:
            await db.delete(existing)
            await db.flush()
        else:
            return existing

    result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.report_date >= month_ago,
            Report.type == ReportType.WEEKLY,
            Report.status == ReportStatus.COMPLETED,
        )
        .order_by(Report.report_date)
    )
    weekly_reports = [r.content for r in result.scalars().all() if r.content]

    if len(weekly_reports) < 2:
        raise HTTPException(status_code=400, detail="至少需要2周的完整数据才能生成月报")

    report = Report(
        pair_id=pair_id,
        type=ReportType.MONTHLY,
        status=ReportStatus.PENDING,
        content=None,
        health_score=None,
        report_date=today,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    if background_tasks:
        background_tasks.add_task(
            _process_monthly_report, report.id, pair_id, pair.type.value, weekly_reports
        )

    return report


@router.get("/latest", response_model=ReportResponse | None)
async def get_latest_report(
    pair_id: str | None = None,
    mode: str | None = None,
    report_type: str = "daily",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取最新报告（可按类型筛选）"""
    is_solo = mode == "solo"
    if is_solo:
        query = select(Report).where(
            Report.user_id == user.id, Report.type == ReportType.SOLO
        )
    else:
        if not pair_id:
            raise HTTPException(status_code=422, detail="缺少配对ID")
        await _get_authorized_pair(db, pair_id, user, require_active=False)
        query = select(Report).where(Report.pair_id == pair_id)
        if report_type in ("daily", "weekly", "monthly"):
            query = query.where(Report.type == ReportType(report_type))
    query = query.order_by(Report.report_date.desc()).limit(1)

    result = await db.execute(query)
    report = result.scalar_one_or_none()
    if not report:
        return None

    safety = await build_safety_status(
        db,
        pair_id=report.pair_id,
        user_id=report.user_id,
    )
    return ReportResponse(
        id=report.id,
        pair_id=report.pair_id,
        user_id=report.user_id,
        type=report.type.value if hasattr(report.type, "value") else str(report.type),
        status=report.status.value
        if hasattr(report.status, "value")
        else str(report.status),
        content=report.content,
        health_score=report.health_score,
        evidence_summary=safety.get("evidence_summary") or [],
        limitation_note=safety.get("limitation_note"),
        safety_handoff=safety.get("handoff_recommendation"),
        report_date=report.report_date,
        created_at=report.created_at,
    )


@router.get("/history", response_model=list[ReportResponse])
async def get_report_history(
    pair_id: str | None = None,
    mode: str | None = None,
    report_type: str = "daily",
    limit: int = 7,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取报告历史（仅返回生成的）"""
    is_solo = mode == "solo"
    if is_solo:
        query = select(Report).where(
            Report.user_id == user.id,
            Report.type == ReportType.SOLO,
            Report.status == ReportStatus.COMPLETED,
        )
    else:
        if not pair_id:
            raise HTTPException(status_code=422, detail="缺少配对ID")
        await _get_authorized_pair(db, pair_id, user, require_active=False)
        query = select(Report).where(
            Report.pair_id == pair_id, Report.status == ReportStatus.COMPLETED
        )
        if report_type in ("daily", "weekly", "monthly"):
            query = query.where(Report.type == ReportType(report_type))
    query = query.order_by(Report.report_date.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/trend", response_model=dict)
async def get_health_trend(
    pair_id: str | None = None,
    mode: str | None = None,
    days: int = 14,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取健康度趋势数据（用于绘制图表）"""
    since = date.today() - timedelta(days=days)
    if mode == "solo":
        result = await db.execute(
            select(Report.report_date, Report.health_score)
            .where(
                Report.user_id == user.id,
                Report.type == ReportType.SOLO,
                Report.status == ReportStatus.COMPLETED,
                Report.report_date >= since,
                Report.health_score.isnot(None),
            )
            .order_by(Report.report_date)
        )
    else:
        if not pair_id:
            raise HTTPException(status_code=422, detail="缺少配对ID")
        await _get_authorized_pair(db, pair_id, user, require_active=False)
        result = await db.execute(
            select(Report.report_date, Report.health_score)
            .where(
                Report.pair_id == pair_id,
                Report.type == ReportType.DAILY,
                Report.status == ReportStatus.COMPLETED,
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
        avg_recent = sum(recent) / len(recent) if recent else 0
        avg_older = sum(older) / len(older) if older else 0
        if avg_recent - avg_older > 5:
            direction = "improving"
        elif avg_older - avg_recent > 5:
            direction = "declining"
        else:
            direction = "stable"
    else:
        direction = "insufficient_data"

    return {"trend": trend_data, "direction": direction, "days": days}
