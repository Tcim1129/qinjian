"""Dual-view narrative alignment helper."""

import asyncio
import json
import logging

from app.ai import chat_completion
from app.ai.policy import compose_relationship_system_prompt
from app.core.config import settings
from app.services.relationship_algorithms import build_alignment_baseline

logger = logging.getLogger(__name__)

# Dual-view alignment prompts are longer than chat prompts and need more headroom
# to avoid dropping into fallback content during normal provider latency spikes.
ALIGNMENT_TIMEOUT_SECONDS = 20


ALIGNMENT_SYSTEM_PROMPT = compose_relationship_system_prompt("""你是亲健平台的关系编辑台分析器。你的任务不是判断谁对谁错，而是把双方对同一天或同一阶段的描述，整理成“共同版本 + 错位点 + 对齐动作”。

请保持克制、具体、可执行，不要夸大风险，不要写成空泛鸡汤。严格输出 JSON。"""
)


ALIGNMENT_PROMPT = """请根据以下关系上下文、双方记录和结构化判断，生成一份“双视角叙事对齐”结果。

【关系上下文】
{context_json}

【A方记录】
{checkin_a_json}

【B方记录】
{checkin_b_json}

【结构化判断（请以此为边界，不要和这些信号相反）】
{evidence_json}

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


def _fallback_payload(base_payload: dict, raw_error: str | None = None) -> dict:
    payload = dict(base_payload)
    payload["source"] = "fallback"
    payload["is_fallback"] = True
    payload.setdefault("fallback_reason", None)
    payload.setdefault("shadow_result", None)
    if raw_error:
        payload["raw_error"] = raw_error
        payload["fallback_reason"] = raw_error
    return payload


def _parse_json(text: str, fallback: dict) -> dict:
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        fallback["raw_response"] = text
        return fallback
    if not isinstance(parsed, dict):
        fallback["raw_response"] = text
        return fallback
    parsed.setdefault("source", "ai")
    parsed.setdefault("is_fallback", False)
    return parsed


def _clean_string(value: object, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned[:limit]


def _clean_list(value: object, *, limit: int = 3, item_limit: int = 40) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    for item in value:
        text = _clean_string(item, item_limit)
        if text and text not in cleaned:
            cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def _merged_score(ai_value: object, fallback_score: int) -> int:
    try:
        ai_score = int(ai_value)
    except (TypeError, ValueError):
        return fallback_score
    ai_score = max(0, min(100, ai_score))
    return max(fallback_score - 15, min(fallback_score + 15, ai_score))


def _merge_alignment_payload(candidate: dict, fallback: dict) -> dict:
    merged = dict(fallback)
    for field, limit in (
        ("shared_story", 80),
        ("view_a_summary", 60),
        ("view_b_summary", 60),
        ("misread_risk", 60),
        ("suggested_opening", 80),
        ("coach_note", 60),
    ):
        value = _clean_string(candidate.get(field), limit)
        if value:
            merged[field] = value

    for field in ("divergence_points", "bridge_actions"):
        values = _clean_list(candidate.get(field))
        if values:
            merged[field] = values

    merged["alignment_score"] = _merged_score(
        candidate.get("alignment_score"),
        int(fallback.get("alignment_score") or 0),
    )
    for field in (
        "algorithm_version",
        "confidence",
        "decision_trace",
        "focus_labels",
        "risk_score",
        "baseline_delta",
        "fallback_reason",
        "shadow_result",
        "feedback_status",
    ):
        if candidate.get(field) is not None:
            merged[field] = candidate.get(field)
    merged["source"] = "ai"
    merged["is_fallback"] = False
    merged.pop("raw_error", None)
    return merged


async def generate_narrative_alignment(
    *,
    context: dict,
    checkin_a: dict,
    checkin_b: dict,
) -> dict:
    base_payload = build_alignment_baseline(
        context=context,
        checkin_a=checkin_a,
        checkin_b=checkin_b,
    )
    base_payload.setdefault("fallback_reason", None)
    base_payload.setdefault("shadow_result", None)
    prompt = ALIGNMENT_PROMPT.format(
        context_json=json.dumps(context, ensure_ascii=False),
        checkin_a_json=json.dumps(checkin_a, ensure_ascii=False),
        checkin_b_json=json.dumps(checkin_b, ensure_ascii=False),
        evidence_json=json.dumps(base_payload.get("structured_evidence") or {}, ensure_ascii=False),
    )
    messages = [
        {"role": "system", "content": ALIGNMENT_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    try:
        result = await asyncio.wait_for(
            chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.35),
            timeout=ALIGNMENT_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.warning(
            "narrative alignment generation failed, using fallback: %s",
            exc.__class__.__name__,
        )
        return _fallback_payload(base_payload, raw_error=exc.__class__.__name__)

    parsed = _parse_json(result, _fallback_payload(base_payload))
    if parsed.get("is_fallback"):
        return parsed
    merged = _merge_alignment_payload(parsed, base_payload)
    merged["shadow_result"] = base_payload
    return merged
