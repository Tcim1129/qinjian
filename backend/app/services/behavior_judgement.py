"""Behavior baseline summaries and deviation judgement helpers."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import re
from typing import Any

from app.services.display_labels import sentiment_label, translate_inline_codes
from app.services.privacy_sandbox import redact_sensitive_text, sanitize_event_payload


DEFAULT_BEHAVIOR_SUMMARY: dict[str, Any] = {
    "explicit_preferences": {},
    "sample_size": 0,
    "history_sufficiency": "insufficient",
    "inferred_language_distribution": {},
    "inferred_tone_distribution": {},
    "sentiment_distribution": {},
    "message_length_distribution": {},
    "risk_distribution": {},
    "reaction_distribution": {},
    "common_emotion_tags": [],
    "recent_deviations": [],
    "dominant_language": "unknown",
    "dominant_tone": "neutral",
    "dominant_sentiment": "neutral",
    "dominant_length_bucket": "medium",
    "dominant_risk_level": "none",
    "dominant_reaction_type": "neutral",
    "average_pressure_score": 0.0,
    "average_softening_score": 0.0,
    "average_blame_score": 0.0,
}

POSITIVE_KEYWORDS = [
    "谢谢",
    "辛苦",
    "理解",
    "抱抱",
    "想你",
    "开心",
    "安心",
    "温柔",
    "愿意",
    "靠近",
]
NEGATIVE_KEYWORDS = [
    "烦",
    "生气",
    "愤怒",
    "怎么又",
    "总是",
    "从来",
    "失望",
    "委屈",
    "难过",
    "难受",
    "不回",
    "冷战",
    "分手",
]
EMOTION_RULES = {
    "开心": ["开心", "高兴", "快乐", "轻松"],
    "平静": ["平静", "安心", "稳定", "踏实", "放松"],
    "感动": ["感动", "温柔", "谢谢", "理解我", "被看见"],
    "期待": ["期待", "盼着", "准备", "想要"],
    "焦虑": ["焦虑", "担心", "害怕", "不安", "压力", "紧张"],
    "委屈": ["委屈", "难受", "难过", "没被理解", "心酸", "被忽略"],
    "生气": ["生气", "愤怒", "火大", "气死", "不爽", "烦"],
    "疲惫": ["累", "疲惫", "耗尽", "没力气", "撑不住", "麻木"],
}
EMOTION_TONES = {
    "开心": "positive",
    "平静": "positive",
    "感动": "positive",
    "期待": "positive",
    "焦虑": "negative",
    "委屈": "negative",
    "生气": "negative",
    "疲惫": "negative",
}
NEGATION_PREFIXES = [
    "已经不",
    "不再",
    "不是",
    "并不",
    "不太",
    "没那么",
    "没这么",
    "没有",
    "没",
    "不",
]
INTENSITY_PREFIX_BONUSES = {
    "特别": 0.7,
    "非常": 0.6,
    "真的": 0.45,
    "太": 0.4,
    "很": 0.35,
    "挺": 0.25,
    "好": 0.2,
    "有点": 0.2,
    "一点": 0.1,
    "越来越": 0.35,
}
CONTRAST_PREFIX_BONUSES = {
    "反而": 0.25,
    "而是": 0.2,
    "还是": 0.12,
    "但是": 0.08,
    "不过": 0.08,
    "可是": 0.08,
    "但": 0.05,
    "却": 0.05,
}
TONE_HINTS = {
    "warm": ["谢谢", "辛苦", "抱抱", "理解", "在意", "想和你", "陪陪我"],
    "gentle": ["能不能", "可以吗", "方便的话", "我有点", "我想", "也许", "麻烦"],
    "direct": ["需要", "希望你", "请你", "现在", "今天", "要不要", "先说清楚"],
    "concise": [],
    "intense": ["怎么又", "总是", "从来", "立刻", "马上", "真的很烦", "受够了"],
}
REACTION_HINTS = {
    "withdraw": ["算了", "随便", "不想说", "先这样", "别聊了", "沉默"],
    "defend": ["不是", "我没有", "你误会", "凭什么", "你总是", "怎么又"],
    "seek_support": ["帮帮我", "陪陪我", "安慰", "我很需要", "我想被看见"],
    "clarify": ["我想确认", "我想知道", "先说清楚", "我想对齐", "确认一下"],
    "repair": ["对不起", "抱歉", "我想修复", "谢谢你", "我想靠近"],
    "reflect": ["复盘", "总结", "为什么", "规律", "变化", "回顾"],
    "urgent": ["现在", "立刻", "马上", "赶紧"],
}
ABSOLUTE_MARKERS = ["每次都", "总是", "从来", "永远", "根本"]
PRESSURE_MARKERS = ["立刻", "马上", "赶紧", "现在就", "必须", "一直", "快点"]
BLAME_MARKERS = ["你怎么又", "都是你", "你就不能", "你到底", "凭什么"]
SOFTENING_MARKERS = ["我想", "我有点", "可以吗", "方便的话", "等你有空", "确认一下", "想和你聊"]
TIME_WINDOW_MARKERS = ["有空", "方便", "十分钟", "忙完", "晚点", "之后", "什么时候"]
RISK_ORDER = {
    "none": 0,
    "low": 1,
    "watch": 2,
    "medium": 3,
    "high": 4,
    "severe": 5,
}
MATCH_LABELS = {
    "match": "符合基线",
    "slight_deviation": "轻微偏离",
    "strong_deviation": "明显异常",
    "insufficient_history": "样本不足",
}


def _clean_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _preview(text: str | None, limit: int = 80) -> str | None:
    cleaned = _clean_text(text)
    if not cleaned:
        return None
    if len(cleaned) <= limit:
        return redact_sensitive_text(cleaned)
    return redact_sensitive_text(f"{cleaned[: limit - 1]}…")


def _marker_count(text: str | None, markers: list[str]) -> int:
    cleaned = _clean_text(text)
    return sum(cleaned.count(marker) for marker in markers if marker)


def normalize_risk_level(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in RISK_ORDER:
        return normalized
    if normalized == "moderate":
        return "medium"
    return "none"


def infer_language(text: str | None) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return "unknown"
    chinese_count = len(re.findall(r"[\u4e00-\u9fff]", cleaned))
    ascii_count = len(re.findall(r"[A-Za-z]", cleaned))
    if chinese_count >= 2 and ascii_count >= 4:
        return "mixed"
    if chinese_count >= max(2, ascii_count * 2):
        return "zh"
    if ascii_count >= max(4, chinese_count * 2):
        return "en"
    if chinese_count and ascii_count:
        return "mixed"
    if chinese_count:
        return "zh"
    if ascii_count:
        return "en"
    return "unknown"


def infer_message_length_bucket(text: str | None) -> str:
    length = len(_clean_text(text))
    if length <= 32:
        return "short"
    if length <= 120:
        return "medium"
    return "long"


def _iter_keyword_positions(cleaned: str, keyword: str):
    start = 0
    while keyword:
        index = cleaned.find(keyword, start)
        if index < 0:
            break
        yield index
        start = index + len(keyword)


def _is_negated_occurrence(cleaned: str, start: int) -> bool:
    prefix = cleaned[max(0, start - 6): start].replace(" ", "")
    return any(prefix.endswith(marker) for marker in NEGATION_PREFIXES)


def _prefix_bonus(cleaned: str, start: int, mapping: dict[str, float]) -> float:
    prefix = cleaned[max(0, start - 6): start].replace(" ", "")
    bonuses = [
        bonus
        for marker, bonus in mapping.items()
        if prefix.endswith(marker) or marker in prefix[-4:]
    ]
    return max(bonuses, default=0.0)


def _weighted_keyword_score(cleaned: str, keyword: str) -> float:
    total = 0.0
    for start in _iter_keyword_positions(cleaned, keyword):
        if _is_negated_occurrence(cleaned, start):
            continue
        total += 1.0
        total += _prefix_bonus(cleaned, start, INTENSITY_PREFIX_BONUSES)
        total += _prefix_bonus(cleaned, start, CONTRAST_PREFIX_BONUSES)
    return round(total, 2)


def _emotion_matches(text: str | None) -> list[dict[str, Any]]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []

    matches: list[dict[str, Any]] = []
    for index, (tag, keywords) in enumerate(EMOTION_RULES.items()):
        score = round(sum(_weighted_keyword_score(cleaned, keyword) for keyword in keywords), 2)
        if score <= 0:
            continue
        matches.append(
            {
                "tag": tag,
                "score": score,
                "tone": EMOTION_TONES.get(tag, "neutral"),
                "index": index,
            }
        )
    return matches


def _sentiment_from_emotion_matches(matches: list[dict[str, Any]]) -> str:
    positive = sum(float(item["score"]) for item in matches if item.get("tone") == "positive")
    negative = sum(float(item["score"]) for item in matches if item.get("tone") == "negative")
    if negative > positive:
        return "negative"
    if positive > negative:
        return "positive"
    if matches:
        top_match = max(
            matches,
            key=lambda item: (float(item.get("score") or 0.0), -int(item.get("index") or 0)),
        )
        top_tone = str(top_match.get("tone") or "neutral")
        if top_tone in {"positive", "negative"}:
            return top_tone
    return "neutral"


def _sort_emotion_matches(
    matches: list[dict[str, Any]],
    dominant_sentiment: str,
) -> list[dict[str, Any]]:
    def priority(item: dict[str, Any]) -> tuple[int, int, int]:
        tone = str(item.get("tone") or "neutral")
        if dominant_sentiment in {"positive", "negative"}:
            tone_priority = 0 if tone == dominant_sentiment else 1
        else:
            tone_priority = 0
        return (tone_priority, -int(item.get("score") or 0), int(item.get("index") or 0))

    return sorted(matches, key=priority)


def detect_emotion_tags(text: str | None) -> list[str]:
    matches = _emotion_matches(text)
    if not matches:
        return []
    dominant_sentiment = _sentiment_from_emotion_matches(matches)
    return [item["tag"] for item in _sort_emotion_matches(matches, dominant_sentiment)[:3]]


def _emotion_tags_from_weights(weights: list[dict[str, Any]]) -> list[str]:
    tags: list[str] = []
    for item in weights:
        tag = str(item.get("tag") or "").strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def _emotion_blend_summary(
    primary_mood: str | None,
    secondary_moods: list[str],
    sentiment: str,
) -> str:
    if primary_mood and secondary_moods:
        return f"这不是单一情绪，更像是{primary_mood}里夹着{'、'.join(secondary_moods[:2])}。"
    if primary_mood:
        return f"当前最明显的是{primary_mood}，系统会继续留意是否还有别的情绪线索。"
    if sentiment == "negative":
        return "暂时没有稳定标签，但整体更像带着压力或不舒服。"
    if sentiment == "positive":
        return "暂时没有稳定标签，但整体更像带着靠近或修复的意愿。"
    return "暂时没有明显情绪词，先按平静或日常表达理解。"


def infer_sentiment(text: str | None, sentiment_hint: Any = None) -> str:
    hinted = str(sentiment_hint or "").strip().lower()
    if hinted in {"positive", "negative", "neutral"}:
        return hinted

    cleaned = _clean_text(text)
    emotion_sentiment = _sentiment_from_emotion_matches(_emotion_matches(cleaned))
    if emotion_sentiment != "neutral":
        return emotion_sentiment
    positive = sum(_weighted_keyword_score(cleaned, keyword) for keyword in POSITIVE_KEYWORDS)
    negative = sum(_weighted_keyword_score(cleaned, keyword) for keyword in NEGATIVE_KEYWORDS)
    if negative > positive:
        return "negative"
    if positive > negative:
        return "positive"
    return "neutral"


def summarize_text_emotion(text: str | None) -> dict[str, Any]:
    cleaned = _clean_text(text)
    if not cleaned:
        emotion_blend_summary = "先留下一句原话，系统再帮你判断情绪线索。"
        return {
            "sentiment": "neutral",
            "sentiment_label": sentiment_label("neutral"),
            "mood_tags": [],
            "display_mood_tags": [],
            "mood_label": "等你开口",
            "primary_mood": "等你开口",
            "secondary_moods": [],
            "emotion_weights": [],
            "emotion_blend_summary": emotion_blend_summary,
            "emotion_profile": {
                "all_mood_tags": [],
                "emotion_weights": [],
                "confidence": 0.0,
                "blend_summary": emotion_blend_summary,
            },
            "score": 0,
            "confidence": 0.0,
            "reason": emotion_blend_summary,
        }

    matches = _emotion_matches(cleaned)
    sentiment = _sentiment_from_emotion_matches(matches)
    if sentiment == "neutral":
        sentiment = infer_sentiment(cleaned, None)

    sorted_matches = _sort_emotion_matches(matches, sentiment)
    mood_tags = [item["tag"] for item in sorted_matches[:3]]
    primary_mood = mood_tags[0] if mood_tags else None
    secondary_moods = mood_tags[1:]
    mood_label = mood_tags[0] if mood_tags else (
        "有压力" if sentiment == "negative" else "有修复感" if sentiment == "positive" else "平静"
    )
    top_score = float(sorted_matches[0]["score"]) if sorted_matches else 0.0
    confidence = (
        min(0.95, 0.55 + top_score * 0.16 + len(mood_tags) * 0.08)
        if sorted_matches
        else 0.35
    )
    score = (
        max(
            1,
            min(
                10,
                4
                + int(round(top_score))
                + max(0, len(mood_tags) - 1)
                + (1 if sentiment == "negative" else 2 if sentiment == "positive" else 0),
            ),
        )
        if cleaned
        else 0
    )
    emotion_weights = [
        {
            "tag": item["tag"],
            "score": round(float(item["score"]), 2),
            "tone": item["tone"],
        }
        for item in sorted_matches
    ]
    display_mood_tags = mood_tags[:3]
    emotion_blend_summary = _emotion_blend_summary(primary_mood, secondary_moods, sentiment)
    all_mood_tags = _emotion_tags_from_weights(emotion_weights)

    return {
        "sentiment": sentiment,
        "sentiment_label": sentiment_label(sentiment),
        "mood_tags": mood_tags,
        "display_mood_tags": display_mood_tags,
        "mood_label": mood_label,
        "primary_mood": primary_mood or mood_label,
        "secondary_moods": secondary_moods,
        "emotion_weights": emotion_weights,
        "emotion_blend_summary": emotion_blend_summary,
        "user_facing": {
            "display_mood_tags": display_mood_tags,
            "blend_summary": emotion_blend_summary,
        },
        "emotion_profile": {
            "all_mood_tags": all_mood_tags,
            "primary_mood": primary_mood or mood_label,
            "secondary_moods": secondary_moods,
            "emotion_weights": emotion_weights,
            "confidence": round(float(confidence), 2),
            "blend_summary": emotion_blend_summary,
        },
        "score": int(score),
        "confidence": round(float(confidence), 2),
        "reason": emotion_blend_summary,
    }


def infer_tone(text: str | None) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return "neutral"

    if any(keyword in cleaned for keyword in TONE_HINTS["intense"]):
        return "intense"
    if any(keyword in cleaned for keyword in TONE_HINTS["warm"]):
        return "warm"
    if any(keyword in cleaned for keyword in TONE_HINTS["gentle"]):
        return "gentle"
    if len(cleaned) <= 18 or cleaned.count("。") + cleaned.count("!") + cleaned.count("！") <= 1:
        return "concise"
    if any(keyword in cleaned for keyword in TONE_HINTS["direct"]):
        return "direct"
    return "neutral"


def infer_reaction_type(text: str | None) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return "neutral"

    for reaction_type in (
        "withdraw",
        "defend",
        "seek_support",
        "repair",
        "clarify",
        "reflect",
        "urgent",
    ):
        if any(keyword in cleaned for keyword in REACTION_HINTS[reaction_type]):
            return reaction_type
    return "neutral"


def infer_relationship_signal(
    *,
    risk_level: str,
    inferred_tone: str,
    reaction_type: str,
) -> str:
    if risk_level in {"high", "severe"}:
        return "protective_pause"
    if inferred_tone == "intense" or reaction_type in {"defend", "urgent"}:
        return "lower_stimulation_first"
    if reaction_type == "withdraw":
        return "slow_down_and_reopen"
    if reaction_type in {"repair", "clarify"}:
        return "safe_to_align"
    if reaction_type == "seek_support":
        return "needs_supportive_response"
    return "steady_check_in"


def build_behavior_signal(
    text: str | None,
    *,
    risk_level: Any = None,
    sentiment_hint: Any = None,
) -> dict[str, Any]:
    normalized_risk = normalize_risk_level(risk_level)
    inferred_tone = infer_tone(text)
    reaction_type = infer_reaction_type(text)
    sentiment = infer_sentiment(text, sentiment_hint)
    signal = {
        "text_preview": _preview(text),
        "inferred_language": infer_language(text),
        "inferred_tone": inferred_tone,
        "message_length_bucket": infer_message_length_bucket(text),
        "sentiment_hint": sentiment,
        "emotion_tags": detect_emotion_tags(text),
        "reaction_type": reaction_type,
        "risk_level": normalized_risk,
        "relationship_signal": infer_relationship_signal(
            risk_level=normalized_risk,
            inferred_tone=inferred_tone,
            reaction_type=reaction_type,
        ),
        "pressure_score": _marker_count(text, PRESSURE_MARKERS)
        + (_clean_text(text).count("!") + _clean_text(text).count("！")),
        "softening_score": _marker_count(text, SOFTENING_MARKERS)
        + _marker_count(text, TIME_WINDOW_MARKERS),
        "blame_score": _marker_count(text, BLAME_MARKERS)
        + _marker_count(text, ABSOLUTE_MARKERS),
        "deviation_candidate": normalized_risk in {"watch", "medium", "high", "severe"}
        or inferred_tone == "intense"
        or reaction_type in {"defend", "withdraw", "urgent"},
    }
    return signal


def _share(counter: Counter[str]) -> dict[str, float]:
    total = sum(counter.values())
    if total <= 0:
        return {}
    return {
        key: round(value / total, 4)
        for key, value in counter.most_common()
    }


def _top_keys(distribution: dict[str, float], limit: int = 2) -> list[str]:
    return [key for key, _value in sorted(distribution.items(), key=lambda item: item[1], reverse=True)[:limit]]


def _distribution_rarity(current: str, distribution: dict[str, float], *, default: float = 0.6) -> float:
    if not distribution:
        return default
    share = float(distribution.get(current) or 0.0)
    if share <= 0:
        return default
    return round(1 - share, 4)


def _history_sufficiency(sample_size: int) -> str:
    if sample_size >= 8:
        return "sufficient"
    if sample_size >= 4:
        return "limited"
    return "insufficient"


def label_baseline_match(value: str) -> str:
    return MATCH_LABELS.get(value, MATCH_LABELS["insufficient_history"])


def make_behavior_observation(
    *,
    source: str,
    event_type: str,
    text: str | None,
    occurred_at: datetime | str | None = None,
    risk_level: Any = None,
    sentiment_hint: Any = None,
    judgement: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "event_type": event_type,
        "occurred_at": (
            occurred_at.isoformat()
            if isinstance(occurred_at, datetime)
            else str(occurred_at)
            if occurred_at
            else None
        ),
        "signal": build_behavior_signal(
            text,
            risk_level=risk_level,
            sentiment_hint=sentiment_hint,
        ),
        "judgement": judgement or {},
        "metadata": metadata or {},
    }


def observation_from_payload(
    *,
    source: str,
    event_type: str,
    payload: dict[str, Any] | None,
    occurred_at: datetime | str | None = None,
) -> dict[str, Any] | None:
    content = payload or {}
    text = (
        content.get("draft")
        or content.get("content")
        or content.get("summary")
        or content.get("shared_story")
        or content.get("suggested_opening")
        or content.get("safer_rewrite")
    )
    if not text and not content:
        return None

    signal = {
        "text_preview": _preview(text),
        "inferred_language": str(content.get("inferred_language") or infer_language(text)),
        "inferred_tone": str(content.get("inferred_tone") or infer_tone(text)),
        "message_length_bucket": str(
            content.get("message_length_bucket") or infer_message_length_bucket(text)
        ),
        "sentiment_hint": str(
            content.get("sentiment_hint") or infer_sentiment(text, None)
        ),
        "emotion_tags": list(content.get("emotion_tags") or detect_emotion_tags(text)),
        "reaction_type": str(content.get("reaction_type") or infer_reaction_type(text)),
        "risk_level": normalize_risk_level(content.get("risk_level")),
        "relationship_signal": str(
            content.get("relationship_signal")
            or infer_relationship_signal(
                risk_level=normalize_risk_level(content.get("risk_level")),
                inferred_tone=str(content.get("inferred_tone") or infer_tone(text)),
                reaction_type=str(content.get("reaction_type") or infer_reaction_type(text)),
            )
        ),
        "pressure_score": int(
            content.get("pressure_score")
            or _marker_count(text, PRESSURE_MARKERS)
            + (_clean_text(text).count("!") + _clean_text(text).count("！"))
        ),
        "softening_score": int(
            content.get("softening_score")
            or _marker_count(text, SOFTENING_MARKERS) + _marker_count(text, TIME_WINDOW_MARKERS)
        ),
        "blame_score": int(
            content.get("blame_score")
            or _marker_count(text, BLAME_MARKERS) + _marker_count(text, ABSOLUTE_MARKERS)
        ),
        "deviation_candidate": bool(
            content.get("deviation_candidate")
            or str(content.get("baseline_match") or "") not in {"", "match", "insufficient_history"}
        ),
    }
    return {
        "source": source,
        "event_type": event_type,
        "occurred_at": (
            occurred_at.isoformat()
            if isinstance(occurred_at, datetime)
            else str(occurred_at)
            if occurred_at
            else None
        ),
        "signal": signal,
        "judgement": {
            "baseline_match": content.get("baseline_match"),
            "deviation_score": content.get("deviation_score"),
            "deviation_reasons": list(content.get("deviation_reasons") or []),
            "reaction_shift": content.get("reaction_shift"),
            "history_sufficiency": content.get("history_sufficiency"),
        },
        "metadata": {},
    }


def summarize_behavior_profile(
    observations: list[dict[str, Any]],
    *,
    explicit_preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not observations:
        summary = dict(DEFAULT_BEHAVIOR_SUMMARY)
        summary["explicit_preferences"] = explicit_preferences or {}
        return summary

    language_counter: Counter[str] = Counter()
    tone_counter: Counter[str] = Counter()
    sentiment_counter: Counter[str] = Counter()
    length_counter: Counter[str] = Counter()
    risk_counter: Counter[str] = Counter()
    reaction_counter: Counter[str] = Counter()
    emotion_counter: Counter[str] = Counter()
    recent_deviations: list[dict[str, Any]] = []
    pressure_total = 0
    softening_total = 0
    blame_total = 0

    for observation in observations:
        signal = observation.get("signal") or {}
        language_counter[str(signal.get("inferred_language") or "unknown")] += 1
        tone_counter[str(signal.get("inferred_tone") or "neutral")] += 1
        sentiment_counter[str(signal.get("sentiment_hint") or "neutral")] += 1
        length_counter[str(signal.get("message_length_bucket") or "medium")] += 1
        risk_counter[normalize_risk_level(signal.get("risk_level"))] += 1
        reaction_counter[str(signal.get("reaction_type") or "neutral")] += 1
        emotion_counter.update(str(tag) for tag in signal.get("emotion_tags") or [])
        pressure_total += int(signal.get("pressure_score") or 0)
        softening_total += int(signal.get("softening_score") or 0)
        blame_total += int(signal.get("blame_score") or 0)

        judgement = observation.get("judgement") or {}
        baseline_match = str(judgement.get("baseline_match") or "").strip()
        if baseline_match and baseline_match not in {"match", "insufficient_history"}:
            recent_deviations.append(
                {
                    "event_type": observation.get("event_type"),
                    "occurred_at": observation.get("occurred_at"),
                    "baseline_match": baseline_match,
                    "baseline_match_label": label_baseline_match(baseline_match),
                    "reaction_shift": judgement.get("reaction_shift"),
                    "deviation_reasons": list(judgement.get("deviation_reasons") or [])[:3],
                    "summary": signal.get("text_preview"),
                }
            )

    sample_size = len(observations)
    history_sufficiency = _history_sufficiency(sample_size)
    recent_deviations.sort(
        key=lambda item: str(item.get("occurred_at") or ""),
        reverse=True,
    )

    inferred_language_distribution = _share(language_counter)
    inferred_tone_distribution = _share(tone_counter)
    sentiment_distribution = _share(sentiment_counter)
    message_length_distribution = _share(length_counter)
    risk_distribution = _share(risk_counter)
    reaction_distribution = _share(reaction_counter)

    return {
        "explicit_preferences": explicit_preferences or {},
        "sample_size": sample_size,
        "history_sufficiency": history_sufficiency,
        "inferred_language_distribution": inferred_language_distribution,
        "inferred_tone_distribution": inferred_tone_distribution,
        "sentiment_distribution": sentiment_distribution,
        "message_length_distribution": message_length_distribution,
        "risk_distribution": risk_distribution,
        "reaction_distribution": reaction_distribution,
        "common_emotion_tags": [
            {"tag": tag, "count": count}
            for tag, count in emotion_counter.most_common(5)
        ],
        "recent_deviations": recent_deviations[:5],
        "dominant_language": next(iter(inferred_language_distribution), "unknown"),
        "dominant_tone": next(iter(inferred_tone_distribution), "neutral"),
        "dominant_sentiment": next(iter(sentiment_distribution), "neutral"),
        "dominant_length_bucket": next(iter(message_length_distribution), "medium"),
        "dominant_risk_level": next(iter(risk_distribution), "none"),
        "dominant_reaction_type": next(iter(reaction_distribution), "neutral"),
        "average_pressure_score": round(pressure_total / sample_size, 2),
        "average_softening_score": round(softening_total / sample_size, 2),
        "average_blame_score": round(blame_total / sample_size, 2),
    }


def _build_deviation_reasons(
    current_signal: dict[str, Any],
    baseline_summary: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []

    dominant_language = str(baseline_summary.get("dominant_language") or "unknown")
    if (
        dominant_language not in {"unknown", ""}
        and current_signal["inferred_language"] not in {"unknown", dominant_language}
    ):
        reasons.append(f"本次语言切到了 {current_signal['inferred_language']}，和平时主语言不一样")

    tone_distribution = baseline_summary.get("inferred_tone_distribution") or {}
    tone_pair = {current_signal["inferred_tone"], str(baseline_summary.get("dominant_tone") or "neutral")}
    if (
        current_signal["inferred_tone"] not in _top_keys(tone_distribution)
        and tone_pair != {"warm", "gentle"}
    ):
        reasons.append(f"本次语气更像 {current_signal['inferred_tone']}，和平时表达习惯不同")

    dominant_length = str(baseline_summary.get("dominant_length_bucket") or "medium")
    length_distribution = baseline_summary.get("message_length_distribution") or {}
    dominant_length_share = float(length_distribution.get(dominant_length) or 0.0)
    length_pair = {current_signal["message_length_bucket"], dominant_length}
    if (
        current_signal["message_length_bucket"] != dominant_length
        and dominant_length_share >= 0.8
        and length_pair != {"short", "medium"}
    ):
        reasons.append(
            f"本次表达长度偏 {current_signal['message_length_bucket']}，不同于常见的 {dominant_length}"
        )

    dominant_risk = normalize_risk_level(baseline_summary.get("dominant_risk_level"))
    if RISK_ORDER[current_signal["risk_level"]] - RISK_ORDER[dominant_risk] >= 2:
        reasons.append("这次风险/刺激性明显高于平时")

    dominant_reaction = str(baseline_summary.get("dominant_reaction_type") or "neutral")
    if current_signal["reaction_type"] not in {"neutral", dominant_reaction}:
        reasons.append(
            f"这次反应更像 {current_signal['reaction_type']}，和平时常见的 {dominant_reaction} 不同"
        )

    dominant_sentiment = str(baseline_summary.get("dominant_sentiment") or "neutral")
    if current_signal["sentiment_hint"] not in {"neutral", dominant_sentiment}:
        reasons.append("这次情绪倾向和近期常态不太一样")

    average_pressure_score = float(baseline_summary.get("average_pressure_score") or 0.0)
    if current_signal.get("pressure_score", 0) - average_pressure_score >= 2:
        reasons.append("这次说话里的催促感或压迫感，比平时更重")

    average_blame_score = float(baseline_summary.get("average_blame_score") or 0.0)
    if current_signal.get("blame_score", 0) - average_blame_score >= 1:
        reasons.append("这次更容易被听成在责怪对方，而不是在说明自己")

    average_softening_score = float(baseline_summary.get("average_softening_score") or 0.0)
    if average_softening_score >= 1.5 and current_signal.get("softening_score", 0) == 0:
        reasons.append("这次少了平时常见的缓冲和留余地，说法会更硬一些")

    deduped: list[str] = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)
    return [translate_inline_codes(item) for item in deduped[:4]]


def _reaction_shift(current_reaction: str, dominant_reaction: str) -> str:
    if current_reaction in {"", "neutral"} or current_reaction == dominant_reaction:
        return "stable"
    return {
        "defend": "more_defensive",
        "withdraw": "more_withdrawn",
        "urgent": "more_urgent",
        "repair": "more_repair_oriented",
        "seek_support": "more_support_seeking",
        "clarify": "more_clarifying",
        "reflect": "more_reflective",
    }.get(current_reaction, "shifted")


def judge_behavior_against_baseline(
    text: str | None,
    *,
    baseline_summary: dict[str, Any] | None,
    explicit_preferences: dict[str, Any] | None = None,
    risk_level: Any = None,
    sentiment_hint: Any = None,
) -> dict[str, Any]:
    current_signal = build_behavior_signal(
        text,
        risk_level=risk_level,
        sentiment_hint=sentiment_hint,
    )
    baseline = baseline_summary or dict(DEFAULT_BEHAVIOR_SUMMARY)
    history_sufficiency = str(
        baseline.get("history_sufficiency") or DEFAULT_BEHAVIOR_SUMMARY["history_sufficiency"]
    )

    if history_sufficiency == "insufficient":
        return {
            "current_signal": current_signal,
            "baseline_match": "insufficient_history",
            "baseline_match_label": label_baseline_match("insufficient_history"),
            "deviation_score": 0.0,
            "deviation_reasons": [],
            "reaction_shift": "unknown",
            "relationship_signal": current_signal["relationship_signal"],
            "history_sufficiency": history_sufficiency,
            "explicit_preferences": explicit_preferences or {},
        }

    reasons = _build_deviation_reasons(current_signal, baseline)
    tone_rarity = _distribution_rarity(
        current_signal["inferred_tone"],
        baseline.get("inferred_tone_distribution") or {},
    )
    reaction_rarity = _distribution_rarity(
        current_signal["reaction_type"],
        baseline.get("reaction_distribution") or {},
    )
    sentiment_rarity = _distribution_rarity(
        current_signal["sentiment_hint"],
        baseline.get("sentiment_distribution") or {},
        default=0.45,
    )
    length_rarity = _distribution_rarity(
        current_signal["message_length_bucket"],
        baseline.get("message_length_distribution") or {},
        default=0.35,
    )
    dominant_risk = normalize_risk_level(baseline.get("dominant_risk_level"))
    risk_delta = max(
        0,
        RISK_ORDER[current_signal["risk_level"]] - RISK_ORDER[dominant_risk],
    )
    pressure_delta = max(
        0.0,
        float(current_signal.get("pressure_score") or 0)
        - float(baseline.get("average_pressure_score") or 0.0),
    )
    blame_delta = max(
        0.0,
        float(current_signal.get("blame_score") or 0)
        - float(baseline.get("average_blame_score") or 0.0),
    )
    softening_gap = max(
        0.0,
        float(baseline.get("average_softening_score") or 0.0)
        - float(current_signal.get("softening_score") or 0),
    )
    deviation_score = min(
        1.0,
        round(
            tone_rarity * 0.2
            + reaction_rarity * 0.18
            + sentiment_rarity * 0.1
            + length_rarity * 0.08
            + min(0.22, risk_delta * 0.07)
            + min(0.18, pressure_delta * 0.05)
            + min(0.16, blame_delta * 0.07)
            + min(0.08, softening_gap * 0.03)
            + (0.12 if current_signal["inferred_tone"] == "intense" else 0.0)
            + (0.08 if current_signal["reaction_type"] in {"withdraw", "defend", "urgent"} else 0.0),
            2,
        ),
    )

    if not reasons:
        baseline_match = "match"
    elif deviation_score >= 0.58 or len(reasons) >= 4:
        baseline_match = "strong_deviation"
    else:
        baseline_match = "slight_deviation"

    reaction_shift = _reaction_shift(
        current_signal["reaction_type"],
        str(baseline.get("dominant_reaction_type") or "neutral"),
    )

    return {
        "current_signal": current_signal,
        "baseline_match": baseline_match,
        "baseline_match_label": label_baseline_match(baseline_match),
        "deviation_score": deviation_score,
        "deviation_reasons": reasons,
        "reaction_shift": reaction_shift,
        "relationship_signal": current_signal["relationship_signal"],
        "history_sufficiency": history_sufficiency,
        "explicit_preferences": explicit_preferences or {},
    }


def apply_judgement_to_payload(
    payload: dict[str, Any] | None,
    *,
    text: str | None = None,
    risk_level: Any = None,
    sentiment_hint: Any = None,
    judgement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged = dict(payload or {})
    current_signal = (judgement or {}).get("current_signal") or build_behavior_signal(
        text,
        risk_level=risk_level or merged.get("risk_level"),
        sentiment_hint=sentiment_hint or merged.get("sentiment_hint"),
    )
    merged.update(current_signal)
    if judgement:
        merged.update(
            {
                "baseline_match": judgement.get("baseline_match"),
                "baseline_match_label": judgement.get("baseline_match_label"),
                "deviation_score": judgement.get("deviation_score"),
                "deviation_reasons": judgement.get("deviation_reasons") or [],
                "reaction_shift": judgement.get("reaction_shift"),
                "history_sufficiency": judgement.get("history_sufficiency"),
            }
        )
    return sanitize_event_payload(merged) or {}
