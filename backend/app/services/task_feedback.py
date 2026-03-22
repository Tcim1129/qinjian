"""Task feedback storage and aggregation helpers."""

from collections import defaultdict
import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RelationshipEvent

FEEDBACK_STYLE_KEYWORDS = {
    "clear": (
        "具体",
        "清楚",
        "明确",
        "拆开",
        "一步",
        "步骤",
        "直接",
        "怎么做",
        "不够清楚",
        "不知道怎么",
    ),
    "gentle": (
        "温柔",
        "柔和",
        "压力",
        "别太硬",
        "轻一点",
        "轻松",
        "缓一点",
        "不要逼",
        "太累",
        "太难",
    ),
    "compact": (
        "简单",
        "简短",
        "短一点",
        "别太多",
        "太长",
        "一句",
        "小一点",
        "容易做",
    ),
    "example": (
        "例子",
        "示例",
        "模板",
        "参考",
        "开头",
        "怎么说",
        "不知道说",
    ),
}


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _date_start(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _date_end(value: date) -> datetime:
    return datetime.combine(value + timedelta(days=1), time.min)


def summarize_feedback_map(feedback_map: dict[str, dict]) -> dict:
    feedbacks = list(feedback_map.values())
    if not feedbacks:
        return {
            "feedback_count": 0,
            "usefulness_avg": None,
            "friction_avg": None,
        }

    usefulness_values = [
        int(item["usefulness_score"])
        for item in feedbacks
        if item.get("usefulness_score") is not None
    ]
    friction_values = [
        int(item["friction_score"])
        for item in feedbacks
        if item.get("friction_score") is not None
    ]
    usefulness_avg = (
        round(sum(usefulness_values) / len(usefulness_values), 2)
        if usefulness_values
        else None
    )
    friction_avg = (
        round(sum(friction_values) / len(friction_values), 2)
        if friction_values
        else None
    )
    return {
        "feedback_count": len(feedbacks),
        "usefulness_avg": usefulness_avg,
        "friction_avg": friction_avg,
    }


def _score_feedback_style(events: list[RelationshipEvent]) -> dict[str, int]:
    style_scores: dict[str, int] = defaultdict(int)

    for event in events:
        payload = event.payload or {}
        usefulness = payload.get("usefulness_score")
        friction = payload.get("friction_score")
        note = str(payload.get("note") or "").strip().lower()

        if usefulness is not None:
            usefulness_value = int(usefulness)
            if usefulness_value <= 2:
                style_scores["clear"] += 2
                style_scores["example"] += 1
            elif usefulness_value >= 4:
                style_scores["compact"] += 1

        if friction is not None:
            friction_value = int(friction)
            if friction_value >= 4:
                style_scores["gentle"] += 2
                style_scores["compact"] += 1
            elif friction_value <= 2:
                style_scores["clear"] += 1

        if not note:
            continue

        for style, keywords in FEEDBACK_STYLE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in note:
                    style_scores[style] += 3

    return style_scores


def _resolve_copy_mode(style_scores: dict[str, int], feedback_count: int) -> str | None:
    if not style_scores or feedback_count < 2:
        return None

    top_mode, top_score = max(
        style_scores.items(),
        key=lambda item: (item[1], item[0]),
    )
    if top_score < 3:
        return None
    return top_mode


async def build_feedback_preference_profile(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
    limit: int = 12,
) -> dict:
    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    if normalized_pair_id is None or normalized_user_id is None:
        return {
            "copy_mode": None,
            "copy_feedback_count": 0,
            "usefulness_avg": None,
            "friction_avg": None,
        }

    result = await db.execute(
        select(RelationshipEvent)
        .where(
            RelationshipEvent.event_type == "task.feedback_submitted",
            RelationshipEvent.entity_type == "relationship_task",
            RelationshipEvent.pair_id == normalized_pair_id,
            RelationshipEvent.user_id == normalized_user_id,
        )
        .order_by(
            RelationshipEvent.occurred_at.desc(),
            RelationshipEvent.created_at.desc(),
        )
        .limit(limit)
    )
    events = result.scalars().all()
    if not events:
        return {
            "copy_mode": None,
            "copy_feedback_count": 0,
            "usefulness_avg": None,
            "friction_avg": None,
        }

    feedback_map: dict[str, dict] = {}
    deduped_events: list[RelationshipEvent] = []
    for event in events:
        entity_id = str(event.entity_id or "")
        if entity_id and entity_id in feedback_map:
            continue
        payload = event.payload or {}
        if entity_id:
            feedback_map[entity_id] = payload
        deduped_events.append(event)

    feedback_summary = summarize_feedback_map(feedback_map)
    style_scores = _score_feedback_style(deduped_events)
    copy_mode = _resolve_copy_mode(
        style_scores,
        feedback_summary["feedback_count"],
    )
    category_preferences: dict[str, dict] = {}
    category_events: dict[str, list[RelationshipEvent]] = defaultdict(list)
    for event in deduped_events:
        payload = event.payload or {}
        category = str(payload.get("category") or "").strip().lower()
        if category:
            category_events[category].append(event)

    for category, scoped_events in category_events.items():
        scoped_feedback_map: dict[str, dict] = {}
        for event in scoped_events:
            entity_id = str(event.entity_id or "")
            if not entity_id or entity_id in scoped_feedback_map:
                continue
            scoped_feedback_map[entity_id] = event.payload or {}

        scoped_summary = summarize_feedback_map(scoped_feedback_map)
        scoped_copy_mode = _resolve_copy_mode(
            _score_feedback_style(scoped_events),
            scoped_summary["feedback_count"],
        )
        if not scoped_copy_mode:
            continue

        category_preferences[category] = {
            "copy_mode": scoped_copy_mode,
            "copy_feedback_count": scoped_summary["feedback_count"],
            "usefulness_avg": scoped_summary["usefulness_avg"],
            "friction_avg": scoped_summary["friction_avg"],
        }

    return {
        "copy_mode": copy_mode,
        "copy_feedback_count": feedback_summary["feedback_count"],
        "usefulness_avg": feedback_summary["usefulness_avg"],
        "friction_avg": feedback_summary["friction_avg"],
        "category_preferences": category_preferences,
    }


async def get_latest_task_feedback_map(
    db: AsyncSession,
    *,
    task_ids: list[str | uuid.UUID] | None = None,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, dict]:
    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    normalized_task_ids = [str(task_id) for task_id in (task_ids or [])]

    stmt = select(RelationshipEvent).where(
        RelationshipEvent.event_type == "task.feedback_submitted",
        RelationshipEvent.entity_type == "relationship_task",
    )
    if normalized_pair_id:
        stmt = stmt.where(RelationshipEvent.pair_id == normalized_pair_id)
    if normalized_user_id:
        stmt = stmt.where(RelationshipEvent.user_id == normalized_user_id)
    if normalized_task_ids:
        stmt = stmt.where(RelationshipEvent.entity_id.in_(normalized_task_ids))
    if start_date:
        stmt = stmt.where(RelationshipEvent.occurred_at >= _date_start(start_date))
    if end_date:
        stmt = stmt.where(RelationshipEvent.occurred_at < _date_end(end_date))

    result = await db.execute(
        stmt.order_by(
            RelationshipEvent.occurred_at.desc(),
            RelationshipEvent.created_at.desc(),
        )
    )
    events = result.scalars().all()

    feedback_map: dict[str, dict] = {}
    for event in events:
        entity_id = str(event.entity_id or "")
        if not entity_id or entity_id in feedback_map:
            continue
        payload = event.payload or {}
        feedback_map[entity_id] = {
            "feedback_event_id": str(event.id),
            "submitted_by_user_id": str(event.user_id) if event.user_id else None,
            "submitted_at": event.occurred_at.isoformat() if event.occurred_at else None,
            "usefulness_score": payload.get("usefulness_score"),
            "friction_score": payload.get("friction_score"),
            "note": payload.get("note"),
        }
    return feedback_map
