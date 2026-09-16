"""AI 模块 - 通用 OpenAI 兼容客户端"""

import json
import time
from openai import AsyncOpenAI
from app.ai.asr import ASRTranscriptionResult, transcribe_file
from app.core.config import settings
from app.models import User
from app.services.ai_context import (
    build_context_pack,
    format_context_pack_message,
    get_current_input_context,
)
from app.services.privacy_sandbox import redact_message_payload
from app.services.privacy_audit import (
    get_privacy_audit_context,
    log_privacy_ai_chat,
    log_privacy_transcription,
)


def _resolve_api_key() -> str:
    return settings.AI_API_KEY or settings.SILICONFLOW_API_KEY


def _resolve_base_url() -> str | None:
    base_url = settings.AI_BASE_URL or settings.SILICONFLOW_BASE_URL
    base_url = (base_url or "").strip()
    return base_url.rstrip("/") if base_url else None


def _resolve_provider_name() -> str:
    base_url = _resolve_base_url() or ""
    if "siliconflow" in base_url:
        return "siliconflow"
    if "openai" in base_url:
        return "openai-compatible"
    return "compatible-gateway"


def _resolve_fallback_model(model: str) -> str | None:
    if model == settings.AI_TEXT_MODEL:
        fallback = settings.AI_TEXT_FALLBACK_MODEL
    elif model == settings.AI_MULTIMODAL_MODEL:
        fallback = settings.AI_MULTIMODAL_FALLBACK_MODEL
    else:
        fallback = ""

    fallback = str(fallback or "").strip()
    return fallback if fallback and fallback != model else None


def _should_try_fallback(exc: Exception) -> bool:
    return getattr(exc, "status_code", None) != 400


client = AsyncOpenAI(
    api_key=_resolve_api_key(),
    base_url=_resolve_base_url(),
    timeout=settings.AI_TIMEOUT_SECONDS,
)


async def _release_read_only_transaction(db) -> None:
    """Avoid holding SQLite read locks while waiting on external AI calls."""
    if not db:
        return
    try:
        has_changes = bool(db.new or db.dirty or db.deleted)
        if db.in_transaction() and not has_changes:
            await db.commit()
    except Exception:
        return


async def chat_completion(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    **kwargs,
) -> str:
    """通用聊天接口"""
    response = await create_chat_completion(
        model=model,
        messages=messages,
        temperature=temperature,
        **kwargs,
    )
    return response.choices[0].message.content


async def create_chat_completion(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    **kwargs,
):
    """统一聊天出口，便于挂载隐私沙盒与后续审计。
    model 传 "default" 时解析为当前的 AI_TEXT_MODEL。
    """
    if not model or model == "default":
        model = settings.AI_TEXT_MODEL
    audit_context = get_privacy_audit_context()
    privacy_mode = await _resolve_privacy_mode(audit_context)
    proxy_strategy = "redact_only"
    context_pack = kwargs.pop("context_pack", None)
    context_enabled = kwargs.pop("context_enabled", True)
    current_input = kwargs.pop("current_input", None)
    session_id = kwargs.pop("session_id", None)
    # 这些是供上下文/审计使用的注入值，不属于 OpenAI 请求参数，必须弹出防止透传给网关。
    kwargs.pop("pair_id", None)
    kwargs.pop("user_id", None)
    kwargs.pop("db", None)
    if context_pack is None and context_enabled:
        db = audit_context.get("db")
        if db:
            try:
                user_id = audit_context.get("user_id")
                pair_id = audit_context.get("pair_id")
                if current_input is None:
                    current_input = get_current_input_context(messages)
                user = await db.get(User, user_id) if user_id else None
                context_pack = await build_context_pack(
                    db,
                    user=user,
                    pair_id=pair_id,
                    user_id=user_id,
                    session_id=session_id,
                    current_input=current_input,
                )
                await _release_read_only_transaction(db)
            except Exception:
                context_pack = None
    safe_messages = redact_message_payload(messages)
    if context_pack:
        safe_messages = [format_context_pack_message(context_pack), *safe_messages]
    started_at = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=safe_messages,
            temperature=temperature,
            **kwargs,
        )
    except Exception as exc:
        await _log_chat_call(
            audit_context,
            model=model,
            raw_messages=messages,
            redacted_messages=safe_messages,
            raw_output=str(exc),
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            status="error",
            error_code=exc.__class__.__name__,
            privacy_mode=privacy_mode,
            proxy_strategy=proxy_strategy,
            proxy_metrics={},
        )
        fallback_model = _resolve_fallback_model(model)
        if not fallback_model or not _should_try_fallback(exc):
            raise

        fallback_started_at = time.perf_counter()
        try:
            response = await client.chat.completions.create(
                model=fallback_model,
                messages=safe_messages,
                temperature=temperature,
                **kwargs,
            )
        except Exception as fallback_exc:
            await _log_chat_call(
                audit_context,
                model=fallback_model,
                raw_messages=messages,
                redacted_messages=safe_messages,
                raw_output=str(fallback_exc),
                latency_ms=int((time.perf_counter() - fallback_started_at) * 1000),
                status="error",
                error_code=fallback_exc.__class__.__name__,
                privacy_mode=privacy_mode,
                proxy_strategy=proxy_strategy,
                proxy_metrics={"fallback_from_model": model},
            )
            raise

        await _log_chat_call(
            audit_context,
            model=fallback_model,
            raw_messages=messages,
            redacted_messages=safe_messages,
            raw_output=_response_output_preview(response),
            latency_ms=int((time.perf_counter() - fallback_started_at) * 1000),
            status="completed",
            privacy_mode=privacy_mode,
            proxy_strategy=proxy_strategy,
            proxy_metrics={"fallback_from_model": model},
        )
        return response

    await _log_chat_call(
        audit_context,
        model=model,
        raw_messages=messages,
        redacted_messages=safe_messages,
        raw_output=_response_output_preview(response),
        latency_ms=int((time.perf_counter() - started_at) * 1000),
        status="completed",
        privacy_mode=privacy_mode,
        proxy_strategy=proxy_strategy,
        proxy_metrics={},
    )
    return response


def _response_output_preview(response) -> str | None:
    if getattr(response, "choices", None):
        message = response.choices[0].message
        if message.content:
            return message.content
        if hasattr(message, "model_dump"):
            return str(message.model_dump())
        return str(message)
    return None


async def _log_chat_call(
    audit_context: dict,
    *,
    model: str,
    raw_messages: list[dict],
    redacted_messages: list[dict],
    raw_output: str | None,
    latency_ms: int,
    status: str,
    privacy_mode: str,
    proxy_strategy: str,
    proxy_metrics: dict,
    error_code: str | None = None,
) -> None:
    await log_privacy_ai_chat(
        audit_context.get("db"),
        model=model,
        provider=_resolve_provider_name(),
        run_type=str(audit_context.get("run_type") or "chat_completion"),
        scope=str(audit_context.get("scope") or "solo"),
        user_id=audit_context.get("user_id"),
        pair_id=audit_context.get("pair_id"),
        raw_messages=raw_messages,
        redacted_messages=redacted_messages,
        raw_output=raw_output,
        latency_ms=latency_ms,
        status=status,
        error_code=error_code,
        privacy_mode=privacy_mode,
        proxy_strategy=proxy_strategy,
        proxy_metrics=proxy_metrics,
    )


async def _resolve_privacy_mode(audit_context: dict) -> str:
    _ = audit_context
    return "cloud"


async def analyze_sentiment(text: str) -> dict:
    """情感分析（使用DeepSeek，性价比高）"""
    messages = [
        {
            "role": "system",
            "content": '你是一个情感分析引擎。分析用户文本的情感倾向，返回JSON格式：{"sentiment": "positive/negative/neutral", "score": 0-10, "emotions": ["情绪标签"]}',
        },
        {"role": "user", "content": text},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.3)
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {"sentiment": "neutral", "score": 5, "emotions": []}


async def transcribe_audio_result(file_path: str) -> ASRTranscriptionResult:
    """语音转文字 - 统一 ASR Provider 入口，保留 provider 元数据。"""
    audit_context = get_privacy_audit_context()
    started_at = time.perf_counter()
    try:
        response = await transcribe_file(file_path)
    except Exception as exc:
        await log_privacy_transcription(
            audit_context.get("db"),
            scope=str(audit_context.get("scope") or "solo"),
            user_id=audit_context.get("user_id"),
            pair_id=audit_context.get("pair_id"),
            provider="qwen3"
            if settings.ASR_PROVIDER == "qwen3"
            else "openai-compatible",
            model=(
                settings.QWEN_ASR_FILE_MODEL
                if settings.ASR_PROVIDER == "qwen3"
                else "whisper-1"
            ),
            file_name=file_path,
            raw_output=str(exc),
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            status="error",
            error_code=exc.__class__.__name__,
        )
        raise

    await log_privacy_transcription(
        audit_context.get("db"),
        scope=str(audit_context.get("scope") or "solo"),
        user_id=audit_context.get("user_id"),
        pair_id=audit_context.get("pair_id"),
        provider=response.provider,
        model=response.model,
        file_name=file_path,
        raw_output=response.text,
        latency_ms=int((time.perf_counter() - started_at) * 1000),
        status="completed",
        audio_info=response.audio_info,
    )
    return response


async def transcribe_audio(file_path: str) -> str:
    """语音转文字 - 兼容旧调用方，仅返回文字。"""
    return (await transcribe_audio_result(file_path)).text
