"""Experiment ledger for intervention policy learning."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RelationshipEvent
from app.core.time import current_local_date
from app.services.intervention_effectiveness import build_intervention_scorecard
from app.services.intervention_evaluation import build_intervention_evaluation
from app.services.intervention_theory import (
    build_evaluation_theory_basis,
    build_task_strategy_theory_basis,
)
from app.services.playbook_runtime import sync_active_playbook_runtime
from app.services.relationship_intelligence import record_relationship_event
from app.services.task_adaptation import compose_task_adaptation_strategy
from app.services.task_feedback import build_feedback_preference_profile

INTENSITY_LABELS = {
    "light": "减压版",
    "steady": "稳定版",
    "stretch": "进阶版",
}

COPY_MODE_LABELS = {
    "clear": "更具体",
    "gentle": "更温和",
    "compact": "更简短",
    "example": "带示例",
}

VERDICT_SCORE = {
    "negative_signal": 0,
    "insufficient_data": 1,
    "mixed_signal": 2,
    "positive_signal": 3,
}

COMPARISON_LABELS = {
    "first_observation": "当前还在建立第一条证据",
    "better_than_baseline": "当前策略比上一版更有起效迹象",
    "worse_than_baseline": "当前策略比上一版更弱",
    "similar_to_baseline": "当前和上一版暂时没有显著差异",
}


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _dedupe_theory_cards(cards: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for card in cards:
        key = str(card.get("id") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(card)
    return deduped


def _snapshot_scope_filters(
    *,
    pair_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    viewer_user_id: uuid.UUID | None,
):
    if pair_id:
        filters = [RelationshipEvent.pair_id == pair_id]
        if viewer_user_id:
            filters.append(RelationshipEvent.user_id == viewer_user_id)
        else:
            filters.append(RelationshipEvent.user_id.is_(None))
        return filters

    return [
        RelationshipEvent.pair_id.is_(None),
        RelationshipEvent.user_id == user_id,
    ]


def _copy_mode_label(copy_mode: str | None) -> str | None:
    if not copy_mode:
        return None
    return COPY_MODE_LABELS.get(copy_mode, copy_mode)


def _policy_signature(
    *,
    branch: str | None,
    intensity: str | None,
    copy_mode: str | None,
    category_copy_modes: dict[str, str] | None,
) -> str:
    parts = [
        f"branch:{branch or 'steady'}",
        f"intensity:{intensity or 'steady'}",
        f"copy:{copy_mode or 'default'}",
    ]
    for category in sorted((category_copy_modes or {}).keys()):
        parts.append(f"{category}:{category_copy_modes[category]}")
    return "|".join(parts)


def _policy_descriptor(playbook: dict | None, strategy: dict | None) -> dict:
    branch = str((playbook or {}).get("active_branch") or "steady")
    branch_label = str((playbook or {}).get("active_branch_label") or "稳步推进")
    intensity = str((strategy or {}).get("intensity") or "steady")
    intensity_label = INTENSITY_LABELS.get(intensity, intensity)
    copy_mode = (strategy or {}).get("copy_mode")
    category_preferences = (strategy or {}).get("category_preferences") or {}
    category_copy_modes = {
        str(category): str(value.get("copy_mode"))
        for category, value in category_preferences.items()
        if value.get("copy_mode")
    }
    copy_mode_label = _copy_mode_label(copy_mode)

    label_parts = [branch_label, intensity_label]
    if copy_mode_label:
        label_parts.append(copy_mode_label)

    return {
        "signature": _policy_signature(
            branch=branch,
            intensity=intensity,
            copy_mode=copy_mode,
            category_copy_modes=category_copy_modes,
        ),
        "label": " / ".join(label_parts),
        "branch": branch,
        "branch_label": branch_label,
        "intensity": intensity,
        "intensity_label": intensity_label,
        "copy_mode": copy_mode,
        "copy_mode_label": copy_mode_label,
        "category_copy_modes": category_copy_modes,
    }


def _current_observation(
    *,
    evaluation: dict,
    policy: dict,
    occurred_on: date,
) -> dict:
    return {
        "snapshot_key": (
            f"{evaluation['plan_id']}:{policy['signature']}:{occurred_on.isoformat()}"
        ),
        "observed_on": occurred_on.isoformat(),
        "summary": evaluation.get("summary"),
        "verdict": evaluation.get("verdict"),
        "verdict_label": evaluation.get("verdict_label"),
        "confidence_level": evaluation.get("confidence_level"),
        "confidence_label": evaluation.get("confidence_label"),
        "data_quality_level": evaluation.get("data_quality_level"),
        "data_quality_label": evaluation.get("data_quality_label"),
        "completion_rate": _to_float(
            _metric_current_value(evaluation, metric_id="task_completion")
        ),
        "risk_now": _metric_current_text(evaluation, metric_id="risk_shift"),
        "usefulness_avg": _fit_usefulness(evaluation),
        "friction_avg": _fit_friction(evaluation),
        "recommendation": evaluation.get("recommendation"),
        "recommendation_label": evaluation.get("recommendation_label"),
        "policy": policy,
    }


def _metric_by_id(evaluation: dict, metric_id: str) -> dict | None:
    for metric in evaluation.get("primary_metrics") or []:
        if str(metric.get("id")) == metric_id:
            return metric
    return None


def _metric_current_text(evaluation: dict, metric_id: str) -> str | None:
    metric = _metric_by_id(evaluation, metric_id)
    return str(metric.get("current")) if metric and metric.get("current") else None


def _metric_current_value(evaluation: dict, metric_id: str) -> float | None:
    metric = _metric_by_id(evaluation, metric_id)
    if not metric:
        return None
    current = str(metric.get("current") or "")
    if "/" in current:
        numerator, _, denominator = current.partition("/")
        try:
            numerator_value = float(numerator)
            denominator_value = float(denominator)
            if denominator_value <= 0:
                return None
            return round(numerator_value / denominator_value, 4)
        except ValueError:
            return None
    if current.endswith("%"):
        return _to_float(current.rstrip("%")) / 100.0
    return _to_float(current)


def _fit_usefulness(evaluation: dict) -> float | None:
    metric = _metric_by_id(evaluation, "subjective_fit")
    if not metric:
        return None
    current = str(metric.get("current") or "")
    if "有用度" not in current:
        return None
    try:
        usefulness = current.split("有用度", maxsplit=1)[1].split("/5", maxsplit=1)[0]
        return round(float(usefulness.strip()), 2)
    except (IndexError, ValueError):
        return None


def _fit_friction(evaluation: dict) -> float | None:
    metric = _metric_by_id(evaluation, "subjective_fit")
    if not metric:
        return None
    current = str(metric.get("current") or "")
    if "摩擦" not in current:
        return None
    try:
        friction = current.split("摩擦", maxsplit=1)[1].split("/5", maxsplit=1)[0]
        return round(float(friction.strip()), 2)
    except (IndexError, ValueError):
        return None


def _to_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _serialize_snapshot_event(event: RelationshipEvent) -> dict:
    payload = dict(event.payload or {})
    payload.setdefault("observed_on", event.occurred_at.date().isoformat())
    payload.setdefault("policy", {})
    return payload


def _dedupe_observations(observations: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for observation in observations:
        key = str(
            observation.get("snapshot_key")
            or f"{observation.get('observed_on')}:{(observation.get('policy') or {}).get('signature')}"
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(observation)
    return deduped


def _variant_summary(variant: dict) -> str:
    if variant["positive_count"] and not variant["negative_count"]:
        return "目前更多是正向信号。"
    if variant["negative_count"] and not variant["positive_count"]:
        return "目前更多是负向信号。"
    if variant["observation_count"] <= 1:
        return "还在积累第一批观测。"
    return "目前证据还偏混合，需要继续比较。"


def _aggregate_variants(
    observations: list[dict],
    *,
    current_signature: str,
) -> list[dict]:
    grouped: dict[str, dict] = {}
    for observation in observations:
        policy = observation.get("policy") or {}
        signature = str(policy.get("signature") or "")
        if not signature:
            continue

        bucket = grouped.setdefault(
            signature,
            {
                "signature": signature,
                "label": policy.get("label"),
                "branch": policy.get("branch"),
                "branch_label": policy.get("branch_label"),
                "intensity": policy.get("intensity"),
                "intensity_label": policy.get("intensity_label"),
                "copy_mode": policy.get("copy_mode"),
                "copy_mode_label": policy.get("copy_mode_label"),
                "observation_count": 0,
                "positive_count": 0,
                "mixed_count": 0,
                "negative_count": 0,
                "insufficient_count": 0,
                "_completion_values": [],
                "_usefulness_values": [],
                "_friction_values": [],
                "last_observed_on": observation.get("observed_on"),
                "latest_verdict": observation.get("verdict"),
                "latest_verdict_label": observation.get("verdict_label"),
            },
        )

        bucket["observation_count"] += 1
        verdict = str(observation.get("verdict") or "")
        if verdict == "positive_signal":
            bucket["positive_count"] += 1
        elif verdict == "negative_signal":
            bucket["negative_count"] += 1
        elif verdict == "mixed_signal":
            bucket["mixed_count"] += 1
        else:
            bucket["insufficient_count"] += 1

        completion_rate = _to_float(observation.get("completion_rate"))
        usefulness_avg = _to_float(observation.get("usefulness_avg"))
        friction_avg = _to_float(observation.get("friction_avg"))
        if completion_rate is not None:
            bucket["_completion_values"].append(completion_rate)
        if usefulness_avg is not None:
            bucket["_usefulness_values"].append(usefulness_avg)
        if friction_avg is not None:
            bucket["_friction_values"].append(friction_avg)

        if str(observation.get("observed_on") or "") >= str(bucket["last_observed_on"] or ""):
            bucket["last_observed_on"] = observation.get("observed_on")
            bucket["latest_verdict"] = observation.get("verdict")
            bucket["latest_verdict_label"] = observation.get("verdict_label")

    variants: list[dict] = []
    for variant in grouped.values():
        completion_values = variant.pop("_completion_values")
        usefulness_values = variant.pop("_usefulness_values")
        friction_values = variant.pop("_friction_values")
        variant["avg_completion_rate"] = (
            round(sum(completion_values) / len(completion_values), 4)
            if completion_values
            else None
        )
        variant["avg_usefulness"] = (
            round(sum(usefulness_values) / len(usefulness_values), 2)
            if usefulness_values
            else None
        )
        variant["avg_friction"] = (
            round(sum(friction_values) / len(friction_values), 2)
            if friction_values
            else None
        )
        variant["is_current"] = variant["signature"] == current_signature
        variant["summary"] = _variant_summary(variant)
        variants.append(variant)

    variants.sort(
        key=lambda item: (
            not item["is_current"],
            -int(item["observation_count"] or 0),
            -(VERDICT_SCORE.get(str(item.get("latest_verdict") or ""), 0)),
            str(item.get("last_observed_on") or ""),
        )
    )
    return variants


def _observation_score(observation: dict | None) -> int:
    if not observation:
        return 0
    return VERDICT_SCORE.get(str(observation.get("verdict") or ""), 0)


def _compare_observations(current: dict, previous: dict | None) -> tuple[str, str]:
    if not previous:
        return (
            "first_observation",
            "当前策略刚开始积累证据，先把今天这条观测当作基线，接下来再看 2 到 3 次连续结果。",
        )

    current_score = _observation_score(current)
    previous_score = _observation_score(previous)
    current_completion = _to_float(current.get("completion_rate"))
    previous_completion = _to_float(previous.get("completion_rate"))
    current_usefulness = _to_float(current.get("usefulness_avg"))
    previous_usefulness = _to_float(previous.get("usefulness_avg"))
    current_friction = _to_float(current.get("friction_avg"))
    previous_friction = _to_float(previous.get("friction_avg"))

    if (
        current_score > previous_score
        or (
            current_score == previous_score
            and current_completion is not None
            and previous_completion is not None
            and current_completion >= previous_completion + 0.15
        )
        or (
            current_usefulness is not None
            and previous_usefulness is not None
            and current_usefulness >= previous_usefulness + 0.6
        )
    ):
        return (
            "better_than_baseline",
            "和上一版相比，这一版策略更像在稳住执行和起效信号，值得先保留再继续观察。",
        )

    if (
        current_score < previous_score
        or (
            current_completion is not None
            and previous_completion is not None
            and current_completion <= previous_completion - 0.15
        )
        or (
            current_friction is not None
            and previous_friction is not None
            and current_friction >= previous_friction + 0.6
        )
    ):
        return (
            "worse_than_baseline",
            "和上一版相比，这一版策略更容易卡住或走弱，下一步更适合调强度或调表达，而不是继续硬推。",
        )

    return (
        "similar_to_baseline",
        "当前和上一版策略看起来差异还不大，需要更多连续观测才能判断到底哪种更合适。",
    )


def _build_hypothesis(current_policy: dict, evaluation: dict) -> str:
    branch_label = current_policy.get("branch_label") or "当前分支"
    intensity_label = current_policy.get("intensity_label") or "当前强度"
    copy_mode_label = current_policy.get("copy_mode_label")
    action_text = f"先用 {intensity_label} 节奏推进"
    if copy_mode_label:
        action_text += f"，并保持 {copy_mode_label} 的任务表达"

    recommendation = str(evaluation.get("recommendation") or "")
    if recommendation == "continue_current_plan":
        target = "稳住已经出现的正向信号，而不是频繁换方向"
    elif recommendation == "escalate_support":
        target = "尽快把风险拉回不继续升级的区间"
    elif recommendation == "collect_more_data":
        target = "先补够连续观测，再判断这套策略是否值得保留"
    else:
        target = "降低执行摩擦，同时看看完成率和主观有用度能不能一起抬起来"

    return f"当前假设：在“{branch_label}”分支下，{action_text}，更可能{target}。"


def _build_next_question(current_policy: dict, evaluation: dict) -> str:
    data_gaps = evaluation.get("data_gaps") or []
    if data_gaps:
        first_gap = str(data_gaps[0])
        if "反馈" in first_gap:
            return "下一步最关键的问题是：这套动作做完之后，用户主观上到底觉得有用还是只是更累？"
        if "观察期" in first_gap:
            return "下一步最关键的问题是：把这套策略连续跑满几天后，趋势会不会继续保持？"
    copy_mode_label = current_policy.get("copy_mode_label")
    if copy_mode_label:
        return f"下一步最关键的问题是：{copy_mode_label} 的表达方式，是否真的比上一版更容易被执行？"
    return "下一步最关键的问题是：当前强度已经合适，还是还需要再减一点负担？"


def _snapshot_payload(
    *,
    evaluation: dict,
    current_policy: dict,
    occurred_on: date,
) -> dict:
    observation = _current_observation(
        evaluation=evaluation,
        policy=current_policy,
        occurred_on=occurred_on,
    )
    observation["plan_type"] = evaluation.get("plan_type")
    observation["theory_basis"] = _dedupe_theory_cards(
        list(evaluation.get("theory_basis") or [])
        + build_task_strategy_theory_basis(
            plan_type=evaluation.get("plan_type"),
            intensity=current_policy.get("intensity"),
            copy_mode=current_policy.get("copy_mode"),
        )
    )
    return observation


async def build_intervention_experiment_ledger(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
    viewer_user_id: str | uuid.UUID | None = None,
    persist_snapshot: bool = False,
    history_limit: int = 8,
) -> dict | None:
    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    normalized_viewer_user_id = _normalize_uuid(viewer_user_id)

    if (normalized_pair_id is None) == (normalized_user_id is None):
        raise ValueError("build_intervention_experiment_ledger requires exactly one scope")

    evaluation = await build_intervention_evaluation(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
    )
    if not evaluation:
        return None

    playbook = await sync_active_playbook_runtime(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
        viewed=False,
    )

    if normalized_pair_id:
        scorecard = await build_intervention_scorecard(db, pair_id=normalized_pair_id)
        profile = await build_feedback_preference_profile(
            db,
            pair_id=normalized_pair_id,
            user_id=normalized_viewer_user_id,
        )
        strategy = compose_task_adaptation_strategy(scorecard, profile)
    else:
        scorecard = await build_intervention_scorecard(db, user_id=normalized_user_id)
        profile = await build_feedback_preference_profile(
            db,
            user_id=normalized_user_id,
        )
        strategy = compose_task_adaptation_strategy(scorecard, profile)

    if not scorecard:
        return None

    current_policy = _policy_descriptor(playbook, strategy)
    today = current_local_date()
    snapshot_payload = _snapshot_payload(
        evaluation=evaluation,
        current_policy=current_policy,
        occurred_on=today,
    )

    if persist_snapshot:
        await record_relationship_event(
            db,
            event_type="plan.evaluation_snapshot",
            pair_id=normalized_pair_id,
            user_id=normalized_viewer_user_id if normalized_pair_id else normalized_user_id,
            entity_type="intervention_plan",
            entity_id=evaluation["plan_id"],
            payload=snapshot_payload,
            idempotency_key=(
                f"plan-evaluation-snapshot:{evaluation['plan_id']}:"
                f"{current_policy['signature']}:{today.isoformat()}:"
                f"{normalized_viewer_user_id or normalized_user_id or normalized_pair_id}"
            ),
        )

    result = await db.execute(
        select(RelationshipEvent)
        .where(
            RelationshipEvent.event_type == "plan.evaluation_snapshot",
            RelationshipEvent.entity_type == "intervention_plan",
            RelationshipEvent.entity_id == str(evaluation["plan_id"]),
            *_snapshot_scope_filters(
                pair_id=normalized_pair_id,
                user_id=normalized_user_id,
                viewer_user_id=normalized_viewer_user_id,
            ),
        )
        .order_by(
            desc(RelationshipEvent.occurred_at),
            desc(RelationshipEvent.created_at),
        )
        .limit(max(history_limit * 2, 12))
    )
    snapshot_events = result.scalars().all()
    observations = _dedupe_observations(
        [_serialize_snapshot_event(event) for event in snapshot_events]
    )
    if not observations:
        observations = [snapshot_payload]

    current_key = str(snapshot_payload.get("snapshot_key"))
    matched_current = False
    for observation in observations:
        is_current = str(observation.get("snapshot_key")) == current_key
        observation["is_current"] = is_current
        matched_current = matched_current or is_current
    if not matched_current:
        snapshot_payload["is_current"] = True
        observations.insert(0, snapshot_payload)
        observations = _dedupe_observations(observations)

    current_observation = next(
        (observation for observation in observations if observation.get("is_current")),
        observations[0],
    )
    previous_observation = next(
        (
            observation
            for observation in observations
            if observation is not current_observation
            and (
                (observation.get("policy") or {}).get("signature")
                != (current_observation.get("policy") or {}).get("signature")
                or observation.get("observed_on") != current_observation.get("observed_on")
            )
        ),
        None,
    )
    comparison_status, comparison_summary = _compare_observations(
        current_observation,
        previous_observation,
    )

    variants = _aggregate_variants(
        observations,
        current_signature=str(current_policy.get("signature") or ""),
    )
    evidence_points = observations[:history_limit]

    theory_cards = _dedupe_theory_cards(
        list(evaluation.get("theory_basis") or [])
        + build_task_strategy_theory_basis(
            plan_type=evaluation.get("plan_type"),
            intensity=current_policy.get("intensity"),
            copy_mode=current_policy.get("copy_mode"),
        )
        + build_evaluation_theory_basis()
    )

    return {
        "plan_id": evaluation["plan_id"],
        "pair_id": normalized_pair_id,
        "user_id": normalized_viewer_user_id if normalized_pair_id else normalized_user_id,
        "plan_type": evaluation["plan_type"],
        "experiment_model": "single_case_policy_learning",
        "experiment_label": "单案例策略实验账本",
        "hypothesis": _build_hypothesis(current_policy, evaluation),
        "current_policy": current_policy,
        "comparison_status": comparison_status,
        "comparison_label": COMPARISON_LABELS[comparison_status],
        "comparison_summary": comparison_summary,
        "recommendation": evaluation.get("recommendation"),
        "recommendation_label": evaluation.get("recommendation_label"),
        "recommendation_reason": evaluation.get("recommendation_reason"),
        "evidence_points": evidence_points,
        "strategy_variants": variants,
        "next_question": _build_next_question(current_policy, evaluation),
        "scientific_note": (
            "这一层不是只看一次结果，而是把同一对关系在不同策略下的连续观测记成账本，"
            "逐步比较哪种强度、分支和表达方式更容易起效。"
        ),
        "clinical_disclaimer": (
            "实验账本用于帮助产品内方案做持续微调，不是医学诊断、心理治疗或正式临床研究结论。"
        ),
        "theory_basis": theory_cards,
    }
