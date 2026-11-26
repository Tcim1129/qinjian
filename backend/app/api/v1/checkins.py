"""打卡接口：支持双方非对称打卡与个人情感日记。"""

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.time import current_local_date, local_date_cutoff_to_utc_naive
from app.api.deps import get_current_user, validate_pair_access
from app.models import User, Pair, Checkin, Report, PairStatus, ReportType, ReportStatus, UserNotification
from app.schemas import (
    CheckinRequest,
    CheckinResponse,
    CheckinVisibilityUpdateRequest,
    ClientContextPayload,
)
from app.ai import analyze_sentiment
from app.ai.reporter import generate_daily_report, generate_solo_report
from app.services.relationship_intelligence import (
    record_relationship_event,
    refresh_profile_and_plan,
)
from app.services.behavior_judgement import apply_judgement_to_payload
from app.services.checkin_visibility import (
    DEFAULT_SCOPE,
    PARTNER_VISIBLE_SCOPES,
    is_partner_visible,
    normalize_scope,
    pair_report_content,
    report_source_snapshot,
    report_sources_authorized,
)
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
MAX_CHECKIN_BACKFILL_DAYS = 30


def _resolve_checkin_date(requested_date: date | None, *, today: date) -> date:
    target_date = requested_date or today
    if target_date > today:
        raise HTTPException(status_code=422, detail="不能为未来的日期写记录")
    earliest_date = today - timedelta(days=MAX_CHECKIN_BACKFILL_DAYS)
    if target_date < earliest_date:
        raise HTTPException(
            status_code=422,
            detail=f"仅支持补记过去 {MAX_CHECKIN_BACKFILL_DAYS} 天内的记录",
        )
    return target_date


def _merge_supplement_content(existing_content: str | None, added_content: str) -> str:
    base = str(existing_content or "").strip()
    addition = str(added_content or "").strip()
    if not base:
        return addition
    if not addition or addition == base or base.endswith(addition):
        return base
    return f"{base}\n\n补充：{addition}"


def _merge_mood_tags(existing_mood_tags: dict | None, added_tags: list[str] | None) -> dict | None:
    merged: list[str] = []
    raw_existing = (existing_mood_tags or {}).get("tags") if isinstance(existing_mood_tags, dict) else []
    for raw in [*(raw_existing or []), *(added_tags or [])]:
        tag = str(raw or "").strip()
        if tag and tag not in merged:
            merged.append(tag)
    return {"tags": merged} if merged else existing_mood_tags


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
    if all(value is None for value in (
        req.mood_score, req.interaction_freq, req.interaction_initiative,
        req.deep_conversation, req.task_completed,
    )):
        return
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
    from app.services.notification_preferences import in_app_notification_enabled
    if not await in_app_notification_enabled(db, user_id, notification_type):
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


def _safe_client_context(context: dict | None) -> ClientContextPayload | None:
    if not isinstance(context, dict):
        return None
    try:
        return ClientContextPayload.model_validate(context)
    except Exception:
        return None


def _serialize_checkin_response(
    checkin: Checkin,
    context: dict | None,
) -> CheckinResponse:
    safe_context = _safe_client_context(context)
    analysis_source = "client_precheck" if safe_context else "server_ai"
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
        client_context=safe_context,
        analysis_source=analysis_source,
        client_precheck=safe_context,
        server_analysis={
            "status": "pending",
            "note": "服务端深分析会在后台继续完成。",
        },
        final_guidance=_build_local_guidance_from_context(context),
        safety_gate=safety_gate,
        visibility_scope=getattr(checkin, "visibility_scope", None) or "private",
        visibility_version=getattr(checkin, "visibility_version", 1),
        checkin_date=checkin.checkin_date,
        created_at=checkin.created_at,
    )


def _behavior_payload_for_checkin(
    *,
    pair_id: uuid.UUID | None,
    mood_score: float | None,
    interaction_freq: int | None,
    deep_conversation: bool | None,
    task_completed: bool | None,
    content: str,
    context: dict | None,
) -> dict:
    return apply_judgement_to_payload(
        {
            "mode": "solo" if pair_id is None else "pair",
            "mood_score": mood_score,
            "interaction_freq": interaction_freq,
            "deep_conversation": deep_conversation,
            "task_completed": task_completed,
            "client_context": context,
        },
        text=content,
        risk_level=(context or {}).get("risk_level"),
        sentiment_hint=(context or {}).get("sentiment_hint"),
    )


async def _ensure_pending_daily_report(
    db: AsyncSession,
    *,
    report_date: date,
    pair_id: uuid.UUID,
    force_refresh: bool = False,
) -> Report:
    result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.report_date == report_date,
            Report.type == ReportType.DAILY,
        )
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        if force_refresh or existing.status == ReportStatus.FAILED:
            existing.status = ReportStatus.PENDING
            existing.content = None
            existing.health_score = None
            existing.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.flush()
        return existing

    report = Report(
        pair_id=pair_id,
        type=ReportType.DAILY,
        status=ReportStatus.PENDING,
        content=None,
        health_score=None,
        report_date=report_date,
    )
    db.add(report)
    await db.flush()
    return report


async def schedule_checkin_side_effects(
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    *,
    checkin: Checkin,
    user: User,
    pair: Pair | None,
    context: dict | None,
    effective_privacy_mode: str = "cloud",
    eager_pending_reports: bool = True,
    is_supplement: bool = False,
) -> None:
    is_solo = pair is None
    pair_id = pair.id if pair is not None else None
    checkin_scope = str(getattr(checkin, "visibility_scope", None) or DEFAULT_SCOPE)
    bind_url = ""
    try:
        bind_url = str(getattr(db.get_bind(), "url", "") or "")
    except Exception:
        bind_url = ""
    is_in_memory_db = bind_url == "sqlite+aiosqlite:///:memory:"

    if not is_in_memory_db:
        background_tasks.add_task(
            _run_sentiment_analysis,
            checkin.id,
            checkin.content,
            user.id,
            effective_privacy_mode,
            pair_id,
        )

    if is_solo:
        solo_report_id = None
        if eager_pending_reports:
            pending_report = await _ensure_pending_solo_report(
                db,
                report_date=checkin.checkin_date,
                user_id=user.id,
                force_refresh=is_supplement,
            )
            solo_report_id = pending_report.id
        if not is_in_memory_db:
            background_tasks.add_task(
                _auto_generate_solo,
                None,
                "solo",
                checkin.content,
                user.id,
                effective_privacy_mode,
                solo_report_id,
                checkin.id,
                checkin.checkin_date,
            )
        return

    partner_result = await db.execute(
        select(Checkin).where(
            Checkin.pair_id == pair_id,
            Checkin.user_id != user.id,
            Checkin.checkin_date == checkin.checkin_date,
            Checkin.raw_deleted_at.is_(None),
            Checkin.visibility_scope.in_(PARTNER_VISIBLE_SCOPES),
        )
    )
    partner_checkin = partner_result.scalar_one_or_none()
    both_partner_visible = (
        partner_checkin is not None and is_partner_visible(checkin_scope)
    )

    if both_partner_visible and partner_checkin is not None and pair is not None:
        a_checkin = checkin if user.id == pair.user_a_id else partner_checkin
        b_checkin = partner_checkin if user.id == pair.user_a_id else checkin
        daily_report_id = None
        if eager_pending_reports:
            pending_daily = await _ensure_pending_daily_report(
                db,
                report_date=checkin.checkin_date,
                pair_id=pair.id,
                force_refresh=is_supplement,
            )
            daily_report_id = pending_daily.id
        if not is_in_memory_db:
            background_tasks.add_task(
                _auto_generate_daily,
                pair.id,
                pair.type.value,
                pair_report_content(a_checkin),
                pair_report_content(b_checkin),
                user.id,
                effective_privacy_mode,
                report_source_snapshot([a_checkin, b_checkin]),
                daily_report_id,
                checkin.id,
                checkin.checkin_date,
            )
    else:
        solo_report_id = None
        if eager_pending_reports:
            pending_report = await _ensure_pending_solo_report(
                db,
                report_date=checkin.checkin_date,
                user_id=user.id,
                pair_id=pair_id,
                force_refresh=is_supplement,
            )
            solo_report_id = pending_report.id
        if not is_in_memory_db:
            background_tasks.add_task(
                _auto_generate_solo,
                pair_id,
                pair.type.value if pair else "solo",
                checkin.content,
                user.id,
                effective_privacy_mode,
                solo_report_id,
                checkin.id,
                checkin.checkin_date,
            )

    if not is_supplement and is_partner_visible(checkin_scope) and not is_in_memory_db:
        from app.api.v1.tree import grow_tree_on_checkin

        background_tasks.add_task(
            grow_tree_on_checkin, pair_id, both_partner_visible, 0
        )
    if not eager_pending_reports and not is_in_memory_db:
        background_tasks.add_task(
            _run_checkin_profile_refresh,
            pair_id,
            user.id,
        )


async def _run_checkin_profile_refresh(
    pair_id: uuid.UUID | str | None,
    user_id: uuid.UUID | str | None,
) -> None:
    try:
        from app.core.database import async_session

        async with async_session() as db:
            await refresh_profile_and_plan(
                db,
                pair_id=str(pair_id) if pair_id else None,
                user_id=str(user_id) if not pair_id and user_id else None,
            )
            await db.commit()
    except Exception as exc:
        logger.warning("后台刷新关系画像失败，已跳过: %s", exc.__class__.__name__)


async def record_checkin_intelligence(
    db: AsyncSession,
    *,
    checkin: Checkin,
    user: User,
    pair_id: uuid.UUID | None,
    context: dict | None,
    page_path: str = "/checkin",
    refresh_profile: bool = True,
    is_supplement: bool = False,
) -> None:
    is_solo = pair_id is None
    today = current_local_date()
    is_historical_backfill = bool(checkin.checkin_date and checkin.checkin_date < today)
    event_occurred_at = (
        local_date_cutoff_to_utc_naive(checkin.checkin_date, hour=20)
        if is_historical_backfill
        else None
    )
    behavior_payload = _behavior_payload_for_checkin(
        pair_id=pair_id,
        mood_score=checkin.mood_score,
        interaction_freq=checkin.interaction_freq,
        deep_conversation=checkin.deep_conversation,
        task_completed=checkin.task_completed,
        content=checkin.content,
        context=context,
    )

    if context:
        await record_relationship_event(
            db,
            event_type="client.precheck.completed",
            pair_id=str(pair_id) if pair_id else None,
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
            pair_id=str(pair_id) if pair_id else None,
            source="client",
            page="checkin",
            path=page_path,
            target_type="checkin",
            target_id=checkin.id,
            payload=build_interaction_payload(
                {
                    "intent": context.get("intent"),
                    "client_tags": context.get("client_tags") or [],
                    "upload_policy": context.get("upload_policy"),
                    "privacy_mode": context.get("privacy_mode"),
                },
                text=checkin.content,
                risk_level=context.get("risk_level"),
                sentiment_hint=context.get("sentiment_hint"),
            ),
        )

        if str(context.get("risk_level") or "none") in {"watch", "high"}:
            await record_relationship_event(
                db,
                event_type="client.risk.flagged",
                pair_id=str(pair_id) if pair_id else None,
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

        if not is_historical_backfill and str(context.get("risk_level") or "none") == "high":
            await record_relationship_event(
                db,
                event_type="safety.crisis_gate_opened",
                pair_id=str(pair_id) if pair_id else None,
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

    if not is_supplement:
        await record_relationship_event(
            db,
            event_type="checkin.created",
            pair_id=str(pair_id) if pair_id else None,
            user_id=user.id,
            entity_type="checkin",
            entity_id=checkin.id,
            payload=behavior_payload,
            occurred_at=event_occurred_at,
            idempotency_key=f"checkin:{checkin.id}:created",
        )

    await record_user_interaction_event(
        db,
        event_type="checkin.submit",
        user_id=user.id,
        pair_id=str(pair_id) if pair_id else None,
        source="server",
        page="checkin",
        path=page_path,
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
            text=checkin.content,
            risk_level=(context or {}).get("risk_level"),
            sentiment_hint=(context or {}).get("sentiment_hint"),
        ),
    )

    if refresh_profile:
        await refresh_profile_and_plan(
            db,
            pair_id=str(pair_id) if pair_id else None,
            user_id=str(user.id) if is_solo else None,
        )


async def _ensure_pending_solo_report(
    db: AsyncSession,
    *,
    report_date: date,
    user_id: uuid.UUID,
    pair_id: uuid.UUID | None = None,
    force_refresh: bool = False,
) -> Report:
    if pair_id:
        result = await db.execute(
            select(Report)
            .where(
                Report.pair_id == pair_id,
                Report.user_id == user_id,
                Report.report_date == report_date,
                Report.type == ReportType.SOLO,
            )
            .order_by(Report.created_at.desc())
            .limit(1)
        )
    else:
        result = await db.execute(
            select(Report)
            .where(
                Report.pair_id.is_(None),
                Report.user_id == user_id,
                Report.report_date == report_date,
                Report.type == ReportType.SOLO,
            )
            .order_by(Report.created_at.desc())
            .limit(1)
        )
    existing = result.scalar_one_or_none()
    if existing:
        if force_refresh or existing.status == ReportStatus.FAILED:
            existing.status = ReportStatus.PENDING
            existing.content = None
            existing.health_score = None
            existing.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
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

    # 校验记录日期（支持今天及过去 30 天内补记；同一天已存在记录时自动转为补充）
    today = current_local_date()
    target_date = _resolve_checkin_date(req.checkin_date, today=today)
    if is_solo:
        result = await db.execute(
            select(Checkin)
            .where(
                Checkin.pair_id.is_(None),
                Checkin.user_id == user.id,
                Checkin.checkin_date == target_date,
                Checkin.raw_deleted_at.is_(None),
            )
            .order_by(Checkin.created_at.desc())
            .limit(1)
        )
    else:
        result = await db.execute(
            select(Checkin)
            .where(
                Checkin.pair_id == req.pair_id,
                Checkin.user_id == user.id,
                Checkin.checkin_date == target_date,
                Checkin.raw_deleted_at.is_(None),
            )
            .order_by(Checkin.created_at.desc())
            .limit(1)
        )
    existing_checkin = result.scalar_one_or_none()

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

    is_supplement = existing_checkin is not None
    if existing_checkin is not None:
        checkin = existing_checkin
        checkin.content = _merge_supplement_content(checkin.content, content_for_storage)
        checkin.mood_tags = _merge_mood_tags(checkin.mood_tags, req.mood_tags)
        if image_url:
            checkin.image_url = image_url
        if voice_url:
            checkin.voice_url = voice_url
        if context is not None:
            checkin.client_context = context
        if req.mood_score is not None:
            checkin.mood_score = req.mood_score
            checkin.interaction_freq = req.interaction_freq
            checkin.interaction_initiative = req.interaction_initiative
            checkin.deep_conversation = req.deep_conversation
            checkin.task_completed = req.task_completed
        # 内容补充后如果原记录处于已分享摘要态，先收回为仅自己可见，避免未经确认暴露新增内容
        if checkin.visibility_scope == "shared_summary":
            checkin.visibility_scope = "private"
            checkin.visibility_version = int(checkin.visibility_version or 1) + 1
        await db.flush()
        ensure_checkin_archive_fields(checkin, refresh=True)
    else:
        checkin = Checkin(
            pair_id=req.pair_id if not is_solo else None,
            user_id=user.id,
            content=content_for_storage,
            visibility_scope="private",
            image_url=image_url,
            voice_url=voice_url,
            mood_tags={"tags": req.mood_tags} if req.mood_tags else None,
            client_context=context,
            mood_score=req.mood_score,
            interaction_freq=req.interaction_freq,
            interaction_initiative=req.interaction_initiative,
            deep_conversation=req.deep_conversation,
            task_completed=req.task_completed,
            checkin_date=target_date,
        )
        db.add(checkin)
        await db.flush()
        ensure_checkin_archive_fields(checkin)

    await schedule_checkin_side_effects(
        db,
        background_tasks,
        checkin=checkin,
        user=user,
        pair=pair if not is_solo else None,
        context=context,
        effective_privacy_mode=effective_privacy_mode,
        eager_pending_reports=True,
        is_supplement=is_supplement,
    )

    await db.commit()
    await db.refresh(checkin)
    response = _serialize_checkin_response(checkin, context)

    try:
        await record_checkin_intelligence(
            db,
            checkin=checkin,
            user=user,
            pair_id=req.pair_id if not is_solo else None,
            context=context,
            page_path="/checkin",
            is_supplement=is_supplement,
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
    checkin_date: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询指定日期（默认今日）的打卡状态"""
    today = current_local_date()
    target_date = _resolve_checkin_date(checkin_date, today=today)
    is_solo = mode == "solo"

    def _build_my_checkin_summary(record: Checkin | None) -> dict:
        return {
            "id": str(record.id) if record else None,
            "pair_id": str(record.pair_id) if record and record.pair_id else None,
            "checkin_date": str(record.checkin_date) if record else str(target_date),
            "mood_score": record.mood_score if record else None,
            "interaction_freq": record.interaction_freq if record else None,
            "deep_conversation": record.deep_conversation if record else None,
            "task_completed": record.task_completed if record else None,
            "mood_tags": record.mood_tags if record else None,
            "visibility_scope": getattr(record, "visibility_scope", "private") if record else None,
            "visibility_version": getattr(record, "visibility_version", 1) if record else None,
            "content": record.content if record else None,
        }

    if is_solo:
        result = await db.execute(
            select(Checkin)
            .where(
                Checkin.pair_id.is_(None),
                Checkin.user_id == user.id,
                Checkin.checkin_date == target_date,
                Checkin.raw_deleted_at.is_(None),
            )
            .order_by(Checkin.created_at.desc())
        )
        checkins = result.scalars().all()
        my_checkin = checkins[0] if checkins else None
        my_done = len(checkins) > 0
        partner_done = False
        both_done = False
        report_result = await db.execute(
            select(Report)
            .where(
                Report.pair_id.is_(None),
                Report.user_id == user.id,
                Report.report_date == target_date,
                Report.type == ReportType.SOLO,
            )
            .order_by(Report.created_at.desc())
            .limit(1)
        )
        report = report_result.scalar_one_or_none()
        has_report = report is not None
        return {
            "date": str(target_date),
            "my_done": my_done,
            "partner_done": partner_done,
            "both_done": both_done,
            "has_report": has_report,
            "has_solo_report": has_report,
            "report_status": _report_status_value(report),
            "solo_report_status": _report_status_value(report),
            "my_checkin": _build_my_checkin_summary(my_checkin),
        }

    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")

    await validate_pair_access(pair_id, user, db, require_active=True)

    result = await db.execute(
        select(Checkin).where(
            Checkin.pair_id == pair_id,
            Checkin.checkin_date == target_date,
            Checkin.raw_deleted_at.is_(None),
        )
    )
    checkins = result.scalars().all()

    my_checkin = next((c for c in checkins if c.user_id == user.id), None)
    my_done = my_checkin is not None
    # 只看对方主动分享出来的记录：对方写了私密记录时既不能报 True，也不能报 False，
    # 否则单凭状态字段就能推断出对方今天有没有写。
    partner_visible = [
        c
        for c in checkins
        if c.user_id != user.id
        and is_partner_visible(normalize_scope(getattr(c, "visibility_scope", None)))
    ]
    partner_done = True if partner_visible else None
    both_done = True if my_done and partner_done else None

    report_result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.report_date == target_date,
            Report.type == ReportType.DAILY,
        )
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    report = report_result.scalar_one_or_none()
    has_report = report is not None

    solo_result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.user_id == user.id,
            Report.report_date == target_date,
            Report.type == ReportType.SOLO,
        )
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    solo_report = solo_result.scalar_one_or_none()
    has_solo_report = solo_report is not None

    return {
        "date": str(target_date),
        "my_done": my_done,
        "partner_done": partner_done,
        "both_done": both_done,
        "has_report": has_report,
        "has_solo_report": has_solo_report,
        "report_status": _report_status_value(report),
        "solo_report_status": _report_status_value(solo_report),
        "my_checkin": _build_my_checkin_summary(my_checkin),
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
            .where(
                Checkin.pair_id.is_(None),
                Checkin.user_id == user.id,
                Checkin.raw_deleted_at.is_(None),
            )
            .order_by(Checkin.checkin_date.desc())
            .limit(limit)
        )
        return [_serialize_checkin_response(c, c.client_context) for c in result.scalars().all()]

    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")

    await validate_pair_access(pair_id, user, db, require_active=True)

    result = await db.execute(
        select(Checkin)
        .where(
            Checkin.pair_id == pair_id,
            Checkin.user_id == user.id,
            Checkin.raw_deleted_at.is_(None),
        )
        .order_by(Checkin.checkin_date.desc())
        .limit(limit)
    )
    return [_serialize_checkin_response(c, c.client_context) for c in result.scalars().all()]


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
            .where(
                Checkin.pair_id.is_(None),
                Checkin.user_id == user.id,
                Checkin.raw_deleted_at.is_(None),
            )
            .distinct()
            .order_by(Checkin.checkin_date.desc())
        )
    else:
        if not pair_id:
            raise HTTPException(status_code=422, detail="缺少配对ID")
        await validate_pair_access(pair_id, user, db, require_active=True)
        result = await db.execute(
            select(Checkin.checkin_date)
            .where(
                Checkin.pair_id == pair_id,
                Checkin.user_id == user.id,
                Checkin.raw_deleted_at.is_(None),
            )
            .distinct()
            .order_by(Checkin.checkin_date.desc())
        )

    dates = [row[0] for row in result.all()]

    streak = 0
    today = current_local_date()
    expected = today
    if dates and dates[0] == today - timedelta(days=1):
        expected = today - timedelta(days=1)
    for d in dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif d < expected:
            break

    return {"streak": streak, "total_checkins": len(dates)}


@router.patch("/{checkin_id}/visibility", response_model=CheckinResponse)
async def update_checkin_visibility(
    checkin_id: uuid.UUID,
    req: CheckinVisibilityUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新打卡记录的可见性范围（契约对齐：PATCH /api/v1/checkins/{checkin_id}/visibility）。"""
    from app.services.checkin_visibility import change_visibility

    checkin = await db.get(Checkin, checkin_id)
    if checkin is None or checkin.raw_deleted_at is not None or str(checkin.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="记录不存在")

    expected_ver = req.expected_version or str(checkin.visibility_version or 1)
    await change_visibility(
        db,
        record_id=checkin.id,
        actor_user_id=user.id,
        expected_version=expected_ver,
        target_scope=req.visibility_scope,
        sharing_confirmed=req.sharing_confirmed,
    )
    await db.commit()
    await db.refresh(checkin)
    return _serialize_checkin_response(checkin, checkin.client_context)


# 后台任务


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
            existing_checkin = await db.get(Checkin, checkin_uuid)
            if not existing_checkin or existing_checkin.raw_deleted_at is not None:
                return
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
    source_versions: list | None = None,
    report_id: uuid.UUID | str | None = None,
    checkin_id: uuid.UUID | str | None = None,
    report_date: date | None = None,
):
    """后台自动生成每日报告"""
    resolved_report_id: uuid.UUID | None = _as_uuid(report_id)
    try:
        pair_uuid = _as_uuid(pair_id)
        checkin_uuid = _as_uuid(checkin_id)
        from app.core.database import async_session
        from app.services.crisis_processor import process_crisis_from_report

        today = report_date or current_local_date()
        async with async_session() as db:
            if checkin_uuid:
                source_checkin = await db.get(Checkin, checkin_uuid)
                if not source_checkin or source_checkin.raw_deleted_at is not None:
                    return
            if resolved_report_id:
                report = await db.get(Report, resolved_report_id)
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
                result = await db.execute(
                    select(Report).where(
                        Report.pair_id == pair_uuid,
                        Report.report_date == today,
                        Report.type == ReportType.DAILY,
                    )
                )
                existing = result.scalar_one_or_none()
                if existing:
                    if existing.status != ReportStatus.FAILED:
                        return
                    await db.delete(existing)
                    await db.flush()

                report = Report(
                    pair_id=pair_uuid,
                    type=ReportType.DAILY,
                    status=ReportStatus.PENDING,
                    content=None,
                    report_date=today,
                )
                db.add(report)
                await db.flush()
                resolved_report_id = report.id
                await db.commit()

        async with async_session() as db:
            if not await report_sources_authorized(db, source_versions):
                report = await db.get(Report, resolved_report_id)
                if report:
                    report.status = ReportStatus.FAILED
                    await db.commit()
                return
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
            report = await db.get(Report, resolved_report_id)
            if not report:
                return
            # 落库前校验：来源记录可能已被撤回共享，撤回前的内容绝不能写回
            if not await report_sources_authorized(db, source_versions, lock=True):
                report.content = None
                report.health_score = None
                report.status = ReportStatus.FAILED
                await db.commit()
                return
            report.content = report_content
            report.health_score = report_content.get("health_score")
            report.status = ReportStatus.COMPLETED

            # 仅对当天日报触发实时危机预警，历史补记归档趋势而不弹过期危机拦截
            pair = await db.get(Pair, pair_uuid)
            if pair:
                if report.report_date >= current_local_date():
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
        if resolved_report_id:
            try:
                from app.core.database import async_session

                async with async_session() as err_db:
                    err_report = await err_db.get(Report, resolved_report_id)
                    if err_report and err_report.status == ReportStatus.PENDING:
                        err_report.status = ReportStatus.FAILED
                        await err_db.commit()
            except Exception:
                logger.exception("标记失败日报状态出错")


async def _auto_generate_solo(
    pair_id: uuid.UUID | str | None,
    pair_type: str,
    content: str,
    user_id: uuid.UUID | str,
    privacy_mode: str = "cloud",
    report_id: uuid.UUID | str | None = None,
    checkin_id: uuid.UUID | str | None = None,
    report_date: date | None = None,
):
    """后台自动生成个人情感日记（单方打卡时）"""
    report_uuid = _as_uuid(report_id)
    try:
        pair_uuid = _as_uuid(pair_id)
        user_uuid = _as_uuid(user_id)
        checkin_uuid = _as_uuid(checkin_id)
        from app.core.database import async_session

        today = report_date or current_local_date()
        async with async_session() as db:
            if checkin_uuid:
                source_checkin = await db.get(Checkin, checkin_uuid)
                if not source_checkin or source_checkin.raw_deleted_at is not None:
                    return
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
        if report_uuid:
            try:
                from app.core.database import async_session

                async with async_session() as err_db:
                    err_report = await err_db.get(Report, report_uuid)
                    if err_report and err_report.status == ReportStatus.PENDING:
                        err_report.status = ReportStatus.FAILED
                        await err_db.commit()
            except Exception:
                logger.exception("标记失败个人日记状态出错")
