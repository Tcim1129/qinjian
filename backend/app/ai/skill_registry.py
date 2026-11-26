"""Skill 注册表：声明各 Skill 的处理函数、依赖与超时，并解析执行顺序。"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

SKILL_OUTPUT_FIELDS = {
    'expression_clarify': {'people': list, 'events': list, 'user_emotion': str, 'core_need': str},
    'stance_analysis': {'stances': list, 'common_ground': str, 'core_tension': str, 'power_dynamic': str},
    'conflict_detect': {'has_conflict': bool, 'conflict_type': str, 'severity': str, 'severity_reason': str,
                        'core_contradiction': str, 'escalation_risk': str, 'misunderstandings': list, 'priority_issue': str},
    'action_plan': {'proposals': list, 'suggestion': str, 'timing': str},
    'draft_message': {'drafts': list, 'opening_line': str, 'tone_guide': str, 'avoid': list, 'best_channel': str},
    'review': {'event_summary': str, 'what_worked': list, 'what_to_improve': list, 'lesson': str,
               'pattern_noticed': str, 'next_attention': str},
    'memory_write': {'memories': list},
}

SKILL_LIST_FIELDS = {
    'expression_clarify': {'people': {'name': str, 'role': str, 'emotion': str},
                           'events': {'description': str, 'time': str, 'importance': str}},
    'stance_analysis': {'stances': {'person': str, 'position': str, 'underlying_need': str, 'worry': str, 'flexibility': str}},
    'action_plan': {'proposals': {'id': str, 'title': str, 'description': str, 'approach': str,
                                 'pros': list, 'cons': list, 'effort': str, 'recommended': bool}},
    'draft_message': {'drafts': {'style': str, 'content': str}},
    'memory_write': {'memories': {'type': str, 'subject': str, 'content': str, 'importance': int}},
}


@dataclass
class SkillOutput:
    """Skill 执行结果的统一包装。"""
    skill_name: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class SkillDefinition:
    """Skill 的完整定义。"""
    name: str                        # 英文标识 e.g. "stance_analysis"
    label: str                       # 中文名 e.g. "立场分析"
    description: str                 # 职责描述
    handler: Callable[..., Awaitable[dict[str, Any]]]
    depends_on: list[str] = field(default_factory=list)
    max_timeout: float = 20.0       # 单个 Skill 超时（秒）
    required_fields: dict[str, type] = field(default_factory=dict)


# 全局注册表
SKILL_REGISTRY: dict[str, SkillDefinition] = {}


def register_skill(skill: SkillDefinition) -> SkillDefinition:
    """注册一个 Skill 到全局注册表。"""
    SKILL_REGISTRY[skill.name] = skill
    logger.debug("Registered skill: %s (%s)", skill.name, skill.label)
    return skill


def get_skill(name: str) -> SkillDefinition | None:
    return SKILL_REGISTRY.get(name)


def resolve_execution_levels(skill_names: list[str]) -> list[list[str]]:
    """根据依赖关系做分层拓扑排序，返回按层分组的执行计划。

    - 不在 skill_names 中的依赖会被自动补入；
    - 同一层的 Skill 之间互不依赖，可以并行执行，后一层可以使用前一层的结果；
    - 层内按名称排序，保证确定性；
    - 循环依赖时抛出 ValueError。
    """
    needed: set[str] = set()

    def _collect(name: str) -> None:
        if name in needed:
            return
        skill = SKILL_REGISTRY.get(name)
        if not skill:
            return
        needed.add(name)
        for dep in skill.depends_on:
            _collect(dep)

    for name in skill_names:
        _collect(name)

    remaining_deps: dict[str, set[str]] = {
        n: {dep for dep in SKILL_REGISTRY[n].depends_on if dep in needed}
        for n in needed
    }

    levels: list[list[str]] = []
    resolved: set[str] = set()
    while remaining_deps:
        ready = sorted(n for n, deps in remaining_deps.items() if not (deps - resolved))
        if not ready:
            raise ValueError(f"Skill 依赖存在循环: {sorted(remaining_deps)}")
        levels.append(ready)
        resolved.update(ready)
        for n in ready:
            remaining_deps.pop(n)

    return levels


def resolve_execution_order(skill_names: list[str]) -> list[str]:
    """根据依赖关系做拓扑排序，返回执行顺序（分层结果展平，层内按字母序）。

    不在 skill_names 中的依赖会被自动补入。
    循环依赖时抛出 ValueError。
    """
    return [name for level in resolve_execution_levels(skill_names) for name in level]


async def execute_skill(
    skill: SkillDefinition,
    *,
    context: dict[str, Any],
    previous_results: dict[str, SkillOutput],
    timeout: float | None = None,
) -> SkillOutput:
    """执行单个 Skill，包含超时保护。"""
    started = time.monotonic()
    if timeout is None:
        from app.services.privacy_audit import get_privacy_audit_context
        deadline = get_privacy_audit_context().get('chat_deadline')
        if deadline is not None:
            timeout = max(0, deadline - started)
    try:
        result = await asyncio.wait_for(
            skill.handler(context=context, previous_results=previous_results),
            timeout=max(0, timeout) if timeout is not None else skill.max_timeout,
        )
        if not isinstance(result, dict) or not result or set(result) in ({'raw'}, {'raw_text'}):
            return SkillOutput(skill_name=skill.name, success=False, error=f'{skill.label}未返回可用的分析结果',
                               duration_ms=(time.monotonic() - started) * 1000)
        required = skill.required_fields or SKILL_OUTPUT_FIELDS.get(skill.name, {})
        for key, kind in required.items():
            if not isinstance(result.get(key), kind):
                raise ValueError(f'{skill.label}缺少或格式不正确的字段：{key}')
        for key, fields in SKILL_LIST_FIELDS.get(skill.name, {}).items():
            for item in result.get(key, []):
                if not isinstance(item, dict) or any(type(item.get(field)) is not kind for field, kind in fields.items()):
                    raise ValueError(f'{skill.label}列表内容格式不正确：{key}')
        if skill.name in {'action_plan', 'draft_message'} and not result.get('proposals' if skill.name == 'action_plan' else 'drafts'):
            raise ValueError(f'{skill.label}未返回可用内容')
        return SkillOutput(
            skill_name=skill.name,
            success=True,
            data=result,
            duration_ms=(time.monotonic() - started) * 1000,
        )
    except asyncio.TimeoutError:
        logger.warning("Skill %s timed out after %.1fs", skill.name, timeout if timeout is not None else skill.max_timeout)
        return SkillOutput(
            skill_name=skill.name,
            success=False,
            error=f"{skill.label}处理超时",
            duration_ms=(time.monotonic() - started) * 1000,
        )
    except Exception as exc:
        logger.exception("Skill %s failed: %s", skill.name, exc)
        return SkillOutput(
            skill_name=skill.name,
            success=False,
            error=str(exc),
            duration_ms=(time.monotonic() - started) * 1000,
        )
