"""社群轻运营 MVP：通知中心 + AI 经营技巧推送"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, Pair, PairStatus, CommunityTip, UserNotification
from app.ai import chat_completion
from app.core.config import settings

router = APIRouter(prefix="/community", tags=["社群"])
logger = logging.getLogger(__name__)

# 内置关系经营技巧库（按类型分类）
BUILT_IN_TIPS = {
    "couple": [
        {"title": "5:1法则", "content": "戈特曼研究表明，稳定的关系中积极互动与消极互动的比例至少为5:1。今天试着给对方5个真诚的赞美 💕"},
        {"title": "爱的五种语言", "content": "每个人感受爱的方式不同：肯定的话语、服务的行动、接受礼物、精心的时刻、身体接触。了解对方最需要哪一种，比盲目付出更有效 ❤️"},
        {"title": "情绪缓冲", "content": "生气时先深呼吸20秒再说话。研究表明，情绪高峰期做的决定80%会后悔。给自己一个缓冲区 🧘"},
    ],
    "spouse": [
        {"title": "家务分工", "content": "公平的家务分工是婚姻满意度的重要预测因子。试着每周一起制定分工计划，而不是默默期待对方主动 📋"},
        {"title": "约会夜", "content": "即使结婚多年，定期的二人约会依然重要。每周留出至少2小时的专属时间，关掉手机，认真聊天 🌙"},
        {"title": "感恩记录", "content": "每天睡前告诉对方一件你今天感激TA的事。持续21天，你会发现关系明显改善 📝"},
    ],
    "bestfriend": [
        {"title": "主动联系", "content": "友谊需要主动维护。如果超过一周没联系，现在就给好朋友发一条消息吧 💬"},
        {"title": "深度对话", "content": "比起表面的寒暄，偶尔一次深度、真诚的对话更能加深友谊。试试分享最近的困惑或感悟 🤝"},
    ],
    "parent": [
        {"title": "统一战线", "content": "在孩子面前保持教育观念一致非常重要。有分歧时，先私下沟通达成共识 👨‍👩‍👧"},
        {"title": "育儿轮班", "content": "设定明确的育儿轮班时间，确保双方都有休息和自我空间。疲惫的父母无法给孩子最好的陪伴 🌟"},
    ],
}


@router.get("/tips")
async def get_tips(
    pair_type: str = "couple",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取匹配关系类型的经营技巧"""
    # 先查数据库中的 AI 生成技巧
    result = await db.execute(
        select(CommunityTip)
        .where(CommunityTip.target_pair_type == pair_type)
        .order_by(desc(CommunityTip.created_at))
        .limit(5)
    )
    db_tips = result.scalars().all()

    tips = [
        {"id": str(t.id), "title": t.title, "content": t.content, "source": "ai"}
        for t in db_tips
    ]

    # 补充内置技巧
    built_in = BUILT_IN_TIPS.get(pair_type, BUILT_IN_TIPS["couple"])
    for tip in built_in:
        tips.append({"title": tip["title"], "content": tip["content"], "source": "built_in"})

    return {"pair_type": pair_type, "tips": tips}


@router.post("/tips/generate")
async def generate_ai_tip(
    pair_type: str = "couple",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 生成一条新的关系经营技巧"""
    from app.ai.reporter import PAIR_TYPE_MAP
    type_label = PAIR_TYPE_MAP.get(pair_type, "伴侣")

    messages = [
        {"role": "system", "content": "你是亲密关系经营专家。请生成一条简短、实用的关系经营技巧。"},
        {"role": "user", "content": f"为一对{type_label}生成一条关系经营小贴士。要求：标题10字内，内容100字内，具体可执行，语气温暖。JSON格式：{{\"title\": \"标题\", \"content\": \"内容\"}}"},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.9)

    import json
    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(cleaned)
    except Exception:
        parsed = {"title": "沟通小技巧", "content": "今天试着用'我觉得...'而不是'你总是...'来表达感受 💬"}

    # 保存到数据库
    tip = CommunityTip(
        target_pair_type=pair_type,
        title=parsed.get("title", "关系小贴士"),
        content=parsed.get("content", ""),
        ai_generated=True,
    )
    db.add(tip)
    await db.flush()

    return {"tip": {"id": str(tip.id), "title": tip.title, "content": tip.content}}


@router.get("/notifications")
async def get_notifications(
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取通知列表"""
    result = await db.execute(
        select(UserNotification)
        .where(UserNotification.user_id == user.id)
        .order_by(desc(UserNotification.created_at))
        .limit(limit)
    )
    notifications = result.scalars().all()

    return [
        {
            "id": str(n.id),
            "type": n.type,
            "content": n.content,
            "is_read": n.is_read,
            "created_at": str(n.created_at),
        }
        for n in notifications
    ]


@router.post("/notifications/read-all")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记所有通知为已读"""
    await db.execute(
        update(UserNotification)
        .where(UserNotification.user_id == user.id, UserNotification.is_read == False)
        .values(is_read=True)
    )
    return {"message": "全部已读"}
