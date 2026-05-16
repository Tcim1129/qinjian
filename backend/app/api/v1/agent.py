"""AI 智能伴侣 Agent 接口（陪伴、聊天、数据提取式打卡）"""

import asyncio
import json
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.time import current_local_date
from app.api.deps import get_current_user, validate_pair_access
from app.ai.asr import create_realtime_asr_client
from app.core.security import decode_access_token
from app.models import (
    User,
    Pair,
    AgentChatSession,
    AgentChatMessage,
    RelationshipProfileSnapshot,
    InterventionPlan,
)
from app.schemas import (
    AgentSessionResponse,
    AgentMessageResponse,
    AgentChatRequest,
    AgentChatResponse,
    MessageSimulationRequest,
    MessageSimulationResponse,
)
from app.ai import create_chat_completion
from app.ai.message_simulator import simulate_message_preview
from app.core.config import settings
from app.services.relationship_intelligence import (
    record_relationship_event,
    refresh_profile_and_plan,
    refresh_profile_snapshot,
)
from app.services.privacy_audit import privacy_audit_scope
from app.services.product_prefs import resolve_privacy_mode
from app.services.safety_summary import build_safety_status

router = APIRouter(prefix="/agent", tags=["智能陪伴"])
logger = logging.getLogger(__name__)

# 这里设定 System Prompt
SYSTEM_PROMPT = """你是一个情感智能伴侣（亲见AI）。你的任务是通过与用户的自然对话，提供情绪支持、感情建议，并“隐式”地引导他们完成每日的情感打卡。
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


def _simulation_fallback_context(pair: Pair, user: User) -> dict:
    is_user_a = str(pair.user_a_id) == str(user.id)
    partner_name = (
        pair.custom_partner_nickname_a if is_user_a else pair.custom_partner_nickname_b
    ) or "对方"
    return {
        "pair_type": pair.type.value,
        "partner_name": partner_name,
        "attachment_summary": {
            "attachment_a": pair.attachment_style_a or "unknown",
            "attachment_b": pair.attachment_style_b or "unknown",
            "is_long_distance": bool(pair.is_long_distance),
        },
        "risk_summary": {"current_level": "none", "trend": "unknown"},
        "suggested_focus": [],
    }


@router.post("/sessions", response_model=AgentSessionResponse)
async def create_or_get_session(
    pair_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取今天的 Agent 会话，如果没有则创建一个新的"""
    if pair_id:
        await validate_pair_access(pair_id, user, db, require_active=True)

    today = current_local_date()

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
    privacy_mode = resolve_privacy_mode(getattr(user, "product_prefs", None))

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
        with privacy_audit_scope(
            db=db,
            user_id=user.id,
            pair_id=session.pair_id,
            scope="pair" if session.pair_id else "solo",
            run_type="agent_chat",
            privacy_mode=privacy_mode,
        ):
            response = await create_chat_completion(
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

                with privacy_audit_scope(
                    db=db,
                    user_id=user.id,
                    pair_id=session.pair_id,
                    scope="pair" if session.pair_id else "solo",
                    run_type="agent_chat_followup",
                    privacy_mode=privacy_mode,
                ):
                    second_response = await create_chat_completion(
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


@router.post("/simulate-message", response_model=MessageSimulationResponse)
async def simulate_message(
    req: MessageSimulationRequest,
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """在消息发出前做一轮关系语境下的风险预演。"""
    if not req.draft.strip():
        raise HTTPException(status_code=400, detail="请先输入准备发送的内容")
    privacy_mode = resolve_privacy_mode(getattr(user, "product_prefs", None))

    pair = await validate_pair_access(pair_id, user, db, require_active=True)

    result = await db.execute(
        select(RelationshipProfileSnapshot)
        .where(
            RelationshipProfileSnapshot.pair_id == pair.id,
            RelationshipProfileSnapshot.user_id.is_(None),
            RelationshipProfileSnapshot.window_days == 7,
        )
        .order_by(
            RelationshipProfileSnapshot.snapshot_date.desc(),
            RelationshipProfileSnapshot.created_at.desc(),
        )
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        snapshot = await refresh_profile_snapshot(db, pair_id=pair.id, window_days=7)

    plan_result = await db.execute(
        select(InterventionPlan)
        .where(
            InterventionPlan.pair_id == pair.id,
            InterventionPlan.user_id.is_(None),
            InterventionPlan.status == "active",
        )
        .order_by(InterventionPlan.created_at.desc())
        .limit(1)
    )
    active_plan = plan_result.scalar_one_or_none()

    context = _simulation_fallback_context(pair, user)
    if snapshot:
        context.update(
            {
                "metrics": snapshot.metrics_json or {},
                "risk_summary": snapshot.risk_summary or {},
                "attachment_summary": snapshot.attachment_summary or {},
                "suggested_focus": (snapshot.suggested_focus or {}).get("items", []),
            }
        )
    if active_plan:
        context["active_plan"] = {
            "plan_type": active_plan.plan_type,
            "risk_level": active_plan.risk_level,
            "goal_json": active_plan.goal_json or {},
        }

    with privacy_audit_scope(
        db=db,
        user_id=user.id,
        pair_id=pair.id,
        scope="pair",
        run_type="message_simulation",
        privacy_mode=privacy_mode,
    ):
        simulation = await simulate_message_preview(req.draft, context)
    safety_status = await build_safety_status(db, pair_id=pair.id)
    simulation_risk = str(simulation.get("risk_level") or "moderate").strip().lower()
    safety_handoff = safety_status.get("handoff_recommendation")
    if simulation_risk in {"high", "severe"} and not safety_handoff:
        safety_handoff = (
            "如果这句话更像会继续升级局面，先不要发送，改为暂停、降温，"
            "必要时改用更低刺激的沟通方式或转向人工支持。"
        )

    await record_relationship_event(
        db,
        event_type="message.simulated",
        pair_id=pair.id,
        user_id=user.id,
        entity_type="message_simulation",
        payload={
            "draft": req.draft[:200],
            "risk_level": simulation.get("risk_level"),
            "conversation_goal": simulation.get("conversation_goal"),
            "suggested_tone": simulation.get("suggested_tone"),
            "safer_rewrite": (simulation.get("safer_rewrite") or req.draft)[:200],
        },
    )

    await refresh_profile_and_plan(db, pair_id=pair.id)

    return MessageSimulationResponse(
        draft=req.draft,
        partner_view=simulation.get("partner_view", ""),
        likely_impact=simulation.get("likely_impact", ""),
        risk_level=simulation.get("risk_level", "medium"),
        risk_reason=simulation.get("risk_reason", ""),
        safer_rewrite=simulation.get("safer_rewrite", req.draft),
        suggested_tone=simulation.get("suggested_tone", ""),
        conversation_goal=simulation.get("conversation_goal"),
        do_list=simulation.get("do_list") or [],
        avoid_list=simulation.get("avoid_list") or [],
        evidence_summary=safety_status.get("evidence_summary") or [],
        limitation_note=safety_status.get("limitation_note"),
        safety_handoff=safety_handoff,
    )


async def _authenticate_realtime_asr_websocket(
    websocket: WebSocket,
    db: AsyncSession,
) -> User | None:
    token = (
        websocket.query_params.get("token")
        or websocket.headers.get("authorization", "").removeprefix("Bearer ").strip()
    )
    if not token:
        await websocket.send_json(
            {"type": "error", "code": "unauthorized", "message": "缺少认证令牌"}
        )
        await websocket.close(code=4401)
        return None

    user_id = decode_access_token(token)
    if not user_id:
        await websocket.send_json(
            {"type": "error", "code": "unauthorized", "message": "登录已失效，请重新登录"}
        )
        await websocket.close(code=4401)
        return None

    try:
        user_uuid = uuid.UUID(str(user_id))
    except (TypeError, ValueError):
        await websocket.send_json(
            {"type": "error", "code": "unauthorized", "message": "登录信息无效，请重新登录"}
        )
        await websocket.close(code=4401)
        return None

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        await websocket.send_json(
            {"type": "error", "code": "unauthorized", "message": "用户不存在"}
        )
        await websocket.close(code=4401)
        return None
    return user


async def _pump_realtime_asr_events(
    provider,
    websocket: WebSocket,
) -> None:
    partial_text = ""
    final_sent = False
    segment_texts: dict[int, str] = {}
    try:
        while True:
            event = await provider.recv_event()
            event_type = str(event.get("type") or "").strip()
            if event_type == "conversation.item.input_audio_transcription.text":
                text = (
                    event.get("text")
                    or event.get("stash")
                    or event.get("transcript")
                    or partial_text
                )
                segment_id = event.get("segment_id")
                if text and isinstance(segment_id, int):
                    segment_texts[segment_id] = str(text)
                    text = "".join(
                        segment_texts[index] for index in sorted(segment_texts)
                    )
                if text:
                    partial_text = str(text)
                    await websocket.send_json({"type": "partial", "text": partial_text})
                continue

            if event_type == "conversation.item.input_audio_transcription.completed":
                text = event.get("transcript") or event.get("text") or partial_text
                segment_id = event.get("segment_id")
                if text and isinstance(segment_id, int):
                    segment_texts[segment_id] = str(text)
                    text = "".join(
                        segment_texts[index] for index in sorted(segment_texts)
                    )
                if text:
                    partial_text = str(text)
                    final_sent = True
                    await websocket.send_json({"type": "final", "text": partial_text})
                continue

            if event_type == "session.finished":
                text = event.get("transcript") or partial_text
                segment_id = event.get("segment_id")
                if text and isinstance(segment_id, int):
                    segment_texts[segment_id] = str(text)
                    text = "".join(
                        segment_texts[index] for index in sorted(segment_texts)
                    )
                if text and not final_sent:
                    await websocket.send_json({"type": "final", "text": str(text)})
                break

            if event_type == "error":
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": str(event.get("code") or "provider_error"),
                        "message": str(event.get("message") or "实时识别失败"),
                    }
                )
                break
    except asyncio.CancelledError:
        raise
    except WebSocketDisconnect:
        return
    except Exception:
        logger.exception("realtime asr provider pump failed")
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "provider_error",
                    "message": "实时识别服务中断，请稍后重试",
                }
            )
        except Exception:
            pass


@router.websocket("/asr/realtime")
async def realtime_asr(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """统一实时语音识别入口，由后端代理到配置的 realtime ASR provider。"""
    await websocket.accept()
    user = await _authenticate_realtime_asr_websocket(websocket, db)
    if not user:
        return

    provider = None
    provider_task: asyncio.Task | None = None

    try:
        while True:
            payload = await websocket.receive_json()
            event_type = str(payload.get("type") or "").strip()

            if event_type == "session.start":
                if provider is not None:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "session_exists",
                            "message": "当前连接已存在一个识别会话",
                        }
                    )
                    continue

                provider = create_realtime_asr_client(
                    provider=str(payload.get("provider") or settings.REALTIME_ASR_PROVIDER),
                    model=str(payload.get("model") or settings.QWEN_ASR_REALTIME_MODEL),
                    language=str(payload.get("language") or "zh"),
                    sample_rate=int(payload.get("sample_rate") or 16000),
                    input_audio_format=str(payload.get("format") or "pcm"),
                )
                await provider.connect()
                await provider.start_session()
                provider_task = asyncio.create_task(
                    _pump_realtime_asr_events(provider, websocket)
                )
                continue

            if event_type == "audio.chunk":
                if provider is None:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "session_missing",
                            "message": "请先发送 session.start",
                        }
                    )
                    continue

                audio = str(payload.get("audio") or "").strip()
                if not audio:
                    continue
                await provider.send_audio_chunk(audio)
                continue

            if event_type == "session.stop":
                if provider is None:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "session_missing",
                            "message": "请先发送 session.start",
                        }
                    )
                    continue

                await provider.stop_session()
                if provider_task is not None:
                    try:
                        await asyncio.wait_for(
                            provider_task,
                            timeout=settings.REALTIME_ASR_STOP_TIMEOUT_SECONDS,
                        )
                    except asyncio.TimeoutError:
                        provider_task.cancel()
                        try:
                            await provider_task
                        except asyncio.CancelledError:
                            pass
                        await websocket.send_json(
                            {
                                "type": "error",
                                "code": "provider_timeout",
                                "message": "实时识别收尾超时，已终止当前会话",
                            }
                        )
                    finally:
                        provider_task = None
                await provider.close()
                provider = None
                continue

            await websocket.send_json(
                {
                    "type": "error",
                    "code": "unsupported_event",
                    "message": f"不支持的事件类型：{event_type or 'unknown'}",
                }
            )

    except WebSocketDisconnect:
        logger.info("realtime asr websocket disconnected user=%s", user.id)
    except Exception:
        logger.exception("realtime asr websocket failed")
        try:
            await websocket.send_json(
                {"type": "error", "code": "server_error", "message": "实时识别服务异常"}
            )
        except Exception:
            pass
    finally:
        if provider_task is not None and not provider_task.done():
            provider_task.cancel()
            try:
                await provider_task
            except asyncio.CancelledError:
                pass
        if provider is not None:
            await provider.close()
        try:
            await websocket.close()
        except Exception:
            pass
