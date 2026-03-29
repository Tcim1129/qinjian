"""Realtime ASR websocket bridge for agent voice input."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.ai.asr import create_realtime_asr_client
from app.core.database import async_session
from app.core.security import decode_realtime_ws_ticket
from app.services.interaction_events import record_user_interaction_event

router = APIRouter(prefix="/agent", tags=["智能陪伴"])
logger = logging.getLogger(__name__)

PARTIAL_EVENT_TYPES = {
    "conversation.item.input_audio_transcription.text",
    "response.audio_transcript.delta",
    "transcript.partial",
    "partial",
}
FINAL_EVENT_TYPES = {
    "conversation.item.input_audio_transcription.completed",
    "response.audio_transcript.done",
    "session.finished",
    "transcript.final",
    "final",
}


def _extract_event_text(payload: dict) -> str:
    for key in ("text", "transcript", "delta"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


async def _record_voice_event(
    user_id: str,
    *,
    event_type: str,
    session_id: str | None = None,
    pair_id: str | None = None,
    page: str | None = None,
    payload: dict | None = None,
) -> None:
    try:
        async with async_session() as db:
            await record_user_interaction_event(
                db,
                user_id=user_id,
                pair_id=pair_id,
                session_id=session_id,
                source="voice",
                event_type=event_type,
                page=page,
                path="/api/v1/agent/asr/realtime",
                payload=payload,
            )
            await db.commit()
    except Exception:
        logger.exception("failed to record voice interaction event")


async def _relay_asr_events(
    websocket: WebSocket,
    asr_client,
    *,
    user_id: str,
    voice_context: dict,
) -> None:
    while True:
        event = await asr_client.recv_event()
        event_type = str(event.get("type") or "").strip().lower()
        if not event_type:
            continue

        if event_type in PARTIAL_EVENT_TYPES:
            await websocket.send_json({"type": "partial", "text": _extract_event_text(event)})
            continue

        if event_type in FINAL_EVENT_TYPES:
            final_text = _extract_event_text(event)
            await websocket.send_json({"type": "final", "text": final_text})
            await _record_voice_event(
                user_id,
                event_type="voice.transcription.completed",
                session_id=voice_context.get("session_id"),
                pair_id=voice_context.get("pair_id"),
                page=voice_context.get("page"),
                payload={"transcript_chars": len(final_text or "")},
            )
            return

        if event_type == "error":
            await _record_voice_event(
                user_id,
                event_type="voice.transcription.failed",
                session_id=voice_context.get("session_id"),
                pair_id=voice_context.get("pair_id"),
                page=voice_context.get("page"),
                payload={"message": str(event.get("message") or "实时识别失败")},
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "message": str(event.get("message") or "实时识别失败"),
                }
            )
            return


@router.websocket("/asr/realtime")
async def agent_realtime_asr(websocket: WebSocket):
    ticket = str(websocket.query_params.get("ticket") or "").strip()
    user_id = decode_realtime_ws_ticket(ticket)
    if not user_id:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="invalid realtime asr ticket",
        )
        return

    await websocket.accept()

    asr_client = None
    relay_task: asyncio.Task | None = None
    voice_context = {
        "session_id": None,
        "pair_id": None,
        "page": "checkin",
        "provider": None,
        "model": None,
        "language": "zh",
    }

    try:
        while True:
            payload = await websocket.receive_json()
            message_type = str(payload.get("type") or "").strip().lower()

            if message_type == "session.start":
                if asr_client is not None:
                    await websocket.send_json({"type": "error", "message": "语音会话已经开始"})
                    continue

                try:
                    voice_context["session_id"] = str(payload.get("session_id") or "").strip() or None
                    voice_context["pair_id"] = str(payload.get("pair_id") or "").strip() or None
                    voice_context["page"] = str(payload.get("page") or "checkin").strip() or "checkin"
                    voice_context["provider"] = str(payload.get("provider") or "").strip() or None
                    voice_context["model"] = str(payload.get("model") or "").strip() or None
                    voice_context["language"] = str(payload.get("language") or "zh").strip() or "zh"
                    asr_client = create_realtime_asr_client(
                        provider=voice_context["provider"],
                        model=voice_context["model"],
                        language=voice_context["language"],
                        sample_rate=int(payload.get("sample_rate") or 16000),
                        input_audio_format=str(payload.get("format") or "pcm").strip() or "pcm",
                    )
                    await asr_client.connect()
                    await asr_client.start_session()
                    relay_task = asyncio.create_task(
                        _relay_asr_events(
                            websocket,
                            asr_client,
                            user_id=user_id,
                            voice_context=voice_context,
                        )
                    )
                    await _record_voice_event(
                        user_id,
                        event_type="voice.session.started",
                        session_id=voice_context["session_id"],
                        pair_id=voice_context["pair_id"],
                        page=voice_context["page"],
                        payload={
                            "provider": voice_context["provider"],
                            "model": voice_context["model"],
                            "language": voice_context["language"],
                            "sample_rate": int(payload.get("sample_rate") or 16000),
                            "format": str(payload.get("format") or "pcm").strip() or "pcm",
                        },
                    )
                except Exception:
                    logger.exception("failed to start realtime asr session for user %s", user_id)
                    await _record_voice_event(
                        user_id,
                        event_type="voice.session.start_failed",
                        session_id=voice_context["session_id"],
                        pair_id=voice_context["pair_id"],
                        page=voice_context["page"],
                        payload={
                            "provider": voice_context["provider"],
                            "model": voice_context["model"],
                        },
                    )
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "实时识别暂时不可用，请稍后重试",
                        }
                    )
                    break
                continue

            if message_type == "audio.chunk":
                if asr_client is None:
                    await websocket.send_json({"type": "error", "message": "语音会话尚未开始"})
                    continue
                audio = str(payload.get("audio") or "").strip()
                if audio:
                    await asr_client.send_audio_chunk(audio)
                continue

            if message_type == "session.stop":
                if asr_client is not None:
                    await asr_client.stop_session()
                    await _record_voice_event(
                        user_id,
                        event_type="voice.session.stop_requested",
                        session_id=voice_context["session_id"],
                        pair_id=voice_context["pair_id"],
                        page=voice_context["page"],
                    )
                continue

            await websocket.send_json({"type": "error", "message": "不支持的实时语音消息类型"})

    except WebSocketDisconnect:
        await _record_voice_event(
            user_id,
            event_type="voice.session.disconnected",
            session_id=voice_context["session_id"],
            pair_id=voice_context["pair_id"],
            page=voice_context["page"],
        )
        return
    except Exception:
        logger.exception("realtime asr websocket crashed for user %s", user_id)
        await _record_voice_event(
            user_id,
            event_type="voice.session.crashed",
            session_id=voice_context["session_id"],
            pair_id=voice_context["pair_id"],
            page=voice_context["page"],
        )
        with contextlib.suppress(Exception):
            await websocket.send_json(
                {"type": "error", "message": "实时语音连接已中断，请稍后重试"}
            )
    finally:
        if relay_task is not None:
            relay_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await relay_task
        if asr_client is not None:
            with contextlib.suppress(Exception):
                await asr_client.close()
