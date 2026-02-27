"""AI 报告生成模块（Phase 3 增强：支持 Solo 个人日记 + 心理学量表背书）"""
import json
import base64
import os
from app.ai import chat_completion, client
from app.core.config import settings


# ── 专业心理学系统 Prompt ──

SYSTEM_PROMPT = """你是亲健平台的AI关系健康顾问，具备循证心理学专业背景。
你的分析框架基于以下权威理论：
- 约翰·戈特曼 (John Gottman) 的亲密关系理论，尤其是「末日四骑士」模型（批评、蔑视、防御、冷暴力）
- 鲍尔比 (Bowlby) 的依恋理论（安全型、焦虑型、回避型、混乱型）
- 积极心理学中的「5:1 积极互动比」原则

请严格按照JSON格式输出，不要包含其他文字。"""


# ── Prompt 模板 ──

DAILY_REPORT_PROMPT = """以下是一对{pair_type}今天的打卡记录。请基于戈特曼理论与依恋理论框架进行分析。

【A方视角】
{content_a}

【B方视角】
{content_b}

请从以下维度分析，并以 JSON 格式输出（不要包含其他内容）：
{{
    "mood_a": {{"score": 1-10, "label": "情绪描述"}},
    "mood_b": {{"score": 1-10, "label": "情绪描述"}},
    "communication_quality": {{"score": 1-10, "note": "沟通质量评价（参考5:1积极互动比）"}},
    "health_score": 1-100,
    "insight": "一句话洞察总结（30字内，语气温暖）",
    "suggestion": "一条可执行的改善建议（50字内）",
    "highlights": ["今日亮点1", "今日亮点2"],
    "concerns": ["潜在问题（如果有的话）"],
    "theory_tag": "本次分析主要参考的理论（如：戈特曼5:1积极互动比）",
    "risk_signals": ["检测到的关系风险信号（如有，参考末日四骑士模型）"]
}}"""

SOLO_REPORT_PROMPT = """以下是一位用户（处于{pair_type}关系中）今天的个人打卡记录。对方今日未打卡。
请基于依恋理论和积极心理学框架，为 TA 生成一份个人情感日记。

【个人视角】
{content}

请以 JSON 格式输出（不要包含其他内容）：
{{
    "mood": {{"score": 1-10, "label": "情绪描述"}},
    "health_score": 1-100,
    "self_insight": "对 TA 今天情感状态的洞察（60字内，温暖共情）",
    "emotional_pattern": "从依恋理论角度解读 TA 今日的情绪模式（50字内）",
    "self_care_tip": "一条个人情绪调节建议（50字内，具体可执行）",
    "relationship_note": "对关系的温柔提醒或鼓励（40字内，不要批评对方未打卡）",
    "theory_tag": "本次分析主要参考的理论"
}}"""

WEEKLY_REPORT_PROMPT = """以下是一对{pair_type}过去7天的打卡记录摘要。请基于戈特曼理论进行纵向趋势分析。

{daily_summaries}

请生成一份周报，JSON 格式输出：
{{
    "overall_health_score": 1-100,
    "trend": "improving/stable/declining",
    "trend_description": "本周关系趋势的详细描述（参考末日四骑士模型，100字内）",
    "mood_trend_a": {{"average": 1-10, "trend": "up/stable/down"}},
    "mood_trend_b": {{"average": 1-10, "trend": "up/stable/down"}},
    "communication_analysis": "沟通模式分析（参考5:1比，80字内）",
    "weekly_highlights": ["本周亮点1", "本周亮点2", "本周亮点3"],
    "areas_to_improve": ["改善方向1", "改善方向2"],
    "action_plan": ["具体行动建议1", "具体行动建议2", "具体行动建议3"],
    "encouragement": "一段温暖的鼓励话语（50字内）",
    "theory_tag": "本周分析主要参考的理论"
}}"""

MONTHLY_REPORT_PROMPT = """以下是一对{pair_type}过去30天的周报摘要。请基于依恋理论与戈特曼模型进行深度月度分析。

{weekly_summaries}

请生成一份月度深度报告，JSON 格式输出：
{{
    "overall_health_score": 1-100,
    "monthly_trend": "improving/stable/declining",
    "executive_summary": "月度关系总结（结合理论框架，150字内）",
    "emotional_patterns": {{
        "a_pattern": "A方情绪模式分析（参考依恋类型，80字内）",
        "b_pattern": "B方情绪模式分析（参考依恋类型，80字内）",
        "interaction_pattern": "互动模式分析（参考末日四骑士，80字内）"
    }},
    "strengths": ["关系优势1", "关系优势2"],
    "growth_areas": ["成长空间1", "成长空间2"],
    "monthly_milestones": ["里程碑1", "里程碑2"],
    "next_month_goals": ["下月目标1", "下月目标2"],
    "professional_note": "专业建议（如发现高风险信号，温和提醒是否需要寻求专业心理咨询）"
}}"""

PAIR_TYPE_MAP = {
    "couple": "情侣",
    "spouse": "夫妻",
    "bestfriend": "挚友",
}


def _parse_ai_json(text: str, fallback: dict) -> dict:
    """解析 AI 输出的 JSON，含降级处理"""
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        fallback["raw_response"] = text
        return fallback


async def generate_daily_report(pair_type: str, content_a: str, content_b: str) -> dict:
    """生成每日关系健康报告"""
    prompt = DAILY_REPORT_PROMPT.format(
        pair_type=PAIR_TYPE_MAP.get(pair_type, "伴侣"),
        content_a=content_a,
        content_b=content_b,
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.6)
    return _parse_ai_json(result, {
        "health_score": 50,
        "insight": "今日数据分析中，请稍后再试",
        "suggestion": "建议多进行面对面交流",
    })


async def generate_solo_report(pair_type: str, content: str) -> dict:
    """生成个人情感日记（单方打卡时使用）"""
    prompt = SOLO_REPORT_PROMPT.format(
        pair_type=PAIR_TYPE_MAP.get(pair_type, "伴侣"),
        content=content,
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.6)
    return _parse_ai_json(result, {
        "health_score": 50,
        "mood": {"score": 5, "label": "平稳"},
        "self_insight": "今日情感分析中，请稍后再试",
        "self_care_tip": "给自己一点安静的时间",
    })


async def generate_weekly_report(pair_type: str, daily_reports: list[dict]) -> dict:
    """生成周报（基于多日日报汇总）"""
    summaries = []
    for i, report in enumerate(daily_reports, 1):
        summaries.append(f"第{i}天: 健康度={report.get('health_score', '--')}, "
                        f"洞察={report.get('insight', '无')}")
    daily_summaries = "\n".join(summaries)

    prompt = WEEKLY_REPORT_PROMPT.format(
        pair_type=PAIR_TYPE_MAP.get(pair_type, "伴侣"),
        daily_summaries=daily_summaries,
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    result = await chat_completion(settings.AI_MULTIMODAL_MODEL, messages, temperature=0.5)
    return _parse_ai_json(result, {
        "overall_health_score": 50,
        "trend": "stable",
        "trend_description": "数据分析中",
        "encouragement": "每一天的记录都是在为这段关系积蓄能量 ❤️",
    })


async def generate_monthly_report(pair_type: str, weekly_reports: list[dict]) -> dict:
    """生成月报（基于周报汇总）"""
    summaries = []
    for i, report in enumerate(weekly_reports, 1):
        summaries.append(f"第{i}周: 健康度={report.get('overall_health_score', '--')}, "
                        f"趋势={report.get('trend', '--')}")
    weekly_summaries = "\n".join(summaries)

    prompt = MONTHLY_REPORT_PROMPT.format(
        pair_type=PAIR_TYPE_MAP.get(pair_type, "伴侣"),
        weekly_summaries=weekly_summaries,
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    result = await chat_completion(settings.AI_MULTIMODAL_MODEL, messages, temperature=0.5)
    return _parse_ai_json(result, {
        "overall_health_score": 50,
        "monthly_trend": "stable",
        "executive_summary": "月度数据分析中",
    })


async def analyze_image(image_path: str, context: str = "") -> dict:
    """多模态图片分析（用 Kimi K2.5 多模态模型）"""
    try:
        abs_path = os.path.join(settings.UPLOAD_DIR, image_path.lstrip("/uploads/"))
        with open(abs_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        ext = os.path.splitext(abs_path)[1].lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
        mime_type = mime_map.get(ext, "image/jpeg")

        messages = [
            {"role": "system", "content": "你是亲密关系分析师。分析图片中的情感线索和社交信号。"},
            {"role": "user", "content": [
                {"type": "text", "text": f"分析这张图片在亲密关系语境下的情感含义。{f'背景信息：{context}' if context else ''}\n\n请以JSON输出：{{\"mood\": \"情绪\", \"social_signal\": \"社交信号描述\", \"score\": 1-10}}"},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}},
            ]},
        ]

        response = await client.chat.completions.create(
            model=settings.AI_MULTIMODAL_MODEL,
            messages=messages,
            temperature=0.4,
        )
        return _parse_ai_json(response.choices[0].message.content, {
            "mood": "neutral",
            "social_signal": "无法分析",
            "score": 5,
        })
    except Exception as e:
        return {"mood": "unknown", "social_signal": str(e), "score": 5}
