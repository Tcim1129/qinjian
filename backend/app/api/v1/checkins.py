"""打卡系统接口（Phase 3 增强：支持非对称打卡 + 个人情感日记）"""

import logging
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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
    today = date.today()
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

    # 异步执行 AI 情感分析（不阻塞响应）
    background_tasks.add_task(_run_sentiment_analysis, str(checkin.id), req.content)

    partner_checkin = None
    if is_solo:
        background_tasks.add_task(
            _auto_generate_solo, None, "solo", checkin.content, str(user.id)
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
                str(req.pair_id),
                pair.type.value,
                checkin_a_content,
                checkin_b_content,
            )
        else:
            background_tasks.add_task(
                _auto_generate_solo,
                str(req.pair_id),
                pair.type.value if pair else "solo",
                checkin.content,
                str(user.id),
            )

    # 关系树成长
    if not is_solo:
        from app.api.v1.tree import grow_tree_on_checkin

        background_tasks.add_task(
            grow_tree_on_checkin, str(req.pair_id), partner_checkin is not None, 0
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

    return _serialize_checkin_response(checkin, context)


@router.get("/today", response_model=dict)
async def get_today_status(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询今日打卡状态"""
    today = date.today()
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
        has_report = report_result.scalar_one_or_none() is not None
        return {
            "date": str(today),
            "my_done": my_done,
            "partner_done": partner_done,
            "both_done": both_done,
            "has_report": has_report,
            "has_solo_report": has_report,
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
    has_report = report_result.scalar_one_or_none() is not None

    solo_result = await db.execute(
        select(Report).where(
            Report.pair_id == pair_id,
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
    pair_id: str | None = None,
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
        await validate_pair_access(pair_id, user, db, require_active=True)
        result = await db.execute(
            select(Checkin.checkin_date)
            .where(Checkin.pair_id == pair_id, Checkin.user_id == user.id)
            .distinct()
            .order_by(Checkin.checkin_date.desc())
        )

    dates = [row[0] for row in result.all()]

    streak = 0
    expected = date.today()
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
    pair_id: str, pair_type: str, checkin_a_content: str, checkin_b_content: str
):
    """后台自动生成每日报告"""
    try:
        from app.core.database import async_session
        from app.services.crisis_processor import process_crisis_from_report

        async with async_session() as db:
            today = date.today()
            result = await db.execute(
                select(Report)
                .where(
                    Report.pair_id == pair_id,
                    Report.report_date == today,
                    Report.type == ReportType.DAILY,
                )
                .order_by(Report.created_at.desc())
                .limit(1)
            )
            if result.scalars().first():
                return

            report = Report(
                pair_id=pair_id,
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
            pair = await db.get(Pair, pair_id)
            if pair:
                await process_crisis_from_report(db, report, pair)

            await db.commit()
    except Exception:
        logger.exception("后台自动生成日报任务失败")


async def _auto_generate_solo(
    pair_id: str | None, pair_type: str, content: str, user_id: str
):
    """后台自动生成个人情感日记（单方打卡时）"""
    try:
        from app.core.database import async_session

        async with async_session() as db:
            today = date.today()
            # 检查是否已有
            if pair_id:
                result = await db.execute(
                    select(Report)
                    .where(
                        Report.pair_id == pair_id,
                        Report.report_date == today,
                        Report.type == ReportType.SOLO,
                    )
                    .order_by(Report.created_at.desc())
                    .limit(1)
                )
            else:
                result = await db.execute(
                    select(Report)
                    .where(
                        Report.user_id == user_id,
                        Report.report_date == today,
                        Report.type == ReportType.SOLO,
                    )
                    .order_by(Report.created_at.desc())
                    .limit(1)
                )
            if result.scalars().first():
                return

            report = Report(
                pair_id=pair_id,
                user_id=user_id,
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
