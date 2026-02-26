"""打卡系统接口（Phase 2 增强版）"""
import asyncio
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, Pair, Checkin, Report, PairStatus, ReportType
from app.schemas import CheckinRequest, CheckinResponse
from app.ai import analyze_sentiment
from app.ai.reporter import generate_daily_report

router = APIRouter(prefix="/checkins", tags=["打卡"])


@router.post("/", response_model=CheckinResponse)
async def create_checkin(req: CheckinRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """提交每日打卡（含自动AI情感分析 + 双方完成检测）"""
    # 验证配对存在且用户属于该配对
    result = await db.execute(select(Pair).where(Pair.id == req.pair_id, Pair.status == PairStatus.ACTIVE))
    pair = result.scalar_one_or_none()
    if not pair or (pair.user_a_id != user.id and pair.user_b_id != user.id):
        raise HTTPException(status_code=403, detail="你不属于该配对")

    # 检查今日是否已打卡
    today = date.today()
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
        pair_id=req.pair_id,
        user_id=user.id,
        content=req.content,
        image_url=req.image_url,
        voice_url=req.voice_url,
        mood_tags={"tags": req.mood_tags} if req.mood_tags else None,
        checkin_date=today,
    )
    db.add(checkin)
    await db.flush()

    # 异步执行 AI 情感分析（不阻塞响应）
    asyncio.create_task(_run_sentiment_analysis(str(checkin.id), req.content))

    # 检查对方是否也打卡完毕 → 自动生成日报
    partner_result = await db.execute(
        select(Checkin).where(
            Checkin.pair_id == req.pair_id,
            Checkin.user_id != user.id,
            Checkin.checkin_date == today,
        )
    )
    partner_checkin = partner_result.scalar_one_or_none()

    if partner_checkin:
        # 双方都完成 → 自动生成日报（后台不阻塞）
        asyncio.create_task(_auto_generate_daily(
            pair_id=str(req.pair_id),
            pair_type=pair.type.value,
            checkin_a_content=checkin.content if user.id == pair.user_a_id else partner_checkin.content,
            checkin_b_content=partner_checkin.content if user.id == pair.user_a_id else checkin.content,
        ))

    return checkin


@router.get("/today", response_model=dict)
async def get_today_status(pair_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """查询今日打卡状态"""
    today = date.today()
    result = await db.execute(
        select(Checkin).where(Checkin.pair_id == pair_id, Checkin.checkin_date == today)
    )
    checkins = result.scalars().all()

    my_done = any(c.user_id == user.id for c in checkins)
    partner_done = any(c.user_id != user.id for c in checkins)
    both_done = my_done and partner_done

    # 检查是否已有今日报告
    report_result = await db.execute(
        select(Report).where(
            Report.pair_id == pair_id,
            Report.report_date == today,
            Report.type == ReportType.DAILY,
        )
    )
    has_report = report_result.scalar_one_or_none() is not None

    return {
        "date": str(today),
        "my_done": my_done,
        "partner_done": partner_done,
        "both_done": both_done,
        "has_report": has_report,
    }


@router.get("/history", response_model=list[CheckinResponse])
async def get_checkin_history(
    pair_id: str, limit: int = 14,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取打卡历史（隐私保护：仅返回自己的原始内容）"""
    result = await db.execute(
        select(Checkin)
        .where(Checkin.pair_id == pair_id, Checkin.user_id == user.id)
        .order_by(Checkin.checkin_date.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/streak", response_model=dict)
async def get_checkin_streak(pair_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取连续打卡天数"""
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
        # 这里简化处理，生产环境应该用独立的数据库会话
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


async def _auto_generate_daily(pair_id: str, pair_type: str, checkin_a_content: str, checkin_b_content: str):
    """后台自动生成每日报告"""
    try:
        from app.core.database import async_session
        async with async_session() as db:
            # 检查是否已有报告
            today = date.today()
            result = await db.execute(
                select(Report).where(Report.pair_id == pair_id, Report.report_date == today, Report.type == ReportType.DAILY)
            )
            if result.scalar_one_or_none():
                return  # 已有报告

            report_content = await generate_daily_report(pair_type, checkin_a_content, checkin_b_content)
            report = Report(
                pair_id=pair_id,
                type=ReportType.DAILY,
                content=report_content,
                health_score=report_content.get("health_score"),
                report_date=today,
            )
            db.add(report)
            await db.commit()
    except Exception as e:
        print(f"自动生成日报失败: {e}")
