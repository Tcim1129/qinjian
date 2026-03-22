"""Message simulation helpers for pre-send relationship coaching."""

import json

from app.ai import chat_completion
from app.core.config import settings


SIMULATION_SYSTEM_PROMPT = """你是亲密关系沟通教练。你的任务不是判断谁对谁错，而是帮助用户在发消息前，预演对方可能的感受、识别误读风险，并给出更安全但不失真诚的表达改写。

请结合提供的关系画像、风险状态和当前草稿，输出一个务实、克制、可执行的判断。不要用治疗式大段安慰，也不要夸张吓人。严格输出 JSON。"""


SIMULATION_PROMPT = """请根据以下关系上下文，预演这条消息可能带来的影响。

【关系上下文】
{context_json}

【用户准备发出的原话】
{draft}

请输出 JSON（不要包含其他文字）：
{{
  "partner_view": "对方最可能的第一感受或理解（40字内）",
  "likely_impact": "这条话发出去后，互动最可能出现的走向（50字内）",
  "risk_level": "low/medium/high",
  "risk_reason": "为什么存在这个风险（50字内）",
  "safer_rewrite": "在保留用户真实意思前提下，更安全、更容易被接住的改写版本（120字内）",
  "suggested_tone": "建议采用的语气，如温和/直接但不指责/先确认再表达需求",
  "conversation_goal": "这条消息真正更适合达成的目标（30字内）",
  "do_list": ["建议做法1", "建议做法2"],
  "avoid_list": ["避免做法1", "避免做法2"]
}}"""


def _parse_json(text: str, fallback: dict) -> dict:
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        fallback["raw_response"] = text
        return fallback


async def simulate_message_preview(draft: str, context: dict) -> dict:
    prompt = SIMULATION_PROMPT.format(
        context_json=json.dumps(context, ensure_ascii=False),
        draft=draft.strip(),
    )
    messages = [
        {"role": "system", "content": SIMULATION_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.4)
    return _parse_json(
        result,
        {
            "partner_view": "对方可能会先感受到压力或防御。",
            "likely_impact": "如果直接发出，容易让沟通先卡在情绪上。",
            "risk_level": "medium",
            "risk_reason": "表达里可能夹带了判断或压迫感。",
            "safer_rewrite": draft,
            "suggested_tone": "先确认感受，再表达需求",
            "conversation_goal": "先把误解降下来",
            "do_list": ["先说自己的感受", "把需求说具体"],
            "avoid_list": ["不要翻旧账", "不要用绝对化措辞"],
        },
    )
