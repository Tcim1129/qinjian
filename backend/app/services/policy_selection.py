"""Conservative policy selection based on experiment evidence."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intervention_experimentation import (
    build_intervention_experiment_ledger,
)
from app.services.intervention_theory import build_task_strategy_theory_basis

INTENSITY_LABELS = {
    "light": "减压版",
    "steady": "稳定版",
    "stretch": "进阶版",
}

INTENSITY_RANK = {
    "light": 0,
    "steady": 1,
    "stretch": 2,
}

SELECTION_LABELS = {
    "keep_current": "保持当前策略",
    "observe_more": "继续观察",
    "adopt_proven_variant": "切到更稳的已验证策略",
    "backoff_to_lower_friction": "回退到更低摩擦版本",
    "adopt_proven_copy": "沿用更有效的表达方式",
}


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _variant_score(variant: dict) -> float:
    positive = float(variant.get("positive_count") or 0)
    mixed = float(variant.get("mixed_count") or 0)
    negative = float(variant.get("negative_count") or 0)
    insufficient = float(variant.get("insufficient_count") or 0)
    observation_count = float(variant.get("observation_count") or 0)
    completion = float(variant.get("avg_completion_rate") or 0.0)
    usefulness = float(variant.get("avg_usefulness") or 0.0)
    friction = float(variant.get("avg_friction") or 3.0)
    return round(
        positive * 3.0
        + mixed * 1.0
        - negative * 3.0
        - insufficient * 0.5
        + min(observation_count, 4) * 0.35
        + completion * 2.0
        + usefulness * 0.35
        - friction * 0.2,
        4,
    )


def _variant_is_eligible(variant: dict) -> bool:
    if int(variant.get("observation_count") or 0) < 2:
        return False
    if int(variant.get("negative_count") or 0) >= max(
        int(variant.get("positive_count") or 0),
        1,
    ):
        return False
    if str(variant.get("latest_verdict") or "") == "negative_signal":
        return False
    return True


def _select_best_candidate(variants: list[dict], current_signature: str) -> dict | None:
    candidates = [
        variant
        for variant in variants
        if variant.get("signature") != current_signature and _variant_is_eligible(variant)
    ]
    if not candidates:
        return None
    return max(candidates, key=_variant_score)


def _selection_reason(
    *,
    mode: str,
    current_policy: dict,
    candidate: dict | None,
    comparison_summary: str,
) -> str:
    if mode == "adopt_proven_copy" and candidate:
        return (
            f"当前更像是表达方式卡住了，系统先沿用更有证据的“{candidate.get('copy_mode_label') or '任务表达'}”，"
            f"避免继续在低效写法上消耗。{comparison_summary}"
        )
    if mode == "backoff_to_lower_friction" and candidate:
        return (
            f"当前策略阻力偏大，系统先回退到更低摩擦的“{candidate.get('label') or '已验证策略'}”，"
            f"优先把执行重新拉起来。{comparison_summary}"
        )
    if mode == "adopt_proven_variant" and candidate:
        return (
            f"当前策略已经出现走弱迹象，系统先切到证据更稳的“{candidate.get('label') or '已验证策略'}”，"
            f"看看能不能更快稳住结果。{comparison_summary}"
        )
    if mode == "observe_more":
        return (
            "现有替代策略证据还不够厚，系统暂时不自动切换，先继续积累 2 到 3 次连续观测。"
        )
    return (
        f"当前策略还没有出现足够强的负向信号，系统先保留“{current_policy.get('label') or '当前策略'}”，"
        "避免为了微小波动频繁改方向。"
    )


def _selection_support(mode: str, intensity: str) -> str:
    if mode == "backoff_to_lower_friction":
        return "先把动作做轻、做稳，等执行重新起来，再判断要不要继续加码。"
    if intensity == "stretch":
        return "现在更适合在稳住有效动作的基础上，多往前走半步。"
    if intensity == "light":
        return "今天先把最小一步做完就够了，目标是恢复可执行性。"
    return "先把稳定执行做出来，效果通常比频繁换方向更好。"


def _policy_selection_payload(
    *,
    mode: str,
    current_policy: dict,
    candidate: dict | None,
    experiment: dict,
) -> dict:
    return {
        "mode": mode,
        "label": SELECTION_LABELS[mode],
        "auto_applied": mode in (
            "adopt_proven_variant",
            "backoff_to_lower_friction",
            "adopt_proven_copy",
        ),
        "reason": _selection_reason(
            mode=mode,
            current_policy=current_policy,
            candidate=candidate,
            comparison_summary=str(experiment.get("comparison_summary") or ""),
        ),
        "comparison_status": experiment.get("comparison_status"),
        "comparison_label": experiment.get("comparison_label"),
        "current_policy_label": current_policy.get("label"),
        "current_policy_signature": current_policy.get("signature"),
        "selected_policy_label": (candidate or current_policy).get("label"),
        "selected_policy_signature": (candidate or current_policy).get("signature"),
        "evidence_observation_count": int((candidate or current_policy).get("observation_count") or 0),
        "next_question": experiment.get("next_question"),
    }


def _should_switch(
    *,
    experiment: dict,
    scorecard: dict | None,
    current_variant: dict | None,
    candidate: dict | None,
) -> str:
    if not candidate:
        return "observe_more"

    recommendation = str(experiment.get("recommendation") or "")
    comparison_status = str(experiment.get("comparison_status") or "")
    current_score = _variant_score(current_variant or {})
    candidate_score = _variant_score(candidate)
    current_friction = float((current_variant or {}).get("avg_friction") or 0.0)
    candidate_friction = float(candidate.get("avg_friction") or 0.0)
    current_intensity = str((current_variant or {}).get("intensity") or "steady")
    candidate_intensity = str(candidate.get("intensity") or "steady")
    current_copy = str((current_variant or {}).get("copy_mode") or "")
    candidate_copy = str(candidate.get("copy_mode") or "")

    current_verdict = str((current_variant or {}).get("latest_verdict") or "")
    needs_change = (
        recommendation in ("adapt_plan", "escalate_support")
        or comparison_status == "worse_than_baseline"
        or current_verdict == "negative_signal"
        or (current_verdict == "mixed_signal" and current_friction >= 3.6)
    )

    clearly_better = (
        candidate_score >= current_score + 1.1
        or (
            float(candidate.get("avg_completion_rate") or 0.0)
            >= float((current_variant or {}).get("avg_completion_rate") or 0.0) + 0.18
        )
        or (
            float(candidate.get("avg_usefulness") or 0.0)
            >= float((current_variant or {}).get("avg_usefulness") or 0.0) + 0.7
        )
        or (
            candidate_friction > 0
            and current_friction >= candidate_friction + 0.7
        )
    )

    if not needs_change or not clearly_better:
        if comparison_status == "first_observation":
            return "observe_more"
        return "keep_current"

    if candidate_intensity == current_intensity and candidate_copy and candidate_copy != current_copy:
        return "adopt_proven_copy"

    if INTENSITY_RANK.get(candidate_intensity, 1) < INTENSITY_RANK.get(current_intensity, 1):
        return "backoff_to_lower_friction"

    return "adopt_proven_variant"


def _apply_selected_variant(base_strategy: dict, candidate: dict | None, payload: dict) -> dict:
    selected = dict(base_strategy)
    selected["policy_selection"] = payload
    selected["experiment_summary"] = {
        "comparison_status": payload.get("comparison_status"),
        "comparison_label": payload.get("comparison_label"),
        "next_question": payload.get("next_question"),
    }

    if not payload.get("auto_applied") or not candidate:
        return selected

    intensity = str(candidate.get("intensity") or selected.get("intensity") or "steady")
    selected["intensity"] = intensity
    selected["label"] = INTENSITY_LABELS.get(intensity, intensity)
    selected["task_limit"] = 2 if intensity == "light" else 3
    selected["copy_mode"] = candidate.get("copy_mode") or selected.get("copy_mode")
    selected["selected_policy_signature"] = candidate.get("signature")
    selected["reason"] = payload.get("reason")
    selected["support_message"] = _selection_support(payload.get("mode"), intensity)

    category_preferences = {
        str(category): dict(value)
        for category, value in (selected.get("category_preferences") or {}).items()
    }
    for category, copy_mode in (candidate.get("category_copy_modes") or {}).items():
        entry = dict(category_preferences.get(str(category)) or {})
        entry["copy_mode"] = copy_mode
        category_preferences[str(category)] = entry
    selected["category_preferences"] = category_preferences
    selected["theory_basis"] = build_task_strategy_theory_basis(
        plan_type=selected.get("plan_type"),
        intensity=selected.get("intensity"),
        copy_mode=selected.get("copy_mode"),
    )
    return selected


def build_policy_selection_decision(
    *,
    experiment: dict,
    scorecard: dict | None,
) -> dict:
    current_policy = dict(experiment.get("current_policy") or {})
    variants = list(experiment.get("strategy_variants") or [])
    current_signature = str(current_policy.get("signature") or "")
    current_variant = next(
        (
            variant
            for variant in variants
            if variant.get("is_current")
            or (
                current_signature
                and str(variant.get("signature") or "") == current_signature
            )
        ),
        None,
    )
    candidate = _select_best_candidate(variants, current_signature)
    mode = _should_switch(
        experiment=experiment,
        scorecard=scorecard,
        current_variant=current_variant,
        candidate=candidate,
    )
    payload = _policy_selection_payload(
        mode=mode,
        current_policy=current_policy,
        candidate=candidate,
        experiment=experiment,
    )
    return {
        "mode": mode,
        "current_policy": current_policy,
        "current_variant": current_variant,
        "candidate": candidate,
        "payload": payload,
    }


async def apply_experiment_policy_selection(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID,
    viewer_user_id: str | uuid.UUID | None,
    scorecard: dict | None,
    base_strategy: dict,
) -> dict:
    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_viewer_user_id = _normalize_uuid(viewer_user_id)
    if not normalized_pair_id or not scorecard:
        strategy = dict(base_strategy)
        strategy["policy_selection"] = {
            "mode": "observe_more",
            "label": SELECTION_LABELS["observe_more"],
            "auto_applied": False,
            "reason": "当前还没有足够的计划证据，先按基础策略推进。",
        }
        return strategy

    experiment = await build_intervention_experiment_ledger(
        db,
        pair_id=normalized_pair_id,
        viewer_user_id=normalized_viewer_user_id,
        persist_snapshot=False,
    )
    if not experiment:
        strategy = dict(base_strategy)
        strategy["policy_selection"] = {
            "mode": "observe_more",
            "label": SELECTION_LABELS["observe_more"],
            "auto_applied": False,
            "reason": "当前还没有形成可比较的实验账本，先按基础策略推进。",
        }
        return strategy

    decision = build_policy_selection_decision(
        experiment=experiment,
        scorecard=scorecard,
    )
    candidate = decision.get("candidate")
    payload = decision.get("payload") or {}
    return _apply_selected_variant(base_strategy, candidate, payload)
