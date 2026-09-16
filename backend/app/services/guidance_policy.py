"""Shared guidance policy helpers for relationship AI outputs."""

from __future__ import annotations

from typing import Any

RISK_ORDER = {
    "none": 0,
    "low": 1,
    "mild": 1,
    "watch": 1,
    "medium": 2,
    "moderate": 2,
    "high": 3,
    "severe": 3,
}

_CRISIS_KEYWORDS = {
    "violence": [
        "打我",
        "家暴",
        "威胁我",
        "威胁",
        "跟踪",
        "骚扰",
        "强迫",
        "控制我",
        "囚禁",
        "不敢回家",
        "不让我走",
        "勒索",
        "报复我",
        "伤害我",
    ],
    "self_harm": [
        "自杀",
        "轻生",
        "不想活",
        "活不下去",
        "自残",
        "割腕",
        "跳楼",
        "吞药",
        "伤害自己",
    ],
    "medical": [
        "昏迷",
        "出血",
        "呼吸困难",
        "药物过量",
        "中毒",
        "受伤很重",
        "休克",
    ],
    "fire": ["起火", "火灾", "爆炸", "浓烟", "着火"],
    "minor": ["未成年", "孩子", "学生", "女儿", "儿子"],
}


def normalize_risk_level(value: str | None) -> str:
    raw = str(value or "none").strip().lower()
    if raw == "low":
        return "mild"
    if raw == "medium":
        return "moderate"
    if raw == "high":
        return "severe"
    if raw not in RISK_ORDER:
        return "none"
    return raw


def _metric_number(container: dict[str, Any], key: str) -> float | None:
    value = container.get(key)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _detect_crisis_categories(text: str | None) -> list[str]:
    lowered = str(text or "").strip().lower()
    if not lowered:
        return []

    hits: list[str] = []
    for category, keywords in _CRISIS_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            hits.append(category)
    return hits


def build_crisis_support(
    *,
    scope_type: str,
    risk_level: str | None,
    current_input_text: str | None = None,
) -> dict[str, Any] | None:
    normalized = normalize_risk_level(risk_level)
    categories = _detect_crisis_categories(current_input_text)
    if normalized != "severe" and not categories:
        return None

    channels: list[dict[str, str]] = []

    def add_channel(channel_id: str, label: str, use_when: str) -> None:
        if any(existing["id"] == channel_id for existing in channels):
            return
        channels.append({"id": channel_id, "label": label, "use_when": use_when})

    if "violence" in categories:
        add_channel("110", "公安报警", "人身威胁、家暴、跟踪、强迫或正在发生的违法侵害")
        add_channel("12110", "短信报警", "不方便通话时，可作为 110 的短信补充")
        add_channel("120", "医疗急救", "如果已经受伤或需要紧急医疗处理")
    if "medical" in categories or "self_harm" in categories or normalized == "severe":
        add_channel("120", "医疗急救", "受伤、昏迷、药物过量、自伤已发生或需要急救")
    if "fire" in categories:
        add_channel("119", "消防救援", "火灾、爆炸、浓烟或需要消防救援")
    if "self_harm" in categories or normalized == "severe":
        add_channel("12356", "心理援助热线", "情绪崩溃、强烈绝望或自伤想法时先求助")
    if "minor" in categories:
        add_channel("12355", "青少年支持热线", "未成年人需要心理或法律支持时可补充联系")

    if not channels:
        add_channel("110", "公安报警", "如果当前存在现实人身危险，请先报警")
        add_channel("120", "医疗急救", "如果有人受伤、昏迷或需要紧急医疗处理")
        add_channel("12356", "心理援助热线", "如果主要是心理危机或强烈绝望感")

    urgent_message = (
        "如果你现在处在现实危险里，请先保证自己的安全，优先联系上面的官方渠道；"
        "等你相对安全后，我再陪你把下一步说清楚。"
    )
    if scope_type == "solo" and "violence" not in categories:
        urgent_message = (
            "如果你现在已经有伤害自己或明显失控的风险，请先联系急救或心理援助热线；"
            "安全优先，其他分析都可以稍后再说。"
        )

    return {
        "urgent_message": urgent_message,
        "channels": channels,
        "detected_categories": categories,
    }


def _is_relationship_stable(
    *,
    scope_type: str,
    recent_baseline: dict[str, Any],
    risk_level: str,
) -> bool:
    if risk_level not in {"none", "mild"}:
        return False

    risk = recent_baseline.get("risk") or {}
    if str(risk.get("trend") or "").strip().lower() == "declining":
        return False

    metrics = recent_baseline.get("metrics") or {}
    crisis_event_count = _metric_number(metrics, "crisis_event_count")
    if crisis_event_count and crisis_event_count > 0:
        return False

    if scope_type != "pair":
        return True

    alignment_score = _metric_number(metrics, "alignment_avg_score")
    overlap_rate = _metric_number(metrics, "interaction_overlap_rate")
    deep_talk_rate = _metric_number(metrics, "deep_conversation_rate")

    return bool(
        (alignment_score is not None and alignment_score >= 65)
        or (overlap_rate is not None and overlap_rate >= 0.45)
        or (deep_talk_rate is not None and deep_talk_rate >= 0.35)
    )


def build_guidance_policy(
    *,
    stable_profile: dict[str, Any] | None,
    recent_baseline: dict[str, Any] | None,
    risk_status: dict[str, Any] | None,
    scope_type: str,
    current_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stable_profile = stable_profile or {}
    recent_baseline = recent_baseline or {}
    risk_status = risk_status or {}
    current_input = current_input or {}

    normalized_risk = normalize_risk_level(
        str(risk_status.get("risk_level") or (recent_baseline.get("risk") or {}).get("current_level") or "none")
    )
    crisis_support = build_crisis_support(
        scope_type=scope_type,
        risk_level=normalized_risk,
        current_input_text=str(current_input.get("text") or ""),
    )

    if crisis_support or normalized_risk == "severe":
        safety_mode = "protective"
    elif normalized_risk == "moderate":
        safety_mode = "cautious"
    else:
        safety_mode = "normal"

    spiritual_opt_in = bool(stable_profile.get("spiritual_support_enabled", False))
    relationship_stable = _is_relationship_stable(
        scope_type=scope_type,
        recent_baseline=recent_baseline,
        risk_level=normalized_risk,
    )
    spiritual_allowed = bool(
        spiritual_opt_in and relationship_stable and safety_mode == "normal"
    )

    if not spiritual_opt_in:
        spiritual_reason = "用户没有明确开启塔罗或星座等轻反思内容。"
    elif safety_mode != "normal":
        spiritual_reason = "当前存在风险或需要更审慎的支持模式，轻娱乐内容已自动关闭。"
    elif not relationship_stable:
        spiritual_reason = "当前关系不属于稳定阶段，系统只保留科学和安全导向的建议。"
    else:
        spiritual_reason = "用户已明确开启，且当前关系稳定、风险较低，可保留轻反思表达。"

    return {
        "response_language": "zh-CN",
        "tone_profile": "gentle_nonjudgmental_clear",
        "science_first": True,
        "scientific_frameworks": [
            "attachment_theory",
            "relationship_psychology",
            "emotion_regulation",
            "positive_psychology",
        ],
        "spiritual_content_enabled_by_user": spiritual_opt_in,
        "spiritual_content_allowed_now": spiritual_allowed,
        "spiritual_content_reason": spiritual_reason,
        "spiritual_content_boundary": "塔罗、星座等内容只能作为轻反思隐喻，不能作为事实判断、风险判断或行动依据。",
        "relationship_state": "stable" if relationship_stable else "strained",
        "safety_mode": safety_mode,
        "crisis_routing_enabled": True,
        "crisis_response_required": crisis_support is not None,
        "crisis_support": crisis_support,
        "coercion_forbidden": True,
        "enabling_forbidden": True,
        "legal_safety_required": True,
        "style_requirements": [
            "始终使用简体中文",
            "保持温柔、清楚、不评判",
            "不给命令式或逼迫式建议",
        ],
        "forbidden_guidance": [
            "操控对方",
            "报复对方",
            "强迫沟通或复合",
            "教唆违法违规",
            "替危险行为出主意",
        ],
    }
