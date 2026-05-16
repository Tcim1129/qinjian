"""打卡系统接口（Phase 3 增强：支持非对称打卡 + 个人情感日记）"""

import logging
import uuid
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.time import current_local_date
from app.api.deps import get_current_user, validate_pair_access
from app.models import User, Pair, Checkin, Report, PairStatus, ReportType, ReportStatus
from app.schemas import CheckinRequest, CheckinResponse
from app.ai import analyze_sentiment
from app.ai.reporter import generate_daily_report, generate_solo_report
from app.services.relationship_intelligence import (
    record_relationship_event,
    refresh_profile_and_plan,
)

router = APIRouter(prefix="/checkins", tags=["打卡"])
logger = logging.getLogger(__name__)

MAX_DAILY_CHECKINS = 3
DAILY_CHECKIN_LIMIT_DETAIL = "今天最多 1 条正式记录和 2 条补充记录"
MAX_DAILY_SUPPLEMENTS = MAX_DAILY_CHECKINS - 1


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _ordered_checkins(checkins: list[Checkin]) -> list[Checkin]:
    return sorted(
        checkins,
        key=lambda item: (
            item.created_at or datetime.min,
            str(item.id or ""),
        ),
    )


def _combine_checkin_contents(checkins: list[Checkin]) -> str:
    ordered = _ordered_checkins(checkins)
    return "\n\n".join(
        f"第 {index} 条记录：{item.content}" for index, item in enumerate(ordered, 1)
    )


def _checkin_entry_index(checkin: Checkin, same_day_checkins: list[Checkin]) -> int:
    ordered = _ordered_checkins(same_day_checkins)
    for index, item in enumerate(ordered, 1):
        if item.id == checkin.id:
            return index
    return len(ordered) + 1


def _checkin_summary(checkin: Checkin | None, entry_index: int | None = None) -> dict:
    return {
        "id": str(checkin.id) if checkin else None,
        "entry_index": entry_index,
        "mood_score": checkin.mood_score if checkin else None,
        "interaction_freq": checkin.interaction_freq if checkin else None,
        "deep_conversation": checkin.deep_conversation if checkin else None,
        "task_completed": checkin.task_completed if checkin else None,
        "content": checkin.content if checkin else None,
        "checkin_date": str(checkin.checkin_date) if checkin else None,
        "created_at": checkin.created_at.isoformat()
        if checkin and checkin.created_at
        else None,
    }


def _checkin_summaries(checkins: list[Checkin]) -> list[dict]:
    return [
        _checkin_summary(checkin, entry_index=index)
        for index, checkin in enumerate(_ordered_checkins(checkins), 1)
    ]


def _remaining_supplements(entry_count: int) -> int:
    return max(0, MAX_DAILY_SUPPLEMENTS - max(0, entry_count - 1))


def _serialize_checkin_history(checkins: list[Checkin]) -> list[CheckinResponse]:
    grouped: dict[date, list[Checkin]] = {}
    for checkin in checkins:
        grouped.setdefault(checkin.checkin_date, []).append(checkin)

    entry_indexes = {}
    for day_checkins in grouped.values():
        for index, checkin in enumerate(_ordered_checkins(day_checkins), 1):
            entry_indexes[checkin.id] = index

    return [
        _serialize_checkin_response(
            checkin,
            checkin.client_context,
            entry_index=entry_indexes.get(checkin.id),
        )
        for checkin in checkins
    ]


async def _get_user_checkins_for_date(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    checkin_date: date,
    pair_id: uuid.UUID | None,
) -> list[Checkin]:
    query = (
        select(Checkin)
        .where(Checkin.user_id == user_id, Checkin.checkin_date == checkin_date)
        .order_by(Checkin.created_at.asc(), Checkin.id.asc())
    )
    if pair_id is None:
        query = query.where(Checkin.pair_id.is_(None))
    else:
        query = query.where(Checkin.pair_id == pair_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def _get_pair_checkins_for_date(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    checkin_date: date,
) -> list[Checkin]:
    result = await db.execute(
        select(Checkin)
        .where(Checkin.pair_id == pair_id, Checkin.checkin_date == checkin_date)
        .order_by(Checkin.created_at.asc(), Checkin.id.asc())
    )
    return list(result.scalars().all())


async def _prepare_report_for_refresh(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    report_type: ReportType,
    report_date: date,
) -> Report:
    query = select(Report).where(
        Report.report_date == report_date,
        Report.type == report_type,
    )
    if pair_id is None:
        query = query.where(Report.pair_id.is_(None), Report.user_id == user_id)
    else:
        query = query.where(Report.pair_id == pair_id)

    result = await db.execute(query)
    report = result.scalar_one_or_none()
    if report is None:
        report = Report(
            pair_id=pair_id,
            user_id=user_id,
            type=report_type,
            status=ReportStatus.PENDING,
            content=None,
            health_score=None,
            report_date=report_date,
        )
        db.add(report)
    else:
        report.status = ReportStatus.PENDING
        report.content = None
        report.health_score = None
    await db.flush()
    return report


async def _schedule_today_report_refresh(
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    *,
    is_solo: bool,
    pair: Pair | None,
    user: User,
    checkin_date: date,
) -> tuple[Checkin | None, bool]:
    if is_solo:
        my_checkins = await _get_user_checkins_for_date(
            db,
            user_id=user.id,
            checkin_date=checkin_date,
            pair_id=None,
        )
        report = await _prepare_report_for_refresh(
            db,
            pair_id=None,
            user_id=user.id,
            report_type=ReportType.SOLO,
            report_date=checkin_date,
        )
        background_tasks.add_task(
            _auto_generate_solo,
            None,
            "solo",
            _combine_checkin_contents(my_checkins),
            str(user.id),
            report.id,
        )
        return None, False

    if not pair:
        return None, False

    pair_checkins = await _get_pair_checkins_for_date(
        db,
        pair_id=pair.id,
        checkin_date=checkin_date,
    )
    partner_checkins = [item for item in pair_checkins if item.user_id != user.id]
    partner_checkin = _ordered_checkins(partner_checkins)[0] if partner_checkins else None

    user_a_checkins = [item for item in pair_checkins if item.user_id == pair.user_a_id]
    user_b_checkins = [item for item in pair_checkins if item.user_id == pair.user_b_id]
    both_done = bool(user_a_checkins and user_b_checkins)

    if both_done:
        report = await _prepare_report_for_refresh(
            db,
            pair_id=pair.id,
            user_id=None,
            report_type=ReportType.DAILY,
            report_date=checkin_date,
        )
        background_tasks.add_task(
            _auto_generate_daily,
            pair.id,
            pair.type.value,
            _combine_checkin_contents(user_a_checkins),
            _combine_checkin_contents(user_b_checkins),
            report.id,
        )
    else:
        my_checkins = [item for item in pair_checkins if item.user_id == user.id]
        report = await _prepare_report_for_refresh(
            db,
            pair_id=pair.id,
            user_id=user.id,
            report_type=ReportType.SOLO,
            report_date=checkin_date,
        )
        background_tasks.add_task(
            _auto_generate_solo,
            pair.id,
            pair.type.value if pair else "solo",
            _combine_checkin_contents(my_checkins),
            str(user.id),
            report.id,
        )

    return partner_checkin, both_done


def _context_value(req: CheckinRequest) -> dict | None:
    return req.client_context.model_dump() if req.client_context else None


def _build_local_guidance_from_context(context: dict | None) -> str | None:
    if not isinstance(context, dict):
        return None

    risk_level = str(context.get("risk_level") or "none")
    intent = str(context.get("intent") or "daily")
    pii_summary = context.get("pii_summary") or {}
    pii_hits = int(pii_summary.get("total_hits") or 0)
    upload_policy = str(context.get("upload_policy") or "full")

    if risk_level == "high":
        return "本地预检识别到高风险信号，建议先使用求助资源、手动记录或冷静步骤，而不是直接进入普通 AI 建议。"
    if intent == "emergency":
        return "本地预检判断你更像是在处理眼前的冲突，建议先看一句更稳妥的表达，再决定是否发送。"
    if pii_hits > 0 and upload_policy == "redacted_only":
        return "本次内容包含敏感信息，系统已优先采用脱敏文本进入后续分析。"
    if upload_policy == "local_only":
        return "这条记录当前只保存在本地，等你确认后再同步到云端。"
    if intent == "reflection":
        return "这次输入更适合进入复盘视角，建议结合时间轴和周评估一起看变化。"
    return "本地预检已完成，系统会结合后端深分析继续整理更完整的判断。"


def _serialize_checkin_response(
    checkin: Checkin,
    context: dict | None,
    *,
    entry_index: int | None = None,
) -> CheckinResponse:
    analysis_source = "client_precheck" if context else "server_ai"
    safety_gate = str((context or {}).get("risk_level") or "none") == "high"
    return CheckinResponse(
        id=checkin.id,
        pair_id=checkin.pair_id,
        user_id=checkin.user_id,
        content=checkin.content,
        image_url=checkin.image_url,
        voice_url=checkin.voice_url,
        mood_tags=checkin.mood_tags,
        sentiment_score=checkin.sentiment_score,
        mood_score=checkin.mood_score,
        interaction_freq=checkin.interaction_freq,
        interaction_initiative=checkin.interaction_initiative,
        deep_conversation=checkin.deep_conversation,
        task_completed=checkin.task_completed,
        client_context=context,
        analysis_source=analysis_source,
        client_precheck=context,
        server_analysis={
            "status": "pending",
            "note": "服务端深分析会在后台继续完成。",
        },
        final_guidance=_build_local_guidance_from_context(context),
        safety_gate=safety_gate,
        entry_index=entry_index,
        daily_entry_limit=MAX_DAILY_CHECKINS,
        checkin_date=checkin.checkin_date,
        created_at=checkin.created_at,
    )


@router.post("/", response_model=CheckinResponse)
async def create_checkin(
    req: CheckinRequest,
    background_tasks: BackgroundTasks,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交每日打卡（含自动AI情感分析 + 双方完成检测 + 单方solo日记）"""
    is_solo = mode == "solo"
    pair = None
    if not is_solo:
        if not req.pair_id:
            raise HTTPException(status_code=422, detail="缺少配对ID")
        result = await db.execute(
            select(Pair).where(Pair.id == req.pair_id, Pair.status == PairStatus.ACTIVE)
        )
        pair = result.scalar_one_or_none()
        if not pair or (pair.user_a_id != user.id and pair.user_b_id != user.id):
            raise HTTPException(status_code=403, detail="你不属于该配对")

    today = current_local_date()
    scope_pair_id = None if is_solo else req.pair_id
    existing_my_checkins = await _get_user_checkins_for_date(
        db,
        user_id=user.id,
        checkin_date=today,
        pair_id=scope_pair_id,
    )
    if len(existing_my_checkins) >= MAX_DAILY_CHECKINS:
        raise HTTPException(status_code=400, detail=DAILY_CHECKIN_LIMIT_DETAIL)

    # 创建打卡记录
    checkin = Checkin(
        pair_id=req.pair_id if not is_solo else None,
        user_id=user.id,
        content=req.content,
        image_url=req.image_url,
        voice_url=req.voice_url,
        mood_tags={"tags": req.mood_tags} if req.mood_tags else None,
        client_context=_context_value(req),
        mood_score=req.mood_score,
        interaction_freq=req.interaction_freq,
        interaction_initiative=req.interaction_initiative,
        deep_conversation=req.deep_conversation,
        task_completed=req.task_completed,
        checkin_date=today,
    )
    db.add(checkin)
    await db.flush()
    my_checkins_after_create = [*existing_my_checkins, checkin]
    entry_index = _checkin_entry_index(checkin, my_checkins_after_create)

    # 异步执行 AI 情感分析（不阻塞响应）
    background_tasks.add_task(_run_sentiment_analysis, str(checkin.id), req.content)

    partner_checkin, both_done = await _schedule_today_report_refresh(
        db,
        background_tasks,
        is_solo=is_solo,
        pair=pair,
        user=user,
        checkin_date=today,
    )

    # 关系树成长
    if not is_solo:
        from app.api.v1.tree import grow_tree_on_checkin

        background_tasks.add_task(
            grow_tree_on_checkin, str(req.pair_id), both_done or partner_checkin is not None, 0
        )

    context = _context_value(req)

    if context:
        await record_relationship_event(
            db,
            event_type="client.precheck.completed",
            pair_id=str(req.pair_id) if req.pair_id and not is_solo else None,
            user_id=user.id,
            entity_type="checkin",
            entity_id=checkin.id,
            source="client",
            payload={
                "intent": context.get("intent"),
                "risk_level": context.get("risk_level"),
                "upload_policy": context.get("upload_policy"),
                "privacy_mode": context.get("privacy_mode"),
                "client_tags": context.get("client_tags") or [],
                "pii_summary": context.get("pii_summary") or {},
            },
            idempotency_key=f"checkin:{checkin.id}:client-precheck",
        )

        if str(context.get("risk_level") or "none") in {"watch", "high"}:
            await record_relationship_event(
                db,
                event_type="client.risk.flagged",
                pair_id=str(req.pair_id) if req.pair_id and not is_solo else None,
                user_id=user.id,
                entity_type="checkin",
                entity_id=checkin.id,
                source="client",
                payload={
                    "intent": context.get("intent"),
                    "risk_level": context.get("risk_level"),
                    "risk_hits": context.get("risk_hits") or [],
                },
                idempotency_key=f"checkin:{checkin.id}:risk-flagged",
            )

        if str(context.get("privacy_mode") or "cloud") == "local_first":
            await record_relationship_event(
                db,
                event_type="checkin.local_saved",
                pair_id=str(req.pair_id) if req.pair_id and not is_solo else None,
                user_id=user.id,
                entity_type="checkin",
                entity_id=checkin.id,
                source="client",
                payload={
                    "upload_policy": context.get("upload_policy"),
                    "privacy_mode": context.get("privacy_mode"),
                },
                idempotency_key=f"checkin:{checkin.id}:local-saved",
            )
            if str(context.get("upload_policy") or "full") != "local_only":
                await record_relationship_event(
                    db,
                    event_type="checkin.synced",
                    pair_id=str(req.pair_id) if req.pair_id and not is_solo else None,
                    user_id=user.id,
                    entity_type="checkin",
                    entity_id=checkin.id,
                    source="client",
                    payload={
                        "upload_policy": context.get("upload_policy"),
                        "privacy_mode": context.get("privacy_mode"),
                    },
                    idempotency_key=f"checkin:{checkin.id}:synced",
                )

        if str(context.get("risk_level") or "none") == "high":
            await record_relationship_event(
                db,
                event_type="safety.crisis_gate_opened",
                pair_id=str(req.pair_id) if req.pair_id and not is_solo else None,
                user_id=user.id,
                entity_type="checkin",
                entity_id=checkin.id,
                source="client",
                payload={
                    "risk_hits": context.get("risk_hits") or [],
                    "intent": context.get("intent"),
                },
                idempotency_key=f"checkin:{checkin.id}:crisis-gate",
            )

    await record_relationship_event(
        db,
        event_type="checkin.created",
        pair_id=str(req.pair_id) if req.pair_id and not is_solo else None,
        user_id=user.id,
        entity_type="checkin",
        entity_id=checkin.id,
        payload={
            "mode": "solo" if is_solo else "pair",
            "mood_score": req.mood_score,
            "interaction_freq": req.interaction_freq,
            "deep_conversation": req.deep_conversation,
            "task_completed": req.task_completed,
            "client_context": context,
        },
        idempotency_key=f"checkin:{checkin.id}:created",
    )

    await refresh_profile_and_plan(
        db,
        pair_id=str(req.pair_id) if req.pair_id and not is_solo else None,
        user_id=str(user.id) if is_solo else None,
    )

    return _serialize_checkin_response(checkin, context, entry_index=entry_index)


@router.get("/today", response_model=dict)
async def get_today_status(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询今日打卡状态"""
    today = current_local_date()
    is_solo = mode == "solo"

    if is_solo:
        result = await db.execute(
            select(Checkin).where(
                Checkin.pair_id.is_(None),
                Checkin.user_id == user.id,
                Checkin.checkin_date == today,
            )
        )
        checkins = result.scalars().all()
        checkins = _ordered_checkins(list(checkins))
        my_checkin = checkins[0] if checkins else None
        my_done = len(checkins) > 0
        my_entry_count = len(checkins)
        partner_done = False
        both_done = False
        report_result = await db.execute(
            select(Report).where(
                Report.user_id == user.id,
                Report.report_date == today,
                Report.type == ReportType.SOLO,
            )
        )
        has_report = report_result.scalar_one_or_none() is not None
        return {
            "date": str(today),
            "my_done": my_done,
            "partner_done": partner_done,
            "both_done": both_done,
            "has_report": has_report,
            "has_solo_report": has_report,
            "my_entry_count": my_entry_count,
            "my_entry_limit": MAX_DAILY_CHECKINS,
            "my_remaining_supplements": _remaining_supplements(my_entry_count),
            "my_checkin": _checkin_summary(my_checkin, 1 if my_checkin else None),
            "my_checkins": _checkin_summaries(checkins),
        }

    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")

    pair = await validate_pair_access(pair_id, user, db, require_active=True)

    result = await db.execute(
        select(Checkin)
        .where(Checkin.pair_id == pair.id, Checkin.checkin_date == today)
        .order_by(Checkin.created_at.asc(), Checkin.id.asc())
    )
    checkins = list(result.scalars().all())

    my_checkins = _ordered_checkins([c for c in checkins if c.user_id == user.id])
    my_checkin = my_checkins[0] if my_checkins else None
    my_done = my_checkin is not None
    partner_done = any(c.user_id != user.id for c in checkins)
    both_done = my_done and partner_done
    my_entry_count = len(my_checkins)

    report_result = await db.execute(
        select(Report).where(
            Report.pair_id == pair.id,
            Report.report_date == today,
            Report.type == ReportType.DAILY,
        )
    )
    has_report = report_result.scalar_one_or_none() is not None

    solo_result = await db.execute(
        select(Report).where(
            Report.pair_id == pair.id,
            Report.report_date == today,
            Report.type == ReportType.SOLO,
        )
    )
    has_solo_report = solo_result.scalar_one_or_none() is not None

    return {
        "date": str(today),
        "my_done": my_done,
        "partner_done": partner_done,
        "both_done": both_done,
        "has_report": has_report,
        "has_solo_report": has_solo_report,
        "my_entry_count": my_entry_count,
        "my_entry_limit": MAX_DAILY_CHECKINS,
        "my_remaining_supplements": _remaining_supplements(my_entry_count),
        "my_checkin": _checkin_summary(my_checkin, 1 if my_checkin else None),
        "my_checkins": _checkin_summaries(my_checkins),
    }


@router.get("/history", response_model=list[CheckinResponse])
async def get_checkin_history(
    pair_id: str | None = None,
    mode: str | None = None,
    limit: int = 14,
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取打卡历史（隐私保护：仅返回自己的原始内容）"""
    is_solo = mode == "solo"

    if is_solo:
        query = (
            select(Checkin)
            .where(Checkin.pair_id.is_(None), Checkin.user_id == user.id)
            .order_by(Checkin.checkin_date.desc(), Checkin.created_at.desc())
        )
        if start_date:
            query = query.where(Checkin.checkin_date >= start_date)
        if end_date:
            query = query.where(Checkin.checkin_date <= end_date)
        result = await db.execute(
            query.limit(limit)
        )
        return _serialize_checkin_history(list(result.scalars().all()))

    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")

    pair = await validate_pair_access(pair_id, user, db, require_active=True)

    query = (
        select(Checkin)
        .where(Checkin.pair_id == pair.id, Checkin.user_id == user.id)
        .order_by(Checkin.checkin_date.desc(), Checkin.created_at.desc())
    )
    if start_date:
        query = query.where(Checkin.checkin_date >= start_date)
    if end_date:
        query = query.where(Checkin.checkin_date <= end_date)
    result = await db.execute(query.limit(limit))
    return _serialize_checkin_history(list(result.scalars().all()))


@router.get("/streak", response_model=dict)
async def get_checkin_streak(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取连续打卡天数"""
    is_solo = mode == "solo"

    if is_solo:
        result = await db.execute(
            select(Checkin.checkin_date)
            .where(Checkin.pair_id.is_(None), Checkin.user_id == user.id)
            .distinct()
            .order_by(Checkin.checkin_date.desc())
        )
    else:
        if not pair_id:
            raise HTTPException(status_code=422, detail="缺少配对ID")
        pair = await validate_pair_access(pair_id, user, db, require_active=True)
        result = await db.execute(
            select(Checkin.checkin_date)
            .where(Checkin.pair_id == pair.id, Checkin.user_id == user.id)
            .distinct()
            .order_by(Checkin.checkin_date.desc())
        )

    dates = [row[0] for row in result.all()]

    streak = 0
    expected = current_local_date()
    for d in dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif d < expected:
            break

    return {"streak": streak, "total_checkins": len(dates)}


# ── 后台任务 ──


async def _run_sentiment_analysis(checkin_id: str, content: str):
    """后台 AI 情感分析（更新 sentiment_score）"""
    try:
        result = await analyze_sentiment(content)
        from app.core.database import async_session

        async with async_session() as db:
            from sqlalchemy import update

            await db.execute(
                update(Checkin)
                .where(Checkin.id == checkin_id)
                .values(sentiment_score=result.get("score", 5.0))
            )
            await db.commit()
    except Exception:
        logger.exception("后台 AI 情感分析任务失败")


async def _auto_generate_daily(
    pair_id: str | uuid.UUID,
    pair_type: str,
    checkin_a_content: str,
    checkin_b_content: str,
    report_id: str | uuid.UUID | None = None,
):
    """后台自动生成每日报告"""
    try:
        from app.core.database import async_session
        from app.services.crisis_processor import process_crisis_from_report

        async with async_session() as db:
            today = current_local_date()
            normalized_pair_id = _normalize_uuid(pair_id)
            if report_id:
                report = await db.get(Report, _normalize_uuid(report_id))
                if not report:
                    return
            else:
                result = await db.execute(
                    select(Report).where(
                        Report.pair_id == normalized_pair_id,
                        Report.report_date == today,
                        Report.type == ReportType.DAILY,
                    )
                )
                report = result.scalar_one_or_none()
                if report and report.status == ReportStatus.COMPLETED:
                    return

            if not report:
                report = Report(
                    pair_id=normalized_pair_id,
                    type=ReportType.DAILY,
                    status=ReportStatus.PENDING,
                    content=None,
                    report_date=today,
                )
                db.add(report)
                await db.commit()
                await db.refresh(report)

            report_content = await generate_daily_report(
                pair_type, checkin_a_content, checkin_b_content
            )
            report.content = report_content
            report.health_score = report_content.get("health_score")
            report.status = ReportStatus.COMPLETED

            # 自动处理危机预警
            pair = await db.get(Pair, normalized_pair_id)
            if pair:
                await process_crisis_from_report(db, report, pair)

            await db.commit()
    except Exception:
        logger.exception("后台自动生成日报任务失败")


async def _auto_generate_solo(
    pair_id: str | uuid.UUID | None,
    pair_type: str,
    content: str,
    user_id: str | uuid.UUID,
    report_id: str | uuid.UUID | None = None,
):
    """后台自动生成个人情感日记（单方打卡时）"""
    try:
        from app.core.database import async_session

        async with async_session() as db:
            today = current_local_date()
            normalized_pair_id = _normalize_uuid(pair_id)
            normalized_user_id = _normalize_uuid(user_id)
            if report_id:
                report = await db.get(Report, _normalize_uuid(report_id))
                if not report:
                    return
            else:
                # 检查是否已有
                if normalized_pair_id:
                    result = await db.execute(
                        select(Report).where(
                            Report.pair_id == normalized_pair_id,
                            Report.report_date == today,
                            Report.type == ReportType.SOLO,
                        )
                    )
                else:
                    result = await db.execute(
                        select(Report).where(
                            Report.user_id == normalized_user_id,
                            Report.report_date == today,
                            Report.type == ReportType.SOLO,
                        )
                    )
                report = result.scalar_one_or_none()
                if report and report.status == ReportStatus.COMPLETED:
                    return

            if not report:
                report = Report(
                    pair_id=normalized_pair_id,
                    user_id=normalized_user_id,
                    type=ReportType.SOLO,
                    status=ReportStatus.PENDING,
                    content=None,
                    report_date=today,
                )
                db.add(report)
                await db.commit()
                await db.refresh(report)

            report_content = await generate_solo_report(pair_type, content)
            report.content = report_content
            report.health_score = report_content.get("health_score")
            report.status = ReportStatus.COMPLETED
            await db.commit()
            # Solo 报告不触发 crisis 预警（单方数据不足以判断）
    except Exception:
        logger.exception("后台自动生成个人日记任务失败")
