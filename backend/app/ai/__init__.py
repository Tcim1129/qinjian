"""AI 模块 - 通用 OpenAI 兼容客户端"""

import json
import time
from openai import AsyncOpenAI
from app.ai.asr import transcribe_file
from app.core.config import settings
from app.models import User
from app.services.product_prefs import resolve_privacy_mode
from app.services.privacy_sandbox import redact_message_payload
from app.services.privacy_audit import (
    get_privacy_audit_context,
    log_privacy_ai_chat,
    log_privacy_transcription,
)
from app.services.privacy_text_proxy import proxy_message_payload, rehydrate_content


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


client = AsyncOpenAI(
    api_key=_resolve_api_key(),
    base_url=_resolve_base_url(),
    timeout=settings.AI_TIMEOUT_SECONDS,
)


async def chat_completion(
    model: str, messages: list[dict], temperature: float = 0.7
) -> str:
    """通用聊天接口"""
    response = await create_chat_completion(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content


async def create_chat_completion(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    **kwargs,
):
    """统一聊天出口，便于挂载隐私沙盒与后续审计。"""
    audit_context = get_privacy_audit_context()
    privacy_mode = await _resolve_privacy_mode(audit_context)
    proxy_bundle = None
    proxy_strategy = "redact_only"
    if privacy_mode == "local_first" and settings.PRIVACY_TEXT_PROXY_ENABLED:
        proxy_bundle = proxy_message_payload(messages)
        safe_messages = proxy_bundle.messages
        proxy_strategy = "local_text_proxy"
    else:
        safe_messages = redact_message_payload(messages)
    started_at = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=safe_messages,
            temperature=temperature,
            **kwargs,
        )
    except Exception as exc:
        await log_privacy_ai_chat(
            audit_context.get("db"),
            model=model,
            provider=_resolve_provider_name(),
            run_type=str(audit_context.get("run_type") or "chat_completion"),
            scope=str(audit_context.get("scope") or "solo"),
            user_id=audit_context.get("user_id"),
            pair_id=audit_context.get("pair_id"),
            raw_messages=messages,
            redacted_messages=safe_messages,
            raw_output=str(exc),
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            status="error",
            error_code=exc.__class__.__name__,
            privacy_mode=privacy_mode,
            proxy_strategy=proxy_strategy,
            proxy_metrics=proxy_bundle.metrics() if proxy_bundle else {},
        )
        raise

    output_preview = None
    if getattr(response, "choices", None):
        message = response.choices[0].message
        output_preview = message.content or str(message.model_dump())
        if proxy_bundle and proxy_bundle.placeholder_map:
            restored_output = rehydrate_content(output_preview, proxy_bundle.placeholder_map)
            output_preview = restored_output
            try:
                message.content = restored_output
            except Exception:
                pass

    await log_privacy_ai_chat(
        audit_context.get("db"),
        model=model,
        provider=_resolve_provider_name(),
        run_type=str(audit_context.get("run_type") or "chat_completion"),
        scope=str(audit_context.get("scope") or "solo"),
        user_id=audit_context.get("user_id"),
        pair_id=audit_context.get("pair_id"),
        raw_messages=messages,
        redacted_messages=safe_messages,
        raw_output=output_preview,
        latency_ms=int((time.perf_counter() - started_at) * 1000),
        status="completed",
        privacy_mode=privacy_mode,
        proxy_strategy=proxy_strategy,
        proxy_metrics=proxy_bundle.metrics() if proxy_bundle else {},
    )
    return response


async def _resolve_privacy_mode(audit_context: dict) -> str:
    explicit = str(audit_context.get("privacy_mode") or "").strip()
    if explicit in {"cloud", "local_first"}:
        return explicit

    db = audit_context.get("db")
    user_id = audit_context.get("user_id")
    if not db or user_id in (None, ""):
        return "cloud"

    try:
        user = await db.get(User, user_id)
    except Exception:
        return "cloud"
    if not user:
        return "cloud"
    return resolve_privacy_mode(getattr(user, "product_prefs", None))


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


async def transcribe_audio(file_path: str) -> str:
    """语音转文字 - 统一 ASR Provider 入口"""
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
            provider="qwen3" if settings.ASR_PROVIDER == "qwen3" else "openai-compatible",
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
    )
    return response.text
