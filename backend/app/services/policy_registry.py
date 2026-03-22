"""Named policy registry for intervention variants."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InterventionPolicyLibrary
from app.services.intervention_effectiveness import build_intervention_scorecard
from app.services.intervention_experimentation import (
    build_intervention_experiment_ledger,
)

POLICY_REGISTRY = [
    {
        "policy_id": "lcr-stabilize-gentle",
        "plan_type": "low_connection_recovery",
        "title": "低压重连版",
        "summary": "先把误伤和压力降下来，先恢复可兑现的小连接。",
        "branch": "stabilize",
        "branch_label": "先稳住",
        "intensity": "light",
        "intensity_label": "减压版",
        "copy_mode": "gentle",
        "copy_mode_label": "更温和",
        "when_to_use": "最近连线容易变任务、情绪也偏绷时。",
        "success_marker": "双方愿意留下下一次连接窗口。",
        "guardrail": "不追求一次聊深，先把节奏接回来。",
    },
    {
        "policy_id": "lcr-steady-clear",
        "plan_type": "low_connection_recovery",
        "title": "稳定重连版",
        "summary": "用更具体的任务表达，把关系从断点拉回稳定节奏。",
        "branch": "steady",
        "branch_label": "稳步推进",
        "intensity": "steady",
        "intensity_label": "稳定版",
        "copy_mode": "clear",
        "copy_mode_label": "更具体",
        "when_to_use": "已经不那么紧绷，但还需要把动作做实的时候。",
        "success_marker": "完成率回到 50% 以上，低互动状态开始松动。",
        "guardrail": "一次只推一个连接动作，不要同时追太多目标。",
    },
    {
        "policy_id": "lcr-deepen-example",
        "plan_type": "low_connection_recovery",
        "title": "高质量连线版",
        "summary": "在已有节奏上再往前半步，用示例开场降低深聊门槛。",
        "branch": "deepen",
        "branch_label": "趁势加深",
        "intensity": "stretch",
        "intensity_label": "进阶版",
        "copy_mode": "example",
        "copy_mode_label": "带示例",
        "when_to_use": "完成率和有用度都已经开始变好之后。",
        "success_marker": "深聊率提升，同时关系健康分继续往上走。",
        "guardrail": "只有在前一版已经稳住时才升级，不要硬推。",
    },
    {
        "policy_id": "crp-stabilize-gentle",
        "plan_type": "conflict_repair_plan",
        "title": "冲突降温版",
        "summary": "先止损，不追求讲清所有问题，优先把升级停下来。",
        "branch": "stabilize",
        "branch_label": "先稳住",
        "intensity": "light",
        "intensity_label": "减压版",
        "copy_mode": "gentle",
        "copy_mode_label": "更温和",
        "when_to_use": "风险在中高位、任务摩擦也偏高时。",
        "success_marker": "风险不再继续升级，争执强度开始回落。",
        "guardrail": "暂不翻旧账，只处理最核心的一件事。",
    },
    {
        "policy_id": "crp-steady-clear",
        "plan_type": "conflict_repair_plan",
        "title": "结构修复版",
        "summary": "把事实、感受、需求拆开，用更具体的动作修复对话。",
        "branch": "steady",
        "branch_label": "稳步推进",
        "intensity": "steady",
        "intensity_label": "稳定版",
        "copy_mode": "clear",
        "copy_mode_label": "更具体",
        "when_to_use": "已经能回到对话桌，但仍容易说着说着跑偏时。",
        "success_marker": "修复动作能真正落地，而不是只停在表态。",
        "guardrail": "一轮只处理一个分歧点，避免议题膨胀。",
    },
    {
        "policy_id": "crp-deepen-example",
        "plan_type": "conflict_repair_plan",
        "title": "深度修复版",
        "summary": "在结构化修复基础上，再加入示例开场和复盘动作。",
        "branch": "deepen",
        "branch_label": "趁势加深",
        "intensity": "stretch",
        "intensity_label": "进阶版",
        "copy_mode": "example",
        "copy_mode_label": "带示例",
        "when_to_use": "争执已明显回落，想开始建立更好的修复习惯时。",
        "success_marker": "不仅吵得少了，复盘和补偿动作也能持续。",
        "guardrail": "如果风险重新上升，立刻回到降温版。",
    },
    {
        "policy_id": "dcp-reduce-load-gentle",
        "plan_type": "distance_compensation_plan",
        "title": "异地减负版",
        "summary": "先把远程陪伴做轻，避免补偿动作本身变成负担。",
        "branch": "reduce_load",
        "branch_label": "减压保节奏",
        "intensity": "light",
        "intensity_label": "减压版",
        "copy_mode": "gentle",
        "copy_mode_label": "更温和",
        "when_to_use": "异地联系时常断、双方又都比较累的时候。",
        "success_marker": "先稳定出现，再谈陪伴质量。",
        "guardrail": "先求可兑现，不求复杂。",
    },
    {
        "policy_id": "dcp-steady-clear",
        "plan_type": "distance_compensation_plan",
        "title": "异地稳定陪伴版",
        "summary": "把远程连接从随机补救，拉回到具体可执行的节律。",
        "branch": "steady",
        "branch_label": "稳步推进",
        "intensity": "steady",
        "intensity_label": "稳定版",
        "copy_mode": "clear",
        "copy_mode_label": "更具体",
        "when_to_use": "已经能稳定约上，但节奏还不够固定的时候。",
        "success_marker": "异地活动完成率上升，陪伴感开始变强。",
        "guardrail": "优先留住最容易兑现的一次，不要排太满。",
    },
    {
        "policy_id": "dcp-deepen-example",
        "plan_type": "distance_compensation_plan",
        "title": "异地仪式感版",
        "summary": "在稳定节律上增加主题感和示例开场，让连接更像一起生活。",
        "branch": "deepen",
        "branch_label": "趁势加深",
        "intensity": "stretch",
        "intensity_label": "进阶版",
        "copy_mode": "example",
        "copy_mode_label": "带示例",
        "when_to_use": "陪伴节律已经起来，想提升质量的时候。",
        "success_marker": "共同体验和期待感都开始增加。",
        "guardrail": "一旦兑现率下降，先回到稳定陪伴版。",
    },
    {
        "policy_id": "srp-reduce-load-gentle",
        "plan_type": "self_regulation_plan",
        "title": "自我调节缓冲版",
        "summary": "先把自我调节动作做轻，重点放在恢复可执行性。",
        "branch": "reduce_load",
        "branch_label": "减压保节奏",
        "intensity": "light",
        "intensity_label": "减压版",
        "copy_mode": "gentle",
        "copy_mode_label": "更温和",
        "when_to_use": "最近状态波动比较大、很容易中断的时候。",
        "success_marker": "先出现连续完成，而不是追求做很多。",
        "guardrail": "先稳定一天一个动作，不做大而全。",
    },
    {
        "policy_id": "srp-steady-compact",
        "plan_type": "self_regulation_plan",
        "title": "自我调节稳定版",
        "summary": "用更短更直接的动作提示，降低启动阻力。",
        "branch": "steady",
        "branch_label": "稳步推进",
        "intensity": "steady",
        "intensity_label": "稳定版",
        "copy_mode": "compact",
        "copy_mode_label": "更简短",
        "when_to_use": "已经能做起来，但还容易被复杂描述拖慢的时候。",
        "success_marker": "完成率和主观有用度一起稳定提升。",
        "guardrail": "不要把任务越写越长。",
    },
    {
        "policy_id": "srp-deepen-clear",
        "plan_type": "self_regulation_plan",
        "title": "自我调节进阶版",
        "summary": "在已有稳定动作上，再加入更具体的复盘要求。",
        "branch": "deepen",
        "branch_label": "趁势加深",
        "intensity": "stretch",
        "intensity_label": "进阶版",
        "copy_mode": "clear",
        "copy_mode_label": "更具体",
        "when_to_use": "已经能稳定执行，想进一步知道什么方法最适合自己时。",
        "success_marker": "不只做得完，还知道哪种调节最有效。",
        "guardrail": "一旦摩擦明显上升，退回稳定版。",
    },
]


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _policy_entry(entry: dict) -> dict:
    return dict(entry)


def _library_row_to_entry(row: InterventionPolicyLibrary) -> dict:
    return {
        "policy_id": row.policy_id,
        "plan_type": row.plan_type,
        "title": row.title,
        "summary": row.summary,
        "branch": row.branch,
        "branch_label": row.branch_label,
        "intensity": row.intensity,
        "intensity_label": row.intensity_label,
        "copy_mode": row.copy_mode,
        "copy_mode_label": row.copy_mode_label,
        "when_to_use": row.when_to_use,
        "success_marker": row.success_marker,
        "guardrail": row.guardrail,
        "version": row.version,
        "status": row.status,
        "source": row.source,
        "sort_order": row.sort_order,
        "metadata_json": dict(row.metadata_json or {}),
    }


async def ensure_policy_library_seeded(db: AsyncSession) -> None:
    existing_result = await db.execute(
        select(InterventionPolicyLibrary.policy_id)
    )
    existing_policy_ids = {str(policy_id) for policy_id in existing_result.scalars().all()}
    missing_entries = [
        entry for entry in POLICY_REGISTRY if entry["policy_id"] not in existing_policy_ids
    ]
    if not missing_entries:
        return

    for sort_order, entry in enumerate(POLICY_REGISTRY):
        if entry["policy_id"] in existing_policy_ids:
            continue
        db.add(
            InterventionPolicyLibrary(
                policy_id=entry["policy_id"],
                plan_type=entry["plan_type"],
                title=entry["title"],
                summary=entry["summary"],
                branch=entry["branch"],
                branch_label=entry["branch_label"],
                intensity=entry["intensity"],
                intensity_label=entry["intensity_label"],
                copy_mode=entry.get("copy_mode"),
                copy_mode_label=entry.get("copy_mode_label"),
                when_to_use=entry["when_to_use"],
                success_marker=entry["success_marker"],
                guardrail=entry["guardrail"],
                version="v1",
                status="active",
                source="seed",
                sort_order=sort_order,
            )
        )
    await db.flush()


async def list_registered_policies(
    db: AsyncSession,
    plan_type: str | None = None,
) -> list[dict]:
    entries: list[dict] = []
    try:
        await ensure_policy_library_seeded(db)
        result = await db.execute(
            select(InterventionPolicyLibrary)
            .where(InterventionPolicyLibrary.status == "active")
            .order_by(
                InterventionPolicyLibrary.sort_order.asc(),
                InterventionPolicyLibrary.policy_id.asc(),
            )
        )
        entries = [_library_row_to_entry(row) for row in result.scalars().all()]
    except SQLAlchemyError:
        entries = [_policy_entry(entry) for entry in POLICY_REGISTRY]

    if plan_type:
        entries = [entry for entry in entries if entry["plan_type"] == plan_type]
    return entries


async def match_registered_policy(
    db: AsyncSession,
    *,
    plan_type: str | None,
    branch: str | None,
    intensity: str | None,
    copy_mode: str | None,
) -> dict | None:
    if not plan_type:
        return None

    candidates = await list_registered_policies(db, plan_type)
    if not candidates:
        return None

    best_match: dict | None = None
    best_score = -1
    for candidate in candidates:
        score = 0
        if str(candidate.get("branch") or "") == str(branch or ""):
            score += 3
        if str(candidate.get("intensity") or "") == str(intensity or ""):
            score += 2
        if str(candidate.get("copy_mode") or "") == str(copy_mode or ""):
            score += 1
        if score > best_score:
            best_score = score
            best_match = candidate
    return _policy_entry(best_match) if best_match else None


def _observed_policy_card(policy: dict, observed_variant: dict | None) -> dict:
    card = dict(policy)
    observed_variant = observed_variant or {}
    card["observation_count"] = int(observed_variant.get("observation_count") or 0)
    card["latest_verdict"] = observed_variant.get("latest_verdict")
    card["latest_verdict_label"] = observed_variant.get("latest_verdict_label")
    card["avg_completion_rate"] = observed_variant.get("avg_completion_rate")
    card["avg_usefulness"] = observed_variant.get("avg_usefulness")
    card["avg_friction"] = observed_variant.get("avg_friction")
    card["summary_note"] = observed_variant.get("summary")
    card["signature"] = observed_variant.get("signature")
    return card


def _fallback_policy_card(experiment_policy: dict) -> dict:
    return {
        "policy_id": f"custom:{experiment_policy.get('signature') or 'current'}",
        "plan_type": None,
        "title": experiment_policy.get("label") or "当前策略",
        "summary": "这是一版尚未正式注册、但系统已经在使用的策略组合。",
        "branch": experiment_policy.get("branch"),
        "branch_label": experiment_policy.get("branch_label"),
        "intensity": experiment_policy.get("intensity"),
        "intensity_label": experiment_policy.get("intensity_label"),
        "copy_mode": experiment_policy.get("copy_mode"),
        "copy_mode_label": experiment_policy.get("copy_mode_label"),
        "when_to_use": "当前系统正在沿用这一版组合继续观察。",
        "success_marker": "看下一轮完成率、主观有用度和风险走势。",
        "guardrail": "如果结果走弱，优先回到注册表里更稳的版本。",
        "observation_count": 0,
        "latest_verdict": None,
        "latest_verdict_label": None,
        "avg_completion_rate": None,
        "avg_usefulness": None,
        "avg_friction": None,
        "summary_note": None,
        "signature": experiment_policy.get("signature"),
    }


async def build_policy_registry_snapshot(
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
        raise ValueError("build_policy_registry_snapshot requires exactly one scope")

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

    # Import locally to avoid a module cycle with the selector importing this registry.
    from app.services.policy_selection import build_policy_selection_decision

    decision = build_policy_selection_decision(experiment=experiment, scorecard=scorecard)
    current_policy = experiment.get("current_policy") or {}
    current_variant = decision.get("current_variant") or {}
    candidate = decision.get("candidate") or None
    payload = decision.get("payload") or {}

    current_registered = await match_registered_policy(
        db,
        plan_type=experiment.get("plan_type"),
        branch=current_policy.get("branch"),
        intensity=current_policy.get("intensity"),
        copy_mode=current_policy.get("copy_mode"),
    )
    current_card = _observed_policy_card(
        current_registered or _fallback_policy_card(current_policy),
        current_variant,
    )
    current_card["is_current"] = True

    recommended_card = None
    if candidate:
        recommended_registered = await match_registered_policy(
            db,
            plan_type=experiment.get("plan_type"),
            branch=candidate.get("branch"),
            intensity=candidate.get("intensity"),
            copy_mode=candidate.get("copy_mode"),
        )
        recommended_card = _observed_policy_card(
            recommended_registered or _fallback_policy_card(candidate),
            candidate,
        )
        recommended_card["is_recommended"] = True
        recommended_card["selection_reason"] = payload.get("reason")

    policies: list[dict] = []
    for policy in await list_registered_policies(db, experiment.get("plan_type")):
        observed_variant = next(
            (
                variant
                for variant in (experiment.get("strategy_variants") or [])
                if policy.get("branch") == variant.get("branch")
                and policy.get("intensity") == variant.get("intensity")
                and policy.get("copy_mode") == variant.get("copy_mode")
            ),
            None,
        )
        card = _observed_policy_card(policy, observed_variant)
        card["is_current"] = card["policy_id"] == current_card.get("policy_id")
        card["is_recommended"] = (
            recommended_card is not None
            and card["policy_id"] == recommended_card.get("policy_id")
        )
        if card["is_recommended"]:
            card["selection_reason"] = payload.get("reason")
        policies.append(card)

    if current_card.get("policy_id", "").startswith("custom:"):
        policies.insert(0, current_card)
    policies.sort(
        key=lambda item: (
            not item.get("is_current"),
            not item.get("is_recommended"),
            -int(item.get("observation_count") or 0),
            str(item.get("policy_id") or ""),
        )
    )

    return {
        "plan_id": experiment["plan_id"],
        "pair_id": experiment.get("pair_id"),
        "user_id": experiment.get("user_id"),
        "plan_type": experiment["plan_type"],
        "registry_label": "策略注册表",
        "selection_mode": payload.get("mode"),
        "selection_label": payload.get("label"),
        "selection_reason": payload.get("reason"),
        "current_policy": current_card,
        "recommended_policy": recommended_card,
        "policies": policies,
        "scientific_note": (
            "注册表把系统可选策略正式命名出来，便于持续比较“哪一版在什么情境下更有效”，"
            "避免自动选策只剩下一串难读的技术签名。"
        ),
        "clinical_disclaimer": (
            "策略注册表用于产品内方案版本管理和持续优化，不等于医学诊疗路径。"
        ),
    }
