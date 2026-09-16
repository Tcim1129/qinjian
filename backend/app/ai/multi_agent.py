"""多智能体协作编排层

思路：把单一的情感陪伴 Agent 拆成一组有明确分工的"角色 Agent"，各自带有独立的
系统提示词与受限工具白名单，按阶段接力协作，最终由"陪伴 Agent"面向用户输出。

角色：
- perception  感知：读取关系状态/近期事件/危机等级（感知类工具）
- analysis    分析：对用户表述做行为/情绪/干预判断（分析类工具）
- companion   陪伴：面向用户的对话与情绪支持（对话 + 可选的行动工具）
- action      行动：在需要时生成任务/干预（行动类工具）

编排器 run_multi_agent_flow 让 perception/analysis 先做"推理热身"并产出简报，
把简报注入 companion 的上下文，再由 companion 完成最终回复。整个过程会产出
swarm_trace，供前端展示"多个智能体接力协作"。
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
]
ANALYSIS_TOOLS = [
    "analyze_behavior",
    "preview_message_risk",
    "evaluate_intervention_need",
]
ACTION_TOOLS = ["create_task"]
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
        "你是亲健智能体协作团队中的「{role}」。你负责「{specific}」。"
        "你与感知/分析/陪伴等同事分工协作，共同维护一段亲密关系。"
        "始终使用简体中文，温柔、清楚、不评判。"
    ).format(role=role, specific=specific)
    return compose_relationship_system_prompt(base + '\n' + NATURAL_CONVERSATION)


ROLE_REGISTRY: dict[str, AgentRole] = {
    "perception": AgentRole(
        key="perception",
        name="感知",
        description="读取关系当前状态与近期变化",
        system_prompt=_role_prompt(
            "感知 Agent",
            "调用感知工具读取关系全景状态、近期事件、危机等级与进行中任务，形成客观观察",
        ),
        allowed_tools=PERCEPTION_TOOLS,
        max_steps=2,
    ),
    "analysis": AgentRole(
        key="analysis",
        name="分析",
        description="对对话内容做情绪与行为判断",
        system_prompt=_role_prompt(
            "分析 Agent",
            "调用分析工具评估用户表述中的情绪、行为信号与是否需要干预，给出冷静分析",
        ),
        allowed_tools=ANALYSIS_TOOLS,
        max_steps=2,
    ),
    "action": AgentRole(
        key="action",
        name="行动",
        description="在必要时把建议转成可执行任务",
        system_prompt=_role_prompt(
            "行动 Agent",
            "只有当明确需要推进一个具体行动时，才调用行动工具提出待确认的任务建议，不可声称已经保存；否则保持安静",
        ),
        allowed_tools=ACTION_TOOLS,
        max_steps=2,
    ),
    "companion": AgentRole(
        key="companion",
        name="陪伴",
        description="面向用户进行共情对话与陪伴",
        system_prompt=_role_prompt(
            "陪伴 Agent",
            "结合感知与分析同事的简报，与用户自然对话，提供情绪支持与稳妥建议",
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
