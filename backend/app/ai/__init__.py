"""AI 模块 - 通用 OpenAI 兼容客户端"""

import json
from openai import AsyncOpenAI
from app.core.config import settings


def _resolve_api_key() -> str:
    return settings.AI_API_KEY or settings.SILICONFLOW_API_KEY


def _resolve_base_url() -> str | None:
    base_url = settings.AI_BASE_URL or settings.SILICONFLOW_BASE_URL
    base_url = (base_url or "").strip()
    return base_url.rstrip("/") if base_url else None


client = AsyncOpenAI(
    api_key=_resolve_api_key(),
    base_url=_resolve_base_url(),
    timeout=settings.AI_TIMEOUT_SECONDS,
)


async def chat_completion(
    model: str, messages: list[dict], temperature: float = 0.7
) -> str:
    """通用聊天接口"""
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content


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
