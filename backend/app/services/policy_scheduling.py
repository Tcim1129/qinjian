"""Policy cycle scheduling for intervention experimentation."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import current_local_date
from app.services.intervention_effectiveness import build_intervention_scorecard
from app.services.intervention_experimentation import build_intervention_experiment_ledger
from app.services.policy_registry import (
    build_policy_registry_snapshot,
    list_registered_policies,
)

SCHEDULE_LABELS = {
    "collect_more_evidence": "继续跑完当前观察周期",
    "hold_current": "先保持当前版本",
    "finish_current_then_switch": "当前周期结束后切换",
    "switch_now": "现在就切到下一版",
    "graduate_current_policy": "当前版本通过，可进入下一层",
    "backoff_now": "先回退到低摩擦版本",
}

PHASE_LABELS = {
    "evidence": "证据积累期",
    "hold": "稳定保持期",
    "transition": "切换准备期",
    "graduate": "升级验证期",
    "backoff": "回退减压期",
    "review": "检查点评估",
}

INTENSITY_RANK = {
    "light": 0,
    "steady": 1,
    "stretch": 2,
}


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _base_cycle_days(
    *,
    plan_type: str | None,
    intensity: str | None,
    risk_now: str | None,
) -> int:
    base = {
        "conflict_repair_plan": 3,
        "self_regulation_plan": 3,
        "low_connection_recovery": 4,
        "distance_compensation_plan": 4,
    }.get(str(plan_type or ""), 4)
    if str(intensity or "") == "stretch":
        base += 1
    elif str(intensity or "") == "light":
        base = max(2, base - 1)
    if str(risk_now or "") in ("moderate", "severe"):
        base = min(base, 3)
    return base


def _min_observations(intensity: str | None) -> int:
    return 2 if str(intensity or "") == "light" else 3


def _float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_percent(value: float | None) -> str:
    if value is None:
        return "待观察"
    return f"{round(value * 100):.0f}%"


def _format_score(value: float | None) -> str:
    if value is None:
        return "待观察"
    return f"{value:.1f}/5"


def _policy_title(policy: dict | None) -> str:
    policy = policy or {}
    return str(policy.get("title") or policy.get("label") or "当前策略")


def _schedule_mode(
    *,
    selection_mode: str | None,
    comparison_status: str | None,
    current_policy: dict,
    recommended_policy: dict | None,
    scorecard: dict,
) -> str:
    risk_now = str(scorecard.get("risk_now") or "")
    completion_rate = _float(scorecard.get("completion_rate")) or 0.0
    usefulness = _float(scorecard.get("usefulness_avg"))
    friction = _float(scorecard.get("friction_avg"))
    observation_count = int(current_policy.get("observation_count") or 0)
    min_observations = _min_observations(current_policy.get("intensity"))

    if selection_mode == "backoff_to_lower_friction" or risk_now in ("moderate", "severe"):
        return "backoff_now"

    if selection_mode in ("adopt_proven_variant", "adopt_proven_copy") and recommended_policy:
        if comparison_status == "worse_than_baseline" or observation_count >= min_observations:
            return "switch_now"
        return "finish_current_then_switch"

    if (
        comparison_status == "better_than_baseline"
        and observation_count >= min_observations
        and completion_rate >= 0.5
        and (usefulness is None or usefulness >= 4.0)
        and (friction is None or friction <= 3.0)
        and risk_now not in ("moderate", "severe")
    ):
        if INTENSITY_RANK.get(str(current_policy.get("intensity") or "steady"), 1) < 2:
            return "graduate_current_policy"
        return "hold_current"

    if comparison_status == "similar_to_baseline":
        return "hold_current"

    return "collect_more_evidence"


def _policy_phase(schedule_mode: str) -> str:
    return {
        "collect_more_evidence": "evidence",
        "hold_current": "hold",
        "finish_current_then_switch": "transition",
        "switch_now": "transition",
        "graduate_current_policy": "graduate",
        "backoff_now": "backoff",
    }.get(schedule_mode, "review")


def _policy_match_score(
    candidate: dict,
    *,
    branch: str | None,
    intensity: str | None,
    copy_mode: str | None,
) -> int:
    score = 0
    if str(candidate.get("branch") or "") == str(branch or ""):
        score += 4
    if str(candidate.get("intensity") or "") == str(intensity or ""):
        score += 2
    if str(candidate.get("copy_mode") or "") == str(copy_mode or ""):
        score += 1
    return score


def _find_progression_policy(current_policy: dict, policies: list[dict]) -> dict | None:
    current_rank = INTENSITY_RANK.get(str(current_policy.get("intensity") or "steady"), 1)
    candidates = [
        policy
        for policy in policies
        if INTENSITY_RANK.get(str(policy.get("intensity") or "steady"), 1) > current_rank
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            _policy_match_score(
                item,
                branch=current_policy.get("branch"),
                intensity="stretch",
                copy_mode=current_policy.get("copy_mode"),
            ),
            INTENSITY_RANK.get(str(item.get("intensity") or "steady"), 1),
        ),
    )


def _find_backoff_policy(current_policy: dict, policies: list[dict]) -> dict | None:
    current_rank = INTENSITY_RANK.get(str(current_policy.get("intensity") or "steady"), 1)
    candidates = [
        policy
        for policy in policies
        if policy.get("policy_id") != current_policy.get("policy_id")
        and INTENSITY_RANK.get(str(policy.get("intensity") or "steady"), 1) <= current_rank
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            str(item.get("intensity") or "") == "light",
            str(item.get("copy_mode") or "") == "gentle",
            _policy_match_score(
                item,
                branch=current_policy.get("branch"),
                intensity="light",
                copy_mode="gentle",
            ),
        ),
    )


def _stage_summary(
    *,
    phase: str,
    policy: dict,
    days_total: int,
    days_remaining: int,
    observations_remaining: int,
) -> str:
    title = _policy_title(policy)
    if phase == "backoff":
        return f"先用“{title}”把执行摩擦和风险降下来，再决定是否恢复推进。"
    if phase == "transition":
        if days_remaining > 0:
            return f"当前版本再跑 {days_remaining} 天到检查点，然后按证据决定是否切到“{title}”。"
        return f"当前已到检查点，下一轮可以切到“{title}”开始新周期。"
    if phase == "graduate":
        return f"这版策略已经接近通过，接下来可以把“{title}”作为下一层升级候选。"
    if observations_remaining > 0:
        return f"这版策略先继续跑满 {days_total} 天或补齐 {observations_remaining} 次观察，再做判断。"
    if days_remaining > 0:
        return f"当前保持这版策略，再观察 {days_remaining} 天看趋势能否稳定。"
    return f"这版策略已经到检查点，适合做一次正式复盘。"


def _build_stage(
    *,
    phase: str,
    policy: dict,
    days_total: int,
    days_observed: int,
    min_observations: int,
) -> dict:
    observed_count = int(policy.get("observation_count") or 0)
    days_remaining = max(days_total - min(days_observed, days_total), 0)
    observations_remaining = max(min_observations - observed_count, 0)
    return {
        "phase": phase,
        "phase_label": PHASE_LABELS.get(phase, phase),
        "title": _policy_title(policy),
        "summary": _stage_summary(
            phase=phase,
            policy=policy,
            days_total=days_total,
            days_remaining=days_remaining,
            observations_remaining=observations_remaining,
        ),
        "policy_id": policy.get("policy_id"),
        "days_total": days_total,
        "days_observed": min(days_observed, days_total),
        "days_remaining": days_remaining,
        "min_observations": min_observations,
        "observations_remaining": observations_remaining,
        "checkpoint_date": current_local_date() + timedelta(days=days_remaining),
        "branch_label": policy.get("branch_label"),
        "intensity_label": policy.get("intensity_label"),
        "copy_mode_label": policy.get("copy_mode_label"),
    }


def _measurement_plan(scorecard: dict, experiment: dict) -> list[dict]:
    return [
        {
            "id": "task_completion",
            "label": "任务完成率",
            "current": _format_percent(_float(scorecard.get("completion_rate"))),
            "target": ">= 50%",
            "why": "先确保这版策略是真的能被执行，而不是理论上更聪明。",
        },
        {
            "id": "subjective_fit",
            "label": "主观有用度/摩擦",
            "current": (
                f"有用度 {_format_score(_float(scorecard.get('usefulness_avg')))} / "
                f"摩擦 {_format_score(_float(scorecard.get('friction_avg')))}"
            ),
            "target": "有用度 >= 4.0/5，摩擦 <= 3.0/5",
            "why": "对这对人来说，低摩擦且主观有用，才值得继续保留。",
        },
        {
            "id": "risk_shift",
            "label": "风险变化",
            "current": str(scorecard.get("risk_now") or "待观察"),
            "target": "不高于当前风险层级",
            "why": "任何升级都不能以风险继续上升为代价。",
        },
        {
            "id": "experiment_signal",
            "label": "实验信号",
            "current": str(experiment.get("comparison_label") or "待观察"),
            "target": "至少达到“保持当前版本”",
            "why": "比较结果要能支持保留、升级或切换，而不是停在模糊状态。",
        },
    ]


def _advance_when(schedule_mode: str) -> list[str]:
    rules = [
        "最近 2-3 次观察里，完成率持续不低于目标线。",
        "主观有用度保持在 4 分左右或更高，且摩擦没有明显上升。",
        "风险层级没有升级，或已出现回落迹象。",
    ]
    if schedule_mode == "graduate_current_policy":
        rules.append("当前版本已经连续稳定，适合进入更高一层的策略验证。")
    return rules


def _hold_when() -> list[str]:
    return [
        "当前策略没有明显变差，但也还没到足够稳定可以升级。",
        "观察次数还不够，或者最近的结果还偏混合。",
        "先把同一版策略连续跑完一个完整周期，再做切换。",
    ]


def _backoff_when() -> list[str]:
    return [
        "风险重新升到中高位，或者冲突/低连接在继续恶化。",
        "主观摩擦明显上升，已经开始拖慢执行。",
        "连续出现负向信号时，先回退到低摩擦版本而不是硬推。",
    ]


def _preview_summary(
    *,
    schedule_mode: str,
    schedule_label: str,
    checkpoint_date: date,
    days_remaining: int,
) -> str:
    if schedule_mode == "switch_now":
        return f"{schedule_label}，今天就可以进入新版本；下一个检查点在 {checkpoint_date.isoformat()}。"
    if schedule_mode == "backoff_now":
        return f"{schedule_label}，先降压 {max(days_remaining, 1)} 天，再在 {checkpoint_date.isoformat()} 复盘。"
    return f"{schedule_label}，这版再跑 {days_remaining} 天，到 {checkpoint_date.isoformat()} 做下一次复盘。"


def build_policy_schedule_preview(*, scorecard: dict | None, strategy: dict) -> dict | None:
    if not scorecard:
        return None

    selection = dict(strategy.get("policy_selection") or {})
    experiment_summary = dict(strategy.get("experiment_summary") or {})
    intensity = str(strategy.get("intensity") or "steady")
    cycle_days = _base_cycle_days(
        plan_type=scorecard.get("plan_type"),
        intensity=intensity,
        risk_now=scorecard.get("risk_now"),
    )
    observation_count = int(selection.get("evidence_observation_count") or 0)
    min_observations = _min_observations(intensity)
    days_observed = min(cycle_days, max(observation_count, 1))
    days_remaining = max(cycle_days - days_observed, 0)
    schedule_mode = _schedule_mode(
        selection_mode=selection.get("mode"),
        comparison_status=experiment_summary.get("comparison_status"),
        current_policy={
            "intensity": intensity,
            "observation_count": observation_count,
        },
        recommended_policy=(
            {"policy_id": selection.get("selected_policy_signature")}
            if selection.get("selected_policy_signature")
            and selection.get("selected_policy_signature")
            != selection.get("current_policy_signature")
            else None
        ),
        scorecard=scorecard,
    )
    schedule_label = SCHEDULE_LABELS.get(schedule_mode, schedule_mode)
    checkpoint_date = current_local_date() + timedelta(days=days_remaining)
    return {
        "schedule_mode": schedule_mode,
        "schedule_label": schedule_label,
        "days_total": cycle_days,
        "days_observed": days_observed,
        "days_remaining": days_remaining,
        "min_observations": min_observations,
        "observations_remaining": max(min_observations - observation_count, 0),
        "checkpoint_date": checkpoint_date.isoformat(),
        "summary": _preview_summary(
            schedule_mode=schedule_mode,
            schedule_label=schedule_label,
            checkpoint_date=checkpoint_date,
            days_remaining=days_remaining,
        ),
    }


async def build_policy_schedule(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
    viewer_user_id: str | uuid.UUID | None = None,
) -> dict | None:
    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    normalized_viewer_user_id = _normalize_uuid(viewer_user_id)
    if (normalized_pair_id is None) == (normalized_user_id is None):
        raise ValueError("build_policy_schedule requires exactly one scope")

    registry = await build_policy_registry_snapshot(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
        viewer_user_id=normalized_viewer_user_id,
    )
    if not registry:
        return None

    experiment = await build_intervention_experiment_ledger(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
        viewer_user_id=normalized_viewer_user_id,
        persist_snapshot=False,
    )
    if not experiment:
        return None

    scorecard = await build_intervention_scorecard(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
    )
    if not scorecard:
        return None

    current_policy = dict(registry.get("current_policy") or {})
    recommended_policy = dict(registry.get("recommended_policy") or {}) or None
    registered_policies = await list_registered_policies(db, registry.get("plan_type"))
    schedule_mode = _schedule_mode(
        selection_mode=registry.get("selection_mode"),
        comparison_status=experiment.get("comparison_status"),
        current_policy=current_policy,
        recommended_policy=recommended_policy,
        scorecard=scorecard,
    )
    schedule_label = SCHEDULE_LABELS.get(schedule_mode, schedule_mode)
    cycle_days = _base_cycle_days(
        plan_type=registry.get("plan_type"),
        intensity=current_policy.get("intensity"),
        risk_now=scorecard.get("risk_now"),
    )
    min_observations = _min_observations(current_policy.get("intensity"))
    days_observed = min(cycle_days, max(int(current_policy.get("observation_count") or 0), 1))

    next_policy = recommended_policy
    if schedule_mode == "graduate_current_policy" and not next_policy:
        next_policy = _find_progression_policy(current_policy, registered_policies)

    fallback_policy = _find_backoff_policy(current_policy, registered_policies)
    if schedule_mode == "backoff_now" and fallback_policy:
        next_policy = fallback_policy

    current_stage = _build_stage(
        phase=_policy_phase(schedule_mode),
        policy=current_policy,
        days_total=cycle_days,
        days_observed=days_observed,
        min_observations=min_observations,
    )

    next_stage = None
    if next_policy:
        next_stage = _build_stage(
            phase="review" if schedule_mode == "hold_current" else "transition",
            policy=next_policy,
            days_total=_base_cycle_days(
                plan_type=registry.get("plan_type"),
                intensity=next_policy.get("intensity"),
                risk_now=scorecard.get("risk_now"),
            ),
            days_observed=0,
            min_observations=_min_observations(next_policy.get("intensity")),
        )

    fallback_stage = None
    if fallback_policy:
        fallback_stage = _build_stage(
            phase="backoff",
            policy=fallback_policy,
            days_total=_base_cycle_days(
                plan_type=registry.get("plan_type"),
                intensity=fallback_policy.get("intensity"),
                risk_now=scorecard.get("risk_now"),
            ),
            days_observed=0,
            min_observations=_min_observations(fallback_policy.get("intensity")),
        )

    return {
        "plan_id": registry["plan_id"],
        "pair_id": registry.get("pair_id"),
        "user_id": registry.get("user_id"),
        "plan_type": registry["plan_type"],
        "scheduler_model": "policy_cycle_scheduler_v1",
        "scheduler_label": "策略实验排期器",
        "schedule_mode": schedule_mode,
        "schedule_label": schedule_label,
        "current_policy": current_policy,
        "recommended_policy": next_policy,
        "current_stage": current_stage,
        "next_stage": next_stage,
        "fallback_stage": fallback_stage,
        "measurement_plan": _measurement_plan(scorecard, experiment),
        "advance_when": _advance_when(schedule_mode),
        "hold_when": _hold_when(),
        "backoff_when": _backoff_when(),
        "scientific_note": (
            "排期器会先固定一个小周期，再用预先声明的检查点、升级条件和回退条件来判断下一步，"
            "避免看到一次波动就频繁改策略。"
        ),
        "clinical_disclaimer": (
            "策略排期器用于产品内干预版本管理与持续优化，不等于医疗或心理治疗方案。"
        ),
    }
