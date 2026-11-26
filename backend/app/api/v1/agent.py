"""AI 智能伴侣 Agent 接口（陪伴、聊天、数据提取式打卡）"""

import asyncio
import json
import logging
import uuid
from datetime import date, datetime, timezone
from app.core.time import current_local_date
from contextlib import asynccontextmanager
from time import monotonic, perf_counter
from typing import Any, Literal
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, validate_pair_access
from app.ai.asr import create_realtime_asr_client
from app.core.security import (
    create_realtime_ws_ticket,
    decode_access_token_payload,
    decode_realtime_ws_ticket_payload,
)
from app.services.ws_ticket_store import get_ws_ticket_store
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
    StyleFeedbackRequest,
    TaskCreateRequest,
)
from app.ai import create_chat_completion
from app.ai.agent_loop import run_agent_loop
from app.ai.multi_agent import run_multi_agent_flow
from app.ai.tools import AGENT_TOOL_GUIDANCE
from app.ai.policy import compose_relationship_system_prompt
from app.ai.conversation import build_agent_system_prompt
from app.services.relationship_memory import get_active_taboos
from app.services.product_prefs import normalize_product_prefs
from app.services.tone_preference import (
    guide_text as tone_guide_text,
    is_default as tone_is_default,
    read_profile as tone_read_profile,
    record_signal as tone_record_signal,
    reset_profile as tone_reset_profile,
)
from app.services.agent_delivery import prepare_chat_turn, complete_chat_turn, fail_chat_turn
from app.ai.message_simulator import (
    SIMULATION_TIMEOUT_SECONDS,
    simulate_message_preview,
    MessageSimulationUnavailableError,
)
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
    translate_inline_codes,
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


import re

_CN_DIGIT_MAP = str.maketrans("零一二三四五六七八九两", "01234567892")
_PROPOSAL_NOISE_RE = re.compile(r"[\s，。、；：！？,.!?;:（）()\[\]“”\"'·\-—]+")
_PROPOSAL_PREFIX_RE = re.compile(r"^(?:今晚|今天|明天|睡前|晚饭后|下班后|抽空|一起|共同|双方)+")


def _normalize_proposal_text(text: Any) -> str:
    raw = str(text or "").strip().lower().translate(_CN_DIGIT_MAP)
    raw = re.sub(r"十(\d)", r"1\1", raw)
    raw = re.sub(r"(\d)十", r"\g<1>0", raw)
    raw = raw.replace("十", "10")
    raw = _PROPOSAL_NOISE_RE.sub("", raw)
    return _PROPOSAL_PREFIX_RE.sub("", raw) or raw


def _char_bigrams(text: str) -> set[str]:
    if len(text) < 2:
        return {text} if text else set()
    return {text[i : i + 2] for i in range(len(text) - 1)}


def _is_similar_task_proposal(candidate: dict[str, Any], existing: dict[str, Any]) -> bool:
    if str(candidate.get("due_date") or "") != str(existing.get("due_date") or ""):
        return False
    title_a = _normalize_proposal_text(candidate.get("title"))
    title_b = _normalize_proposal_text(existing.get("title"))
    if title_a and title_b:
        if title_a == title_b:
            return True
        shorter, longer = (title_a, title_b) if len(title_a) <= len(title_b) else (title_b, title_a)
        if len(shorter) >= 4 and shorter in longer:
            return True
        bigrams_a, bigrams_b = _char_bigrams(title_a), _char_bigrams(title_b)
        union = bigrams_a | bigrams_b
        if union and (len(bigrams_a & bigrams_b) / len(union)) >= 0.45:
            return True

    full_a = _normalize_proposal_text(f"{candidate.get('title') or ''}{candidate.get('description') or ''}")
    full_b = _normalize_proposal_text(f"{existing.get('title') or ''}{existing.get('description') or ''}")
    if full_a and full_b:
        if full_a == full_b:
            return True
        bigrams_a, bigrams_b = _char_bigrams(full_a), _char_bigrams(full_b)
        union = bigrams_a | bigrams_b
        if union and (len(bigrams_a & bigrams_b) / len(union)) >= 0.55:
            return True
    return False


def _task_proposals_from_steps(steps):
    proposals: list[dict[str, Any]] = []
    for step in steps:
        for item in step.tool_results or []:
            result = item.get('result') or {}
            data = result.get('data') or {}
            if item.get('name') == 'create_task' and result.get('status') == 'success' and data.get('requires_confirmation'):
                matched_index = next(
                    (idx for idx, existing in enumerate(proposals) if _is_similar_task_proposal(data, existing)),
                    None,
                )
                if matched_index is not None:
                    proposals[matched_index] = data
                    continue
                if len(proposals) < 5:
                    proposals.append(data)
    return proposals


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
    """生成实时语音临时访问令牌，避免在 WebSocket 地址中暴露长期有效的 JWT。"""
    return AgentRealtimeTicketResponse(
        ticket=create_realtime_ws_ticket(
            str(user.id),
            token_version=int(getattr(user, "token_version", 0) or 0),
        ),
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
    pair = None
    if session.pair_id:
        pair = await validate_pair_access(session.pair_id, user, db, require_active=True)
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

    # 记录用户的消息
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

    # 调用 AI 循环
    include_checkin = (req.surface != "chat" and not session.has_extracted_checkin)

    try:
        # Summary failures must also leave the saved turn retryable.
        history = await refresh_session_summary_if_needed(db, session=session)
        await db.commit()
        active_taboos = []
        if session.pair_id:
            try:
                active_taboos = await get_active_taboos(db, pair_id=session.pair_id, user_id=user.id)
            except Exception:
                active_taboos = []
        from app.services.companion_style import (
            build_companion_style_prompt,
            merge_taboos,
            resolve_companion_context,
        )
        companion_ctx = resolve_companion_context(
            user,
            pair=pair,
            pair_id=session.pair_id,
            requested_style=req.tone_preference,
            requested_intensity=req.expression_intensity,
            current_text=effective_content,
        )
        system_prompt = build_agent_system_prompt(
            surface=req.surface,
            intent=req.scene_context.intent if req.scene_context else 'auto',
            taboos=merge_taboos(companion_ctx.get("habit_taboos"), active_taboos),
            companion_style_block=build_companion_style_prompt(companion_ctx),
        )
        from app.services.chat_memory_permission import save_question_guard
        guard = save_question_guard(history)
        if guard:
            system_prompt = f"{system_prompt}\n\n## 这一轮要注意\n- {guard}"
        messages_for_llm = build_messages_for_llm(
            system_prompt=system_prompt,
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
                chat_deadline=monotonic() + AGENT_COMPLETION_TIMEOUT_SECONDS,
            ):
                reply_content, agent_steps, checkin_extracted = await asyncio.wait_for(
                    run_agent_loop(
                        messages=messages_for_llm,
                        pair_id=str(session.pair_id) if session.pair_id else None,
                        user_id=str(user.id),
                        session_id=str(session.id),
                        user_message_id=str(user_msg.id),
                        db=db,
                        include_checkin_tool=include_checkin,
                    ),
                    timeout=AGENT_COMPLETION_TIMEOUT_SECONDS,
                )
        except asyncio.TimeoutError:
            logger.warning("agent chat completion timed out")
            raise HTTPException(status_code=504, detail="这次没能及时收到模型回复，请稍后重试这条消息。")
        except Exception as exc:
            logger.warning("agent loop failed: %s", exc.__class__.__name__)
            raise HTTPException(status_code=502, detail="这次没能连上助手，请稍后重试。") from exc

        # 如果没有内容则兜底
        if not reply_content or not reply_content.strip():
            raise HTTPException(status_code=502, detail="这次没有收到回复，请重试。")

        from app.services.reply_style import polish_reply
        from app.services.draft_grounding import needs_draft_review
        reply_content = polish_reply(reply_content, draft_requested=bool(
            (req.scene_context and req.scene_context.intent == 'wording') or needs_draft_review(messages_for_llm)))
        if not reply_content.strip():
            raise HTTPException(status_code=502, detail="这次没有收到完整回复，请重试。")

        if session.pair_id:
            # 用户自己说出危险信号时留一份预警，私密单聊只通知本人。
            try:
                from app.services.crisis_processor import record_chat_crisis_signal
                await record_chat_crisis_signal(
                    db,
                    pair_id=session.pair_id,
                    user_id=user.id,
                    text=effective_content,
                    source_ref=f"session:{session.id}",
                )
            except Exception as exc:
                logger.warning("record chat crisis signal failed: %s", exc.__class__.__name__)

        action = "chat"
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
                    interaction_initiative="equal",
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

        # 保存 AI 最终回复和思路
        task_proposals = _task_proposals_from_steps(agent_steps)
        reply_payload = {'task_proposals': task_proposals} if task_proposals else {}
        if ((user_msg.payload or {}).get('memory_removal_request') or {}).get('state') == 'pending':
            reply_payload['memory_removal_request_id'] = str(user_msg.id)
        assistant_msg = AgentChatMessage(
            session_id=session.id, role="assistant", content=reply_content,
            payload=reply_payload or None,
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
    from app.services.intervention_evaluation import (
        RECOMMENDATION_LABELS,
        build_intervention_evaluation,
    )
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
            or intervention.get("recommendation_reason")
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
    risk_display = (
        "低风险（整体平稳）"
        if risk_level in ("low", "none")
        else risk_level_label(risk_level)
    )
    report_lines.append(f"当前风险等级为“{risk_display}”。")
    if risk_reason:
        report_lines.append(translate_inline_codes(risk_reason))
    if isinstance(intervention, dict) and intervention.get("recommendation"):
        recommendation = str(intervention["recommendation"])
        recommendation_text = (
            intervention.get("recommendation_label")
            or RECOMMENDATION_LABELS.get(recommendation)
            or translate_inline_codes(recommendation)
        )
        report_lines.append(f"建议：{recommendation_text}")
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


def _resolve_background_tasks(background_tasks: BackgroundTasks) -> BackgroundTasks:
    return background_tasks


@router.post(
    "/sessions/{session_id}/collaborate",
    response_model=AgentSwarmResponse,
)
async def collaborate_multi_agent(
    session_id: uuid.UUID,
    req: AgentChatRequest,
    background_tasks: BackgroundTasks = Depends(_resolve_background_tasks),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """多智能体协作：感知→分析→行动→陪伴 四个角色接力处理后给出陪伴回复。

    这是一个面向展示与体验的入口；普通聊天仍走 /chat。
    """
    session = await db.get(AgentChatSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    pair = None
    if session.pair_id:
        pair = await validate_pair_access(session.pair_id, user, db, require_active=True)
    checkin_extracted = False
    effective_content = str(req.content or "").strip()
    user_payload = {
        "surface": req.surface,
        "multi_agent": True,
        **({"scene_context": req.scene_context.model_dump()} if req.scene_context else {}),
    }
    user_msg, cached_reply, _ = await prepare_chat_turn(
        db,
        session_id=session.id,
        client_message_id=req.client_message_id,
        content=effective_content,
        payload=user_payload,
    )
    if cached_reply is not None:
        return AgentSwarmResponse(
            reply=cached_reply.reply,
            action=cached_reply.action,
            message_id=cached_reply.message_id,
            task_proposals=cached_reply.task_proposals,
            swarm=[],
            trace=[],
        )
    touch_session_activity(session)
    await db.flush()
    user_message_id = user_msg.id
    await db.commit()

    try:
        history = await refresh_session_summary_if_needed(db, session=session)
        await db.commit()
        active_taboos = []
        if session.pair_id:
            try:
                active_taboos = await get_active_taboos(db, pair_id=session.pair_id, user_id=user.id)
            except Exception:
                active_taboos = []
        from app.services.companion_style import (
            build_companion_style_prompt,
            merge_taboos,
            resolve_companion_context,
        )
        companion_ctx = resolve_companion_context(
            user,
            pair=pair,
            pair_id=session.pair_id,
            requested_style=req.tone_preference,
            requested_intensity=req.expression_intensity,
            current_text=effective_content,
        )
        system_prompt = build_agent_system_prompt(
            surface=req.surface,
            intent=req.scene_context.intent if req.scene_context else 'auto',
            taboos=merge_taboos(companion_ctx.get("habit_taboos"), active_taboos),
            companion_style_block=build_companion_style_prompt(companion_ctx),
        )
        from app.services.chat_memory_permission import save_question_guard
        guard = save_question_guard(history)
        if guard:
            system_prompt = f"{system_prompt}\n\n## 这一轮要注意\n- {guard}"
        messages_for_llm = build_messages_for_llm(
            system_prompt=system_prompt,
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
                chat_deadline=monotonic() + MULTI_AGENT_COMPLETION_TIMEOUT_SECONDS,
            ):
                final_reply, final_steps, swarm, checkin_extracted = await asyncio.wait_for(
                    run_multi_agent_flow(
                        messages=messages_for_llm,
                        pair_id=str(session.pair_id) if session.pair_id else None,
                        user_id=str(user.id),
                        session_id=str(session.id),
                        user_message_id=str(user_msg.id),
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

        from app.services.reply_style import polish_reply
        from app.services.draft_grounding import needs_draft_review
        final_reply = polish_reply(final_reply, draft_requested=bool(
            (req.scene_context and req.scene_context.intent == 'wording') or needs_draft_review(messages_for_llm)))
        if not final_reply.strip():
            raise HTTPException(status_code=502, detail="这次没有收到完整回复，请重试。")

        if session.pair_id:
            try:
                from app.services.crisis_processor import record_chat_crisis_signal
                await record_chat_crisis_signal(
                    db,
                    pair_id=session.pair_id,
                    user_id=user.id,
                    text=effective_content,
                    source_ref=f"session:{session.id}",
                )
            except Exception as exc:
                logger.warning("record collaborate crisis signal failed: %s", exc.__class__.__name__)

        action = "checkin_extracted" if checkin_extracted else "chat"
        if checkin_extracted:
            func_args = {}
            for step in final_steps:
                for tc in getattr(step, "tool_calls", None) or []:
                    fn = tc.get("function") or {}
                    if fn.get("name") == "extract_checkin_data":
                        try:
                            func_args = json.loads(fn.get("arguments") or "{}")
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
                    interaction_initiative="equal",
                    deep_conversation=func_args.get("deep_conversation", False),
                    task_completed=False,
                )
                try:
                    resolved_tasks = (
                        background_tasks
                        if isinstance(background_tasks, BackgroundTasks)
                        else BackgroundTasks()
                    )
                    await create_checkin(
                        req=checkin_req,
                        background_tasks=resolved_tasks,
                        mode="solo" if not session.pair_id else None,
                        user=user,
                        db=db,
                    )
                    session.has_extracted_checkin = True
                except Exception as exc:
                    logger.error("Save collaborative checkin failed: %s", exc.__class__.__name__)

        task_proposals = _task_proposals_from_steps(final_steps)
        reply_payload = {'task_proposals': task_proposals} if task_proposals else {}
        if ((user_msg.payload or {}).get('memory_removal_request') or {}).get('state') == 'pending':
            reply_payload['memory_removal_request_id'] = str(user_msg.id)
        assistant_msg = AgentChatMessage(
            session_id=session.id, role="assistant", content=final_reply,
            payload=reply_payload or None,
        )
        db.add(assistant_msg)
        await db.flush()
        complete_chat_turn(user_msg, reply_id=assistant_msg.id, action=action)
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
    except HTTPException:
        await db.rollback()
        await fail_chat_turn(db, user_message_id)
        raise
    except Exception:
        await db.rollback()
        await fail_chat_turn(db, user_message_id)
        logger.exception("multi-agent collaborate failed")
        raise HTTPException(status_code=500, detail="智能服务暂时不可用，请稍后再试")


@router.post("/simulate-message", response_model=MessageSimulationResponse)
async def simulate_message(
    req: MessageSimulationRequest,
    pair_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """在消息发出前做一轮关系语境下的风险预演。"""
    t_total_start = perf_counter()
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

    t_snapshot_start = perf_counter()
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
    snapshot_ms = int((perf_counter() - t_snapshot_start) * 1000)

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
    from app.services.companion_style import (
        build_simulation_style_context,
        resolve_companion_context,
    )
    pair_taboos = []
    if pair:
        try:
            pair_taboos = await get_active_taboos(db, pair_id=pair.id, user_id=user.id)
        except Exception:
            pair_taboos = []
    companion_ctx = resolve_companion_context(
        user,
        pair=pair,
        pair_id=pair.id if pair else None,
        requested_style=req.tone_preference,
        requested_intensity=req.expression_intensity,
        current_text=req.draft,
    )
    context["communication_profile"] = build_simulation_style_context(
        companion_ctx,
        pair_taboos=pair_taboos,
    )

    t_model_start = perf_counter()
    try:
        with privacy_audit_scope(
            db=db,
            user_id=user.id,
            pair_id=pair.id if pair else None,
            scope="pair" if pair else "solo",
            run_type="message_simulation",
            privacy_mode=privacy_mode,
            chat_deadline=monotonic() + SIMULATION_TIMEOUT_SECONDS,
        ):
            simulation = await simulate_message_preview(req.draft, context)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="处理超过 1 分钟，已自动超时，请稍后再试")
    except MessageSimulationUnavailableError:
        raise HTTPException(status_code=502, detail="这次没能完成改写，原句已保留，请重试。")
    model_ms = int((perf_counter() - t_model_start) * 1000)
    t_post_start = perf_counter()
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
            "safer_rewrite": simulation.get("safer_rewrite", "")[:200],
            "rewrite_blocked": simulation.get("rewrite_blocked", False),
            "rewrite_block_reason": simulation.get("rewrite_block_reason"),
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
                "safer_rewrite": simulation.get("safer_rewrite", "")[:200],
                "rewrite_blocked": simulation.get("rewrite_blocked", False),
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
    post_persist_ms = int((perf_counter() - t_post_start) * 1000)
    total_ms = int((perf_counter() - t_total_start) * 1000)
    sim_sub = simulation.get("_timings_ms") or {}
    stage_timings_ms = {
        "snapshot_ms": snapshot_ms,
        "baseline_ms": int(sim_sub.get("baseline_ms") or 0),
        "llm_ms": int(sim_sub.get("llm_ms") or model_ms),
        "model_stage_ms": model_ms,
        "persist_ms": post_persist_ms,
        "total_ms": total_ms,
    }
    logger.info("message_simulation_timings scope=%s timings=%s", "pair" if pair else "solo", stage_timings_ms)

    return MessageSimulationResponse(
        event_id=simulation_event.id,
        draft=req.draft,
        partner_view=simulation.get("partner_view", ""),
        likely_impact=simulation.get("likely_impact", ""),
        risk_level=simulation.get("risk_level", "medium"),
        risk_level_label=simulation.get("risk_level_label") or risk_level_label(simulation.get("risk_level", "medium")),
        risk_reason=simulation.get("risk_reason", ""),
        speaker_attribution=simulation.get("speaker_attribution"),
        pressure_risk_level=simulation.get("pressure_risk_level"),
        pressure_risk_label=simulation.get("pressure_risk_label"),
        escalation_friction_level=simulation.get("escalation_friction_level"),
        escalation_friction_label=simulation.get("escalation_friction_label"),
        escalation_cues=simulation.get("escalation_cues") or [],
        safer_rewrite=simulation.get("safer_rewrite", req.draft),
        rewrite_blocked=simulation.get("rewrite_blocked", False),
        rewrite_block_reason=simulation.get("rewrite_block_reason"),
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
        stage_timings_ms=stage_timings_ms,
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


@asynccontextmanager
async def _open_ws_db_session(websocket: WebSocket):
    db_dep = websocket.app.dependency_overrides.get(get_db, get_db)
    gen = db_dep()
    db = await anext(gen)
    try:
        yield db
    except Exception:
        try:
            await gen.athrow(Exception("ws_db_rollback"))
        except StopAsyncIteration:
            pass
        except Exception:
            pass
        raise
    else:
        try:
            await anext(gen)
        except StopAsyncIteration:
            pass
    finally:
        await gen.aclose()


async def _authenticate_realtime_asr_websocket(
    websocket: WebSocket,
    db: AsyncSession,
) -> User | None:
    ticket = str(websocket.query_params.get("ticket") or "").strip()
    auth_payload = decode_realtime_ws_ticket_payload(ticket) if ticket else None
    auth_header = ""

    if auth_payload is not None:
        consumed = await get_ws_ticket_store().consume_once(
            auth_payload["jti"], auth_payload["remaining_seconds"]
        )
        if not consumed:
            auth_payload = None
    elif not ticket:
        auth_header = websocket.headers.get("authorization", "").strip()
        token = auth_header.removeprefix("Bearer ").strip()
        auth_payload = decode_access_token_payload(token) if token else None

    if not auth_payload:
        message = "登录已失效，请重新登录" if ticket or auth_header else "缺少认证令牌"
        await websocket.send_json(
            {"type": "error", "code": "unauthorized", "message": message}
        )
        await websocket.close(code=4401)
        return None

    try:
        user_uuid = uuid.UUID(str(auth_payload["user_id"]))
    except (TypeError, ValueError):
        await websocket.send_json(
            {"type": "error", "code": "unauthorized", "message": "登录信息无效，请重新登录"}
        )
        await websocket.close(code=4401)
        return None

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if (
        not user
        or (user.email or "").startswith("deleted_")
        or int(getattr(user, "token_version", 0) or 0)
        != int(auth_payload.get("token_version", 0) or 0)
    ):
        await websocket.send_json(
            {"type": "error", "code": "unauthorized", "message": "登录已失效，请重新登录"}
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
):
    """统一实时语音识别入口，由后端代理到配置的 realtime ASR provider。"""
    await websocket.accept()
    async with _open_ws_db_session(websocket) as auth_db:
        user = await _authenticate_realtime_asr_websocket(websocket, auth_db)
    if not user:
        return
    user_id = user.id

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
                    async with _open_ws_db_session(websocket) as audit_db:
                        await _log_realtime_asr_audit(
                            audit_db,
                            user_id=user_id,
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

                provider_name = str(settings.REALTIME_ASR_PROVIDER)
                sample_rate_raw = int(payload.get("sample_rate") or 16000)
                sample_rate = (
                    sample_rate_raw
                    if sample_rate_raw in {8000, 16000, 24000, 44100, 48000}
                    else 16000
                )
                audio_format_raw = str(payload.get("format") or "pcm").lower()
                audio_format = audio_format_raw if audio_format_raw in {"pcm", "wav", "opus"} else "pcm"
                language_raw = str(payload.get("language") or "zh").strip()[:16] or "zh"
                session_started_at = perf_counter()
                realtime_audit_logged = False
                realtime_result = {
                    "transcript": "",
                    "status": "completed",
                    "error_code": None,
                }
                provider = create_realtime_asr_client(
                    provider=provider_name,
                    model=None,
                    language=language_raw,
                    sample_rate=sample_rate,
                    input_audio_format=audio_format,
                )
                provider_model = str(
                    getattr(provider, "model", None)
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
                    async with _open_ws_db_session(websocket) as audit_db:
                        await _log_realtime_asr_audit(
                            audit_db,
                            user_id=user_id,
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
        logger.info("realtime asr websocket disconnected user=%s", user_id)
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
            async with _open_ws_db_session(websocket) as audit_db:
                await _log_realtime_asr_audit(
                    audit_db,
                    user_id=user_id,
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


# 多步骤分析接口


@router.post("/skill/analyze")
async def skill_analyze(
    pair_id: uuid.UUID,
    content: str,
    save_memories: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """调用各分析模块处理关系事件，并返回分析结果和建议。

    前端用这个端点发送复杂关系事件，后端自动执行：
    表达澄清 → 立场分析 → 冲突识别 → 行动规划 → 记忆提取

    记忆提取的结果默认只作为建议返回，不直接落库；用户在界面上确认要长期记住，
    调用时带上 save_memories=true 再写一次，和单聊里的保存口径保持一致。
    """
    from app.ai.skill_orchestrator import orchestrate
    from app.services.relationship_memory import recall_memories, batch_store_from_skill
    from app.models import SkillAnalysisRecord

    pair = await validate_pair_access(pair_id, user, db, require_active=True)

    # 查找相关的历史记录，供本次分析参考
    memories = await recall_memories(
        db, pair_id=pair_id, user_id=user.id, query=content, limit=5,
    )

    # 独立分析遵守整轮等待预算，分析模型由编排器明确选择。
    with privacy_audit_scope(chat_deadline=monotonic() + AGENT_COMPLETION_TIMEOUT_SECONDS):
        package = await orchestrate(
            content,
            combine_core=True,
            pair_id=str(pair_id),
            user_id=str(user.id),
            relationship_memories=memories,
        )

    delivery = package.to_dict()

    # 保存分析记录
    record = SkillAnalysisRecord(
        pair_id=pair_id,
        user_id=user.id,
        user_input=content,
        primary_intent=package.primary_intent,
        delivery_json=delivery,
    )
    db.add(record)

    # 记忆提取结果默认只回给前端当建议，用户确认后再写
    stored_memories = 0
    if package.memories_to_save and save_memories:
        await batch_store_from_skill(
            db,
            pair_id=pair_id,
            user_id=user.id,
            memories=package.memories_to_save,
        )
        stored_memories = len(package.memories_to_save)

    await db.commit()

    failed_skills = [
        {
            "skill": step["skill_name"],
            "status": step["status"],
            "reason": step.get("reason"),
        }
        for step in delivery["skill_trace"]
        if step["status"] not in {"ok", "success"}
    ]

    return {
        "record_id": str(record.id),
        "delivery": delivery,
        "related_memories": memories,
        "pending_memories": package.memories_to_save or [],
        "memories_saved": stored_memories,
        "partial": bool(failed_skills),
        "failed_skills": failed_skills,
    }


@router.post("/skill/select-proposal")
async def skill_select_proposal(
    pair_id: uuid.UUID,
    record_id: uuid.UUID,
    proposal_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """选择方案 — 用户选定方案后，生成沟通草稿 + 行动计划。"""
    from app.ai.skill_orchestrator import generate_draft_for_proposal
    from app.models import SkillAnalysisRecord

    await validate_pair_access(pair_id, user, db, require_active=True)

    record = await db.get(SkillAnalysisRecord, record_id)
    if not record or record.user_id != user.id or record.pair_id != pair_id:
        raise HTTPException(status_code=404, detail="分析记录不存在")

    # 从保存的分析结果中提取上下文
    delivery_json = record.delivery_json or {}
    analysis_results = {}
    # 将 delivery 中的结构化数据回传给草稿 Skill
    if delivery_json.get("summary"):
        analysis_results["expression_clarify"] = delivery_json["summary"]
    if delivery_json.get("stances"):
        analysis_results["stance_analysis"] = {"stances": delivery_json["stances"]}
    if delivery_json.get("proposals"):
        analysis_results["action_plan"] = {"proposals": delivery_json["proposals"]}

    with privacy_audit_scope(chat_deadline=monotonic() + AGENT_COMPLETION_TIMEOUT_SECONDS):
        draft = await generate_draft_for_proposal(
            record.user_input,
            proposal_id,
            analysis_results=analysis_results,
        )

    # 更新记录（使用新字典赋值触发 SQLAlchemy JSON 字段变更保存）
    record.selected_proposal_id = proposal_id
    record.delivery_json = {**delivery_json, "draft": draft}
    await db.commit()

    return {"draft": draft, "proposal_id": proposal_id}


@router.post("/skill/review")
async def skill_review(
    pair_id: uuid.UUID,
    content: str,
    record_id: uuid.UUID | None = None,
    save_memories: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """复盘 — 对一次关系事件进行复盘分析。

    复盘里顺带提取的记忆同样先当建议返回，用户确认（save_memories=true）才写库。
    """
    from app.ai.skill_registry import SKILL_REGISTRY, execute_skill
    from app.ai.skill_registry import SkillOutput
    from app.services.relationship_memory import batch_store_from_skill
    import app.ai.skills  # noqa: F401

    await validate_pair_access(pair_id, user, db, require_active=True)

    review_skill = SKILL_REGISTRY.get("review")
    memory_skill = SKILL_REGISTRY.get("memory_write")
    if not review_skill:
        raise HTTPException(status_code=500, detail="复盘模块不可用")

    context = {"user_input": content, "review_input": content}
    memories_to_save = []
    memories_saved = 0
    memory_output = None
    with privacy_audit_scope(chat_deadline=monotonic() + AGENT_COMPLETION_TIMEOUT_SECONDS):
        review_output = await execute_skill(
            review_skill, context=context, previous_results={},
        )
        if memory_skill:
            memory_output = await execute_skill(
                memory_skill, context=context,
                previous_results={"review": review_output},
            )

    # 同时提取记忆（默认只回建议）
    if memory_output and memory_output.success:
        memories_to_save = memory_output.data.get("memories", [])
        if save_memories and memories_to_save:
            await batch_store_from_skill(
                db, pair_id=pair_id, user_id=user.id, memories=memories_to_save,
            )
            memories_saved = len(memories_to_save)

    await db.commit()
    failed_skills = []
    if not review_output.success:
        failed_skills.append(
            {
                "skill": "review",
                "status": "ok" if review_output.success else "error",
                "reason": review_output.error,
            }
        )
    if memory_output is not None and not memory_output.success:
        failed_skills.append(
            {
                "skill": "memory_write",
                "status": "ok" if memory_output.success else "error",
                "reason": memory_output.error,
            }
        )
    return {
        "review": review_output.data if review_output.success else {},
        "memories_saved": memories_saved,
        "pending_memories": memories_to_save,
        "partial": bool(failed_skills),
        "failed_skills": failed_skills,
    }


@router.get("/skill/memories")
async def skill_memories(
    pair_id: uuid.UUID,
    query: str = "",
    memory_type: str | None = None,
    limit: int = 10,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询长期关系记忆。"""
    from app.services.relationship_memory import recall_memories, list_all_memories

    await validate_pair_access(pair_id, user, db, require_active=True)

    if query:
        types = [memory_type] if memory_type else None
        results = await recall_memories(
            db, pair_id=pair_id, user_id=user.id,
            query=query, memory_types=types, limit=limit,
        )
    else:
        results = await list_all_memories(
            db, pair_id=pair_id, user_id=user.id, limit=limit,
        )

    return {"memories": results, "total": len(results)}


@router.get("/companion-styles")
async def get_companion_styles(
    pair_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """返回亲健 4 种陪聊风格、3 档表达力度及当前账号/关系生效的配置。"""
    from app.services.companion_style import (
        list_companion_styles,
        list_expression_intensities,
        resolve_companion_context,
    )

    pair = None
    if pair_id is not None:
        pair = await validate_pair_access(pair_id, user, db, require_active=True)
    ctx = resolve_companion_context(user, pair=pair, pair_id=pair_id)
    prefs = normalize_product_prefs(user.product_prefs)
    return {
        "styles": list_companion_styles(),
        "default_style": ctx["requested_style_key"] if pair_id is None else prefs.get("tone_preference", "gentle"),
        "active_style": ctx["style_key"],
        "pair_tone_preferences": dict(prefs.get("pair_tone_preferences") or {}),
        "intensities": list_expression_intensities(),
        "default_intensity": prefs.get("expression_intensity", "balanced"),
        "active_intensity": ctx["intensity_key"],
    }


@router.get("/style-profile")
async def get_style_profile(user: User = Depends(get_current_user)) -> dict[str, Any]:
    """当前用户的说话方式档位。只有风格偏好会进这里，当轮情绪不进。"""
    prefs = normalize_product_prefs(user.product_prefs)
    profile = tone_read_profile(prefs.get("tone_profile"))
    return {"profile": profile, "guide": tone_guide_text(profile), "is_default": tone_is_default(profile)}


@router.post("/style-feedback")
async def submit_style_feedback(
    payload: StyleFeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """记一条语气反馈。单次点击不改档位，同一方向攒够三条且满七天才会挪一格。"""
    prefs = normalize_product_prefs(user.product_prefs)
    profile, result = tone_record_signal(prefs.get("tone_profile"), verdict=payload.verdict, note=payload.note)
    merged = dict(user.product_prefs or {})
    merged["tone_profile"] = profile
    user.product_prefs = normalize_product_prefs(merged)
    await db.commit()
    return {"profile": profile, "guide": tone_guide_text(profile), "result": result}


@router.post("/style-profile/reset")
async def reset_style_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """一键回到默认语气，留着历史以便事后查。"""
    merged = dict(user.product_prefs or {})
    profile = tone_reset_profile(merged.get("tone_profile"))
    merged["tone_profile"] = profile
    user.product_prefs = normalize_product_prefs(merged)
    await db.commit()
    return {"profile": profile, "guide": tone_guide_text(profile), "result": {"changed": True, "reason": "已回到默认语气。"}}
