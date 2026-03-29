"""Timeline insight routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, validate_pair_access
from app.core.database import get_db
from app.models import (
    Checkin,
    CrisisAlert,
    InterventionPlan,
    PlaybookTransition,
    RelationshipEvent,
    RelationshipTask,
    Report,
    User,
)
from app.schemas import (
    RelationshipTimelineCurrentContextResponse,
    RelationshipTimelineEventDetailResponse,
    RelationshipTimelineEvidenceCardResponse,
    RelationshipTimelineMetricResponse,
    RelationshipTimelineResponse,
)
from app.services.intervention_effectiveness import build_intervention_scorecard
from app.services.playbook_runtime import sync_active_playbook_runtime
from app.services.relationship_intelligence import record_relationship_event

from .shared import (
    detail_card,
    detail_metric,
    event_scope_query,
    format_bool,
    get_latest_completed_report_for_scope,
    resolve_scope,
    serialize_timeline_event,
)

router = APIRouter(tags=["关系智能"])


async def get_accessible_timeline_event(
    db: AsyncSession, *, event_id: str, user: User
) -> RelationshipEvent:
    event = await db.get(RelationshipEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="时间轴节点不存在")

    if event.pair_id:
        await validate_pair_access(str(event.pair_id), user, db, require_active=False)
        return event

    if event.user_id and str(event.user_id) == str(user.id):
        return event

    raise HTTPException(status_code=403, detail="无权访问该时间轴节点")


def _dedupe_text_items(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _timeline_impact_modules_for_event(event: RelationshipEvent) -> list[str]:
    event_type = str(event.event_type or "").strip()
    entity_type = str(event.entity_type or "").strip()

    modules: list[str] = ["时间轴证据"]

    if event_type.startswith("report.") or entity_type == "report":
        modules.extend(["关系简报", "策略判断"])
    if event_type.startswith("client.") or event_type.startswith("safety."):
        modules.extend(["端侧预检", "隐私保护", "风险拦截"])
    if event_type.startswith("message.") or entity_type == "message_simulation":
        modules.extend(["消息预演", "表达建议"])
    if event_type.startswith("alignment.") or entity_type == "narrative_alignment":
        modules.extend(["双视角对齐", "沟通桥接"])
    if event_type.startswith("crisis.") or event_type.startswith("repair_protocol."):
        modules.extend(["风险状态", "修复协议"])
    if event_type.startswith("task.") or entity_type == "relationship_task":
        modules.extend(["行动任务", "效果回流"])
    if event_type.startswith("playbook.") or entity_type == "playbook_transition":
        modules.extend(["七天剧本", "策略排期"])
    if event_type.startswith("plan.") or entity_type == "intervention_plan":
        modules.extend(["干预计划", "策略审计"])
    if event_type.startswith("assessment."):
        modules.extend(["周评估", "趋势跟踪"])
    if event_type.startswith("checkin.") or entity_type == "checkin":
        modules.extend(["关系画像", "关系简报"])

    return _dedupe_text_items(modules)


async def build_timeline_event_detail(
    db: AsyncSession, event: RelationshipEvent
) -> dict:
    serialized = serialize_timeline_event(event)
    metrics: list[dict] = []
    evidence_cards: list[dict] = []
    payload = event.payload or {}
    pair_scope_id = str(event.pair_id) if event.pair_id else None
    user_scope_id = None if pair_scope_id else (str(event.user_id) if event.user_id else None)

    if event.entity_type == "checkin" and event.entity_id:
        checkin = await db.get(Checkin, event.entity_id)
        if checkin:
            metrics.extend(
                item
                for item in [
                    detail_metric("情绪分", checkin.mood_score),
                    detail_metric("互动频率", checkin.interaction_freq),
                    detail_metric("深聊", format_bool(checkin.deep_conversation)),
                    detail_metric("任务完成", format_bool(checkin.task_completed)),
                ]
                if item
            )
            evidence_cards.extend(
                item
                for item in [
                    detail_card("记录内容", checkin.content, tone="neutral"),
                    detail_card(
                        "情绪标签",
                        ",".join((checkin.mood_tags or {}).get("tags", [])),
                    ),
                ]
                if item
            )

    elif event.entity_type == "report" and event.entity_id:
        report = await db.get(Report, event.entity_id)
        if report:
            content = report.content or {}
            metrics.extend(
                item
                for item in [
                    detail_metric("报告类型", report.type.value),
                    detail_metric("状态", report.status.value),
                    detail_metric("健康分", report.health_score),
                    detail_metric("报告日期", report.report_date.isoformat()),
                ]
                if item
            )
            evidence_cards.extend(
                item
                for item in [
                    detail_card(
                        "核心洞察",
                        content.get("insight")
                        or content.get("self_insight")
                        or content.get("executive_summary"),
                        tone="insight",
                    ),
                    detail_card(
                        "系统建议",
                        content.get("suggestion")
                        or content.get("self_care_tip")
                        or content.get("professional_note"),
                        tone="support",
                    ),
                    detail_card(
                        "鼓励提醒",
                        content.get("encouragement")
                        or content.get("relationship_note"),
                    ),
                ]
                if item
            )

    elif event.entity_type == "relationship_task" and event.entity_id:
        task = await db.get(RelationshipTask, event.entity_id)
        if task:
            metrics.extend(
                item
                for item in [
                    detail_metric("任务类别", task.category),
                    detail_metric("任务状态", task.status.value),
                    detail_metric("截止日期", task.due_date.isoformat()),
                    detail_metric(
                        "完成时间",
                        task.completed_at.isoformat() if task.completed_at else None,
                    ),
                ]
                if item
            )
            evidence_cards.extend(
                item
                for item in [
                    detail_card("任务标题", task.title, tone="progress"),
                    detail_card("任务说明", task.description),
                    detail_card("主观反馈备注", payload.get("note"), tone="support"),
                ]
                if item
            )

    elif event.entity_type == "crisis_alert" and event.entity_id:
        alert = await db.get(CrisisAlert, event.entity_id)
        if alert:
            metrics.extend(
                item
                for item in [
                    detail_metric("风险等级", alert.level.value),
                    detail_metric("预警状态", alert.status.value),
                    detail_metric("关联健康分", alert.health_score),
                ]
                if item
            )
            evidence_cards.extend(
                item
                for item in [
                    detail_card("干预标题", alert.intervention_title, tone="warning"),
                    detail_card("干预说明", alert.intervention_desc),
                    detail_card(
                        "建议动作",
                        "；".join(alert.action_items or []),
                        tone="support",
                    ),
                ]
                if item
            )

    elif event.entity_type == "playbook_transition" and event.entity_id:
        transition = await db.get(PlaybookTransition, event.entity_id)
        if transition:
            metrics.extend(
                item
                for item in [
                    detail_metric("迁移类型", transition.transition_type),
                    detail_metric("触发方式", transition.trigger_type),
                    detail_metric("推进到第几天", transition.to_day),
                    detail_metric("目标分支", transition.to_branch),
                ]
                if item
            )
            evidence_cards.extend(
                item
                for item in [
                    detail_card("迁移说明", transition.trigger_summary, tone="movement"),
                ]
                if item
            )

    elif event.entity_type == "intervention_plan" and event.entity_id:
        plan = await db.get(InterventionPlan, event.entity_id)
        if plan:
            goal = plan.goal_json or {}
            metrics.extend(
                item
                for item in [
                    detail_metric("计划类型", plan.plan_type),
                    detail_metric("风险级别", plan.risk_level),
                    detail_metric("计划状态", plan.status),
                    detail_metric("开始日期", plan.start_date.isoformat()),
                ]
                if item
            )
            evidence_cards.extend(
                item
                for item in [
                    detail_card("主要目标", goal.get("primary_goal"), tone="insight"),
                    detail_card("当前聚焦", "；".join(goal.get("focus", []))),
                ]
                if item
            )

    metrics.extend(
        item
        for item in [
            detail_metric("事件类型", event.event_type),
            detail_metric("事件来源", event.source),
        ]
        if item
    )

    latest_report = await get_latest_completed_report_for_scope(
        db, pair_id=pair_scope_id, user_id=user_scope_id
    )
    latest_report_content = (latest_report.content or {}) if latest_report else {}
    scorecard = await build_intervention_scorecard(
        db, pair_id=pair_scope_id, user_id=user_scope_id
    )
    playbook = await sync_active_playbook_runtime(
        db, pair_id=pair_scope_id, user_id=user_scope_id, viewed=False
    )

    current_context = RelationshipTimelineCurrentContextResponse(
        active_plan_type=(scorecard or {}).get("plan_type"),
        active_branch_label=(playbook or {}).get("active_branch_label"),
        momentum=(scorecard or {}).get("momentum"),
        risk_level=(scorecard or {}).get("risk_now") or (scorecard or {}).get("risk_level"),
        latest_report_insight=(
            latest_report_content.get("insight")
            or latest_report_content.get("self_insight")
            or latest_report_content.get("executive_summary")
        ),
        recommended_next_action=(
            (scorecard or {}).get("next_actions", [None])[0]
            or latest_report_content.get("suggestion")
            or latest_report_content.get("self_care_tip")
        ),
    )
    recommended_next_action = (
        current_context.recommended_next_action
        or payload.get("recommendation_label")
        or payload.get("suggestion")
        or serialized.get("detail")
    )

    return {
        "event": serialized,
        "event_summary": serialized.get("summary"),
        "metrics": [RelationshipTimelineMetricResponse(**item) for item in metrics],
        "evidence_cards": [
            RelationshipTimelineEvidenceCardResponse(**item)
            for item in evidence_cards
        ],
        "impact_modules": _timeline_impact_modules_for_event(event),
        "recommended_next_action": recommended_next_action,
        "current_context": current_context,
    }


@router.get(
    "/timeline",
    response_model=RelationshipTimelineResponse,
)
async def get_relationship_timeline(
    pair_id: str | None = None,
    mode: str | None = None,
    limit: int = 24,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )
    bounded_limit = max(6, min(limit, 60))
    result = await db.execute(
        select(RelationshipEvent)
        .where(
            *event_scope_query(pair_scope_id, user_scope_id),
            RelationshipEvent.event_type.not_like("%.viewed"),
        )
        .order_by(
            RelationshipEvent.occurred_at.desc(),
            RelationshipEvent.created_at.desc(),
        )
        .limit(bounded_limit)
    )
    events = result.scalars().all()
    serialized_events = [serialize_timeline_event(event) for event in events]
    highlights = [item["summary"] for item in serialized_events[:3]]

    await record_relationship_event(
        db,
        event_type="timeline.viewed",
        pair_id=pair_scope_id,
        user_id=user.id if pair_scope_id else user_scope_id,
        entity_type="relationship_timeline",
        entity_id=f"{pair_scope_id or user_scope_id}",
        payload={
            "scope": "pair" if pair_scope_id else "solo",
            "limit": bounded_limit,
            "event_count": len(serialized_events),
        },
    )
    await db.commit()

    return RelationshipTimelineResponse(
        scope="pair" if pair_scope_id else "solo",
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        event_count=len(serialized_events),
        latest_event_at=events[0].occurred_at if events else None,
        highlights=highlights,
        events=serialized_events,
    )


@router.get(
    "/timeline/events/{event_id}",
    response_model=RelationshipTimelineEventDetailResponse,
)
async def get_relationship_timeline_event_detail(
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = await get_accessible_timeline_event(db, event_id=event_id, user=user)
    detail = await build_timeline_event_detail(db, event)

    await record_relationship_event(
        db,
        event_type="timeline.event_detail_viewed",
        pair_id=str(event.pair_id) if event.pair_id else None,
        user_id=user.id if event.pair_id else event.user_id,
        entity_type="relationship_event",
        entity_id=event.id,
        payload={
            "event_type": event.event_type,
            "entity_type": event.entity_type,
        },
        idempotency_key=f"timeline-detail:{event.id}:{user.id}",
    )
    await db.commit()
    return RelationshipTimelineEventDetailResponse(**detail)
