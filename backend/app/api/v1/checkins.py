"""打卡系统接口（Phase 3 增强：支持非对称打卡 + 个人情感日记）"""

import logging
import uuid
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.time import current_local_date
from app.api.deps import get_current_user, validate_pair_access
from app.models import User, Pair, Checkin, Report, PairStatus, ReportType, ReportStatus, UserNotification
from app.schemas import CheckinRequest, CheckinResponse
from app.ai import analyze_sentiment
from app.ai.reporter import generate_daily_report, generate_solo_report
from app.services.relationship_intelligence import (
    record_relationship_event,
    refresh_profile_and_plan,
)
from app.services.behavior_judgement import apply_judgement_to_payload
from app.services.interaction_events import (
    build_interaction_payload,
    record_user_interaction_event,
)
from app.services.privacy_audit import privacy_audit_scope
from app.services.product_prefs import resolve_privacy_mode
from app.services.privacy_sandbox import redact_sensitive_text
from app.services.timeline_archive import ensure_checkin_archive_fields
from app.services.upload_access import actor_can_reference_upload, normalize_upload_storage_path

router = APIRouter(prefix="/checkins", tags=["打卡"])
logger = logging.getLogger(__name__)


def _as_uuid(value: uuid.UUID | str | None) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _context_value(req: CheckinRequest) -> dict | None:
    return req.client_context.model_dump() if req.client_context else None


def _report_status_value(report: Report | None) -> str:
    return str(report.status.value if report else "idle")


def _normalize_client_context(
    req: CheckinRequest,
    *,
    user: User,
) -> tuple[dict | None, str, str]:
    context = _context_value(req)
    _ = user
    privacy_mode = resolve_privacy_mode(None)
    if not context:
        return None, privacy_mode, req.content

    normalized = dict(context)
    normalized["privacy_mode"] = privacy_mode
    normalized["upload_policy"] = "full"
    if normalized.get("redacted_text"):
        normalized["redacted_text"] = redact_sensitive_text(
            str(normalized.get("redacted_text") or req.content)
        )

    return normalized, privacy_mode, req.content


async def _normalize_owned_upload_reference(
    value: str | None,
    *,
    user: User,
    db: AsyncSession,
    label: str,
) -> str | None:
    normalized = normalize_upload_storage_path(str(value).strip() if value else None)
    if normalized and not await actor_can_reference_upload(
        db,
        normalized,
        actor_user_id=user.id,
    ):
        raise HTTPException(status_code=403, detail=f"无权使用这份{label}")
    return normalized


def _build_local_guidance_from_context(context: dict | None) -> str | None:
    if not isinstance(context, dict):
        return None

    risk_level = str(context.get("risk_level") or "none")
    intent = str(context.get("intent") or "daily")
    pii_summary = context.get("pii_summary") or {}
    pii_hits = int(pii_summary.get("total_hits") or 0)
    upload_policy = str(context.get("upload_policy") or "full")

    if risk_level == "high":
        return "本地预检识别到高风险信号，建议先使用求助资源、手动记录或冷静步骤，而不是直接进入普通智能建议。"
    if intent == "emergency":
        return "本地预检判断你更像是在处理眼前的冲突，建议先看一句更稳妥的表达，再决定是否发送。"
    if pii_hits > 0:
        return "本次内容包含敏感信息，系统会继续按受控方式处理并长期保留分析结果。"
    if intent == "reflection":
        return "这次输入更适合进入复盘视角，建议结合时间轴和周评估一起看变化。"
    return "本地预检已完成，系统会结合后端深分析继续整理更完整的判断。"


def _missing_checkin_background_fields(req: CheckinRequest) -> list[str]:
    missing_fields: list[str] = []

    if req.mood_score is None:
        missing_fields.append("今天整体感受")
    if req.interaction_freq is None:
        missing_fields.append("互动频率")
    if not str(req.interaction_initiative or "").strip():
        missing_fields.append("谁先开口")
    if req.deep_conversation is None:
        missing_fields.append("有没有深聊")
    if req.task_completed is None:
        missing_fields.append("之前的约定")

    return missing_fields


def _ensure_checkin_background_complete(req: CheckinRequest) -> None:
    missing_fields = _missing_checkin_background_fields(req)
    if missing_fields:
        raise HTTPException(
            status_code=422,
            detail=f"背景补充未完成：{'、'.join(missing_fields)}",
        )


async def _queue_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    content: str,
    target_path: str = "/report",
    notification_type: str = "report_ready",
) -> None:
    if not user_id:
        return
    db.add(
        UserNotification(
            user_id=user_id,
            type=notification_type,
            content=content,
            target_path=target_path,
        )
    )
    await db.flush()


def _serialize_checkin_response(
    checkin: Checkin,
    context: dict | None,
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
        checkin_date=checkin.checkin_date,
        created_at=checkin.created_at,
    )


def _behavior_payload_for_checkin(req: CheckinRequest, context: dict | None) -> dict:
    return apply_judgement_to_payload(
        {
            "mode": "solo" if req.pair_id is None else "pair",
            "mood_score": req.mood_score,
            "interaction_freq": req.interaction_freq,
            "deep_conversation": req.deep_conversation,
            "task_completed": req.task_completed,
            "client_context": context,
        },
        text=req.content,
        risk_level=(context or {}).get("risk_level"),
        sentiment_hint=(context or {}).get("sentiment_hint"),
    )


async def _ensure_pending_solo_report(
    db: AsyncSession,
    *,
    report_date: date,
    user_id: uuid.UUID,
    pair_id: uuid.UUID | None = None,
) -> Report:
    if pair_id:
        result = await db.execute(
            select(Report).where(
                Report.pair_id == pair_id,
                Report.user_id == user_id,
                Report.report_date == report_date,
                Report.type == ReportType.SOLO,
            )
        )
    else:
        result = await db.execute(
            select(Report).where(
                Report.pair_id.is_(None),
                Report.user_id == user_id,
                Report.report_date == report_date,
                Report.type == ReportType.SOLO,
            )
        )
    existing = result.scalar_one_or_none()
    if existing:
        if existing.status == ReportStatus.FAILED:
            existing.status = ReportStatus.PENDING
            existing.content = None
            existing.health_score = None
            await db.flush()
        return existing

    report = Report(
        pair_id=pair_id,
        user_id=user_id,
        type=ReportType.SOLO,
        status=ReportStatus.PENDING,
        content=None,
        health_score=None,
        report_date=report_date,
    )
    db.add(report)
    await db.flush()
    return report


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

    # 检查今日是否已打卡
    today = current_local_date()
    if is_solo:
        result = await db.execute(
            select(Checkin).where(
                Checkin.pair_id.is_(None),
                Checkin.user_id == user.id,
                Checkin.checkin_date == today,
            )
        )
    else:
        result = await db.execute(
            select(Checkin).where(
                Checkin.pair_id == req.pair_id,
                Checkin.user_id == user.id,
                Checkin.checkin_date == today,
            )
        )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="今天已经打过卡了")

    context, effective_privacy_mode, content_for_storage = _normalize_client_context(
        req,
        user=user,
    )
    image_url = await _normalize_owned_upload_reference(
        req.image_url,
        user=user,
        db=db,
        label="图片",
    )
    voice_url = await _normalize_owned_upload_reference(
        req.voice_url,
        user=user,
        db=db,
        label="语音",
    )
    _ensure_checkin_background_complete(req)
    # 创建打卡记录
    checkin = Checkin(
        pair_id=req.pair_id if not is_solo else None,
        user_id=user.id,
        content=content_for_storage,
        image_url=image_url,
        voice_url=voice_url,
        mood_tags={"tags": req.mood_tags} if req.mood_tags else None,
        client_context=context,
        mood_score=req.mood_score,
        interaction_freq=req.interaction_freq,
        interaction_initiative=req.interaction_initiative,
        deep_conversation=req.deep_conversation,
        task_completed=req.task_completed,
        checkin_date=today,
    )
    db.add(checkin)
    await db.flush()
    ensure_checkin_archive_fields(checkin)

    # 异步执行 AI 情感分析（不阻塞响应）
    background_tasks.add_task(
        _run_sentiment_analysis,
        checkin.id,
        content_for_storage,
        user.id,
        effective_privacy_mode,
        req.pair_id if not is_solo else None,
    )

    partner_checkin = None
    if is_solo:
        pending_report = await _ensure_pending_solo_report(
            db,
            report_date=today,
            user_id=user.id,
        )
        background_tasks.add_task(
            _auto_generate_solo,
            None,
            "solo",
            checkin.content,
            user.id,
            effective_privacy_mode,
            pending_report.id,
        )
    else:
        # 检查对方是否也打卡完毕
        partner_result = await db.execute(
            select(Checkin).where(
                Checkin.pair_id == req.pair_id,
                Checkin.user_id != user.id,
                Checkin.checkin_date == today,
            )
        )
        partner_checkin = partner_result.scalar_one_or_none()

        if partner_checkin and pair:
            checkin_a_content = (
                checkin.content
                if user.id == pair.user_a_id
                else partner_checkin.content
            )
            checkin_b_content = (
                partner_checkin.content
                if user.id == pair.user_a_id
                else checkin.content
            )
            background_tasks.add_task(
                _auto_generate_daily,
                req.pair_id,
                pair.type.value,
                checkin_a_content,
                checkin_b_content,
                user.id,
                effective_privacy_mode,
            )
        else:
            pending_report = await _ensure_pending_solo_report(
                db,
                report_date=today,
                user_id=user.id,
                pair_id=req.pair_id,
            )
            background_tasks.add_task(
                _auto_generate_solo,
                req.pair_id,
                pair.type.value if pair else "solo",
                checkin.content,
                user.id,
                effective_privacy_mode,
                pending_report.id,
            )

    # 关系树成长
    if not is_solo:
        from app.api.v1.tree import grow_tree_on_checkin

        background_tasks.add_task(
            grow_tree_on_checkin, req.pair_id, partner_checkin is not None, 0
        )

    await db.commit()
    await db.refresh(checkin)
    response = _serialize_checkin_response(checkin, context)

    try:
        behavior_payload = _behavior_payload_for_checkin(req, context)

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
                    "sentiment_hint": context.get("sentiment_hint"),
                    "inferred_language": behavior_payload.get("inferred_language"),
                    "inferred_tone": behavior_payload.get("inferred_tone"),
                    "message_length_bucket": behavior_payload.get(
                        "message_length_bucket"
                    ),
                    "reaction_type": behavior_payload.get("reaction_type"),
                    "deviation_candidate": behavior_payload.get("deviation_candidate"),
                },
                idempotency_key=f"checkin:{checkin.id}:client-precheck",
            )

            await record_user_interaction_event(
                db,
                event_type="checkin.precheck",
                user_id=user.id,
                pair_id=str(req.pair_id) if req.pair_id and not is_solo else None,
                source="client",
                page="checkin",
                path="/checkin",
                target_type="checkin",
                target_id=checkin.id,
                payload=build_interaction_payload(
                    {
                        "intent": context.get("intent"),
                        "client_tags": context.get("client_tags") or [],
                        "upload_policy": context.get("upload_policy"),
                        "privacy_mode": context.get("privacy_mode"),
                    },
                    text=content_for_storage,
                    risk_level=context.get("risk_level"),
                    sentiment_hint=context.get("sentiment_hint"),
                ),
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
            payload=behavior_payload,
            idempotency_key=f"checkin:{checkin.id}:created",
        )

        await record_user_interaction_event(
            db,
            event_type="checkin.submit",
            user_id=user.id,
            pair_id=str(req.pair_id) if req.pair_id and not is_solo else None,
            source="server",
            page="checkin",
            path="/checkin",
            http_method="POST",
            http_status=200,
            target_type="checkin",
            target_id=checkin.id,
            payload=build_interaction_payload(
                {
                    "mode": "solo" if is_solo else "pair",
                    "checkin_id": str(checkin.id),
                    "client_context": context,
                },
                text=content_for_storage,
                risk_level=(context or {}).get("risk_level"),
                sentiment_hint=(context or {}).get("sentiment_hint"),
            ),
        )

        await refresh_profile_and_plan(
            db,
            pair_id=str(req.pair_id) if req.pair_id and not is_solo else None,
            user_id=str(user.id) if is_solo else None,
        )

        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.exception(
            "打卡核心记录已保存，但后续关系智能处理失败: %s",
            exc.__class__.__name__,
        )

    return response


@router.get("/today", response_model=dict)
async def get_today_status(
    pair_id: uuid.UUID | None = None,
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
        my_checkin = checkins[0] if checkins else None
        my_done = len(checkins) > 0
        partner_done = False
        both_done = False
        report_result = await db.execute(
            select(Report).where(
                Report.user_id == user.id,
                Report.report_date == today,
                Report.type == ReportType.SOLO,
            )
        )
        report = report_result.scalar_one_or_none()
        has_report = report is not None
        return {
            "date": str(today),
            "my_done": my_done,
            "partner_done": partner_done,
            "both_done": both_done,
            "has_report": has_report,
            "has_solo_report": has_report,
            "report_status": _report_status_value(report),
            "solo_report_status": _report_status_value(report),
            "my_checkin": {
                "mood_score": my_checkin.mood_score if my_checkin else None,
                "interaction_freq": my_checkin.interaction_freq if my_checkin else None,
                "deep_conversation": my_checkin.deep_conversation
                if my_checkin
                else None,
                "task_completed": my_checkin.task_completed if my_checkin else None,
                "content": my_checkin.content if my_checkin else None,
            },
        }

    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")

    await validate_pair_access(pair_id, user, db, require_active=True)

    result = await db.execute(
        select(Checkin).where(Checkin.pair_id == pair_id, Checkin.checkin_date == today)
    )
    checkins = result.scalars().all()

    my_checkin = next((c for c in checkins if c.user_id == user.id), None)
    my_done = my_checkin is not None
    partner_done = any(c.user_id != user.id for c in checkins)
    both_done = my_done and partner_done

    report_result = await db.execute(
        select(Report).where(
            Report.pair_id == pair_id,
            Report.report_date == today,
            Report.type == ReportType.DAILY,
        )
    )
    report = report_result.scalar_one_or_none()
    has_report = report is not None

    solo_result = await db.execute(
        select(Report).where(
            Report.pair_id == pair_id,
            Report.user_id == user.id,
            Report.report_date == today,
            Report.type == ReportType.SOLO,
        )
    )
    solo_report = solo_result.scalar_one_or_none()
    has_solo_report = solo_report is not None

    return {
        "date": str(today),
        "my_done": my_done,
        "partner_done": partner_done,
        "both_done": both_done,
        "has_report": has_report,
        "has_solo_report": has_solo_report,
        "report_status": _report_status_value(report),
        "solo_report_status": _report_status_value(solo_report),
        "my_checkin": {
            "mood_score": my_checkin.mood_score if my_checkin else None,
            "interaction_freq": my_checkin.interaction_freq if my_checkin else None,
            "deep_conversation": my_checkin.deep_conversation if my_checkin else None,
            "task_completed": my_checkin.task_completed if my_checkin else None,
            "content": my_checkin.content if my_checkin else None,
        },
    }


@router.get("/history", response_model=list[CheckinResponse])
async def get_checkin_history(
    pair_id: uuid.UUID | None = None,
    mode: str | None = None,
    limit: int = 14,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取打卡历史（隐私保护：仅返回自己的原始内容）"""
    is_solo = mode == "solo"

    if is_solo:
        result = await db.execute(
            select(Checkin)
            .where(Checkin.pair_id.is_(None), Checkin.user_id == user.id)
            .order_by(Checkin.checkin_date.desc())
            .limit(limit)
        )
        return result.scalars().all()

    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")

    await validate_pair_access(pair_id, user, db, require_active=True)

    result = await db.execute(
        select(Checkin)
        .where(Checkin.pair_id == pair_id, Checkin.user_id == user.id)
        .order_by(Checkin.checkin_date.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/streak", response_model=dict)
async def get_checkin_streak(
    pair_id: uuid.UUID | None = None,
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
        await validate_pair_access(pair_id, user, db, require_active=True)
        result = await db.execute(
            select(Checkin.checkin_date)
            .where(Checkin.pair_id == pair_id, Checkin.user_id == user.id)
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


async def _run_sentiment_analysis(
    checkin_id: uuid.UUID | str,
    content: str,
    user_id: uuid.UUID | str | None = None,
    privacy_mode: str = "cloud",
    pair_id: uuid.UUID | str | None = None,
):
    """后台 AI 情感分析（更新 sentiment_score）"""
    try:
        checkin_uuid = _as_uuid(checkin_id)
        from app.core.database import async_session

        async with async_session() as db:
            try:
                with privacy_audit_scope(
                    db=db,
                    user_id=_as_uuid(user_id),
                    pair_id=_as_uuid(pair_id),
                    scope="pair" if pair_id else "solo",
                    run_type="checkin_sentiment_analysis",
                    privacy_mode=privacy_mode,
                ):
                    result = await analyze_sentiment(content)
            except Exception:
                await db.commit()
                raise
            from sqlalchemy import update

            await db.execute(
                update(Checkin)
                .where(Checkin.id == checkin_uuid)
                .values(sentiment_score=result.get("score", 5.0))
            )
            await db.commit()
    except Exception as exc:
        logger.warning("后台 AI 情感分析任务失败，已跳过: %s", exc.__class__.__name__)


async def _auto_generate_daily(
    pair_id: uuid.UUID | str,
    pair_type: str,
    checkin_a_content: str,
    checkin_b_content: str,
    user_id: uuid.UUID | str | None = None,
    privacy_mode: str = "cloud",
):
    """后台自动生成每日报告"""
    try:
        pair_uuid = _as_uuid(pair_id)
        from app.core.database import async_session
        from app.services.crisis_processor import process_crisis_from_report

        today = current_local_date()
        report_id: uuid.UUID | None = None
        async with async_session() as db:
            result = await db.execute(
                select(Report).where(
                    Report.pair_id == pair_uuid,
                    Report.report_date == today,
                    Report.type == ReportType.DAILY,
                )
            )
            if result.scalar_one_or_none():
                return

            report = Report(
                pair_id=pair_uuid,
                type=ReportType.DAILY,
                status=ReportStatus.PENDING,
                content=None,
                report_date=today,
            )
            db.add(report)
            await db.flush()
            report_id = report.id
            await db.commit()

        async with async_session() as db:
            try:
                with privacy_audit_scope(
                    db=db,
                    user_id=_as_uuid(user_id),
                    pair_id=pair_uuid,
                    scope="pair",
                    run_type="daily_report_generation",
                    privacy_mode=privacy_mode,
                ):
                    report_content = await generate_daily_report(
                        pair_type, checkin_a_content, checkin_b_content
                    )
            except Exception:
                await db.commit()
                raise
            await db.commit()

        async with async_session() as db:
            report = await db.get(Report, report_id)
            if not report:
                return
            report.content = report_content
            report.health_score = report_content.get("health_score")
            report.status = ReportStatus.COMPLETED

            # 自动处理危机预警
            pair = await db.get(Pair, pair_uuid)
            if pair:
                await process_crisis_from_report(db, report, pair)
                await _queue_notification(
                    db,
                    user_id=pair.user_a_id,
                    content="新的关系简报已经整理好了，可以直接回看重点。",
                )
                await _queue_notification(
                    db,
                    user_id=pair.user_b_id,
                    content="新的关系简报已经整理好了，可以直接回看重点。",
                )

            await db.commit()
    except Exception:
        logger.exception("后台自动生成日报任务失败")


async def _auto_generate_solo(
    pair_id: uuid.UUID | str | None,
    pair_type: str,
    content: str,
    user_id: uuid.UUID | str,
    privacy_mode: str = "cloud",
    report_id: uuid.UUID | str | None = None,
):
    """后台自动生成个人情感日记（单方打卡时）"""
    try:
        pair_uuid = _as_uuid(pair_id)
        user_uuid = _as_uuid(user_id)
        report_uuid = _as_uuid(report_id)
        from app.core.database import async_session

        today = current_local_date()
        async with async_session() as db:
            if report_uuid:
                report = await db.get(Report, report_uuid)
                if not report:
                    return
                if report.status == ReportStatus.COMPLETED and report.content:
                    return
                if report.status == ReportStatus.FAILED:
                    report.status = ReportStatus.PENDING
                    report.content = None
                    report.health_score = None
                    await db.commit()
            else:
                if pair_uuid:
                    result = await db.execute(
                        select(Report).where(
                            Report.pair_id == pair_uuid,
                            Report.user_id == user_uuid,
                            Report.report_date == today,
                            Report.type == ReportType.SOLO,
                        )
                    )
                else:
                    result = await db.execute(
                        select(Report).where(
                            Report.user_id == user_uuid,
                            Report.pair_id.is_(None),
                            Report.report_date == today,
                            Report.type == ReportType.SOLO,
                        )
                    )
                existing = result.scalar_one_or_none()
                if existing:
                    report_uuid = existing.id
                    if existing.status == ReportStatus.COMPLETED and existing.content:
                        return
                else:
                    report = Report(
                        pair_id=pair_uuid,
                        user_id=user_uuid,
                        type=ReportType.SOLO,
                        status=ReportStatus.PENDING,
                        content=None,
                        report_date=today,
                    )
                    db.add(report)
                    await db.flush()
                    report_uuid = report.id
                    await db.commit()

        async with async_session() as db:
            try:
                with privacy_audit_scope(
                    db=db,
                    user_id=user_uuid,
                    pair_id=pair_uuid,
                    scope="pair" if pair_uuid else "solo",
                    run_type="solo_report_generation",
                    privacy_mode=privacy_mode,
                ):
                    report_content = await generate_solo_report(pair_type, content)
            except Exception:
                await db.commit()
                raise
            await db.commit()

        async with async_session() as db:
            report = await db.get(Report, report_uuid)
            if not report:
                return
            report.content = report_content
            report.health_score = report_content.get("health_score")
            report.status = ReportStatus.COMPLETED
            await _queue_notification(
                db,
                user_id=user_uuid,
                content="你的个人简报已经整理好了，可以回来看重点。",
            )
            await db.commit()
            # Solo 报告不触发 crisis 预警（单方数据不足以判断）
    except Exception:
        logger.exception("后台自动生成个人日记任务失败")
