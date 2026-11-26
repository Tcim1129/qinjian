"""Weekly assessment helpers backed by the relationship event stream."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RelationshipEvent
from app.services.relationship_intelligence import (
    record_relationship_event,
    refresh_profile_and_plan,
)

QUESTION_DIMENSION_MAP = {
    "沟通质量": "connection",
    "情感支持": "connection",
    "信任程度": "trust",
    "表达能力": "connection",
    "修复能力": "repair",
    "尊重感": "trust",
    "共同愿景": "shared_future",
    "安全感": "trust",
    "幸福感": "vitality",
    "总体满意": "vitality",
}

DIMENSION_LABELS = {
    "connection": "连接与表达",
    "trust": "信任与安全",
    "repair": "修复能力",
    "shared_future": "共同愿景",
    "vitality": "关系活力",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _normalize_answers(raw_answers: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for entry in raw_answers or []:
        dim = str(entry.get("dim") or entry.get("dimension") or "").strip()
        item_id = str(entry.get("item_id") or "").strip()
        option_id = str(entry.get("option_id") or "").strip()
        score = entry.get("score")
        if not dim:
            continue
        try:
            numeric_score = max(0, min(100, int(score)))
        except (TypeError, ValueError):
            continue
        payload = {"dim": dim, "score": numeric_score}
        if item_id:
            payload["item_id"] = item_id
        if option_id:
            payload["option_id"] = option_id
        normalized.append(payload)
    return normalized


def _build_dimension_scores(answers: list[dict]) -> list[dict]:
    buckets: dict[str, list[int]] = defaultdict(list)
    for answer in answers:
        dimension_key = str(answer.get("dim") or "").strip()
        group = (
            dimension_key
            if dimension_key in DIMENSION_LABELS
            else QUESTION_DIMENSION_MAP.get(dimension_key, "vitality")
        )
        buckets[group].append(int(answer["score"]))

    dimension_scores: list[dict] = []
    for dimension_id, label in DIMENSION_LABELS.items():
        values = buckets.get(dimension_id, [])
        score = round(sum(values) / len(values)) if values else None
        status = "strong" if (score or 0) >= 75 else "watch" if (score or 0) >= 50 else "fragile"
        dimension_scores.append(
            {
                "id": dimension_id,
                "label": label,
                "score": score,
                "status": status,
            }
        )
    return dimension_scores


def _build_change_summary(current_score: int, previous_score: int | None) -> str:
    if previous_score is None:
        return "这是你的第一次周评估，暂时没有可比较的记录。下次填写后，可以查看各项分数的变化。"
    delta = current_score - previous_score
    if delta >= 8:
        return "这次总分比上次提高较多，可以结合最近的相处情况，看看哪些方面有了改善。"
    if delta >= 3:
        return "这次总分比上次略高，可以继续尝试最近觉得有帮助的做法。"
    if delta <= -8:
        return "这次总分比上次下降较多。可以先看看哪些题目的分数变低了，再回顾最近是否遇到了让你不舒服的事情。"
    if delta <= -3:
        return "这次总分比上次略低，可以留意分数较低的项目，下次填写时再作比较。"
    return "这次总分与上次接近，各项分数仍可能有变化，可以分别查看。"


def _profile_signal(current_score: int, previous_score: int | None) -> str | None:
    if previous_score is None:
        return None
    if abs(current_score - previous_score) <= 3:
        return "stable_band"
    return None


def _serialize_assessment_payload(
    *,
    scope: str,
    total_score: int,
    answers: list[dict],
    dimension_scores: list[dict],
    submitted_at: datetime,
    previous_score: int | None,
) -> dict:
    return {
        "scope": scope,
        "total_score": total_score,
        "answers": answers,
        "dimension_scores": dimension_scores,
        "submitted_at": submitted_at.isoformat(),
        "change_summary": _build_change_summary(total_score, previous_score),
        "profile_signal": _profile_signal(total_score, previous_score),
    }


def _event_to_point(event: RelationshipEvent) -> dict:
    payload = event.payload or {}
    dimension_scores = payload.get("dimension_scores") or []
    return {
        "event_id": event.id,
        "submitted_at": payload.get("submitted_at") or event.occurred_at.isoformat(),
        "total_score": int(payload.get("total_score") or 0),
        "dimension_scores": dimension_scores,
        "scope": payload.get("scope") or ("pair" if event.pair_id else "solo"),
        "change_summary": payload.get("change_summary"),
    }


async def _get_recent_assessment_events(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    limit: int,
) -> list[RelationshipEvent]:
    stmt = (
        select(RelationshipEvent)
        .where(
            RelationshipEvent.event_type == "assessment.weekly_submitted",
            RelationshipEvent.pair_id == pair_id,
            RelationshipEvent.user_id == user_id,
        )
        .order_by(desc(RelationshipEvent.occurred_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def submit_weekly_assessment(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
    answers: list[dict],
    submitted_at: datetime | None = None,
) -> dict:
    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    if (normalized_pair_id is None) == (normalized_user_id is None):
        raise ValueError("submit_weekly_assessment requires exactly one scope")

    normalized_answers = _normalize_answers(answers)
    if not normalized_answers:
        raise ValueError("weekly assessment answers cannot be empty")

    scope = "pair" if normalized_pair_id else "solo"
    occurred_at = (submitted_at or _utcnow()).replace(tzinfo=None)
    dimension_scores = _build_dimension_scores(normalized_answers)
    scored_dimensions = [
        int(item["score"])
        for item in dimension_scores
        if item.get("score") is not None
    ]
    total_score = (
        round(sum(scored_dimensions) / len(scored_dimensions))
        if scored_dimensions
        else round(
            sum(int(item["score"]) for item in normalized_answers)
            / len(normalized_answers)
        )
    )
    previous = await get_latest_weekly_assessment(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
    )
    previous_score = previous.get("total_score") if previous else None
    payload = _serialize_assessment_payload(
        scope=scope,
        total_score=total_score,
        answers=normalized_answers,
        dimension_scores=dimension_scores,
        submitted_at=occurred_at,
        previous_score=previous_score,
    )

    event = await record_relationship_event(
        db,
        event_type="assessment.weekly_submitted",
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
        entity_type="weekly_assessment",
        payload=payload,
        occurred_at=occurred_at,
    )
    if payload.get("profile_signal") == "stable_band":
        await record_relationship_event(
            db,
            event_type="assessment.weekly_stable_band_detected",
            pair_id=normalized_pair_id,
            user_id=normalized_user_id,
            entity_type="weekly_assessment_profile_signal",
            payload={
                "summary": "最近两次关系体检总分接近，可以先看看得分最低的项目。",
                "profile_signal": "stable_band",
                "current_score": total_score,
                "previous_score": previous_score,
                "change_summary": payload["change_summary"],
                "risk_level": "none",
            },
            occurred_at=occurred_at,
            idempotency_key=(
                f"assessment:stable-band:{normalized_pair_id or normalized_user_id}:{occurred_at.isoformat()}"
            ),
        )
    await refresh_profile_and_plan(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
    )
    await db.commit()

    point = _event_to_point(event)
    point["change_summary"] = payload["change_summary"]
    return point


async def get_latest_weekly_assessment(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
) -> dict | None:
    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    events = await _get_recent_assessment_events(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
        limit=1,
    )
    if not events:
        return None
    return _event_to_point(events[0])


async def get_weekly_assessment_trend(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
    limit: int = 4,
) -> dict:
    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    events = await _get_recent_assessment_events(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
        limit=max(limit, 1),
    )
    ordered = list(reversed(events))
    points = [_event_to_point(event) for event in ordered]
    latest = points[-1] if points else None
    previous = points[-2] if len(points) >= 2 else None

    return {
        "latest_score": latest["total_score"] if latest else None,
        "dimension_scores": latest["dimension_scores"] if latest else [],
        "trend_points": points,
        "change_summary": (
            _build_change_summary(
                latest["total_score"],
                previous["total_score"] if previous else None,
            )
            if latest
            else "还没有正式周评估记录。"
        ),
    }
