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
        return "这句话把请求和时间边界说得比较清楚，刺激性不高。"
    if _has_any(cleaned, ABSOLUTE_MARKERS + BLAME_MARKERS):
        return "里面带着绝对化或责备感，对方容易先起防御。"
    if signal.get("reaction_type") in {"withdraw", "defend", "urgent"}:
        return "这句话更容易先把情绪推高，而不是把重点说清楚。"
    return "里面的压力感偏重，容易让对方先卡在情绪上。"


def _partner_view(risk_level: str, signal: dict[str, Any]) -> str:
    reaction = str(signal.get("reaction_type") or "neutral")
    if risk_level == "low":
        return "对方更容易把它听成想温和确认安排，不会感到被指责。"
    if reaction in {"defend", "urgent"}:
        return "对方一看到容易先感受到被劈头盖脸指责，注意力全被火药味带偏，下意识想防守。"
    if reaction == "withdraw":
        return "对方容易觉得气氛太沉重、有压迫感，下意识想缩回壳子里回避。"
    return "对方可能会先觉得有些紧张，感受不到你的需要，只听到情绪负担。"


def _likely_impact(risk_level: str, signal: dict[str, Any]) -> str:
    reaction = str(signal.get("reaction_type") or "neutral")
    if risk_level == "low":
        return "温和对齐了彼此的安排与心意，很容易顺畅继续聊。"
    if risk_level == "high":
        if reaction == "withdraw":
            return "如果直接发出，容易让对方想逃避或已读不回，原本想要关爱反而变成冷战。"
        return "如果直接发出，容易把原本的在乎变成辩论赛，谁也不肯低头退让。"
    return "如果直接发出，容易在误会和解释里来回打转，让彼此都心累。"


def _conversation_goal(risk_level: str, signal: dict[str, Any]) -> str:
    if risk_level == "low":
        return "温和确认彼此的安排"
    if risk_level == "high":
        return "化解防御，让对方心软并愿意回应"
    if str(signal.get("reaction_type") or "") == "seek_support":
        return "让对方听懂你其实是需要关心"
    return "把真实需求软软表达清楚"


def _suggested_tone(risk_level: str, signal: dict[str, Any]) -> str:
    if risk_level == "low":
        return "保持现在这种温和体贴的口吻"
    if risk_level == "high":
        return "温柔轻软，先体谅辛苦再示弱表达挂念"
    if str(signal.get("reaction_type") or "") == "seek_support":
        return "先体谅垫字，再说内心委屈与需要"
    return "温和诚恳，直接表达感受但不带指责"


def _rewrite_draft(cleaned: str, risk_level: str, signal: dict[str, Any]) -> str:
    if not cleaned:
        return "今天一直没怎么听到你的消息，心里有点空落落的。等你不忙的时候，我们温和地聊聊好不好？"

    if _has_any(cleaned, ABSOLUTE_MARKERS + BLAME_MARKERS + DISENGAGE_MARKERS):
        if _has_any(cleaned, RESPONSE_MARKERS):
            return "知道你今天肯定特别忙。不过一直没等到你回复，我一个人等得有点空落落的，也有点挂念。忙完抽空回我个表情包报个平安好嘛，等你哦~"
        return "刚刚这件事让我心里有点委屈和小失落，怕带着急躁的情绪说话会不小心伤到你。我们都先缓一缓喝口水，晚点心平气和抱抱聊好不好？"

    if risk_level == "low":
        if cleaned.endswith(("吗？", "吗?", "可以吗？", "可以吗?")):
            return cleaned
        if _has_any(cleaned, TIME_WINDOW_MARKERS):
            return f"{cleaned.rstrip('。！？!?')}，可以吗？"
        return cleaned

    if _has_any(cleaned, RESPONSE_MARKERS):
        return "知道你今天肯定特别忙。不过一直没等到你回复，我一个人等得有点空落落的，也有点挂念。忙完抽空回我个表情包报个平安好嘛，等你哦~"
    if str(signal.get("reaction_type") or "") == "withdraw":
        return "我这会儿心里有点小委屈，怕说多了一时冲动。我们都先停一停、歇会儿，晚点心平气和抱抱聊好不好？"
    return "今天一直很挂念你，想把心里的感受软软地跟你说说。等你手头事情忙顺了，我们聊聊天好不好？"


def build_message_preview_baseline(draft: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    del context
    cleaned = _clean_text(draft)
    signal = build_behavior_signal(cleaned, risk_level="none", sentiment_hint=None)
    focus_labels = _focus_labels(cleaned, signal)
    absolute_count = _count_markers(cleaned, ABSOLUTE_MARKERS)
    blame_count = _count_markers(cleaned, BLAME_MARKERS)
    pressure_count = _count_markers(cleaned, PRESSURE_MARKERS)
    soften_count = _count_markers(cleaned, SOFTENING_MARKERS)
    time_window_count = _count_markers(cleaned, TIME_WINDOW_MARKERS)
    disengage_count = _count_markers(cleaned, DISENGAGE_MARKERS)
    exclamation_count = cleaned.count("!") + cleaned.count("！")

    score = 0.0
    if signal["inferred_tone"] == "intense":
        score += 1.1
    if signal["reaction_type"] in {"defend", "urgent"}:
        score += 0.9
    elif signal["reaction_type"] == "withdraw":
        score += 0.5
    score += min(1.75, absolute_count * 0.62 + blame_count * 0.68 + pressure_count * 0.3 + disengage_count * 0.5)
    if absolute_count and cleaned.startswith("你"):
        score += 0.35
    if absolute_count and disengage_count:
        score += 0.55
    score += min(0.45, exclamation_count * 0.18)
    score -= min(1.2, soften_count * 0.32 + time_window_count * 0.22)
    if signal["reaction_type"] in {"clarify", "repair"}:
        score -= 0.28
    score = max(0.0, round(score, 2))

    risk_level = _risk_level_from_score(score)
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
        "markers": round(min(1.75, absolute_count * 0.62 + blame_count * 0.68 + pressure_count * 0.3 + disengage_count * 0.5), 2),
        "softening": round(min(1.2, soften_count * 0.32 + time_window_count * 0.22), 2),
        "punctuation": round(min(0.45, exclamation_count * 0.18), 2),
    }
    if absolute_count and cleaned.startswith("你"):
        score_breakdown["markers"] = round(score_breakdown["markers"] + 0.35, 2)
    if absolute_count and disengage_count:
        score_breakdown["markers"] = round(score_breakdown["markers"] + 0.55, 2)

    payload = {
        "partner_view": _partner_view(risk_level, signal),
        "likely_impact": _likely_impact(risk_level, signal),
        "risk_level": risk_level,
        "risk_reason": _risk_reason(score, cleaned, signal),
        "safer_rewrite": _rewrite_draft(cleaned, risk_level, signal),
        "suggested_tone": _suggested_tone(risk_level, signal),
        "conversation_goal": _conversation_goal(risk_level, signal),
        "algorithm_version": ALGORITHM_VERSION,
        "confidence": confidence,
        "decision_trace": {
            "algorithm_version": ALGORITHM_VERSION,
            "layer": "message_simulation",
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
                "partner_view": _partner_view(risk_level, signal),
                "likely_impact": _likely_impact(risk_level, signal),
                "conversation_goal": _conversation_goal(risk_level, signal),
                "suggested_tone": _suggested_tone(risk_level, signal),
            },
        },
        "focus_labels": focus_labels,
        "risk_score": score,
        "baseline_delta": round(score - 1.0, 2),
        "fallback_reason": None,
        "shadow_result": None,
        "feedback_status": "pending_feedback",
        "do_list": (
            ["先把想确认的事具体说出来", "给对方一个能从容回应的时间窗口"]
            if risk_level == "low"
            else ["先垫一句体谅对方的辛苦", "把内心的委屈和在乎软软说出来"]
            if risk_level == "medium"
            else ["先给个台阶（如随手报个平安就行）", "等彼此都心平气和了再抱抱聊"]
        ),
        "avoid_list": (
            ["不要临时加码旧账", "不要把琐事一下子铺太大"]
            if risk_level == "low"
            else ["千万别发泄说‘我很烦’或用‘你怎么又’", "不要连续夺命追问"]
            if risk_level == "medium"
            else ["不要把‘我需要你’扭曲成攻击指责", "气头上不要逼对方立刻秒回或认错"]
        ),
        "structured_evidence": {
            "risk_score": score,
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
        return "我知道你昨天可能是真的太累了；我这边是因为没等到回应会慌，想先把这件事对齐一下。"
    if "被理解" in pair:
        return "我不是想跟你算账，我是想先把我刚才卡住的点说清楚，看看你听见的是不是同一件事。"
    return "我想先对齐一下，我们刚才各自最在意的到底是什么，不急着分对错。"


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
