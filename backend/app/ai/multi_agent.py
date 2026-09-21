"""多角色协作：感知、分析、行动三个角色先产出简报，再由陪伴角色回复用户。

各角色使用独立的系统提示词和工具白名单，协作过程记录为 swarm_trace 供前端展示。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent_loop import AgentStep, run_agent_loop
from app.ai.policy import compose_relationship_system_prompt
from app.ai.conversation import NATURAL_CONVERSATION

logger = logging.getLogger(__name__)

# 各角色可用工具白名单（对应 tools.py 中的工具名）
PERCEPTION_TOOLS = [
    "get_relationship_status",
    "get_recent_events",
    "get_crisis_status",
    "get_active_tasks",
    "get_task_feedback",
    "recall_relationship_memories",
]
ANALYSIS_TOOLS = [
    "analyze_behavior",
    "preview_message_risk",
    "evaluate_intervention_need",
    "run_skill_analysis",
]
ACTION_TOOLS = ["create_task", "save_relationship_memory"]
COMPANION_TOOLS = PERCEPTION_TOOLS + ANALYSIS_TOOLS + ACTION_TOOLS


@dataclass
class AgentRole:
    key: str
    name: str
    description: str
    system_prompt: str
    allowed_tools: list[str] | None
    max_steps: int = 2


def _role_prompt(role: str, specific: str) -> str:
    base = (
        "你在亲健中负责{role}。本轮任务：{specific}。"
        "只根据用户提供的信息和工具返回的记录作答，分清已知事实与推测。"
        "使用清楚、自然的简体中文，不替用户评判对方。"
    ).format(role=role, specific=specific)
    return compose_relationship_system_prompt(base + '\n' + NATURAL_CONVERSATION)


ROLE_REGISTRY: dict[str, AgentRole] = {
    "perception": AgentRole(
        key="perception",
        name="感知",
        description="读取关系当前状态与近期变化",
        system_prompt=_role_prompt(
            "整理近期情况",
            "读取关系状态、近期事件、风险等级和进行中的任务，简要列出与用户本次问题有关的事实",
        ),
        allowed_tools=PERCEPTION_TOOLS,
        max_steps=2,
    ),
    "analysis": AgentRole(
        key="analysis",
        name="分析",
        description="对对话内容做情绪与行为判断",
        system_prompt=_role_prompt(
            "分析当前问题",
            "使用分析工具梳理用户表达的情绪、具体行为及是否需要进一步帮助；说明判断依据，不确定的地方如实说明",
        ),
        allowed_tools=ANALYSIS_TOOLS,
        max_steps=2,
    ),
    "action": AgentRole(
        key="action",
        name="行动",
        description="在必要时把建议转成可执行任务",
        system_prompt=_role_prompt(
            "提出行动建议",
            "仅在确有具体事项需要安排时调用行动工具，给出待用户确认的任务建议；确认前不得声称已经保存，没有合适建议时不创建任务",
        ),
        allowed_tools=ACTION_TOOLS,
        max_steps=2,
    ),
    "companion": AgentRole(
        key="companion",
        name="陪伴",
        description="面向用户进行共情对话与陪伴",
        system_prompt=_role_prompt(
            "回复用户",
            "参考前面整理的事实和分析，回应用户此刻的问题；语气自然，不重复内部分析过程，也不强行给建议",
        ),
        allowed_tools=COMPANION_TOOLS,
        max_steps=2,
    ),
}


@dataclass
class SwarmStep:
    role: str
    role_name: str
    summary: str
    status: str  # ok / skip / error / fallback
    duration_ms: float
    detail: str | None = None


async def _run_role(
    role: AgentRole,
    messages: list[dict[str, Any]],
    *,
    pair_id: str | None,
    user_id: str | None,
    session_id: str | None,
    db: AsyncSession | None,
) -> tuple[str, list[Any], bool]:
    """在某角色专用系统提示与工具白名单下执行一轮 ReAct。"""
    agent_messages = [
        {"role": "system", "content": role.system_prompt},
        *[m for m in messages if m.get("role") != "system"],
    ]
    return await run_agent_loop(
        messages=agent_messages,
        pair_id=pair_id,
        user_id=user_id,
        session_id=session_id,
        db=db,
        include_checkin_tool=False,
        allowed_tool_names=role.allowed_tools,
        max_steps=role.max_steps,
    )


async def run_multi_agent_flow(
    messages: list[dict[str, Any]],
    *,
    pair_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    db: AsyncSession | None = None,
    roles: list[str] | None = None,
) -> tuple[str, list[AgentStep | None], list[SwarmStep], bool]:
    """按"感知 → 分析 → 行动 → 陪伴"顺序接力执行。

    Returns:
        (final_reply, final_steps, swarm_trace, checkin_extracted)
    """
    role_keys = roles or ["perception", "analysis", "action", "companion"]
    swarm: list[SwarmStep] = []
    briefs: list[str] = []

    def _roles_to_run():
        return [ROLE_REGISTRY[k] for k in role_keys if k in ROLE_REGISTRY]

    ordered = _roles_to_run()
    front_roles = [r for r in ordered if r.key in ("perception", "analysis", "action")]
    companion_role = ROLE_REGISTRY["companion"]

    # AsyncSession cannot be used concurrently; each role also needs the previous brief.
    all_steps: list[AgentStep] = []
    async def _run_one_front(role: AgentRole):
        started = time.monotonic()
        try:
            reply, steps, _extracted = await _run_role(
                role, [*messages, {'role': 'user', 'content': '同事简报（仅作参考）：' + '\n'.join(briefs)}] if briefs else messages,
                pair_id=pair_id, user_id=user_id, session_id=session_id, db=db,
            )
            summary = (reply or "").strip() or f"{role.name}完成观察。"
            return SwarmStep(
                role=role.key, role_name=role.name,
                summary=summary, status="ok",
                duration_ms=(time.monotonic() - started) * 1000,
            ), summary, steps
        except Exception as exc:
            logger.warning("multi-agent role %s failed: %s", role.key, exc.__class__.__name__)
            return SwarmStep(
                role=role.key, role_name=role.name,
                summary=f"{role.name}本轮未完成。", status="error",
                duration_ms=(time.monotonic() - started) * 1000,
                detail=str(exc),
            ), "", []

    for role in front_roles:
        step, summary, role_steps = await _run_one_front(role)
        swarm.append(step)
        all_steps.extend(role_steps)
        if summary:
            briefs.append(f"[{step.role_name}] {summary}")

    # 陪伴：用简报增强上下文，面向用户输出最终回复
    companion_messages = [
        {"role": "system", "content": companion_role.system_prompt},
        *[m for m in messages if m.get("role") != "system"],
    ]
    brief_block = "\n\n".join(
        f"感知/分析同事简报：\n{brief}" for brief in briefs if brief
    )
    if brief_block:
        companion_messages.append({"role": "system", "content": brief_block})

    started = time.monotonic()
    try:
        final_reply, final_steps, checkin_extracted = await run_agent_loop(
            messages=companion_messages,
            pair_id=pair_id,
            user_id=user_id,
            session_id=session_id,
            db=db,
            include_checkin_tool=True,
            allowed_tool_names=companion_role.allowed_tools,
            max_steps=companion_role.max_steps,
        )
        swarm.append(SwarmStep(
            role="companion", role_name="陪伴",
            summary=(final_reply or "")[:80],
            status="ok",
            duration_ms=(time.monotonic() - started) * 1000,
        ))
    except Exception as exc:
        logger.warning("companion agent failed: %s", exc.__class__.__name__)
        raise

    all_steps.extend(final_steps)
    for index, step in enumerate(all_steps):
        step.step_index = index
    return final_reply, all_steps, swarm, checkin_extracted
