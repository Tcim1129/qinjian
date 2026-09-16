"""Conflict repair protocol builder.

This keeps the first version rule-based on purpose so the product can explain a
clear, competition-friendly interaction loop even when model services are slow
or unavailable.
"""

from app.models import InterventionPlan, Pair, RelationshipProfileSnapshot
from app.services.display_labels import (
    focus_tag_label,
    model_family_label,
    plan_type_label,
    protocol_type_label,
    risk_level_label,
    translate_inline_codes,
)
from app.services.intervention_theory import build_repair_protocol_theory_basis


def build_repair_protocol(
    *,
    pair: Pair,
    crisis_level: str,
    active_plan: InterventionPlan | None = None,
    snapshot: RelationshipProfileSnapshot | None = None,
) -> dict:
    is_long_distance = bool(pair.is_long_distance)
    focus_tags = _derive_focus_tags(
        pair=pair,
        active_plan=active_plan,
        snapshot=snapshot,
    )

    if crisis_level == "severe":
        protocol = _severe_protocol(is_long_distance=is_long_distance)
    elif crisis_level == "moderate":
        protocol = _moderate_protocol(is_long_distance=is_long_distance)
    elif crisis_level == "mild":
        protocol = _mild_protocol(is_long_distance=is_long_distance)
    else:
        protocol = _stable_protocol(is_long_distance=is_long_distance)

    protocol["level"] = crisis_level
    protocol["level_label"] = risk_level_label(crisis_level)
    protocol["active_plan_type"] = active_plan.plan_type if active_plan else None
    protocol["active_plan_type_label"] = (
        plan_type_label(active_plan.plan_type) if active_plan else None
    )
    protocol["focus_tags"] = focus_tags
    protocol["focus_tag_labels"] = [focus_tag_label(tag) for tag in focus_tags]
    protocol["protocol_type_label"] = protocol_type_label(protocol["protocol_type"])
    protocol["model_family"] = "rule_engine_with_safety_first"
    protocol["model_family_label"] = model_family_label(protocol["model_family"])
    protocol["clinical_disclaimer"] = (
        "修复方案用于一般关系冲突与沟通修复，不替代法律、医疗或专业心理支持；若存在暴力、自伤他伤或强控制风险，应直接转专业支持。"
    )
    protocol["theory_basis"] = build_repair_protocol_theory_basis(
        protocol_type=protocol["protocol_type"],
        crisis_level=crisis_level,
        active_plan_type=protocol["active_plan_type"],
    )
    protocol["evidence_summary"] = _build_protocol_evidence(
        crisis_level=crisis_level,
        active_plan=active_plan,
        snapshot=snapshot,
    )
    protocol["limitation_note"] = (
        "修复方案基于最近的风险等级、关系画像和当前计划生成，"
        "它用于帮助双方降温和重建沟通，不替代专业判断。"
    )
    protocol["safety_handoff"] = _build_protocol_handoff(crisis_level)
    return protocol


def build_solo_repair_protocol(
    *,
    crisis_level: str,
    active_plan: InterventionPlan | None = None,
    snapshot: RelationshipProfileSnapshot | None = None,
) -> dict:
    focus_tags = _derive_solo_focus_tags(
        active_plan=active_plan,
        snapshot=snapshot,
    )

    if crisis_level == "severe":
        protocol = _solo_severe_protocol()
    elif crisis_level == "moderate":
        protocol = _solo_moderate_protocol()
    elif crisis_level == "mild":
        protocol = _solo_mild_protocol()
    else:
        protocol = _solo_stable_protocol()

    protocol["level"] = crisis_level
    protocol["level_label"] = risk_level_label(crisis_level)
    protocol["active_plan_type"] = active_plan.plan_type if active_plan else None
    protocol["active_plan_type_label"] = (
        plan_type_label(active_plan.plan_type) if active_plan else None
    )
    protocol["focus_tags"] = focus_tags
    protocol["focus_tag_labels"] = [focus_tag_label(tag) for tag in focus_tags]
    protocol["protocol_type_label"] = protocol_type_label(protocol["protocol_type"])
    protocol["model_family"] = "rule_engine_with_safety_first"
    protocol["model_family_label"] = model_family_label(protocol["model_family"])
    protocol["clinical_disclaimer"] = (
        "缓和准备版用于帮助你先稳住自己、整理表达和判断开口节奏，"
        "不替代法律、医疗或专业心理支持。"
    )
    protocol["theory_basis"] = build_repair_protocol_theory_basis(
        protocol_type=protocol["protocol_type"],
        crisis_level=crisis_level,
        active_plan_type=protocol["active_plan_type"],
    )
    protocol["evidence_summary"] = _build_solo_protocol_evidence(
        crisis_level=crisis_level,
        active_plan=active_plan,
        snapshot=snapshot,
    )
    protocol["limitation_note"] = (
        "缓和准备版基于你最近的个人记录、风险摘要和当前计划生成，"
        "它帮助你先稳住节奏，不等于对对方意图或关系走向的确定判断。"
    )
    protocol["safety_handoff"] = _build_solo_protocol_handoff(crisis_level)
    return protocol


def _derive_focus_tags(
    *,
    pair: Pair,
    active_plan: InterventionPlan | None,
    snapshot: RelationshipProfileSnapshot | None,
) -> list[str]:
    tags: list[str] = []
    if pair.is_long_distance:
        tags.append("long_distance")
    if active_plan:
        tags.append(active_plan.plan_type)

    suggested = []
    if snapshot and snapshot.suggested_focus:
        suggested = (snapshot.suggested_focus or {}).get("items", [])
    for item in suggested[:3]:
        if item not in tags:
            tags.append(item)
    return tags


def _derive_solo_focus_tags(
    *,
    active_plan: InterventionPlan | None,
    snapshot: RelationshipProfileSnapshot | None,
) -> list[str]:
    tags: list[str] = []
    if active_plan:
        tags.append(active_plan.plan_type)

    suggested = []
    if snapshot and snapshot.suggested_focus:
        suggested = (snapshot.suggested_focus or {}).get("items", [])
    for item in suggested[:3]:
        if item not in tags:
            tags.append(item)
    return tags


def _build_protocol_evidence(
    *,
    crisis_level: str,
    active_plan: InterventionPlan | None,
    snapshot: RelationshipProfileSnapshot | None,
) -> list[str]:
    evidence: list[str] = []
    normalized = risk_level_label(crisis_level or "none")
    evidence.append(f"当前处在 {normalized} 风险区间，修复节奏会先围绕降温还是推进来设计。")
    if active_plan:
        goal = (active_plan.goal_json or {}).get("primary_goal") or plan_type_label(active_plan.plan_type)
        evidence.append(f"当前激活计划的主要目标是：{goal}。")
    metrics = (snapshot.metrics_json or {}) if snapshot else {}
    overlap = metrics.get("interaction_overlap_rate")
    if overlap is not None:
        evidence.append(
            f"近阶段互动重合率约为 {round(float(overlap) * 100)}%，会影响系统对连接是否在回暖的判断。"
        )
    crisis_count = metrics.get("crisis_event_count")
    if crisis_count:
        evidence.append(f"近阶段已记录 {int(crisis_count)} 次风险事件，所以方案会更保守。")
    return [translate_inline_codes(item) for item in evidence[:4]]


def _build_protocol_handoff(crisis_level: str) -> str | None:
    if crisis_level not in {"moderate", "severe"}:
        return None
    return (
        "如果已经出现持续升级、威胁、羞辱、肢体伤害风险或明显失控，"
        "请停止继续推进对话，转向可信任的人、专业咨询或当地紧急支持。"
    )


def _build_solo_protocol_evidence(
    *,
    crisis_level: str,
    active_plan: InterventionPlan | None,
    snapshot: RelationshipProfileSnapshot | None,
) -> list[str]:
    evidence: list[str] = []
    normalized = risk_level_label(crisis_level or "none")
    evidence.append(f"你当前处在 {normalized} 风险区间，所以系统会先围绕稳住自己和判断开口节奏来设计。")
    if active_plan:
        goal = (active_plan.goal_json or {}).get("primary_goal") or plan_type_label(active_plan.plan_type)
        evidence.append(f"当前激活计划的主要目标是：{goal}。")
    metrics = (snapshot.metrics_json or {}) if snapshot else {}
    mood = metrics.get("mood_avg")
    if mood is not None:
        evidence.append(f"近阶段个人情绪均值约为 {round(float(mood), 1)}/10，这会影响系统对当前承压程度的判断。")
    task_rate = metrics.get("task_completion_rate")
    if task_rate is not None:
        evidence.append(f"近阶段自我照顾动作完成率约为 {round(float(task_rate) * 100)}%，用于判断你现在适合推进还是先减压。")
    risk_summary = (snapshot.risk_summary or {}) if snapshot else {}
    trend = risk_summary.get("trend")
    if trend:
        evidence.append(f"当前风险趋势显示为“{translate_inline_codes(trend)}”，所以建议会更偏向节奏管理而不是立刻推进。")
    return [translate_inline_codes(item) for item in evidence[:4]]


def _build_solo_protocol_handoff(crisis_level: str) -> str | None:
    if crisis_level not in {"moderate", "severe"}:
        return None
    return (
        "如果最近已经明显影响睡眠、工作、饮食，或出现持续失控感，"
        "请尽快寻求线下专业支持，而不是只靠自助建议继续硬撑。"
    )


def _stable_protocol(*, is_long_distance: bool) -> dict:
    sync_hint = "先用文字铺垫，再约一个 10 分钟视频确认。" if is_long_distance else "直接找一个不被打断的 10 分钟窗口。"
    return {
        "protocol_type": "steady_maintenance",
        "title": "低压维护方案",
        "summary": "当前没有明显风险，但可以用一轮轻量沟通，把误会提前消化掉。",
        "timing_hint": sync_hint,
        "steps": [
            {
                "sequence": 1,
                "title": "先发低威胁开场",
                "action": "先说“我想把今天的小别扭讲清楚，不是来吵架的”。",
                "why": "先降低防御，对方更容易进入理解模式。",
                "duration_hint": "30 秒",
            },
            {
                "sequence": 2,
                "title": "只说一个点",
                "action": "一次只谈今天最想澄清的一件事，不顺手带第二个问题。",
                "why": "避免对方觉得被集中清算。",
                "duration_hint": "3 分钟",
            },
            {
                "sequence": 3,
                "title": "落一个小动作",
                "action": "最后约定一个今晚就能做到的小动作，比如回消息方式或一个固定联系时间。",
                "why": "让沟通有结果，不停在“说过了”。",
                "duration_hint": "2 分钟",
            },
        ],
        "do_not": ["不要临时翻旧账", "不要把“你总是”挂在句首"],
        "success_signal": "对方愿意继续聊，并能确认一个小的下一步。",
        "escalation_rule": "如果对方连续两次回避或情绪明显升高，再切换到中度修复方案。",
    }


def _mild_protocol(*, is_long_distance: bool) -> dict:
    channel_hint = "先文字确认情绪，再约一个短通话。" if is_long_distance else "最好面对面或语音，不建议纯文字硬谈。"
    return {
        "protocol_type": "gentle_repair",
        "title": "轻度修复方案",
        "summary": "适合刚出现别扭、互动变冷或误会初起时，用低压力但具体的方式把关系拉回正轨。",
        "timing_hint": channel_hint,
        "steps": [
            {
                "sequence": 1,
                "title": "先停一停情绪惯性",
                "action": "先暂停 10 到 20 分钟，不在情绪顶点继续发消息。",
                "why": "让表达从冲动变成沟通。",
                "duration_hint": "10-20 分钟",
            },
            {
                "sequence": 2,
                "title": "用感受开头",
                "action": "用“我刚刚有点失落/着急，因为……”表达，而不是直接判断对方。",
                "why": "感受更容易让对方听进去，指责更容易引发防御。",
                "duration_hint": "1 分钟",
            },
            {
                "sequence": 3,
                "title": "只提一个具体需求",
                "action": "把需求说成一个可执行动作，例如“忙的时候提前告诉我一声”。",
                "why": "模糊期待很难被满足，具体动作更容易被回应。",
                "duration_hint": "2 分钟",
            },
            {
                "sequence": 4,
                "title": "收尾做确认",
                "action": "问一句“你理解成的重点是什么”，确认没有再次误读。",
                "why": "很多冲突不是没说，而是双方理解的不是同一句话。",
                "duration_hint": "2 分钟",
            },
        ],
        "do_not": ["不要连续追问", "不要用沉默测试对方", "不要把语气词写成质问"],
        "success_signal": "对方能复述你的重点，且双方确认了一个具体行动。",
        "escalation_rule": "如果沟通后仍持续冷淡 24 小时以上，切换到中度修复方案。",
    }


def _moderate_protocol(*, is_long_distance: bool) -> dict:
    channel_hint = "优先视频或语音，尽量不要只靠长段文字。" if is_long_distance else "优先面对面，至少保证实时沟通。"
    return {
        "protocol_type": "structured_repair",
        "title": "中度修复方案",
        "summary": "适合已经出现回避、冷处理或反复争执的情况，需要一轮结构化修复，而不是继续即兴发挥。",
        "timing_hint": channel_hint,
        "steps": [
            {
                "sequence": 1,
                "title": "先宣布暂停升级",
                "action": "明确说“我想解决，不想升级，我们先把语气放下来”。",
                "why": "先共同定义目标，减少彼此把修复当成输赢。",
                "duration_hint": "30 秒",
            },
            {
                "sequence": 2,
                "title": "按事实-感受-需求顺序说",
                "action": "先说发生了什么，再说自己的感受，最后说希望怎么调整。",
                "why": "这能避免一句话里同时塞满指责、委屈和要求。",
                "duration_hint": "4 分钟",
            },
            {
                "sequence": 3,
                "title": "要求对方复述，不要求立刻认同",
                "action": "请对方先复述你的重点，只确认听懂，不急着争结论。",
                "why": "先对齐理解，再讨论立场，更容易止损。",
                "duration_hint": "3 分钟",
            },
            {
                "sequence": 4,
                "title": "交换各自最小可让步动作",
                "action": "每个人都给出一个自己今晚能做到的修复动作。",
                "why": "修复不是道理赢了，而是关系开始重新流动。",
                "duration_hint": "4 分钟",
            },
            {
                "sequence": 5,
                "title": "设置 24 小时复盘点",
                "action": "约定明天同一时间再复盘一次，确认问题是否真的降温。",
                "why": "中度冲突不靠一次对话彻底解决，需要观察后效。",
                "duration_hint": "1 分钟",
            },
        ],
        "do_not": ["不要要求对方立刻道歉", "不要边修复边翻全部旧账", "不要在第三人面前继续争论"],
        "success_signal": "双方都能说出自己的让步动作，并愿意在 24 小时内继续复盘。",
        "escalation_rule": "如果出现辱骂、羞辱、断联或反复爆发，立即切换到严重修复方案并考虑专业帮助。",
    }


def _severe_protocol(*, is_long_distance: bool) -> dict:
    distance_note = "先停止高强度文字拉扯，只保留安全确认和必要沟通。" if is_long_distance else "先停止当场拉扯，确保双方先离开高压场景。"
    return {
        "protocol_type": "de_escalation_protocol",
        "title": "严重冲突止损方案",
        "summary": "适合高强度争执、羞辱、防御升级或明显冷暴力迹象。第一目标不是讲清全部问题，而是先止损、保安全、再决定如何修复。",
        "timing_hint": distance_note,
        "steps": [
            {
                "sequence": 1,
                "title": "先停战，不再追击",
                "action": "立即停止争论和追问，只保留一句“我们先暂停，等情绪降下来再谈”。",
                "why": "严重冲突阶段，继续解释只会继续升级。",
                "duration_hint": "立即执行",
            },
            {
                "sequence": 2,
                "title": "做安全确认",
                "action": "确认双方人身和情绪状态安全，必要时联系可信任的人陪同。",
                "why": "任何关系修复都不能建立在失控和恐惧上。",
                "duration_hint": "5 分钟",
            },
            {
                "sequence": 3,
                "title": "改成低刺激表达",
                "action": "24 小时内只允许发送低刺激、短句、无指责的信息，例如“我知道现在不适合继续吵，等你愿意时我们再谈”。",
                "why": "先把系统从高压模式切回可沟通模式。",
                "duration_hint": "24 小时内",
            },
            {
                "sequence": 4,
                "title": "不要独立硬修复",
                "action": "如果近期已多次升级，优先引入第三方支持：咨询师、导师或可信任长辈。",
                "why": "严重冲突往往已经超过双方单次自救能力。",
                "duration_hint": "24-48 小时",
            },
        ],
        "do_not": ["不要继续逼对方回复", "不要用威胁、羞辱或分手试探", "不要在失控时做重大决定"],
        "success_signal": "双方至少能停止升级，并同意在安全边界内再安排下一次沟通。",
        "escalation_rule": "如果存在家庭暴力、自伤他伤风险或长期羞辱控制，跳过产品内修复，直接寻求专业和法律支持。",
    }


def _solo_stable_protocol() -> dict:
    return {
        "protocol_type": "steady_maintenance",
        "title": "低压整理方案",
        "summary": "当前没有明显升级风险，先把想说的话和自己的真实需求理顺，不急着一次讲透。",
        "timing_hint": "先留 10 分钟给自己，把最想被理解的那一句写下来，再决定要不要现在开口。",
        "steps": [
            {
                "sequence": 1,
                "title": "先分清事实和情绪",
                "action": "先写下发生了什么，再写下你真正难受的点，不要把两者混在一句里。",
                "why": "事实和情绪分开后，你更容易知道自己到底想沟通什么。",
                "duration_hint": "3 分钟",
            },
            {
                "sequence": 2,
                "title": "给这次对话定一个小目标",
                "action": "先决定这次只想做到一件事，比如确认安排、表达感受，或先把误会说清。",
                "why": "小目标比“一次解决全部问题”更容易让对话稳定。",
                "duration_hint": "2 分钟",
            },
            {
                "sequence": 3,
                "title": "用低刺激开场",
                "action": "把开场改成“我想确认一下”或“我有点在意这件事”，不要直接上结论。",
                "why": "低刺激开场更容易让对方先听进去。",
                "duration_hint": "1 分钟",
            },
        ],
        "do_not": ["不要一上来就翻旧账", "不要把“总是”“从来”放在句首"],
        "success_signal": "你已经能说清自己想表达什么，而且开口时不再只剩情绪。",
        "escalation_rule": "如果越整理越急、越想立刻发出去，先切换到轻度缓和方案。",
    }


def _solo_mild_protocol() -> dict:
    return {
        "protocol_type": "gentle_repair",
        "title": "轻度缓和方案",
        "summary": "适合刚刚开始上头、反复想发消息或已经有一点委屈时，先让自己从冲动切回可沟通状态。",
        "timing_hint": "先暂停 10 到 20 分钟，不在最想立刻发出去的时候决定表达方式。",
        "steps": [
            {
                "sequence": 1,
                "title": "先停一下冲动发送",
                "action": "把消息放到草稿里，不立刻按发送，先离开当前对话框几分钟。",
                "why": "很多后悔都发生在“再多发一句”的瞬间。",
                "duration_hint": "10-20 分钟",
            },
            {
                "sequence": 2,
                "title": "把责备改成感受",
                "action": "先把“你怎么又”改成“我刚刚有点失落/着急，因为……”。",
                "why": "感受更容易让对方听进去，责备更容易引发防御。",
                "duration_hint": "2 分钟",
            },
            {
                "sequence": 3,
                "title": "只留下一个具体请求",
                "action": "把这次最想得到的回应压缩成一个动作，比如提前说一声、约个时间、先确认一下。",
                "why": "一个明确请求，比很多混在一起的期待更容易被回应。",
                "duration_hint": "2 分钟",
            },
        ],
        "do_not": ["不要连发追问", "不要用沉默或撤回试探对方"],
        "success_signal": "你能把原本想发的那句降下来，而且更知道这次真正想得到什么。",
        "escalation_rule": "如果你已经明显停不下来、反复想追击，切换到中度缓和方案。",
    }


def _solo_moderate_protocol() -> dict:
    return {
        "protocol_type": "structured_repair",
        "title": "结构化缓和方案",
        "summary": "适合已经明显被关系情绪带着走、脑子里反复排练争论时，先把自己从高压回路里拉出来。",
        "timing_hint": "今天先不要追求讲清全部问题，先把身体和节奏稳住，再决定是否继续推进。",
        "steps": [
            {
                "sequence": 1,
                "title": "先做身体降压",
                "action": "先离开当前环境，做一次走动、喝水、呼吸或冲洗，让身体先降下来。",
                "why": "身体还在高压里时，再漂亮的话也容易发成攻击。",
                "duration_hint": "5-10 分钟",
            },
            {
                "sequence": 2,
                "title": "写出事实-感受-请求",
                "action": "按“发生了什么 / 我现在什么感受 / 我希望下一步是什么”三行写下来。",
                "why": "结构化整理能减少脑内争辩，把重点从情绪切回表达。",
                "duration_hint": "5 分钟",
            },
            {
                "sequence": 3,
                "title": "决定今天只推进到哪一步",
                "action": "明确今天是只发一个低刺激开场，还是先不发，只把草稿留到明天再看。",
                "why": "把推进边界说清楚，能减少你被情绪继续拖走。",
                "duration_hint": "2 分钟",
            },
            {
                "sequence": 4,
                "title": "给自己设一个复盘点",
                "action": "约一个明确时间，再看这件事是否还值得继续推进，比如今晚 9 点或明早。",
                "why": "有复盘点，就不必一直挂在心里反复咀嚼。",
                "duration_hint": "1 分钟",
            },
        ],
        "do_not": ["不要边哭边继续写长消息", "不要拿最坏结果反复吓自己", "不要在高压时做关系结论"],
        "success_signal": "你已经从想立刻解决，切回到知道今天最多只推进哪一步。",
        "escalation_rule": "如果已经连续影响睡眠、工作或吃饭，切换到高风险止损方案并考虑专业支持。",
    }


def _solo_severe_protocol() -> dict:
    return {
        "protocol_type": "de_escalation_protocol",
        "title": "高压止损方案",
        "summary": "适合已经明显失控、反复崩溃、停不下脑内冲突或已经影响基本生活功能时。第一目标不是继续分析关系，而是先止损和保安全。",
        "timing_hint": "今天先停止高刺激沟通和反复重看聊天记录，把重点放回身体、安全和现实支持。",
        "steps": [
            {
                "sequence": 1,
                "title": "先停掉继续升级的输入",
                "action": "先暂停继续发消息、反复看记录或脑内排练争论，给自己一个明确的停战窗口。",
                "why": "高压状态下继续输入，只会把神经系统拉得更紧。",
                "duration_hint": "立即执行",
            },
            {
                "sequence": 2,
                "title": "做现实安全确认",
                "action": "先确认自己有没有吃饭、喝水、休息，有没有一个可信任的人可以联系。",
                "why": "关系问题一旦压到基本功能，优先级就不再是沟通，而是安全。",
                "duration_hint": "5 分钟",
            },
            {
                "sequence": 3,
                "title": "把今天的目标降到最小",
                "action": "今天只保留一个最小动作，比如不再追加消息、给朋友发一句求助、或预约一次专业支持。",
                "why": "高压期不适合追求高质量修复，只适合先保住自己。",
                "duration_hint": "10 分钟内",
            },
            {
                "sequence": 4,
                "title": "转向线下支持",
                "action": "如果已经持续失控、明显影响生活，尽快联系咨询师、可信任家人朋友或当地紧急支持。",
                "why": "这类状态往往已经超过单次自助整理能解决的范围。",
                "duration_hint": "24 小时内",
            },
        ],
        "do_not": ["不要继续逼自己想清楚所有答案", "不要在失控时做重大关系决定", "不要把求助看成失败"],
        "success_signal": "你已经从继续失控，切回到至少能先保护自己和暂停升级。",
        "escalation_rule": "如果出现持续失眠、无法进食、惊恐、自伤冲动或明显安全担忧，直接转线下专业支持。",
    }
