"""Shared helpers for relationship insight routes."""

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import validate_pair_access
from app.models import (
    Checkin,
    InterventionPlan,
    Pair,
    RelationshipEvent,
    RelationshipProfileSnapshot,
    Report,
    ReportStatus,
    User,
)
from app.services.relationship_intelligence import refresh_profile_snapshot


async def resolve_scope(
    *,
    pair_id: str | None,
    mode: str | None,
    user: User,
    db: AsyncSession,
) -> tuple[str | None, str | None]:
    if mode == "solo":
        return None, str(user.id)

    if not pair_id:
        raise HTTPException(status_code=422, detail="缺少配对ID")

    await validate_pair_access(pair_id, user, db, require_active=False)
    return pair_id, None


def profile_scope_query(pair_id: str | None, user_id: str | None):
    if pair_id:
        return [
            RelationshipProfileSnapshot.pair_id == pair_id,
            RelationshipProfileSnapshot.user_id.is_(None),
        ]
    return [
        RelationshipProfileSnapshot.user_id == user_id,
        RelationshipProfileSnapshot.pair_id.is_(None),
    ]


def plan_scope_query(pair_id: str | None, user_id: str | None):
    if pair_id:
        return [
            InterventionPlan.pair_id == pair_id,
            InterventionPlan.user_id.is_(None),
        ]
    return [
        InterventionPlan.user_id == user_id,
        InterventionPlan.pair_id.is_(None),
    ]


def event_scope_query(pair_id: str | None, user_id: str | None):
    if pair_id:
        return [RelationshipEvent.pair_id == pair_id]
    return [
        RelationshipEvent.user_id == user_id,
        RelationshipEvent.pair_id.is_(None),
    ]


def dedupe_theory_cards(cards: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[str] = set()
    for card in cards:
        key = str(card.get("id") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(card)
    return deduped


def repair_protocol_type_for_level(level: str) -> str:
    if level == "severe":
        return "de_escalation_protocol"
    if level == "moderate":
        return "structured_repair"
    if level == "mild":
        return "gentle_repair"
    return "steady_maintenance"


def timeline_category_for_event(event_type: str) -> str:
    if event_type.startswith("client."):
        return "client"
    if event_type.startswith("checkin."):
        return "checkin"
    if event_type.startswith("report."):
        return "report"
    if event_type.startswith("crisis."):
        return "risk"
    if event_type.startswith("safety."):
        return "risk"
    if event_type.startswith("task."):
        return "action"
    if event_type.startswith("playbook."):
        return "playbook"
    if event_type.startswith("plan."):
        return "strategy"
    if event_type.startswith("message."):
        return "coach"
    if event_type.startswith("alignment."):
        return "alignment"
    return "system"


def timeline_category_label(category: str) -> str:
    return {
        "client": "端侧",
        "checkin": "记录",
        "report": "洞察",
        "risk": "风险",
        "action": "行动",
        "playbook": "剧本",
        "strategy": "策略",
        "coach": "教练",
        "alignment": "对齐",
        "system": "系统",
    }.get(category, "系统")


def timeline_tone_for_event(event_type: str, payload: dict) -> str:
    if event_type in {"crisis.raised", "crisis.updated"}:
        return "warning"
    if event_type in {"client.risk.flagged", "safety.crisis_gate_opened"}:
        return "warning"
    if event_type in {"crisis.resolved", "task.completed", "task.feedback_submitted"}:
        return "progress"
    if event_type in {"report.completed", "plan.evaluation_snapshot"}:
        return "insight"
    if event_type in {"message.simulated", "alignment.generated"}:
        return "support"
    if event_type in {"playbook.transitioned", "task.generated"}:
        return "movement"
    if payload.get("risk_level") in {"moderate", "severe"}:
        return "warning"
    return "neutral"


def timeline_tone_label(tone: str) -> str:
    return {
        "warning": "需要留意",
        "progress": "正在推进",
        "insight": "得到洞察",
        "support": "辅助理解",
        "movement": "状态切换",
        "neutral": "持续记录",
    }.get(tone, "持续记录")


def timeline_event_label(event_type: str) -> str:
    labels = {
        "client.precheck.completed": "端侧预检已完成",
        "client.risk.flagged": "端侧发现了风险信号",
        "checkin.created": "完成了一次记录",
        "checkin.local_saved": "记录先保存在本地",
        "checkin.synced": "本地记录已同步到云端",
        "checkin.analyzed": "记录分析已更新",
        "report.completed": "新简报生成完成",
        "safety.crisis_gate_opened": "安全边界已被触发",
        "crisis.raised": "风险信号被抬升",
        "crisis.updated": "风险状态已刷新",
        "crisis.resolved": "风险信号已回落",
        "task.generated": "系统排出了新任务",
        "task.completed": "一项任务已完成",
        "task.feedback_submitted": "任务反馈已回收",
        "playbook.transitioned": "七天剧本切换分支",
        "message.simulated": "聊天前预演已完成",
        "alignment.generated": "双视角对齐已生成",
        "plan.evaluation_snapshot": "干预评估快照已更新",
    }
    if event_type in labels:
        return labels[event_type]
    if event_type.endswith(".completed"):
        return "一个节点已完成"
    if event_type.endswith(".generated"):
        return "系统生成了新的输出"
    return event_type.replace(".", " / ")


def format_timeline_summary(event: RelationshipEvent) -> tuple[str, str | None]:
    payload = event.payload or {}
    event_type = event.event_type

    if event_type == "client.precheck.completed":
        intent = payload.get("intent") or "daily"
        risk = payload.get("risk_level") or "none"
        tags = payload.get("client_tags") or []
        summary = f"端侧完成了一次 {intent} 预检"
        detail = f"风险等级 {risk}"
        if tags:
            detail = f"{detail}，标签：{'，'.join(str(item) for item in tags[:3])}"
        return summary, detail

    if event_type == "client.risk.flagged":
        hits = payload.get("risk_hits") or []
        summary = f"端侧捕捉到 {payload.get('risk_level') or 'watch'} 风险信号"
        return summary, f"命中关键词：{'，'.join(str(item) for item in hits[:4])}" if hits else None

    if event_type == "checkin.created":
        mode = "个人" if payload.get("mode") == "solo" else "关系"
        mood = payload.get("mood_score")
        summary = (
            f"{mode}记录已写入"
            f"{f'，情绪分 {mood}' if mood is not None else ''}"
        )
        detail_parts = []
        if payload.get("deep_conversation") is True:
            detail_parts.append("记录里提到有深聊")
        if payload.get("task_completed") is True:
            detail_parts.append("并且完成了当天任务")
        return summary, "，".join(detail_parts) if detail_parts else None

    if event_type == "checkin.local_saved":
        policy = payload.get("upload_policy") or "full"
        return "这条记录先留在了本地", f"隐私模式：{payload.get('privacy_mode') or 'local_first'} · 上传策略：{policy}"

    if event_type == "checkin.synced":
        policy = payload.get("upload_policy") or "full"
        return "本地记录已同步进入系统", f"上传策略：{policy}"

    if event_type == "safety.crisis_gate_opened":
        hits = payload.get("risk_hits") or []
        return "系统切换到高风险保护路径", f"命中信号：{'，'.join(str(item) for item in hits[:4])}" if hits else None

    if event_type == "report.completed":
        report_type = payload.get("report_type") or "daily"
        score = payload.get("health_score")
        summary = (
            f"{report_type} 简报已生成"
            f"{f'，健康分 {score}' if score is not None else ''}"
        )
        return summary, payload.get("summary") or payload.get("suggestion")

    if event_type in {"crisis.raised", "crisis.updated"}:
        level = payload.get("level") or "unknown"
        score = payload.get("health_score")
        summary = f"风险等级变为 {level}"
        detail = f"关联健康分 {score}" if score is not None else None
        return summary, detail

    if event_type == "crisis.resolved":
        reason = payload.get("reason")
        summary = "风险信号已解除"
        return summary, f"解除原因：{reason}" if reason else None

    if event_type == "task.generated":
        count = payload.get("task_count")
        intensity = payload.get("intensity")
        summary = f"系统生成了 {count or 0} 个行动建议"
        return summary, f"当前任务强度：{intensity}" if intensity else None

    if event_type == "task.completed":
        title = payload.get("title")
        category = payload.get("category")
        summary = f"完成了一项行动：{title}" if title else "完成了一项行动任务"
        return summary, f"任务类别：{category}" if category else None

    if event_type == "task.feedback_submitted":
        useful = payload.get("usefulness_score")
        friction = payload.get("friction_score")
        summary = "系统收到了这项任务的主观反馈"
        detail_parts = []
        if useful is not None:
            detail_parts.append(f"有用度 {useful}/5")
        if friction is not None:
            detail_parts.append(f"摩擦感 {friction}/5")
        return summary, "，".join(detail_parts) if detail_parts else None

    if event_type == "playbook.transitioned":
        to_branch = payload.get("to_branch")
        to_day = payload.get("to_day")
        summary = f"七天剧本切到了 {to_branch or '新'} 分支"
        return summary, f"当前推进到第 {to_day} 天" if to_day else None

    if event_type == "message.simulated":
        risk_level = payload.get("risk_level")
        summary = "系统完成了一次发言预演"
        return summary, f"预演风险等级：{risk_level}" if risk_level else None

    if event_type == "alignment.generated":
        score = payload.get("alignment_score")
        summary = "系统整理出了一版双视角对齐"
        return summary, f"对齐分 {score}" if score is not None else None

    if event_type == "plan.evaluation_snapshot":
        verdict = payload.get("verdict_label") or payload.get("verdict")
        recommendation = payload.get("recommendation_label")
        summary = f"干预效果快照已刷新{f'：{verdict}' if verdict else ''}"
        return summary, recommendation

    return timeline_event_label(event_type), None


def timeline_tags_for_event(event: RelationshipEvent) -> list[str]:
    payload = event.payload or {}
    tags: list[str] = []
    for key in (
        "level",
        "risk_level",
        "plan_type",
        "momentum",
        "intensity",
        "report_type",
        "intent",
        "upload_policy",
    ):
        value = payload.get(key)
        if value:
            tags.append(str(value))
    return tags[:4]


def serialize_timeline_event(event: RelationshipEvent) -> dict:
    payload = event.payload or {}
    category = timeline_category_for_event(event.event_type)
    tone = timeline_tone_for_event(event.event_type, payload)
    summary, detail = format_timeline_summary(event)
    return {
        "id": event.id,
        "occurred_at": event.occurred_at,
        "event_type": event.event_type,
        "label": timeline_event_label(event.event_type),
        "summary": summary,
        "detail": detail,
        "category": category,
        "category_label": timeline_category_label(category),
        "tone": tone,
        "tone_label": timeline_tone_label(tone),
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "source": event.source,
        "tags": timeline_tags_for_event(event),
        "payload": payload or None,
    }


def detail_metric(label: str, value: object | None) -> dict | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return {"label": label, "value": text}


def detail_card(title: str, body: object | None, *, tone: str | None = None) -> dict | None:
    if body is None:
        return None
    text = str(body).strip()
    if not text:
        return None
    return {"title": title, "body": text, "tone": tone}


def format_bool(value: bool | None) -> str | None:
    if value is None:
        return None
    return "是" if value else "否"


async def get_latest_pair_snapshot(
    db: AsyncSession, pair_id: str
) -> RelationshipProfileSnapshot:
    result = await db.execute(
        select(RelationshipProfileSnapshot)
        .where(
            RelationshipProfileSnapshot.pair_id == pair_id,
            RelationshipProfileSnapshot.user_id.is_(None),
        )
        .order_by(
            RelationshipProfileSnapshot.snapshot_date.desc(),
            RelationshipProfileSnapshot.created_at.desc(),
        )
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if snapshot:
        return snapshot
    return await refresh_profile_snapshot(db, pair_id=pair_id)


async def get_latest_pair_plan(
    db: AsyncSession, pair_id: str
) -> InterventionPlan | None:
    result = await db.execute(
        select(InterventionPlan)
        .where(
            InterventionPlan.pair_id == pair_id,
            InterventionPlan.user_id.is_(None),
            InterventionPlan.status == "active",
        )
        .order_by(desc(InterventionPlan.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_completed_report(db: AsyncSession, pair_id: str) -> Report | None:
    result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.status == ReportStatus.COMPLETED,
        )
        .order_by(Report.report_date.desc(), Report.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_completed_report_for_scope(
    db: AsyncSession, *, pair_id: str | None, user_id: str | None
) -> Report | None:
    if pair_id:
        return await get_latest_completed_report(db, pair_id)

    result = await db.execute(
        select(Report)
        .where(
            Report.user_id == user_id,
            Report.status == ReportStatus.COMPLETED,
        )
        .order_by(Report.report_date.desc(), Report.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_dual_checkins(
    db: AsyncSession, pair: Pair
) -> tuple[Checkin | None, Checkin | None]:
    if not pair.user_b_id:
        return None, None

    result = await db.execute(
        select(Checkin)
        .where(Checkin.pair_id == pair.id)
        .order_by(Checkin.checkin_date.desc(), Checkin.created_at.desc())
        .limit(40)
    )
    checkins = result.scalars().all()
    by_date: dict[str, dict[str, Checkin]] = {}
    user_a_id = str(pair.user_a_id)
    user_b_id = str(pair.user_b_id)

    for checkin in checkins:
        date_key = checkin.checkin_date.isoformat()
        bucket = by_date.setdefault(date_key, {})
        user_key = str(checkin.user_id)
        if user_key not in bucket:
            bucket[user_key] = checkin

    for date_key in sorted(by_date.keys(), reverse=True):
        bucket = by_date[date_key]
        if user_a_id in bucket and user_b_id in bucket:
            return bucket[user_a_id], bucket[user_b_id]

    return None, None


def serialize_checkin(checkin: Checkin, label: str) -> dict:
    return {
        "label": label,
        "checkin_date": checkin.checkin_date.isoformat(),
        "content": checkin.content,
        "mood_score": checkin.mood_score,
        "interaction_freq": checkin.interaction_freq,
        "interaction_initiative": checkin.interaction_initiative,
        "deep_conversation": checkin.deep_conversation,
        "task_completed": checkin.task_completed,
        "sentiment_score": checkin.sentiment_score,
    }
