"""Message simulation helpers for pre-send relationship coaching."""

import asyncio
import json

from app.ai import chat_completion
from app.ai.policy import compose_relationship_system_prompt
from app.core.config import settings
from app.services.display_labels import risk_level_label, translate_inline_codes
from app.services.relationship_algorithms import build_message_preview_baseline

# Frontend AI requests are capped at 60s; surface timeout before the client aborts.
SIMULATION_TIMEOUT_SECONDS = 55


SIMULATION_SYSTEM_PROMPT = compose_relationship_system_prompt("""你负责亲健的“发前看看”功能，帮助用户检查准备发出的消息，并提供可供选择的改写。
保留原话中的事实、感受、请求和明确边界，使用日常说话的语气。不要替用户示弱、撒娇或讨好，也不要把所有不满解释成缺少安全感。
只根据提供的记录作判断。不能编造对方很忙、很辛苦等背景，也不能断言对方的想法或保证改写后会得到回应。
指出具体措辞可能造成的误解，并说明这只是可能性。原话已经清楚、合适时，可以保留原意，不必强行改写。
遵守结构化判断给出的风险边界，遇到威胁、控制或伤害风险时，不用委婉措辞掩盖问题。
严格按指定字段输出 JSON。"""
)


SIMULATION_PROMPT = """请检查下面这条待发送消息，说明可能的误解，并给出自然、清楚的表达建议。

【关系上下文】
{context_json}

【用户准备发出的原话】
{draft}

【结构化判断（以此为边界，不夸大低风险，也不淡化高风险）】
{evidence_json}

请输出 JSON，不要包含其他文字：
{{
  "partner_view": "对方可能怎样理解这句话；信息不足时说明无法判断（40字内）",
  "likely_impact": "这句话可能怎样影响接下来的交流，不预测必然结果（50字内）",
  "risk_level": "low/medium/high",
  "risk_reason": "结合原话中的具体措辞解释风险（50字内）",
  "safer_rewrite": "保留事实、感受、请求和边界，用用户平时说话的方式改写，不添加未经提供的背景（120字内）",
  "suggested_tone": "适合这次交流的语气，例如平静、直接、友好",
  "conversation_goal": "根据原话可以确认的交流目的（30字内）",
  "do_list": ["一条具体的表达建议", "另一条具体的表达建议"],
  "avoid_list": ["一种需要避免的表达方式", "另一种需要避免的表达方式"]
}}"""


class MessageSimulationUnavailableError(RuntimeError):
    """No usable model result. Never replace it with a canned expression."""


def _parse_json(text: str) -> dict:
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError()
        return parsed
    except (ValueError, IndexError, AttributeError, TypeError) as exc:
        raise MessageSimulationUnavailableError("这次没能整理出完整建议，请重试。") from exc


def _clean_string(value: object, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned[:limit]


def _clean_list(value: object, *, limit: int = 2, item_limit: int = 24) -> list[str]:
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


def _merge_risk_level(ai_value: object, baseline_value: str) -> str:
    ai_level = str(ai_value or "").strip().lower()
    if ai_level not in {"low", "medium", "high", "severe"}:
        return baseline_value
    return ai_level if {"low": 1, "medium": 2, "high": 3, "severe": 4}[ai_level] >= {"low": 1, "medium": 2, "high": 3}[baseline_value] else baseline_value


def _merge_preview_payload(candidate: dict, baseline: dict, draft: str) -> dict:
    # Rules supply risk/evidence metadata, not replacement model prose.
    merged = dict(baseline)
    for field, limit in (
        ("partner_view", 40),
        ("likely_impact", 50),
        ("risk_reason", 50),
        ("safer_rewrite", 120),
        ("suggested_tone", 32),
        ("conversation_goal", 30),
    ):
        value = _clean_string(candidate.get(field), limit)
        if not value:
            raise MessageSimulationUnavailableError("这次没能整理出完整建议，请重试。")
        merged[field] = value

    for field in ("do_list", "avoid_list"):
        if not isinstance(candidate.get(field), list):
            raise MessageSimulationUnavailableError("这次没能整理出完整建议，请重试。")
        merged[field] = _clean_list(candidate[field])

    if candidate.get("risk_level") not in {"low", "medium", "high", "severe"}:
        raise MessageSimulationUnavailableError("这次没能整理出完整建议，请重试。")
    merged["risk_level"] = _merge_risk_level(
        candidate.get("risk_level"),
        str(baseline.get("risk_level") or "medium"),
    )
    if merged["risk_level"] != candidate["risk_level"]:
        merged["risk_reason"] = baseline["risk_reason"]
    merged["fallback_reason"] = None
    merged["shadow_result"] = None
    merged.pop("raw_error", None)
    merged.pop("raw_response", None)
    return merged


async def simulate_message_preview(draft: str, context: dict) -> dict:
    fallback = build_message_preview_baseline(draft, context)
    fallback.setdefault("fallback_reason", None)
    fallback.setdefault("shadow_result", None)
    prompt = SIMULATION_PROMPT.format(
        context_json=json.dumps(context, ensure_ascii=False),
        draft=draft.strip(),
        evidence_json=json.dumps(fallback.get("structured_evidence") or {}, ensure_ascii=False),
    )
    messages = [
        {"role": "system", "content": SIMULATION_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    try:
        result = await asyncio.wait_for(
            chat_completion(settings.AI_TEXT_MODEL, messages, temperature=0.4),
            timeout=SIMULATION_TIMEOUT_SECONDS,
        )
        payload = _merge_preview_payload(_parse_json(result), fallback, draft)
    except (asyncio.TimeoutError, MessageSimulationUnavailableError):
        raise
    except Exception as exc:
        raise MessageSimulationUnavailableError("这次没能连上改写服务，请重试。") from exc
    payload["risk_level_label"] = risk_level_label(payload.get("risk_level"))
    payload["suggested_tone"] = translate_inline_codes(payload.get("suggested_tone", ""))
    payload["deviation_reasons"] = [
        translate_inline_codes(item) for item in payload.get("deviation_reasons", [])
    ]
    payload.setdefault("feedback_status", "pending_feedback")
    payload.setdefault("shadow_result", None)
    return payload
