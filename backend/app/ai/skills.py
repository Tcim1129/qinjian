"""Skill 实现集合。

每个 Skill 调用模型完成一项分析，以 JSON 返回结果，由调度模块汇总；
依赖关系与执行顺序由 skill_registry 声明和解析。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.ai import chat_completion
from app.ai.policy import compose_relationship_system_prompt
from app.ai.skill_registry import SkillOutput, register_skill, SkillDefinition
from app.core.config import settings

logger = logging.getLogger(__name__)


def parse_json_safe(text: str) -> dict[str, Any]:
    """安全解析 LLM 返回的 JSON，兼容 markdown 代码块。"""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        result = json.loads(cleaned)
        return result if isinstance(result, dict) else {"raw": cleaned}
    except (json.JSONDecodeError, IndexError):
        return {"raw_text": cleaned}


_parse_json_safe = parse_json_safe


def _get_user_input(context: dict[str, Any]) -> str:
    return str(context.get("user_input", "")).strip()


def _get_previous_data(
    previous_results: dict[str, SkillOutput], skill_name: str
) -> dict[str, Any]:
    output = previous_results.get(skill_name)
    if output and output.success:
        return output.data
    return {}


EXPRESSION_CLARIFY_PROMPT = compose_relationship_system_prompt(
    """你是亲健平台的「表达澄清」分析模块。你的任务是从用户描述的关系事件中，提取结构化信息。

请根据用户输入，提取以下信息并输出 JSON（不要包含其他文字）：
{
  "people": [{"name": "称呼", "role": "关系角色（如伴侣/朋友/父母）", "emotion": "当前情绪状态"}],
  "events": [{"description": "事件描述（40字内）", "time": "发生时间（如有）", "importance": "high/medium/low"}],
  "user_emotion": "用户当前情绪（如委屈、愤怒、焦虑、纠结）",
  "core_need": "用户真正需要的是什么（40字内）",
  "unsaid": "用户可能没说出口但真正想表达的（40字内）",
  "context_gaps": ["还需要了解的信息1", "还需要了解的信息2"]
}"""
)


async def _expression_clarify(
    *, context: dict[str, Any], previous_results: dict[str, SkillOutput]
) -> dict[str, Any]:
    user_input = _get_user_input(context)
    messages = [
        {"role": "system", "content": EXPRESSION_CLARIFY_PROMPT},
        {"role": "user", "content": f"请分析以下关系事件：\n\n{user_input}"},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.3)
    return parse_json_safe(result)


register_skill(SkillDefinition(
    name="expression_clarify",
    label="表达澄清",
    description="从用户描述中提取关键人物、事件时间线、情绪状态和真实诉求",
    handler=_expression_clarify,
    depends_on=[],
    max_timeout=15.0,
))


STANCE_ANALYSIS_PROMPT = compose_relationship_system_prompt(
    """你是亲健平台的「立场分析」模块。根据已有的表达澄清结果，分析各方立场。

请输出 JSON（不要包含其他文字）：
{
  "stances": [
    {
      "person": "人物称呼",
      "position": "当前立场/态度（40字内）",
      "underlying_need": "底层需求（30字内）",
      "worry": "最担心的事（30字内）",
      "flexibility": "high/medium/low（妥协空间）"
    }
  ],
  "common_ground": "双方的共同点或共识（40字内）",
  "core_tension": "核心张力/矛盾点（40字内）",
  "power_dynamic": "关系中的权力/主导动态（30字内）"
}"""
)


async def _stance_analysis(
    *, context: dict[str, Any], previous_results: dict[str, SkillOutput]
) -> dict[str, Any]:
    user_input = _get_user_input(context)
    clarify_data = _get_previous_data(previous_results, "expression_clarify")

    messages = [
        {"role": "system", "content": STANCE_ANALYSIS_PROMPT},
        {"role": "user", "content": (
            f"用户描述：\n{user_input}\n\n"
            f"表达澄清结果：\n{json.dumps(clarify_data, ensure_ascii=False)}"
        )},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.3)
    return parse_json_safe(result)


register_skill(SkillDefinition(
    name="stance_analysis",
    label="立场分析",
    description="识别各方立场、底层需求、担忧和妥协空间",
    handler=_stance_analysis,
    depends_on=["expression_clarify"],
    max_timeout=15.0,
))


CONFLICT_DETECT_PROMPT = compose_relationship_system_prompt(
    """你是亲健平台的「冲突识别」模块。根据表达澄清和立场分析结果，判断冲突状况。

请输出 JSON（不要包含其他文字）：
{
  "has_conflict": true/false,
  "conflict_type": "价值观冲突/利益冲突/沟通误解/期望落差/边界侵犯/情绪积累",
  "severity": "low/medium/high",
  "severity_reason": "判断依据（40字内）",
  "core_contradiction": "核心矛盾（40字内）",
  "escalation_risk": "升级风险（low/medium/high）",
  "misunderstandings": ["容易发生的误读1", "容易发生的误读2"],
  "priority_issue": "当前最需要先处理的问题（40字内）"
}"""
)


async def _conflict_detect(
    *, context: dict[str, Any], previous_results: dict[str, SkillOutput]
) -> dict[str, Any]:
    user_input = _get_user_input(context)
    clarify_data = _get_previous_data(previous_results, "expression_clarify")
    stance_data = _get_previous_data(previous_results, "stance_analysis")

    messages = [
        {"role": "system", "content": CONFLICT_DETECT_PROMPT},
        {"role": "user", "content": (
            f"用户描述：\n{user_input}\n\n"
            f"表达澄清：\n{json.dumps(clarify_data, ensure_ascii=False)}\n\n"
            f"立场分析：\n{json.dumps(stance_data, ensure_ascii=False)}"
        )},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.3)
    return parse_json_safe(result)


register_skill(SkillDefinition(
    name="conflict_detect",
    label="冲突识别",
    description="判断冲突类型、严重程度、核心矛盾和升级风险",
    handler=_conflict_detect,
    depends_on=["stance_analysis"],
    max_timeout=15.0,
))


ACTION_PLAN_PROMPT = compose_relationship_system_prompt(
    """你是亲健平台的「行动规划」模块。根据前面的分析结果，生成 2-3 个可选行动方案。

每个方案要具体、可执行、有温度。请输出 JSON（不要包含其他文字）：
{
  "proposals": [
    {
      "id": "A",
      "title": "方案标题（15字内）",
      "description": "具体做什么（80字内）",
      "approach": "direct/gentle/gradual（直接/温和/渐进）",
      "pros": ["优点1", "优点2"],
      "cons": ["风险1"],
      "effort": "low/medium/high（执行难度）",
      "recommended": true/false
    }
  ],
  "suggestion": "综合建议（60字内）",
  "timing": "建议行动时机（30字内）"
}"""
)


async def _action_plan(
    *, context: dict[str, Any], previous_results: dict[str, SkillOutput]
) -> dict[str, Any]:
    user_input = _get_user_input(context)
    clarify_data = _get_previous_data(previous_results, "expression_clarify")
    stance_data = _get_previous_data(previous_results, "stance_analysis")
    conflict_data = _get_previous_data(previous_results, "conflict_detect")

    messages = [
        {"role": "system", "content": ACTION_PLAN_PROMPT},
        {"role": "user", "content": (
            f"用户描述：\n{user_input}\n\n"
            f"表达澄清：\n{json.dumps(clarify_data, ensure_ascii=False)}\n\n"
            f"立场分析：\n{json.dumps(stance_data, ensure_ascii=False)}\n\n"
            f"冲突识别：\n{json.dumps(conflict_data, ensure_ascii=False)}"
        )},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.5)
    return parse_json_safe(result)


register_skill(SkillDefinition(
    name="action_plan",
    label="行动规划",
    description="生成 2-3 个具体可执行的行动方案",
    handler=_action_plan,
    depends_on=["conflict_detect"],
    max_timeout=20.0,
))


DRAFT_MESSAGE_PROMPT = compose_relationship_system_prompt(
    """你是亲健平台的「沟通草稿」模块。根据用户选择的方案，生成一份可以直接使用的沟通表达。

要求：
- 使用日常说话的语气，保留用户原有的称呼和表达习惯
- 根据已知事实说清感受和请求，不编造对方的处境，也不要求用户示弱或讨好
- 不指责、不操控、不翻旧账
- 给出 2 个版本：一个偏温和，一个偏直接

请输出 JSON（不要包含其他文字）：
{
  "drafts": [
    {"style": "温和版", "content": "具体表达内容（150字内）"},
    {"style": "直接版", "content": "具体表达内容（150字内）"}
  ],
  "opening_line": "建议的开场白（40字内）",
  "tone_guide": "语气建议（30字内）",
  "avoid": ["不要说的话1", "不要说的话2"],
  "best_channel": "建议的沟通方式（如面对面/消息/电话）"
}"""
)


async def _draft_message(
    *, context: dict[str, Any], previous_results: dict[str, SkillOutput]
) -> dict[str, Any]:
    user_input = _get_user_input(context)
    clarify_data = _get_previous_data(previous_results, "expression_clarify")
    stance_data = _get_previous_data(previous_results, "stance_analysis")
    plan_data = _get_previous_data(previous_results, "action_plan")
    selected_proposal = context.get("selected_proposal_id", "A")

    messages = [
        {"role": "system", "content": DRAFT_MESSAGE_PROMPT},
        {"role": "user", "content": (
            f"用户描述：\n{user_input}\n\n"
            f"表达澄清：\n{json.dumps(clarify_data, ensure_ascii=False)}\n\n"
            f"立场分析：\n{json.dumps(stance_data, ensure_ascii=False)}\n\n"
            f"行动方案：\n{json.dumps(plan_data, ensure_ascii=False)}\n\n"
            f"用户选择的方案：{selected_proposal}"
        )},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.5)
    return parse_json_safe(result)


register_skill(SkillDefinition(
    name="draft_message",
    label="沟通草稿",
    description="基于选定方案生成可直接使用的沟通表达",
    handler=_draft_message,
    depends_on=["action_plan"],
    max_timeout=20.0,
))


REVIEW_PROMPT = compose_relationship_system_prompt(
    """你是亲健平台的「复盘」模块。帮助用户回顾一次关系事件的处理过程。

请输出 JSON（不要包含其他文字）：
{
  "event_summary": "事件概要（60字内）",
  "what_worked": ["做得好的地方1", "做得好的地方2"],
  "what_to_improve": ["可以改进的地方1"],
  "lesson": "这次事件的核心经验（60字内）",
  "pattern_noticed": "是否发现重复出现的关系模式（60字内，没有就写'暂未发现明显模式'）",
  "next_attention": "下次类似情况需要留意的点（40字内）"
}"""
)


async def _review(
    *, context: dict[str, Any], previous_results: dict[str, SkillOutput]
) -> dict[str, Any]:
    user_input = _get_user_input(context)
    review_input = context.get("review_input", "")

    messages = [
        {"role": "system", "content": REVIEW_PROMPT},
        {"role": "user", "content": (
            f"原始事件：\n{user_input}\n\n"
            f"用户的复盘反馈：\n{review_input}" if review_input
            else f"请基于以下事件生成复盘提纲：\n\n{user_input}"
        )},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.4)
    return parse_json_safe(result)


register_skill(SkillDefinition(
    name="review",
    label="复盘",
    description="回顾事件处理过程，提炼经验教训和关系模式",
    handler=_review,
    depends_on=[],
    max_timeout=15.0,
))


MEMORY_EXTRACT_PROMPT = compose_relationship_system_prompt(
    """你是亲健平台的「关系记忆」提取模块。从对话和分析结果中提取值得长期记住的信息。

请输出 JSON（不要包含其他文字）：
{
  "memories": [
    {
      "type": "person/event/strategy/pattern",
      "subject": "关键词或人名（10字内）",
      "content": "需要记住的信息（80字内）",
      "importance": 1-5
    }
  ]
}

提取原则：
- person：新出现的人物及其关系角色和特征
- event：重要的关系事件及其结果
- strategy：用户尝试过的处理方式及效果
- pattern：反复出现的互动模式
- 只提取有长期价值的信息，不记录琐碎细节"""
)


async def _memory_write(
    *, context: dict[str, Any], previous_results: dict[str, SkillOutput]
) -> dict[str, Any]:
    user_input = _get_user_input(context)

    # 收集所有前置 Skill 的输出作为参考
    all_data = {}
    for name, output in previous_results.items():
        if output.success:
            all_data[name] = output.data

    messages = [
        {"role": "system", "content": MEMORY_EXTRACT_PROMPT},
        {"role": "user", "content": (
            f"用户描述：\n{user_input}\n\n"
            f"分析结果：\n{json.dumps(all_data, ensure_ascii=False)}"
        )},
    ]
    result = await chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.2)
    return parse_json_safe(result)


register_skill(SkillDefinition(
    name="memory_write",
    label="关系记忆",
    description="从对话中提取值得长期记住的人物、事件、策略和模式",
    handler=_memory_write,
    depends_on=[],
    max_timeout=15.0,
))
