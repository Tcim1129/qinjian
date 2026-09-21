"""社群轻运营：通知中心 + 基于历史状态的明日微建议。"""

import asyncio
import json
import logging
import re
import uuid
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import desc, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.reporter import PAIR_TYPE_MAP
from app.api.deps import get_current_user, validate_pair_access
from app.core.config import settings
from app.core.database import get_db
from app.core.time import current_local_date
from app.models import (
    Checkin,
    Pair,
    PairStatus,
    RelationshipProfileSnapshot,
    Report,
    ReportStatus,
    User,
    UserNotification,
)
from app.ai import chat_completion
from app.services.relationship_intelligence import refresh_profile_snapshot
from app.services.request_cooldown_store import consume_request_cooldown
from app.services.test_accounts import is_relaxed_test_account

router = APIRouter(prefix="/community", tags=["社群"])
logger = logging.getLogger(__name__)
TIP_GENERATE_WINDOW_SECONDS = 60
TIP_GENERATE_MAX_ATTEMPTS = 2
TIP_AI_TIMEOUT_SECONDS = 6

# 内置兜底建议：标题维持在小卡片可读范围内。
BUILT_IN_TIPS = {
    "solo": [
        {"title": "先做一件小事", "description": "如果最近有点累，明天先完成最轻的一步。"},
        {"title": "留一句真实感受", "description": "不急着解释全局，先写下一句最真实的感受。"},
    ],
    "couple": [
        {"title": "先软一点开口", "description": "如果最近容易顶起来，明天先用更软的开场。"},
        {"title": "只聊眼前这件事", "description": "先别把旧账一起翻，明天只处理最卡的一点。"},
    ],
    "spouse": [
        {"title": "先排一件要事", "description": "事情多的时候，明天先只对齐最紧要的一件。"},
        {"title": "请求说具体点", "description": "比起情绪控诉，明天先提一个具体可执行请求。"},
    ],
    "bestfriend": [
        {"title": "先发一句近况", "description": "朋友有点疏时，明天先丢一句真实近况。"},
        {"title": "先问别先猜", "description": "如果最近联系少，明天先问一句近况再下判断。"},
    ],
    "friend": [
        {"title": "先发一句近况", "description": "普通朋友联系变少时，明天先发一句轻松近况。"},
        {"title": "先问别先猜", "description": "如果最近有点疏，明天先问一句近况再判断。"},
    ],
    "parent": [
        {"title": "先对齐口径", "description": "涉及家庭安排时，明天先私下把说法对齐。"},
        {"title": "轮班写清楚", "description": "育儿和照顾别靠猜，明天先把分工写明。"},
    ],
}

PAIR_TYPE_LABELS = {
    **PAIR_TYPE_MAP,
    "friend": "朋友",
    "solo": "自己",
}

FOCUS_FALLBACKS = {
    "practice_softened_startup": {
        "title": "先软一点开口",
        "description": "最近表达刺激偏高，明天先换一个更柔和的开场。",
    },
    "message_rehearsal_before_sending": {
        "title": "先打草稿再发",
        "description": "如果最近容易误伤，明天先把话写进草稿里看一遍。",
    },
    "align_narratives_before_solving": {
        "title": "先对齐再解决",
        "description": "最近理解偏差偏多，明天先确认彼此在说哪件事。",
    },
    "increase_shared_checkins": {
        "title": "先补一次联系",
        "description": "最近连接偏少，明天先把联系重新接回来。",
    },
    "create_deep_conversation_window": {
        "title": "留十分钟深聊",
        "description": "如果最近一直浅聊，明天先留一个短一点的深聊窗口。",
    },
    "reduce_task_friction": {
        "title": "先把任务减半",
        "description": "如果最近总完不成，明天先把动作缩到更容易做到。",
    },
    "conflict_repair": {
        "title": "先降温再靠近",
        "description": "最近风险偏高，明天先做降温动作，不急着一次谈完。",
    },
    "distance_compensation": {
        "title": "约一次同步陪伴",
        "description": "异地联系偏稀，明天先补一次固定同步时段。",
    },
    "stabilize_self_rhythm": {
        "title": "先稳住自己节奏",
        "description": "如果最近状态起伏大，明天先照顾好自己的节奏。",
    },
    "practice_honest_reflection": {
        "title": "写一句真实感受",
        "description": "如果最近总憋着，明天先给自己留一句真实感受。",
    },
}


def _enum_value(value: Any, fallback: str = "") -> str:
    raw = getattr(value, "value", value)
    text = str(raw or "").strip()
    return text or fallback


def _compact_text(value: Any, limit: int = 40) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 1, 1)]}…"


def _compact_title(value: Any, limit: int = 15) -> str:
    text = re.sub(r"\s+", "", str(value or "")).strip()
    text = re.sub(r"[。！？!?，,；;：:]+$", "", text)
    if not text:
        return ""
    return text[:limit]


def _rate_to_percent(value: Any) -> str | None:
    try:
        if value in (None, ""):
            return None
        return f"{round(float(value) * 100)}%"
    except (TypeError, ValueError):
        return None


def _first_text(*values: Any) -> str | None:
    for value in values:
        text = _compact_text(value, limit=60)
        if text:
            return text
    return None


def _report_hint(content: Any) -> str | None:
    if not isinstance(content, dict):
        return None
    intervention = content.get("intervention") or {}
    action_plan = content.get("action_plan") or []
    return _first_text(
        content.get("change_summary"),
        content.get("suggestion"),
        content.get("relationship_note"),
        content.get("self_care_tip"),
        content.get("insight"),
        intervention.get("title"),
        intervention.get("description"),
        action_plan[0] if isinstance(action_plan, list) and action_plan else None,
    )


def _tip_payload(title: str, description: str, source: str) -> dict[str, str]:
    safe_title = _compact_title(title) or "先做一个小动作"
    safe_description = _compact_text(description, limit=40) or "明天先做一步最轻的小动作。"
    return {
        "title": safe_title,
        "description": safe_description,
        "content": safe_description,
        "source": source,
    }


def _focus_items(snapshot: RelationshipProfileSnapshot | None) -> list[str]:
    raw = getattr(snapshot, "suggested_focus", None) or {}
    if isinstance(raw, dict):
        items = raw.get("items") or []
    elif isinstance(raw, list):
        items = raw
    else:
        items = []
    return [str(item).strip() for item in items if str(item or "").strip()]


def _fallback_tip(
    *,
    pair_type: str,
    focus_items: list[str] | None = None,
    risk_summary: dict[str, Any] | None = None,
) -> dict[str, str]:
    for focus in focus_items or []:
        candidate = FOCUS_FALLBACKS.get(str(focus))
        if candidate:
            return _tip_payload(candidate["title"], candidate["description"], "rule")

    current_level = str((risk_summary or {}).get("current_level") or "none")
    trend = str((risk_summary or {}).get("trend") or "stable")
    if current_level in {"moderate", "severe"}:
        return _tip_payload("先降温再靠近", "最近风险偏高，明天先做低刺激的小动作。", "rule")
    if trend == "watch":
        return _tip_payload("先补一次联系", "最近状态需要留意，明天先把联系轻轻接回来。", "rule")

    defaults = BUILT_IN_TIPS.get(pair_type) or BUILT_IN_TIPS["couple"]
    primary = defaults[0]
    return _tip_payload(primary["title"], primary["description"], "built_in")


def _parse_tip_response(text: str, fallback: dict[str, str]) -> dict[str, str]:
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(cleaned)
    except Exception:
        return fallback

    return _tip_payload(
        parsed.get("title") or parsed.get("tip") or fallback["title"],
        parsed.get("description") or parsed.get("content") or parsed.get("reason") or fallback["description"],
        "ai",
    )


async def _resolve_tip_pair(
    db: AsyncSession,
    *,
    user: User,
    pair_id: str | None,
    pair_type: str,
) -> tuple[Pair | None, str]:
    if pair_id:
        pair = await validate_pair_access(pair_id, user, db, require_active=True)
        return pair, _enum_value(pair.type, pair_type or "couple")

    normalized_type = str(pair_type or "solo").strip() or "solo"
    if normalized_type == "solo":
        return None, "solo"

    result = await db.execute(
        select(Pair)
        .where(
            Pair.status == PairStatus.ACTIVE,
            Pair.type == normalized_type,
            or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
        )
        .order_by(desc(Pair.created_at))
        .limit(1)
    )
    pair = result.scalar_one_or_none()
    return pair, normalized_type


async def _load_snapshot(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    window_days: int = 7,
    force_refresh: bool = False,
) -> RelationshipProfileSnapshot | None:
    snapshot_date = current_local_date()
    if not force_refresh:
        result = await db.execute(
            select(RelationshipProfileSnapshot)
            .where(
                RelationshipProfileSnapshot.pair_id == pair_id,
                RelationshipProfileSnapshot.user_id == user_id,
                RelationshipProfileSnapshot.window_days == window_days,
                RelationshipProfileSnapshot.snapshot_date == snapshot_date,
                RelationshipProfileSnapshot.version == "v1",
            )
            .order_by(desc(RelationshipProfileSnapshot.created_at))
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()
        if snapshot:
            return snapshot

    if pair_id:
        return await refresh_profile_snapshot(
            db,
            pair_id=pair_id,
            window_days=window_days,
            snapshot_date=snapshot_date,
        )
    if user_id:
        return await refresh_profile_snapshot(
            db,
            user_id=user_id,
            window_days=window_days,
            snapshot_date=snapshot_date,
        )
    return None


async def _recent_status_lines(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> list[str]:
    lines: list[str] = []

    checkin_stmt = select(Checkin)
    report_stmt = select(Report).where(Report.status == ReportStatus.COMPLETED)

    if pair_id:
        checkin_stmt = checkin_stmt.where(Checkin.pair_id == pair_id)
        report_stmt = report_stmt.where(Report.pair_id == pair_id)
    elif user_id:
        checkin_stmt = checkin_stmt.where(
            Checkin.user_id == user_id,
            Checkin.pair_id.is_(None),
        )
        report_stmt = report_stmt.where(
            Report.user_id == user_id,
            Report.pair_id.is_(None),
        )
    else:
        return lines

    checkins_result = await db.execute(
        checkin_stmt.order_by(desc(Checkin.checkin_date), desc(Checkin.created_at)).limit(3)
    )
    for checkin in checkins_result.scalars().all():
        parts = []
        if checkin.mood_score is not None:
            parts.append(f"心情{checkin.mood_score}/10")
        if checkin.interaction_freq is not None:
            parts.append(f"互动{checkin.interaction_freq}/10")
        if checkin.deep_conversation is not None:
            parts.append("有深聊" if checkin.deep_conversation else "没深聊")
        if checkin.task_completed is not None:
            parts.append("已完成约定" if checkin.task_completed else "未完成约定")
        detail = "，".join(parts) if parts else "有记录"
        lines.append(f"打卡 {checkin.checkin_date.isoformat()}: {detail}")

    reports_result = await db.execute(
        report_stmt.order_by(desc(Report.report_date), desc(Report.created_at)).limit(2)
    )
    for report in reports_result.scalars().all():
        score = (
            f"健康分{round(float(report.health_score))}"
            if report.health_score is not None
            else "有报告"
        )
        hint = _report_hint(report.content)
        lines.append(
            f"报告 {report.report_date.isoformat()}: {score}"
            + (f"，{hint}" if hint else "")
        )

    return lines[:5]


def _ai_prompt(
    *,
    pair_type: str,
    target_date: date,
    snapshot: RelationshipProfileSnapshot | None,
    status_lines: list[str],
) -> str:
    metrics = (snapshot.metrics_json or {}) if snapshot else {}
    risk_summary = (snapshot.risk_summary or {}) if snapshot else {}
    attachment_summary = (snapshot.attachment_summary or {}) if snapshot else {}
    focus_codes = _focus_items(snapshot)
    focus_labels = [
        FOCUS_FALLBACKS.get(code, {}).get("title", code)
        for code in focus_codes
    ]

    lines = [
        f"关系类型：{PAIR_TYPE_LABELS.get(pair_type, '关系')}",
        f"建议日期：{target_date.isoformat()}",
        f"当前风险等级：{risk_summary.get('current_level') or 'none'}",
        f"当前趋势：{risk_summary.get('trend') or 'stable'}",
    ]

    report_health_avg = metrics.get("report_health_avg")
    if report_health_avg is not None:
        lines.append(f"最近健康分均值：{report_health_avg}")

    mood_avg = metrics.get("mood_avg")
    if mood_avg is not None:
        lines.append(f"最近心情均值：{mood_avg}/10")

    deep_rate = _rate_to_percent(metrics.get("deep_conversation_rate"))
    if deep_rate:
        lines.append(f"深聊占比：{deep_rate}")

    overlap_rate = _rate_to_percent(metrics.get("interaction_overlap_rate"))
    if overlap_rate:
        lines.append(f"共同互动覆盖：{overlap_rate}")

    task_rate = _rate_to_percent(metrics.get("task_completion_rate"))
    if task_rate:
        lines.append(f"任务完成率：{task_rate}")

    high_risk_count = metrics.get("message_simulation_high_risk_count")
    if high_risk_count not in (None, ""):
        lines.append(f"高风险消息预演次数：{high_risk_count}")

    last_goal = _compact_text(metrics.get("last_simulation_goal"), limit=28)
    if last_goal:
        lines.append(f"最近一次沟通目标：{last_goal}")

    last_bridge = _compact_text(metrics.get("last_alignment_bridge"), limit=28)
    if last_bridge:
        lines.append(f"最近一次桥接动作：{last_bridge}")

    if attachment_summary.get("is_long_distance"):
        lines.append("当前关系特征：异地")

    attachment_a = _compact_text(attachment_summary.get("attachment_a"), limit=20)
    if attachment_a and attachment_a != "unknown":
        lines.append(f"依恋线索：{attachment_a}")

    if focus_labels:
        lines.append("系统聚焦：" + "、".join(focus_labels[:3]))

    if status_lines:
        lines.append("最近状态：")
        lines.extend(f"- {line}" for line in status_lines)
    else:
        lines.append("最近状态：暂无足够历史状态，只能给稳妥的小动作建议。")

    return "\n".join(
        [
            "请基于以下状态，为用户生成 1 条“明天当天的微安排建议”。",
            *lines,
            "",
            "输出要求：",
            '1. 只输出 JSON：{"title":"...","description":"..."}',
            "2. title 必须 15 个字以内，像卡片上的一句小建议。",
            "3. title 直接描述明天当天要做的最小动作，不要鸡汤，不要评判。",
            "4. description 40 字以内，温和说明为什么建议这一步。",
            "5. 只能给一步，不要多步计划，不要使用“必须、立刻、赶紧”。",
            "6. 如果信息不足，也要给一条最稳妥的小动作建议。",
        ]
    )


async def _generate_personalized_tip(
    db: AsyncSession,
    *,
    user: User,
    pair_type: str,
    pair: Pair | None = None,
    varied: bool = False,
) -> dict[str, str]:
    snapshot = await _load_snapshot(
        db,
        pair_id=pair.id if pair else None,
        user_id=None if pair else user.id,
        force_refresh=True,
    )
    risk_summary = (snapshot.risk_summary or {}) if snapshot else {}
    focus_items = _focus_items(snapshot)
    fallback = _fallback_tip(
        pair_type=pair_type,
        focus_items=focus_items,
        risk_summary=risk_summary,
    )
    status_lines = await _recent_status_lines(
        db,
        pair_id=pair.id if pair else None,
        user_id=None if pair else user.id,
    )

    messages = [
        {
            "role": "system",
            "content": "你是亲健的每日关系安排助手。你只给一条轻量、温和、可执行的明日微建议。",
        },
        {
            "role": "user",
            "content": _ai_prompt(
                pair_type=pair_type,
                target_date=current_local_date() + timedelta(days=1),
                snapshot=snapshot,
                status_lines=status_lines,
            ),
        },
    ]
    try:
        result = await asyncio.wait_for(
            chat_completion(
                settings.AI_TEXT_MODEL,
                messages,
                temperature=0.75 if varied else 0.35,
            ),
            timeout=TIP_AI_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("personalized community tip timed out, using rule fallback")
        return fallback
    except Exception:
        logger.exception("failed to generate personalized community tip")
        return fallback

    return _parse_tip_response(result, fallback)


@router.get("/tips")
async def get_tips(
    pair_type: str = "couple",
    pair_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取基于历史状态整理的明日微建议。"""
    pair, effective_pair_type = await _resolve_tip_pair(
        db,
        user=user,
        pair_id=pair_id,
        pair_type=pair_type,
    )

    primary_tip = await _generate_personalized_tip(
        db,
        user=user,
        pair_type=effective_pair_type,
        pair=pair,
        varied=False,
    )

    tips: list[dict[str, str]] = [primary_tip]
    seen_titles = {primary_tip["title"]}
    for tip in BUILT_IN_TIPS.get(effective_pair_type, BUILT_IN_TIPS["couple"]):
        normalized = _tip_payload(tip["title"], tip["description"], "built_in")
        if normalized["title"] in seen_titles:
            continue
        seen_titles.add(normalized["title"])
        tips.append(normalized)

    return {
        "pair_type": effective_pair_type,
        "generated_for_date": (current_local_date() + timedelta(days=1)).isoformat(),
        "tips": tips,
    }


@router.post("/tips/generate")
async def generate_ai_tip(
    pair_type: str = "couple",
    pair_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """按当前历史状态生成另一条明日微建议。"""
    pair, effective_pair_type = await _resolve_tip_pair(
        db,
        user=user,
        pair_id=pair_id,
        pair_type=pair_type,
    )
    await consume_request_cooldown(
        bucket="community-tip-generate",
        scope_key=f"{user.id}:{pair.id if pair else 'solo'}",
        window_seconds=TIP_GENERATE_WINDOW_SECONDS,
        max_attempts=TIP_GENERATE_MAX_ATTEMPTS,
        limit_message="建议生成得有点频繁了",
        bypass=is_relaxed_test_account(user),
    )
    tip = await _generate_personalized_tip(
        db,
        user=user,
        pair_type=effective_pair_type,
        pair=pair,
        varied=True,
    )
    return {
        "generated_for_date": (current_local_date() + timedelta(days=1)).isoformat(),
        "tip": tip,
    }


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
            "target_path": n.target_path,
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
