"""Realtime ASR websocket bridge for agent voice input."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.ai.asr import create_realtime_asr_client
from app.core.security import decode_realtime_ws_ticket

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


async def _relay_asr_events(websocket: WebSocket, asr_client) -> None:
    while True:
        event = await asr_client.recv_event()
        event_type = str(event.get("type") or "").strip().lower()
        if not event_type:
            continue

        if event_type in PARTIAL_EVENT_TYPES:
            await websocket.send_json({"type": "partial", "text": _extract_event_text(event)})
            continue

        if event_type in FINAL_EVENT_TYPES:
            await websocket.send_json({"type": "final", "text": _extract_event_text(event)})
            return

        if event_type == "error":
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

    try:
        while True:
            payload = await websocket.receive_json()
            message_type = str(payload.get("type") or "").strip().lower()

            if message_type == "session.start":
                if asr_client is not None:
                    await websocket.send_json({"type": "error", "message": "语音会话已经开始"})
                    continue

                try:
                    asr_client = create_realtime_asr_client(
                        provider=str(payload.get("provider") or "").strip() or None,
                        model=str(payload.get("model") or "").strip() or None,
                        language=str(payload.get("language") or "zh").strip() or "zh",
                        sample_rate=int(payload.get("sample_rate") or 16000),
                        input_audio_format=str(payload.get("format") or "pcm").strip() or "pcm",
                    )
                    await asr_client.connect()
                    await asr_client.start_session()
                    relay_task = asyncio.create_task(_relay_asr_events(websocket, asr_client))
                except Exception:
                    logger.exception("failed to start realtime asr session for user %s", user_id)
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
                continue

            await websocket.send_json({"type": "error", "message": "不支持的实时语音消息类型"})

    except WebSocketDisconnect:
        return
    except Exception:
        logger.exception("realtime asr websocket crashed for user %s", user_id)
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
