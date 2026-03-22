"""Adaptive daily-task shaping based on intervention momentum."""

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intervention_effectiveness import build_intervention_scorecard
from app.services.task_feedback import build_feedback_preference_profile
from app.services.intervention_theory import build_task_strategy_theory_basis


def _normalize_uuid(value: str | uuid.UUID) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _anchor_task_for_plan(plan_type: str | None, intensity: str) -> dict | None:
    anchors = {
        "low_connection_recovery": {
            "light": {
                "title": "只做一次低压力连接",
                "description": "今晚只约一个 10 分钟的小连接，不追求聊深，只先把节奏接上。",
                "target": "both",
                "category": "connection",
            },
            "steady": {
                "title": "恢复一次稳定连线",
                "description": "安排一段不会被打断的 10 到 15 分钟交流，先把今天最想被理解的一点说清楚。",
                "target": "both",
                "category": "communication",
            },
            "stretch": {
                "title": "完成一次高质量连线",
                "description": "今晚做一次 15 分钟高质量交流，除了近况，也补一句最近最感谢对方的地方。",
                "target": "both",
                "category": "communication",
            },
        },
        "conflict_repair_plan": {
            "light": {
                "title": "先暂停升级",
                "description": "今天先不求讲清全部问题，只保留一个降温动作，比如暂停争执或确认稍后再聊。",
                "target": "both",
                "category": "repair",
            },
            "steady": {
                "title": "只对齐一个分歧点",
                "description": "选一个最核心的误会来讲，先说感受，再说需求，不顺手带出第二件事。",
                "target": "both",
                "category": "repair",
            },
            "stretch": {
                "title": "做一次结构化修复对话",
                "description": "安排一次 15 分钟修复对话，按事实、感受、需求的顺序说，并在最后确认下一步。",
                "target": "both",
                "category": "repair",
            },
        },
        "distance_compensation_plan": {
            "light": {
                "title": "先固定一次陪伴动作",
                "description": "今天先定下一次可兑现的异地陪伴，不需要复杂，只要可执行。",
                "target": "both",
                "category": "activity",
            },
            "steady": {
                "title": "补一次远程陪伴",
                "description": "今晚完成一次短但稳定的远程陪伴，比如视频、共看或同步吃饭。",
                "target": "both",
                "category": "activity",
            },
            "stretch": {
                "title": "做一次带仪式感的异地连接",
                "description": "把远程交流升级成一次有主题的小约会，并在结束时约好下一次节奏。",
                "target": "both",
                "category": "activity",
            },
        },
        "self_regulation_plan": {
            "light": {
                "title": "先做一件最轻的自我照顾",
                "description": "今天先完成一个 10 分钟的自我调节动作，比如散步、深呼吸或写一句感受。",
                "target": "both",
                "category": "reflection",
            },
            "steady": {
                "title": "记录并照顾自己的节律",
                "description": "今天先看见自己最容易被触发的时刻，再配一个可以执行的稳定动作。",
                "target": "both",
                "category": "reflection",
            },
            "stretch": {
                "title": "完成一次带复盘的自我调节",
                "description": "今天做完调节动作后，再记一句什么方式最能让自己慢下来。",
                "target": "both",
                "category": "reflection",
            },
        },
    }
    plan_anchors = anchors.get(plan_type or "")
    if not plan_anchors:
        return None
    return dict(plan_anchors.get(intensity, plan_anchors.get("steady")))


def _dedupe_tasks(tasks: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[str] = set()
    for task in tasks:
        title = str(task.get("title") or "").strip()
        key = title.lower()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(task)
    return deduped


def _with_copy_preference(strategy: dict, profile: dict | None) -> dict:
    updated = dict(strategy)
    profile = profile or {}
    updated["copy_mode"] = profile.get("copy_mode")
    updated["copy_feedback_count"] = int(profile.get("copy_feedback_count") or 0)
    updated["copy_usefulness_avg"] = profile.get("usefulness_avg")
    updated["copy_friction_avg"] = profile.get("friction_avg")
    updated["category_preferences"] = dict(profile.get("category_preferences") or {})
    updated["theory_basis"] = build_task_strategy_theory_basis(
        plan_type=updated.get("plan_type"),
        intensity=updated.get("intensity", "steady"),
        copy_mode=updated.get("copy_mode"),
    )
    updated["clinical_disclaimer"] = (
        "任务引擎当前基于行为科学与反馈闭环做强度调整，不等于正式治疗方案，重点是提升真实执行和关系修复概率。"
    )
    return updated


def compose_task_adaptation_strategy(
    scorecard: dict | None,
    profile: dict | None = None,
) -> dict:
    return _with_copy_preference(
        build_task_adaptation_strategy(scorecard),
        profile,
    )


def build_task_adaptation_strategy(scorecard: dict | None) -> dict:
    if not scorecard:
        return {
            "intensity": "steady",
            "label": "稳定版",
            "momentum": "none",
            "task_limit": 3,
            "plan_type": None,
            "reason": "当前还没有明确干预计划，先按正常节奏给出日常任务。",
            "support_message": "先保持稳定记录和轻量互动，系统会随着你们的数据越来越懂节奏。",
        }

    momentum = scorecard.get("momentum") or "mixed"
    risk_now = str(scorecard.get("risk_now") or "none")
    plan_type = scorecard.get("plan_type")
    completion_rate = float(scorecard.get("completion_rate") or 0.0)
    usefulness_avg = scorecard.get("usefulness_avg")
    friction_avg = scorecard.get("friction_avg")
    feedback_count = int(scorecard.get("feedback_count") or 0)

    if (
        momentum == "stalled"
        or risk_now in ("moderate", "severe")
        or (feedback_count >= 2 and friction_avg is not None and float(friction_avg) >= 3.6)
        or (feedback_count >= 2 and usefulness_avg is not None and float(usefulness_avg) <= 2.8)
    ):
        return {
            "intensity": "light",
            "label": "减压版",
            "momentum": momentum,
            "task_limit": 2,
            "plan_type": plan_type,
            "reason": "最近执行阻力或主观效果不理想，系统会先把动作减轻，优先让这轮计划重新跑起来。",
            "support_message": "今天不用贪多，只把最小的一步完成就够了。",
        }

    if (
        momentum == "improving"
        and risk_now in ("none", "mild")
        and completion_rate >= 0.5
        and (usefulness_avg is None or float(usefulness_avg) >= 4.0)
        and (friction_avg is None or float(friction_avg) <= 2.8)
    ):
        return {
            "intensity": "stretch",
            "label": "进阶版",
            "momentum": momentum,
            "task_limit": 3,
            "plan_type": plan_type,
            "reason": "这轮动作已经开始起效，而且主观反馈也不错，可以在不打乱节奏的前提下，把任务稍微做深一点。",
            "support_message": "现在最适合保留有效动作，再往前多走半步。",
        }

    return {
        "intensity": "steady",
        "label": "稳定版",
        "momentum": momentum,
        "task_limit": 3,
        "plan_type": plan_type,
        "reason": "系统会继续沿着当前计划稳步推进，避免忽轻忽重。",
        "support_message": "先把稳定执行做出来，效果通常会比频繁换方向更好。",
    }


def _compact_task_description(description: str) -> str:
    text = (description or "").strip()
    if not text:
        return ""

    first_sentence = re.split(r"[。！？!?]", text)[0].strip()
    duration_match = re.search(r"(\d+\s*分钟)", text)
    if duration_match and duration_match.group(1) not in first_sentence:
        first_sentence = f"{first_sentence}（{duration_match.group(1)}）"
    return f"{first_sentence}。"


def _example_opening(task: dict, strategy: dict) -> str:
    category = str(task.get("category") or "")
    plan_type = str(strategy.get("plan_type") or "")
    if category == "repair" or plan_type == "conflict_repair_plan":
        return "我想先把今天最容易误会的那一点说清楚。"
    if category == "reflection" or plan_type == "self_regulation_plan":
        return "我现在的状态是这样，我想先照顾好自己再继续。"
    if category == "activity" or plan_type == "distance_compensation_plan":
        return "今晚我们先约一个能兑现的小陪伴，好吗？"
    return "我想先花十分钟认真和你连一下。"


def personalize_task_payloads(tasks: list[dict], strategy: dict) -> list[dict]:
    personalized: list[dict] = []
    category_preferences = strategy.get("category_preferences") or {}
    for task in tasks:
        updated = dict(task)
        category = str(updated.get("category") or "").strip().lower()
        category_preference = category_preferences.get(category) or {}
        copy_mode = category_preference.get("copy_mode") or strategy.get("copy_mode")
        if not copy_mode:
            personalized.append(updated)
            continue

        description = str(updated.get("description") or "").strip()
        if copy_mode == "clear" and description:
            updated["description"] = f"先只做这一件事：{description.rstrip('。')}。做到这一步就算完成。"
        elif copy_mode == "gentle" and description:
            updated["description"] = f"{description.rstrip('。')}。如果今天状态一般，做到一半也算推进。"
        elif copy_mode == "compact":
            updated["description"] = _compact_task_description(description)
        elif copy_mode == "example":
            example = _example_opening(updated, strategy)
            if description:
                updated["description"] = f"{description.rstrip('。')}。可以直接这样开口：{example}"
            else:
                updated["description"] = example

        updated["copy_mode"] = copy_mode
        updated["copy_mode_source"] = "category" if category_preference.get("copy_mode") else "global"
        personalized.append(updated)

    return personalized


def adapt_daily_tasks(tasks_data: list[dict], strategy: dict) -> list[dict]:
    tasks = [dict(task) for task in (tasks_data or []) if isinstance(task, dict)]
    anchor = _anchor_task_for_plan(
        strategy.get("plan_type"),
        strategy.get("intensity", "steady"),
    )
    if anchor:
        tasks.insert(0, anchor)

    tasks = _dedupe_tasks(tasks)
    limit = int(strategy.get("task_limit") or 3)
    tasks = tasks[:limit]

    intensity = strategy.get("intensity", "steady")
    adapted: list[dict] = []
    for index, task in enumerate(tasks):
        updated = dict(task)
        description = str(updated.get("description") or "").strip()
        if intensity == "light":
            if index == 0:
                updated["description"] = (
                    f"{description.rstrip('。') or '先把这一步做完'}。今天只要先做到这一件，就已经算有效推进。"
                )
            else:
                updated["description"] = (
                    f"{description.rstrip('。') or '把动作尽量做轻一点'}。如果今天状态一般，只完成前一项也可以。"
                )
        elif intensity == "stretch" and index == len(tasks) - 1:
            updated["description"] = (
                f"{description.rstrip('。') or '做完后多复盘一句'}。完成后再补一句什么方式最容易被接住。"
            )
        adapted.append(updated)

    if intensity == "stretch" and len(adapted) < 3:
        adapted.append(
            {
                "title": "补一句微复盘",
                "description": "今天的任务完成后，各自补一句最被接住或最需要调整的地方。",
                "target": "both",
                "category": "reflection",
            }
        )

    return adapted[:limit]


def merge_task_insight(base_insight: str, strategy: dict) -> str:
    base = (base_insight or "").strip()
    support = str(strategy.get("support_message") or "").strip()
    if base and support:
        return f"{base} {support}"
    return base or support


async def build_pair_task_adaptation(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID,
    user_id: str | uuid.UUID | None = None,
) -> tuple[dict, dict | None]:
    normalized_pair_id = _normalize_uuid(pair_id)
    scorecard = await build_intervention_scorecard(db, pair_id=normalized_pair_id)
    profile = await build_feedback_preference_profile(
        db,
        pair_id=normalized_pair_id,
        user_id=user_id,
    )
    strategy = compose_task_adaptation_strategy(
        scorecard,
        profile,
    )
    from app.services.policy_selection import apply_experiment_policy_selection

    strategy = await apply_experiment_policy_selection(
        db,
        pair_id=normalized_pair_id,
        viewer_user_id=_normalize_uuid(user_id) if user_id else None,
        scorecard=scorecard,
        base_strategy=strategy,
    )
    from app.services.policy_scheduling import build_policy_schedule_preview

    schedule_preview = build_policy_schedule_preview(
        scorecard=scorecard,
        strategy=strategy,
    )
    if schedule_preview:
        strategy["policy_schedule"] = schedule_preview
    return strategy, scorecard
