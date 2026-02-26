"""AI 模块 - 硅基流动多模态客户端"""
import json
from openai import AsyncOpenAI
from app.core.config import settings

# 硅基流动兼容 OpenAI 格式
client = AsyncOpenAI(
    api_key=settings.SILICONFLOW_API_KEY,
    base_url=settings.SILICONFLOW_BASE_URL,
)


async def chat_completion(model: str, messages: list[dict], temperature: float = 0.7) -> str:
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
        {"role": "system", "content": "你是一个情感分析引擎。分析用户文本的情感倾向，返回JSON格式：{\"sentiment\": \"positive/negative/neutral\", \"score\": 0-10, \"emotions\": [\"情绪标签\"]}"},
        {"role": "user", "content": text},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.3)
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {"sentiment": "neutral", "score": 5, "emotions": []}
