"""Intervention effect scorecard builder."""

import uuid
from datetime import date

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    InterventionPlan,
    RelationshipEvent,
    RelationshipProfileSnapshot,
    RelationshipTask,
    Report,
    ReportStatus,
    TaskStatus,
)
from app.core.time import current_local_date
from app.services.task_feedback import summarize_feedback_map

RISK_ORDER = {
    "none": 0,
    "mild": 1,
    "moderate": 2,
    "severe": 3,
}


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _scope_filters(model, *, pair_id: uuid.UUID | None, user_id: uuid.UUID | None):
    if pair_id:
        return [
            model.pair_id == pair_id,
            getattr(model, "user_id", None).is_(None)
            if hasattr(model, "user_id")
            else True,
        ]
    return [
        model.user_id == user_id,
        model.pair_id.is_(None),
    ]


def _risk_rank(level: str | None) -> int:
    return RISK_ORDER.get(str(level or "none"), 0)


def _derive_momentum(
    *,
    completion_rate: float,
    health_delta: float | None,
    risk_before: str | None,
    risk_now: str | None,
    duration_days: int,
) -> str:
    if duration_days <= 2 and completion_rate == 0 and health_delta is None:
        return "early"
    if (
        _risk_rank(risk_now) < _risk_rank(risk_before)
        or (health_delta is not None and health_delta >= 5)
        or completion_rate >= 0.67
    ):
        return "improving"
    if duration_days >= 4 and completion_rate < 0.25 and (
        health_delta is None or health_delta <= 0
    ):
        return "stalled"
    return "mixed"


def _plan_actions(plan_type: str | None) -> list[str]:
    return {
        "low_connection_recovery": [
            "先完成一个 10 分钟低压力连接动作",
            "把任务拆成今晚就能做完的一步",
            "优先恢复稳定节奏，不急着谈所有问题",
        ],
        "conflict_repair_plan": [
            "先降温，再进入结构化修复对话",
            "一次只处理一个核心冲突点",
            "在 24 小时内复盘哪句表达最容易升级",
        ],
        "distance_compensation_plan": [
            "先固定一次可兑现的远程陪伴动作",
            "把联系从随机改成有节奏",
            "用共同活动替代纯信息交换",
        ],
        "self_regulation_plan": [
            "先把任务改成更轻的自我调节动作",
            "先稳定情绪节律，再要求自己输出更多",
            "记录哪种自我照顾最容易坚持",
        ],
    }.get(
        plan_type,
        [
            "先保留真正有效的一步，不要同时改太多",
            "优先降低执行摩擦，再继续加任务",
            "下一轮复盘时只看一个最核心指标",
        ],
    )


def _build_qualitative_summary(
    *,
    plan: InterventionPlan,
    completion_rate: float,
    completed_task_count: int,
    total_task_count: int,
    health_delta: float | None,
    risk_before: str | None,
    risk_now: str | None,
    duration_days: int,
    feedback_count: int,
    usefulness_avg: float | None,
    friction_avg: float | None,
) -> tuple[list[str], list[str], list[str]]:
    wins: list[str] = []
    watchouts: list[str] = []

    if total_task_count and completion_rate >= 0.5:
        wins.append(
            f"计划期内已完成 {completed_task_count}/{total_task_count} 个动作，执行开始形成节奏。"
        )
    if health_delta is not None and health_delta > 0:
        wins.append(f"关系健康分较计划开始前提升了 {health_delta:.1f}。")
    if _risk_rank(risk_now) < _risk_rank(risk_before):
        wins.append(f"风险等级已从 {risk_before or 'none'} 降到 {risk_now or 'none'}。")
    if feedback_count >= 2 and usefulness_avg is not None and usefulness_avg >= 4.0:
        wins.append("最近的主观反馈整体偏正向，说明任务方向基本贴合。")
    if not wins and duration_days <= 2:
        wins.append("计划刚启动，先看动作是否能稳定落地。")

    if total_task_count and completion_rate < 0.34:
        watchouts.append("当前执行率偏低，说明任务可能还是偏重或触发时机不对。")
    if health_delta is not None and health_delta < 0:
        watchouts.append("最近健康分还没有回升，建议降低动作摩擦并缩小目标。")
    if _risk_rank(risk_now) >= _risk_rank(risk_before) and _risk_rank(risk_now) >= 2:
        watchouts.append("当前风险仍在中高位，接下来要优先做止损和降温。")
    if not total_task_count:
        watchouts.append("目前还缺少足够的承载动作，计划更像方向，未完全形成执行链。")
    if feedback_count >= 2 and friction_avg is not None and friction_avg >= 3.6:
        watchouts.append("最近反馈显示任务执行摩擦偏高，下一轮需要继续减轻动作。")
    if feedback_count == 0 and duration_days >= 3:
        watchouts.append("还缺少“这步有没有用”的主观反馈，系统学习速度会受影响。")

    next_actions = _plan_actions(plan.plan_type)
    if total_task_count and completion_rate < 0.34:
        next_actions[0] = "先把当前任务减量，只保留今晚最容易完成的一步"
    elif health_delta is not None and health_delta > 0 and _risk_rank(risk_now) <= 1:
        next_actions[0] = "保留已经起效的动作，再连续维持 3 天观察"

    return wins[:3], watchouts[:3], next_actions[:3]


async def _get_latest_plan(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> InterventionPlan | None:
    active_result = await db.execute(
        select(InterventionPlan)
        .where(
            *_scope_filters(InterventionPlan, pair_id=pair_id, user_id=user_id),
            InterventionPlan.status == "active",
        )
        .order_by(desc(InterventionPlan.updated_at), desc(InterventionPlan.created_at))
        .limit(1)
    )
    active_plan = active_result.scalar_one_or_none()
    if active_plan:
        return active_plan

    latest_result = await db.execute(
        select(InterventionPlan)
        .where(*_scope_filters(InterventionPlan, pair_id=pair_id, user_id=user_id))
        .order_by(desc(InterventionPlan.updated_at), desc(InterventionPlan.created_at))
        .limit(1)
    )
    return latest_result.scalar_one_or_none()


async def _get_latest_snapshot(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    before_date: date | None = None,
) -> RelationshipProfileSnapshot | None:
    stmt = (
        select(RelationshipProfileSnapshot)
        .where(*_scope_filters(RelationshipProfileSnapshot, pair_id=pair_id, user_id=user_id))
        .order_by(
            RelationshipProfileSnapshot.snapshot_date.desc(),
            RelationshipProfileSnapshot.created_at.desc(),
        )
    )
    if before_date:
        stmt = stmt.where(RelationshipProfileSnapshot.snapshot_date <= before_date)
    result = await db.execute(stmt.limit(1))
    return result.scalar_one_or_none()


async def _get_health_baseline(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    start_date: date,
) -> float | None:
    result = await db.execute(
        select(Report)
        .where(
            *_scope_filters(Report, pair_id=pair_id, user_id=user_id),
            Report.status == ReportStatus.COMPLETED,
            Report.health_score.isnot(None),
            Report.report_date < start_date,
        )
        .order_by(Report.report_date.desc(), Report.created_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if report and report.health_score is not None:
        return round(float(report.health_score), 1)
    return None


async def _get_health_current(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    start_date: date,
) -> float | None:
    result = await db.execute(
        select(Report)
        .where(
            *_scope_filters(Report, pair_id=pair_id, user_id=user_id),
            Report.status == ReportStatus.COMPLETED,
            Report.health_score.isnot(None),
            Report.report_date >= start_date,
        )
        .order_by(Report.report_date.desc(), Report.created_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if report and report.health_score is not None:
        return round(float(report.health_score), 1)
    return None


async def build_intervention_scorecard(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
) -> dict | None:
    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    if (normalized_pair_id is None) == (normalized_user_id is None):
        raise ValueError("build_intervention_scorecard requires exactly one scope")

    plan = await _get_latest_plan(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
    )
    if not plan:
        return None

    today = current_local_date()
    effective_end_date = (
        min(plan.end_date, today)
        if plan.end_date and plan.end_date < today
        else today
    )
    duration_days = max((effective_end_date - plan.start_date).days + 1, 1)

    tasks: list[RelationshipTask] = []
    if normalized_pair_id:
        task_result = await db.execute(
            select(RelationshipTask)
            .where(
                RelationshipTask.pair_id == normalized_pair_id,
                RelationshipTask.due_date >= plan.start_date,
                RelationshipTask.due_date <= effective_end_date,
            )
            .order_by(RelationshipTask.due_date.asc(), RelationshipTask.created_at.asc())
        )
        tasks = task_result.scalars().all()

    total_task_count = len(tasks)
    completed_task_count = sum(
        1 for task in tasks if task.status == TaskStatus.COMPLETED
    )
    completion_rate = (
        round(completed_task_count / total_task_count, 4) if total_task_count else 0.0
    )
    task_id_strings = [str(task.id) for task in tasks]
    feedback_map: dict[str, dict] = {}
    if task_id_strings:
        feedback_result = await db.execute(
            select(RelationshipEvent)
            .where(
                RelationshipEvent.event_type == "task.feedback_submitted",
                RelationshipEvent.entity_type == "relationship_task",
                RelationshipEvent.entity_id.in_(task_id_strings),
            )
            .order_by(
                RelationshipEvent.occurred_at.desc(),
                RelationshipEvent.created_at.desc(),
            )
        )
        for event in feedback_result.scalars().all():
            entity_id = str(event.entity_id or "")
            feedback_key = f"{entity_id}:{event.user_id or 'anon'}"
            if not entity_id or feedback_key in feedback_map:
                continue
            payload = event.payload or {}
            feedback_map[feedback_key] = {
                "usefulness_score": payload.get("usefulness_score"),
                "friction_score": payload.get("friction_score"),
                "note": payload.get("note"),
            }
    feedback_summary = summarize_feedback_map(feedback_map)

    trigger_snapshot = None
    if plan.trigger_snapshot_id:
        trigger_snapshot = await db.get(
            RelationshipProfileSnapshot,
            plan.trigger_snapshot_id,
        )
    baseline_snapshot = trigger_snapshot or await _get_latest_snapshot(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
        before_date=plan.start_date,
    )
    current_snapshot = await _get_latest_snapshot(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
    )

    risk_before = (
        (baseline_snapshot.risk_summary or {}).get("current_level")
        if baseline_snapshot
        else plan.risk_level
    ) or plan.risk_level
    risk_now = (
        (current_snapshot.risk_summary or {}).get("current_level")
        if current_snapshot
        else plan.risk_level
    ) or plan.risk_level

    health_before = await _get_health_baseline(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
        start_date=plan.start_date,
    )
    if health_before is None and baseline_snapshot:
        health_before = baseline_snapshot.metrics_json.get("report_health_avg")
    if health_before is not None:
        health_before = round(float(health_before), 1)

    health_now = await _get_health_current(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
        start_date=plan.start_date,
    )
    if health_now is None and current_snapshot:
        health_now = current_snapshot.metrics_json.get("report_health_avg")
    if health_now is not None:
        health_now = round(float(health_now), 1)

    health_delta = None
    if health_before is not None and health_now is not None:
        health_delta = round(health_now - health_before, 1)

    momentum = _derive_momentum(
        completion_rate=completion_rate,
        health_delta=health_delta,
        risk_before=risk_before,
        risk_now=risk_now,
        duration_days=duration_days,
    )
    wins, watchouts, next_actions = _build_qualitative_summary(
        plan=plan,
        completion_rate=completion_rate,
        completed_task_count=completed_task_count,
        total_task_count=total_task_count,
        health_delta=health_delta,
        risk_before=risk_before,
        risk_now=risk_now,
        duration_days=duration_days,
        feedback_count=feedback_summary["feedback_count"],
        usefulness_avg=feedback_summary["usefulness_avg"],
        friction_avg=feedback_summary["friction_avg"],
    )

    return {
        "plan_id": plan.id,
        "pair_id": plan.pair_id,
        "user_id": plan.user_id,
        "plan_type": plan.plan_type,
        "status": plan.status,
        "risk_level": plan.risk_level,
        "primary_goal": (plan.goal_json or {}).get("primary_goal"),
        "focus": (plan.goal_json or {}).get("focus", []),
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "duration_days": duration_days,
        "risk_before": risk_before,
        "risk_now": risk_now,
        "health_before": health_before,
        "health_now": health_now,
        "health_delta": health_delta,
        "completion_rate": completion_rate,
        "completed_task_count": completed_task_count,
        "total_task_count": total_task_count,
        "feedback_count": feedback_summary["feedback_count"],
        "usefulness_avg": feedback_summary["usefulness_avg"],
        "friction_avg": feedback_summary["friction_avg"],
        "momentum": momentum,
        "wins": wins,
        "watchouts": watchouts,
        "next_actions": next_actions,
    }
