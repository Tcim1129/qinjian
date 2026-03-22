"""Conflict repair protocol builder.

This keeps the first version rule-based on purpose so the product can explain a
clear, competition-friendly interaction loop even when model services are slow
or unavailable.
"""

from app.models import InterventionPlan, Pair, RelationshipProfileSnapshot
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
    protocol["active_plan_type"] = active_plan.plan_type if active_plan else None
    protocol["focus_tags"] = focus_tags
    protocol["model_family"] = "rule_engine_with_safety_first"
    protocol["clinical_disclaimer"] = (
        "修复协议用于一般关系冲突与沟通修复，不替代法律、医疗或专业心理支持；若存在暴力、自伤他伤或强控制风险，应直接转专业支持。"
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
        "修复协议基于最近的风险等级、关系画像和当前计划生成，"
        "它用于帮助双方降温和重建沟通，不替代专业判断。"
    )
    protocol["safety_handoff"] = _build_protocol_handoff(crisis_level)
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


def _build_protocol_evidence(
    *,
    crisis_level: str,
    active_plan: InterventionPlan | None,
    snapshot: RelationshipProfileSnapshot | None,
) -> list[str]:
    evidence: list[str] = []
    normalized = str(crisis_level or "none")
    evidence.append(f"当前风险等级为 {normalized}，修复节奏会先围绕止损还是推进来设计。")
    if active_plan:
        goal = (active_plan.goal_json or {}).get("primary_goal") or active_plan.plan_type
        evidence.append(f"当前激活计划的主要目标是：{goal}。")
    metrics = (snapshot.metrics_json or {}) if snapshot else {}
    overlap = metrics.get("interaction_overlap_rate")
    if overlap is not None:
        evidence.append(
            f"近阶段互动重合率约为 {round(float(overlap) * 100)}%，会影响系统对连接是否在回暖的判断。"
        )
    crisis_count = metrics.get("crisis_event_count")
    if crisis_count:
        evidence.append(f"近阶段已记录 {int(crisis_count)} 次风险事件，所以协议会更保守。")
    return evidence[:4]


def _build_protocol_handoff(crisis_level: str) -> str | None:
    if crisis_level not in {"moderate", "severe"}:
        return None
    return (
        "如果已经出现持续升级、威胁、羞辱、肢体伤害风险或明显失控，"
        "请停止继续推进对话，转向可信任的人、专业咨询或当地紧急支持。"
    )


def _stable_protocol(*, is_long_distance: bool) -> dict:
    sync_hint = "先用文字铺垫，再约一个 10 分钟视频确认。" if is_long_distance else "直接找一个不被打断的 10 分钟窗口。"
    return {
        "protocol_type": "steady_maintenance",
        "title": "低压维护协议",
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
        "escalation_rule": "如果对方连续两次回避或情绪明显升高，再切换到中度修复协议。",
    }


def _mild_protocol(*, is_long_distance: bool) -> dict:
    channel_hint = "先文字确认情绪，再约一个短通话。" if is_long_distance else "最好面对面或语音，不建议纯文字硬谈。"
    return {
        "protocol_type": "gentle_repair",
        "title": "轻度修复协议",
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
                "why": "感受更容易被接住，指责更容易引发防御。",
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
        "escalation_rule": "如果沟通后仍持续冷淡 24 小时以上，切换到中度修复协议。",
    }


def _moderate_protocol(*, is_long_distance: bool) -> dict:
    channel_hint = "优先视频或语音，尽量不要只靠长段文字。" if is_long_distance else "优先面对面，至少保证实时沟通。"
    return {
        "protocol_type": "structured_repair",
        "title": "中度修复协议",
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
        "escalation_rule": "如果出现辱骂、羞辱、断联或反复爆发，立即切换到严重修复协议并考虑专业帮助。",
    }


def _severe_protocol(*, is_long_distance: bool) -> dict:
    distance_note = "先停止高强度文字拉扯，只保留安全确认和必要沟通。" if is_long_distance else "先停止当场拉扯，确保双方先离开高压场景。"
    return {
        "protocol_type": "de_escalation_protocol",
        "title": "严重冲突止损协议",
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
