"""Chinese display labels for public API responses.

Raw enum/code values stay available for machines; label fields and translated
summaries keep user-facing surfaces from leaking implementation codes.
"""

from __future__ import annotations

import re
from typing import Any


PAIR_TYPE_LABELS = {
    "couple": "情侣",
    "spouse": "夫妻",
    "friend": "朋友",
    "bestfriend": "挚友",
    "parent": "育儿夫妻",
    "": "待双方确认",
}

STATUS_LABELS = {
    "pending": "待确认",
    "active": "已启用",
    "completed": "已完成",
    "failed": "未完成",
    "ended": "已结束",
    "acknowledged": "已查看",
    "resolved": "已解除",
    "escalated": "已升级处理",
    "skipped": "已跳过",
    "approved": "已确认",
    "rejected": "未确认",
    "cancelled": "已取消",
}

RISK_LEVEL_LABELS = {
    "none": "平稳",
    "low": "轻度",
    "mild": "轻度",
    "watch": "值得留意",
    "medium": "中度",
    "moderate": "中度",
    "high": "高风险",
    "severe": "高风险",
}

LANGUAGE_LABELS = {
    "zh": "中文",
    "en": "英文",
    "mixed": "中英混合",
    "unknown": "待识别",
}

SENTIMENT_LABELS = {
    "positive": "偏正向",
    "negative": "偏负向",
    "neutral": "平稳",
}

TONE_LABELS = {
    "warm": "温暖",
    "gentle": "温和",
    "direct": "直接",
    "concise": "简短",
    "intense": "强烈",
    "neutral": "平稳",
}

REACTION_TYPE_LABELS = {
    "withdraw": "退开",
    "defend": "防御",
    "seek_support": "想被回应",
    "clarify": "先对齐理解",
    "repair": "想修复",
    "reflect": "复盘",
    "urgent": "急着解决",
    "neutral": "平稳",
}

RELATIONSHIP_SIGNAL_LABELS = {
    "protective_pause": "先暂停保护",
    "lower_stimulation_first": "先降刺激",
    "slow_down_and_reopen": "先慢下来再重开",
    "safe_to_align": "可以进入对齐",
    "needs_supportive_response": "先回应情绪",
    "steady_check_in": "日常记录",
}

EMOTION_LABELS = {
    "positive": "偏正向",
    "negative": "偏负向",
    "neutral": "平稳",
    "happy": "开心",
    "sad": "失落",
    "angry": "生气",
    "anxious": "焦虑",
    "calm": "平静",
    "tired": "疲惫",
    "excited": "兴奋",
}

PLAN_TYPE_LABELS = {
    "conflict_repair_plan": "冲突修复计划",
    "low_connection_recovery": "低连接修复计划",
    "distance_compensation_plan": "异地连接计划",
    "self_regulation_plan": "自我调节计划",
}

PROTOCOL_TYPE_LABELS = {
    "steady_maintenance": "低压维护方案",
    "gentle_repair": "轻度修复方案",
    "structured_repair": "结构化修复方案",
    "de_escalation_protocol": "冲突止损方案",
    "conflict_repair_plan": "冲突修复计划",
}

MODEL_FAMILY_LABELS = {
    "rule_engine_with_safety_first": "安全优先的规则引擎",
    "rule_engine_with_feedback_loop": "规则引擎与反馈闭环",
}

FOCUS_TAG_LABELS = {
    "long_distance": "异地",
    "practice_honest_reflection": "练习诚实复盘",
}

DECISION_FEEDBACK_LABELS = {
    "judgement_too_high": "判断偏高",
    "judgement_too_low": "判断偏低",
    "direction_off": "方向不对",
    "copy_unnatural": "文案不自然",
    "acceptable": "可接受",
}

TASK_CATEGORY_LABELS = {
    "communication": "沟通类",
    "repair": "修复类",
    "activity": "陪伴类",
    "reflection": "调节类",
    "connection": "连接类",
}

REPORT_TYPE_LABELS = {
    "daily": "日报",
    "weekly": "周报",
    "monthly": "月报",
    "solo": "个人简报",
}

INLINE_CODE_LABELS = {
    **RISK_LEVEL_LABELS,
    **LANGUAGE_LABELS,
    **SENTIMENT_LABELS,
    **TONE_LABELS,
    **REACTION_TYPE_LABELS,
    **RELATIONSHIP_SIGNAL_LABELS,
    **EMOTION_LABELS,
    **PLAN_TYPE_LABELS,
    **PROTOCOL_TYPE_LABELS,
    **MODEL_FAMILY_LABELS,
    **FOCUS_TAG_LABELS,
    "relationship_intervention_system_v1": "关系行为干预系统第一版",
    "reduce_load": "先降负荷",
    "steady": "稳步推进",
    "deepen": "加深连接",
    "clear": "清晰具体",
    "gentle": "温和",
    "compact": "简短",
    "example": "带示例",
    "default": "默认",
    "auto_applied": "自动采用",
    "level_changed": "等级变化",
    "auto_recovered": "自动恢复",
    **DECISION_FEEDBACK_LABELS,
}


def label_from(mapping: dict[str, str], value: Any, fallback: str) -> str:
    return mapping.get(str(value or "").strip(), fallback)


def pair_type_label(value: Any) -> str:
    return label_from(PAIR_TYPE_LABELS, value, "待双方确认")


def status_label(value: Any) -> str:
    return label_from(STATUS_LABELS, value, "待确认")


def risk_level_label(value: Any) -> str:
    return label_from(RISK_LEVEL_LABELS, value, "待评估")


def language_label(value: Any) -> str:
    return label_from(LANGUAGE_LABELS, value, "待识别")


def sentiment_label(value: Any) -> str:
    return label_from(SENTIMENT_LABELS, value, "平稳")


def tone_label(value: Any) -> str:
    return label_from(TONE_LABELS, value, "平稳")


def reaction_type_label(value: Any) -> str:
    return label_from(REACTION_TYPE_LABELS, value, "平稳")


def relationship_signal_label(value: Any) -> str:
    return label_from(RELATIONSHIP_SIGNAL_LABELS, value, "日常记录")


def emotion_label(value: Any) -> str:
    fallback = translate_inline_codes(value)
    return label_from(EMOTION_LABELS, value, fallback or "待识别")


def plan_type_label(value: Any) -> str:
    return label_from(PLAN_TYPE_LABELS, value, "关系支持计划")


def protocol_type_label(value: Any) -> str:
    return label_from(PROTOCOL_TYPE_LABELS, value, "修复方案")


def model_family_label(value: Any) -> str:
    return label_from(MODEL_FAMILY_LABELS, value, "规则引擎与反馈闭环")


def focus_tag_label(value: Any) -> str:
    return label_from(FOCUS_TAG_LABELS, value, translate_inline_codes(value) or "关系重点")


def decision_feedback_label(value: Any) -> str:
    return label_from(DECISION_FEEDBACK_LABELS, value, "可接受")


def task_category_label(value: Any) -> str:
    return label_from(TASK_CATEGORY_LABELS, value, "任务类")


def report_type_label(value: Any) -> str:
    return label_from(REPORT_TYPE_LABELS, value, "简报")


def translate_inline_codes(value: Any) -> str:
    text = str(value or "")
    for code, label in INLINE_CODE_LABELS.items():
        pattern = re.compile(rf"(^|[^A-Za-z0-9_]){re.escape(code)}(?=$|[^A-Za-z0-9_])")
        text = pattern.sub(lambda match, label=label: f"{match.group(1)}{label}", text)
    return text.replace(" v1", "第一版")
