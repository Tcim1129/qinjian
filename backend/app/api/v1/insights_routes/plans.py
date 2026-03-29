"""Plan and policy insight routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import InterventionPlan, RelationshipEvent, User
from app.schemas import (
    InterventionEvaluationResponse,
    InterventionExperimentLedgerResponse,
    InterventionPlanResponse,
    InterventionScorecardResponse,
    PolicyDecisionAuditResponse,
    PolicyRegistrySnapshotResponse,
    PolicyScheduleResponse,
)
from app.services.intervention_effectiveness import build_intervention_scorecard
from app.services.intervention_evaluation import build_intervention_evaluation
from app.services.intervention_experimentation import (
    build_intervention_experiment_ledger,
)
from app.services.playbook_runtime import sync_active_playbook_runtime
from app.services.policy_registry import build_policy_registry_snapshot
from app.services.policy_scheduling import SCHEDULE_LABELS, build_policy_schedule
from app.services.policy_selection import SELECTION_LABELS
from app.services.relationship_intelligence import record_relationship_event

from .shared import (
    detail_metric,
    event_scope_query,
    plan_scope_query,
    resolve_scope,
    serialize_timeline_event,
)

router = APIRouter(tags=["关系智能"])


def policy_title_lookup(registry: dict | None) -> dict[str, str]:
    lookup: dict[str, str] = {}
    registry = registry or {}
    for policy in [
        registry.get("current_policy"),
        registry.get("recommended_policy"),
        *(registry.get("policies") or []),
    ]:
        if not isinstance(policy, dict):
            continue
        signature = str(policy.get("signature") or "").strip()
        title = str(
            policy.get("title") or policy.get("label") or policy.get("policy_id") or ""
        ).strip()
        if signature and title and signature not in lookup:
            lookup[signature] = title
    return lookup


def humanize_slug(value: str | None) -> str | None:
    if not value:
        return None
    return str(value).replace("_", " ").strip()


def build_policy_audit_history_item(
    event: RelationshipEvent,
    *,
    title_lookup: dict[str, str],
    current_policy: dict,
) -> dict | None:
    payload = event.payload or {}
    selection_mode = str(payload.get("policy_selection_mode") or "").strip() or None
    schedule_mode = str(payload.get("policy_schedule_mode") or "").strip() or None
    selected_signature = str(
        payload.get("selected_policy_signature") or payload.get("policy_signature") or ""
    ).strip() or None
    selected_label = (
        title_lookup.get(selected_signature or "")
        or current_policy.get("title")
        or current_policy.get("label")
        or selected_signature
    )
    selection_label = SELECTION_LABELS.get(selection_mode or "", humanize_slug(selection_mode))
    schedule_label = SCHEDULE_LABELS.get(schedule_mode or "", humanize_slug(schedule_mode))
    auto_applied = bool(payload.get("policy_selection_auto_applied"))

    if auto_applied and selection_label:
        summary = (
            f"System auto-applied {selection_label.lower()} and routed the next batch through "
            f"{selected_label or 'the selected policy'}."
        )
    elif selection_mode == "keep_current":
        summary = (
            f"System held {selected_label or 'the current policy'} and kept observing "
            "instead of switching early."
        )
    elif selection_label:
        summary = (
            f"System recorded {selection_label.lower()} while keeping "
            f"{selected_label or 'the current policy'} active."
        )
    else:
        summary = (
            f"System generated a new task batch under "
            f"{selected_label or 'the current policy'}."
        )

    return {
        "occurred_at": event.occurred_at,
        "summary": summary,
        "selection_mode": selection_mode,
        "selection_label": selection_label,
        "schedule_mode": schedule_mode,
        "schedule_label": schedule_label,
        "selected_policy_signature": selected_signature,
        "selected_policy_label": selected_label,
        "auto_applied": auto_applied,
        "checkpoint_date": payload.get("policy_schedule_checkpoint_date"),
    }


async def build_policy_decision_audit(
    db: AsyncSession,
    *,
    pair_id: str | None,
    user_id: str | None,
    viewer_user_id: str | None,
) -> dict | None:
    registry = await build_policy_registry_snapshot(
        db,
        pair_id=pair_id,
        user_id=user_id,
        viewer_user_id=viewer_user_id,
    )
    if not registry:
        return None

    schedule = await build_policy_schedule(
        db,
        pair_id=pair_id,
        user_id=user_id,
        viewer_user_id=viewer_user_id,
    )
    await build_intervention_experiment_ledger(
        db,
        pair_id=pair_id,
        user_id=user_id,
        viewer_user_id=viewer_user_id,
        persist_snapshot=False,
    )
    scorecard = await build_intervention_scorecard(
        db,
        pair_id=pair_id,
        user_id=user_id,
    )
    playbook = await sync_active_playbook_runtime(
        db,
        pair_id=pair_id,
        user_id=user_id,
        viewed=False,
    )

    result = await db.execute(
        select(RelationshipEvent)
        .where(*event_scope_query(pair_id, user_id))
        .order_by(
            RelationshipEvent.occurred_at.desc(),
            RelationshipEvent.created_at.desc(),
        )
        .limit(40)
    )
    recent_events = result.scalars().all()

    title_lookup = policy_title_lookup(registry)
    decision_history: list[dict] = []
    supporting_events: list[dict] = []
    support_event_types = {
        "checkin.created",
        "report.completed",
        "task.completed",
        "task.feedback_submitted",
        "crisis.raised",
        "crisis.updated",
        "crisis.resolved",
        "playbook.transitioned",
    }

    for event in recent_events:
        if event.event_type.endswith(".viewed") or event.event_type == "timeline.event_detail_viewed":
            continue

        payload = event.payload or {}
        if event.event_type == "task.generated" and (
            payload.get("policy_selection_mode") or payload.get("policy_schedule_mode")
        ):
            history_item = build_policy_audit_history_item(
                event,
                title_lookup=title_lookup,
                current_policy=registry.get("current_policy") or {},
            )
            if history_item:
                decision_history.append(history_item)
            continue

        if event.event_type in support_event_types and len(supporting_events) < 6:
            supporting_events.append(serialize_timeline_event(event))

    signals = [
        detail_metric(
            "Current policy",
            (registry.get("current_policy") or {}).get("title"),
        ),
        detail_metric(
            "Recommended next",
            (
                (registry.get("recommended_policy") or {}).get("title")
                if registry.get("recommended_policy")
                else None
            ),
        ),
        detail_metric("Selection rule", registry.get("selection_label")),
        detail_metric(
            "Schedule rule",
            schedule.get("schedule_label") if schedule else None,
        ),
        detail_metric(
            "Observed runs",
            (registry.get("current_policy") or {}).get("observation_count"),
        ),
        detail_metric("Momentum", scorecard.get("momentum") if scorecard else None),
        detail_metric(
            "Completion rate",
            (
                f"{round(float(scorecard.get('completion_rate') or 0.0) * 100)}%"
                if scorecard and scorecard.get("completion_rate") is not None
                else None
            ),
        ),
        detail_metric(
            "Usefulness",
            (
                f"{float(scorecard.get('usefulness_avg')):.1f}/5"
                if scorecard and scorecard.get("usefulness_avg") is not None
                else None
            ),
        ),
        detail_metric(
            "Friction",
            (
                f"{float(scorecard.get('friction_avg')):.1f}/5"
                if scorecard and scorecard.get("friction_avg") is not None
                else None
            ),
        ),
        detail_metric(
            "Active branch",
            playbook.get("active_branch_label") if playbook else None,
        ),
        detail_metric(
            "Next checkpoint",
            (
                (schedule.get("current_stage") or {}).get("checkpoint_date")
                if schedule
                else None
            ),
        ),
    ]

    return {
        "plan_id": registry["plan_id"],
        "pair_id": registry.get("pair_id"),
        "user_id": registry.get("user_id"),
        "plan_type": registry["plan_type"],
        "audit_label": "Decision audit",
        "decision_model": "event_backed_policy_audit_v1",
        "current_policy": registry["current_policy"],
        "recommended_policy": registry.get("recommended_policy"),
        "selection_mode": registry.get("selection_mode"),
        "selection_label": registry.get("selection_label"),
        "selection_reason": registry.get("selection_reason"),
        "schedule_mode": schedule.get("schedule_mode") if schedule else None,
        "schedule_label": schedule.get("schedule_label") if schedule else None,
        "schedule_summary": (
            (schedule.get("current_stage") or {}).get("summary")
            if schedule
            else None
        ),
        "active_branch_label": playbook.get("active_branch_label") if playbook else None,
        "next_checkpoint": (
            (schedule.get("current_stage") or {}).get("checkpoint_date")
            if schedule
            else None
        ),
        "evidence_observation_count": int(
            ((registry.get("current_policy") or {}).get("observation_count") or 0)
        ),
        "signals": [item for item in signals if item],
        "supporting_events": supporting_events,
        "decision_history": decision_history[:4],
        "scientific_note": (
            "This audit layer ties together strategy selection, schedule checkpoints, "
            "and supporting relationship events so each policy move can be explained "
            "against concrete evidence instead of opaque model output."
        ),
        "clinical_disclaimer": (
            "This audit view is a product-side explanation and optimization surface. "
            "It does not replace clinical judgment or therapy."
        ),
    }


@router.get("/plans/active", response_model=InterventionPlanResponse | None)
async def get_active_plan(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )

    result = await db.execute(
        select(InterventionPlan)
        .where(
            *plan_scope_query(pair_scope_id, user_scope_id),
            InterventionPlan.status == "active",
        )
        .order_by(desc(InterventionPlan.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get(
    "/plans/scorecard",
    response_model=InterventionScorecardResponse | None,
)
async def get_plan_scorecard(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )
    scorecard = await build_intervention_scorecard(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
    )
    if not scorecard:
        return None

    await record_relationship_event(
        db,
        event_type="plan.scorecard_viewed",
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        entity_type="intervention_plan",
        entity_id=scorecard["plan_id"],
        payload={
            "plan_type": scorecard["plan_type"],
            "momentum": scorecard["momentum"],
        },
    )
    await db.commit()
    return InterventionScorecardResponse(**scorecard)


@router.get(
    "/plans/evaluation",
    response_model=InterventionEvaluationResponse | None,
)
async def get_plan_evaluation(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )
    evaluation = await build_intervention_evaluation(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
    )
    if not evaluation:
        return None

    await record_relationship_event(
        db,
        event_type="plan.evaluation_viewed",
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        entity_type="intervention_plan",
        entity_id=evaluation["plan_id"],
        payload={
            "plan_type": evaluation["plan_type"],
            "verdict": evaluation["verdict"],
            "confidence_level": evaluation["confidence_level"],
        },
    )
    await db.commit()
    return InterventionEvaluationResponse(**evaluation)


@router.get(
    "/plans/experiment",
    response_model=InterventionExperimentLedgerResponse | None,
)
async def get_plan_experiment_ledger(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )
    experiment = await build_intervention_experiment_ledger(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        viewer_user_id=user.id,
        persist_snapshot=True,
    )
    if not experiment:
        return None

    await record_relationship_event(
        db,
        event_type="plan.experiment_viewed",
        pair_id=pair_scope_id,
        user_id=user.id if pair_scope_id else user_scope_id,
        entity_type="intervention_plan",
        entity_id=experiment["plan_id"],
        payload={
            "plan_type": experiment["plan_type"],
            "comparison_status": experiment["comparison_status"],
            "policy_signature": experiment["current_policy"]["signature"],
        },
    )
    await db.commit()
    return InterventionExperimentLedgerResponse(**experiment)


@router.get(
    "/plans/policy-registry",
    response_model=PolicyRegistrySnapshotResponse | None,
)
async def get_plan_policy_registry(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )
    registry = await build_policy_registry_snapshot(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        viewer_user_id=user.id,
    )
    if not registry:
        return None

    await record_relationship_event(
        db,
        event_type="plan.policy_registry_viewed",
        pair_id=pair_scope_id,
        user_id=user.id if pair_scope_id else user_scope_id,
        entity_type="intervention_plan",
        entity_id=registry["plan_id"],
        payload={
            "plan_type": registry["plan_type"],
            "selection_mode": registry.get("selection_mode"),
            "current_policy_id": registry["current_policy"]["policy_id"],
            "recommended_policy_id": (
                registry["recommended_policy"]["policy_id"]
                if registry.get("recommended_policy")
                else None
            ),
        },
    )
    await db.commit()
    return PolicyRegistrySnapshotResponse(**registry)


@router.get(
    "/plans/policy-schedule",
    response_model=PolicyScheduleResponse | None,
)
async def get_plan_policy_schedule(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )
    schedule = await build_policy_schedule(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        viewer_user_id=user.id,
    )
    if not schedule:
        return None

    await record_relationship_event(
        db,
        event_type="plan.policy_schedule_viewed",
        pair_id=pair_scope_id,
        user_id=user.id if pair_scope_id else user_scope_id,
        entity_type="intervention_plan",
        entity_id=schedule["plan_id"],
        payload={
            "plan_type": schedule["plan_type"],
            "schedule_mode": schedule["schedule_mode"],
            "current_policy_id": schedule["current_policy"]["policy_id"],
            "recommended_policy_id": (
                schedule["recommended_policy"]["policy_id"]
                if schedule.get("recommended_policy")
                else None
            ),
        },
    )
    await db.commit()
    return PolicyScheduleResponse(**schedule)


@router.get(
    "/plans/policy-audit",
    response_model=PolicyDecisionAuditResponse | None,
)
async def get_plan_policy_audit(
    pair_id: str | None = None,
    mode: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair_scope_id, user_scope_id = await resolve_scope(
        pair_id=pair_id, mode=mode, user=user, db=db
    )
    audit = await build_policy_decision_audit(
        db,
        pair_id=pair_scope_id,
        user_id=user_scope_id,
        viewer_user_id=str(user.id),
    )
    if not audit:
        return None

    await record_relationship_event(
        db,
        event_type="plan.policy_audit_viewed",
        pair_id=pair_scope_id,
        user_id=user.id if pair_scope_id else user_scope_id,
        entity_type="intervention_plan",
        entity_id=audit["plan_id"],
        payload={
            "plan_type": audit["plan_type"],
            "selection_mode": audit.get("selection_mode"),
            "schedule_mode": audit.get("schedule_mode"),
            "current_policy_id": audit["current_policy"]["policy_id"],
            "recommended_policy_id": (
                audit["recommended_policy"]["policy_id"]
                if audit.get("recommended_policy")
                else None
            ),
        },
    )
    await db.commit()
    return PolicyDecisionAuditResponse(**audit)
