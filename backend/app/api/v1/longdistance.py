"""异地关系专属模块 API"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.time import current_local_date
from app.api.deps import get_current_user, validate_pair_access
from app.models import User, Pair, PairStatus, LongDistanceActivity, Checkin, Report
from sqlalchemy import func

router = APIRouter(prefix="/longdistance", tags=["异地关系"])


@router.post("/activities")
async def create_activity(
    pair_id: str,
    activity_type: str,  # movie / meal / chat / gift / exercise
    title: str = "",
    scheduled_at: str = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建异地互动活动"""
    await validate_pair_access(pair_id, user, db, require_active=True)

    ACTIVITY_TITLES = {
        "movie": "一起看电影 🎬",
        "meal": "云打卡吃饭 🍜",
        "chat": "视频深度聊天 📞",
        "gift": "给对方寄礼物 🎁",
        "exercise": "同步运动打卡 🏃",
    }

    activity = LongDistanceActivity(
        pair_id=pair_id,
        type=activity_type,
        title=title or ACTIVITY_TITLES.get(activity_type, "异地互动"),
        created_by=str(user.id),
    )
    db.add(activity)
    await db.flush()

    return {
        "id": str(activity.id),
        "type": activity.type,
        "title": activity.title,
        "status": activity.status,
        "message": "活动已创建，邀请对方一起参与！",
    }


@router.get("/activities/{pair_id}")
async def get_activities(
    pair_id: str,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取异地互动活动列表"""
    await validate_pair_access(pair_id, user, db, require_active=True)

    result = await db.execute(
        select(LongDistanceActivity)
        .where(LongDistanceActivity.pair_id == pair_id)
        .order_by(desc(LongDistanceActivity.created_at))
        .limit(limit)
    )
    activities = result.scalars().all()

    return [
        {
            "id": str(a.id),
            "type": a.type,
            "title": a.title,
            "status": a.status,
            "created_by": str(a.created_by),
            "created_at": str(a.created_at),
        }
        for a in activities
    ]


@router.post("/activities/{activity_id}/complete")
async def complete_activity(
    activity_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记活动完成"""
    activity = await db.get(LongDistanceActivity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")

    await validate_pair_access(str(activity.pair_id), user, db, require_active=True)

    activity.status = "completed"
    activity.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    return {"message": "活动完成 🎉", "status": "completed"}


@router.get("/health-index/{pair_id}")
async def get_health_index(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """异地关系健康指数（聚焦沟通及时性和情感表达频率）"""
    pair = await validate_pair_access(pair_id, user, db, require_active=True)

    # 近14天打卡数据
    from datetime import timedelta

    cutoff = current_local_date() - timedelta(days=14)
    result = await db.execute(
        select(Checkin)
        .where(Checkin.pair_id == pair_id, Checkin.checkin_date >= cutoff)
    )
    checkins = result.scalars().all()

    total_days = 14
    checkin_days_a = len(set(c.checkin_date for c in checkins if str(c.user_id) == str(pair.user_a_id)))
    checkin_days_b = len(set(c.checkin_date for c in checkins if str(c.user_id) == str(pair.user_b_id)))
    deep_conv_count = sum(1 for c in checkins if c.deep_conversation)

    # 沟通及时性 = 双方打卡重合天数比例
    dates_a = set(c.checkin_date for c in checkins if str(c.user_id) == str(pair.user_a_id))
    dates_b = set(c.checkin_date for c in checkins if str(c.user_id) == str(pair.user_b_id))
    overlap_days = len(dates_a & dates_b)

    comm_timeliness = round(overlap_days / total_days * 100, 1) if total_days else 0
    expression_freq = round((checkin_days_a + checkin_days_b) / (total_days * 2) * 100, 1)
    deep_conv_rate = round(deep_conv_count / max(len(checkins), 1) * 100, 1)

    # 综合健康指数
    health_index = round(comm_timeliness * 0.4 + expression_freq * 0.3 + deep_conv_rate * 0.3, 1)

    return {
        "pair_id": pair_id,
        "health_index": health_index,
        "communication_timeliness": comm_timeliness,
        "expression_frequency": expression_freq,
        "deep_conversation_rate": deep_conv_rate,
        "period_days": total_days,
        "checkin_days_a": checkin_days_a,
        "checkin_days_b": checkin_days_b,
        "overlap_days": overlap_days,
    }
