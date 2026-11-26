"""打卡可见性：默认共享摘要（伴侣只见去敏摘要，永不见原文），private 为逐条显式选择。

设计依据：docs/plans/打卡可见性设计.md
- 契约 scope：private / shared_summary / shared_original / system_only
- 伴侣投影：伴侣侧只回答"对方今天有记录、大致情绪如何"，不回答"说了什么、发生了什么"
- 乐观并发：visibility_version 单调递增，变更用 expected_version 做 CAS
- 幂等：client_request_id 去重
- 撤回：在同一事务内失效派生结果，杜绝"已撤回但报告仍可读"的中间态
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from fastapi import HTTPException, status
from sqlalchemy import Text, cast, delete, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Checkin,
    CheckinVisibilityEvent,
    InterventionPlan,
    RelationshipEvent,
    RelationshipMemory,
    RelationshipProfileSnapshot,
    Report,
    ReportStatus,
    ReportType,
)

PRIVATE = "private"
SHARED_SUMMARY = "shared_summary"
# 原文共享已按隐私决策收回，当前不开放向伴侣直接暴露原文
SHARED_ORIGINAL = "shared_original"
SYSTEM_ONLY = "system_only"

SCOPES = (PRIVATE, SHARED_SUMMARY, SYSTEM_ONLY)
DEFAULT_SCOPE = SHARED_SUMMARY
PARTNER_VISIBLE_SCOPES = (SHARED_SUMMARY,)

# 伴侣侧只保留这两个意图，其余（emergency/crisis）一律剥离。
PARTNER_SAFE_INTENTS = ("daily", "reflection")
INTENT_PARTNER_LABELS = {
    "daily": "日常记录",
    "reflection": "关系复盘",
}

ALIGNMENT_EVENT_TYPE = "alignment.generated"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_scope(value: str | None) -> str:
    scope = str(value or "").strip().lower()
    if scope == SHARED_ORIGINAL:
        raise HTTPException(
            status_code=422,
            detail="暂不支持直接共享原文，仅支持摘要共享（shared_summary）或仅自己可见（private）",
        )
    if scope not in SCOPES:
        raise HTTPException(status_code=422, detail="无效的可见性范围")
    return scope


def is_partner_visible(scope: str) -> bool:
    return scope in PARTNER_VISIBLE_SCOPES


def sharing_active(scope: str) -> bool:
    return is_partner_visible(scope)


def partner_can_use_summary(scope: str) -> bool:
    return is_partner_visible(scope)


def partner_can_read_original(scope: str) -> bool:
    return False


PARTNER_HIDDEN_REPORT_PLACEHOLDER = "（这条记录选择了仅自己可见，内容不参与双方报告。）"


def pair_report_content(checkin: Checkin | None, fallback: str = "") -> str:
    """双方报告（日报/周报/月报）的输入内容。

    规则（"系统可分析" 与 "伴侣可见分析结果" 是两种权限，不能混用）：

    - ``private`` / ``system_only``：中性占位，原文绝不进入生成任务。
    - ``shared_summary``：只使用**过滤后的共享摘要**（伴侣投影），不使用原文，
      避免模型引用或透露摘要之外的细节。
    """
    if checkin is None:
        return fallback
    scope = str(checkin.visibility_scope or DEFAULT_SCOPE)
    if scope == SHARED_SUMMARY:
        projection = partner_projection_from_checkin(checkin)
        parts = [str(projection.get("title") or ""), str(projection.get("summary") or "")]
        tags = _safe_list(projection.get("tags"))
        if tags:
            parts.append("标签：" + "、".join(tags))
        text = " ".join(part for part in parts if part).strip()
        return text or fallback
    return PARTNER_HIDDEN_REPORT_PLACEHOLDER


def report_source_snapshot(checkins: Sequence[Checkin | None]) -> list[list[Any]]:
    """记录生成任务入队时来源记录的授权版本，供落库前复核。"""
    snapshot: list[list[Any]] = []
    for checkin in checkins:
        if checkin is None or not is_partner_visible(str(checkin.visibility_scope or DEFAULT_SCOPE)):
            continue
        snapshot.append([str(checkin.id), int(checkin.visibility_version or 1)])
    return snapshot


def _report_content_digest(content: dict | None) -> str:
    encoded = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def report_input_snapshot(reports: Sequence[Report]) -> list[list[str]]:
    """记录周报和月报实际使用的报告及其内容。"""
    return [[str(report.id), _report_content_digest(report.content)] for report in reports]


async def report_inputs_current(
    db: AsyncSession, sources: Sequence[Any] | None, *, lock: bool = False
) -> bool:
    """输入报告被撤回清空或替换后，旧生成结果不能落库。"""
    if sources is None:
        return True
    for item in sources:
        try:
            report_id, digest = uuid.UUID(str(item[0])), str(item[1])
        except (TypeError, ValueError, IndexError):
            return False
        query = select(Report).where(Report.id == report_id).execution_options(populate_existing=True)
        if lock:
            query = query.with_for_update(read=True)
        report = (await db.execute(query)).scalar_one_or_none()
        if (
            report is None
            or report.status != ReportStatus.COMPLETED
            or _report_content_digest(report.content) != digest
        ):
            return False
    return True


async def report_sources_authorized(
    db: AsyncSession, sources: Sequence[Any] | None, *, lock: bool = False
) -> bool:
    """复核来源记录是否仍对伴侣可见、且授权版本未变。

    撤回共享后，排队中或运行中的生成任务必须据此作废，不能把撤回前的内容写回报告。
    """
    if not sources:
        return True
    for item in sources:
        try:
            checkin_id, version = item[0], int(item[1])
            normalized_id = uuid.UUID(str(checkin_id))
        except (TypeError, ValueError, IndexError):
            return False
        query = select(Checkin).where(Checkin.id == normalized_id).execution_options(populate_existing=True)
        if lock:
            query = query.with_for_update(read=True)
        checkin = (await db.execute(query)).scalar_one_or_none()
        if checkin is None:
            return False
        if not is_partner_visible(str(checkin.visibility_scope or DEFAULT_SCOPE)):
            return False
        if int(checkin.visibility_version or 1) != version:
            return False
    return True


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or "").strip()]


def build_partner_projection(archive_insight: dict[str, Any]) -> dict[str, Any]:
    """从结构化标签重建伴侣可见摘要：不含原文、不含风险/危机、不含图片场景描述。"""
    insight = _safe_dict(archive_insight)
    text_emotion = _safe_dict(insight.get("text_emotion"))
    voice = _safe_dict(insight.get("voice"))
    has_image = bool(insight.get("image"))

    primary_mood = str(text_emotion.get("primary_mood") or "").strip()
    secondary_moods = [
        item for item in _safe_list(text_emotion.get("secondary_moods")) if item.strip()
    ]

    parts: list[str] = []
    if secondary_moods:
        parts.append(
            f"这天更像在记录{primary_mood or '一些感受'}，同时也带着{'、'.join(secondary_moods)}。"
        )
    elif primary_mood and primary_mood != "等你开口":
        parts.append(f"这天更像在记录{primary_mood}。")

    intent = str(insight.get("intent") or "daily").strip().lower()
    if intent in PARTNER_SAFE_INTENTS and intent != "daily":
        parts.append(f"这条内容更像{INTENT_PARTNER_LABELS[intent]}。")

    if has_image:
        parts.append("也附带了一张图片。")

    duration = voice.get("duration_seconds")
    try:
        voice_duration = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        voice_duration = None
    if voice_duration:
        parts.append(f"还附带了一段 {voice_duration:.1f} 秒的语音。")

    summary = " ".join(parts).strip() or "这天留下了一条记录。"

    title_parts = [item for item in [primary_mood] if item and item != "等你开口"]
    title = "·".join(title_parts) or "今天的记录"

    # 标签必须重建，不能直接复制 archive_insight["tags"]：
    # 后者混入了意图标签（如危机意图的“需要保护”）与图片分析标签。
    partner_tags: list[str] = []
    for item in _safe_list(text_emotion.get("mood_tags")):
        if item and item not in partner_tags:
            partner_tags.append(item)
    if has_image and "图片线索" not in partner_tags:
        partner_tags.append("图片线索")
    if voice and "语音记录" not in partner_tags:
        partner_tags.append("语音记录")
    safe_intent_label = INTENT_PARTNER_LABELS.get(intent) if intent in PARTNER_SAFE_INTENTS else None
    if safe_intent_label and safe_intent_label not in partner_tags:
        partner_tags.append(safe_intent_label)

    return {
        "title": title[:60],
        "summary": summary[:220],
        "tags": partner_tags,
    }


def partner_projection_from_checkin(checkin: Checkin) -> dict[str, Any]:
    from app.services.timeline_archive import ensure_checkin_archive_fields

    return build_partner_projection(ensure_checkin_archive_fields(checkin))


def serialize_visibility(
    checkin: Checkin,
    *,
    actor_user_id: uuid.UUID | str,
    known_version: str | None = None,
) -> dict[str, Any]:
    scope = str(checkin.visibility_scope or DEFAULT_SCOPE)
    version = int(checkin.visibility_version or 1)
    version_token = str(version)
    return {
        "record_id": checkin.id,
        "relationship_space_id": checkin.pair_id,
        "visibility_scope": scope if scope != SYSTEM_ONLY else PRIVATE,
        "sharing_active": sharing_active(scope),
        "partner_can_use_summary": partner_can_use_summary(scope),
        "partner_can_read_original": partner_can_read_original(scope),
        "version": version_token,
        "not_modified": bool(known_version) and str(known_version) == version_token,
        "deduplicated": False,
        "data_minimized": True,
    }


async def _find_actor_checkin(
    db: AsyncSession,
    record_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> Checkin:
    checkin = await db.get(Checkin, record_id, with_for_update=True)
    if checkin is None or str(checkin.user_id) != str(actor_user_id):
        # 不泄露存在性：无权访问一律 404
        raise HTTPException(status_code=404, detail="记录不存在")
    return checkin


async def invalidate_derived_artifacts(
    db: AsyncSession,
    checkin: Checkin,
) -> dict[str, int]:
    """撤回共享后，在同一事务内失效可能包含该记录的派生结果。"""
    pair_id = checkin.pair_id
    counts = {
        "alignment_results_invalidated": 0,
        "derived_insights_invalidated": 0,
        "snapshots_invalidated": 0,
        "reports_invalidated": 0,
    }
    if pair_id is None:
        return counts

    marker = str(checkin.id)

    alignment_ids = select(RelationshipEvent.id).where(
        RelationshipEvent.pair_id == pair_id,
        RelationshipEvent.event_type == ALIGNMENT_EVENT_TYPE,
        cast(RelationshipEvent.payload, Text).like(f"%{marker}%"),
    )
    snapshot_ids = select(RelationshipProfileSnapshot.id).where(
        RelationshipProfileSnapshot.pair_id == pair_id,
        RelationshipProfileSnapshot.snapshot_date >= checkin.checkin_date,
    )
    plans = (await db.execute(select(InterventionPlan).where(or_(
        InterventionPlan.trigger_snapshot_id.in_(snapshot_ids),
        InterventionPlan.trigger_event_id.in_(alignment_ids),
    )))).scalars().all()
    for plan in plans:
        plan.trigger_snapshot_id = None
        plan.trigger_event_id = None
        plan.status = "invalidated"
        plan.goal_json = {"reason": "记录可见范围已变更，需要重新生成建议"}
    await db.flush()

    alignment_result = await db.execute(
        delete(RelationshipEvent).where(
            RelationshipEvent.pair_id == pair_id,
            RelationshipEvent.event_type == ALIGNMENT_EVENT_TYPE,
            cast(RelationshipEvent.payload, Text).like(f"%{marker}%"),
        )
    )
    counts["alignment_results_invalidated"] = int(alignment_result.rowcount or 0)

    memory_result = await db.execute(
        delete(RelationshipMemory).where(
            RelationshipMemory.pair_id == pair_id,
            RelationshipMemory.user_id == checkin.user_id,
            RelationshipMemory.source_session_id.is_(None),
            ~cast(RelationshipMemory.content, Text).like('%"source_user_message_id"%'),
            RelationshipMemory.created_at >= checkin.created_at,
        )
    )
    counts["derived_insights_invalidated"] = int(memory_result.rowcount or 0)

    snapshot_result = await db.execute(
        delete(RelationshipProfileSnapshot).where(
            RelationshipProfileSnapshot.pair_id == pair_id,
            RelationshipProfileSnapshot.snapshot_date >= checkin.checkin_date,
        )
    )
    counts["snapshots_invalidated"] = int(snapshot_result.rowcount or 0)

    reports = (
        await db.execute(
            select(Report).where(
                Report.pair_id == pair_id,
                Report.type.in_((ReportType.DAILY, ReportType.WEEKLY, ReportType.MONTHLY)),
                Report.status == ReportStatus.COMPLETED,
                Report.report_date >= checkin.checkin_date,
            )
        )
    ).scalars().all()
    for report in reports:
        report.content = None
        report.health_score = None
        report.status = ReportStatus.FAILED
    counts["reports_invalidated"] = len(reports)

    await db.flush()
    return counts


async def change_visibility(
    db: AsyncSession,
    *,
    record_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    expected_version: str,
    target_scope: str,
    sharing_confirmed: bool = False,
    client_request_id: str | None = None,
) -> dict[str, Any]:
    scope = normalize_scope(target_scope)

    if client_request_id:
        existing = (
            await db.execute(
                select(CheckinVisibilityEvent).where(
                    CheckinVisibilityEvent.actor_user_id == actor_user_id,
                    CheckinVisibilityEvent.checkin_id == record_id,
                    CheckinVisibilityEvent.client_request_id == client_request_id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            checkin = await db.get(Checkin, existing.checkin_id)
            if checkin is None:
                raise HTTPException(status_code=404, detail="记录不存在")
            payload = serialize_visibility(
                checkin, actor_user_id=actor_user_id, known_version=None
            )
            payload.update(_safe_dict(existing.invalidated))
            payload["deduplicated"] = True
            payload["sharing_revoked"] = False
            return payload

    checkin = await _find_actor_checkin(db, record_id, actor_user_id)

    current_scope = str(checkin.visibility_scope or DEFAULT_SCOPE)
    current_version = int(checkin.visibility_version or 1)

    if str(expected_version) != str(current_version):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "记录可见性已被更新，请刷新后重试",
                "version": str(current_version),
            },
        )

    if scope in PARTNER_VISIBLE_SCOPES and not sharing_confirmed:
        raise HTTPException(status_code=422, detail="共享前必须显式确认")
    if scope in PARTNER_VISIBLE_SCOPES and checkin.pair_id is None:
        raise HTTPException(status_code=422, detail="单人记录没有可共享的对象")

    was_partner_visible = is_partner_visible(current_scope)
    now_partner_visible = is_partner_visible(scope)
    revoking = was_partner_visible and not now_partner_visible

    counts = {
        "alignment_results_invalidated": 0,
        "derived_insights_invalidated": 0,
        "snapshots_invalidated": 0,
        "reports_invalidated": 0,
    }
    if revoking:
        counts = await invalidate_derived_artifacts(db, checkin)

    checkin.visibility_scope = scope
    checkin.visibility_version = current_version + 1
    checkin.visibility_updated_at = _now()
    if scope in PARTNER_VISIBLE_SCOPES:
        if checkin.sharing_confirmed_at is None:
            checkin.sharing_confirmed_at = _now()
    else:
        checkin.sharing_confirmed_at = None

    event = CheckinVisibilityEvent(
        checkin_id=checkin.id,
        actor_user_id=actor_user_id,
        from_scope=current_scope,
        to_scope=scope,
        from_version=current_version,
        to_version=checkin.visibility_version,
        sharing_confirmed=bool(sharing_confirmed),
        client_request_id=client_request_id,
        invalidated=counts,
        created_at=_now(),
    )
    db.add(event)
    await db.flush()

    payload = serialize_visibility(checkin, actor_user_id=actor_user_id)
    payload.update(counts)
    payload["sharing_revoked"] = revoking
    return payload
