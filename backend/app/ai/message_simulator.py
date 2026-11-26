"""Message simulation helpers for pre-send relationship coaching."""

import asyncio
import json
import logging
import re
from time import perf_counter

from app.ai import chat_completion
from app.ai.policy import compose_relationship_system_prompt
from app.core.config import settings
from app.services.display_labels import risk_level_label, translate_inline_codes
from app.services.relationship_algorithms import build_message_preview_baseline

logger = logging.getLogger(__name__)

# Frontend AI requests are capped at 60s; surface timeout before the client aborts.
SIMULATION_TIMEOUT_SECONDS = 55


SIMULATION_SYSTEM_PROMPT = compose_relationship_system_prompt("""你负责亲健的“发前看看”功能，帮助用户检查准备发出的消息，并提供可供选择的改写。
保留原话中的事实、感受、请求和明确边界，使用日常说话的语气。不要替用户示弱、撒娇或讨好，也不要把所有不满解释成缺少安全感。
只根据提供的记录作判断。不能编造对方很忙、很辛苦等背景，也不能断言对方的想法或保证改写后会得到回应。
必须区分三件事：
1. 是否存在施压/威胁/控制风险（coercion_detected）：先判断是否以泄露隐私、伤害、惩罚或限制自由迫使对方服从。识别为胁迫时 coercion_detected=true，safer_rewrite 输出空字符串，只解释风险和停止胁迫的处理建议，不能提供继续索要密码、定位或控制对方的话术。普通拒绝、要求归还借款、保护自己的隐私、表达烦躁都不等于胁迫。
2. 表达摩擦与容易让对话升级的字眼（escalation_friction_level 与 escalation_cues）：一句话可以没有威胁或胁迫，但包含反问指责、概括定性、厌烦推开等容易引发对立的措辞（例如“你能不能别总来烦我”）。这类句子不是胁迫，但 escalation_friction_level 应为 medium 或 high，并在 escalation_cues 点出具体容易引发防御的字眼；相反，平静清楚的正当边界（例如“我今晚想自己待一会儿”）不是冷战也不是施压，escalation_friction_level 应为 low，escalation_cues 为空数组，不要强行挑刺。
3. 说话人归属（speaker_attribution）：如果输入明显是在转述对方说过的话（例如“他对我说‘别来烦我’”或粘贴对方发来的带刺消息如“真羡慕你每天准时下班”），speaker_attribution 设为 quoted_other_party，escalation_friction_level 设为 low，escalation_cues 为空数组，不要把对方说的话当成用户在攻击对方；如实说明这像是在转述原话，若存在反差夸奖、拉踩对照（“羡慕你……不像我们……”）、提前免责（“我说话直你别介意”）或语气标点错位等可能的话外音，点出让人不舒服的刺在哪（同时说明需结合平时熟络程度判断，不替对方定罪），并在改写里给出一条自然、体面、贴合用户风格的回应示范。
4. 尊重上下文里的 communication_profile（包含用户陪聊风格 style_label、表达力度 expression_intensity / intensity_label、舒适偏好 comfort_preferences、个人雷点 taboos 与关系类型 pair_type）：改写既符合微信日常打字的顺口语感，也绝不踩用户写明的雷点；当 expression_intensity 为 soft 时侧重留台阶、多用“嘛 / 呀 / 啦 / 好不好”替代生硬的“吗”，为 balanced 时保持自然有态度、少用客服句式，为 sharp 时大胆硬气、拒绝自证清白、善用冷静反问或直白底线把皮球踢回去（绝不替用户擅自揽活）。但风格与力度都不能覆盖事实、边界与胁迫拦截规则。
用户明确说“真心”“真的想让你专心”“不是赌气”等意图时，以其说明为准。原句明确在体谅时，partner_view、likely_impact、risk_reason 以及建议都不得假设其在试探、冷战、推开或疏远对方，不给正常体谅附加心理风险。原句适合时直接保留，不额外添加“忙完找我”等期待或承诺。有具体威胁行为时仍须指出，不能因自称关心而忽略行为。
改写不能比原话多出事实：原话没提具体时间，就不要自己加“这两天”“今晚”“明天”“周日”“明早”“这周末”；原话没说的情绪，就不要替他说成“有点着急”“挺委屈”“挺失望”“心里堵”；原话没答应的事，就不要写成“晚点回你”“回头再聊”“等我缓过来再聊”“缓过来再找你”“过会儿再聊”“我陪你去”“我来安排”。这些只能来自用户自己说过的话。

改写语感要求：
- 改写后的话要像真人在微信上打字，不是在写检讨书或客服回访。亲近人或熟人提小要求时，尽量少用冷硬的“……吗？”，按语境换用“嘛 / 呗 / 呀 / 啦 / 好不好”等更活人的中文语气词；需要硬气立边界或冷静反问时干脆利落收尾。
- 可以用比喻、轻微的自嘲或日常口语让表达更自然。一句话如果能同时传递事实和态度，就不要拆成两句干巴巴的陈述。
- 允许用一语双关或借小事表达态度，这种含蓄是中文日常沟通的自然方式。
- “你忙吧”“行吧”需结合用户的明确解释理解，单凭这些词不能判定赌气或推测隐藏期待。信息不足时承认不确定。
- 改写结果应该让用户读完觉得“这就是我想说的，但说得更舒服了”。
- 改写后的话是用户发给那个人的：用“我”说、“你”指对方。不要把处境复述一遍当成交付物（写成“我妈又催我找对象，说再不找就没人要了”是描述，不是发给她的话），也不要用第三人称说对方。

严格按指定字段输出 JSON。"""
)


SIMULATION_PROMPT = """请检查下面这条待发送消息，分开说明是否存在施压风险，以及哪些具体字眼可能让对话升级，并给出自然、清楚的表达建议。

【关系上下文】
{context_json}

【用户准备发出的原话】
{draft}

【结构化判断（以此为边界，不夸大低风险，也不淡化高风险）】
{evidence_json}

请输出 JSON，不要包含其他文字：
{{
  "coercion_detected": false,
  "speaker_attribution": "self_outgoing/quoted_other_party/mixed",
  "escalation_friction_level": "low/medium/high",
  "escalation_cues": ["点出原话里可能引发防御或升级对立的具体字眼，如无则输出空数组"],
  "partner_view": "对方可能怎样理解这句话；信息不足时说明无法判断（60字内）",
  "likely_impact": "这句话可能怎样影响接下来的交流，不预测必然结果（70字内）",
  "risk_level": "low/medium/high",
  "risk_reason": "结合原话中的具体措辞，分开说清有无施压风险及是否有易升级字眼（80字内）",
  "safer_rewrite": "存在胁迫时为空字符串；其他情况保留事实、感受、请求和边界，绝不替用户补未说的时间期限或后续再聊/再回的承诺（如‘这两天’‘晚点回你’‘等我缓过来再聊’）；写成用户对那个人说的第一人称，不复述处境（120字内）",
  "suggested_tone": "适合这次交流的语气，例如平静、直接、友好",
  "conversation_goal": "根据原话可以确认的交流目的（40字内）",
  "do_list": ["一条完整、具体的表达建议（40字内，不要写半截）", "另一条完整建议"],
  "avoid_list": ["一种需要避免的表达方式（40字内，不要写半截）", "另一种需要避免的表达方式"]
}}"""


class MessageSimulationUnavailableError(RuntimeError):
    """No usable model result. Never replace it with a canned expression."""


def _parse_json(text: str) -> dict:
    try:
        if not isinstance(text, str):
            raise ValueError("non-string response")
        cleaned = re.sub(
            r"<(?:thinking|thought|system_warning)>[\s\S]*?</(?:thinking|thought|system_warning)>",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned, flags=re.IGNORECASE)
        if fenced:
            cleaned = fenced.group(1).strip()
        try:
            parsed = json.loads(cleaned)
        except ValueError:
            start = cleaned.find("{")
            if start < 0:
                raise
            parsed, _ = json.JSONDecoder().raw_decode(cleaned[start:])
        if not isinstance(parsed, dict):
            raise ValueError("json root is not dict")
        return parsed
    except (ValueError, IndexError, AttributeError, TypeError) as exc:
        logger.warning(
            "message_simulator invalid json output (len=%d)",
            len(text) if isinstance(text, str) else -1,
        )
        raise MessageSimulationUnavailableError("这次没能整理出完整建议，请重试。") from exc


def _trim_complete_sentence(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    snippet = text[:limit]
    min_cut = max(8, int(limit * 0.45))
    for sep in ("。", "！", "？", "；", "，", " "):
        idx = snippet.rfind(sep)
        if idx >= min_cut:
            trimmed = snippet[: idx + (0 if sep == " " else 1)].rstrip("，,；; ")
            if trimmed.count("“") > trimmed.count("”"):
                trimmed += "”"
            return trimmed
    trimmed = snippet.rstrip("，,；;“\"‘' ")
    if trimmed.count("“") > trimmed.count("”"):
        trimmed += "”"
    return trimmed


def _clean_string(value: object, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return _trim_complete_sentence(cleaned, limit)


def _clean_list(value: object, *, limit: int = 3, item_limit: int = 80) -> list[str]:
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


def _merge_friction_level(ai_value: object, baseline_value: str) -> str:
    order = {"low": 1, "medium": 2, "high": 3}
    base = baseline_value if baseline_value in order else "low"
    ai_level = str(ai_value or "").strip().lower()
    if ai_level not in order:
        return base
    return ai_level if order[ai_level] >= order[base] else base


def _friction_label_for(level: str, speaker_attribution: str, coercion: bool) -> str:
    if coercion:
        return "存在施压或威胁，请先停下"
    if speaker_attribution == "quoted_other_party":
        return "像是在转述对方的话，不是你主动发出的指责"
    return {
        "high": "刺激性较强，容易引发明显对立",
        "medium": "部分字眼容易让对方防御或让对话升级",
        "low": "表达较平和，未见明显刺激字眼",
    }.get(level, "表达较平和，未见明显刺激字眼")


_NEGATED_COERCION = re.compile(
    r"(?:没有|没见|没什么|没发现|并无|毫无|暂无|无|未见|未|零|绝非|并非|非"
    r"|不含|不存在|不涉及|不构成|不是|不属于|不算|不等于|不带|不具有|不具|不显|不够"
    r"|谈不上|算不上|称不上|构不成|看不出).{0,24}(?:胁迫|要挟|勒索|威胁)"
    r"|(?:胁迫|要挟|勒索|威胁).{0,8}(?:为零|为0|不存在|没有|无|极低|几乎没有)"
)
# 用户是在讲别人怎么威胁他，不是在威胁别人。
_COERCION_BY_OTHER_PARTY = re.compile(
    r"(?:他|她|对方|前任|男朋友|女朋友|老公|老婆|对象|我爸|我妈|妈|爸|哥|姐|弟|妹|朋友|同事|领导|室友)"
    r"[^，。；;！？!?\n]{0,10}(?:用|拿|以|老是|总是|又|每次|一直)?"
    r"[^，。；;！？!?\n]{0,6}(?:威胁|要挟|勒索|恐吓|逼)"
)


def _coercion_clause(clause: str) -> bool:
    if not re.search(r"胁迫|要挟|勒索|威胁", clause):
        return False
    if _NEGATED_COERCION.search(clause) or _COERCION_BY_OTHER_PARTY.search(clause):
        return False
    return True


def _merge_preview_payload(candidate: dict, baseline: dict, draft: str) -> dict:
    # Rules supply risk/evidence metadata, not replacement model prose.
    merged = dict(baseline)
    baseline_speaker = str(baseline.get("speaker_attribution") or "self_outgoing")
    ai_speaker = str(candidate.get("speaker_attribution") or "").strip().lower()
    if baseline_speaker == "quoted_other_party":
        speaker_attribution = "quoted_other_party"
    elif ai_speaker in {"self_outgoing", "quoted_other_party", "mixed"}:
        speaker_attribution = ai_speaker
    else:
        speaker_attribution = baseline_speaker

    # 明确识别出的胁迫不得通过改写字段重新进入发送流程；纯转述对方原话不误拦为本人胁迫。
    coercion = candidate.get("coercion_detected") is True or (
        speaker_attribution != "quoted_other_party"
        and bool(
            re.search(
                r"(?:不给|不交|不发|不听|不照|不回|不去|不把|不让).{0,35}就.{0,15}"
                r"(?:公开|曝光|发到群|发进群|群发|伤害|打你|闹|堵你|堵到|骚扰|告诉大家|告诉你爸妈|告诉你领导)",
                draft,
            )
        )
    )
    reason = str(candidate.get("risk_reason") or "")
    coercion = coercion or (
        speaker_attribution != "quoted_other_party"
        and any(_coercion_clause(clause) for clause in re.split(r"[，。；;\n]", reason))
    )
    coercion = bool(coercion)
    for field, limit in (
        ("partner_view", 80),
        ("likely_impact", 90),
        ("risk_reason", 100),
        ("safer_rewrite", 140),
        ("suggested_tone", 40),
        ("conversation_goal", 50),
    ):
        if field == "safer_rewrite" and coercion:
            merged[field] = ""
            continue
        if field == "conversation_goal" and coercion:
            merged[field] = "停止胁迫，尊重对方的隐私和选择"
            continue
        value = _clean_string(candidate.get(field), limit)
        if not value:
            if field == "suggested_tone" and coercion:
                merged[field] = "先暂停发送"
                continue
            logger.warning("message_simulator missing required string field: %s", field)
            raise MessageSimulationUnavailableError("这次没能整理出完整建议，请重试。")
        merged[field] = value

    for field in ("do_list", "avoid_list"):
        raw_list = candidate.get(field)
        if not isinstance(raw_list, list):
            if coercion:
                merged[field] = []
                continue
            logger.warning("message_simulator missing required list field: %s", field)
            raise MessageSimulationUnavailableError("这次没能整理出完整建议，请重试。")
        merged[field] = _clean_list(raw_list, limit=2, item_limit=80)

    ai_risk_level = str(candidate.get("risk_level") or "").strip().lower()
    if ai_risk_level not in {"low", "medium", "high", "severe"}:
        if coercion:
            ai_risk_level = "high"
        else:
            logger.warning("message_simulator invalid risk_level: %r", candidate.get("risk_level"))
            raise MessageSimulationUnavailableError("这次没能整理出完整建议，请重试。")
    merged["risk_level"] = _merge_risk_level(
        ai_risk_level,
        str(baseline.get("risk_level") or "medium"),
    )
    if coercion:
        merged["risk_level"] = _merge_risk_level(merged["risk_level"], "high")

    ai_friction = candidate.get("escalation_friction_level")
    base_friction = str(baseline.get("escalation_friction_level") or "low")
    if coercion:
        friction_level = "high"
    elif speaker_attribution == "quoted_other_party":
        friction_level = "low"
        merged["risk_level"] = "low"
    else:
        friction_level = _merge_friction_level(ai_friction, base_friction)
        if merged["risk_level"] in {"high", "severe"} and friction_level == "low":
            friction_level = "high"
        elif merged["risk_level"] == "medium" and friction_level == "low":
            friction_level = "medium"

    if merged["risk_level"] != ai_risk_level and not coercion:
        if str(ai_friction or "").strip().lower() not in {"medium", "high"}:
            merged["risk_reason"] = baseline["risk_reason"]

    ai_cues = _clean_list(candidate.get("escalation_cues"), limit=3, item_limit=80) if isinstance(candidate.get("escalation_cues"), list) else []
    base_cues = list(baseline.get("escalation_cues") or [])
    if coercion:
        escalation_cues = ["包含威胁、控制或施压措辞"]
        pressure_risk_level = "high"
        pressure_risk_label = "存在明显施压或威胁风险"
    elif speaker_attribution == "quoted_other_party":
        escalation_cues = []
        pressure_risk_level = "none"
        pressure_risk_label = "暂无施压或威胁风险"
    else:
        escalation_cues = ai_cues if ai_cues else (base_cues if friction_level != "low" else [])
        pressure_risk_level = str(baseline.get("pressure_risk_level") or "none")
        pressure_risk_label = str(baseline.get("pressure_risk_label") or "暂无施压或威胁风险")

    merged["speaker_attribution"] = speaker_attribution
    merged["pressure_risk_level"] = pressure_risk_level
    merged["pressure_risk_label"] = pressure_risk_label
    merged["escalation_friction_level"] = friction_level
    merged["escalation_friction_label"] = _friction_label_for(
        friction_level, speaker_attribution, coercion
    )
    merged["escalation_cues"] = escalation_cues
    merged["fallback_reason"] = None
    merged["shadow_result"] = None
    merged["rewrite_blocked"] = coercion
    merged["rewrite_block_reason"] = "这句话含有胁迫，请先停止施压，尊重对方的隐私和选择。" if coercion else None
    if coercion:
        merged["conversation_goal"] = "停止胁迫，尊重对方的隐私和选择"
        merged["do_list"] = ["先停止威胁和索取，给对方选择空间"]
        merged["avoid_list"] = ["不要以公开隐私或伤害迫使对方配合"]
    merged.pop("raw_error", None)
    merged.pop("raw_response", None)
    return merged


async def simulate_message_preview(draft: str, context: dict) -> dict:
    t0 = perf_counter()
    fallback = build_message_preview_baseline(draft, context)
    baseline_ms = int((perf_counter() - t0) * 1000)
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
    t_llm = perf_counter()
    try:
        result = await asyncio.wait_for(
            chat_completion(
                "default",
                messages,
                temperature=0.4,
                response_format={"type": "json_object"},
            ),
            timeout=SIMULATION_TIMEOUT_SECONDS,
        )
        llm_ms = int((perf_counter() - t_llm) * 1000)
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
    payload["_timings_ms"] = {
        "baseline_ms": baseline_ms,
        "llm_ms": llm_ms,
    }
    return payload
