"""报告接口（Phase 2 增强：支持日报/周报/月报 + 趋势查询）"""

import uuid
import logging
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, async_session
from app.core.time import current_local_date
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
from app.services.product_prefs import resolve_privacy_mode
from app.api.v1.checkins import _combine_checkin_contents

router = APIRouter(prefix="/reports", tags=["报告"])
logger = logging.getLogger(__name__)


async def _get_authorized_pair(
    db: AsyncSession,
    pair_id: str,
    user: User,
    *,
    require_active: bool,
) -> Pair:
    normalized_pair_id = uuid.UUID(str(pair_id))
    result = await db.execute(select(Pair).where(Pair.id == normalized_pair_id))
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="配对不存在")
    if str(user.id) not in (str(pair.user_a_id), str(pair.user_b_id)):
        raise HTTPException(status_code=403, detail="无权访问该配对数据")
    if require_active and pair.status != PairStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="配对不存在或未激活")
    return pair


async def _process_daily_report(
    report_id: uuid.UUID,
    pair_id: str,
    pair_type: str,
    content_a: str,
    content_b: str,
    actor_user_id: str | None = None,
    privacy_mode: str = "cloud",
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
                    privacy_mode=privacy_mode,
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
                user_id=actor_user_id,
                pair_id=report.pair_id,
                scope="pair",
                run_type="daily_report",
                privacy_mode=privacy_mode,
            ):
                report_content = await generate_daily_report(
                    pair_type=pair_type,
                    content_a=content_a,
                    content_b=content_b,
                )
            report.content = report_content
            report.health_score = report_content.get("health_score")
            report.status = ReportStatus.COMPLETED

            pair = await db.get(Pair, uuid.UUID(str(pair_id)))
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
    report_id: uuid.UUID,
    pair_id: str,
    pair_type: str,
    daily_reports: list,
    actor_user_id: str | None = None,
    privacy_mode: str = "cloud",
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
                user_id=actor_user_id,
                pair_id=report.pair_id,
                scope="pair",
                run_type="weekly_report",
                privacy_mode=privacy_mode,
            ):
                report_content = await generate_weekly_report(pair_type, daily_reports)
            report.content = report_content
            report.health_score = report_content.get("overall_health_score")
            report.status = ReportStatus.COMPLETED

            pair = await db.get(Pair, uuid.UUID(str(pair_id)))
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
    report_id: uuid.UUID,
    pair_id: str,
    pair_type: str,
    weekly_reports: list,
    actor_user_id: str | None = None,
    privacy_mode: str = "cloud",
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
                user_id=actor_user_id,
                pair_id=report.pair_id,
                scope="pair",
                run_type="monthly_report",
                privacy_mode=privacy_mode,
            ):
                report_content = await generate_monthly_report(pair_type, weekly_reports)
            report.content = report_content
            report.health_score = report_content.get("overall_health_score")
            report.status = ReportStatus.COMPLETED

            pair = await db.get(Pair, uuid.UUID(str(pair_id)))
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
    today = current_local_date()
    is_solo = mode == "solo"
    privacy_mode = resolve_privacy_mode(getattr(user, "product_prefs", None))

    if is_solo:
        result = await db.execute(
            select(Checkin)
            .where(
                Checkin.user_id == user.id,
                Checkin.pair_id.is_(None),
                Checkin.checkin_date == today,
            )
            .order_by(Checkin.created_at.asc(), Checkin.id.asc())
        )
        checkins = list(result.scalars().all())
        if not checkins:
            raise HTTPException(status_code=400, detail="今天尚未打卡")

        result = await db.execute(
            select(Report).where(
                Report.user_id == user.id,
                Report.report_date == today,
                Report.type == ReportType.SOLO,
            )
        )
        existing = result.scalar_one_or_none()
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
                _process_daily_report,
                report.id,
                "solo",
                "solo",
                _combine_checkin_contents(checkins),
                "",
                str(user.id),
                privacy_mode,
            )
        return report

    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")

    pair = await _get_authorized_pair(db, pair_id, user, require_active=True)

    result = await db.execute(
        select(Checkin)
        .where(Checkin.pair_id == pair.id, Checkin.checkin_date == today)
        .order_by(Checkin.created_at.asc(), Checkin.id.asc())
    )
    checkins = list(result.scalars().all())
    checkin_a_entries = [item for item in checkins if item.user_id == pair.user_a_id]
    checkin_b_entries = [item for item in checkins if item.user_id == pair.user_b_id]
    if not checkin_a_entries or not checkin_b_entries:
        raise HTTPException(status_code=400, detail="需要双方都完成打卡后才能生成报告")
    result = await db.execute(
        select(Report).where(
            Report.pair_id == pair.id,
            Report.report_date == today,
            Report.type == ReportType.DAILY,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        if existing.status == ReportStatus.FAILED:
            await db.delete(existing)
            await db.flush()
        else:
            return existing

    report = Report(
        pair_id=pair.id,
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
            str(pair.id),
            pair.type.value,
            _combine_checkin_contents(checkin_a_entries),
            _combine_checkin_contents(checkin_b_entries),
            str(user.id),
            privacy_mode,
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
    today = current_local_date()
    privacy_mode = resolve_privacy_mode(getattr(user, "product_prefs", None))
    if mode == "solo":
        raise HTTPException(status_code=400, detail="单人模式不支持周报")
    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")
    week_ago = today - timedelta(days=7)

    pair = await _get_authorized_pair(db, pair_id, user, require_active=True)

    result = await db.execute(
        select(Report).where(
            Report.pair_id == pair.id,
            Report.report_date >= week_ago,
            Report.type == ReportType.WEEKLY,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        if existing.status == ReportStatus.FAILED:
            await db.delete(existing)
            await db.flush()
        else:
            return existing

    result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair.id,
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
        pair_id=pair.id,
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
            _process_weekly_report,
            report.id,
            str(pair.id),
            pair.type.value,
            daily_reports,
            str(user.id),
            privacy_mode,
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
    today = current_local_date()
    privacy_mode = resolve_privacy_mode(getattr(user, "product_prefs", None))
    if mode == "solo":
        raise HTTPException(status_code=400, detail="单人模式不支持月报")
    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")
    month_ago = today - timedelta(days=30)

    pair = await _get_authorized_pair(db, pair_id, user, require_active=True)

    result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair.id,
            Report.report_date >= month_ago,
            Report.type == ReportType.MONTHLY,
        )
        .order_by(Report.report_date)
    )
    existing = result.scalar_one_or_none()
    if existing:
        if existing.status == ReportStatus.FAILED:
            await db.delete(existing)
            await db.flush()
        else:
            return existing

    result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair.id,
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
        pair_id=pair.id,
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
            _process_monthly_report,
            report.id,
            str(pair.id),
            pair.type.value,
            weekly_reports,
            str(user.id),
            privacy_mode,
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
        pair = await _get_authorized_pair(db, pair_id, user, require_active=False)
        query = select(Report).where(Report.pair_id == pair.id)
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
    start_date: date | None = None,
    end_date: date | None = None,
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
        if start_date:
            query = query.where(Report.report_date >= start_date)
        if end_date:
            query = query.where(Report.report_date <= end_date)
    else:
        if not pair_id:
            raise HTTPException(status_code=422, detail="缺少配对ID")
        pair = await _get_authorized_pair(db, pair_id, user, require_active=False)
        query = select(Report).where(
            Report.pair_id == pair.id, Report.status == ReportStatus.COMPLETED
        )
        if report_type in ("daily", "weekly", "monthly"):
            query = query.where(Report.type == ReportType(report_type))
        if start_date:
            query = query.where(Report.report_date >= start_date)
        if end_date:
            query = query.where(Report.report_date <= end_date)
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
    since = current_local_date() - timedelta(days=days)
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
        pair = await _get_authorized_pair(db, pair_id, user, require_active=False)
        result = await db.execute(
            select(Report.report_date, Report.health_score)
            .where(
                Report.pair_id == pair.id,
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
