"""Timeline insight routes."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, validate_pair_access
from app.core.time import current_local_date, utc_naive_to_local_datetime
from app.core.database import get_db
from app.models import (
    Checkin,
    CrisisAlert,
    InterventionPlan,
    PlaybookTransition,
    RelationshipEvent,
    RelationshipTask,
    Report,
    ReportStatus,
    ReportType,
    User,
)
from app.schemas import (
    RelationshipTimelineCurrentContextResponse,
    RelationshipTimelineArchiveItemResponse,
    RelationshipTimelineArchiveResponse,
    RelationshipTimelineEventDetailResponse,
    RelationshipTimelineEvidenceCardResponse,
    RelationshipTimelineMetricResponse,
    RelationshipTimelineResponse,
)
from app.services.intervention_effectiveness import build_intervention_scorecard
from app.services.playbook_runtime import sync_active_playbook_runtime
from app.services.relationship_intelligence import record_relationship_event
from app.services.display_labels import (
    decision_feedback_label,
    plan_type_label,
    report_type_label,
    risk_level_label,
    status_label,
    task_category_label,
)
from app.services.timeline_archive import (
    list_archive_checkins,
    list_archive_reports,
    merge_archive_items,
    parse_archive_cursor,
)

from .shared import (
    detail_card,
    detail_metric,
    event_scope_query,
    format_bool,
    get_latest_completed_report_for_scope,
    resolve_scope,
    serialize_timeline_event,
    timeline_branch_label,
    timeline_event_label,
    timeline_source_label,
    timeline_transition_type_label,
    timeline_trigger_type_label,
)

router = APIRouter(tags=["关系智能"])

TIMELINE_HIDDEN_EVENT_TYPES = (
    "message.simulated",
    "message.feedback_submitted",
    "decision.feedback_submitted",
)


def _is_owner_private_event(event: RelationshipEvent) -> bool:
    event_type = str(event.event_type or "").strip()
    return event_type.startswith("privacy.") or event_type in TIMELINE_HIDDEN_EVENT_TYPES


async def get_accessible_timeline_event(
    db: AsyncSession, *, event_id: str, user: User
) -> RelationshipEvent:
    event = await db.get(RelationshipEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="时间轴节点不存在")

    if _is_owner_private_event(event):
        if event.user_id and str(event.user_id) == str(user.id):
            return event
        raise HTTPException(status_code=404, detail="时间轴节点不存在")

    if event.pair_id:
        await validate_pair_access(str(event.pair_id), user, db, require_active=False)
        if event.entity_type == "checkin" and event.entity_id:
            checkin = await db.get(Checkin, event.entity_id)
            if not checkin or (str(checkin.user_id) != str(user.id) and (
                checkin.raw_deleted_at is not None or checkin.visibility_scope != "shared_summary"
            )):
                raise HTTPException(status_code=404, detail="时间轴节点不存在")
        if event.entity_type == "report" and event.entity_id:
            report = await db.get(Report, event.entity_id)
            if report and report.type == ReportType.SOLO and str(report.user_id) != str(user.id):
                raise HTTPException(status_code=404, detail="时间轴节点不存在")
        elif event.entity_type == "relationship_task" and event.entity_id:
            task = await db.get(RelationshipTask, event.entity_id)
            if task and task.user_id is not None and str(task.user_id) != str(user.id):
                raise HTTPException(status_code=404, detail="时间轴节点不存在")
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
        modules.extend(["消息预演", "表达建议", "反馈闭环"])
    if event_type.startswith("alignment.") or entity_type == "narrative_alignment":
        modules.extend(["双视角对齐", "沟通桥接", "反馈闭环"])
    if event_type.startswith("crisis.") or event_type.startswith("repair_protocol."):
        modules.extend(["风险状态", "修复方案"])
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
    db: AsyncSession, event: RelationshipEvent, *, viewer: User
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
            is_owner = checkin.user_id is None or str(checkin.user_id) == str(viewer.id)
            if is_owner:
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
            else:
                scrubbed_payload = dict(serialized.get("payload") or {})
                scrubbed_payload.pop("text_preview", None)
                scrubbed_payload.pop("client_context", None)
                serialized["payload"] = scrubbed_payload or None
                evidence_cards.append(
                    detail_card(
                        "记录内容",
                        "对方在这天也留下了一条记录。原文和原媒体默认仅记录者本人可见。",
                        tone="neutral",
                    )
                )

    elif event.entity_type == "report" and event.entity_id:
        report = await db.get(Report, event.entity_id)
        if report and (report.type != ReportType.SOLO or str(report.user_id) == str(viewer.id)):
            content = report.content or {}
            metrics.extend(
                item
                for item in [
                    detail_metric("报告类型", report_type_label(report.type.value)),
                    detail_metric("状态", status_label(report.status.value)),
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
        if task and (task.user_id is None or str(task.user_id) == str(viewer.id)):
            completed_local = utc_naive_to_local_datetime(task.completed_at)
            metrics.extend(
                item
                for item in [
                    detail_metric("任务类别", task_category_label(task.category)),
                    detail_metric("任务状态", status_label(task.status.value)),
                    detail_metric("截止日期", task.due_date.isoformat()),
                    detail_metric(
                        "完成时间",
                        completed_local.strftime("%Y-%m-%d %H:%M") if completed_local else None,
                    ),
                ]
                if item
            )
            evidence_cards.extend(
                item
                for item in [
                    detail_card("任务标题", task.title, tone="progress"),
                    detail_card("任务说明", task.description),
                    detail_card("后来怎么样", {'helped': '有帮助', 'not_yet': '还没做', 'difficult': '不太顺'}.get(payload.get('outcome')), tone="support"),
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
                    detail_metric("风险等级", risk_level_label(alert.level.value)),
                    detail_metric("预警状态", status_label(alert.status.value)),
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
                    detail_metric("变更类型", timeline_transition_type_label(transition.transition_type)),
                    detail_metric("触发方式", timeline_trigger_type_label(transition.trigger_type)),
                    detail_metric("推进到第几天", transition.to_day),
                    detail_metric("当前节奏", timeline_branch_label(transition.to_branch)),
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
                    detail_metric("计划类型", plan_type_label(plan.plan_type)),
                    detail_metric("风险级别", risk_level_label(plan.risk_level)),
                    detail_metric("计划状态", status_label(plan.status)),
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

    elif event.event_type == "assessment.weekly_submitted" or event.entity_type == "weekly_assessment":
        total_score = payload.get("total_score")
        scope_text = "双人关系" if payload.get("scope") == "pair" else "自我回看"
        metrics.extend(
            item
            for item in [
                detail_metric("体检范围", scope_text),
                detail_metric("综合分", f"{total_score}/100" if total_score is not None else None),
            ]
            if item
        )
        for dimension in payload.get("dimension_scores") or []:
            if isinstance(dimension, dict) and dimension.get("label") and dimension.get("score") is not None:
                metric = detail_metric(str(dimension["label"]), f"{dimension['score']} 分")
                if metric:
                    metrics.append(metric)
        change_summary = payload.get("change_summary")
        if change_summary:
            evidence_cards.append(detail_card("变化说明", change_summary, tone="insight"))

    elif event.event_type in {"message.feedback_submitted", "alignment.feedback_submitted", "decision.feedback_submitted"}:
        feedback_text = payload.get("feedback_label") or (
            decision_feedback_label(payload.get("feedback_type"))
            if payload.get("feedback_type")
            else None
        )
        target_event_text = (
            timeline_event_label(str(payload.get("target_event_type")))
            if payload.get("target_event_type")
            else None
        )
        metrics.extend(
            item
            for item in [
                detail_metric("反馈类型", feedback_text),
                detail_metric("关联事件", target_event_text),
            ]
            if item
        )
        evidence_cards.extend(
            item
            for item in [
                detail_card("反馈备注", payload.get("note"), tone="support"),
                detail_card("反馈记录", feedback_text, tone="progress"),
            ]
            if item
        )

    metrics.extend(
        item
        for item in [
            detail_metric("事件类型", timeline_event_label(event.event_type)),
            detail_metric("记录来源", timeline_source_label(event.source)),
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


async def _load_archive_items(
    db: AsyncSession,
    *,
    pair_scope_id: str | None,
    user_scope_id: str | None,
    actor_user_id,
    limit: int,
    before: str | None = None,
    export_mode: bool = False,
) -> tuple[list[dict], str | None]:
    try:
        before_at, before_seen_ids = parse_archive_cursor(before)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="归档分页游标无效") from exc
    checkins = await list_archive_checkins(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        actor_user_id=actor_user_id,
        before_at=before_at,
        before_seen_ids=before_seen_ids,
        limit=limit,
        export_mode=export_mode,
    )
    reports = await list_archive_reports(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        actor_user_id=actor_user_id,
        before_at=before_at,
        before_seen_ids=before_seen_ids,
        limit=limit,
        export_mode=export_mode,
    )
    return merge_archive_items(
        checkins=checkins,
        reports=reports,
        actor_user_id=actor_user_id,
        limit=None if export_mode else limit,
        incoming_cursor=before,
    )


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
            RelationshipEvent.event_type.not_like("privacy.%"),
            RelationshipEvent.event_type.not_in(TIMELINE_HIDDEN_EVENT_TYPES),
        )
        .order_by(
            RelationshipEvent.occurred_at.desc(),
            RelationshipEvent.created_at.desc(),
        )
        .limit(bounded_limit)
    )
    raw_events = result.scalars().all()
    report_ids = [
        e.entity_id for e in raw_events if e.entity_type == "report" and e.entity_id
    ]
    task_ids = [
        e.entity_id for e in raw_events if e.entity_type == "relationship_task" and e.entity_id
    ]
    hidden_report_ids: set[str] = set()
    if report_ids:
        rep_rows = (await db.execute(select(Report).where(Report.id.in_(report_ids)))).scalars().all()
        hidden_report_ids = {
            str(r.id)
            for r in rep_rows
            if r.type == ReportType.SOLO and str(r.user_id) != str(user.id)
        }
    hidden_task_ids: set[str] = set()
    if task_ids:
        task_rows = (
            await db.execute(select(RelationshipTask).where(RelationshipTask.id.in_(task_ids)))
        ).scalars().all()
        hidden_task_ids = {
            str(t.id)
            for t in task_rows
            if t.user_id is not None and str(t.user_id) != str(user.id)
        }
    events = [
        e
        for e in raw_events
        if not (
            (e.entity_type == "report" and e.entity_id and str(e.entity_id) in hidden_report_ids)
            or (
                e.entity_type == "relationship_task"
                and e.entity_id
                and str(e.entity_id) in hidden_task_ids
            )
        )
    ]
    serialized_events = []
    for event in events:
        item = serialize_timeline_event(event)
        if event.entity_type == "checkin" and str(event.user_id) != str(user.id):
            checkin = await db.get(Checkin, event.entity_id) if event.entity_id else None
            if not checkin or checkin.raw_deleted_at is not None or checkin.visibility_scope != "shared_summary":
                continue
            item["payload"] = None
        serialized_events.append(item)
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
    "/timeline/archive",
    response_model=RelationshipTimelineArchiveResponse,
)
async def get_relationship_timeline_archive(
    pair_id: str | None = None,
    mode: str | None = None,
    limit: int = Query(default=24, ge=6, le=60),
    before: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id,
        mode=mode,
        user=user,
        db=db,
    )
    items, next_before = await _load_archive_items(
        db,
        pair_scope_id=pair_scope_id,
        user_scope_id=user_scope_id,
        actor_user_id=user.id,
        limit=max(6, min(limit, 60)),
        before=before,
    )

    return RelationshipTimelineArchiveResponse(
        scope="pair" if pair_scope_id else "solo",
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        item_count=len(items),
        latest_item_at=items[0]["occurred_at"] if items else None,
        next_before=next_before,
        items=items,
    )


@router.get("/timeline/archive/items/{item_id}/export")
async def export_relationship_timeline_archive_item(
    item_id: str,
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id,
        mode=mode,
        user=user,
        db=db,
    )
    items, _ = await _load_archive_items(
        db,
        pair_scope_id=pair_scope_id,
        user_scope_id=user_scope_id,
        actor_user_id=user.id,
        limit=60,
        export_mode=True,
    )
    item = next((candidate for candidate in items if str(candidate["id"]) == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="归档条目不存在")
    if item.get("item_type") == "partner_record_placeholder":
        raise HTTPException(status_code=403, detail="该条档案不可导出")

    safe_item = RelationshipTimelineArchiveItemResponse(**item)
    response = JSONResponse(content=jsonable_encoder(safe_item))
    response.headers["Content-Disposition"] = (
        f'attachment; filename="qinjian-archive-{item_id}.json"'
    )
    return response


@router.get("/timeline/archive/export")
async def export_relationship_timeline_archive(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id,
        mode=mode,
        user=user,
        db=db,
    )
    items, _ = await _load_archive_items(
        db,
        pair_scope_id=pair_scope_id,
        user_scope_id=user_scope_id,
        actor_user_id=user.id,
        limit=60,
        export_mode=True,
    )
    safe_items = [RelationshipTimelineArchiveItemResponse(**item) for item in items]
    scope = "pair" if pair_scope_id else "solo"
    payload = {
        "scope": scope,
        "pair_id": pair_scope_id,
        "user_id": user_scope_id,
        "item_count": len(safe_items),
        "exported_at": datetime.now(timezone.utc),
        "items": safe_items,
    }
    response = JSONResponse(content=jsonable_encoder(payload))
    response.headers["Content-Disposition"] = (
        f'attachment; filename="qinjian-{scope}-archive-{current_local_date().isoformat()}.json"'
    )
    return response


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
    detail = await build_timeline_event_detail(db, event, viewer=user)

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
