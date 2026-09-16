"""报告接口（Phase 2 增强：支持日报/周报/月报 + 趋势查询）"""

import uuid
import logging
import re
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, async_session
from app.core.time import current_local_date
from app.api.deps import get_current_user
from app.models import (
    User,
    Pair,
    Checkin,
    Report,
    ReportType,
    PairStatus,
    ReportStatus,
    RelationshipProfileSnapshot,
)
from app.schemas import ReportResponse, ReportScopeOptionResponse
from app.ai.reporter import (
    generate_daily_report,
    generate_weekly_report,
    generate_monthly_report,
    generate_solo_report,
)
from app.services.relationship_intelligence import (
    record_relationship_event,
    refresh_profile_and_plan,
    refresh_profile_snapshot,
)
from app.services.display_labels import pair_type_label
from app.services.safety_summary import build_safety_status
from app.services.privacy_audit import privacy_audit_scope
from app.services.product_prefs import resolve_privacy_mode
from app.services.test_accounts import is_relaxed_test_account

router = APIRouter(prefix="/reports", tags=["报告"])
logger = logging.getLogger(__name__)

SUPPORTED_SCOPE_REPORT_TYPES = {"daily", "weekly", "monthly"}
BOTH_SIDE_PATTERNS = (
    re.compile(r"A\s*方\s*(?:和|与|及|跟|、|/)\s*B\s*方"),
    re.compile(r"B\s*方\s*(?:和|与|及|跟|、|/)\s*A\s*方"),
)
RELAXED_REPORT_PLACEHOLDER = "测试账号暂无足够记录，用于验证报告生成流程。"


def _relaxed_daily_report_placeholder(index: int) -> dict:
    return {
        "health_score": 50,
        "insight": f"测试账号第{index}天占位日报，样本不足，仅用于验证周报流程。",
        "source": "relaxed_test_account",
    }


def _relaxed_weekly_report_placeholder(index: int) -> dict:
    return {
        "overall_health_score": 50,
        "trend": "stable",
        "trend_description": f"测试账号第{index}周占位周报，样本不足，仅用于验证月报流程。",
        "source": "relaxed_test_account",
    }


def _pad_relaxed_report_inputs(
    items: list[dict],
    required_count: int,
    factory,
) -> list[dict]:
    padded = list(items)
    while len(padded) < required_count:
        padded.append(factory(len(padded) + 1))
    return padded


def _as_uuid(value: uuid.UUID | str, *, detail: str = "配对不存在") -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=detail) from exc


async def _get_authorized_pair(
    db: AsyncSession,
    pair_id: uuid.UUID | str,
    user: User,
    *,
    require_active: bool,
) -> Pair:
    pair_uuid = _as_uuid(pair_id)
    result = await db.execute(select(Pair).where(Pair.id == pair_uuid))
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="配对不存在")
    if str(user.id) not in (str(pair.user_a_id), str(pair.user_b_id)):
        raise HTTPException(status_code=403, detail="无权访问该配对数据")
    if require_active and pair.status != PairStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="配对不存在或未激活")
    return pair


def _normalize_scope_report_type(report_type: str) -> ReportType:
    normalized = str(report_type or "daily").strip().lower()
    if normalized not in SUPPORTED_SCOPE_REPORT_TYPES:
        raise HTTPException(status_code=422, detail="不支持的简报类型")
    return ReportType(normalized)


async def _resolve_partner_for_pair(
    db: AsyncSession,
    *,
    pair: Pair,
    user: User,
) -> User | None:
    partner_id = pair.user_b_id if str(pair.user_a_id) == str(user.id) else pair.user_a_id
    if not partner_id:
        return None
    return await db.get(User, partner_id)


def _partner_label(pair: Pair, user: User, partner: User | None) -> str:
    is_user_a = str(pair.user_a_id) == str(user.id)
    custom_nickname = (
        pair.custom_partner_nickname_a
        if is_user_a
        else pair.custom_partner_nickname_b
    )
    return str(
        custom_nickname
        or getattr(partner, "nickname", None)
        or getattr(partner, "email", None)
        or getattr(partner, "phone", None)
        or "对方"
    ).strip() or "对方"


def _normalize_report_text(text: str, *, self_label: str, partner_label: str) -> str:
    normalized = str(text or "")
    if not normalized:
        return normalized

    for pattern in BOTH_SIDE_PATTERNS:
        normalized = pattern.sub("双方", normalized)

    normalized = re.sub(r"A\s*方", self_label, normalized)
    normalized = re.sub(r"B\s*方", partner_label, normalized)
    return normalized


def _normalize_report_value(value, *, self_label: str, partner_label: str):
    if isinstance(value, str):
        return _normalize_report_text(
            value,
            self_label=self_label,
            partner_label=partner_label,
        )
    if isinstance(value, list):
        return [
            _normalize_report_value(
                item,
                self_label=self_label,
                partner_label=partner_label,
            )
            for item in value
        ]
    if isinstance(value, dict):
        return {
            key: _normalize_report_value(
                item,
                self_label=self_label,
                partner_label=partner_label,
            )
            for key, item in value.items()
        }
    return value


def _report_enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _report_health_score(report: Report | None, snapshot: RelationshipProfileSnapshot | None) -> int:
    if report and report.health_score is not None:
        return int(round(float(report.health_score)))

    snapshot_health = None
    if snapshot:
        snapshot_health = (snapshot.metrics_json or {}).get("report_health_avg")
    if snapshot_health is not None:
        try:
            return int(round(float(snapshot_health)))
        except (TypeError, ValueError):
            pass

    return 50


def _clamp_ratio(value, *, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, numeric))


def _metric_number(metrics: dict | None, key: str, *, default: float = 0.0) -> float:
    if not metrics:
        return default
    try:
        return float(metrics.get(key) or default)
    except (TypeError, ValueError):
        return default


def _latest_signal_at(
    *,
    pair: Pair,
    latest_report: Report | None,
    snapshot: RelationshipProfileSnapshot | None,
) -> datetime | None:
    candidates = [pair.created_at]
    if latest_report and latest_report.created_at:
        candidates.append(latest_report.created_at)
    if snapshot:
        if snapshot.generated_from_event_at:
            candidates.append(snapshot.generated_from_event_at)
        if snapshot.created_at:
            candidates.append(snapshot.created_at)
    filtered = [value for value in candidates if value]
    return max(filtered) if filtered else None


def _report_scope_reason_tags(
    *,
    activity_score: int,
    dual_activity_score: int,
    health_score: int,
    latest_report: Report | None,
) -> list[str]:
    tags: list[str] = []

    if dual_activity_score >= 60:
        tags.append("双方最近都活跃")
    if health_score >= 70:
        tags.append("近期分数较高")
    if latest_report:
        tags.append("最近有记录")

    if not tags and activity_score >= 40:
        tags.append("最近互动在恢复")
    if not tags:
        tags.append("最近值得先看")

    return tags[:3]


async def _get_latest_scope_snapshot(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
) -> RelationshipProfileSnapshot | None:
    result = await db.execute(
        select(RelationshipProfileSnapshot)
        .where(
            RelationshipProfileSnapshot.pair_id == pair_id,
            RelationshipProfileSnapshot.user_id.is_(None),
            RelationshipProfileSnapshot.window_days == 7,
        )
        .order_by(
            RelationshipProfileSnapshot.snapshot_date.desc(),
            RelationshipProfileSnapshot.created_at.desc(),
        )
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if snapshot:
        return snapshot

    try:
        return await refresh_profile_snapshot(db, pair_id=pair_id, window_days=7)
    except Exception:
        logger.exception("Failed to refresh profile snapshot for report scope %s", pair_id)
        return None


async def _get_latest_completed_report_by_type(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    report_type: ReportType,
) -> Report | None:
    result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.type == report_type,
            Report.status == ReportStatus.COMPLETED,
        )
        .order_by(Report.report_date.desc(), Report.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _serialize_report_response(
    report: Report,
    *,
    partner_label: str = "对方",
    include_copy_normalization: bool = False,
    evidence_summary: list[str] | None = None,
    limitation_note: str | None = None,
    safety_handoff: str | None = None,
) -> ReportResponse:
    content = report.content
    normalized_evidence_summary = evidence_summary or []
    normalized_limitation_note = limitation_note
    normalized_safety_handoff = safety_handoff

    if include_copy_normalization:
        content = _normalize_report_value(
            content,
            self_label="你",
            partner_label=partner_label,
        )
        normalized_evidence_summary = _normalize_report_value(
            normalized_evidence_summary,
            self_label="你",
            partner_label=partner_label,
        )
        normalized_limitation_note = _normalize_report_value(
            normalized_limitation_note,
            self_label="你",
            partner_label=partner_label,
        )
        normalized_safety_handoff = _normalize_report_value(
            normalized_safety_handoff,
            self_label="你",
            partner_label=partner_label,
        )

    return ReportResponse(
        id=report.id,
        pair_id=report.pair_id,
        user_id=report.user_id,
        type=_report_enum_value(report.type),
        status=_report_enum_value(report.status),
        content=content,
        health_score=report.health_score,
        evidence_summary=normalized_evidence_summary or [],
        limitation_note=normalized_limitation_note,
        safety_handoff=normalized_safety_handoff,
        report_date=report.report_date,
        created_at=report.created_at,
    )


async def _process_daily_report(
    report_id: uuid.UUID,
    pair_id: uuid.UUID | str,
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

            pair = await db.get(Pair, _as_uuid(pair_id))
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
    pair_id: uuid.UUID | str,
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

            pair = await db.get(Pair, _as_uuid(pair_id))
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
    pair_id: uuid.UUID | str,
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

            pair = await db.get(Pair, _as_uuid(pair_id))
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
    pair_id: uuid.UUID | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """手动触发生成今日报告（异步，使用后台任务以防阻塞）"""
    today = current_local_date()
    is_solo = mode == "solo"
    privacy_mode = resolve_privacy_mode(getattr(user, "product_prefs", None))
    relaxed_test_account = is_relaxed_test_account(user)

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
            if not relaxed_test_account:
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
            if existing.status == ReportStatus.FAILED:
                await db.delete(existing)
                await db.flush()
            else:
                return existing

        content = checkin.content if checkin else RELAXED_REPORT_PLACEHOLDER

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
                content,
                "",
                str(user.id),
                privacy_mode,
            )
        return report

    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")

    pair = await _get_authorized_pair(db, pair_id, user, require_active=True)
    pair_id = pair.id

    result = await db.execute(
        select(Checkin).where(Checkin.pair_id == pair_id, Checkin.checkin_date == today)
    )
    checkins = result.scalars().all()
    if len(checkins) < 2 and not relaxed_test_account:
        raise HTTPException(status_code=400, detail="需要双方都完成打卡后才能生成报告")
    result = await db.execute(
        select(Report).where(
            Report.pair_id == pair_id,
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

    checkin_a = next((c for c in checkins if c.user_id == pair.user_a_id), None)
    checkin_b = next((c for c in checkins if c.user_id == pair.user_b_id), None)
    if not checkin_a or not checkin_b:
        if not relaxed_test_account:
            raise HTTPException(status_code=400, detail="需要双方都完成打卡后才能生成报告")
    content_a = checkin_a.content if checkin_a else RELAXED_REPORT_PLACEHOLDER
    content_b = checkin_b.content if checkin_b else RELAXED_REPORT_PLACEHOLDER

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
            content_a,
            content_b,
            str(user.id),
            privacy_mode,
        )

    return report


@router.post("/generate-weekly", response_model=ReportResponse)
async def trigger_weekly_report(
    background_tasks: BackgroundTasks,
    pair_id: uuid.UUID | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成周报（基于过去7天的日报汇总，异步后台任务）"""
    today = current_local_date()
    privacy_mode = resolve_privacy_mode(getattr(user, "product_prefs", None))
    relaxed_test_account = is_relaxed_test_account(user)
    if mode == "solo":
        raise HTTPException(status_code=400, detail="单人模式不支持周报")
    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")
    week_ago = today - timedelta(days=7)

    pair = await _get_authorized_pair(db, pair_id, user, require_active=True)
    pair_id = pair.id

    result = await db.execute(
        select(Report).where(
            Report.pair_id == pair_id,
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
            Report.pair_id == pair_id,
            Report.report_date >= week_ago,
            Report.type == ReportType.DAILY,
            Report.status == ReportStatus.COMPLETED,
        )
        .order_by(Report.report_date)
    )
    daily_reports = [r.content for r in result.scalars().all() if r.content]

    if len(daily_reports) < 3:
        if not relaxed_test_account:
            raise HTTPException(
                status_code=400, detail="至少需要3天的完整日报数据才能生成周报"
            )
        daily_reports = _pad_relaxed_report_inputs(
            daily_reports,
            3,
            _relaxed_daily_report_placeholder,
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
            _process_weekly_report,
            report.id,
            pair_id,
            pair.type.value,
            daily_reports,
            str(user.id),
            privacy_mode,
        )

    return report


@router.post("/generate-monthly", response_model=ReportResponse)
async def trigger_monthly_report(
    background_tasks: BackgroundTasks,
    pair_id: uuid.UUID | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成月报（基于过去30天的周报汇总，异步后台任务）"""
    today = current_local_date()
    privacy_mode = resolve_privacy_mode(getattr(user, "product_prefs", None))
    relaxed_test_account = is_relaxed_test_account(user)
    if mode == "solo":
        raise HTTPException(status_code=400, detail="单人模式不支持月报")
    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")
    month_ago = today - timedelta(days=30)

    pair = await _get_authorized_pair(db, pair_id, user, require_active=True)
    pair_id = pair.id

    result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
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
            Report.pair_id == pair_id,
            Report.report_date >= month_ago,
            Report.type == ReportType.WEEKLY,
            Report.status == ReportStatus.COMPLETED,
        )
        .order_by(Report.report_date)
    )
    weekly_reports = [r.content for r in result.scalars().all() if r.content]

    if len(weekly_reports) < 2:
        if not relaxed_test_account:
            raise HTTPException(status_code=400, detail="至少需要2周的完整数据才能生成月报")
        weekly_reports = _pad_relaxed_report_inputs(
            weekly_reports,
            2,
            _relaxed_weekly_report_placeholder,
        )

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
            _process_monthly_report,
            report.id,
            pair_id,
            pair.type.value,
            weekly_reports,
            str(user.id),
            privacy_mode,
        )

    return report


@router.get("/scopes", response_model=list[ReportScopeOptionResponse])
async def get_report_scopes(
    report_type: str = "daily",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    requested_report_type = _normalize_scope_report_type(report_type)
    result = await db.execute(
        select(Pair)
        .where(
            or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
            Pair.status == PairStatus.ACTIVE,
        )
        .order_by(Pair.created_at.desc())
    )
    pairs = result.scalars().all()

    scope_options: list[ReportScopeOptionResponse] = []
    for pair in pairs:
        partner = await _resolve_partner_for_pair(db, pair=pair, user=user)
        partner_label = _partner_label(pair, user, partner)
        snapshot = await _get_latest_scope_snapshot(db, pair_id=pair.id)
        latest_report = await _get_latest_completed_report_by_type(
            db,
            pair_id=pair.id,
            report_type=requested_report_type,
        )

        metrics = (snapshot.metrics_json or {}) if snapshot else {}
        activity_score = int(
            round(
                _clamp_ratio(_metric_number(metrics, "checkin_count") / 14.0) * 100
            )
        )
        dual_activity_score = int(
            round(_clamp_ratio(metrics.get("interaction_overlap_rate")) * 100)
        )
        health_score = _report_health_score(latest_report, snapshot)
        sort_score = int(
            round(
                activity_score * 0.35
                + dual_activity_score * 0.40
                + health_score * 0.25
            )
        )
        latest_signal_at = _latest_signal_at(
            pair=pair,
            latest_report=latest_report,
            snapshot=snapshot,
        )

        scope_options.append(
            ReportScopeOptionResponse(
                pair_id=pair.id,
                partner_label=partner_label,
                pair_type=_report_enum_value(pair.type) if pair.type else None,
                pair_type_label=pair_type_label(
                    _report_enum_value(pair.type) if pair.type else None
                ),
                sort_score=sort_score,
                activity_score=activity_score,
                dual_activity_score=dual_activity_score,
                health_score=health_score,
                latest_report_date=latest_report.report_date if latest_report else None,
                latest_signal_at=latest_signal_at,
                reason_tags=_report_scope_reason_tags(
                    activity_score=activity_score,
                    dual_activity_score=dual_activity_score,
                    health_score=health_score,
                    latest_report=latest_report,
                ),
            )
        )

    scope_options.sort(
        key=lambda item: (
            -item.sort_score,
            -(item.latest_signal_at.timestamp() if item.latest_signal_at else 0),
            item.partner_label,
        )
    )
    return scope_options


@router.get("/latest", response_model=ReportResponse | None)
async def get_latest_report(
    pair_id: uuid.UUID | None = None,
    mode: str | None = None,
    report_type: str = "daily",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取最新报告（可按类型筛选）"""
    is_solo = mode == "solo"
    pair = None
    partner_label = "对方"
    if is_solo:
        query = select(Report).where(
            Report.user_id == user.id, Report.type == ReportType.SOLO
        )
    else:
        if not pair_id:
            raise HTTPException(status_code=422, detail="缺少配对ID")
        pair = await _get_authorized_pair(db, pair_id, user, require_active=False)
        pair_id = pair.id
        partner = await _resolve_partner_for_pair(db, pair=pair, user=user)
        partner_label = _partner_label(pair, user, partner)
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
    return _serialize_report_response(
        report,
        partner_label=partner_label,
        include_copy_normalization=bool(pair),
        evidence_summary=safety.get("evidence_summary") or [],
        limitation_note=safety.get("limitation_note"),
        safety_handoff=safety.get("handoff_recommendation"),
    )


@router.get("/history", response_model=list[ReportResponse])
async def get_report_history(
    pair_id: uuid.UUID | None = None,
    mode: str | None = None,
    report_type: str = "daily",
    limit: int = 7,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取报告历史（仅返回生成的）"""
    is_solo = mode == "solo"
    pair = None
    partner_label = "对方"
    if is_solo:
        query = select(Report).where(
            Report.user_id == user.id,
            Report.type == ReportType.SOLO,
            Report.status == ReportStatus.COMPLETED,
        )
    else:
        if not pair_id:
            raise HTTPException(status_code=422, detail="缺少配对ID")
        pair = await _get_authorized_pair(db, pair_id, user, require_active=False)
        pair_id = pair.id
        partner = await _resolve_partner_for_pair(db, pair=pair, user=user)
        partner_label = _partner_label(pair, user, partner)
        query = select(Report).where(
            Report.pair_id == pair_id, Report.status == ReportStatus.COMPLETED
        )
        if report_type in ("daily", "weekly", "monthly"):
            query = query.where(Report.type == ReportType(report_type))
    query = query.order_by(Report.report_date.desc()).limit(limit)

    result = await db.execute(query)
    return [
        _serialize_report_response(
            report,
            partner_label=partner_label,
            include_copy_normalization=bool(pair),
        )
        for report in result.scalars().all()
    ]


@router.get("/trend", response_model=dict)
async def get_health_trend(
    pair_id: uuid.UUID | None = None,
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
        pair_id = pair.id
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
