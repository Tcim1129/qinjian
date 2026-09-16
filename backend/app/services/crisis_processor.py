"""危机预警自动处理模块 - 报告生成后自动创建 CrisisAlert + 通知"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CrisisAlert,
    CrisisLevel,
    CrisisAlertStatus,
    Pair,
    Report,
    UserNotification,
)
from app.services.relationship_intelligence import record_relationship_event

logger = logging.getLogger(__name__)

# 危机等级中文映射
CRISIS_LEVEL_LABELS = {
    "none": "正常",
    "mild": "轻度预警",
    "moderate": "中度预警",
    "severe": "严重预警",
}

# 危机等级数值映射（用于比较严重程度）
CRISIS_LEVEL_SEVERITY = {
    "none": 0,
    "mild": 1,
    "moderate": 2,
    "severe": 3,
}


def _as_uuid(value: uuid.UUID | str | None) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


async def process_crisis_from_report(
    db: AsyncSession,
    report: Report,
    pair: Pair,
) -> CrisisAlert | None:
    """
    从已完成的报告中提取 crisis_level，创建/更新 CrisisAlert。
    如果 crisis_level 不是 none，同时向双方发送通知。

    应在报告的 content 已写入、status=COMPLETED 之后调用。
    """
    if not report.content:
        return None

    crisis_level_str = report.content.get("crisis_level", "none")
    if crisis_level_str not in CRISIS_LEVEL_SEVERITY:
        crisis_level_str = "none"

    # 如果是 none 级别，不创建预警记录（节省存储）
    # 但如果之前有 active 预警且现在恢复正常，则自动标记为 resolved
    if crisis_level_str == "none":
        await _auto_resolve_active_alerts(db, report.pair_id)
        return None

    # 获取最近一条 active 预警，看是否需要升级/降级
    result = await db.execute(
        select(CrisisAlert)
        .where(
            CrisisAlert.pair_id == report.pair_id,
            CrisisAlert.status == CrisisAlertStatus.ACTIVE,
        )
        .order_by(desc(CrisisAlert.created_at))
        .limit(1)
    )
    last_active = result.scalar_one_or_none()

    previous_level_str = last_active.level.value if last_active else "none"

    # 如果已有同级别的 active 预警，不重复创建
    if last_active and last_active.level.value == crisis_level_str:
        # 但更新干预方案（可能不同的报告给出了更新的建议）
        intervention = report.content.get("intervention") or {}
        last_active.intervention_type = intervention.get("type")
        last_active.intervention_title = intervention.get("title")
        last_active.intervention_desc = intervention.get("description")
        last_active.action_items = intervention.get("action_items")
        last_active.health_score = report.content.get(
            "health_score"
        ) or report.content.get("overall_health_score")
        last_active.report_id = report.id
        await db.flush()
        await record_relationship_event(
            db,
            event_type="crisis.updated",
            pair_id=report.pair_id,
            entity_type="crisis_alert",
            entity_id=last_active.id,
            payload={
                "level": crisis_level_str,
                "health_score": last_active.health_score,
                "status": last_active.status.value,
            },
            idempotency_key=f"crisis:{last_active.id}:updated:{report.id}",
        )
        return last_active

    # 如果之前有 active 预警但级别变了，把旧的标记为 resolved
    if last_active:
        last_active.status = CrisisAlertStatus.RESOLVED
        last_active.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        last_active.resolve_note = f"危机等级变更：{CRISIS_LEVEL_LABELS.get(previous_level_str, previous_level_str)} → {CRISIS_LEVEL_LABELS.get(crisis_level_str, crisis_level_str)}"
        await record_relationship_event(
            db,
            event_type="crisis.resolved",
            pair_id=report.pair_id,
            entity_type="crisis_alert",
            entity_id=last_active.id,
            payload={
                "level": previous_level_str,
                "status": last_active.status.value,
                "reason": "level_changed",
            },
            idempotency_key=f"crisis:{last_active.id}:resolved:{report.id}",
        )

    # 创建新的 CrisisAlert
    intervention = report.content.get("intervention") or {}
    alert = CrisisAlert(
        pair_id=report.pair_id,
        report_id=report.id,
        level=CrisisLevel(crisis_level_str),
        previous_level=CrisisLevel(previous_level_str)
        if previous_level_str != "none"
        else None,
        status=CrisisAlertStatus.ACTIVE,
        intervention_type=intervention.get("type"),
        intervention_title=intervention.get("title"),
        intervention_desc=intervention.get("description"),
        action_items=intervention.get("action_items"),
        health_score=report.content.get("health_score")
        or report.content.get("overall_health_score"),
    )
    db.add(alert)
    await db.flush()
    await record_relationship_event(
        db,
        event_type="crisis.raised",
        pair_id=report.pair_id,
        entity_type="crisis_alert",
        entity_id=alert.id,
        payload={
            "level": crisis_level_str,
            "previous_level": previous_level_str,
            "health_score": alert.health_score,
            "status": alert.status.value,
        },
        idempotency_key=f"crisis:{alert.id}:raised",
    )

    # 创建通知（向配对双方）
    await _create_crisis_notifications(db, pair, crisis_level_str, previous_level_str)

    logger.info(
        f"CrisisAlert created: pair={report.pair_id}, level={crisis_level_str}, "
        f"previous={previous_level_str}, alert_id={alert.id}"
    )

    return alert


async def _auto_resolve_active_alerts(db: AsyncSession, pair_id: uuid.UUID | str):
    """当 crisis_level 恢复 none 时，自动将所有 active 预警标记为 resolved"""
    pair_uuid = _as_uuid(pair_id)
    result = await db.execute(
        select(CrisisAlert).where(
            CrisisAlert.pair_id == pair_uuid,
            CrisisAlert.status == CrisisAlertStatus.ACTIVE,
        )
    )
    active_alerts = result.scalars().all()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for alert in active_alerts:
        alert.status = CrisisAlertStatus.RESOLVED
        alert.resolved_at = now
        alert.resolve_note = "关系状态恢复正常，预警自动解除"
        await record_relationship_event(
            db,
            event_type="crisis.resolved",
            pair_id=pair_uuid,
            entity_type="crisis_alert",
            entity_id=alert.id,
            payload={
                "level": alert.level.value,
                "status": alert.status.value,
                "reason": "auto_recovered",
            },
            idempotency_key=f"crisis:{alert.id}:auto_resolved",
        )
    if active_alerts:
        logger.info(
            f"Auto-resolved {len(active_alerts)} crisis alerts for pair={pair_id}"
        )


async def _create_crisis_notifications(
    db: AsyncSession, pair: Pair, crisis_level: str, previous_level: str
):
    """向配对双方创建危机通知"""
    level_label = CRISIS_LEVEL_LABELS.get(crisis_level, crisis_level)
    is_escalation = CRISIS_LEVEL_SEVERITY.get(
        crisis_level, 0
    ) > CRISIS_LEVEL_SEVERITY.get(previous_level, 0)

    if is_escalation and previous_level != "none":
        content = f"⚠️ 关系预警升级至【{level_label}】，请关注并查看干预建议"
    elif crisis_level == "severe":
        content = (
            f"🚨 检测到【{level_label}】信号，建议立即查看干预方案，必要时寻求专业帮助"
        )
    elif crisis_level == "moderate":
        content = f"⚠️ 检测到【{level_label}】信号，建议查看沟通引导建议"
    else:
        content = f"💡 检测到【{level_label}】信号，推荐尝试趣味互动任务改善关系"

    user_ids = [pair.user_a_id]
    if pair.user_b_id:
        user_ids.append(pair.user_b_id)

    for uid in user_ids:
        notification = UserNotification(
            user_id=uid,
            type="crisis",
            content=content,
        )
        db.add(notification)
