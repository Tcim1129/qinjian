"""多步推理循环：模型思考后调用工具，依据工具结果继续，直至给出回复。"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import create_chat_completion
from app.core.time import current_local_date
from app.ai.tools import execute_tool, get_openai_tools_schema

logger = logging.getLogger(__name__)

MAX_AGENT_STEPS = 5
MAX_TOTAL_TIMEOUT = 45.0


@dataclass
class AgentStep:
    """单步推理的思考内容、工具调用与结果。"""
    step_index: int
    thought: str | None
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    timestamp: float
    duration_ms: float


async def run_agent_loop(
    messages: list[dict[str, Any]],
    *,
    pair_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    db: AsyncSession | None = None,
    include_checkin_tool: bool = True,
    allowed_tool_names: list[str] | None = None,
    max_steps: int | None = None,
) -> tuple[str, list[AgentStep], bool]:
    """返回 (回复内容, 推理步骤, 是否触发打卡提取)。"""
    messages = [*messages, {'role': 'system', 'content': (
        f'当前业务日期是 {current_local_date().isoformat()}。行动建议请明确计划日期；'
        '工具只提出建议，用户确认前不要声称任务已经保存。'
    )}]
    tools_schema = get_openai_tools_schema(
        include_checkin=include_checkin_tool,
        allowed_names=allowed_tool_names,
    )
    steps: list[AgentStep] = []
    loop_start = time.monotonic()
    # 单次循环内复用配对权限校验结果，避免每个工具调用都重复查库
    auth_cache: dict[tuple[str, str], Any] = {}
    checkin_extracted = False
    loop_max_steps = max(1, int(max_steps or MAX_AGENT_STEPS))

    for step_idx in range(loop_max_steps):
        step_start = time.monotonic()
        elapsed = step_start - loop_start
        if elapsed > MAX_TOTAL_TIMEOUT:
            logger.warning(f"Agent loop timed out after {elapsed:.2f}s")
            break

        # 末步收回工具权限，强制模型直接作答
        is_last_step = step_idx >= loop_max_steps - 1
        current_tools = None if is_last_step else tools_schema
        current_tool_choice = "none" if is_last_step else ("auto" if current_tools else "none")

        response = await create_chat_completion(
            model="default",
            messages=messages,
            tools=current_tools,
            tool_choice=current_tool_choice,
            pair_id=pair_id,
            user_id=user_id,
            session_id=session_id,
            db=db,
        )
        if not response or not response.choices:
            break

        ai_msg = response.choices[0].message
        thought = ai_msg.content

        tool_calls = []
        if ai_msg.tool_calls:
            for tc in ai_msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                })

        if not tool_calls:
            steps.append(AgentStep(
                step_index=step_idx,
                thought=thought,
                tool_calls=[],
                tool_results=[],
                timestamp=step_start,
                duration_ms=(time.monotonic() - step_start) * 1000,
            ))
            return thought or "", steps, checkin_extracted

        tool_results = []
        for tc in tool_calls:
            func_name = tc["function"]["name"]
            try:
                func_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                func_args = {}

            result = await execute_tool(
                func_name, func_args,
                pair_id=pair_id,
                user_id=user_id,
                db=db,
                allowed_names={item['function']['name'] for item in (current_tools or [])},
                auth_cache=auth_cache,
            )
            if func_name == 'extract_checkin_data' and result.get('status') == 'success':
                checkin_extracted = True

            tool_results.append({
                "tool_call_id": tc["id"],
                "name": func_name,
                "result": result,
            })

        steps.append(AgentStep(
            step_index=step_idx,
            thought=thought,
            tool_calls=tool_calls,
            tool_results=tool_results,
            timestamp=step_start,
            duration_ms=(time.monotonic() - step_start) * 1000,
        ))

        messages.append({
            "role": "assistant",
            "content": thought,
            "tool_calls": tool_calls,
        })
        for tr in tool_results:
            result_str = tr["result"]
            if not isinstance(result_str, str):
                try:
                    result_str = json.dumps(result_str, ensure_ascii=False)
                except Exception:
                    result_str = str(result_str)
            messages.append({
                "role": "tool",
                "tool_call_id": tr["tool_call_id"],
                "content": result_str,
            })

    logger.warning("Agent reached max steps, forcing final text response")
    final_response = await create_chat_completion(
        model="default",
        messages=messages,
        tools=None,
        tool_choice="none",
        pair_id=pair_id,
        user_id=user_id,
        session_id=session_id,
        db=db,
    )

    final_content = ""
    if final_response and final_response.choices:
        final_content = final_response.choices[0].message.content or ""

    return final_content, steps, checkin_extracted
