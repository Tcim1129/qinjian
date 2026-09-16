"""依恋模式分析模块 - 基于打卡数据识别依恋类型"""

import json
from app.ai import chat_completion
from app.ai.policy import compose_relationship_system_prompt
from app.core.config import settings


ATTACHMENT_ANALYSIS_PROMPT = """你是一位精通鲍尔比依恋理论的心理学专家。请根据以下用户近期的打卡数据，分析其依恋类型。

依恋类型定义：
- secure（安全型）：情绪稳定，信任伴侣，主动沟通，能平衡亲密与独立
- anxious（焦虑型）：担心被抛弃，需要频繁确认，情绪波动大，过度关注对方动态
- avoidant（回避型）：回避亲密，强调独立，情感表达少，倾向冷处理冲突
- fearful（恐惧型）：既渴望亲密又害怕受伤，情绪矛盾，行为反复

分析数据：
- 情绪评分分布：{mood_scores}
- 互动主动性：{initiative_pattern}（me=主动, partner=被动, equal=平衡）
- 深度对话频率：{deep_conv_rate}%
- 互动频率均值：{avg_interaction}
- 打卡内容关键词摘要：{content_summary}

请以 JSON 格式输出（不要包含其他内容）：
{{
    "primary_type": "secure/anxious/avoidant/fearful",
    "confidence": 0.0-1.0,
    "secondary_traits": ["次要特征1", "次要特征2"],
    "analysis": "依恋类型分析说明（80字内）",
    "growth_suggestion": "基于依恋类型的成长建议（60字内）"
}}"""


COMBINATION_TASK_PROMPT = """你是亲密关系改善专家。以下是一对{pair_type}双方的依恋类型组合：

A方依恋类型：{type_a}
B方依恋类型：{type_b}

请根据这个依恋类型组合，推荐3个今日关系改善任务。任务要求：
- 针对这种组合的常见摩擦点
- 具体可执行（30字内每个）
- 温和不说教

请以 JSON 格式输出（不要包含其他内容）：
{{
    "combination_insight": "这种组合的关系特点（50字内）",
    "tasks": [
        {{"title": "任务标题", "description": "具体描述", "target": "a/b/both", "category": "communication/activity/reflection"}},
        {{"title": "任务标题", "description": "具体描述", "target": "a/b/both", "category": "communication/activity/reflection"}},
        {{"title": "任务标题", "description": "具体描述", "target": "a/b/both", "category": "communication/activity/reflection"}}
    ]
}}"""


def _parse_json(text: str, fallback: dict) -> dict:
    """解析 AI JSON 输出"""
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        fallback["raw_response"] = text
        return fallback


async def analyze_attachment_style(
    mood_scores: list[int],
    initiative_counts: dict[str, int],
    deep_conv_rate: float,
    avg_interaction: float,
    content_summary: str,
) -> dict:
    """基于打卡数据分析用户依恋类型"""
    # 构建主动性分布描述
    total = sum(initiative_counts.values()) or 1
    initiative_pattern = ", ".join(
        f"{k}={v}次({v*100//total}%)" for k, v in initiative_counts.items()
    )

    prompt = ATTACHMENT_ANALYSIS_PROMPT.format(
        mood_scores=str(mood_scores[-14:]),  # 最近14天
        initiative_pattern=initiative_pattern,
        deep_conv_rate=round(deep_conv_rate, 1),
        avg_interaction=round(avg_interaction, 1),
        content_summary=content_summary[:200],
    )
    messages = [
        {
            "role": "system",
            "content": compose_relationship_system_prompt(
                "你是依恋理论研究专家。严格以JSON格式输出分析结果。"
            ),
        },
        {"role": "user", "content": prompt},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.4)
    return _parse_json(result, {
        "primary_type": "secure",
        "confidence": 0.5,
        "analysis": "数据不足，暂时识别为安全型",
        "growth_suggestion": "继续保持开放的沟通",
    })


async def generate_combination_tasks(
    pair_type: str, type_a: str, type_b: str
) -> dict:
    """根据双方依恋类型组合生成定制任务"""
    from app.ai.reporter import PAIR_TYPE_MAP

    prompt = COMBINATION_TASK_PROMPT.format(
        pair_type=PAIR_TYPE_MAP.get(pair_type, "伴侣"),
        type_a=type_a,
        type_b=type_b,
    )
    messages = [
        {
            "role": "system",
            "content": compose_relationship_system_prompt(
                "你是亲密关系改善专家。严格以JSON格式输出任务建议。"
            ),
        },
        {"role": "user", "content": prompt},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.7)
    return _parse_json(result, {
        "combination_insight": "保持开放沟通是所有关系的基石",
        "tasks": [
            {"title": "今日互动", "description": "花10分钟面对面交流今天的感受", "target": "both", "category": "communication"},
        ],
    })
