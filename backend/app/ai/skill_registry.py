"""Skill 注册表：声明各 Skill 的处理函数、依赖与超时，并解析执行顺序。"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


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
) -> SkillOutput:
    """执行单个 Skill，包含超时保护。"""
    started = time.monotonic()
    try:
        result = await asyncio.wait_for(
            skill.handler(context=context, previous_results=previous_results),
            timeout=skill.max_timeout,
        )
        return SkillOutput(
            skill_name=skill.name,
            success=True,
            data=result if isinstance(result, dict) else {"raw": result},
            duration_ms=(time.monotonic() - started) * 1000,
        )
    except asyncio.TimeoutError:
        logger.warning("Skill %s timed out after %.1fs", skill.name, skill.max_timeout)
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
