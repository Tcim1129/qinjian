"""Safety status helpers for explainable, competition-friendly boundaries."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CrisisAlert,
    CrisisAlertStatus,
    InterventionPlan,
    RelationshipProfileSnapshot,
    Report,
    ReportStatus,
)
from app.services.display_labels import plan_type_label, risk_level_label, translate_inline_codes
from app.services.guidance_policy import build_crisis_support

RISK_ORDER = {
    "none": 0,
    "low": 1,
    "mild": 1,
    "medium": 2,
    "moderate": 2,
    "high": 3,
    "severe": 3,
}

PAIR_HANDOFF = (
    "如果已经出现持续升级、威胁、羞辱、断联试探或任何安全担忧，"
    "请停止依赖产品内建议，转向可信任的人、专业咨询或当地紧急支持。"
)
SOLO_HANDOFF = (
    "如果最近已经明显影响睡眠、工作、饮食，或出现持续失控感，"
    "请尽快寻求线下专业支持，而不是只靠自助建议继续硬撑。"
)


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _normalize_level(value: str | None) -> str:
    raw = str(value or "none").strip().lower()
    if raw == "low":
        return "mild"
    if raw == "medium":
        return "moderate"
    if raw == "high":
        return "severe"
    if raw not in RISK_ORDER:
        return "none"
    return raw


def _max_risk(*levels: str | None) -> str:
    resolved = [_normalize_level(level) for level in levels if level is not None]
    if not resolved:
        return "none"
    return max(resolved, key=lambda item: RISK_ORDER.get(item, 0))


def _label_for_level(level: str) -> str:
    return {
        "none": "低风险",
        "mild": "轻度风险",
        "moderate": "中度风险",
        "severe": "高风险",
    }.get(_normalize_level(level), "低风险")


def _format_score(value: float | int | None) -> str | None:
    if value is None:
        return None
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}"


def _build_evidence_summary(
    *,
    scope_is_pair: bool,
    risk_level: str,
    snapshot: RelationshipProfileSnapshot | None,
    active_alert: CrisisAlert | None,
    active_plan: InterventionPlan | None,
    latest_report: Report | None,
) -> list[str]:
    evidence: list[str] = []
    metrics = (snapshot.metrics_json or {}) if snapshot else {}
    risk_summary = (snapshot.risk_summary or {}) if snapshot else {}

    if active_alert:
        alert_level = _normalize_level(
            getattr(active_alert.level, "value", active_alert.level)
        )
        evidence.append(
            f"当前危机监测仍标记为{_label_for_level(alert_level)}，说明系统先把安全边界放在建议之前。"
        )
    elif risk_level in {"moderate", "severe"}:
        evidence.append("最近多条信号同时指向升级风险，所以系统优先给边界和止损建议。")

    if latest_report and latest_report.health_score is not None:
        report_label = "关系简报" if scope_is_pair else "个人简报"
        evidence.append(
            f"最近一份{report_label}健康分为 {_format_score(latest_report.health_score)}/100。"
        )

    if scope_is_pair:
        overlap = metrics.get("interaction_overlap_rate")
        if overlap is not None:
            evidence.append(
                f"近 7 天互动重合率约为 {round(float(overlap) * 100)}%，这是判断连接稳定度的重要依据。"
            )
        crisis_count = metrics.get("crisis_event_count")
        if crisis_count:
            evidence.append(f"近阶段已记录 {int(crisis_count)} 次风险事件，系统会更保守地给出沟通建议。")
        high_risk_count = metrics.get("message_simulation_high_risk_count")
        if high_risk_count:
            evidence.append(
                f"最近已有 {int(high_risk_count)} 次高风险消息预演，说明表达方式仍可能触发误解或升级。"
            )
    else:
        mood = metrics.get("mood_avg")
        if mood is not None:
            evidence.append(f"近 7 天个人情绪均值约为 {_format_score(mood)}/10。")
        task_rate = metrics.get("task_completion_rate")
        if task_rate is not None:
            evidence.append(
                f"最近自我照顾动作完成率约为 {round(float(task_rate) * 100)}%，用于判断当前节奏是否可持续。"
            )

    trend = str(risk_summary.get("trend") or "").strip()
    if trend:
        evidence.append(f"风险趋势当前显示为“{trend}”，系统会用它来决定是保持、减压还是转介。")

    if active_plan:
        goal = (active_plan.goal_json or {}).get("primary_goal") or plan_type_label(active_plan.plan_type)
        evidence.append(f"当前仍有一条激活中的干预计划，主要目标是：{goal}。")

    return [translate_inline_codes(item) for item in evidence[:4]]


def _build_why_now(
    *,
    scope_is_pair: bool,
    risk_level: str,
    active_plan: InterventionPlan | None,
    active_alert: CrisisAlert | None,
    snapshot: RelationshipProfileSnapshot | None,
) -> str:
    risk_level = _normalize_level(risk_level)
    risk_summary = (snapshot.risk_summary or {}) if snapshot else {}
    trend = str(risk_summary.get("trend") or "").strip()

    if risk_level == "severe":
        return (
            "当前已经接近高风险升级区间，系统先要求止损、降温和转向人工支持，"
            "而不是继续推动高强度沟通。"
        )
    if risk_level == "moderate":
        return (
            "最近的风险信号已经不是一次性波动，所以系统把边界说明和修复节奏放在首位。"
        )
    if active_alert:
        return "当前仍有未解除的风险提醒，所以所有建议都会附带边界说明。"
    if active_plan:
        return (
            f"系统仍在执行“{plan_type_label(active_plan.plan_type)}”这一阶段的计划，"
            "所以会优先给与当前策略一致的下一步动作。"
        )
    if trend:
        return f"最近的关系信号呈现“{trend}”趋势，所以系统会先解释判断依据，再给下一步建议。"
    if scope_is_pair:
        return "当前没有进入高风险区间，但系统仍会把最近的互动质量和风险走势一起解释清楚。"
    return "当前更多是稳定与自我调节问题，系统会先说明依据和边界，再给节奏建议。"


def _build_recommended_action(
    *,
    scope_is_pair: bool,
    risk_level: str,
    active_plan: InterventionPlan | None,
    latest_report: Report | None,
) -> str:
    risk_level = _normalize_level(risk_level)
    if risk_level == "severe":
        return "先停止升级性沟通，保证安全，再联系可信任的人或专业支持。"
    if risk_level == "moderate":
        return "先按修复方案降温，避免继续争辩，把目标放在重新建立可沟通窗口。"
    if active_plan:
        goal = (active_plan.goal_json or {}).get("primary_goal")
        if goal:
            return translate_inline_codes(f"继续沿当前计划推进，先完成与“{goal}”最相关的一个小动作。")
    if latest_report and latest_report.content:
        suggestion = (
            latest_report.content.get("suggestion")
            or latest_report.content.get("self_care_tip")
            or latest_report.content.get("trend_description")
        )
        if suggestion:
            return str(suggestion)
    if scope_is_pair:
        return "优先做一件低摩擦的小修复动作，再观察今天的互动是否更稳定。"
    return "先做一个最容易完成的自我照顾动作，再观察这周状态是否回稳。"


def _build_limitation_note(scope_is_pair: bool) -> str:
    if scope_is_pair:
        return (
            "本次判断基于最近的打卡、报告、任务反馈和风险事件，"
            "它是关系支持系统，不等于对伴侣意图、人格或安全状况的临床判断。"
        )
    return (
        "本次判断基于最近的记录、报告和任务反馈，"
        "它用于帮助你看见趋势，不等于医疗或心理诊断。"
    )


def _build_handoff_recommendation(*, scope_is_pair: bool, risk_level: str) -> str | None:
    if _normalize_level(risk_level) not in {"moderate", "severe"}:
        return None
    return PAIR_HANDOFF if scope_is_pair else SOLO_HANDOFF


async def _get_latest_snapshot(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> RelationshipProfileSnapshot | None:
    stmt = (
        select(RelationshipProfileSnapshot)
        .where(
            RelationshipProfileSnapshot.pair_id == pair_id,
            RelationshipProfileSnapshot.user_id == user_id,
            RelationshipProfileSnapshot.window_days == 7,
        )
        .order_by(
            RelationshipProfileSnapshot.snapshot_date.desc(),
            RelationshipProfileSnapshot.created_at.desc(),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_latest_active_alert(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None,
) -> CrisisAlert | None:
    if pair_id is None:
        return None
    stmt = (
        select(CrisisAlert)
        .where(
            CrisisAlert.pair_id == pair_id,
            CrisisAlert.status.in_(
                [CrisisAlertStatus.ACTIVE, CrisisAlertStatus.ACKNOWLEDGED]
            ),
        )
        .order_by(desc(CrisisAlert.created_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_latest_plan(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> InterventionPlan | None:
    stmt = (
        select(InterventionPlan)
        .where(
            InterventionPlan.pair_id == pair_id,
            InterventionPlan.user_id == user_id,
            InterventionPlan.status == "active",
        )
        .order_by(desc(InterventionPlan.created_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_latest_report(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> Report | None:
    stmt = (
        select(Report)
        .where(
            Report.pair_id == pair_id,
            Report.user_id == user_id,
            Report.status == ReportStatus.COMPLETED,
        )
        .order_by(Report.report_date.desc(), Report.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def build_safety_status(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
) -> dict:
    """Build a scope-aware trust, safety, and limitation summary."""

    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    if (normalized_pair_id is None) == (normalized_user_id is None):
        raise ValueError("build_safety_status requires exactly one scope")

    scope_is_pair = normalized_pair_id is not None
    snapshot = await _get_latest_snapshot(
        db,
        pair_id=normalized_pair_id,
        user_id=None if scope_is_pair else normalized_user_id,
    )
    active_alert = await _get_latest_active_alert(db, pair_id=normalized_pair_id)
    active_plan = await _get_latest_plan(
        db,
        pair_id=normalized_pair_id,
        user_id=None if scope_is_pair else normalized_user_id,
    )
    latest_report = await _get_latest_report(
        db,
        pair_id=normalized_pair_id,
        user_id=None if scope_is_pair else normalized_user_id,
    )

    snapshot_risk = (snapshot.risk_summary or {}).get("current_level") if snapshot else None
    report_risk = (latest_report.content or {}).get("crisis_level") if latest_report and latest_report.content else None
    alert_risk = getattr(active_alert.level, "value", active_alert.level) if active_alert else None
    plan_risk = active_plan.risk_level if active_plan else None
    risk_level = _max_risk(alert_risk, snapshot_risk, report_risk, plan_risk)

    evidence_summary = _build_evidence_summary(
        scope_is_pair=scope_is_pair,
        risk_level=risk_level,
        snapshot=snapshot,
        active_alert=active_alert,
        active_plan=active_plan,
        latest_report=latest_report,
    )
    crisis_support = build_crisis_support(
        scope_type="pair" if scope_is_pair else "solo",
        risk_level=risk_level,
    )

    return {
        "risk_level": risk_level,
        "risk_level_label": risk_level_label(risk_level),
        "why_now": _build_why_now(
            scope_is_pair=scope_is_pair,
            risk_level=risk_level,
            active_plan=active_plan,
            active_alert=active_alert,
            snapshot=snapshot,
        ),
        "evidence_summary": evidence_summary,
        "limitation_note": _build_limitation_note(scope_is_pair),
        "recommended_action": _build_recommended_action(
            scope_is_pair=scope_is_pair,
            risk_level=risk_level,
            active_plan=active_plan,
            latest_report=latest_report,
        ),
        "handoff_recommendation": _build_handoff_recommendation(
            scope_is_pair=scope_is_pair,
            risk_level=risk_level,
        ),
        "crisis_support": crisis_support,
        "generated_at": datetime.utcnow().isoformat(),
    }
