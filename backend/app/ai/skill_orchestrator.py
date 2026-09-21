"""分析任务调度：识别用户需求，按依赖顺序调用 Skill，汇总分析结果。"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.ai import chat_completion
from app.ai.policy import compose_relationship_system_prompt
from app.ai.skill_registry import (
    SKILL_REGISTRY,
    SkillOutput,
    execute_skill,
    resolve_execution_levels,
)
from app.ai.skill_delivery import (
    DeliveryPackage,
    SkillStep,
    assemble_delivery_package,
)
from app.ai.skills import parse_json_safe
from app.core.config import settings

# 确保 Skills 被注册
import app.ai.skills  # noqa: F401

logger = logging.getLogger(__name__)

# 整次分析的超时时间
MAX_ORCHESTRATION_TIMEOUT = 90.0


COMPLEXITY_JUDGE_PROMPT = compose_relationship_system_prompt(
    """你是亲健平台的意图判断器。判断用户输入是否是一个需要深度分析的复杂关系事件。

判断标准：
- 涉及多人关系或多个事件 → 复杂
- 包含冲突、矛盾或情绪困扰 → 复杂
- 用户明确在寻求处理方案 → 复杂
- 简单问候、闲聊、单句提问 → 简单

请只输出 JSON（不要包含其他文字）：
{
  "is_complex": true/false,
  "reason": "判断依据（20字内）",
  "suggested_skills": ["需要用到的skill名称列表"],
  "primary_intent": "listen/clarify/resolve/plan/review（倾听/澄清/解决/规划/复盘）"
}

可选的 skill 名称：expression_clarify, stance_analysis, conflict_detect, action_plan, draft_message, review, memory_write"""
)


# 不同意图对应的默认 Skill 组合
INTENT_SKILL_PRESETS: dict[str, list[str]] = {
    "resolve": [
        "expression_clarify", "stance_analysis", "conflict_detect",
        "action_plan", "memory_write",
    ],
    "clarify": ["expression_clarify", "stance_analysis", "memory_write"],
    "plan": [
        "expression_clarify", "conflict_detect",
        "action_plan", "memory_write",
    ],
    "review": ["expression_clarify", "review", "memory_write"],
    "listen": ["expression_clarify", "memory_write"],
}


@dataclass
class OrchestrationPlan:
    """分析任务及其执行顺序。"""
    is_complex: bool
    primary_intent: str
    skill_names: list[str]
    execution_order: list[str] = field(default_factory=list)
    reason: str = ""


def _plan_execution_levels(skill_names: list[str]) -> list[list[str]]:
    """生成分层执行计划：同层无依赖可并行，memory_write 恒为最后一层。

    memory_write 是聚合器，会汇总所有前置 Skill 的输出；
    若按普通拓扑排序执行，它会先于 stance/conflict/action 等分析类 Skill，
    导致记忆提取漏掉后半段分析结果，因此强制调度到最后。
    """
    try:
        levels = resolve_execution_levels(skill_names)
    except ValueError:
        levels = [[name] for name in skill_names]

    if any("memory_write" in level for level in levels):
        levels = [
            [name for name in level if name != "memory_write"]
            for level in levels
        ]
        levels = [level for level in levels if level]
        levels.append(["memory_write"])

    return levels


def _plan_from_intent(intent: str) -> OrchestrationPlan:
    """已知用户意图时，直接安排分析步骤，不再调用模型判断意图。"""
    resolved_intent = intent if intent in INTENT_SKILL_PRESETS else "resolve"
    skills = list(INTENT_SKILL_PRESETS[resolved_intent])
    levels = _plan_execution_levels(skills)
    return OrchestrationPlan(
        is_complex=True,
        primary_intent=resolved_intent,
        skill_names=skills,
        execution_order=[name for level in levels for name in level],
        reason="调用方已指定意图",
    )


async def judge_complexity(user_input: str) -> OrchestrationPlan:
    """由模型判断问题是否复杂，以及需要调用哪些分析模块。"""
    messages = [
        {"role": "system", "content": COMPLEXITY_JUDGE_PROMPT},
        {"role": "user", "content": user_input},
    ]
    try:
        result = await chat_completion(
            settings.AI_TEXT_MODEL, messages, temperature=0.1,
        )
        parsed = parse_json_safe(result)
        if "is_complex" not in parsed:
            raise ValueError("意图判断器未返回有效 JSON")
    except Exception:
        # 解析失败时默认当作复杂事件处理
        parsed = {
            "is_complex": True,
            "reason": "默认进入深度分析",
            "suggested_skills": INTENT_SKILL_PRESETS["resolve"],
            "primary_intent": "resolve",
        }

    is_complex = bool(parsed.get("is_complex", True))
    intent = str(parsed.get("primary_intent", "resolve"))
    if intent not in INTENT_SKILL_PRESETS:
        intent = "resolve"

    suggested = parsed.get("suggested_skills") or []
    # 如果模型未返回有效的分析模块列表，则使用预设模块
    valid_skills = [s for s in suggested if s in SKILL_REGISTRY]
    if not valid_skills:
        valid_skills = INTENT_SKILL_PRESETS.get(intent, INTENT_SKILL_PRESETS["resolve"])

    levels = _plan_execution_levels(valid_skills)
    execution_order = [name for level in levels for name in level]

    return OrchestrationPlan(
        is_complex=is_complex,
        primary_intent=intent,
        skill_names=valid_skills,
        execution_order=execution_order,
        reason=str(parsed.get("reason", "")),
    )


async def orchestrate(
    user_input: str,
    *,
    pair_id: str | None = None,
    user_id: str | None = None,
    selected_proposal_id: str | None = None,
    relationship_memories: list[dict[str, Any]] | None = None,
    intent: str | None = None,
) -> DeliveryPackage:
    """按依赖顺序调用分析模块，并汇总结果。

    Args:
        intent: 调用方已知的意图（listen/clarify/resolve/plan/review）。
            提供此参数时按预设步骤执行；未提供时先由模型判断意图。

    Returns:
        DeliveryPackage：汇总后的分析结果和建议
    """
    started = time.monotonic()

    known_intent = intent if intent in INTENT_SKILL_PRESETS else None
    plan = _plan_from_intent(known_intent) if known_intent else await judge_complexity(user_input)

    context: dict[str, Any] = {
        "user_input": user_input,
        "pair_id": pair_id,
        "user_id": user_id,
        "selected_proposal_id": selected_proposal_id or "A",
        "relationship_memories": relationship_memories or [],
    }

    # 没有依赖关系的任务并行执行；后一组等待前一组完成。
    results: dict[str, SkillOutput] = {}
    skill_steps: list[SkillStep] = []
    levels = _plan_execution_levels(plan.skill_names)
    timed_out = False

    for level in levels:
        pending = [SKILL_REGISTRY[name] for name in level if name in SKILL_REGISTRY]
        if not pending:
            continue

        elapsed = time.monotonic() - started
        if timed_out or elapsed > MAX_ORCHESTRATION_TIMEOUT:
            timed_out = True
            for skill in pending:
                logger.warning(
                    "Orchestration timeout, skipping skill %s (elapsed %.1fs)",
                    skill.name, elapsed,
                )
                skill_steps.append(SkillStep(
                    skill_name=skill.name,
                    skill_label=skill.label,
                    status="skipped",
                    reason="分析步骤执行超时",
                ))
            continue

        outputs = await asyncio.gather(*[
            execute_skill(skill, context=context, previous_results=results)
            for skill in pending
        ])
        for skill, output in zip(pending, outputs):
            results[skill.name] = output
            skill_steps.append(SkillStep(
                skill_name=skill.name,
                skill_label=skill.label,
                status="ok" if output.success else "error",
                duration_ms=output.duration_ms,
                reason=output.error,
            ))

    total_duration = (time.monotonic() - started) * 1000
    return assemble_delivery_package(
        results=results,
        skill_steps=skill_steps,
        plan=plan,
        total_duration_ms=total_duration,
    )


async def generate_draft_for_proposal(
    user_input: str,
    proposal_id: str,
    *,
    analysis_results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """用户选择方案后，单独调用沟通草稿 Skill。"""
    context = {
        "user_input": user_input,
        "selected_proposal_id": proposal_id,
    }

    previous: dict[str, SkillOutput] = {}
    if analysis_results:
        for name, data in analysis_results.items():
            previous[name] = SkillOutput(
                skill_name=name, success=True, data=data,
            )

    skill = SKILL_REGISTRY.get("draft_message")
    if not skill:
        return {"error": "沟通草稿模块不可用"}

    output = await execute_skill(skill, context=context, previous_results=previous)
    return output.data if output.success else {"error": output.error}
