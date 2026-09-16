"""AI 智能伴侣 Agent 接口（陪伴、聊天、数据提取式打卡）"""

import asyncio
import json
import logging
import uuid
from datetime import date, datetime, timezone
from app.core.time import current_local_date
from time import perf_counter
from typing import Any, Literal
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, validate_pair_access
from app.ai.asr import create_realtime_asr_client
from app.core.security import (
    create_realtime_ws_ticket,
    decode_access_token,
    decode_realtime_ws_ticket,
)
from app.models import (
    User,
    Pair,
    AgentChatSession,
    AgentChatMessage,
    AgentThought,
    RelationshipEvent,
    RelationshipProfileSnapshot,
    InterventionPlan,
    RelationshipTask,
)
from app.schemas import (
    AgentSessionResponse,
    AgentSessionListItemResponse,
    AgentMessageResponse,
    AgentChatRequest,
    AgentChatResponse,
    AgentThoughtTraceResponse,
    AgentSwarmResponse,
    AgentCheckupResponse,
    AgentRealtimeTicketResponse,
    DecisionFeedbackRequest,
    MessageSimulationRequest,
    MessageSimulationResponse,
    TaskCreateRequest,
)
from app.ai import create_chat_completion
from app.ai.agent_loop import run_agent_loop
from app.ai.multi_agent import run_multi_agent_flow
from app.ai.tools import AGENT_TOOL_GUIDANCE
from app.ai.policy import compose_relationship_system_prompt
from app.ai.conversation import build_agent_system_prompt
from app.services.agent_delivery import prepare_chat_turn, complete_chat_turn, fail_chat_turn
from app.ai.message_simulator import simulate_message_preview
from app.core.config import settings
from app.services.relationship_intelligence import (
    record_relationship_event,
    refresh_profile_and_plan,
    refresh_profile_snapshot,
)
from app.services.behavior_judgement import (
    apply_judgement_to_payload,
    infer_language,
    judge_behavior_against_baseline,
    summarize_text_emotion,
)
from app.services.display_labels import (
    decision_feedback_label,
    emotion_label,
    language_label,
    risk_level_label,
)
from app.services.guidance_policy import build_crisis_support
from app.services.agent_session_memory import (
    _derive_topic,
    _preview_text,
    build_messages_for_llm,
    get_or_create_active_session,
    list_agent_sessions,
    list_session_messages,
    refresh_session_summary_if_needed,
    touch_session_activity,
)
from app.services.interaction_events import (
    build_interaction_payload,
    record_user_interaction_event,
)
from app.services.privacy_audit import log_privacy_transcription, privacy_audit_scope
from app.services.product_prefs import resolve_privacy_mode
from app.services.privacy_sandbox import redact_sensitive_text, sanitize_event_payload
from app.services.request_cooldown_store import consume_request_cooldown
from app.services.safety_summary import build_safety_status
from app.services.test_accounts import is_relaxed_test_account
from app.services.upload_access import (
    actor_can_reference_upload,
    normalize_upload_storage_path,
    to_client_upload_url,
)

router = APIRouter(prefix="/agent", tags=["智能陪伴"])
logger = logging.getLogger(__name__)


def _task_proposals_from_steps(steps):
    proposals = {}
    for step in steps:
        for item in step.tool_results or []:
            result = item.get('result') or {}
            data = result.get('data') or {}
            if item.get('name') == 'create_task' and result.get('status') == 'success' and data.get('requires_confirmation'):
                proposals[data['proposal_id']] = data
    return list(proposals.values())[:5]


@router.post('/sessions/{session_id}/messages/{message_id}/tasks/{proposal_id}/confirm')
async def confirm_agent_task(
    session_id: uuid.UUID, message_id: uuid.UUID, proposal_id: uuid.UUID,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    from app.api.v1.tasks import create_manual_task, _task_to_dict

    session = await db.get(AgentChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail='会话不存在')
    if not session.pair_id:
        raise HTTPException(status_code=400, detail='请先选择一段关系')
    await validate_pair_access(session.pair_id, user, db, require_active=True)
    # Lock the persisted suggestion so retries create at most one task (PostgreSQL).
    message = (await db.execute(select(AgentChatMessage).where(
        AgentChatMessage.id == message_id, AgentChatMessage.session_id == session_id,
        AgentChatMessage.role == 'assistant',
    ).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    payload = dict(message.payload or {}) if message else {}
    proposals = [dict(item) for item in payload.get('task_proposals', [])]
    proposal = next((item for item in proposals if item.get('proposal_id') == str(proposal_id)), None)
    if not proposal or not proposal.get('requires_confirmation'):
        raise HTTPException(status_code=404, detail='这条行动建议不存在')
    if proposal.get('confirmed_task_id'):
        task = await db.get(RelationshipTask, uuid.UUID(proposal['confirmed_task_id']))
        if not task or task.pair_id != session.pair_id or task.user_id != user.id:
            raise HTTPException(status_code=409, detail='原安排已变更，请回到安排页面查看')
        return {'message': '已加入安排', 'task': _task_to_dict(task, viewer=user)}
    try:
        due_date = date.fromisoformat(proposal['due_date'])
    except (ValueError, TypeError, KeyError):
        raise HTTPException(status_code=409, detail='建议日期无效，请重新生成')
    if due_date < current_local_date():
        raise HTTPException(status_code=409, detail='建议日期已过，请重新安排')
    result = await create_manual_task(session.pair_id, TaskCreateRequest(
        title=proposal['title'], description=proposal.get('description', ''),
        due_date=due_date, target_scope='self',
    ), user=user, db=db)
    proposal['confirmed_task_id'] = str(result['task']['id'])
    payload['task_proposals'] = proposals
    message.payload = payload
    await db.commit()
    return result

# 这里设定系统提示词
SYSTEM_PROMPT = build_agent_system_prompt(surface='checkin_assist')

# Frontend AI requests are capped at 60s; stop before that so the user sees a timeout.
AGENT_COMPLETION_TIMEOUT_SECONDS = 55
# 多智能体协作涉及 4 个角色接力调用，网关延迟下允许更长的深度思考窗口。
MULTI_AGENT_COMPLETION_TIMEOUT_SECONDS = 150
AGENT_FALLBACK_REPLY = (
    "这次没能连上助手，暂时没有生成回复。你的话还在，可以稍后重试。"
)
MESSAGE_SIMULATION_WINDOW_SECONDS = 60
MESSAGE_SIMULATION_MAX_ATTEMPTS = 2
REALTIME_ASR_MIN_SESSION_SECONDS = 15
REALTIME_ASR_MAX_SESSION_SECONDS = 300



def _surface_page_context(
    surface: Literal["chat", "checkin_assist"] | str,
) -> tuple[str, str]:
    normalized = str(surface or "").strip()
    if normalized == "chat":
        return "chat", "/chat"
    return "checkin", "/checkin"


def _build_voice_evidence_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    voice_url = normalize_upload_storage_path(payload.get("voice_url"))
    return {
        "voice_url": voice_url,
        "transcript_text": str(payload.get("transcript_text") or "").strip() or None,
        "duration_seconds": payload.get("duration_seconds"),
        "source": str(payload.get("source") or "").strip() or None,
        "voice_emotion": payload.get("voice_emotion"),
        "content_emotion": payload.get("content_emotion"),
        "transcript_language": payload.get("transcript_language"),
    }


def _serialize_message_payload_for_client(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return payload
    serialized = dict(payload)
    voice_evidence = serialized.get("voice_evidence")
    if isinstance(voice_evidence, dict):
        normalized_voice = dict(voice_evidence)
        normalized_voice["voice_url"] = to_client_upload_url(
            normalized_voice.get("voice_url")
        )
        serialized["voice_evidence"] = normalized_voice
    return serialized


def _serialize_agent_steps(steps: list[Any]) -> list[dict[str, Any]]:
    """把 AgentStep 序列化为可下发的推理痕迹 trace。"""
    trace = []
    for step in steps:
        trace.append(
            {
                "step_index": step.step_index,
                "thought": step.thought,
                "tool_calls": getattr(step, "tool_calls", []) or [],
                "tool_results": getattr(step, "tool_results", []) or [],
                "duration_ms": step.duration_ms,
            }
        )
    return trace


@router.post("/asr/ws-ticket", response_model=AgentRealtimeTicketResponse)
async def create_agent_asr_ws_ticket(
    user: User = Depends(get_current_user),
):
    """签发实时语音短时票据，避免长期 JWT 进入 WebSocket URL。"""
    return AgentRealtimeTicketResponse(
        ticket=create_realtime_ws_ticket(str(user.id)),
        expires_in=max(30, settings.REALTIME_ASR_TICKET_EXPIRE_SECONDS),
    )


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


def _simulation_solo_context(
    user: User,
    snapshot: RelationshipProfileSnapshot | None = None,
) -> dict:
    attachment_summary = {
        "attachment_a": "unknown",
        "attachment_b": "unknown",
        "is_long_distance": False,
    }
    metrics = {}
    risk_summary = {"current_level": "none", "trend": "stable"}
    suggested_focus: list[str] = []

    if snapshot:
        attachment_summary.update(snapshot.attachment_summary or {})
        metrics = snapshot.metrics_json or {}
        risk_summary = snapshot.risk_summary or risk_summary
        suggested_focus = (snapshot.suggested_focus or {}).get("items", [])

    return {
        "pair_type": "solo",
        "partner_name": "对方",
        "scope": "solo_preparation",
        "self_label": user.nickname or user.email or user.phone or "我",
        "attachment_summary": attachment_summary,
        "metrics": metrics,
        "risk_summary": risk_summary,
        "suggested_focus": suggested_focus,
    }


@router.post("/sessions", response_model=AgentSessionResponse)
async def create_or_get_session(
    pair_id: uuid.UUID | None = None,
    force_new: bool = False,
    surface: Literal["chat", "checkin_assist"] = "checkin_assist",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前有效的 Agent 会话，若无则创建新会话。"""
    pair_uuid = None
    if pair_id:
        pair = await validate_pair_access(pair_id, user, db, require_active=True)
        pair_uuid = pair.id

    session, reused = await get_or_create_active_session(
        db,
        user_id=user.id,
        pair_id=pair_uuid,
        force_new=force_new,
    )

    page, path = _surface_page_context(surface)
    await record_user_interaction_event(
        db,
        event_type="agent.session.opened",
        user_id=user.id,
        pair_id=pair_uuid,
        source="agent",
        page=page,
        path=path,
        http_method="POST",
        http_status=200,
        session_id=str(session.id),
        target_type="agent_session",
        target_id=session.id,
        payload={
            "status": session.status,
            "has_extracted_checkin": session.has_extracted_checkin,
            "reused": reused,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        },
    )
    await db.commit()
    await db.refresh(session)

    return AgentSessionResponse(
        session_id=session.id,
        has_extracted_checkin=session.has_extracted_checkin,
        expires_at=session.expires_at,
        reused=reused,
    )


@router.get(
    "/sessions", response_model=list[AgentSessionListItemResponse]
)
async def list_agent_sessions_route(
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出当前用户最近的 Agent 会话及其 topic / 最近消息 / 消息数。"""
    sessions = await list_agent_sessions(
        db,
        user_id=user.id,
        limit=limit,
    )

    items = []
    for session in sessions:
        messages = await list_session_messages(db, session_id=session.id)
        topic = (session.summary_json or {}).get("topic") if isinstance(session.summary_json, dict) else None
        if not topic:
            topic = _derive_topic(messages)
        last_content = messages[-1].content if messages else ""
        last_message = _preview_text(last_content, 120) or ""
        items.append(
            AgentSessionListItemResponse(
                session_id=session.id,
                pair_id=session.pair_id,
                status=session.status,
                topic=topic or "",
                last_message=last_message or "",
                message_count=len(messages),
                has_extracted_checkin=session.has_extracted_checkin,
                session_date=session.session_date,
                created_at=session.created_at,
                updated_at=session.updated_at,
                expires_at=session.expires_at,
            )
        )
    return items


@router.get(
    "/sessions/{session_id}/messages", response_model=list[AgentMessageResponse]
)
async def get_session_messages(
    session_id: uuid.UUID,
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
            id=msg.id,
            role=msg.role,
            content=msg.content,
            payload=_serialize_message_payload_for_client(msg.payload),
        )
        for msg in messages
        if msg.role in ("user", "assistant")
    ]


@router.post("/sessions/{session_id}/chat", response_model=AgentChatResponse)
async def chat_with_agent(
    session_id: uuid.UUID,
    req: AgentChatRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """向智能伴侣发送消息并获取回复"""
    session = await db.get(AgentChatSession, session_id, with_for_update=True, populate_existing=True)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    page, path = _surface_page_context(req.surface)
    if session.pair_id:
        await validate_pair_access(session.pair_id, user, db, require_active=True)
    voice_evidence_payload = _build_voice_evidence_payload(
        req.voice_evidence.model_dump(exclude_none=True)
        if req.voice_evidence is not None
        else None
    )
    if voice_evidence_payload and voice_evidence_payload.get("voice_url"):
        if not await actor_can_reference_upload(
            db,
            voice_evidence_payload["voice_url"],
            actor_user_id=user.id,
        ):
            raise HTTPException(status_code=403, detail="无权使用这份语音文件")
    transcript_text = str(
        (voice_evidence_payload or {}).get("transcript_text") or ""
    ).strip()
    effective_content = str(req.content or "").strip() or transcript_text
    privacy_mode = resolve_privacy_mode(getattr(user, "product_prefs", None))
    stored_user_content = effective_content
    user_payload = {"surface": req.surface}
    if req.scene_context:
        user_payload['scene_context'] = req.scene_context.model_dump()
    if voice_evidence_payload:
        user_payload["voice_evidence"] = voice_evidence_payload

    # 1. 记录用户的消息
    user_msg, cached_reply, is_new_turn = await prepare_chat_turn(
        db, session_id=session.id, client_message_id=req.client_message_id,
        content=stored_user_content, payload=user_payload,
    )
    if cached_reply is not None:
        return cached_reply
    touch_session_activity(session)
    await db.flush()
    user_message_id = user_msg.id

    if is_new_turn:
        await record_user_interaction_event(
            db,
            event_type="agent.chat.user_message",
            user_id=user.id,
            pair_id=session.pair_id,
            source="agent",
            page=page,
            path=path,
            http_method="POST",
            http_status=200,
            session_id=str(session.id),
            target_type="agent_message",
            target_id=user_msg.id,
            payload=build_interaction_payload(
                {
                    "role": "user",
                    "surface": req.surface,
                    "has_voice_evidence": bool(voice_evidence_payload),
                    "voice_source": (voice_evidence_payload or {}).get("source"),
                    "voice_duration_seconds": (voice_evidence_payload or {}).get("duration_seconds"),
                },
                text=effective_content,
            ),
        )
    await db.commit()

    # 3. 调用 AI 循环
    include_checkin = (req.surface != "chat" and not session.has_extracted_checkin)

    try:
        # Summary failures must also leave the saved turn retryable.
        history = await refresh_session_summary_if_needed(db, session=session)
        await db.commit()
        messages_for_llm = build_messages_for_llm(
            system_prompt=build_agent_system_prompt(surface=req.surface, intent=req.scene_context.intent if req.scene_context else 'auto'),
            history=history,
        )
        try:
            with privacy_audit_scope(
                db=db,
                user_id=user.id,
                pair_id=session.pair_id,
                scope="pair" if session.pair_id else "solo",
                run_type="agent_chat",
                privacy_mode=privacy_mode,
            ):
                reply_content, agent_steps, checkin_extracted = await asyncio.wait_for(
                    run_agent_loop(
                        messages=messages_for_llm,
                        pair_id=str(session.pair_id) if session.pair_id else None,
                        user_id=str(user.id),
                        session_id=str(session.id),
                        db=db,
                        include_checkin_tool=include_checkin
                    ),
                    timeout=AGENT_COMPLETION_TIMEOUT_SECONDS,
                )
        except asyncio.TimeoutError:
            logger.warning("agent chat completion timed out")
            raise HTTPException(status_code=504, detail="处理超过 1 分钟，已自动超时，请稍后再试")
        except Exception as exc:
            logger.warning("agent loop failed: %s", exc.__class__.__name__)
            raise HTTPException(status_code=502, detail="这次没能连上助手，请稍后重试。") from exc

        # 如果没有内容则兜底
        if not reply_content or not reply_content.strip():
            raise HTTPException(status_code=502, detail="这次没有收到回复，请重试。")

        action = "chat"
        # 4. 判断 AI 是否提取了打卡
        if checkin_extracted:
            action = "checkin_extracted"
            # 找到参数并生成 Checkin
            func_args = {}
            for step in agent_steps:
                for tc in step.tool_calls:
                    if tc["function"]["name"] == "extract_checkin_data":
                        try:
                            func_args = json.loads(tc["function"]["arguments"])
                        except Exception:
                            pass
                        break

            if func_args:
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
                    await create_checkin(
                        req=checkin_req,
                        background_tasks=background_tasks,
                        mode="solo" if not session.pair_id else None,
                        user=user,
                        db=db,
                    )
                    session.has_extracted_checkin = True
                except Exception as e:
                    logger.error(f"Save checkin failed: {e}")

        # 5. 保存 AI 最终回复和思路
        task_proposals = _task_proposals_from_steps(agent_steps)
        assistant_msg = AgentChatMessage(
            session_id=session.id, role="assistant", content=reply_content,
            payload={'task_proposals': task_proposals} if task_proposals else None,
        )
        db.add(assistant_msg)
        await db.flush()
        complete_chat_turn(user_msg, reply_id=assistant_msg.id, action=action)

        for step in agent_steps:
            if step.tool_calls:
                thought_record = AgentThought(
                    session_id=session.id,
                    step_index=step.step_index,
                    thought=step.thought,
                    tool_calls_json=json.dumps(step.tool_calls, ensure_ascii=False),
                    tool_results_json=json.dumps(step.tool_results, ensure_ascii=False),
                    duration_ms=step.duration_ms,
                )
                db.add(thought_record)

        touch_session_activity(session)
        await record_user_interaction_event(
            db,
            event_type="agent.chat.assistant_reply",
            user_id=user.id,
            pair_id=session.pair_id,
            source="agent",
            page=page,
            path=path,
            http_method="POST",
            http_status=200,
            session_id=str(session.id),
            target_type="agent_message",
            target_id=assistant_msg.id,
            payload={"role": "assistant", "reply_preview": reply_content[:120]},
        )
        await db.commit()
        await refresh_session_summary_if_needed(db, session=session)
        await db.commit()

        return AgentChatResponse(
            reply=reply_content,
            action=action,
            message_id=assistant_msg.id,
            task_proposals=task_proposals,
            trace=_serialize_agent_steps(agent_steps),
        )

    except HTTPException:
        await db.rollback()
        await fail_chat_turn(db, user_message_id)
        raise
    except Exception:
        await db.rollback()
        await fail_chat_turn(db, user_message_id)
        logger.exception("agent chat failed")
        raise HTTPException(status_code=500, detail="智能服务暂时不可用，请稍后再试")


@router.get("/sessions/{session_id}/thoughts", response_model=list[AgentThoughtTraceResponse])
async def get_agent_thoughts(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取一次 Agent 会话中每一步的推理痕迹(想法与工具调用)，供前端做过程可视化。"""
    session = await db.get(AgentChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    result = await db.execute(
        select(AgentThought)
        .where(AgentThought.session_id == session_id)
        .order_by(AgentThought.step_index.asc())
    )
    rows = result.scalars().all()
    trace = []
    for row in rows:
        tool_calls = []
        tool_results = []
        if row.tool_calls_json:
            try:
                tool_calls = json.loads(row.tool_calls_json)
            except Exception:
                tool_calls = []
        if row.tool_results_json:
            try:
                tool_results = json.loads(row.tool_results_json)
            except Exception:
                tool_results = []
        trace.append(
            AgentThoughtTraceResponse(
                step_index=row.step_index,
                thought=row.thought,
                tool_calls=tool_calls,
                tool_results=tool_results,
                duration_ms=row.duration_ms,
            )
        )
    return trace


@router.post(
    "/sessions/{session_id}/checkup",
    response_model=AgentCheckupResponse,
)
async def run_active_checkup(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """主动巡查：不等用户提问，Agent 主动体检关系健康并产出干预建议。

    流程：拉起关系全景 → 评估是否需干预 → 判断危机 → 汇总成可执行的主动干预报告。
    """
    session = await db.get(AgentChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    from app.services.safety_summary import build_safety_status
    from app.services.intervention_evaluation import build_intervention_evaluation
    from app.ai.tools import _get_crisis_status, _get_active_tasks

    privacy_mode = resolve_privacy_mode(getattr(user, "product_prefs", None))
    pair_id = str(session.pair_id) if session.pair_id else None
    user_id = str(user.id)

    try:
        with privacy_audit_scope(
            db=db,
            user_id=user.id,
            pair_id=session.pair_id,
            scope="pair" if session.pair_id else "solo",
            run_type="agent_checkup",
            privacy_mode=privacy_mode,
        ):
            if session.pair_id:
                snapshot = await build_safety_status(db=db, pair_id=pair_id)
                intervention = await build_intervention_evaluation(
                    db=db, pair_id=pair_id
                )
                crisis = await _get_crisis_status(db=db, pair_id=pair_id)
                active_tasks = await _get_active_tasks(db=db, pair_id=pair_id)
            else:
                snapshot = await build_safety_status(db=db, user_id=user_id)
                intervention = await build_intervention_evaluation(
                    db=db, user_id=user_id
                )
                crisis = await _get_crisis_status(db=db, pair_id=pair_id, user_id=user_id)
                active_tasks = await _get_active_tasks(db=db, pair_id=pair_id, user_id=user_id)
    except Exception as exc:
        logger.warning("active checkup perception failed: %s", exc.__class__.__name__)
        raise HTTPException(status_code=500, detail="暂时无法完成主动体检")

    health = None
    raw_health = (snapshot or {}).get("health_score") if isinstance(snapshot, dict) else None
    if raw_health is None:
        raw_health = (snapshot or {}).get("score")
    try:
        health = int(raw_health)
    except (TypeError, ValueError):
        health = None

    risk_level = str(crisis.get("highest_level") or "low") if isinstance(crisis, dict) else "low"
    risk_reason = ""
    if isinstance(intervention, dict):
        risk_reason = str(
            intervention.get("reason")
            or intervention.get("risk_reason")
            or risk_reason
        )
    urgency = "monitor"
    if risk_level in ("severe", "high"):
        urgency = "immediate"
    elif risk_level == "medium":
        urgency = "soon"

    recommended_actions = []
    tasks = active_tasks if isinstance(active_tasks, list) else []
    for task in tasks[:3]:
        title = task.get("title") or task.get("name") or "待办任务"
        recommended_actions.append(title)

    report_lines = []
    if health is not None:
        report_lines.append(f"本期主动巡查完成。关系健康分约 {health}/100，")
    else:
        report_lines.append("本期主动巡查完成。")
    report_lines.append(f"当前风险等级为「{risk_level}」。")
    if risk_reason:
        report_lines.append(risk_reason)
    if isinstance(intervention, dict) and intervention.get("recommendation"):
        report_lines.append(f"建议：{intervention['recommendation']}")
    else:
        report_lines.append("当前整体平稳，建议保持规律记录与沟通节奏。")
    report = "".join(report_lines)

    await record_user_interaction_event(
        db,
        event_type="agent.checkup.completed",
        user_id=user.id,
        pair_id=session.pair_id,
        source="agent",
        page="chat",
        path="/agent/sessions/{session_id}/checkup",
        http_method="POST",
        http_status=200,
        session_id=str(session.id),
        target_type="agent_checkup",
        target_id=None,
        payload={"health": health, "risk_level": risk_level, "urgency": urgency},
    )
    await db.commit()

    return AgentCheckupResponse(
        report=report,
        health=health,
        risk_level=risk_level,
        risk_reason=risk_reason,
        recommended_actions=recommended_actions,
        urgency=urgency,
        generated_at=datetime.now(timezone.utc),
    )


@router.post(
    "/sessions/{session_id}/collaborate",
    response_model=AgentSwarmResponse,
)
async def collaborate_multi_agent(
    session_id: uuid.UUID,
    req: AgentChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """多智能体协作：感知→分析→行动→陪伴 四个角色接力处理后给出陪伴回复。

    这是一个面向展示与体验的入口；普通聊天仍走 /chat。
    """
    session = await db.get(AgentChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session.pair_id:
        await validate_pair_access(session.pair_id, user, db, require_active=True)
    checkin_extracted = False
    effective_content = str(req.content or "").strip()
    user_msg = AgentChatMessage(
        session_id=session.id,
        role="user",
        content=effective_content,
        payload={"surface": req.surface, "multi_agent": True, **({'scene_context': req.scene_context.model_dump()} if req.scene_context else {})},
    )
    db.add(user_msg)
    touch_session_activity(session)
    await db.flush()
    await db.commit()

    history = await refresh_session_summary_if_needed(db, session=session)
    await db.commit()
    messages_for_llm = build_messages_for_llm(
        system_prompt=build_agent_system_prompt(surface=req.surface, intent=req.scene_context.intent if req.scene_context else 'auto'),
        history=history,
    )
    privacy_mode = resolve_privacy_mode(getattr(user, "product_prefs", None))

    try:
        with privacy_audit_scope(
            db=db,
            user_id=user.id,
            pair_id=session.pair_id,
            scope="pair" if session.pair_id else "solo",
            run_type="agent_collaborate",
            privacy_mode=privacy_mode,
        ):
            final_reply, final_steps, swarm, checkin_extracted = await asyncio.wait_for(
                run_multi_agent_flow(
                    messages=messages_for_llm,
                    pair_id=str(session.pair_id) if session.pair_id else None,
                    user_id=str(user.id),
                    session_id=str(session.id),
                    db=db,
                ),
                timeout=MULTI_AGENT_COMPLETION_TIMEOUT_SECONDS,
            )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="协作深度思考较久，请稍后再试或减少内容量")
    except Exception as exc:
        logger.warning("multi-agent collaborate failed: %s", exc.__class__.__name__)
        raise HTTPException(status_code=502, detail="这次协作没能完成，请重试。") from exc

    if not final_reply or not final_reply.strip():
        raise HTTPException(status_code=502, detail="这次没有收到回复，请重试。")
    action = "checkin_extracted" if checkin_extracted else "chat"

    task_proposals = _task_proposals_from_steps(final_steps)
    assistant_msg = AgentChatMessage(
        session_id=session.id, role="assistant", content=final_reply,
        payload={'task_proposals': task_proposals} if task_proposals else None,
    )
    db.add(assistant_msg)
    for step in final_steps:
        if step.tool_calls:
            db.add(AgentThought(
                session_id=session.id,
                step_index=step.step_index,
                thought=step.thought,
                tool_calls_json=json.dumps(step.tool_calls, ensure_ascii=False),
                tool_results_json=json.dumps(step.tool_results, ensure_ascii=False),
                duration_ms=step.duration_ms,
            ))
    touch_session_activity(session)
    await db.commit()
    await refresh_session_summary_if_needed(db, session=session)
    await db.commit()

    return AgentSwarmResponse(
        reply=final_reply,
        action=action,
        message_id=assistant_msg.id,
        task_proposals=task_proposals,
        swarm=[
            {
                "role": s.role,
                "role_name": s.role_name,
                "summary": s.summary,
                "status": s.status,
                "duration_ms": s.duration_ms,
            }
            for s in swarm
        ],
        trace=_serialize_agent_steps(final_steps),
    )


@router.post("/simulate-message", response_model=MessageSimulationResponse)
async def simulate_message(
    req: MessageSimulationRequest,
    pair_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """在消息发出前做一轮关系语境下的风险预演。"""
    if not req.draft.strip():
        raise HTTPException(status_code=400, detail="请先输入准备发送的内容")
    privacy_mode = resolve_privacy_mode(getattr(user, "product_prefs", None))

    pair = None
    if pair_id:
        pair = await validate_pair_access(pair_id, user, db, require_active=True)
    await consume_request_cooldown(
        bucket="message-simulation",
        scope_key=f"{user.id}:{pair.id if pair else 'solo'}",
        window_seconds=MESSAGE_SIMULATION_WINDOW_SECONDS,
        max_attempts=MESSAGE_SIMULATION_MAX_ATTEMPTS,
        limit_message="消息预演得有点频繁了",
        bypass=is_relaxed_test_account(user),
    )

    if pair:
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
    else:
        snapshot = await refresh_profile_snapshot(db, user_id=user.id, window_days=7)

    user_baseline_snapshot = await refresh_profile_snapshot(
        db,
        user_id=user.id,
        window_days=30,
    )
    await db.commit()

    active_plan = None
    if pair:
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

    context = _simulation_fallback_context(pair, user) if pair else _simulation_solo_context(user, snapshot)
    if pair and snapshot:
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

    try:
        with privacy_audit_scope(
            db=db,
            user_id=user.id,
            pair_id=pair.id if pair else None,
            scope="pair" if pair else "solo",
            run_type="message_simulation",
            privacy_mode=privacy_mode,
        ):
            simulation = await simulate_message_preview(req.draft, context)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="处理超过 1 分钟，已自动超时，请稍后再试")
    safety_status = await build_safety_status(
        db,
        pair_id=pair.id if pair else None,
        user_id=None if pair else user.id,
    )
    simulation_risk = str(simulation.get("risk_level") or "moderate").strip().lower()
    crisis_support = build_crisis_support(
        scope_type="pair" if pair else "solo",
        risk_level=simulation_risk,
        current_input_text=req.draft,
    )
    behaviour_judgement = judge_behavior_against_baseline(
        req.draft,
        baseline_summary=getattr(user_baseline_snapshot, "behavior_summary", None),
        explicit_preferences=(user_baseline_snapshot.behavior_summary or {}).get("explicit_preferences")
        if getattr(user_baseline_snapshot, "behavior_summary", None)
        else None,
        risk_level=simulation_risk,
    )
    safety_handoff = safety_status.get("handoff_recommendation")
    if crisis_support:
        safety_handoff = crisis_support.get("urgent_message")
    if simulation_risk in {"high", "severe"} and not safety_handoff:
        safety_handoff = (
            "如果这句话更像会继续升级局面，先不要发送，改为暂停、降温，"
            "必要时改用更低刺激的沟通方式或转向人工支持。"
        )

    simulation_payload = apply_judgement_to_payload(
        {
            "draft": req.draft[:200],
            "risk_level": simulation.get("risk_level"),
            "conversation_goal": simulation.get("conversation_goal"),
            "suggested_tone": simulation.get("suggested_tone"),
            "safer_rewrite": (simulation.get("safer_rewrite") or req.draft)[:200],
            "algorithm_version": simulation.get("algorithm_version"),
            "confidence": simulation.get("confidence"),
            "decision_trace": simulation.get("decision_trace") or {},
            "focus_labels": simulation.get("focus_labels") or [],
            "risk_score": simulation.get("risk_score"),
            "baseline_delta": simulation.get("baseline_delta"),
            "fallback_reason": simulation.get("fallback_reason"),
            "shadow_result": simulation.get("shadow_result"),
            "feedback_status": simulation.get("feedback_status"),
        },
        text=req.draft,
        risk_level=simulation.get("risk_level"),
        judgement=behaviour_judgement,
    )

    simulation_event = await record_relationship_event(
        db,
        event_type="message.simulated",
        pair_id=pair.id if pair else None,
        user_id=user.id,
        entity_type="message_simulation",
        payload=simulation_payload,
    )

    simulation_payload["feedback_status"] = simulation_payload.get("feedback_status") or "pending_feedback"

    await record_user_interaction_event(
        db,
        event_type="coach.simulate_message",
        user_id=user.id,
        pair_id=pair.id if pair else None,
        source="insights",
        page="message-simulation",
        path="/message-simulation",
        http_method="POST",
        http_status=200,
        target_type="message_simulation",
        payload=build_interaction_payload(
            {
                "conversation_goal": simulation.get("conversation_goal"),
                "suggested_tone": simulation.get("suggested_tone"),
                "safer_rewrite": (simulation.get("safer_rewrite") or req.draft)[:200],
                "algorithm_version": simulation.get("algorithm_version"),
                "confidence": simulation.get("confidence"),
                "decision_trace": simulation.get("decision_trace") or {},
                "focus_labels": simulation.get("focus_labels") or [],
                "risk_score": simulation.get("risk_score"),
                "baseline_delta": simulation.get("baseline_delta"),
                "fallback_reason": simulation.get("fallback_reason"),
                "shadow_result": simulation.get("shadow_result"),
                "feedback_status": simulation.get("feedback_status"),
            },
            text=req.draft,
            risk_level=simulation.get("risk_level"),
            judgement=behaviour_judgement,
        ),
    )

    if pair:
        await refresh_profile_and_plan(db, pair_id=pair.id)

    return MessageSimulationResponse(
        event_id=simulation_event.id,
        draft=req.draft,
        partner_view=simulation.get("partner_view", ""),
        likely_impact=simulation.get("likely_impact", ""),
        risk_level=simulation.get("risk_level", "medium"),
        risk_level_label=simulation.get("risk_level_label") or risk_level_label(simulation.get("risk_level", "medium")),
        risk_reason=simulation.get("risk_reason", ""),
        safer_rewrite=simulation.get("safer_rewrite", req.draft),
        suggested_tone=simulation.get("suggested_tone", ""),
        conversation_goal=simulation.get("conversation_goal"),
        do_list=simulation.get("do_list") or [],
        avoid_list=simulation.get("avoid_list") or [],
        algorithm_version=simulation.get("algorithm_version"),
        confidence=simulation.get("confidence"),
        decision_trace=simulation.get("decision_trace") or {},
        focus_labels=simulation.get("focus_labels") or [],
        risk_score=simulation.get("risk_score"),
        baseline_delta=simulation.get("baseline_delta"),
        fallback_reason=simulation.get("fallback_reason"),
        shadow_result=simulation.get("shadow_result"),
        feedback_status=simulation.get("feedback_status"),
        baseline_match=behaviour_judgement.get("baseline_match"),
        deviation_score=behaviour_judgement.get("deviation_score"),
        deviation_reasons=behaviour_judgement.get("deviation_reasons") or [],
        reaction_shift=behaviour_judgement.get("reaction_shift"),
        evidence_summary=safety_status.get("evidence_summary") or [],
        limitation_note=safety_status.get("limitation_note"),
        safety_handoff=safety_handoff,
        crisis_support=crisis_support or safety_status.get("crisis_support"),
    )


@router.post("/decision-feedback/{event_id}")
async def submit_message_decision_feedback(
    event_id: str,
    req: DecisionFeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        event_uuid = uuid.UUID(str(event_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="无效的结果事件ID")
    target_event = await db.get(RelationshipEvent, event_uuid)
    if not target_event:
        raise HTTPException(status_code=404, detail="结果事件不存在")

    if target_event.pair_id:
        await validate_pair_access(str(target_event.pair_id), user, db, require_active=False)
    elif not target_event.user_id or str(target_event.user_id) != str(user.id):
        raise HTTPException(status_code=403, detail="无权反馈这条结果")

    feedback_type = str(req.feedback_type or "").strip()
    payload = {
        "target_event_id": str(target_event.id),
        "target_event_type": target_event.event_type,
        "feedback_type": feedback_type,
        "feedback_label": decision_feedback_label(feedback_type),
        "note": (req.note or "")[:200] or None,
        "algorithm_version": "relationship_judgement_v2",
    }
    target_payload = dict(target_event.payload or {})
    target_payload.update(
        {
            "feedback_status": feedback_type,
            "feedback_label": decision_feedback_label(feedback_type),
            "feedback_note": (req.note or "")[:200] or None,
        }
    )
    target_event.payload = sanitize_event_payload(target_payload)
    event_type = (
        "message.feedback_submitted"
        if str(target_event.event_type).startswith("message.")
        else "alignment.feedback_submitted"
        if str(target_event.event_type).startswith("alignment.")
        else "decision.feedback_submitted"
    )
    feedback_event = await record_relationship_event(
        db,
        event_type=event_type,
        pair_id=target_event.pair_id,
        user_id=user.id,
        entity_type=target_event.entity_type,
        entity_id=target_event.id,
        payload=payload,
    )
    await db.commit()
    return {
        "accepted": True,
        "event_id": str(feedback_event.id),
        "target_event_id": str(target_event.id),
        "feedback_type": feedback_type,
        "feedback_label": decision_feedback_label(feedback_type),
    }


async def _authenticate_realtime_asr_websocket(
    websocket: WebSocket,
    db: AsyncSession,
) -> User | None:
    ticket = str(websocket.query_params.get("ticket") or "").strip()
    user_id = decode_realtime_ws_ticket(ticket) if ticket else None
    auth_header = ""

    if not user_id:
        auth_header = websocket.headers.get("authorization", "").strip()
        token = auth_header.removeprefix("Bearer ").strip()
        user_id = decode_access_token(token) if token else None

    if not user_id:
        message = "登录已失效，请重新登录" if ticket or auth_header else "缺少认证令牌"
        await websocket.send_json(
            {"type": "error", "code": "unauthorized", "message": message}
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
    result_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    partial_text = ""
    final_sent = False
    segment_texts: dict[int, str] = {}
    status = "completed"
    error_code = None

    def _sync_result_state() -> None:
        if result_state is None:
            return
        result_state["transcript"] = partial_text
        result_state["status"] = status
        result_state["error_code"] = error_code

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
                    _sync_result_state()
                    await websocket.send_json({"type": "partial", "text": partial_text})
                continue

            if event_type == "conversation.item.input_audio_transcription.completed":
                text = event.get("transcript") or event.get("text") or partial_text
                segment_id = event.get("segment_id")
                audio_info = _extract_realtime_audio_info(event)
                if text and isinstance(segment_id, int):
                    segment_texts[segment_id] = str(text)
                    text = "".join(
                        segment_texts[index] for index in sorted(segment_texts)
                    )
                if text:
                    partial_text = str(text)
                    _sync_result_state()
                    final_sent = True
                    await websocket.send_json(
                        _build_realtime_final_payload(
                            partial_text,
                            audio_info=audio_info,
                        )
                    )
                continue

            if event_type == "session.finished":
                text = event.get("transcript") or partial_text
                segment_id = event.get("segment_id")
                audio_info = _extract_realtime_audio_info(event)
                if text and isinstance(segment_id, int):
                    segment_texts[segment_id] = str(text)
                    text = "".join(
                        segment_texts[index] for index in sorted(segment_texts)
                    )
                if text:
                    final_text = str(text)
                    should_send_final = (not final_sent) or final_text != partial_text
                    partial_text = final_text
                    _sync_result_state()
                    if should_send_final:
                        await websocket.send_json(
                            _build_realtime_final_payload(
                                partial_text,
                                audio_info=audio_info,
                            )
                        )
                break

            if event_type == "error":
                status = "error"
                error_code = str(event.get("code") or "provider_error")
                _sync_result_state()
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": error_code,
                        "message": str(event.get("message") or "实时识别失败"),
                    }
                )
                break
    except asyncio.CancelledError:
        _sync_result_state()
        raise
    except WebSocketDisconnect:
        status = "error"
        error_code = "websocket_disconnect"
        _sync_result_state()
    except Exception:
        status = "error"
        error_code = "provider_error"
        _sync_result_state()
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
    _sync_result_state()
    return {"transcript": partial_text, "status": status, "error_code": error_code}


def _extract_realtime_audio_info(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("audio_info")
    if isinstance(payload, dict):
        audio_info = {
            key: str(payload.get(key) or "").strip()
            for key in ("type", "language", "emotion")
            if payload.get(key) is not None and str(payload.get(key) or "").strip()
        }
        if audio_info and "type" not in audio_info:
            audio_info["type"] = "audio_info"
        return audio_info

    audio_info = {
        key: str(event.get(key) or "").strip()
        for key in ("language", "emotion")
        if event.get(key) is not None and str(event.get(key) or "").strip()
    }
    if audio_info:
        audio_info["type"] = "audio_info"
    return audio_info


def _build_realtime_final_payload(
    text: str | None,
    *,
    audio_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    transcript = str(text or "").strip()
    emotion_summary = summarize_text_emotion(transcript)
    language_code = str(
        (audio_info or {}).get("language") or infer_language(transcript)
    ).strip()
    emotion_code = str((audio_info or {}).get("emotion") or "").strip()

    return {
        "type": "final",
        "text": transcript,
        "audio_info": audio_info or None,
        "voice_emotion": {
            "code": emotion_code,
            "label": emotion_label(emotion_code),
        },
        "content_emotion": emotion_summary,
        "transcript_language": {
            "code": language_code,
            "label": language_label(language_code),
        },
    }


def _realtime_asr_latency_ms(started_at: float | None) -> int | None:
    if started_at is None:
        return None
    return int(max(0.0, perf_counter() - started_at) * 1000)


def _realtime_asr_max_session_seconds() -> int:
    try:
        configured = int(getattr(settings, "REALTIME_ASR_MAX_SESSION_SECONDS", 60))
    except (TypeError, ValueError):
        configured = 60
    return max(
        REALTIME_ASR_MIN_SESSION_SECONDS,
        min(REALTIME_ASR_MAX_SESSION_SECONDS, configured),
    )


def _realtime_asr_remaining_seconds(started_at: float | None) -> float | None:
    if started_at is None:
        return None
    return max(0.0, _realtime_asr_max_session_seconds() - (perf_counter() - started_at))


async def _finish_realtime_asr_session(
    provider,
    provider_task: asyncio.Task | None,
    websocket: WebSocket,
    realtime_result: dict[str, Any],
) -> tuple[asyncio.Task | None, dict[str, Any]]:
    await provider.stop_session()
    if provider_task is None:
        return None, realtime_result

    try:
        realtime_result = await asyncio.wait_for(
            provider_task,
            timeout=settings.REALTIME_ASR_STOP_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        provider_task.cancel()
        try:
            await provider_task
        except asyncio.CancelledError:
            pass
        fallback_transcript = str(realtime_result.get("transcript") or "").strip()
        if fallback_transcript:
            try:
                await websocket.send_json(_build_realtime_final_payload(fallback_transcript))
            except Exception:
                pass
            realtime_result = {
                "transcript": fallback_transcript,
                "status": "completed",
                "error_code": "provider_timeout_fallback",
            }
        else:
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "provider_timeout",
                    "message": "实时识别收尾超时，已终止当前会话",
                }
            )
            realtime_result = {
                "transcript": "",
                "status": "error",
                "error_code": "provider_timeout",
            }
    return None, realtime_result


async def _log_realtime_asr_audit(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider_name: str,
    model_name: str,
    started_at: float | None,
    result: dict[str, Any] | None = None,
) -> None:
    payload = result or {}
    try:
        await log_privacy_transcription(
            db,
            scope="solo",
            user_id=user_id,
            provider=provider_name,
            model=model_name,
            file_name="[realtime_asr_stream]",
            raw_output=str(payload.get("transcript") or "") or None,
            latency_ms=_realtime_asr_latency_ms(started_at),
            status=str(payload.get("status") or "completed"),
            error_code=payload.get("error_code"),
        )
        await db.commit()
    except Exception:
        logger.exception("failed to write realtime asr privacy audit")


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
    provider_name: str | None = None
    provider_model: str | None = None
    session_started_at: float | None = None
    realtime_audit_logged = False
    realtime_result: dict[str, Any] = {
        "transcript": "",
        "status": "completed",
        "error_code": None,
    }

    try:
        while True:
            receive_timeout = _realtime_asr_remaining_seconds(session_started_at)
            try:
                payload = (
                    await asyncio.wait_for(websocket.receive_json(), timeout=receive_timeout)
                    if provider is not None and receive_timeout is not None
                    else await websocket.receive_json()
                )
            except asyncio.TimeoutError:
                if provider is None:
                    continue
                await websocket.send_json(
                    {
                        "type": "notice",
                        "code": "session_max_duration",
                        "message": f"录音已到 {_realtime_asr_max_session_seconds()} 秒上限，正在保存这段语音。",
                    }
                )
                provider_task, realtime_result = await _finish_realtime_asr_session(
                    provider,
                    provider_task,
                    websocket,
                    realtime_result,
                )
                if provider_name and provider_model:
                    await _log_realtime_asr_audit(
                        db,
                        user_id=user.id,
                        provider_name=provider_name,
                        model_name=provider_model,
                        started_at=session_started_at,
                        result=realtime_result,
                    )
                    realtime_audit_logged = True
                await provider.close()
                provider = None
                provider_name = None
                provider_model = None
                session_started_at = None
                continue
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

                provider_name = str(payload.get("provider") or settings.REALTIME_ASR_PROVIDER)
                requested_model = payload.get("model")
                session_started_at = perf_counter()
                realtime_audit_logged = False
                realtime_result = {
                    "transcript": "",
                    "status": "completed",
                    "error_code": None,
                }
                provider = create_realtime_asr_client(
                    provider=provider_name,
                    model=str(requested_model) if requested_model else None,
                    language=str(payload.get("language") or "zh"),
                    sample_rate=int(payload.get("sample_rate") or 16000),
                    input_audio_format=str(payload.get("format") or "pcm"),
                )
                provider_model = str(
                    getattr(provider, "model", None)
                    or requested_model
                    or settings.QWEN_ASR_REALTIME_MODEL
                )
                await provider.connect()
                await provider.start_session()
                provider_task = asyncio.create_task(
                    _pump_realtime_asr_events(provider, websocket, realtime_result)
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

                provider_task, realtime_result = await _finish_realtime_asr_session(
                    provider,
                    provider_task,
                    websocket,
                    realtime_result,
                )
                if provider_name and provider_model:
                    await _log_realtime_asr_audit(
                        db,
                        user_id=user.id,
                        provider_name=provider_name,
                        model_name=provider_model,
                        started_at=session_started_at,
                        result=realtime_result,
                    )
                    realtime_audit_logged = True
                await provider.close()
                provider = None
                provider_name = None
                provider_model = None
                session_started_at = None
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
        realtime_result = {
            "transcript": realtime_result.get("transcript") or "",
            "status": "error",
            "error_code": "websocket_disconnect",
        }
    except Exception:
        logger.exception("realtime asr websocket failed")
        realtime_result = {
            "transcript": realtime_result.get("transcript") or "",
            "status": "error",
            "error_code": "server_error",
        }
        try:
            await websocket.send_json(
                {"type": "error", "code": "server_error", "message": "实时识别服务异常"}
            )
        except Exception:
            pass
    finally:
        if provider_task is not None and provider_task.done():
            try:
                realtime_result = provider_task.result()
            except asyncio.CancelledError:
                pass
            except Exception:
                realtime_result = {
                    "transcript": realtime_result.get("transcript") or "",
                    "status": "error",
                    "error_code": "provider_error",
                }
        if provider_task is not None and not provider_task.done():
            provider_task.cancel()
            try:
                await provider_task
            except asyncio.CancelledError:
                pass
        if (
            not realtime_audit_logged
            and provider_name
            and provider_model
            and session_started_at is not None
        ):
            await _log_realtime_asr_audit(
                db,
                user_id=user.id,
                provider_name=provider_name,
                model_name=provider_model,
                started_at=session_started_at,
                result=realtime_result,
            )
        if provider is not None:
            await provider.close()
        try:
            await websocket.close()
        except Exception:
            pass
