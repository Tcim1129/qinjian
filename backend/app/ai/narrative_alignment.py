"""Dual-view narrative alignment helper."""

import json

from app.ai import chat_completion
from app.core.config import settings


ALIGNMENT_SYSTEM_PROMPT = """你是亲健平台的关系编辑台分析器。你的任务不是判断谁对谁错，而是把双方对同一天或同一阶段的描述，整理成“共同版本 + 错位点 + 对齐动作”。

请保持克制、具体、可执行，不要夸大风险，不要写成空泛鸡汤。严格输出 JSON。"""


ALIGNMENT_PROMPT = """请根据以下关系上下文与双方记录，生成一份“双视角叙事对齐”结果。

【关系上下文】
{context_json}

【A方记录】
{checkin_a_json}

【B方记录】
{checkin_b_json}

请输出 JSON（不要包含其他文字）：
{{
  "alignment_score": 0-100,
  "shared_story": "双方其实都在经历的共同版本（80字内）",
  "view_a_summary": "A方更在意或更容易卡住的点（60字内）",
  "view_b_summary": "B方更在意或更容易卡住的点（60字内）",
  "misread_risk": "最容易发生的误读或错位（60字内）",
  "divergence_points": ["分歧点1", "分歧点2", "分歧点3"],
  "bridge_actions": ["可以这样对齐1", "可以这样对齐2", "可以这样对齐3"],
  "suggested_opening": "一句更容易开启对齐的开场白（80字内）",
  "coach_note": "给双方的编辑部备注（60字内）"
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


async def generate_narrative_alignment(
    *,
    context: dict,
    checkin_a: dict,
    checkin_b: dict,
) -> dict:
    prompt = ALIGNMENT_PROMPT.format(
        context_json=json.dumps(context, ensure_ascii=False),
        checkin_a_json=json.dumps(checkin_a, ensure_ascii=False),
        checkin_b_json=json.dumps(checkin_b, ensure_ascii=False),
    )
    messages = [
        {"role": "system", "content": ALIGNMENT_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.35)
    return _parse_json(
        result,
        {
            "alignment_score": 61,
            "shared_story": "双方都在意这段关系，只是表达节奏和接收方式没有完全对上。",
            "view_a_summary": "A方更在意被及时回应和被认真接住。",
            "view_b_summary": "B方更在意先被理解，而不是立刻被要求调整。",
            "misread_risk": "一方在表达需求，另一方却先把它听成了指责或压力。",
            "divergence_points": [
                "对同一件事的情绪重量判断不一致",
                "一方想解决问题，另一方先需要被理解",
                "表达方式比真实意图更容易被看见",
            ],
            "bridge_actions": [
                "先分别确认感受，再谈谁该怎么做",
                "一轮沟通里只解决一个最核心的问题",
                "用复述确认双方理解的是不是同一件事",
            ],
            "suggested_opening": "我想先对齐一下我们今天各自怎么理解这件事，不急着分对错。",
            "coach_note": "先把彼此的版本讲清楚，修复往往就已经开始了。",
        },
    )
