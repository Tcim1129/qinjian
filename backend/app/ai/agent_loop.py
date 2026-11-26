"""多步推理循环：模型思考后调用工具，依据工具结果继续，直至给出回复。"""

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import create_chat_completion
from app.core.time import current_local_date
from app.ai.tools import execute_tool, get_openai_tools_schema
from app.services.draft_grounding import DraftReviewUnavailable, loan_direction_question, needs_draft_review, review_draft
from app.services.person_reference import person_direction_question
from app.services.turn_reference import resolve_current_topic_reference

logger = logging.getLogger(__name__)

MAX_AGENT_STEPS = 5
MAX_TOTAL_TIMEOUT = 45.0


def _contains_tool_markup(text: str | None) -> bool:
    return bool(re.search(r'<[|｜]DSML[|｜]|<tool_call\b|<function=', text or '', re.I))


def _next_week_reminder_date(messages: list[dict[str, Any]], today: date) -> date | None:
    text = next((m.get('content') for m in reversed(messages) if m.get('role') == 'user'), None)
    if not isinstance(text, str):
        return None
    reminder = re.fullmatch(
        r'(?:请)?(?:帮我)?提醒我(?:在)?下个?(?:周|星期)([一二三四五六日天])'
        r'([^，,。！？!?；;\n]+)(?:[，,]\s*(?:但)?先(?:给我看|让我看|别加|别保存)[^\n]*)?[。！!]?',
        text.strip(),
    )
    if not reminder or re.search(
        r'周[一二三四五六日天]|星期|今天|明天|后天|\d+[月日号点]', reminder[2],
    ):
        return None
    weekday = '一二三四五六日'.index(reminder[1].replace('天', '日'))
    return today + timedelta(days=7 - today.weekday() + weekday)


@dataclass
class AgentStep:
    """单步推理的思考内容、工具调用与结果。"""
    step_index: int
    thought: str | None
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    timestamp: float
    duration_ms: float


async def handle_memory_control_turn(
    *, pair_id=None, user_id=None, session_id=None, user_message_id=None,
    db=None, allowed_tool_names=None,
):
    """服务端核对记忆控制请求；多角色入口也只处理一次。"""
    # 确认由服务端核对本轮真实消息，模型不能调用工具代替用户确认。
    if db is not None and pair_id and user_id and session_id and user_message_id and (allowed_tool_names is None or 'remove_relationship_memory' in allowed_tool_names):
        from app.services.memory_removal import consume_confirmation
        confirmed_reply = await consume_confirmation(db,pair_id=pair_id,user_id=user_id,session_id=session_id,user_message_id=user_message_id)
        if confirmed_reply is not None:
            return confirmed_reply, [], False
    if db is not None and pair_id and user_id and session_id and user_message_id and (allowed_tool_names is None or 'remove_relationship_memory' in allowed_tool_names):
        from app.services.chat_memory_permission import verified_memory_removal
        removal = await verified_memory_removal(db, pair_id=pair_id, user_id=user_id, session_id=session_id, user_message_id=user_message_id)
        selection=None
        if removal:
            from app.services.memory_removal import resolve_explicit_target
            selection={} if removal.get('all_scope_requested') else await resolve_explicit_target(db,user_id=user_id,pair_id=pair_id,request_text=removal['request_text'],session_id=session_id,current_message_id=user_message_id)
        if isinstance(selection,str):
            return selection, [], False
        if removal and selection is None:
            # 服务端定位不到就不再交给模型自己挑一条，避免删错主题。
            return ('这句我还不确定指的是哪条记忆。可以说清楚是谁的哪件事、或者哪一次的安排吗？现在没有停用任何记录。', [], False)
        if selection is not None:
            started = time.monotonic()
            result = await execute_tool('remove_relationship_memory', selection, db=db, pair_id=pair_id, user_id=user_id,
                                        session_id=session_id, user_message_id=user_message_id,
                                        allowed_names=set(allowed_tool_names) if allowed_tool_names is not None else None,
                                        extra={'deictic': True} if selection.get('deictic') else None)
            reply = result.get('message') or (result.get('data') or {}).get('message') or '记忆尚未停用，请核对范围后再确认。'
            call_id = 'server-memory-removal-preview'
            step = AgentStep(step_index=0, thought=None, tool_calls=[{'id':call_id,'type':'function','function':{'name':'remove_relationship_memory','arguments':json.dumps(selection,ensure_ascii=False)}}],
                             tool_results=[{'tool_call_id':call_id,'name':'remove_relationship_memory','result':result}],
                             timestamp=started, duration_ms=(time.monotonic()-started)*1000)
            return reply, [step], False
    return None


async def run_agent_loop(
    messages: list[dict[str, Any]],
    *,
    pair_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    user_message_id: str | None = None,
    db: AsyncSession | None = None,
    include_checkin_tool: bool = True,
    allowed_tool_names: list[str] | None = None,
    max_steps: int | None = None,
) -> tuple[str, list[AgentStep], bool]:
    """返回 (回复内容, 推理步骤, 是否触发打卡提取)。"""
    control = await handle_memory_control_turn(
        pair_id=pair_id, user_id=user_id, session_id=session_id,
        user_message_id=user_message_id, db=db, allowed_tool_names=allowed_tool_names,
    )
    if control is not None:
        return control
    clarification = person_direction_question(messages) or loan_direction_question(messages)
    if clarification:
        return clarification, [], False
    turn_ref = resolve_current_topic_reference(messages)
    if turn_ref is not None:
        messages = [*messages, {'role': 'system', 'content': turn_ref['system_instruction']}]
    if (turn_ref is None or turn_ref.get('kind') != 'abandon_reply') and needs_draft_review(messages):
        started = time.monotonic()
        try:
            reply = await review_draft(messages, None, complete=create_chat_completion)
        except DraftReviewUnavailable as exc:
            # 事实核对服务不可用时，不把整轮打成失败：退成普通对话，并明确不许补事实。
            logger.warning('draft review unavailable: %s', exc)
            messages = [*messages, {'role': 'system', 'content': (
                '这一轮的事实核对暂时用不了。写的时候只许用用户原话里已经有的事实：'
                '不加他没说过的时间点、情绪、承诺，也不猜对方的反应。'
                '如果连一句能发的话都不确定，就直说这次没能核对，请他稍后再试。')}]
        else:
            step = AgentStep(step_index=0, thought=reply, tool_calls=[], tool_results=[],
                             timestamp=started, duration_ms=(time.monotonic()-started)*1000)
            return reply, [step], False

    today = current_local_date()
    reminder_date = _next_week_reminder_date(messages, today)
    task_guidance = f'当前业务日期是 {today.isoformat()}。行动建议请明确计划日期；工具只提出建议，用户确认前不要声称任务已经保存。'
    if reminder_date is not None:
        task_guidance += f'本轮用户明确要看提醒建议，已核对日期为 {reminder_date.isoformat()}。调用 create_task 提出一条待确认的安排，然后回复。'
    from app.ai.skill_orchestrator import has_coercion_pressure
    from app.services.draft_grounding import current_user_text
    if has_coercion_pressure(current_user_text(messages)):
        task_guidance += (
            '本轮输入包含施压、威胁或公开他人隐私/截图的风险（rewrite_blocked=true）。'
            '必须先明确拒绝协助施压或公开隐私，提醒停止施压并尊重对方边界；'
            '严禁在本轮给出任何可直接发送或复制的改写话术，无论分析工具是否超时或降级。'
        )
    messages = [*messages, {'role': 'system', 'content': task_guidance}]
    tools_schema = get_openai_tools_schema(
        include_checkin=include_checkin_tool,
        allowed_names=allowed_tool_names,
        pair_available=bool(pair_id),
    )
    save_grant = None
    if db is not None and pair_id and user_id and session_id and user_message_id:
        from app.services.chat_memory_permission import verified_memory_request, verified_memory_removal
        context = dict(pair_id=pair_id,user_id=user_id,session_id=session_id,user_message_id=user_message_id)
        save_grant = await verified_memory_request(db, **context)
        remove_grant = await verified_memory_removal(db, **context)
        unavailable = set()
        if save_grant is None:
            unavailable.add('save_relationship_memory')
        if remove_grant is None:
            unavailable.add('remove_relationship_memory')
        tools_schema = [tool for tool in tools_schema if tool['function']['name'] not in unavailable]
        if save_grant is not None:
            messages = [*messages, {'role':'system','content':(
                '本轮已核对用户明确的保存要求，请先调用保存工具，以工具结果为准再回复，不要重复征询要不要记。'
                '如果是带日期的安排，先按原话保存这一次，不必先问是否每周；不要补存本轮没有授权的其他话题。'
            )}]
    permitted_names = [item['function']['name'] for item in tools_schema]
    tool_scope = (
        '本阶段唯一可调用的工具：' + '、'.join(permitted_names) + '。其他阶段的工具在本阶段不可用，不要尝试调用。'
        if permitted_names else
        '本阶段没有可用工具。只根据用户本轮原话归纳，不读取历史、风险状态或已有安排，也不要模拟工具调用。'
    )
    messages = [*messages, {'role': 'system', 'content': tool_scope +
        '正文只输出自然中文，不输出工具协议或调用标记。候选安排等待用户点击确认属于正常流程，不等于保存失败。'}]
    steps: list[AgentStep] = []
    loop_start = time.monotonic()
    # 单次循环内复用配对权限校验结果，避免每个工具调用都重复查库
    auth_cache: dict[tuple[str, str], Any] = {}
    checkin_extracted = False
    malformed_retries = 0
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
            if _contains_tool_markup(thought):
                if malformed_retries >= 1 or is_last_step:
                    raise ValueError('模型未返回可用的正文')
                malformed_retries += 1
                messages = [*messages, {'role': 'system', 'content': tool_scope +
                    '上次回复不是可用正文，也没有执行任何操作。请重新用自然中文给出本阶段结论，不输出调用标记。'}]
                continue
            if save_grant is not None and re.search(
                r'^(?:用户说[：:]|根据规则[：:])|我需要调用\s*save_relationship_memory', thought or ''
            ):
                if not steps and not is_last_step:
                    messages.append({'role': 'system', 'content': '上一次只输出了内部说明，未执行保存。请先调用保存工具，或只给用户一句需要澄清的问题。不要输出内部分析。'})
                    steps.append(AgentStep(step_idx, None, [], [], step_start, (time.monotonic() - step_start) * 1000))
                    continue
                saved = any(item['name']=='save_relationship_memory' and item['result'].get('status')=='success'
                            for step in steps for item in step.tool_results)
                return ('已保存这条记忆。' if saved else '这次还没保存，请再试一次。'), steps, checkin_extracted
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
            if func_name == 'create_task' and reminder_date is not None and isinstance(func_args, dict):
                func_args['due_date'] = reminder_date.isoformat()

            result = await execute_tool(
                func_name, func_args,
                pair_id=pair_id,
                user_id=user_id,
                session_id=session_id,
                user_message_id=user_message_id,
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

        pending = next((tr['result'] for tr in tool_results if tr['name']=='remove_relationship_memory' and tr['result'].get('status')=='confirmation_required'),None)
        if pending is not None:
            return pending.get('message') or pending['data']['message'], steps, False

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

    if _contains_tool_markup(final_content):
        raise ValueError('模型未返回可用的正文')

    return final_content, steps, checkin_extracted
