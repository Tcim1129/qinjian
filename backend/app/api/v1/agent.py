"""AI 智能伴侣 Agent 接口（陪伴、聊天、数据提取式打卡）"""

import json
import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, validate_pair_access
from app.models import User, Pair, AgentChatSession, AgentChatMessage
from app.schemas import (
    AgentSessionResponse,
    AgentMessageResponse,
    AgentChatRequest,
    AgentChatResponse,
)
from app.ai import client
from app.core.config import settings

router = APIRouter(prefix="/agent", tags=["智能陪伴"])
logger = logging.getLogger(__name__)

# 这里设定 System Prompt
SYSTEM_PROMPT = """你是一个情感智能伴侣（亲健AI）。你的任务是通过与用户的自然对话，提供情绪支持、感情建议，并“隐式”地引导他们完成每日的情感打卡。
你不能直接说“请填写表单”或者“请打卡”。相反，你需要在自然的聊天中，通过共情和引导提问，引出以下信息：
1. 他们今天的心情指数（1-10分，不要直接问几分，而是从对方描述中感知或轻巧地确认）
2. 他们今天与伴侣（或自己）的互动频率和深入程度
3. 是否有什么特别的事情发生或任务完成

一旦你认为收集到了足够丰富的信息，你可以调用 `extract_checkin_data` 工具将今天的内容提炼出来。
"""

tools = [
    {
        "type": "function",
        "function": {
            "name": "extract_checkin_data",
            "description": "当在聊天中收集到足够的信息（心情、互动情况、发生的事件）时，提取这些数据用于生成当日的关系日记",
            "parameters": {
                "type": "object",
                "properties": {
                    "diary_content": {
                        "type": "string",
                        "description": "基于今天用户的倾诉，替用户总结出一段富有感情、条理清晰的日记正文（约100-200字即可）。这会作为打卡的 content 字段。",
                    },
                    "mood_score": {
                        "type": "integer",
                        "description": "推断出的心情分数，范围 1 到 10",
                    },
                    "interaction_freq": {
                        "type": "integer",
                        "description": "今天关系互动的频率，比如 1（很少）到 5（很高）。如果是单人就是和自己的相处评分。",
                    },
                    "deep_conversation": {
                        "type": "boolean",
                        "description": "是否有较深入或有意义的对话反思",
                    },
                },
                "required": [
                    "diary_content",
                    "mood_score",
                    "interaction_freq",
                    "deep_conversation",
                ],
            },
        },
    }
]


@router.post("/sessions", response_model=dict)
async def create_or_get_session(
    pair_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取今天的 Agent 会话，如果没有则创建一个新的"""
    if pair_id:
        await validate_pair_access(pair_id, user, db, require_active=True)

    today = date.today()

    # 查找是否有今天的未归档会话
    stmt = select(AgentChatSession).where(
        AgentChatSession.user_id == user.id,
        AgentChatSession.session_date == today,
    )
    if pair_id:
        stmt = stmt.where(AgentChatSession.pair_id == pair_id)
    else:
        stmt = stmt.where(AgentChatSession.pair_id.is_(None))

    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        session = AgentChatSession(
            user_id=user.id, pair_id=pair_id, session_date=today, status="active"
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    return AgentSessionResponse(
        session_id=session.id, has_extracted_checkin=session.has_extracted_checkin
    )


@router.get(
    "/sessions/{session_id}/messages", response_model=list[AgentMessageResponse]
)
async def get_session_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取特定会话的历史消息"""
    session = await db.get(AgentChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    result = await db.execute(
        select(AgentChatMessage)
        .where(AgentChatMessage.session_id == session_id)
        .order_by(AgentChatMessage.created_at.asc())
    )
    messages = result.scalars().all()

    return [
        AgentMessageResponse(
            id=msg.id, role=msg.role, content=msg.content, payload=msg.payload
        )
        for msg in messages
        if msg.role in ("user", "assistant")
    ]


@router.post("/sessions/{session_id}/chat", response_model=AgentChatResponse)
async def chat_with_agent(
    session_id: str,
    req: AgentChatRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """向智能伴侣发送消息并获取回复"""
    session = await db.get(AgentChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 1. 记录用户的消息
    user_msg = AgentChatMessage(session_id=session.id, role="user", content=req.content)
    db.add(user_msg)
    await db.flush()

    # 2. 组装历史消息传递给大模型
    result = await db.execute(
        select(AgentChatMessage)
        .where(AgentChatMessage.session_id == session.id)
        .order_by(AgentChatMessage.created_at.asc())
    )
    history = result.scalars().all()

    messages_for_llm = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        tool_call_id = str((msg.payload or {}).get("tool_call_id") or "")
        # OpenAI 格式要求如果有 tool_calls 需要特殊处理，这里简易适配
        if msg.role == "assistant" and msg.payload and "tool_calls" in msg.payload:
            messages_for_llm.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": msg.payload["tool_calls"],
                }
            )
        elif msg.role == "tool":
            messages_for_llm.append(
                {
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": tool_call_id,
                }
            )
        else:
            messages_for_llm.append({"role": msg.role, "content": msg.content})

    # 3. 调用 AI (若今日已提取过打卡，就不带 tools 了，纯聊天)
    current_tools = tools if not session.has_extracted_checkin else None

    try:
        response = await client.chat.completions.create(
            model=settings.AI_TEXT_MODEL,
            messages=messages_for_llm,
            temperature=0.7,
            tools=current_tools,
            tool_choice="auto" if current_tools else "none",
        )
        ai_msg = response.choices[0].message

        # 4. 判断 AI 是否决意调用工具（提取打卡）
        if ai_msg.tool_calls:
            # 存下 AI 这一轮带 function call 的回复
            t_call = ai_msg.tool_calls[0]
            func_name = t_call.function.name
            func_args = json.loads(t_call.function.arguments)

            assistant_msg = AgentChatMessage(
                session_id=session.id,
                role="assistant",
                content=ai_msg.content or "",
                payload={
                    "tool_calls": [
                        {
                            "id": t_call.id,
                            "type": "function",
                            "function": {
                                "name": func_name,
                                "arguments": t_call.function.arguments,
                            },
                        }
                    ]
                },
            )
            db.add(assistant_msg)

            # --- 执行提取打卡的逻辑 ---
            if func_name == "extract_checkin_data":
                # 这里引入 Checkin 的写入逻辑
                from app.api.v1.checkins import create_checkin
                from app.schemas import CheckinRequest

                checkin_req = CheckinRequest(
                    pair_id=session.pair_id,
                    content=func_args.get("diary_content", "通过对话生成的今日打卡..."),
                    mood_score=func_args.get("mood_score", 5),
                    interaction_freq=func_args.get("interaction_freq", 3),
                    interaction_initiative="both",
                    deep_conversation=func_args.get("deep_conversation", False),
                    task_completed=False,
                )

                try:
                    # 复用核心打卡业务逻辑（其中自带触发生成每日合拍报告等）
                    await create_checkin(
                        req=checkin_req,
                        background_tasks=background_tasks,
                        mode="solo" if not session.pair_id else None,
                        user=user,
                        db=db,
                    )
                    session.has_extracted_checkin = True
                    tool_result_content = (
                        "打卡成功生成入库！可以跟用户说一声辛苦了或者晚安。"
                    )
                except Exception as e:
                    tool_result_content = f"保存打卡失败：{str(e)}"

                # 记录 Tool 回执
                tool_msg = AgentChatMessage(
                    session_id=session.id,
                    role="tool",
                    content=tool_result_content,
                    payload={"tool_call_id": t_call.id},
                )
                db.add(tool_msg)
                await db.flush()

                # 带上回执再次让大模型生成最终文本答复
                messages_for_llm.append(ai_msg.model_dump())
                messages_for_llm.append(
                    {
                        "role": "tool",
                        "tool_call_id": t_call.id,
                        "content": tool_result_content,
                    }
                )

                second_response = await client.chat.completions.create(
                    model=settings.AI_TEXT_MODEL,
                    messages=messages_for_llm,
                    temperature=0.7,
                )
                final_content = second_response.choices[0].message.content

                final_assistant_msg = AgentChatMessage(
                    session_id=session.id, role="assistant", content=final_content
                )
                db.add(final_assistant_msg)
                await db.commit()

                return AgentChatResponse(
                    reply=final_content, action="checkin_extracted"
                )

        # 没有进行工具调用（纯聊天回复）
        reply_content = ai_msg.content or "抱歉，我刚刚走神了。"
        assistant_msg = AgentChatMessage(
            session_id=session.id, role="assistant", content=reply_content
        )
        db.add(assistant_msg)
        await db.commit()

        return AgentChatResponse(reply=reply_content, action="chat")

    except Exception:
        await db.rollback()
        logger.exception("agent chat failed")
        raise HTTPException(status_code=500, detail="AI 服务暂时不可用，请稍后再试")
