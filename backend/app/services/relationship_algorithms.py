"""Structured relationship-text algorithms used before LLM copy generation."""

from __future__ import annotations

import re
from typing import Any

from app.services.behavior_judgement import RISK_ORDER, build_behavior_signal


ABSOLUTE_MARKERS = ("每次都", "总是", "从来", "永远", "根本")
BLAME_MARKERS = ("你怎么又", "都是你", "你就不能", "你到底", "凭什么")
PRESSURE_MARKERS = ("立刻", "马上", "赶紧", "现在就", "必须", "一直", "快点")
DISENGAGE_MARKERS = ("算了", "随便", "不想说了", "别聊了", "滚", "闭嘴", "懒得", "不想再解释")
SOFTENING_MARKERS = ("我想", "我有点", "可以吗", "方便的话", "等你有空", "确认一下", "想和你聊")
RESPONSE_MARKERS = ("没回", "不回", "回我", "回复", "回应", "消息", "联系")
SPACE_MARKERS = ("缓一下", "冷静", "先缓", "晚点", "没力气", "太累", "先一个人", "先静一静")
CARE_MARKERS = ("在乎", "理解", "听见", "\u63a5\u4f4f", "认真", "被看见", "想好好说", "不想吵")
TIME_WINDOW_MARKERS = ("有空", "方便", "十分钟", "晚点", "忙完", "之后", "什么时候", "今天", "明天")

FOCUS_RULES = {
    "回应节奏": RESPONSE_MARKERS,
    "被理解": ("理解", "听见", "\u63a5\u4f4f", "认真", "被看见", "在乎", "尊重"),
    "缓冲空间": SPACE_MARKERS,
    "压力感": ("催", "质问", "压力", "逼", "怎么又", "总是", "从来", "立刻"),
    "修复连接": ("想好好说", "不想吵", "修复", "靠近", "继续", "重新聊", "不想失去"),
    "时间安排": TIME_WINDOW_MARKERS,
}

FOCUS_SUMMARIES = {
    "回应节奏": "更在意回应有没有跟上，没等到时容易多想。",
    "被理解": "更在意自己的感受有没有被认真听进去。",
    "缓冲空间": "更需要一点缓冲，不想在太累或太满的时候硬聊。",
    "压力感": "更容易先感到被催或被审问，注意力会先跑到防御上。",
    "修复连接": "其实是在想把关系接回来，不是想继续顶着走。",
    "时间安排": "更想把什么时候聊、聊多久说具体，心里才会稳一点。",
}

ALGORITHM_VERSION = "relationship_judgement_v2"

_OTHER_PARTY_SUBJECT = (
    r"(?:他|她|对方|男朋友|女朋友|老公|老婆|对象|前任|室友|朋友|同事|领导|我爸|我妈|爸|妈)"
)
_OTHER_PARTY_QUOTED_SPAN_RE = re.compile(
    _OTHER_PARTY_SUBJECT
    + r"[^，。；;！？!?\n]{0,10}(?:说|发|发了|发来|回了|回我|讲|骂)(?:了)?(?:一句|句)?[：:\s]*"
    + r"[“\"‘'「『]([^”\"’'」』]+)[”\"’'」』]"
)
_OTHER_PARTY_PURE_REPORT_RE = re.compile(
    r"^"
    + _OTHER_PARTY_SUBJECT
    + r"(?:刚刚|刚才|刚|昨天|今天)?(?:对我|跟我|向我|给我|回我)(?:说|发|发了|讲|骂)(?:了)?(?:一句|句)?[：:\s]*"
    + r"[^，。；;！？!?\n]{1,28}[。！？!?]?$"
)
_RHETORICAL_REBUKE_RE = re.compile(
    r"(?:你|你们)?(?:能不能|就不能|可不可以)\s*(?:别|不要|少|滚)"
)
_SECOND_PERSON_DISMISSIVE_RE = re.compile(
    r"(?:别|不要|少)(?:总|老|一直|天天)?(?:来)?烦我|(?:总|老|天天)来烦我|少来这套|真烦人"
)
_SECOND_PERSON_GENERALIZING_RE = re.compile(
    r"你(?:每次都|总是|老是|从来|永远|根本|动不动就|别总|总来)"
)
_CALM_SELF_BOUNDARY_RE = re.compile(
    r"^我(?:今天|今晚|现在|这会儿|暂时|先)?(?:有点累|想先静一静|想安静|想自己待|需要自己待|先一个人待|不想继续聊|想先休息)"
)


def analyze_draft_attribution(cleaned: str) -> dict[str, Any]:
    """区分本人准备发出的话与转述/引用对方原话，避免把对方说的话当成本人指责。"""
    if not cleaned:
        return {
            "speaker_attribution": "self_outgoing",
            "self_authored_text": "",
            "quoted_segments": [],
        }

    quoted_segments = [m.group(1).strip() for m in _OTHER_PARTY_QUOTED_SPAN_RE.finditer(cleaned) if m.group(1).strip()]
    remainder = _OTHER_PARTY_QUOTED_SPAN_RE.sub("", cleaned)
    remainder_clean = re.sub(r"[，,。；;！？!?：:\s]+", "", remainder)

    if quoted_segments:
        if not remainder_clean or remainder_clean in {"这句", "这句话", "这样"}:
            return {
                "speaker_attribution": "quoted_other_party",
                "self_authored_text": "",
                "quoted_segments": quoted_segments,
            }
        return {
            "speaker_attribution": "mixed",
            "self_authored_text": _clean_text(remainder),
            "quoted_segments": quoted_segments,
        }

    if _OTHER_PARTY_PURE_REPORT_RE.match(cleaned):
        return {
            "speaker_attribution": "quoted_other_party",
            "self_authored_text": "",
            "quoted_segments": [cleaned],
        }

    return {
        "speaker_attribution": "self_outgoing",
        "self_authored_text": cleaned,
        "quoted_segments": [],
    }


def _collect_escalation_cues(self_authored: str) -> tuple[list[str], float]:
    if not self_authored:
        return [], 0.0
    cues: list[str] = []
    extra_score = 0.0
    if _RHETORICAL_REBUKE_RE.search(self_authored):
        cues.append("“你能不能别……”这类反问句式容易让对方先感到被责怪而防御")
        extra_score += 0.65
    if _SECOND_PERSON_DISMISSIVE_RE.search(self_authored):
        cues.append("“别总来烦我”这类排斥表达容易让对方感到被嫌弃，引发对立")
        extra_score += 0.75
    if _SECOND_PERSON_GENERALIZING_RE.search(self_authored) or _has_any(self_authored, ABSOLUTE_MARKERS):
        cues.append("“每次都/总/从来”等概括词容易把讨论拉向争论对错")
    if _has_any(self_authored, BLAME_MARKERS):
        cues.append("指责性开头容易让对方只听到批评，忽略你真正想说的事")
    if _has_any(self_authored, ("滚", "闭嘴", "真服了", "懒得")):
        cues.append("带厌烦或推开意味的措辞容易让对话直接僵住")
    return cues[:3], round(extra_score, 2)


def _pressure_risk_summary(self_authored: str, pressure_count: int) -> tuple[str, str]:
    if not self_authored:
        return "none", "暂无施压或威胁风险"
    if pressure_count >= 2 or (pressure_count >= 1 and _has_any(self_authored, BLAME_MARKERS + ABSOLUTE_MARKERS)):
        return "watch", "带有催促或施压语气，留意对方压迫感"
    if pressure_count >= 1:
        return "watch", "略带催促语气，暂无明显威胁"
    return "none", "暂无施压或威胁风险"


def _friction_level_summary(
    speaker_attribution: str,
    score: float,
    cues: list[str],
) -> tuple[str, str]:
    if speaker_attribution == "quoted_other_party":
        return "low", "像是在转述对方的话，不是你主动发出的指责"
    if score >= 1.9:
        return "high", "刺激性较强，容易引发明显对立"
    if score >= 0.95 or cues:
        return "medium", "部分字眼容易让对方防御或让对话升级"
    return "low", "表达较平和，未见明显刺激字眼"


def _clean_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _count_markers(text: str, markers: tuple[str, ...]) -> int:
    return sum(text.count(marker) for marker in markers if marker)


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _trim(text: str, limit: int) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1]}…"


def _char_ngrams(text: str, n: int = 2) -> set[str]:
    cleaned = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", _clean_text(text))
    if len(cleaned) < n:
        return {cleaned} if cleaned else set()
    return {cleaned[i : i + n] for i in range(len(cleaned) - n + 1)}


def _overlap_ratio(text_a: str, text_b: str) -> float:
    grams_a = _char_ngrams(text_a)
    grams_b = _char_ngrams(text_b)
    union = grams_a | grams_b
    if not union:
        return 0.0
    return round(len(grams_a & grams_b) / len(union), 4)


def _focus_labels(text: str, signal: dict[str, Any]) -> list[str]:
    hits: list[tuple[str, int]] = []
    for label, markers in FOCUS_RULES.items():
        score = _count_markers(text, markers)
        if score > 0:
            hits.append((label, score))
    hits.sort(key=lambda item: item[1], reverse=True)
    labels = [label for label, _score in hits[:2]]
    if labels:
        return labels

    reaction = str(signal.get("reaction_type") or "neutral")
    fallback = {
        "withdraw": ["缓冲空间"],
        "defend": ["压力感"],
        "seek_support": ["被理解"],
        "clarify": ["时间安排"],
        "repair": ["修复连接"],
        "urgent": ["回应节奏"],
    }
    return fallback.get(reaction, ["被理解"])


def _confidence_from_message_score(
    *,
    score: float,
    signal: dict[str, Any],
    focus_labels: list[str],
    absolute_count: int,
    blame_count: int,
    pressure_count: int,
    soften_count: int,
    time_window_count: int,
) -> float:
    confidence = 0.45
    confidence += min(0.18, (absolute_count + blame_count) * 0.045 + pressure_count * 0.025)
    confidence += min(0.12, soften_count * 0.03 + time_window_count * 0.025)
    confidence += min(0.1, len(focus_labels) * 0.04)
    if signal.get("reaction_type") != "neutral":
        confidence += 0.05
    if score >= 1.9:
        confidence += 0.08
    elif score < 0.6:
        confidence -= 0.04
    return max(0.35, min(0.95, round(confidence, 2)))


def _confidence_from_alignment_score(
    *,
    score: int,
    overlap: float,
    emotion_overlap: float,
    focus_overlap: float,
    signal_a: dict[str, Any],
    signal_b: dict[str, Any],
) -> float:
    confidence = 0.46
    confidence += min(0.18, (score - 54) / 120)
    confidence += min(0.12, overlap * 0.08 + emotion_overlap * 0.06 + focus_overlap * 0.08)
    if signal_a.get("reaction_type") == signal_b.get("reaction_type") == "clarify":
        confidence += 0.05
    if signal_a.get("reaction_type") in {"repair", "seek_support"} or signal_b.get("reaction_type") in {"repair", "seek_support"}:
        confidence += 0.04
    if {str(signal_a.get("reaction_type") or ""), str(signal_b.get("reaction_type") or "")} in ({"urgent", "withdraw"}, {"defend", "withdraw"}):
        confidence -= 0.06
    return max(0.35, min(0.94, round(confidence, 2)))


def _risk_level_from_score(score: float) -> str:
    if score >= 1.9:
        return "high"
    if score >= 0.95:
        return "medium"
    return "low"


def _risk_reason(score: float, cleaned: str, signal: dict[str, Any]) -> str:
    if score < 0.95:
        return "这句话说清了请求和时间，没有明显的责怪或催促。"
    if _has_any(cleaned, ABSOLUTE_MARKERS + BLAME_MARKERS):
        return "有些措辞像是在责怪对方，可能让人忽略你想说的事。"
    if signal.get("reaction_type") in {"withdraw", "defend", "urgent"}:
        return "语气比较急，但还没有说清希望对方怎么做。"
    return "这句话可能让对方感到被催促，可以把要求说得更具体。"


def _partner_view(risk_level: str, signal: dict[str, Any]) -> str:
    reaction = str(signal.get("reaction_type") or "neutral")
    if risk_level == "low":
        return "对方可能会理解为你在确认安排。"
    if reaction in {"defend", "urgent"}:
        return "对方可能觉得自己被责怪了，先解释或反驳。"
    if reaction == "withdraw":
        return "对方可能认为你不想再聊，也可能继续追问原因。"
    return "对方可能看得出你不高兴，但不清楚你希望怎么处理。"


def _likely_impact(risk_level: str, signal: dict[str, Any]) -> str:
    reaction = str(signal.get("reaction_type") or "neutral")
    if risk_level == "low":
        return "可以接着确认时间或具体安排。"
    if risk_level == "high":
        if reaction == "withdraw":
            return "这句话可能使对话中断，事情仍然没有说清楚。"
        return "接下来可能争论谁对谁错，而没有讨论怎么处理这件事。"
    return "双方可能需要先解释这句话是什么意思，才能继续讨论。"


def _conversation_goal(risk_level: str, signal: dict[str, Any]) -> str:
    if risk_level == "low":
        return "确认具体安排"
    if risk_level == "high":
        return "说清当前的问题和自己的要求"
    if str(signal.get("reaction_type") or "") == "seek_support":
        return "说明自己需要什么帮助"
    return "说清自己的想法和要求"


def _suggested_tone(risk_level: str, signal: dict[str, Any]) -> str:
    if risk_level == "low":
        return "保持当前语气"
    if risk_level == "high":
        return "平静、直接"
    if str(signal.get("reaction_type") or "") == "seek_support":
        return "直接说明自己的感受"
    return "说具体的事，不评价对方为人"


def _rewrite_draft(cleaned: str, risk_level: str, signal: dict[str, Any]) -> str:
    if not cleaned:
        return "请先输入准备发出的消息。"

    if _has_any(cleaned, ABSOLUTE_MARKERS + BLAME_MARKERS + DISENGAGE_MARKERS):
        if _has_any(cleaned, RESPONSE_MARKERS):
            return "一直没等到你的回复，我有些着急。方便的时候回我一下吧。"
        return "这件事我有些在意，想和你说清楚。你什么时候方便聊？"

    if risk_level == "low":
        if cleaned.endswith(("吗？", "吗?", "可以吗？", "可以吗?")):
            return cleaned
        if _has_any(cleaned, TIME_WINDOW_MARKERS):
            return f"{cleaned.rstrip('。！？!?')}，可以吗？"
        return cleaned

    if _has_any(cleaned, RESPONSE_MARKERS):
        return "一直没等到你的回复，我有些着急。方便的时候回我一下吧。"
    if str(signal.get("reaction_type") or "") == "withdraw":
        return "我现在不太想继续聊，需要先休息一会儿。晚点再说，可以吗？"
    return "我想把这件事说清楚，你现在方便聊吗？"


def build_message_preview_baseline(draft: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    del context
    cleaned = _clean_text(draft)
    attribution = analyze_draft_attribution(cleaned)
    speaker_attribution = attribution["speaker_attribution"]
    scored_text = attribution["self_authored_text"]

    if speaker_attribution == "quoted_other_party":
        signal = build_behavior_signal("", risk_level="none", sentiment_hint="neutral")
        return {
            "partner_view": "如果原样发出去，对方可能不清楚你是在复述他的话，还是想接着回应。",
            "likely_impact": "只把对方说过的话转述回去，容易让对话停在重复原话，还没说清你的态度。",
            "risk_level": "low",
            "risk_reason": "这句像是在转述对方对你说的话，不是你主动发出的指责；发前可以先写清你想回什么。",
            "safer_rewrite": "你刚才那句话让我挺不舒服的。",
            "suggested_tone": "先写清你自己的回应",
            "conversation_goal": "确认是转述原话还是准备回复",
            "speaker_attribution": speaker_attribution,
            "pressure_risk_level": "none",
            "pressure_risk_label": "暂无施压或威胁风险",
            "escalation_friction_level": "low",
            "escalation_friction_label": "像是在转述对方的话，不是你主动发出的指责",
            "escalation_cues": [],
            "algorithm_version": ALGORITHM_VERSION,
            "confidence": 0.62,
            "decision_trace": {
                "algorithm_version": ALGORITHM_VERSION,
                "layer": "message_simulation",
                "speaker_attribution": speaker_attribution,
                "quoted_segments": attribution["quoted_segments"],
                "focus_labels": ["被理解"],
                "signal": {
                    "inferred_tone": "neutral",
                    "reaction_type": "neutral",
                    "pressure_score": 0,
                    "softening_score": 0,
                    "blame_score": 0,
                    "emotion_tags": [],
                },
                "score_breakdown": {"tone": 0.0, "reaction": 0.0, "markers": 0.0, "softening": 0.0, "punctuation": 0.0},
                "risk_score": 0.0,
                "confidence": 0.62,
                "narrative": {
                    "partner_view": "如果原样发出去，对方可能不清楚你是在复述他的话，还是想接着回应。",
                    "likely_impact": "只把对方说过的话转述回去，容易让对话停在重复原话，还没说清你的态度。",
                    "conversation_goal": "确认是转述原话还是准备回复",
                    "suggested_tone": "先写清你自己的回应",
                },
            },
            "focus_labels": ["被理解"],
            "risk_score": 0.0,
            "baseline_delta": -1.0,
            "fallback_reason": None,
            "shadow_result": None,
            "feedback_status": "pending_feedback",
            "do_list": ["先确认这是对方说的话，再写出你想回复的内容"],
            "avoid_list": ["不要把转述原话直接当成待发送消息"],
            "structured_evidence": {
                "speaker_attribution": speaker_attribution,
                "quoted_segments": attribution["quoted_segments"],
                "risk_score": 0.0,
                "pressure_risk_level": "none",
                "escalation_friction_level": "low",
                "escalation_cues": [],
                "reaction_type": "neutral",
                "inferred_tone": "neutral",
                "absolute_count": 0,
                "blame_count": 0,
                "pressure_count": 0,
                "soften_count": 0,
                "time_window_count": 0,
            },
        }

    signal = build_behavior_signal(scored_text, risk_level="none", sentiment_hint=None)
    focus_labels = _focus_labels(scored_text, signal)
    absolute_count = _count_markers(scored_text, ABSOLUTE_MARKERS)
    blame_count = _count_markers(scored_text, BLAME_MARKERS)
    pressure_count = _count_markers(scored_text, PRESSURE_MARKERS)
    soften_count = _count_markers(scored_text, SOFTENING_MARKERS)
    time_window_count = _count_markers(scored_text, TIME_WINDOW_MARKERS)
    disengage_count = _count_markers(scored_text, DISENGAGE_MARKERS)
    exclamation_count = scored_text.count("!") + scored_text.count("！")
    escalation_cues, friction_bonus = _collect_escalation_cues(scored_text)

    score = 0.0
    if signal["inferred_tone"] == "intense":
        score += 1.1
    if signal["reaction_type"] in {"defend", "urgent"}:
        score += 0.9
    elif signal["reaction_type"] == "withdraw":
        score += 0.5
    score += min(
        1.95,
        absolute_count * 0.62
        + blame_count * 0.68
        + pressure_count * 0.3
        + disengage_count * 0.5
        + friction_bonus,
    )
    if (absolute_count or friction_bonus > 0) and scored_text.startswith("你"):
        score += 0.35
    if absolute_count and disengage_count:
        score += 0.55
    score += min(0.45, exclamation_count * 0.18)
    score -= min(1.2, soften_count * 0.32 + time_window_count * 0.22)
    if signal["reaction_type"] in {"clarify", "repair"}:
        score -= 0.28
    # 平和的第一人称边界表达不按冲突计分
    if _CALM_SELF_BOUNDARY_RE.match(scored_text) and not escalation_cues and pressure_count == 0:
        score = 0.0
    score = max(0.0, round(score, 2))

    risk_level = _risk_level_from_score(score)
    pressure_risk_level, pressure_risk_label = _pressure_risk_summary(scored_text, pressure_count)
    escalation_friction_level, escalation_friction_label = _friction_level_summary(
        speaker_attribution, score, escalation_cues
    )
    confidence = _confidence_from_message_score(
        score=score,
        signal=signal,
        focus_labels=focus_labels,
        absolute_count=absolute_count,
        blame_count=blame_count,
        pressure_count=pressure_count,
        soften_count=soften_count,
        time_window_count=time_window_count,
    )
    score_breakdown = {
        "tone": 1.1 if signal["inferred_tone"] == "intense" else 0.0,
        "reaction": 0.9 if signal["reaction_type"] in {"defend", "urgent"} else 0.5 if signal["reaction_type"] == "withdraw" else 0.0,
        "markers": round(
            min(
                1.95,
                absolute_count * 0.62
                + blame_count * 0.68
                + pressure_count * 0.3
                + disengage_count * 0.5
                + friction_bonus,
            ),
            2,
        ),
        "softening": round(min(1.2, soften_count * 0.32 + time_window_count * 0.22), 2),
        "punctuation": round(min(0.45, exclamation_count * 0.18), 2),
    }
    if (absolute_count or friction_bonus > 0) and scored_text.startswith("你"):
        score_breakdown["markers"] = round(score_breakdown["markers"] + 0.35, 2)
    if absolute_count and disengage_count:
        score_breakdown["markers"] = round(score_breakdown["markers"] + 0.55, 2)

    if _CALM_SELF_BOUNDARY_RE.match(scored_text) and risk_level == "low":
        reason_text = "直接说明了自己需要空间，没有责怪或施压。"
        partner_view_text = "对方会知道你现在想自己待一会儿，没有明显的指责意味。"
        likely_impact_text = "大多能先暂停当前对话，保留各自的边界。"
        rewrite_text = cleaned
        goal_text = "平静说明自己需要独处或暂停"
        tone_text = "保持当前平静语气"
    elif friction_bonus > 0 and risk_level != "low":
        reason_text = "没有明显威胁或强迫，但反问和排斥措辞容易让对方先防御或升级对立。"
        partner_view_text = "对方可能感到被指责、被推开，容易先防御或顶回来。"
        likely_impact_text = "对话容易转成争执态度问题，而不是说清你现在想暂停沟通。"
        rewrite_text = "我现在不想被打扰，先不聊了。"
        goal_text = "表达想暂停沟通的边界，不激化对立"
        tone_text = "平静、直接"
    else:
        reason_text = _risk_reason(score, scored_text, signal)
        partner_view_text = _partner_view(risk_level, signal)
        likely_impact_text = _likely_impact(risk_level, signal)
        rewrite_text = _rewrite_draft(cleaned, risk_level, signal)
        goal_text = _conversation_goal(risk_level, signal)
        tone_text = _suggested_tone(risk_level, signal)

    payload = {
        "partner_view": partner_view_text,
        "likely_impact": likely_impact_text,
        "risk_level": risk_level,
        "risk_reason": reason_text,
        "safer_rewrite": rewrite_text,
        "suggested_tone": tone_text,
        "conversation_goal": goal_text,
        "speaker_attribution": speaker_attribution,
        "pressure_risk_level": pressure_risk_level,
        "pressure_risk_label": pressure_risk_label,
        "escalation_friction_level": escalation_friction_level,
        "escalation_friction_label": escalation_friction_label,
        "escalation_cues": escalation_cues,
        "algorithm_version": ALGORITHM_VERSION,
        "confidence": confidence,
        "decision_trace": {
            "algorithm_version": ALGORITHM_VERSION,
            "layer": "message_simulation",
            "speaker_attribution": speaker_attribution,
            "focus_labels": focus_labels,
            "signal": {
                "inferred_tone": signal["inferred_tone"],
                "reaction_type": signal["reaction_type"],
                "pressure_score": signal["pressure_score"],
                "softening_score": signal["softening_score"],
                "blame_score": signal["blame_score"],
                "emotion_tags": signal["emotion_tags"],
            },
            "score_breakdown": score_breakdown,
            "risk_score": score,
            "confidence": confidence,
            "narrative": {
                "partner_view": partner_view_text,
                "likely_impact": likely_impact_text,
                "conversation_goal": goal_text,
                "suggested_tone": tone_text,
            },
        },
        "focus_labels": focus_labels,
        "risk_score": score,
        "baseline_delta": round(score - 1.0, 2),
        "fallback_reason": None,
        "shadow_result": None,
        "feedback_status": "pending_feedback",
        "do_list": (
            ["直接保留你现在的平静边界表达即可"]
            if _CALM_SELF_BOUNDARY_RE.match(scored_text) and risk_level == "low"
            else ["先把想确认的事具体说出来", "问问对方什么时候方便回复"]
            if risk_level == "low"
            else ["先说具体发生了什么", "说清自己的感受和边界"]
            if risk_level == "medium"
            else ["只讨论当前这一件事", "如果说不下去，可以先暂停"]
        ),
        "avoid_list": (
            ["不必额外补出你没打算兑现的承诺"]
            if _CALM_SELF_BOUNDARY_RE.match(scored_text) and risk_level == "low"
            else ["不要临时翻出以前的事", "不要一次讨论太多问题"]
            if risk_level == "low"
            else ["避免用“你每次都这样”概括对方", "不要连续发消息催促"]
            if risk_level == "medium"
            else ["不要辱骂或贬低对方", "不要要求对方立刻回复或认错"]
        ),
        "structured_evidence": {
            "speaker_attribution": speaker_attribution,
            "risk_score": score,
            "pressure_risk_level": pressure_risk_level,
            "escalation_friction_level": escalation_friction_level,
            "escalation_cues": escalation_cues,
            "reaction_type": signal["reaction_type"],
            "inferred_tone": signal["inferred_tone"],
            "absolute_count": absolute_count,
            "blame_count": blame_count,
            "pressure_count": pressure_count,
            "soften_count": soften_count,
            "time_window_count": time_window_count,
        },
    }
    return payload


def _focus_summary(label: str) -> str:
    return FOCUS_SUMMARIES.get(label, "更在意先把自己的位置说清楚。")


def _shared_story(
    focus_a: list[str],
    focus_b: list[str],
    signal_a: dict[str, Any],
    signal_b: dict[str, Any],
) -> str:
    pair = {focus_a[0], focus_b[0]}
    if pair == {"回应节奏", "缓冲空间"}:
        return "一边在等回应，一边在撑着最后一点力气想先缓一下，两边都不是不在乎，只是节奏没对上。"
    if pair <= {"被理解", "修复连接", "时间安排"}:
        return "双方其实都想把这件事讲清楚，也都不想关系继续僵着，只是开口顺序没对上。"
    if signal_a.get("reaction_type") == signal_b.get("reaction_type") == "clarify":
        return "双方都在试着把事情讲明白，只是各自先抓住的重点不同。"
    return "双方都在意这件事，只是各自先看到的重点不同。"


def _misread_risk(focus_a: list[str], focus_b: list[str]) -> str:
    pair = {focus_a[0], focus_b[0]}
    if pair == {"回应节奏", "缓冲空间"}:
        return "一方在等回应，另一方只是想先缓一下，这很容易被互相听成不在乎和催促。"
    if "压力感" in pair and "被理解" in pair:
        return "一方在解释自己的难受，另一方却可能先听成了指责或审问。"
    if "时间安排" in pair and "被理解" in pair:
        return "一方在想把时间说清楚，另一方却可能先在意自己有没有被听见。"
    return "真实意图还没来得及说全，先被听见的已经是压力或冷淡。"


def _divergence_points(focus_a: list[str], focus_b: list[str], signal_a: dict[str, Any], signal_b: dict[str, Any]) -> list[str]:
    points = [
        f"一方先看到{focus_a[0]}，另一方先看到{focus_b[0]}。",
        "真实意图还没完全说出来，先被听见的是说话方式。",
    ]
    reaction_pair = {str(signal_a.get('reaction_type') or ''), str(signal_b.get('reaction_type') or '')}
    if reaction_pair == {"urgent", "withdraw"}:
        points.append("一个更急着确认，一个更想先退开缓冲。")
    elif reaction_pair == {"defend", "withdraw"}:
        points.append("一个在顶住压力，一个在试着把门先关小。")
    else:
        points.append("同一件事里，两边进入对话的节奏没有对上。")
    return [_trim(item, 36) for item in points[:3]]


def _bridge_actions(focus_a: list[str], focus_b: list[str]) -> list[str]:
    actions = ["先复述对方刚才真正担心的是什么，再说自己的版本。", "一次只聊这次卡住的一个点，不顺手扩展到所有旧问题。"]
    pair = {focus_a[0], focus_b[0]}
    if pair == {"回应节奏", "缓冲空间"}:
        actions.insert(0, "先约一个明确的回复时间，让等待的一方心里有底。")
    else:
        actions.insert(0, "先确认这次想解决的是什么，再决定要不要马上深入。")
    return [_trim(item, 36) for item in actions[:3]]


def _suggested_opening(focus_a: list[str], focus_b: list[str]) -> str:
    pair = {focus_a[0], focus_b[0]}
    if pair == {"回应节奏", "缓冲空间"}:
        return "我知道你昨天可能是真的太累了；我这边是因为没等到回应会慌，想和你说清楚这件事。"
    if "被理解" in pair:
        return "我不是想跟你算账，我是想先把我刚才卡住的点说清楚，看看你听见的是不是同一件事。"
    return "我想先听听你刚才最在意什么，也说说我的想法，不急着分对错。"


def _coach_note(focus_a: list[str], focus_b: list[str], score: int) -> str:
    if {focus_a[0], focus_b[0]} == {"回应节奏", "缓冲空间"}:
        return "这次更像是节奏错位，不太像立场对立。"
    if score >= 72:
        return "两边的真实目标并没有离得很远，主要是进入方式不同。"
    return "先把彼此各自看到的那一半讲清楚，后面的修复会更容易。"


def _alignment_score(
    text_a: str,
    text_b: str,
    signal_a: dict[str, Any],
    signal_b: dict[str, Any],
    focus_a: list[str],
    focus_b: list[str],
) -> int:
    overlap = _overlap_ratio(text_a, text_b)
    emotion_a = set(signal_a.get("emotion_tags") or [])
    emotion_b = set(signal_b.get("emotion_tags") or [])
    emotion_overlap = len(emotion_a & emotion_b) / max(len(emotion_a | emotion_b), 1)
    focus_overlap = len(set(focus_a) & set(focus_b)) / max(len(set(focus_a) | set(focus_b)), 1)

    score = 54.0
    score += overlap * 16
    score += emotion_overlap * 10
    score += focus_overlap * 12
    if signal_a.get("reaction_type") == signal_b.get("reaction_type") == "clarify":
        score += 6
    if signal_a.get("reaction_type") in {"repair", "seek_support"} or signal_b.get("reaction_type") in {"repair", "seek_support"}:
        score += 4
    if {
        str(signal_a.get("reaction_type") or ""),
        str(signal_b.get("reaction_type") or ""),
    } in ({"urgent", "withdraw"}, {"defend", "withdraw"}):
        score -= 10
    if signal_a.get("inferred_tone") == "intense" or signal_b.get("inferred_tone") == "intense":
        score -= 8
    if {focus_a[0], focus_b[0]} == {"回应节奏", "缓冲空间"}:
        score -= 4
    return max(32, min(90, int(round(score))))


def build_alignment_baseline(
    *,
    context: dict[str, Any] | None = None,
    checkin_a: dict[str, Any] | None = None,
    checkin_b: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del context
    payload_a = checkin_a or {}
    payload_b = checkin_b or {}
    text_a = _clean_text(payload_a.get("content"))
    text_b = _clean_text(payload_b.get("content"))
    signal_a = build_behavior_signal(text_a, risk_level=payload_a.get("risk_level"), sentiment_hint=payload_a.get("sentiment_score"))
    signal_b = build_behavior_signal(text_b, risk_level=payload_b.get("risk_level"), sentiment_hint=payload_b.get("sentiment_score"))
    focus_a = _focus_labels(text_a, signal_a)
    focus_b = _focus_labels(text_b, signal_b)
    score = _alignment_score(text_a, text_b, signal_a, signal_b, focus_a, focus_b)
    overlap = _overlap_ratio(text_a, text_b)
    emotion_a = set(signal_a.get("emotion_tags") or [])
    emotion_b = set(signal_b.get("emotion_tags") or [])
    emotion_overlap = len(emotion_a & emotion_b) / max(len(emotion_a | emotion_b), 1)
    focus_overlap = len(set(focus_a) & set(focus_b)) / max(len(set(focus_a) | set(focus_b)), 1)
    focus_labels = list(dict.fromkeys([*focus_a, *focus_b]))[:4]
    confidence = _confidence_from_alignment_score(
        score=score,
        overlap=overlap,
        emotion_overlap=emotion_overlap,
        focus_overlap=focus_overlap,
        signal_a=signal_a,
        signal_b=signal_b,
    )
    risk_score = round((100 - score) / 100, 2)
    score_breakdown = {
        "text_overlap": round(overlap, 4),
        "emotion_overlap": round(emotion_overlap, 4),
        "focus_overlap": round(focus_overlap, 4),
        "reaction_bonus": 6 if signal_a.get("reaction_type") == signal_b.get("reaction_type") == "clarify" else 4 if signal_a.get("reaction_type") in {"repair", "seek_support"} or signal_b.get("reaction_type") in {"repair", "seek_support"} else 0,
        "reaction_penalty": 10 if {str(signal_a.get("reaction_type") or ""), str(signal_b.get("reaction_type") or "")} in ({"urgent", "withdraw"}, {"defend", "withdraw"}) else 0,
        "tone_penalty": 8 if signal_a.get("inferred_tone") == "intense" or signal_b.get("inferred_tone") == "intense" else 0,
    }

    return {
        "alignment_score": score,
        "shared_story": _trim(_shared_story(focus_a, focus_b, signal_a, signal_b), 80),
        "view_a_summary": _trim(_focus_summary(focus_a[0]), 60),
        "view_b_summary": _trim(_focus_summary(focus_b[0]), 60),
        "misread_risk": _trim(_misread_risk(focus_a, focus_b), 60),
        "divergence_points": _divergence_points(focus_a, focus_b, signal_a, signal_b),
        "bridge_actions": _bridge_actions(focus_a, focus_b),
        "suggested_opening": _trim(_suggested_opening(focus_a, focus_b), 80),
        "coach_note": _trim(_coach_note(focus_a, focus_b, score), 60),
        "algorithm_version": ALGORITHM_VERSION,
        "confidence": confidence,
        "decision_trace": {
            "algorithm_version": ALGORITHM_VERSION,
            "layer": "alignment",
            "focus_labels": focus_labels,
            "signal_a": {
                "inferred_tone": signal_a.get("inferred_tone"),
                "reaction_type": signal_a.get("reaction_type"),
                "emotion_tags": signal_a.get("emotion_tags") or [],
            },
            "signal_b": {
                "inferred_tone": signal_b.get("inferred_tone"),
                "reaction_type": signal_b.get("reaction_type"),
                "emotion_tags": signal_b.get("emotion_tags") or [],
            },
            "score_breakdown": score_breakdown,
            "risk_score": risk_score,
            "confidence": confidence,
            "narrative": {
                "shared_story": _trim(_shared_story(focus_a, focus_b, signal_a, signal_b), 80),
                "misread_risk": _trim(_misread_risk(focus_a, focus_b), 60),
                "bridge_actions": _bridge_actions(focus_a, focus_b),
            },
        },
        "focus_labels": focus_labels,
        "risk_score": risk_score,
        "baseline_delta": round(score - 54, 2),
        "fallback_reason": None,
        "shadow_result": None,
        "feedback_status": "pending_feedback",
        "structured_evidence": {
            "focus_a": focus_a,
            "focus_b": focus_b,
            "signal_a": {
                "inferred_tone": signal_a.get("inferred_tone"),
                "reaction_type": signal_a.get("reaction_type"),
                "emotion_tags": signal_a.get("emotion_tags") or [],
            },
            "signal_b": {
                "inferred_tone": signal_b.get("inferred_tone"),
                "reaction_type": signal_b.get("reaction_type"),
                "emotion_tags": signal_b.get("emotion_tags") or [],
            },
            "text_overlap": _overlap_ratio(text_a, text_b),
            "focus_labels": focus_labels,
            "alignment_score": score,
        },
        "source": "fallback",
        "is_fallback": True,
    }


def build_message_simulation_metadata(
    draft: str,
    *,
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = build_message_preview_baseline(draft, baseline)
    return {
        "algorithm_version": data.get("algorithm_version") or ALGORITHM_VERSION,
        "confidence": data.get("confidence"),
        "decision_trace": data.get("decision_trace") or {},
        "focus_labels": data.get("focus_labels") or [],
        "risk_score": data.get("risk_score"),
        "baseline_delta": data.get("baseline_delta"),
        "fallback_reason": data.get("fallback_reason"),
        "shadow_result": data.get("shadow_result"),
        "feedback_status": data.get("feedback_status"),
    }


def build_alignment_metadata(
    *,
    context: dict[str, Any] | None = None,
    checkin_a: dict[str, Any] | None = None,
    checkin_b: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = build_alignment_baseline(context=context, checkin_a=checkin_a, checkin_b=checkin_b)
    return {
        "algorithm_version": data.get("algorithm_version") or ALGORITHM_VERSION,
        "confidence": data.get("confidence"),
        "decision_trace": data.get("decision_trace") or {},
        "focus_labels": data.get("focus_labels") or [],
        "risk_score": data.get("risk_score"),
        "baseline_delta": data.get("baseline_delta"),
        "fallback_reason": data.get("fallback_reason"),
        "shadow_result": data.get("shadow_result"),
        "feedback_status": data.get("feedback_status"),
    }
