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


SIMULATION_SYSTEM_PROMPT = compose_relationship_system_prompt("""你是亲健平台的「发前看看」亲密沟通教练，精通高情商沟通套路、非暴力沟通（NVC）与亲密依恋心理学。
你的核心任务是：在用户把冲动、怨气、生硬或指责的话发出去之前，帮用户把【火药味与向外指责】巧妙化解为【让人心软的高情商表达与真实需要的示弱】。

【高情商沟通核心套路与心法】
1. **化攻击为示弱与向往**：
   - 用户原话里的愤怒、怨怼（如“你怎么又这么晚”、“我很烦”、“算了吧”、“每次都这样”），本质上是“渴望被在乎、害怕被忽略、缺少安全感”的脆弱呼救。
   - 严禁在改写中保留生硬、对抗、负能量的硬杠词汇（绝不要出现“我很烦”、“我不是想跟你算账”、“不要让我更烦”、“对齐一下”等冷漠或防御性字眼）。
   - 引导用户把刺收起来、把软肋亮出来。用“在乎、挂念、需要、有点小落空”替代“指责、抱怨、翻旧账”。
2. **高情商三明治表达法则（改写 safer_rewrite 必须严格践行）**：
   - **第一层（前置垫字·体谅关怀）**：先理解对方的不易与辛苦（如“知道你今天肯定忙晕了/辛苦啦”、“明白你手头事情多”）；
   - **第二层（柔和示弱·表达真实感受）**：委婉说出自己的在乎与小失落（如“一直没等到消息，我一个人心里有点空落落的/有点挂念”）；
   - **第三层（递个台阶·提出零压力微请求）**：给对方一个极容易做到的轻量动作（如“忙完随手丢个小表情报个平安就好，先专心忙，想你啦~”）。
3. **语言风格与人情温度**：
   - 语气温柔、自然、有烟火气，像高情商伴侣之间撒娇又懂事的温存对话，让人看一眼就心生怜惜、忍不住立刻想回、想哄、想抱抱，彻底避免把对方推向防御反击或冷战。
4. **客观测定与对方视角**：
   - partner_view（对方可能先听成）：透彻点出对方听到火药味时的下意识防卫心理（如“对方听不到你的想念，只会觉得被劈头盖脸指责，下意识想关掉对话框防卫”）。
   - likely_impact（走向）：点出硬刚会导致辩论赛或冷战，而委婉改写则能换来心疼与温和回应。
   - 严格输出 JSON 格式。"""
)


SIMULATION_PROMPT = """请根据以下关系上下文和结构化判断，进行高情商预演，把原话的火药味或刚硬感化解为温柔、委婉、让人心软的高情商沟通。

【关系上下文】
{context_json}

【用户准备发出的原话】
{draft}

【结构化判断（请以此为边界，不要把低风险写成高风险，也不要把高风险轻描淡写）】
{evidence_json}

请输出 JSON（不要包含其他文字）：
{{
  "partner_view": "对方最可能的第一感受或误读（点出对方容易开启防御或感受到的压力，40字内）",
  "likely_impact": "如果原话直接发出去，互动最可能出现的走向（如争论、辩驳或冷战，50字内）",
  "risk_level": "low/medium/high",
  "risk_reason": "为什么存在这个风险（如指责词、火药味、未表达真实需要，50字内）",
  "safer_rewrite": "高情商三明治改写版本：体谅对方辛苦+委婉表达挂念与示弱+零压力台阶与微请求，绝不出现'我很烦'或生硬指责（120字内）",
  "suggested_tone": "建议采用的语气，如温柔轻软/体谅中带点示弱/先垫字再表达需要",
  "conversation_goal": "这条消息真正更适合达成的目标（如让对方心软并愿意回应，30字内）",
  "do_list": ["高情商建议做法1（如先体谅对方辛苦）", "高情商建议做法2（如亮出在乎而非指责）"],
  "avoid_list": ["应避免的低情商做法1（如直接发泄说我很烦）", "应避免的低情商做法2（如使用你怎么又扫射）"]
}}"""


def _parse_json(text: str, fallback: dict) -> dict:
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        fallback["raw_response"] = text
        return fallback


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


def _merge_preview_payload(candidate: dict, fallback: dict, draft: str) -> dict:
    merged = dict(fallback)
    for field, limit in (
        ("partner_view", 40),
        ("likely_impact", 50),
        ("risk_reason", 50),
        ("safer_rewrite", 120),
        ("suggested_tone", 32),
        ("conversation_goal", 30),
    ):
        value = _clean_string(candidate.get(field), limit)
        if value:
            merged[field] = value

    for field in ("do_list", "avoid_list"):
        values = _clean_list(candidate.get(field))
        if values:
            merged[field] = values

    merged["risk_level"] = _merge_risk_level(
        candidate.get("risk_level"),
        str(fallback.get("risk_level") or "medium"),
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
    if str(merged.get("safer_rewrite") or "").strip() == draft.strip():
        merged["safer_rewrite"] = fallback["safer_rewrite"]
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
        parsed = _parse_json(result, fallback)
        if parsed.get("raw_response"):
            payload = dict(fallback)
            payload["fallback_reason"] = "parse_error"
        else:
            payload = _merge_preview_payload(parsed, fallback, draft)
            payload["shadow_result"] = fallback
    except asyncio.TimeoutError:
        raise
    except Exception as exc:
        fallback["raw_error"] = exc.__class__.__name__
        fallback["fallback_reason"] = exc.__class__.__name__
        payload = fallback
    safer_rewrite = str(payload.get("safer_rewrite") or "").strip()
    if not safer_rewrite or safer_rewrite == draft.strip():
        payload["safer_rewrite"] = fallback["safer_rewrite"]
    payload["risk_level_label"] = risk_level_label(payload.get("risk_level"))
    payload["suggested_tone"] = translate_inline_codes(payload.get("suggested_tone", ""))
    payload["deviation_reasons"] = [
        translate_inline_codes(item) for item in payload.get("deviation_reasons", [])
    ]
    payload.setdefault("feedback_status", "pending_feedback")
    payload.setdefault("shadow_result", None)
    return payload
