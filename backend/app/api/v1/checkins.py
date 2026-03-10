"""打卡系统接口（Phase 3 增强：支持非对称打卡 + 个人情感日记）"""

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

router = APIRouter(prefix="/checkins", tags=["打卡"])


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

    return checkin


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
    except Exception as e:
        print(f"情感分析失败: {e}")


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
                select(Report).where(
                    Report.pair_id == pair_id,
                    Report.report_date == today,
                    Report.type == ReportType.DAILY,
                )
            )
            if result.scalar_one_or_none():
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
    except Exception as e:
        print(f"自动生成日报失败: {e}")


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
                    select(Report).where(
                        Report.pair_id == pair_id,
                        Report.report_date == today,
                        Report.type == ReportType.SOLO,
                    )
                )
            else:
                result = await db.execute(
                    select(Report).where(
                        Report.user_id == user_id,
                        Report.report_date == today,
                        Report.type == ReportType.SOLO,
                    )
                )
            if result.scalar_one_or_none():
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
    except Exception as e:
        print(f"自动生成个人日记失败: {e}")
