"""Relationship intelligence helpers.

This module adds a lightweight event stream and profile-snapshot layer on top of
the existing domain tables, so reports, tasks, and the agent can share the same
derived understanding of a relationship instead of each re-deriving it ad hoc.
"""

import uuid
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from statistics import mean

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Checkin,
    CrisisAlert,
    InterventionPlan,
    Pair,
    RelationshipEvent,
    RelationshipProfileSnapshot,
    RelationshipTask,
    Report,
    ReportStatus,
    TaskStatus,
    LongDistanceActivity,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _require_uuid(value: uuid.UUID | None) -> uuid.UUID:
    if value is None:
        raise ValueError("expected normalized uuid")
    return value


def _avg(values: Sequence[int | float]) -> float | None:
    if not values:
        return None
    return round(float(mean(values)), 2)


def _rate(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(part / total, 4)


def _stability(values: Sequence[int | float], *, scale: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return 1.0
    deltas = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    avg_delta = sum(deltas) / len(deltas)
    return round(max(0.0, 1.0 - (avg_delta / max(scale, 1.0))), 4)


def _date_window(snapshot_date: date, window_days: int) -> tuple[date, date]:
    start = snapshot_date - timedelta(days=max(window_days - 1, 0))
    return start, snapshot_date


async def record_relationship_event(
    db: AsyncSession,
    *,
    event_type: str,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | uuid.UUID | None = None,
    source: str = "system",
    payload: dict | None = None,
    idempotency_key: str | None = None,
    occurred_at: datetime | None = None,
) -> RelationshipEvent:
    """Persist a normalized relationship event and dedupe on idempotency key."""

    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    normalized_entity_id = str(entity_id) if entity_id is not None else None

    if (
        normalized_pair_id is None
        and normalized_user_id is None
        and not str(event_type).startswith("privacy.")
    ):
        raise ValueError("record_relationship_event requires pair_id or user_id")

    if idempotency_key:
        result = await db.execute(
            select(RelationshipEvent).where(
                RelationshipEvent.idempotency_key == idempotency_key
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

    event = RelationshipEvent(
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=normalized_entity_id,
        source=source,
        payload=payload,
        idempotency_key=idempotency_key,
        occurred_at=occurred_at or _utcnow(),
    )
    db.add(event)
    await db.flush()
    return event


async def refresh_profile_snapshot(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
    window_days: int = 7,
    snapshot_date: date | None = None,
    version: str = "v1",
) -> RelationshipProfileSnapshot:
    """Rebuild a scope's latest profile snapshot from current business tables."""

    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)

    if (normalized_pair_id is None) == (normalized_user_id is None):
        raise ValueError("refresh_profile_snapshot requires exactly one scope")

    resolved_snapshot_date = snapshot_date or date.today()
    start_date, end_date = _date_window(resolved_snapshot_date, window_days)

    if normalized_pair_id:
        (
            metrics,
            risk_summary,
            attachment_summary,
            suggested_focus,
        ) = await _build_pair_profile(
            db,
            pair_id=normalized_pair_id,
            start_date=start_date,
            end_date=end_date,
            window_days=window_days,
        )
        latest_event_at = await _get_latest_event_at(db, pair_id=normalized_pair_id)
    else:
        assert normalized_user_id is not None
        (
            metrics,
            risk_summary,
            attachment_summary,
            suggested_focus,
        ) = await _build_user_profile(
            db,
            user_id=_require_uuid(normalized_user_id),
            start_date=start_date,
            end_date=end_date,
            window_days=window_days,
        )
        latest_event_at = await _get_latest_event_at(
            db, user_id=normalized_user_id, solo_only=True
        )

    result = await db.execute(
        select(RelationshipProfileSnapshot).where(
            RelationshipProfileSnapshot.pair_id == normalized_pair_id,
            RelationshipProfileSnapshot.user_id == normalized_user_id,
            RelationshipProfileSnapshot.window_days == window_days,
            RelationshipProfileSnapshot.snapshot_date == resolved_snapshot_date,
            RelationshipProfileSnapshot.version == version,
        )
    )
    snapshot = result.scalar_one_or_none()

    if snapshot:
        snapshot.metrics_json = metrics
        snapshot.risk_summary = risk_summary
        snapshot.attachment_summary = attachment_summary
        snapshot.suggested_focus = {"items": suggested_focus}
        snapshot.generated_from_event_at = latest_event_at
    else:
        snapshot = RelationshipProfileSnapshot(
            pair_id=normalized_pair_id,
            user_id=normalized_user_id,
            window_days=window_days,
            snapshot_date=resolved_snapshot_date,
            metrics_json=metrics,
            risk_summary=risk_summary,
            attachment_summary=attachment_summary,
            suggested_focus={"items": suggested_focus},
            generated_from_event_at=latest_event_at,
            version=version,
        )
        db.add(snapshot)

    await db.flush()
    return snapshot


async def maybe_create_intervention_plan(
    db: AsyncSession,
    *,
    snapshot: RelationshipProfileSnapshot,
) -> InterventionPlan | None:
    """Create a lightweight active plan when the latest snapshot crosses a threshold."""

    metrics = snapshot.metrics_json or {}
    risk_summary = snapshot.risk_summary or {}
    current_level = str(risk_summary.get("current_level") or "none")
    plan_type: str | None = None
    risk_level = current_level
    goal_json: dict | None = None

    if snapshot.pair_id:
        pair = await db.get(Pair, snapshot.pair_id)
        overlap = float(metrics.get("interaction_overlap_rate") or 0.0)
        crisis_count = int(metrics.get("crisis_event_count") or 0)
        long_distance_rate = float(metrics.get("long_distance_activity_rate") or 0.0)
        high_risk_message_count = int(
            metrics.get("message_simulation_high_risk_count") or 0
        )
        low_alignment_count = int(metrics.get("alignment_low_score_count") or 0)

        if (
            current_level in ("moderate", "severe")
            or crisis_count >= 2
            or high_risk_message_count >= 2
            or low_alignment_count >= 2
        ):
            plan_type = "conflict_repair_plan"
            goal_json = {
                "primary_goal": "降低沟通升级风险，恢复安全沟通",
                "focus": ["减少升级", "先对齐版本", "建立修复窗口"],
            }
            if current_level == "none":
                risk_level = "mild"
            else:
                risk_level = current_level
        elif overlap < 0.3:
            plan_type = "low_connection_recovery"
            goal_json = {
                "primary_goal": "恢复连接感与共同节奏",
                "focus": ["提高同日互动", "增加轻量联系", "恢复深聊"],
            }
            risk_level = "mild"
        elif pair and pair.is_long_distance and long_distance_rate < 0.2:
            plan_type = "distance_compensation_plan"
            goal_json = {
                "primary_goal": "补偿异地互动稀薄期",
                "focus": ["安排固定视频", "共同活动", "表达确认"],
            }
            risk_level = "mild"
    else:
        mood_avg = metrics.get("mood_avg")
        mood_stability = metrics.get("mood_stability")
        if (
            mood_avg is not None
            and mood_avg < 4.5
            and (mood_stability is None or mood_stability < 0.6)
        ):
            plan_type = "self_regulation_plan"
            goal_json = {
                "primary_goal": "先把自己的节奏稳住",
                "focus": ["情绪识别", "低成本自我照顾", "表达练习"],
            }
            risk_level = "mild"

    if not plan_type:
        return None

    result = await db.execute(
        select(InterventionPlan).where(
            InterventionPlan.pair_id == snapshot.pair_id,
            InterventionPlan.user_id == snapshot.user_id,
            InterventionPlan.plan_type == plan_type,
            InterventionPlan.status == "active",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    plan = InterventionPlan(
        pair_id=snapshot.pair_id,
        user_id=snapshot.user_id,
        plan_type=plan_type,
        trigger_snapshot_id=snapshot.id,
        risk_level=risk_level,
        goal_json=goal_json,
        status="active",
        start_date=snapshot.snapshot_date,
        end_date=snapshot.snapshot_date + timedelta(days=6),
        owner_version=snapshot.version,
    )
    db.add(plan)
    await db.flush()
    return plan


async def refresh_profile_and_plan(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
    window_days: int = 7,
    snapshot_date: date | None = None,
    version: str = "v1",
) -> tuple[RelationshipProfileSnapshot, InterventionPlan | None]:
    """Convenience helper used by business flows after writing important events."""

    snapshot = await refresh_profile_snapshot(
        db,
        pair_id=pair_id,
        user_id=user_id,
        window_days=window_days,
        snapshot_date=snapshot_date,
        version=version,
    )
    plan = await maybe_create_intervention_plan(db, snapshot=snapshot)
    if plan:
        from app.services.playbook_runtime import sync_active_playbook_runtime

        await sync_active_playbook_runtime(
            db,
            pair_id=pair_id,
            user_id=user_id,
            viewed=False,
        )
    return snapshot, plan


async def _get_latest_event_at(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    solo_only: bool = False,
) -> datetime | None:
    query = select(func.max(RelationshipEvent.occurred_at))
    if pair_id:
        query = query.where(RelationshipEvent.pair_id == pair_id)
    if user_id:
        query = query.where(RelationshipEvent.user_id == user_id)
    if solo_only:
        query = query.where(RelationshipEvent.pair_id.is_(None))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def _build_pair_profile(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID,
    start_date: date,
    end_date: date,
    window_days: int,
) -> tuple[dict, dict, dict, list[str]]:
    pair = await db.get(Pair, pair_id)
    if not pair:
        raise ValueError("pair not found for profile snapshot")

    checkin_result = await db.execute(
        select(Checkin)
        .where(
            Checkin.pair_id == pair_id,
            Checkin.checkin_date >= start_date,
            Checkin.checkin_date <= end_date,
        )
        .order_by(Checkin.checkin_date.asc(), Checkin.created_at.asc())
    )
    checkins = checkin_result.scalars().all()

    report_result = await db.execute(
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.status == ReportStatus.COMPLETED,
            Report.report_date >= start_date,
            Report.report_date <= end_date,
            Report.health_score.isnot(None),
        )
        .order_by(Report.report_date.asc())
    )
    reports = report_result.scalars().all()

    crisis_result = await db.execute(
        select(CrisisAlert)
        .where(
            CrisisAlert.pair_id == pair_id,
            func.date(CrisisAlert.created_at) >= start_date,
            func.date(CrisisAlert.created_at) <= end_date,
        )
        .order_by(CrisisAlert.created_at.asc())
    )
    crisis_alerts = crisis_result.scalars().all()

    task_result = await db.execute(
        select(RelationshipTask).where(
            RelationshipTask.pair_id == pair_id,
            RelationshipTask.due_date >= start_date,
            RelationshipTask.due_date <= end_date,
        )
    )
    tasks = task_result.scalars().all()

    activity_result = await db.execute(
        select(LongDistanceActivity).where(
            LongDistanceActivity.pair_id == pair_id,
            func.date(LongDistanceActivity.created_at) >= start_date,
            func.date(LongDistanceActivity.created_at) <= end_date,
        )
    )
    activities = activity_result.scalars().all()

    event_result = await db.execute(
        select(RelationshipEvent)
        .where(
            RelationshipEvent.pair_id == pair_id,
            func.date(RelationshipEvent.occurred_at) >= start_date,
            func.date(RelationshipEvent.occurred_at) <= end_date,
            RelationshipEvent.event_type == "message.simulated",
        )
        .order_by(RelationshipEvent.occurred_at.asc())
    )
    message_simulations = event_result.scalars().all()

    alignment_result = await db.execute(
        select(RelationshipEvent)
        .where(
            RelationshipEvent.pair_id == pair_id,
            func.date(RelationshipEvent.occurred_at) >= start_date,
            func.date(RelationshipEvent.occurred_at) <= end_date,
            RelationshipEvent.event_type == "alignment.generated",
        )
        .order_by(RelationshipEvent.occurred_at.asc())
    )
    alignments = alignment_result.scalars().all()

    checkins_a = [c for c in checkins if str(c.user_id) == str(pair.user_a_id)]
    checkins_b = [c for c in checkins if str(c.user_id) == str(pair.user_b_id)]

    moods_a = [c.mood_score for c in checkins_a if c.mood_score is not None]
    moods_b = [c.mood_score for c in checkins_b if c.mood_score is not None]

    dates_a = {c.checkin_date for c in checkins_a}
    dates_b = {c.checkin_date for c in checkins_b}
    dual_checkin_days = len(dates_a & dates_b)

    mood_map_a = {
        c.checkin_date: c.mood_score for c in checkins_a if c.mood_score is not None
    }
    mood_map_b = {
        c.checkin_date: c.mood_score for c in checkins_b if c.mood_score is not None
    }
    shared_dates = sorted(set(mood_map_a) & set(mood_map_b))
    mood_gaps = [abs(mood_map_a[d] - mood_map_b[d]) for d in shared_dates]

    initiative_a = 0
    initiative_b = 0
    initiative_equal = 0
    for checkin in checkins:
        if checkin.interaction_initiative == "equal":
            initiative_equal += 1
        elif checkin.interaction_initiative == "me":
            if str(checkin.user_id) == str(pair.user_a_id):
                initiative_a += 1
            else:
                initiative_b += 1
        elif checkin.interaction_initiative == "partner":
            if str(checkin.user_id) == str(pair.user_a_id):
                initiative_b += 1
            else:
                initiative_a += 1

    initiative_total = initiative_a + initiative_b + initiative_equal
    completed_tasks = sum(1 for task in tasks if task.status == TaskStatus.COMPLETED)
    completed_activities = sum(
        1 for activity in activities if activity.status == "completed"
    )
    simulation_risks = [
        str((event.payload or {}).get("risk_level") or "medium")
        for event in message_simulations
    ]
    simulation_high_risk_count = sum(1 for risk in simulation_risks if risk == "high")
    simulation_medium_risk_count = sum(
        1 for risk in simulation_risks if risk == "medium"
    )
    latest_simulation_goal = next(
        (
            str((event.payload or {}).get("conversation_goal") or "")
            for event in reversed(message_simulations)
            if (event.payload or {}).get("conversation_goal")
        ),
        None,
    )
    alignment_scores = []
    for event in alignments:
        score = (event.payload or {}).get("alignment_score")
        if score is None:
            continue
        try:
            alignment_scores.append(float(score))
        except (TypeError, ValueError):
            continue
    alignment_low_score_count = sum(1 for score in alignment_scores if score < 55)
    latest_alignment_opening = next(
        (
            str((event.payload or {}).get("suggested_opening") or "")
            for event in reversed(alignments)
            if (event.payload or {}).get("suggested_opening")
        ),
        None,
    )
    latest_alignment_bridge = next(
        (
            str(((event.payload or {}).get("bridge_actions") or [None])[0] or "")
            for event in reversed(alignments)
            if (event.payload or {}).get("bridge_actions")
        ),
        None,
    )

    latest_crisis = crisis_alerts[-1] if crisis_alerts else None
    current_level = latest_crisis.level.value if latest_crisis else "none"

    metrics = {
        "window_days": window_days,
        "checkin_count": len(checkins),
        "dual_checkin_days": dual_checkin_days,
        "mood_avg_a": _avg(moods_a),
        "mood_avg_b": _avg(moods_b),
        "mood_gap_avg": _avg(mood_gaps),
        "mood_stability_a": _stability(moods_a, scale=10.0),
        "mood_stability_b": _stability(moods_b, scale=10.0),
        "deep_conversation_rate": _rate(
            sum(1 for checkin in checkins if checkin.deep_conversation), len(checkins)
        ),
        "interaction_overlap_rate": _rate(dual_checkin_days, window_days),
        "initiative_a_rate": _rate(initiative_a, initiative_total),
        "initiative_b_rate": _rate(initiative_b, initiative_total),
        "initiative_equal_rate": _rate(initiative_equal, initiative_total),
        "task_completion_rate": _rate(completed_tasks, len(tasks)),
        "crisis_event_count": len(crisis_alerts),
        "long_distance_activity_rate": _rate(completed_activities, len(activities)),
        "message_simulation_count": len(message_simulations),
        "message_simulation_high_risk_count": simulation_high_risk_count,
        "message_simulation_medium_risk_count": simulation_medium_risk_count,
        "last_simulation_goal": latest_simulation_goal,
        "alignment_generation_count": len(alignments),
        "alignment_avg_score": _avg(alignment_scores),
        "alignment_low_score_count": alignment_low_score_count,
        "last_alignment_opening": latest_alignment_opening,
        "last_alignment_bridge": latest_alignment_bridge,
        "report_health_avg": _avg(
            [
                report.health_score
                for report in reports
                if report.health_score is not None
            ]
        ),
    }

    if current_level in ("moderate", "severe") or len(crisis_alerts) >= 2:
        trend = "elevated"
    elif current_level == "mild" or metrics["interaction_overlap_rate"] < 0.3:
        trend = "watch"
    else:
        trend = "stable"

    risk_summary = {
        "current_level": current_level,
        "crisis_events_window": len(crisis_alerts),
        "trend": trend,
    }
    attachment_summary = {
        "attachment_a": pair.attachment_style_a or "unknown",
        "attachment_b": pair.attachment_style_b or "unknown",
        "is_long_distance": bool(pair.is_long_distance),
    }

    suggested_focus: list[str] = []
    if simulation_high_risk_count >= 1:
        suggested_focus.append("practice_softened_startup")
    if len(message_simulations) >= 2:
        suggested_focus.append("message_rehearsal_before_sending")
    if alignment_low_score_count >= 1:
        suggested_focus.append("align_narratives_before_solving")
    if metrics["interaction_overlap_rate"] < 0.3:
        suggested_focus.append("increase_shared_checkins")
    if metrics["deep_conversation_rate"] < 0.3:
        suggested_focus.append("create_deep_conversation_window")
    if len(tasks) > 0 and metrics["task_completion_rate"] < 0.4:
        suggested_focus.append("reduce_task_friction")
    if len(crisis_alerts) >= 2:
        suggested_focus.append("conflict_repair")
    if pair.is_long_distance and metrics["long_distance_activity_rate"] < 0.2:
        suggested_focus.append("distance_compensation")

    return metrics, risk_summary, attachment_summary, suggested_focus[:3]


async def _build_user_profile(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
    window_days: int,
) -> tuple[dict, dict, dict, list[str]]:
    checkin_result = await db.execute(
        select(Checkin)
        .where(
            Checkin.user_id == user_id,
            Checkin.pair_id.is_(None),
            Checkin.checkin_date >= start_date,
            Checkin.checkin_date <= end_date,
        )
        .order_by(Checkin.checkin_date.asc(), Checkin.created_at.asc())
    )
    checkins = checkin_result.scalars().all()

    report_result = await db.execute(
        select(Report)
        .where(
            Report.user_id == user_id,
            Report.pair_id.is_(None),
            Report.status == ReportStatus.COMPLETED,
            Report.report_date >= start_date,
            Report.report_date <= end_date,
            Report.health_score.isnot(None),
        )
        .order_by(Report.report_date.asc())
    )
    reports = report_result.scalars().all()

    moods = [
        checkin.mood_score for checkin in checkins if checkin.mood_score is not None
    ]
    interaction_freq = [
        checkin.interaction_freq
        for checkin in checkins
        if checkin.interaction_freq is not None
    ]

    metrics = {
        "window_days": window_days,
        "checkin_count": len(checkins),
        "mood_avg": _avg(moods),
        "mood_stability": _stability(moods, scale=10.0),
        "deep_conversation_rate": _rate(
            sum(1 for checkin in checkins if checkin.deep_conversation), len(checkins)
        ),
        "interaction_freq_avg": _avg(interaction_freq),
        "report_health_avg": _avg(
            [
                report.health_score
                for report in reports
                if report.health_score is not None
            ]
        ),
        "crisis_event_count": 0,
        "task_completion_rate": 0.0,
    }

    mood_avg = metrics.get("mood_avg")
    if mood_avg is not None and mood_avg < 4.5:
        trend = "watch"
    else:
        trend = "stable"

    risk_summary = {
        "current_level": "none",
        "crisis_events_window": 0,
        "trend": trend,
    }
    attachment_summary = {
        "attachment_a": "unknown",
        "attachment_b": "unknown",
        "is_long_distance": False,
    }

    suggested_focus: list[str] = []
    if mood_avg is not None and mood_avg < 4.5:
        suggested_focus.append("stabilize_self_rhythm")
    if metrics["deep_conversation_rate"] < 0.3:
        suggested_focus.append("practice_honest_reflection")

    return metrics, risk_summary, attachment_summary, suggested_focus[:3]
