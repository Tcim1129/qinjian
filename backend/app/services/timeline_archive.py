"""Archive timeline helpers for long-term safe history and short-lived raw data."""

from __future__ import annotations

import os
import re
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.time import current_local_date, local_date_cutoff_to_utc_naive
from app.models import Checkin, Report, ReportStatus
from app.services.behavior_judgement import summarize_text_emotion
from app.services.upload_access import (
    is_local_upload_path,
    resolve_upload_file_path,
)

RAW_RETENTION_DAYS = 30
ARCHIVE_FETCH_MULTIPLIER = 4
MAX_ARCHIVE_FETCH = 240
MAX_EXPORT_FETCH = 400

INTENT_LABELS = {
    "daily": "日常记录",
    "emergency": "冲突处理中",
    "crisis": "需要保护",
    "reflection": "关系复盘",
}
RISK_LABELS = {
    "none": "平稳",
    "watch": "值得留意",
    "high": "需要谨慎处理",
}
REPORT_TYPE_LABELS = {
    "daily": "每日报告",
    "weekly": "周报告",
    "monthly": "月报告",
    "solo": "个人记录报告",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def archive_retention_until(reference: datetime | None = None) -> datetime:
    local_day = current_local_date(reference)
    retention_day = local_day + timedelta(days=RAW_RETENTION_DAYS)
    return local_date_cutoff_to_utc_naive(
        retention_day,
        hour=settings.PRIVACY_RETENTION_CUTOFF_HOUR_LOCAL,
    )


def archive_retention_policy() -> dict[str, Any]:
    return {
        "timezone": settings.APP_TIMEZONE,
        "retention_days": RAW_RETENTION_DAYS,
        "cutoff_hour_local": int(settings.PRIVACY_RETENTION_CUTOFF_HOUR_LOCAL),
        "cutoff_label": f"北京时间每日 {int(settings.PRIVACY_RETENTION_CUTOFF_HOUR_LOCAL):02d}:00",
    }


def _as_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _truncate(value: str | None, limit: int) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 1, 1)]}…"


def _dedupe_texts(values: list[str | None]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in values:
        item = _clean_text(raw)
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _dedupe_uuid_strings(values: list[str | uuid.UUID]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in values:
        item = str(raw or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _safe_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item or "").strip()]
    return []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _client_context_preview(context: dict[str, Any] | None) -> dict[str, Any]:
    payload = _safe_dict(context)
    return {
        "intent": str(payload.get("intent") or "daily"),
        "risk_level": str(payload.get("risk_level") or "none"),
        "upload_policy": str(payload.get("upload_policy") or "full"),
        "source_type": str(payload.get("source_type") or "text"),
        "client_tags": _safe_list(payload.get("client_tags")),
    }


def _retention_reference_for_checkin(checkin: Checkin) -> datetime:
    if isinstance(checkin.checkin_date, date):
        return local_date_cutoff_to_utc_naive(
            checkin.checkin_date,
            hour=settings.PRIVACY_RETENTION_CUTOFF_HOUR_LOCAL,
        )
    return checkin.created_at or utcnow()


def _build_archive_title(
    *,
    primary_mood: str | None,
    intent: str,
    image_analysis: dict[str, Any],
    has_voice: bool,
) -> str:
    image_summary = _truncate(image_analysis.get("scene_summary"), 32)
    if image_summary:
        return image_summary
    if primary_mood and primary_mood not in {"等你开口", "平静"}:
        return f"{primary_mood}的一次记录"
    if intent == "reflection":
        return "一次复盘记录"
    if has_voice:
        return "留下一段语音记录"
    return "留下一条今天的记录"


def build_checkin_archive_insight(
    *,
    content: str | None,
    context: dict[str, Any] | None,
    mood_tags: dict | None,
) -> dict[str, Any]:
    payload = _safe_dict(context)
    preview = _client_context_preview(payload)
    device_meta = _safe_dict(payload.get("device_meta"))
    image_meta = _safe_dict(device_meta.get("image"))
    image_analysis = _safe_dict(image_meta.get("analysis"))
    voice_meta = _safe_dict(device_meta.get("voice"))
    text_emotion = summarize_text_emotion(content)

    mood_tag_values = _safe_list(_safe_dict(mood_tags).get("tags"))
    derived_tags = _dedupe_texts(
        mood_tag_values
        + _safe_list(text_emotion.get("mood_tags"))
        + _safe_list(image_analysis.get("mood_tags"))
        + [INTENT_LABELS.get(preview["intent"]) if preview["intent"] != "daily" else None]
        + (["图片线索"] if image_analysis else [])
        + (["语音记录"] if voice_meta else [])
    )

    primary_mood = str(
        text_emotion.get("primary_mood")
        or text_emotion.get("mood_label")
        or "平静"
    )
    secondary_moods = _safe_list(text_emotion.get("secondary_moods"))

    summary_parts: list[str] = []
    if secondary_moods:
        summary_parts.append(
            f"这天更像在记录{primary_mood}，同时也带着{'、'.join(secondary_moods)}。"
        )
    elif primary_mood and primary_mood != "等你开口":
        summary_parts.append(f"这天更像在记录{primary_mood}。")

    intent = preview["intent"]
    if intent in {"emergency", "crisis", "reflection"}:
        summary_parts.append(f"这条内容更像{INTENT_LABELS.get(intent, '一段重要片段')}。")

    image_scene = _truncate(image_analysis.get("scene_summary"), 60)
    if image_scene:
        summary_parts.append(f"也附带了一张图片，画面里更像{image_scene}。")

    duration_seconds = voice_meta.get("duration_seconds")
    try:
        voice_duration = float(duration_seconds) if duration_seconds is not None else None
    except (TypeError, ValueError):
        voice_duration = None
    if voice_duration:
        summary_parts.append(f"还附带了一段 {voice_duration:.1f} 秒的语音。")

    risk_level = preview["risk_level"]
    if risk_level in {"watch", "high"}:
        summary_parts.append(
            f"系统把它标记为{RISK_LABELS.get(risk_level, '值得留意')}。"
        )

    summary = _truncate(" ".join(summary_parts) or "这天留下了一条记录，并补充了结构化线索。", 220)
    title = _truncate(
        _build_archive_title(
            primary_mood=primary_mood,
            intent=intent,
            image_analysis=image_analysis,
            has_voice=bool(voice_meta),
        ),
        60,
    ) or "留下一条今天的记录"

    return {
        "title": title,
        "summary": summary or "这天留下了一条记录。",
        "tags": derived_tags,
        "retention_policy": archive_retention_policy(),
        "intent": intent,
        "intent_label": INTENT_LABELS.get(intent, "日常记录"),
        "risk_level": risk_level,
        "risk_label": RISK_LABELS.get(risk_level, "平稳"),
        "text_emotion": {
            "sentiment": text_emotion.get("sentiment"),
            "sentiment_label": text_emotion.get("sentiment_label"),
            "mood_label": text_emotion.get("mood_label"),
            "primary_mood": primary_mood,
            "secondary_moods": secondary_moods,
            "mood_tags": _safe_list(text_emotion.get("mood_tags")),
            "score": text_emotion.get("score"),
            "reason": text_emotion.get("reason"),
        },
        "image": {
            "scene_summary": image_analysis.get("scene_summary"),
            "mood": image_analysis.get("mood"),
            "mood_tags": _safe_list(image_analysis.get("mood_tags")),
            "risk_level_label": image_analysis.get("risk_level_label"),
            "privacy_sensitivity_label": image_analysis.get(
                "privacy_sensitivity_label"
            ),
            "retention_recommendation_label": image_analysis.get(
                "retention_recommendation_label"
            ),
        }
        if image_analysis
        else None,
        "voice": {
            "duration_seconds": voice_duration,
            "silence_ratio": voice_meta.get("silence_ratio"),
            "peak_level": voice_meta.get("peak_level"),
            "voice_emotion": _safe_dict(voice_meta.get("voice_emotion")) or None,
            "content_emotion": _safe_dict(voice_meta.get("content_emotion")) or None,
        }
        if voice_meta
        else None,
        "client_context_preview": preview,
    }


def ensure_checkin_archive_fields(checkin: Checkin) -> dict[str, Any]:
    context = _safe_dict(checkin.client_context)
    archive_insight = _safe_dict(context.get("archive_insight"))
    if not archive_insight:
        archive_insight = build_checkin_archive_insight(
            content=checkin.content,
            context=context,
            mood_tags=checkin.mood_tags,
        )
    context["archive_insight"] = archive_insight
    checkin.client_context = context

    if not _clean_text(checkin.archive_title):
        checkin.archive_title = str(archive_insight.get("title") or "留下一条今天的记录")
    if not _clean_text(checkin.archive_summary):
        checkin.archive_summary = str(
            archive_insight.get("summary") or "这天留下了一条记录。"
        )
    if not isinstance(checkin.archive_tags, list) or not checkin.archive_tags:
        checkin.archive_tags = _safe_list(archive_insight.get("tags"))
    if (
        checkin.raw_retention_until is None
        and checkin.raw_deleted_at is None
        and (checkin.image_url or checkin.voice_url)
    ):
        checkin.raw_retention_until = archive_retention_until(
            _retention_reference_for_checkin(checkin)
        )

    return archive_insight


async def backfill_archive_checkins(
    db: AsyncSession,
    *,
    limit: int = 200,
) -> int:
    stmt = (
        select(Checkin)
        .where(
            or_(
                Checkin.archive_title.is_(None),
                Checkin.archive_summary.is_(None),
                Checkin.archive_tags.is_(None),
                and_(
                    Checkin.raw_retention_until.is_(None),
                    Checkin.raw_deleted_at.is_(None),
                    or_(
                        Checkin.image_url.is_not(None),
                        Checkin.voice_url.is_not(None),
                    ),
                ),
            )
        )
        .order_by(Checkin.created_at.asc(), Checkin.id.asc())
        .limit(max(limit, 1))
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    for checkin in rows:
        ensure_checkin_archive_fields(checkin)
    return len(rows)


def raw_window_open(checkin: Checkin, reference_now: datetime | None = None) -> bool:
    now = reference_now or utcnow()
    if checkin.raw_deleted_at is not None:
        return False
    if checkin.raw_retention_until and checkin.raw_retention_until <= now:
        return False
    return True


def _upload_exists(upload_path: str | None) -> bool:
    if not upload_path:
        return False
    if is_local_upload_path(upload_path):
        try:
            return os.path.exists(resolve_upload_file_path(upload_path))
        except ValueError:
            return False
    return True


def has_raw_content(checkin: Checkin, reference_now: datetime | None = None) -> bool:
    _ = reference_now
    return bool(_clean_text(checkin.content))


def has_image_original(checkin: Checkin, reference_now: datetime | None = None) -> bool:
    return raw_window_open(checkin, reference_now) and _upload_exists(checkin.image_url)


def has_voice_original(checkin: Checkin, reference_now: datetime | None = None) -> bool:
    return raw_window_open(checkin, reference_now) and _upload_exists(checkin.voice_url)


def checkin_raw_deleted(checkin: Checkin, reference_now: datetime | None = None) -> bool:
    if checkin.raw_deleted_at is not None:
        return True
    if checkin.raw_retention_until and checkin.raw_retention_until <= (reference_now or utcnow()):
        return True
    return False


def serialize_archive_checkin_item(
    checkin: Checkin,
    *,
    actor_user_id: uuid.UUID | str,
    reference_now: datetime | None = None,
) -> dict[str, Any]:
    now = reference_now or utcnow()
    archive_insight = ensure_checkin_archive_fields(checkin)
    is_owner = str(checkin.user_id) == str(actor_user_id)
    owned_raw_text = has_raw_content(checkin, now)
    owned_raw_image = has_image_original(checkin, now)
    owned_raw_voice = has_voice_original(checkin, now)
    raw_deleted = checkin_raw_deleted(checkin, now)
    local_date = checkin.checkin_date or checkin.created_at.date()
    title = _truncate(checkin.archive_title, 80) or "留下一条今天的记录"
    summary = _truncate(checkin.archive_summary, 240) or "这天留下了一条记录。"
    tags = _safe_list(checkin.archive_tags) or _safe_list(archive_insight.get("tags"))

    if not is_owner:
        return {
            "id": checkin.id,
            "item_type": "partner_record_placeholder",
            "occurred_at": checkin.created_at,
            "local_date": local_date,
            "title": "对方在这天也留下了一条记录",
            "summary": summary,
            "tags": tags,
            "visibility": "shared_summary",
            "locked_reason": "原文和原媒体默认仅记录者本人可见。",
            "has_raw_content": False,
            "has_image_original": False,
            "has_voice_original": False,
            "raw_retention_until": None,
            "raw_deleted_at": None,
            "download_available": False,
            "__export_kind": "placeholder",
        }

    return {
        "id": checkin.id,
        "item_type": "record",
        "occurred_at": checkin.created_at,
        "local_date": local_date,
        "title": title,
        "summary": summary,
        "tags": tags,
        "visibility": "owner_only",
        "locked_reason": None,
        "has_raw_content": owned_raw_text,
        "has_image_original": owned_raw_image,
        "has_voice_original": owned_raw_voice,
        "raw_retention_until": None,
        "raw_deleted_at": None,
        "download_available": False,
        "record": {
            "content": checkin.content if owned_raw_text else None,
            "mood_tags": _safe_list(_safe_dict(checkin.mood_tags).get("tags")),
            "sentiment_score": checkin.sentiment_score,
            "mood_score": checkin.mood_score,
            "interaction_freq": checkin.interaction_freq,
            "interaction_initiative": checkin.interaction_initiative,
            "deep_conversation": checkin.deep_conversation,
            "task_completed": checkin.task_completed,
            "image": {
                "access_url": None,
                "available": owned_raw_image,
                "analysis": archive_insight.get("image"),
            },
            "voice": {
                "access_url": None,
                "available": owned_raw_voice,
                "duration_seconds": _safe_dict(archive_insight.get("voice")).get(
                    "duration_seconds"
                ),
                "silence_ratio": _safe_dict(archive_insight.get("voice")).get(
                    "silence_ratio"
                ),
                "voice_emotion": _safe_dict(archive_insight.get("voice")).get(
                    "voice_emotion"
                ),
                "content_emotion": _safe_dict(archive_insight.get("voice")).get(
                    "content_emotion"
                ),
            },
            "archive_insight": archive_insight,
            "client_context_preview": _client_context_preview(checkin.client_context),
        },
        "__export_kind": "record",
        "__raw_content": checkin.content if owned_raw_text else None,
        "__image_upload_path": checkin.image_url if owned_raw_image else None,
        "__voice_upload_path": checkin.voice_url if owned_raw_voice else None,
    }


def serialize_archive_report_item(report: Report) -> dict[str, Any]:
    content = _safe_dict(report.content)
    report_type = str(getattr(report.type, "value", report.type) or "daily")
    title = REPORT_TYPE_LABELS.get(report_type, report_type)
    summary = _truncate(
        content.get("insight")
        or content.get("self_insight")
        or content.get("executive_summary")
        or content.get("relationship_note")
        or "这一期报告已经归档，可以回来回看。",
        240,
    ) or "这一期报告已经归档，可以回来回看。"
    recommendations = content.get("recommendations")
    if not isinstance(recommendations, list):
        recommendations = [item for item in [content.get("suggestion"), content.get("self_care_tip")] if item]
    tags = _dedupe_texts(
        [
            "报告",
            title,
            content.get("crisis_level"),
        ]
    )
    return {
        "id": report.id,
        "item_type": "report",
        "occurred_at": report.created_at,
        "local_date": report.report_date,
        "title": title,
        "summary": summary,
        "tags": tags,
        "visibility": "shared_report",
        "locked_reason": None,
        "has_raw_content": False,
        "has_image_original": False,
        "has_voice_original": False,
        "raw_retention_until": None,
        "raw_deleted_at": None,
        "download_available": False,
        "report": {
            "report_type": report_type,
            "status": str(getattr(report.status, "value", report.status) or "completed"),
            "health_score": report.health_score,
            "report_date": report.report_date,
            "summary": summary,
            "recommendations": recommendations[:3],
            "content": content,
        },
        "__export_kind": "report",
        "__report_content": content,
    }


def parse_archive_cursor(value: str | None) -> tuple[datetime | None, list[uuid.UUID]]:
    raw = str(value or "").strip()
    if not raw:
        return None, []

    before_raw, seen_raw = (raw.split("|", 1) + [""])[:2]
    normalized_before = before_raw.strip()
    if not normalized_before:
        return None, []

    try:
        before_at = datetime.fromisoformat(normalized_before.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid archive cursor") from exc
    if before_at.tzinfo is not None:
        before_at = before_at.astimezone(timezone.utc).replace(tzinfo=None)

    seen_ids: list[uuid.UUID] = []
    for item in seen_raw.split(","):
        token = item.strip()
        if not token:
            continue
        try:
            seen_ids.append(uuid.UUID(token))
        except ValueError:
            continue
    return before_at, seen_ids


def build_archive_cursor(
    occurred_at: datetime | None,
    seen_ids: list[str | uuid.UUID] | None = None,
) -> str | None:
    if not isinstance(occurred_at, datetime):
        return None
    seen_tokens = ",".join(_dedupe_uuid_strings(list(seen_ids or [])))
    return (
        f"{occurred_at.isoformat()}|{seen_tokens}"
        if seen_tokens
        else occurred_at.isoformat()
    )


def _archive_item_sort_key(item: dict[str, Any]) -> tuple[datetime, int]:
    occurred_at = item.get("occurred_at")
    if not isinstance(occurred_at, datetime):
        occurred_at = datetime.min

    item_id = item.get("id")
    try:
        uuid_int = uuid.UUID(str(item_id)).int
    except (TypeError, ValueError, AttributeError):
        uuid_int = 0
    return occurred_at, uuid_int


def merge_archive_items(
    *,
    checkins: list[Checkin],
    reports: list[Report],
    actor_user_id: uuid.UUID | str,
    limit: int | None,
    reference_now: datetime | None = None,
    incoming_cursor: str | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    now = reference_now or utcnow()
    items = [
        *[
            serialize_archive_checkin_item(
                checkin,
                actor_user_id=actor_user_id,
                reference_now=now,
            )
            for checkin in checkins
        ],
        *[serialize_archive_report_item(report) for report in reports],
    ]
    items.sort(key=_archive_item_sort_key, reverse=True)

    if limit is None or len(items) <= limit:
        return items, None

    page_items = items[:limit]
    boundary_time = page_items[-1].get("occurred_at")
    boundary_ids = [
        str(item.get("id"))
        for item in page_items
        if item.get("occurred_at") == boundary_time and item.get("id") is not None
    ]
    incoming_time, incoming_seen_ids = parse_archive_cursor(incoming_cursor)
    if incoming_time == boundary_time and incoming_seen_ids:
        boundary_ids = _dedupe_uuid_strings([*incoming_seen_ids, *boundary_ids])
    next_before = build_archive_cursor(boundary_time, boundary_ids)
    return page_items, next_before


def _archive_window_bounds(
    date_from: date | None,
    date_to: date | None,
) -> tuple[datetime | None, datetime | None]:
    start_at = (
        datetime.combine(date_from, time.min) if isinstance(date_from, date) else None
    )
    end_at = (
        datetime.combine(date_to + timedelta(days=1), time.min)
        if isinstance(date_to, date)
        else None
    )
    return start_at, end_at


async def list_archive_checkins(
    db: AsyncSession,
    *,
    pair_id: str | None,
    user_id: str | None,
    before_at: datetime | None = None,
    before_seen_ids: list[uuid.UUID] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int | None = 24,
    export_mode: bool = False,
) -> list[Checkin]:
    stmt = select(Checkin)
    if pair_id:
        stmt = stmt.where(Checkin.pair_id == _as_uuid(pair_id))
    else:
        stmt = stmt.where(
            Checkin.user_id == _as_uuid(user_id),
            Checkin.pair_id.is_(None),
        )
    if before_at:
        if before_seen_ids:
            stmt = stmt.where(
                or_(
                    Checkin.created_at < before_at,
                    and_(
                        Checkin.created_at == before_at,
                        Checkin.id.not_in(list(before_seen_ids)),
                    ),
                )
            )
        else:
            stmt = stmt.where(Checkin.created_at < before_at)
    start_at, end_at = _archive_window_bounds(date_from, date_to)
    if start_at:
        stmt = stmt.where(Checkin.checkin_date >= start_at.date())
    if end_at:
        stmt = stmt.where(Checkin.checkin_date < end_at.date())

    fetch_limit = None
    if limit is not None:
        base_limit = max(limit * ARCHIVE_FETCH_MULTIPLIER, 40)
        fetch_limit = min(base_limit, MAX_EXPORT_FETCH if export_mode else MAX_ARCHIVE_FETCH)

    stmt = stmt.order_by(Checkin.created_at.desc(), Checkin.id.desc())
    if fetch_limit is not None:
        stmt = stmt.limit(fetch_limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_archive_reports(
    db: AsyncSession,
    *,
    pair_id: str | None,
    user_id: str | None,
    before_at: datetime | None = None,
    before_seen_ids: list[uuid.UUID] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int | None = 24,
    export_mode: bool = False,
) -> list[Report]:
    stmt = select(Report).where(Report.status == ReportStatus.COMPLETED)
    if pair_id:
        stmt = stmt.where(Report.pair_id == _as_uuid(pair_id))
    else:
        stmt = stmt.where(
            Report.user_id == _as_uuid(user_id),
            Report.pair_id.is_(None),
        )
    if before_at:
        if before_seen_ids:
            stmt = stmt.where(
                or_(
                    Report.created_at < before_at,
                    and_(
                        Report.created_at == before_at,
                        Report.id.not_in(list(before_seen_ids)),
                    ),
                )
            )
        else:
            stmt = stmt.where(Report.created_at < before_at)
    start_at, end_at = _archive_window_bounds(date_from, date_to)
    if start_at:
        stmt = stmt.where(Report.report_date >= start_at.date())
    if end_at:
        stmt = stmt.where(Report.report_date < end_at.date())

    fetch_limit = None
    if limit is not None:
        base_limit = max(limit * ARCHIVE_FETCH_MULTIPLIER, 24)
        fetch_limit = min(base_limit, MAX_EXPORT_FETCH if export_mode else MAX_ARCHIVE_FETCH)

    stmt = stmt.order_by(Report.created_at.desc(), Report.id.desc())
    if fetch_limit is not None:
        stmt = stmt.limit(fetch_limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


def filter_archive_items(
    items: list[dict[str, Any]],
    *,
    item_filter: str,
) -> list[dict[str, Any]]:
    normalized = str(item_filter or "all").strip().lower()
    if normalized == "reports":
        return [item for item in items if item.get("item_type") == "report"]
    if normalized == "mine":
        return [item for item in items if item.get("item_type") == "record"]
    return items
