"""ASR provider layer for file transcription and realtime streaming."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
import uuid
import wave
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlencode, urlparse

from openai import AsyncOpenAI
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed

from app.core.config import settings


SYNC_TRANSCRIPTION_MAX_SECONDS = 5 * 60


@dataclass(slots=True)
class ASRTranscriptionResult:
    text: str
    provider: str
    model: str
    audio_info: dict[str, Any] | None = None


def _normalized_provider() -> str:
    provider = str(settings.ASR_PROVIDER or "qwen3").strip().lower()
    return provider or "qwen3"


def _normalized_realtime_provider(provider: str | None = None) -> str:
    value = str(
        provider
        or settings.REALTIME_ASR_PROVIDER
        or settings.ASR_PROVIDER
        or "qwen3"
    ).strip().lower()
    return value or "qwen3"


def _resolve_qwen_api_key() -> str:
    api_key = settings.QWEN_ASR_API_KEY or settings.AI_API_KEY
    if not api_key:
        raise RuntimeError("未配置语音转写密钥")
    return api_key


def _resolve_qwen_base_url() -> str:
    base_url = (settings.QWEN_ASR_BASE_URL or "").strip()
    if not base_url:
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    return base_url.rstrip("/")


def _resolve_qwen_realtime_ws_url() -> str:
    parsed = urlparse(_resolve_qwen_base_url())
    if not parsed.netloc:
        return "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
    return f"wss://{parsed.netloc}/api-ws/v1/realtime"


def _resolve_xfyun_app_id() -> str:
    value = str(settings.XFYUN_RTASR_APP_ID or "").strip()
    if not value:
        raise RuntimeError("未配置讯飞实时转写 APPID")
    return value


def _resolve_xfyun_api_key() -> str:
    value = str(settings.XFYUN_RTASR_API_KEY or "").strip()
    if not value:
        raise RuntimeError("未配置讯飞实时转写 APIKey")
    return value


def _resolve_xfyun_api_secret() -> str:
    value = str(settings.XFYUN_RTASR_API_SECRET or "").strip()
    if not value:
        raise RuntimeError("未配置讯飞实时转写 APISecret")
    return value


def _resolve_xfyun_ws_url() -> str:
    value = str(settings.XFYUN_RTASR_WS_URL or "").strip()
    if not value:
        value = "wss://office-api-ast-dx.iflyaisol.com/ast/communicate/v1"
    return value.rstrip("/")


def _resolve_xfyun_language(language: str | None = None) -> str:
    value = str(language or settings.XFYUN_RTASR_LANG or "autodialect").strip()
    if not value:
        return "autodialect"
    if value.lower() in {"zh", "zh-cn", "cn", "auto"}:
        return "autodialect"
    return value


def _resolve_xfyun_audio_encode(input_audio_format: str | None = None) -> str:
    value = str(input_audio_format or "pcm").strip().lower()
    if value == "opus":
        return "opus-wb"
    if value.startswith("speex"):
        return value
    return "pcm_s16le"


def _build_xfyun_signature(params: dict[str, str]) -> str:
    encoded_pairs = sorted(
        (quote(str(key), safe=""), quote(str(value), safe=""))
        for key, value in params.items()
        if value is not None and value != ""
    )
    base_string = "&".join(f"{key}={value}" for key, value in encoded_pairs)
    digest = hmac.new(
        _resolve_xfyun_api_secret().encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def _resolve_legacy_api_key() -> str:
    api_key = settings.AI_API_KEY or settings.SILICONFLOW_API_KEY
    if not api_key:
        raise RuntimeError("未配置语音转写网关密钥")
    return api_key


def _resolve_legacy_base_url() -> str | None:
    base_url = (settings.AI_BASE_URL or settings.SILICONFLOW_BASE_URL or "").strip()
    return base_url.rstrip("/") if base_url else None


def _resolve_openai_compatible_asr_model() -> str:
    model = str(getattr(settings, "OPENAI_COMPATIBLE_ASR_MODEL", "") or "").strip()
    return model or "whisper-1"


def _resolve_file_asr_model(provider: str | None = None) -> str:
    resolved_provider = str(provider or _normalized_provider()).strip().lower()
    if resolved_provider == "qwen3":
        return settings.QWEN_ASR_FILE_MODEL
    if resolved_provider in {"whisper", "openai", "openai-compatible"}:
        return _resolve_openai_compatible_asr_model()
    return ""


_qwen_chat_client: AsyncOpenAI | None = None
_legacy_audio_client: AsyncOpenAI | None = None


def _get_qwen_chat_client() -> AsyncOpenAI:
    global _qwen_chat_client
    if _qwen_chat_client is None:
        _qwen_chat_client = AsyncOpenAI(
            api_key=_resolve_qwen_api_key(),
            base_url=_resolve_qwen_base_url(),
            timeout=settings.AI_TIMEOUT_SECONDS,
        )
    return _qwen_chat_client


def _get_legacy_audio_client() -> AsyncOpenAI:
    global _legacy_audio_client
    if _legacy_audio_client is None:
        _legacy_audio_client = AsyncOpenAI(
            api_key=_resolve_legacy_api_key(),
            base_url=_resolve_legacy_base_url(),
            timeout=settings.AI_TIMEOUT_SECONDS,
        )
    return _legacy_audio_client


def _guess_media_type(file_path: str, content_type: str | None = None) -> str:
    if content_type:
        return content_type
    guessed, _ = mimetypes.guess_type(file_path)
    return guessed or "audio/mpeg"


def _read_audio_data_uri(file_path: str, content_type: str | None = None) -> str:
    media_type = _guess_media_type(file_path, content_type)
    with open(file_path, "rb") as audio_file:
        encoded = base64.b64encode(audio_file.read()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def _probe_duration_seconds_with_ffprobe(file_path: str) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    try:
        value = float((result.stdout or "").strip())
    except ValueError:
        return None
    return value if value > 0 else None


def _probe_duration_seconds_with_wave(file_path: str) -> float | None:
    try:
        with wave.open(file_path, "rb") as audio_file:
            frames = audio_file.getnframes()
            rate = audio_file.getframerate()
    except (wave.Error, OSError):
        return None
    if rate <= 0:
        return None
    return frames / rate


def _probe_duration_seconds(file_path: str) -> float | None:
    return _probe_duration_seconds_with_ffprobe(
        file_path
    ) or _probe_duration_seconds_with_wave(file_path)


def _validate_sync_transcription_constraints(file_path: str) -> None:
    file_size = os.path.getsize(file_path)
    if file_size <= 0:
        raise ValueError("音频文件为空")
    if file_size > settings.MAX_FILE_SIZE:
        raise ValueError(
            f"音频文件大小超过限制 ({settings.MAX_FILE_SIZE // 1024 // 1024}MB)"
        )

    duration_seconds = _probe_duration_seconds(file_path)
    if duration_seconds and duration_seconds > SYNC_TRANSCRIPTION_MAX_SECONDS:
        raise ValueError("同步转写仅支持 5 分钟以内的音频，请裁剪后重试")


def _extract_message_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text") or item.get("content")
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
        return "".join(chunks).strip()
    return str(content or "").strip()


def _extract_transcription_text(response: Any) -> str:
    if isinstance(response, str):
        return response.strip()
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text.strip()
    if isinstance(response, dict):
        text = response.get("text")
        if isinstance(text, str):
            return text.strip()
    return str(response or "").strip()


def _model_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        try:
            dumped = value.model_dump()
        except Exception:
            return {}
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _extract_audio_info(message: Any) -> dict[str, Any]:
    annotations = getattr(message, "annotations", None)
    if annotations is None and isinstance(message, dict):
        annotations = message.get("annotations")
    if not isinstance(annotations, list):
        return {}

    for item in annotations:
        payload = _model_to_dict(item)
        if payload.get("type") != "audio_info":
            continue
        return {
            key: payload[key]
            for key in ("type", "language", "emotion")
            if payload.get(key) is not None
        }
    return {}


async def _transcribe_with_qwen(
    file_path: str,
    *,
    content_type: str | None = None,
) -> ASRTranscriptionResult:
    _validate_sync_transcription_constraints(file_path)
    data_uri = _read_audio_data_uri(file_path, content_type)
    client = _get_qwen_chat_client()
    response = await client.chat.completions.create(
        model=settings.QWEN_ASR_FILE_MODEL,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": data_uri,
                        },
                    },
                ],
            }
        ],
        extra_body={
            "asr_options": {
                "language": "zh",
                "enable_itn": False,
            }
        },
    )
    message = response.choices[0].message
    text = _extract_message_text(message.content)
    audio_info = _extract_audio_info(message)
    return ASRTranscriptionResult(
        text=text,
        provider="qwen3",
        model=settings.QWEN_ASR_FILE_MODEL,
        audio_info=audio_info or None,
    )


async def _transcribe_with_legacy_whisper(file_path: str) -> ASRTranscriptionResult:
    client = _get_legacy_audio_client()
    model = _resolve_openai_compatible_asr_model()
    with open(file_path, "rb") as audio_file:
        response = await client.audio.transcriptions.create(
            model=model, file=audio_file, language="zh", response_format="text"
        )
    return ASRTranscriptionResult(
        text=_extract_transcription_text(response),
        provider="openai-compatible",
        model=model,
    )


async def transcribe_file(
    file_path: str,
    *,
    content_type: str | None = None,
) -> ASRTranscriptionResult:
    provider = _normalized_provider()
    if provider == "qwen3":
        return await _transcribe_with_qwen(file_path, content_type=content_type)
    if provider in {"whisper", "openai", "openai-compatible"}:
        return await _transcribe_with_legacy_whisper(file_path)
    raise RuntimeError("不支持的语音转写服务配置")


class QwenRealtimeASRClient:
    """Thin relay client for DashScope realtime ASR."""

    def __init__(
        self,
        *,
        model: str | None = None,
        language: str = "zh",
        sample_rate: int = 16000,
        input_audio_format: str = "pcm",
    ) -> None:
        self.model = model or settings.QWEN_ASR_REALTIME_MODEL
        self.language = language or "zh"
        self.sample_rate = int(sample_rate or 16000)
        self.input_audio_format = str(input_audio_format or "pcm").strip().lower()
        self._ws = None

    async def connect(self) -> None:
        if self._ws is not None:
            return
        url = f"{_resolve_qwen_realtime_ws_url()}?model={quote(self.model)}"
        self._ws = await ws_connect(
            url,
            additional_headers={
                "Authorization": f"Bearer {_resolve_qwen_api_key()}",
                "OpenAI-Beta": "realtime=v1",
            },
            open_timeout=settings.AI_TIMEOUT_SECONDS,
            close_timeout=5,
            max_size=None,
        )

    async def start_session(self) -> None:
        await self._send_event(
            {
                "type": "session.update",
                "session": {
                    "modalities": ["text"],
                    "input_audio_format": self.input_audio_format,
                    "sample_rate": self.sample_rate,
                    "input_audio_transcription": {
                        "language": self.language,
                    },
                    "turn_detection": None,
                },
            }
        )

    async def send_audio_chunk(self, audio_base64: str) -> None:
        await self._send_event(
            {
                "type": "input_audio_buffer.append",
                "audio": audio_base64,
            }
        )

    async def stop_session(self) -> None:
        await self._send_event({"type": "input_audio_buffer.commit"})
        await self._send_event({"type": "session.finish"})

    async def recv_event(self) -> dict:
        if self._ws is None:
            raise RuntimeError("realtime ASR websocket 尚未连接")
        raw = await self._ws.recv()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    async def close(self) -> None:
        if self._ws is None:
            return
        try:
            await self._ws.close()
        except ConnectionClosed:
            pass
        finally:
            self._ws = None

    async def _send_event(self, payload: dict) -> None:
        if self._ws is None:
            raise RuntimeError("realtime ASR websocket 尚未连接")
        if "event_id" not in payload:
            payload = {"event_id": f"evt_{uuid.uuid4().hex}", **payload}
        await self._ws.send(json.dumps(payload, ensure_ascii=False))


class BatchRealtimeASRClient:
    """Record browser PCM chunks and transcribe them with the configured file ASR."""

    def __init__(
        self,
        *,
        model: str | None = None,
        language: str = "zh",
        sample_rate: int = 16000,
        input_audio_format: str = "pcm",
    ) -> None:
        del language
        self.sample_rate = int(sample_rate or 16000)
        self.input_audio_format = str(input_audio_format or "pcm").strip().lower()
        self.provider = _normalized_provider()
        self.model = model or _resolve_file_asr_model(self.provider)
        self._audio_chunks: list[bytes] = []
        self._pending_events: list[dict] = []
        self._event = asyncio.Event()
        self._closed = False

    async def connect(self) -> None:
        return None

    async def start_session(self) -> None:
        self._audio_chunks = []
        self._pending_events = []
        self._event.clear()
        self._closed = False

    async def send_audio_chunk(self, audio_base64: str) -> None:
        if self._closed:
            raise RuntimeError("批量语音会话已关闭")
        try:
            audio_bytes = base64.b64decode(audio_base64)
        except (ValueError, TypeError) as exc:
            raise RuntimeError("音频片段格式无效") from exc
        if audio_bytes:
            self._audio_chunks.append(audio_bytes)

    async def stop_session(self) -> None:
        if self._closed:
            return
        self._closed = True
        if not self._audio_chunks:
            self._enqueue(
                {
                    "type": "error",
                    "code": "empty_audio",
                    "message": "没有收到可转写的录音内容",
                }
            )
            return

        temp_path = ""
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_path = temp_file.name
            temp_file.close()
            with wave.open(temp_path, "wb") as audio_file:
                audio_file.setnchannels(1)
                audio_file.setsampwidth(2)
                audio_file.setframerate(self.sample_rate)
                audio_file.writeframes(b"".join(self._audio_chunks))

            transcription = await transcribe_file(temp_path, content_type="audio/wav")
            audio_info = dict(transcription.audio_info or {})
            text = str(transcription.text or "").strip()
            if text:
                self._enqueue(
                    {
                        "type": "conversation.item.input_audio_transcription.completed",
                        "transcript": text,
                        "audio_info": audio_info or None,
                    }
                )
            self._enqueue(
                {
                    "type": "session.finished",
                    "transcript": text,
                    "audio_info": audio_info or None,
                }
            )
        except Exception as exc:
            self._enqueue(
                {
                    "type": "error",
                    "code": "batch_provider_error",
                    "message": str(exc) or "录音转写失败，请稍后重试",
                }
            )
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    async def recv_event(self) -> dict:
        while not self._pending_events:
            self._event.clear()
            await self._event.wait()
        return self._pending_events.pop(0)

    async def close(self) -> None:
        self._closed = True
        self._event.set()

    def _enqueue(self, payload: dict) -> None:
        self._pending_events.append(payload)
        self._event.set()


class XFYunRealtimeASRClient:
    """讯飞实时语音转写 WebSocket 客户端。"""

    def __init__(
        self,
        *,
        model: str | None = None,
        language: str = "zh",
        sample_rate: int = 16000,
        input_audio_format: str = "pcm",
    ) -> None:
        del model
        self.language = _resolve_xfyun_language(language)
        self.sample_rate = int(sample_rate or 16000)
        self.input_audio_format = str(input_audio_format or "pcm").strip().lower()
        self.audio_encode = _resolve_xfyun_audio_encode(self.input_audio_format)
        self.request_uuid = str(uuid.uuid4())
        self.session_id = ""
        self._ws = None
        self._pending_events: list[dict] = []

    async def connect(self) -> None:
        if self._ws is not None:
            return
        utc_now = datetime.now(timezone(timedelta(hours=8))).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )
        params = {
            "accessKeyId": _resolve_xfyun_api_key(),
            "appId": _resolve_xfyun_app_id(),
            "uuid": self.request_uuid,
            "utc": utc_now,
            "audio_encode": self.audio_encode,
            "lang": self.language,
            "samplerate": str(self.sample_rate),
        }
        query = urlencode(
            {**params, "signature": _build_xfyun_signature(params)},
            quote_via=quote,
        )
        self._ws = await ws_connect(
            f"{_resolve_xfyun_ws_url()}?{query}",
            open_timeout=settings.AI_TIMEOUT_SECONDS,
            close_timeout=5,
            max_size=None,
        )

    async def start_session(self) -> None:
        return None

    async def send_audio_chunk(self, audio_base64: str) -> None:
        if self._ws is None:
            raise RuntimeError("讯飞 realtime websocket 尚未连接")
        audio_bytes = base64.b64decode(audio_base64)
        chunk_size = 1280 if self.audio_encode == "pcm_s16le" else len(audio_bytes)
        for index in range(0, len(audio_bytes), chunk_size):
            await self._ws.send(audio_bytes[index:index + chunk_size])
            if index + chunk_size < len(audio_bytes):
                await asyncio.sleep(0.04)

    async def stop_session(self) -> None:
        if self._ws is None:
            raise RuntimeError("讯飞 realtime websocket 尚未连接")
        session_id = self.session_id or self.request_uuid
        await self._ws.send(
            json.dumps({"end": True, "sessionId": session_id}, ensure_ascii=False)
        )

    async def recv_event(self) -> dict:
        if self._pending_events:
            return self._pending_events.pop(0)
        if self._ws is None:
            raise RuntimeError("讯飞 realtime websocket 尚未连接")
        raw = await self._ws.recv()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        event = self._normalize_event(json.loads(raw))
        if event is None:
            return await self.recv_event()
        return event

    async def close(self) -> None:
        if self._ws is None:
            return
        try:
            await self._ws.close()
        except ConnectionClosed:
            pass
        finally:
            self._ws = None

    def _normalize_event(self, payload: dict) -> dict | None:
        msg_type = str(payload.get("msg_type") or "").strip().lower()
        payload_data = payload.get("data") or {}
        action = str(
            payload.get("action")
            or (payload_data.get("action") if isinstance(payload_data, dict) else "")
        ).strip().lower()
        code = str(payload.get("code") or "0").strip()
        if msg_type == "action" and action == "started":
            if isinstance(payload_data, dict):
                self.session_id = str(payload_data.get("sessionId") or self.session_id)
            return {
                "type": "session.created",
                "sid": self.session_id or payload.get("sid"),
            }
        if action == "error":
            return {
                "type": "error",
                "code": code or "provider_error",
                "message": str(payload.get("desc") or "讯飞实时识别失败"),
            }

        data = payload_data if isinstance(payload_data, dict) else {}
        if isinstance(data, dict) and data.get("normal") is False:
            return {
                "type": "error",
                "code": code or "provider_error",
                "message": str(data.get("desc") or payload.get("desc") or "讯飞实时识别失败"),
            }

        text = self._extract_text(data)
        is_final = bool(data.get("ls"))
        segment_id = data.get("seg_id")
        if text and is_final:
            self._pending_events.append(
                {
                    "type": "session.finished",
                    "transcript": text,
                    "segment_id": segment_id,
                }
            )
            return {
                "type": "conversation.item.input_audio_transcription.completed",
                "text": text,
                "transcript": text,
                "segment_id": segment_id,
            }
        if text:
            return {
                "type": "conversation.item.input_audio_transcription.text",
                "text": text,
                "transcript": text,
                "segment_id": segment_id,
            }
        if is_final:
            return {"type": "session.finished", "transcript": "", "segment_id": segment_id}
        return None

    @staticmethod
    def _extract_text(data: dict) -> str:
        cn = data.get("cn") or {}
        st = cn.get("st") or {}
        rt = st.get("rt") or []
        parts: list[str] = []
        for rt_item in rt:
            for ws_item in rt_item.get("ws") or []:
                for cw_item in ws_item.get("cw") or []:
                    word = cw_item.get("w")
                    if isinstance(word, str) and word:
                        parts.append(word)
        return "".join(parts).strip()


def create_realtime_asr_client(
    *,
    provider: str | None = None,
    model: str | None = None,
    language: str = "zh",
    sample_rate: int = 16000,
    input_audio_format: str = "pcm",
):
    resolved_provider = _normalized_realtime_provider(provider)
    if resolved_provider in {"batch", "file", "sync", "whisper", "openai", "openai-compatible"}:
        return BatchRealtimeASRClient(
            model=model,
            language=language,
            sample_rate=sample_rate,
            input_audio_format=input_audio_format,
        )
    if resolved_provider in {"xfyun", "iflytek"}:
        return XFYunRealtimeASRClient(
            language=language,
            sample_rate=sample_rate,
            input_audio_format=input_audio_format,
        )
    if resolved_provider == "qwen3":
        return QwenRealtimeASRClient(
            model=model,
            language=language,
            sample_rate=sample_rate,
            input_audio_format=input_audio_format,
        )
    raise RuntimeError("不支持的实时语音转写服务配置")
