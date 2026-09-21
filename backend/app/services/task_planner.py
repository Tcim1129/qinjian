"""Task planner settings, AI generation, and reminder helpers."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from collections import defaultdict
from contextlib import suppress
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import delete, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.core.time import current_local_date, current_local_datetime
from app.models import (
    Checkin,
    Pair,
    PairStatus,
    RelationshipEvent,
    RelationshipProfileSnapshot,
    RelationshipTask,
    Report,
    ReportStatus,
    TaskStatus,
    User,
    UserNotification,
)
from app.services.task_adaptation import (
    build_daily_pack_label,
    build_daily_task_note,
    clamp_daily_note_length,
)

import os
import sys

logger = logging.getLogger(__name__)

TASK_PLANNER_AI_TIMEOUT_SECONDS = float(os.getenv("TASK_PLANNER_AI_TIMEOUT_SECONDS", "8.0"))
TASK_PLANNER_DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_TASK_PLANNER_DEFAULTS = {
    "daily_ai_task_count": 5,
    "reminder_enabled": True,
    "reminder_time": "21:00",
    "reminder_timezone": TASK_PLANNER_DEFAULT_TIMEZONE,
}
MIN_DAILY_AI_TASK_COUNT = 3
MAX_DAILY_AI_TASK_COUNT = 8
MAX_MANUAL_TASKS_PER_DATE = 10
VALID_TASK_IMPORTANCE_LEVELS = {"low", "medium", "high"}
TASK_IMPORTANCE_RANK = {"high": 0, "medium": 1, "low": 2}
TASK_REMINDER_NOTIFICATION_TYPE = "task_plan_reminder"
VALID_TASK_CATEGORIES = {
    "communication",
    "repair",
    "connection",
    "activity",
    "reflection",
}
PAIR_TYPE_LABELS = {
    "couple": "情侣",
    "friend": "朋友",
    "spouse": "伴侣",
    "bestfriend": "挚友",
    "parent": "育儿搭档",
}


class TaskPlannerError(RuntimeError):
    """Raised when the planner cannot safely produce AI output."""


def _normalize_time_string(value: object, *, fallback: str) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
        return text
    return fallback


def _normalize_timezone_name(value: object, *, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    try:
        ZoneInfo(text)
    except ZoneInfoNotFoundError:
        return fallback
    return text


def _normalize_task_count(value: object, *, fallback: int) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        numeric = fallback
    return max(MIN_DAILY_AI_TASK_COUNT, min(MAX_DAILY_AI_TASK_COUNT, numeric))


def normalize_task_planner_defaults(raw: dict | None) -> dict[str, object]:
    payload = dict(DEFAULT_TASK_PLANNER_DEFAULTS)
    if not isinstance(raw, dict):
        return payload

    payload["daily_ai_task_count"] = _normalize_task_count(
        raw.get("daily_ai_task_count"),
        fallback=int(DEFAULT_TASK_PLANNER_DEFAULTS["daily_ai_task_count"]),
    )
    if isinstance(raw.get("reminder_enabled"), bool):
        payload["reminder_enabled"] = raw["reminder_enabled"]
    payload["reminder_time"] = _normalize_time_string(
        raw.get("reminder_time"),
        fallback=str(DEFAULT_TASK_PLANNER_DEFAULTS["reminder_time"]),
    )
    payload["reminder_timezone"] = _normalize_timezone_name(
        raw.get("reminder_timezone"),
        fallback=str(DEFAULT_TASK_PLANNER_DEFAULTS["reminder_timezone"]),
    )
    return payload


def normalize_task_planner_overrides(raw: dict | None) -> dict[str, object]:
    if not isinstance(raw, dict):
        return {}

    payload: dict[str, object] = {}
    if "daily_ai_task_count" in raw:
        value = raw.get("daily_ai_task_count")
        payload["daily_ai_task_count"] = (
            None
            if value in (None, "")
            else _normalize_task_count(
                value,
                fallback=int(DEFAULT_TASK_PLANNER_DEFAULTS["daily_ai_task_count"]),
            )
        )
    if "reminder_enabled" in raw:
        value = raw.get("reminder_enabled")
        payload["reminder_enabled"] = value if isinstance(value, bool) else None
    if "reminder_time" in raw:
        value = raw.get("reminder_time")
        payload["reminder_time"] = (
            None
            if value in (None, "")
            else _normalize_time_string(
                value,
                fallback=str(DEFAULT_TASK_PLANNER_DEFAULTS["reminder_time"]),
            )
        )
    if "reminder_timezone" in raw:
        value = raw.get("reminder_timezone")
        payload["reminder_timezone"] = (
            None
            if value in (None, "")
            else _normalize_timezone_name(
                value,
                fallback=str(DEFAULT_TASK_PLANNER_DEFAULTS["reminder_timezone"]),
            )
        )
    return payload


def resolve_user_task_planner_defaults(product_prefs: dict | None) -> dict[str, object]:
    if not isinstance(product_prefs, dict):
        return dict(DEFAULT_TASK_PLANNER_DEFAULTS)
    return normalize_task_planner_defaults(product_prefs.get("task_planner_defaults"))


def resolve_pair_task_planner_overrides(pair_settings: dict | None) -> dict[str, object]:
    cleaned: dict[str, object] = {}
    for key, value in normalize_task_planner_overrides(pair_settings).items():
        if value is not None:
            cleaned[key] = value
    return cleaned


def resolve_effective_task_planner_settings(
    product_prefs: dict | None,
    pair_settings: dict | None,
) -> dict[str, object]:
    defaults = resolve_user_task_planner_defaults(product_prefs)
    effective = dict(defaults)
    for key, value in resolve_pair_task_planner_overrides(pair_settings).items():
        effective[key] = value
    return effective


def merge_pair_task_planner_overrides(
    existing: dict | None,
    patch: dict[str, object],
) -> dict[str, object] | None:
    merged = resolve_pair_task_planner_overrides(existing)
    for key, value in patch.items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return merged or None


def normalize_task_importance_level(value: object, *, fallback: str = "medium") -> str:
    raw_val = getattr(value, "value", value)
    normalized = str(raw_val or fallback).strip().lower() or fallback
    return normalized if normalized in VALID_TASK_IMPORTANCE_LEVELS else fallback


def sort_tasks_by_status_and_importance(tasks: list[RelationshipTask]) -> list[RelationshipTask]:
    return sorted(
        tasks,
        key=lambda task: (
            1 if getattr(task, "status", None) == TaskStatus.COMPLETED else 0,
            TASK_IMPORTANCE_RANK.get(
                normalize_task_importance_level(
                    getattr(task, "importance_level", "medium")
                ),
                TASK_IMPORTANCE_RANK["medium"],
            ),
            1 if getattr(task, "parent_task_id", None) else 0,
            getattr(task, "created_at", None) or datetime.min,
        ),
    )


def resolve_date_scope(for_date: date, *, today: date | None = None) -> str:
    local_today = today or current_local_date()
    if for_date == local_today:
        return "today"
    if for_date == local_today + timedelta(days=1):
        return "tomorrow"
    return "custom"


def build_encouragement_copy(*, completed_count: int, remaining_count: int) -> str:
    if completed_count <= 0 and remaining_count <= 0:
        return "今天先从最轻的一步开始，哪怕只推进一点也算数。"
    if remaining_count <= 0:
        return "今天这轮已经完成了，记得给自己一个肯定。"
    if completed_count <= 0:
        return (
            "还没开始也没关系，先做最轻的一步，把节奏慢慢接上。"
            if remaining_count >= 2
            else "先把眼前这一件做完，今天就已经有推进了。"
        )
    if completed_count < remaining_count:
        return (
            f"已经完成 {completed_count} 条了，后面还剩 {remaining_count} 条，继续按现在这个节奏就好。"
        )
    return (
        f"已经推进了 {completed_count} 条，剩下 {remaining_count} 条，今天很有机会顺顺地收尾。"
    )


def build_planning_note(
    *,
    strategy: dict | None,
    effective_settings: dict[str, object],
) -> str:
    count = int(effective_settings.get("daily_ai_task_count") or 5)
    if strategy and strategy.get("support_message"):
        return str(strategy["support_message"]).strip()
    return f"明天先按这 {count} 条排着走，不合适的可以单独换掉。"


def _datetime_in_timezone(now: datetime | None, timezone_name: object) -> datetime:
    normalized_name = _normalize_timezone_name(
        timezone_name,
        fallback=TASK_PLANNER_DEFAULT_TIMEZONE,
    )
    target_timezone = ZoneInfo(normalized_name)
    if now is None:
        return datetime.now(target_timezone)
    normalized_now = now
    if normalized_now.tzinfo is None:
        normalized_now = normalized_now.replace(tzinfo=timezone.utc)
    return normalized_now.astimezone(target_timezone)


def _reminder_due_in_window(local_now: datetime, reminder_time: object) -> bool:
    reminder_text = _normalize_time_string(
        reminder_time,
        fallback=str(DEFAULT_TASK_PLANNER_DEFAULTS["reminder_time"]),
    )
    hour, minute = [int(part) for part in reminder_text.split(":", 1)]
    scheduled = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    diff_seconds = (local_now - scheduled).total_seconds()
    return 0 <= diff_seconds < 300


def _clean_json_block(text: str) -> str:
    cleaned = str(text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
    return cleaned.strip()


def _compact_task_title(value: object, *, fallback: str) -> str:
    text = re.sub(r"\s+", "", str(value or "")).strip()
    text = re.sub(r"[。！？!?；;：:,，]+$", "", text)
    if not text:
        return fallback
    return text[:18]


def _compact_task_description(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    return text[:120]


def _normalize_task_category(value: object, *, fallback: str = "activity") -> str:
    category = str(value or fallback).strip().lower() or fallback
    return category if category in VALID_TASK_CATEGORIES else fallback


def _normalize_generated_tasks(
    raw_tasks: Any,
    *,
    task_count: int,
) -> list[dict[str, str]]:
    if not isinstance(raw_tasks, list):
        raise TaskPlannerError("planner output missing tasks")

    normalized: list[dict[str, str]] = []
    seen_titles: set[str] = set()
    for index, item in enumerate(raw_tasks):
        if len(normalized) >= task_count:
            break
        if not isinstance(item, dict):
            continue
        title = _compact_task_title(item.get("title"), fallback=f"安排第{index + 1}步")
        title_key = title.casefold()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        normalized.append(
            {
                "title": title,
                "description": _compact_task_description(item.get("description")),
                "category": _normalize_task_category(item.get("category")),
                "target": "both",
            }
        )

    if len(normalized) != task_count:
        raise TaskPlannerError("planner output does not contain enough tasks")
    return normalized


def _parse_task_pack_response(
    text: str,
    *,
    task_count: int,
    strategy: dict | None,
    effective_settings: dict[str, object],
    date_scope: str,
) -> dict[str, object]:
    try:
        payload = json.loads(_clean_json_block(text))
    except Exception as exc:
        raise TaskPlannerError("planner output is not valid json") from exc

    tasks = _normalize_generated_tasks(payload.get("tasks"), task_count=task_count)
    generated_daily_note = str(payload.get("daily_note") or "").strip()
    if generated_daily_note:
        generated_daily_note = clamp_daily_note_length(generated_daily_note)
    generated_planning_note = str(payload.get("planning_note") or "").strip()
    if generated_planning_note:
        generated_planning_note = clamp_daily_note_length(generated_planning_note)
    generated_pack_label = str(payload.get("daily_pack_label") or "").strip()
    return {
        "tasks": tasks,
        "daily_note": generated_daily_note
        or build_daily_task_note(strategy or {}, randomize=True),
        "planning_note": generated_planning_note
        or build_planning_note(
            strategy=strategy,
            effective_settings=effective_settings,
        ),
        "daily_pack_label": generated_pack_label
        or build_daily_pack_label(strategy or {}),
        "raw": payload,
        "date_scope": date_scope,
    }


def _parse_refresh_response(text: str, *, fallback_title: str) -> dict[str, str]:
    try:
        payload = json.loads(_clean_json_block(text))
    except Exception as exc:
        raise TaskPlannerError("refresh output is not valid json") from exc

    title = _compact_task_title(payload.get("title"), fallback=fallback_title)
    description = _compact_task_description(payload.get("description"))
    category = _normalize_task_category(payload.get("category"))
    return {
        "title": title,
        "description": description,
        "category": category,
    }


async def _load_or_refresh_snapshot(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
) -> RelationshipProfileSnapshot | None:
    from app.services.relationship_intelligence import refresh_profile_snapshot

    result = await db.execute(
        select(RelationshipProfileSnapshot)
        .where(RelationshipProfileSnapshot.pair_id == pair_id)
        .order_by(
            desc(RelationshipProfileSnapshot.snapshot_date),
            desc(RelationshipProfileSnapshot.created_at),
        )
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if snapshot:
        return snapshot
    try:
        return await refresh_profile_snapshot(db, pair_id=pair_id)
    except Exception:
        logger.exception("Failed to refresh pair snapshot", extra={"pair_id": str(pair_id)})
        return None


async def _build_recent_status_lines(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> list[str]:
    lines: list[str] = []

    checkins_result = await db.execute(
        select(Checkin)
        .where(Checkin.pair_id == pair_id)
        .order_by(desc(Checkin.checkin_date), desc(Checkin.created_at))
        .limit(4)
    )
    for checkin in checkins_result.scalars().all():
        parts = []
        if checkin.mood_score is not None:
            parts.append(f"心情 {checkin.mood_score}/10")
        if checkin.interaction_freq is not None:
            parts.append(f"互动 {checkin.interaction_freq}/10")
        if checkin.deep_conversation is not None:
            parts.append("有深聊" if checkin.deep_conversation else "没深聊")
        if parts:
            lines.append(f"打卡 {checkin.checkin_date.isoformat()}：{'，'.join(parts)}")

    reports_result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.status == ReportStatus.COMPLETED,
        )
        .order_by(desc(Report.report_date), desc(Report.created_at))
        .limit(2)
    )
    for report in reports_result.scalars().all():
        summary = []
        if report.health_score is not None:
            summary.append(f"健康分 {round(float(report.health_score))}")
        if isinstance(report.content, dict):
            hint = str(
                report.content.get("change_summary")
                or report.content.get("suggestion")
                or ""
            ).strip()
            if hint:
                summary.append(hint[:48])
        if summary:
            lines.append(f"报告 {report.report_date.isoformat()}：{'；'.join(summary)}")

    feedback_result = await db.execute(
        select(RelationshipEvent)
        .where(
            RelationshipEvent.pair_id == pair_id,
            RelationshipEvent.event_type == "task.feedback_submitted",
        )
        .order_by(desc(RelationshipEvent.occurred_at), desc(RelationshipEvent.created_at))
        .limit(10)
    )
    for event in feedback_result.scalars().all():
        payload = event.payload or {}
        event_user_id = str(event.user_id) if event.user_id else None
        current_user_str = str(user_id) if user_id else None

        outcome = payload.get("outcome")
        if outcome in ("not_yet", "difficult"):
            if current_user_str and event_user_id and current_user_str != event_user_id:
                continue
            outcome_label = "还没做" if outcome == "not_yet" else "遇到阻力"
            lines.append(f"反馈：{outcome_label}")
            continue

        usefulness = payload.get("usefulness_score")
        friction = payload.get("friction_score")
        shift = payload.get("relationship_shift_score")
        if usefulness is None and friction is None and shift is None:
            if outcome == "helped":
                lines.append("反馈：觉得有帮助")
            continue
        items = []
        if usefulness is not None:
            items.append(f"有用度 {usefulness}/5")
        if friction is not None:
            items.append(f"阻力 {friction}/5")
        if shift is not None:
            items.append(f"关系变化 {shift}")
        if items:
            lines.append("反馈：" + "，".join(items))

    return lines[:8]


def _build_task_plan_prompt(
    *,
    pair: Pair,
    for_date: date,
    date_scope: str,
    task_count: int,
    strategy: dict | None,
    scorecard: dict | None,
    effective_settings: dict[str, object],
    snapshot: RelationshipProfileSnapshot | None,
    status_lines: list[str],
) -> str:
    metrics = (snapshot.metrics_json or {}) if snapshot else {}
    risk_summary = (snapshot.risk_summary or {}) if snapshot else {}
    pair_type = str(getattr(getattr(pair, "type", None), "value", pair.type) or "couple")
    lines = [
        f"关系类型：{PAIR_TYPE_LABELS.get(pair_type, '关系')}",
        f"目标日期：{for_date.isoformat()}",
        f"日期层：{'明天预排' if date_scope == 'tomorrow' else '当天执行'}",
        f"任务条数：{task_count}",
        f"当前风险：{risk_summary.get('current_level') or 'none'}",
        f"风险趋势：{risk_summary.get('trend') or 'stable'}",
        f"当前策略强度：{(strategy or {}).get('intensity') or 'steady'}",
    ]

    if scorecard:
        plan_type = str(scorecard.get("plan_type") or "").strip()
        if plan_type:
            lines.append(f"当前计划主题：{plan_type}")
        completion_rate = scorecard.get("completion_rate")
        if completion_rate not in (None, ""):
            lines.append(f"最近任务完成率：{round(float(completion_rate) * 100)}%")
        usefulness_avg = scorecard.get("usefulness_avg")
        if usefulness_avg not in (None, ""):
            lines.append(f"最近任务有用度均值：{usefulness_avg}")
        friction_avg = scorecard.get("friction_avg")
        if friction_avg not in (None, ""):
            lines.append(f"最近任务阻力均值：{friction_avg}")

    mood_avg = metrics.get("mood_avg")
    if mood_avg not in (None, ""):
        lines.append(f"最近心情均值：{mood_avg}/10")
    health_avg = metrics.get("report_health_avg")
    if health_avg not in (None, ""):
        lines.append(f"最近健康分均值：{health_avg}")
    if metrics.get("task_completion_rate") not in (None, ""):
        lines.append(
            f"窗口期任务完成率：{round(float(metrics.get('task_completion_rate') or 0) * 100)}%"
        )

    if status_lines:
        lines.append("最近状态：")
        lines.extend(f"- {line}" for line in status_lines[:8])

    reminder_time = effective_settings.get("reminder_time") or "21:00"
    note_label = "planning_note" if date_scope == "tomorrow" else "daily_note"
    note_hint = (
        "planning_note 写成轻量说明，如“明天已帮你排好，可先调顺优先级”，字数控制在 24 字内。"
        if date_scope == "tomorrow"
        else "daily_note 写成今天执行时的温情引导语，必须控制在 18 到 26 字内，不要鸡汤，绝不能超过 28 字。"
    )

    return "\n".join(
        [
            "你是亲健的关系任务规划助手，请只输出 JSON。",
            *lines,
            "",
            "请生成一组能直接执行的关系任务。",
            "要求：",
            f"1. tasks 必须正好 {task_count} 条。",
            "2. 每条任务都要包含 title、description、category。",
            "3. title 要像一句具体动作，不要空泛鸡汤，不要出现序号。",
            "4. description 40 字内，说明做到什么程度算推进。",
            "5. category 只能是 communication / repair / connection / activity / reflection。",
            "6. 整组任务要有轻重层次，但不要重复同一个动作。",
            "7. 默认任务是双方都能执行的共同任务。",
            f"8. {note_hint}",
            "9. daily_pack_label 写成 6 到 10 个字的短标签。",
            f"10. 这组任务会在 {reminder_time} 前后被查看，内容要适合直接执行。",
            "",
            f'输出 JSON：{{"{note_label}":"...","daily_pack_label":"...","tasks":[{{"title":"...","description":"...","category":"connection"}}]}}',
        ]
    )


def _build_refresh_prompt(
    *,
    pair: Pair,
    task: RelationshipTask,
    sibling_titles: list[str],
    strategy: dict | None,
    snapshot: RelationshipProfileSnapshot | None,
    status_lines: list[str],
) -> str:
    pair_type = str(getattr(getattr(pair, "type", None), "value", pair.type) or "couple")
    risk_summary = (snapshot.risk_summary or {}) if snapshot else {}
    importance = normalize_task_importance_level(
        getattr(task, "importance_level", "medium")
    )
    lines = [
        f"关系类型：{PAIR_TYPE_LABELS.get(pair_type, '关系')}",
        f"原任务标题：{task.title}",
        f"原任务分类：{task.category}",
        f"原任务重要度：{importance}",
        f"当前策略强度：{(strategy or {}).get('intensity') or 'steady'}",
        f"当前风险：{risk_summary.get('current_level') or 'none'}",
    ]
    if sibling_titles:
        lines.append("同层其他任务：")
        lines.extend(f"- {title}" for title in sibling_titles)
    if status_lines:
        lines.append("最近状态：")
        lines.extend(f"- {line}" for line in status_lines[:6])

    return "\n".join(
        [
            "你是亲健的任务刷新助手，请把这一条任务换成更合适的一条，只输出 JSON。",
            *lines,
            "",
            "要求：",
            "1. 只返回一条替代任务，不要解释。",
            "2. title、description、category 都必须返回。",
            "3. 不要和同层其他任务重复。",
            "4. 要保留这条任务的大致重要度，动作依然要具体、温和、可执行。",
            "5. category 只能是 communication / repair / connection / activity / reflection。",
            '输出 JSON：{"title":"...","description":"...","category":"connection"}',
        ]
    )


async def generate_ai_task_pack(
    db: AsyncSession,
    *,
    pair: Pair,
    for_date: date,
    strategy: dict | None,
    scorecard: dict | None,
    effective_settings: dict[str, object],
    user_id: uuid.UUID | None = None,
) -> dict[str, object]:
    from app.ai import chat_completion

    date_scope = resolve_date_scope(for_date)
    task_count = int(effective_settings.get("daily_ai_task_count") or 5)
    snapshot = await _load_or_refresh_snapshot(db, pair_id=pair.id)
    status_lines = await _build_recent_status_lines(db, pair_id=pair.id, user_id=user_id)
    prompt = _build_task_plan_prompt(
        pair=pair,
        for_date=for_date,
        date_scope=date_scope,
        task_count=task_count,
        strategy=strategy,
        scorecard=scorecard,
        effective_settings=effective_settings,
        snapshot=snapshot,
        status_lines=status_lines,
    )
    timeout_seconds = getattr(
        sys.modules[__name__],
        "TASK_PLANNER_AI_TIMEOUT_SECONDS",
        TASK_PLANNER_AI_TIMEOUT_SECONDS,
    )
    try:
        result = await asyncio.wait_for(
            chat_completion(
                settings.AI_TEXT_MODEL,
                [
                    {
                        "role": "system",
                        "content": "你是亲健的关系任务规划助手，输出必须是合法 JSON。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.45,
            ),
            timeout=timeout_seconds,
        )
    except Exception as exc:
        raise TaskPlannerError("planner ai call failed") from exc

    return _parse_task_pack_response(
        result,
        task_count=task_count,
        strategy=strategy,
        effective_settings=effective_settings,
        date_scope=date_scope,
    )


async def generate_ai_task_refresh(
    db: AsyncSession,
    *,
    pair: Pair,
    task: RelationshipTask,
    siblings: list[RelationshipTask],
    strategy: dict | None,
    user_id: uuid.UUID | None = None,
) -> dict[str, str]:
    from app.ai import chat_completion

    snapshot = await _load_or_refresh_snapshot(db, pair_id=pair.id)
    status_lines = await _build_recent_status_lines(db, pair_id=pair.id, user_id=user_id)
    prompt = _build_refresh_prompt(
        pair=pair,
        task=task,
        sibling_titles=[item.title for item in siblings if str(item.id) != str(task.id)],
        strategy=strategy,
        snapshot=snapshot,
        status_lines=status_lines,
    )
    try:
        result = await chat_completion(
            settings.AI_TEXT_MODEL,
            [
                {
                    "role": "system",
                    "content": "你是亲健的任务刷新助手，输出必须是合法 JSON。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
    except Exception as exc:
        raise TaskPlannerError("refresh ai call failed") from exc

    return _parse_refresh_response(result, fallback_title=task.title)


async def get_task_batch_event(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    for_date: date,
) -> RelationshipEvent | None:
    entity_id = f"{pair_id}:{for_date.isoformat()}"
    result = await db.execute(
        select(RelationshipEvent)
        .where(
            RelationshipEvent.pair_id == pair_id,
            RelationshipEvent.event_type == "task.generated",
            RelationshipEvent.entity_type == "daily_task_batch",
            RelationshipEvent.entity_id == entity_id,
        )
        .order_by(desc(RelationshipEvent.occurred_at), desc(RelationshipEvent.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def mark_tomorrow_plan_viewed(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    user_id: uuid.UUID,
    for_date: date,
) -> RelationshipEvent:
    from app.services.relationship_intelligence import record_relationship_event

    return await record_relationship_event(
        db,
        event_type="task.plan_viewed",
        pair_id=pair_id,
        user_id=user_id,
        entity_type="daily_task_batch",
        entity_id=f"{pair_id}:{for_date.isoformat()}",
        payload={"for_date": for_date.isoformat(), "layer": "tomorrow"},
        idempotency_key=f"task-plan-viewed:{pair_id}:{user_id}:{for_date.isoformat()}",
    )


async def has_viewed_tomorrow_plan(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    user_id: uuid.UUID,
    for_date: date,
) -> bool:
    result = await db.execute(
        select(RelationshipEvent)
        .where(
            RelationshipEvent.pair_id == pair_id,
            RelationshipEvent.user_id == user_id,
            RelationshipEvent.event_type == "task.plan_viewed",
        )
        .order_by(desc(RelationshipEvent.occurred_at), desc(RelationshipEvent.created_at))
    )
    target = for_date.isoformat()
    for event in result.scalars().all():
        payload = event.payload or {}
        if payload.get("for_date") == target and payload.get("layer") == "tomorrow":
            return True
    return False


async def was_reminder_sent_for_pair(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    user_id: uuid.UUID,
    target_date: date,
    reminder_time: str,
) -> bool:
    result = await db.execute(
        select(RelationshipEvent)
        .where(
            RelationshipEvent.pair_id == pair_id,
            RelationshipEvent.user_id == user_id,
            RelationshipEvent.event_type == "task.reminder_sent",
        )
        .order_by(desc(RelationshipEvent.occurred_at), desc(RelationshipEvent.created_at))
    )
    target = target_date.isoformat()
    for event in result.scalars().all():
        payload = event.payload or {}
        if (
            payload.get("for_date") == target
            and payload.get("reminder_time") == reminder_time
        ):
            return True
    return False


async def mark_reminder_sent_for_pair(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    user_id: uuid.UUID,
    target_date: date,
    reminder_time: str,
) -> RelationshipEvent:
    from app.services.relationship_intelligence import record_relationship_event

    return await record_relationship_event(
        db,
        event_type="task.reminder_sent",
        pair_id=pair_id,
        user_id=user_id,
        entity_type="daily_task_batch",
        entity_id=f"{pair_id}:{target_date.isoformat()}",
        payload={"for_date": target_date.isoformat(), "reminder_time": reminder_time},
        idempotency_key=f"task-reminder:{pair_id}:{user_id}:{target_date.isoformat()}:{reminder_time}",
    )


async def is_task_layer_started(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    for_date: date,
) -> bool:
    task_result = await db.execute(
        select(RelationshipTask).where(
            RelationshipTask.pair_id == pair_id,
            RelationshipTask.due_date == for_date,
        )
    )
    tasks = task_result.scalars().all()
    if any(str(getattr(task, "source", "") or "system").lower() == "manual" for task in tasks):
        return True
    if any(getattr(task, "status", None) == TaskStatus.COMPLETED for task in tasks):
        return True

    result = await db.execute(
        select(RelationshipEvent)
        .where(
            RelationshipEvent.pair_id == pair_id,
            RelationshipEvent.event_type.in_(
                ["task.refreshed", "task.importance_changed"]
            ),
        )
        .order_by(desc(RelationshipEvent.occurred_at), desc(RelationshipEvent.created_at))
    )
    target = for_date.isoformat()
    for event in result.scalars().all():
        payload = event.payload or {}
        if payload.get("for_date") == target:
            return True
    return False


async def reset_unstarted_system_tasks(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    target_dates: list[date],
) -> int:
    reset_count = 0
    for target_date in target_dates:
        if await is_task_layer_started(db, pair_id=pair_id, for_date=target_date):
            continue
        delete_result = await db.execute(
            delete(RelationshipTask).where(
                RelationshipTask.pair_id == pair_id,
                RelationshipTask.due_date == target_date,
                RelationshipTask.source == "system",
            )
        )
        reset_count += int(delete_result.rowcount or 0)
    return reset_count


async def create_task_planner_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    target_pair_id: uuid.UUID,
    pair_ids: list[uuid.UUID],
    target_date: date,
) -> UserNotification:
    pair_count = len(pair_ids)
    if pair_count > 1:
        content = "有几段关系的明天安排还没看，系统已经先帮你排好了。"
    else:
        content = "明天的安排已经排好，记得抽空看一眼。"

    notification = UserNotification(
        user_id=user_id,
        type=TASK_REMINDER_NOTIFICATION_TYPE,
        content=content,
        target_path=(
            f"/challenges?pair_id={target_pair_id}&scope=tomorrow"
            f"&date={target_date.isoformat()}"
        ),
    )
    db.add(notification)
    await db.flush()
    return notification


async def run_task_planner_reminder_cycle(*, now: datetime | None = None) -> dict[str, int]:
    from app.services.relationship_intelligence import record_relationship_event

    summary_time = current_local_datetime(now).strftime("%H:%M")
    reminded_users = 0
    reminded_pairs = 0

    async with async_session() as db:
        pair_result = await db.execute(
            select(Pair).where(
                Pair.status == PairStatus.ACTIVE,
                Pair.user_b_id.is_not(None),
            )
        )
        pairs = pair_result.scalars().all()

        due_by_user: dict[
            uuid.UUID,
            list[tuple[Pair, dict[str, object], date, str]],
        ] = defaultdict(list)
        for pair in pairs:
            user_a = await db.get(User, pair.user_a_id)
            user_b = await db.get(User, pair.user_b_id) if pair.user_b_id else None
            for viewer in [user_a, user_b]:
                if not viewer:
                    continue
                effective = resolve_effective_task_planner_settings(
                    getattr(viewer, "product_prefs", None),
                    getattr(pair, "task_planner_settings", None),
                )
                if not effective.get("reminder_enabled", True):
                    continue
                local_now = _datetime_in_timezone(
                    now,
                    effective.get("reminder_timezone"),
                )
                reminder_time = str(effective.get("reminder_time") or "21:00")
                if not _reminder_due_in_window(local_now, reminder_time):
                    continue
                due_by_user[viewer.id].append(
                    (pair, effective, local_now.date() + timedelta(days=1), reminder_time)
                )

        for user_id, scoped_pairs in due_by_user.items():
            candidates_by_date: dict[
                date,
                list[tuple[Pair, dict[str, object], str]],
            ] = defaultdict(list)
            for pair, effective, target_date, reminder_time in scoped_pairs:
                if await was_reminder_sent_for_pair(
                    db,
                    pair_id=pair.id,
                    user_id=user_id,
                    target_date=target_date,
                    reminder_time=reminder_time,
                ):
                    continue
                if await has_viewed_tomorrow_plan(
                    db,
                    pair_id=pair.id,
                    user_id=user_id,
                    for_date=target_date,
                ):
                    continue
                candidates_by_date[target_date].append((pair, effective, reminder_time))

            for target_date, candidate_pairs in candidates_by_date.items():
                if not candidate_pairs:
                    continue

                viewer = await db.get(User, user_id)
                pending_pairs: list[uuid.UUID] = []
                for pair, effective, _reminder_time in candidate_pairs:
                    existing_result = await db.execute(
                        select(RelationshipTask).where(
                            RelationshipTask.pair_id == pair.id,
                            RelationshipTask.due_date == target_date,
                            RelationshipTask.source == "system",
                        )
                    )
                    existing_system_tasks = existing_result.scalars().all()
                    if not existing_system_tasks:
                        from app.services.task_adaptation import build_pair_task_adaptation

                        try:
                            strategy, scorecard = await build_pair_task_adaptation(
                                db,
                                pair_id=pair.id,
                                user_id=None,
                            )
                        except Exception:
                            logger.exception(
                                "Failed to build task strategy during reminder cycle",
                                extra={"pair_id": str(pair.id)},
                            )
                            strategy, scorecard = ({}, None)
                        try:
                            pack = await generate_ai_task_pack(
                                db,
                                pair=pair,
                                for_date=target_date,
                                strategy=strategy,
                                scorecard=scorecard,
                                effective_settings=effective,
                            )
                        except TaskPlannerError:
                            logger.warning(
                                "Skipping reminder generation for pair=%s due to planner failure",
                                str(pair.id),
                            )
                            continue

                        saved_tasks: list[RelationshipTask] = []
                        for item in pack["tasks"]:
                            task = RelationshipTask(
                                pair_id=pair.id,
                                user_id=None,
                                title=item["title"],
                                description=item["description"],
                                category=item["category"],
                                due_date=target_date,
                                source="system",
                                importance_level="medium",
                            )
                            db.add(task)
                            saved_tasks.append(task)
                        await db.flush()
                        await record_relationship_event(
                            db,
                            event_type="task.generated",
                            pair_id=pair.id,
                            entity_type="daily_task_batch",
                            entity_id=f"{pair.id}:{target_date.isoformat()}",
                            payload={
                                "for_date": target_date.isoformat(),
                                "generated_by": "reminder_cycle",
                                "task_count": len(saved_tasks),
                                "daily_note": pack["daily_note"],
                                "planning_note": pack["planning_note"],
                                "daily_pack_label": pack["daily_pack_label"],
                                "effective_settings": effective,
                                "strategy": strategy or {},
                            },
                        )
                    pending_pairs.append(pair.id)

                if not pending_pairs:
                    continue

                target_pair_id = pending_pairs[0]
                selected_pair_id = ""
                if viewer and isinstance(getattr(viewer, "product_prefs", None), dict):
                    selected_pair_id = str(
                        (viewer.product_prefs or {}).get("selected_pair_id") or ""
                    ).strip()
                if selected_pair_id:
                    selected_uuid = None
                    try:
                        selected_uuid = uuid.UUID(selected_pair_id)
                    except ValueError:
                        selected_uuid = None
                    if selected_uuid and selected_uuid in pending_pairs:
                        target_pair_id = selected_uuid

                for pair_id in pending_pairs:
                    pair = await db.get(Pair, pair_id)
                    if not pair:
                        continue
                    effective = resolve_effective_task_planner_settings(
                        getattr(viewer, "product_prefs", None) if viewer else None,
                        getattr(pair, "task_planner_settings", None),
                    )
                    await mark_reminder_sent_for_pair(
                        db,
                        pair_id=pair.id,
                        user_id=user_id,
                        target_date=target_date,
                        reminder_time=str(effective.get("reminder_time") or "21:00"),
                    )

                await create_task_planner_notification(
                    db,
                    user_id=user_id,
                    target_pair_id=target_pair_id,
                    pair_ids=pending_pairs,
                    target_date=target_date,
                )
                reminded_users += 1
                reminded_pairs += len(pending_pairs)

        await db.commit()

    summary = {
        "reminded_users": reminded_users,
        "reminded_pairs": reminded_pairs,
    }
    if reminded_users or reminded_pairs:
        logger.info(
            "Task planner reminders sent users=%s pairs=%s time=%s",
            reminded_users,
            reminded_pairs,
            summary_time,
        )
    return summary


async def run_task_planner_reminder_loop() -> None:
    while True:
        await asyncio.sleep(300)
        try:
            await run_task_planner_reminder_cycle()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Task planner reminder loop failed, skipped this run: %s",
                exc.__class__.__name__,
            )


async def stop_task_planner_reminder_loop(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
