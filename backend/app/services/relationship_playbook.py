"""Seven-day relationship playbook builder."""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intervention_effectiveness import build_intervention_scorecard
from app.services.intervention_theory import build_playbook_theory_basis

PLAYBOOK_TEMPLATES = {
    "low_connection_recovery": {
        "title": "7天重新连上线",
        "summary": "先把压力降下来，再慢慢恢复共同节奏和深聊。",
        "days": [
            {
                "title": "先把连接窗口约出来",
                "theme": "reset",
                "objective": "恢复一个可兑现的连接时段",
                "action": "今晚先约一个10分钟、不解决问题的轻连接窗口。",
                "reduce_load": "如果今天都很累，只确认一个明天更容易兑现的时间。",
                "deepen": "确定时间后，再补一句今天最想被理解的感受。",
                "stabilize": "如果气氛紧绷，先只确认“我们明天再聊也可以”。",
                "success_signal": "双方都愿意留下下一次连接窗口。",
                "checkin_prompt": "今天这次连接更像靠近，还是更像任务？",
            },
            {
                "title": "交换一句真实感受",
                "theme": "warmup",
                "objective": "让交流回到真实而不是流程",
                "action": "各自只说一句今天最真实的感受，不解释对错。",
                "reduce_load": "只说“我今天最强的感受是……”。",
                "deepen": "在感受后补一句“我最希望你怎么接住我”。",
                "stabilize": "如果有防御感，只说感受，不提要求。",
                "success_signal": "出现至少一句不带指责的真感受。",
                "checkin_prompt": "哪一句让你感觉更被看见？",
            },
            {
                "title": "对齐一个小误会",
                "theme": "clarify",
                "objective": "先清掉最小的一处错位",
                "action": "只挑一件最近最容易误会的小事来对齐版本。",
                "reduce_load": "如果今天状态一般，只先确认“那天我们理解不一样”。",
                "deepen": "对齐完版本后，再说一句自己真正想表达的初衷。",
                "stabilize": "不翻旧账，只讲这一件事。",
                "success_signal": "双方能说出“原来你当时是这样理解的”。",
                "checkin_prompt": "这次对齐之后，误会感下降了吗？",
            },
            {
                "title": "重新建一个微仪式",
                "theme": "ritual",
                "objective": "把连接从偶然变成节奏",
                "action": "约定一个本周能坚持的小仪式，比如晚安、语音或同步吃饭。",
                "reduce_load": "仪式先做得更小，只保留一个最容易坚持的动作。",
                "deepen": "在仪式里加一句固定表达感谢或确认。",
                "stabilize": "先不要追求频率，只求能兑现。",
                "success_signal": "你们都觉得这个动作现实可行。",
                "checkin_prompt": "什么样的仪式最不容易变成负担？",
            },
            {
                "title": "补一次积极确认",
                "theme": "repair",
                "objective": "让关系不只围着问题转",
                "action": "各自说一件最近感谢对方的小事。",
                "reduce_load": "如果今天难开口，就先发一句简短感谢。",
                "deepen": "感谢之后补一句“这为什么对我重要”。",
                "stabilize": "只说感谢，不夹带批评。",
                "success_signal": "积极确认能被接住而不是被回避。",
                "checkin_prompt": "哪种确认最容易被你真正听进去？",
            },
            {
                "title": "说清下周最需要的支持",
                "theme": "expectation",
                "objective": "把期待从猜测变成可说",
                "action": "各自说一件下周最需要对方支持的小事。",
                "reduce_load": "只提一个最小支持请求，不要列清单。",
                "deepen": "请求之后说明“做到这件事我会安心很多”。",
                "stabilize": "请求要具体，不评价过去。",
                "success_signal": "至少有一个请求听起来明确又能兑现。",
                "checkin_prompt": "你提的请求有被认真对待吗？",
            },
            {
                "title": "复盘哪一步最有用",
                "theme": "review",
                "objective": "把有效动作留下来",
                "action": "一起复盘这周哪一步最有用，并留下下周继续保留的一步。",
                "reduce_load": "只保留最轻、最能坚持的一步带进下周。",
                "deepen": "除了保留动作，再补一句你希望下周更进一步的方向。",
                "stabilize": "先看有效动作，不急着总结所有问题。",
                "success_signal": "你们能明确说出下周继续保留的一步。",
                "checkin_prompt": "这周最值得带走的一步是什么？",
            },
        ],
    },
    "conflict_repair_plan": {
        "title": "7天冲突修复剧本",
        "summary": "先止损降温，再慢慢恢复安全沟通和修复动作。",
        "days": [
            {
                "title": "先停下升级",
                "theme": "de-escalate",
                "objective": "先把冲突强度降下来",
                "action": "约定一个暂停时段，今天先不继续升级争执。",
                "reduce_load": "只确认“我们晚点再说”，不追求现在讲清楚。",
                "deepen": "暂停时顺带约一个具体回到对话的时间。",
                "stabilize": "如果情绪还高，优先拉开时间和空间。",
                "success_signal": "冲突没有继续往上顶。",
                "checkin_prompt": "这次暂停是缓和了，还是更悬着了？",
            },
            {
                "title": "各说一件事实",
                "theme": "fact",
                "objective": "把事实和解读先分开",
                "action": "各自只说一件自己确认发生过的事实，不猜动机。",
                "reduce_load": "如果怕又吵起来，就先写下来再发。",
                "deepen": "事实说完后，加一句“我当时最在意的是……”。",
                "stabilize": "不抢结论，只把事实放桌上。",
                "success_signal": "你们开始在同一件事上对齐版本。",
                "checkin_prompt": "哪一句事实最让误会变少？",
            },
            {
                "title": "说感受，不给定性",
                "theme": "feeling",
                "objective": "把受伤感说出来，而不是继续贴标签",
                "action": "各自用“我感到……”表达感受，不评价对方人格。",
                "reduce_load": "只说一种最强烈的感受，别一次讲太多。",
                "deepen": "感受后面补一句“这件事触发了我什么担心”。",
                "stabilize": "避免“你总是”“你就是”。",
                "success_signal": "对话里开始出现感受而不是攻击。",
                "checkin_prompt": "你今天的感受有被听到吗？",
            },
            {
                "title": "说一个核心需求",
                "theme": "need",
                "objective": "把修复指向明确需求",
                "action": "各自只说一个最核心的需要，比如被回应、被尊重或被解释。",
                "reduce_load": "只说一个需求，不同时提要求和批评。",
                "deepen": "再补一句对方做到后你会更安心的原因。",
                "stabilize": "需求要落地，不要抽象指责。",
                "success_signal": "至少有一个需求变得足够具体。",
                "checkin_prompt": "哪个需求最值得先被满足？",
            },
            {
                "title": "做一个修复动作",
                "theme": "repair",
                "objective": "让修复从说变成做",
                "action": "选一个可兑现的小修复动作，比如解释、确认、道歉或补偿。",
                "reduce_load": "动作越小越好，重点是今天能做到。",
                "deepen": "修复动作后补一句“以后我会怎么提前避免”。",
                "stabilize": "别一次承诺太多，先兑现一件。",
                "success_signal": "有一件修复动作真的落了地。",
                "checkin_prompt": "哪种修复动作最让你感觉事情开始往回走？",
            },
            {
                "title": "重新连一次线",
                "theme": "reconnect",
                "objective": "把关系从问题模式拉回连接模式",
                "action": "安排一次不以解决冲突为主的小连接，比如散步、吃饭或语音。",
                "reduce_load": "连接时间控制在10到15分钟，别让它变重。",
                "deepen": "连接里补一句“这几天我最珍惜你的一点”。",
                "stabilize": "不要在连接时顺手重启争论。",
                "success_signal": "你们能短暂回到不是敌对的状态。",
                "checkin_prompt": "今天的连接有把人拉回来一点吗？",
            },
            {
                "title": "复盘冲突触发点",
                "theme": "review",
                "objective": "把这次争执变成下次少踩坑的经验",
                "action": "一起复盘这次最早的触发点和下次更好的处理方式。",
                "reduce_load": "如果复盘容易再吵，就只各说一条经验。",
                "deepen": "再约一个下次出现同类情况时的暗号或停损动作。",
                "stabilize": "先看模式，不追究输赢。",
                "success_signal": "你们能说出下次怎么更早刹车。",
                "checkin_prompt": "这次冲突最早是从哪一步开始失控的？",
            },
        ],
    },
    "distance_compensation_plan": {
        "title": "7天异地补偿剧本",
        "summary": "把联系从随机补救，变成能兑现的节奏和陪伴感。",
        "days": [
            {
                "title": "先定一个能兑现的连接点",
                "theme": "anchor",
                "objective": "先把异地联系变成具体安排",
                "action": "先约一次本周最容易兑现的远程陪伴。",
                "reduce_load": "先定时间，不定内容也可以。",
                "deepen": "时间定下后，再定一个小主题。",
                "stabilize": "如果最近状态乱，就只做最短的一次。",
                "success_signal": "至少有一次连接被真正排进日程。",
                "checkin_prompt": "什么时间最容易让你们都不觉得赶？",
            },
            {
                "title": "补一个日常陪伴动作",
                "theme": "presence",
                "objective": "让陪伴感进入日常",
                "action": "各自补一个低门槛陪伴动作，比如语音、照片或一句晚安。",
                "reduce_load": "只做一个最轻动作，不要同时做很多。",
                "deepen": "动作后补一句今天最想分享的小瞬间。",
                "stabilize": "重在出现，不重在完美。",
                "success_signal": "陪伴开始变得更像日常而不是任务。",
                "checkin_prompt": "什么样的陪伴最容易被你感受到？",
            },
            {
                "title": "做一次同步体验",
                "theme": "co-experience",
                "objective": "增加共同经历而不只是交换信息",
                "action": "一起做一件同步小事，比如吃同一顿饭、看同一段视频。",
                "reduce_load": "体验不用完整，哪怕一起听10分钟也算。",
                "deepen": "结束后互相说一句最喜欢的片段。",
                "stabilize": "别把流程搞复杂，先保住完成率。",
                "success_signal": "你们开始有“像在一起做过一件事”的感觉。",
                "checkin_prompt": "哪种同步体验最让你觉得像一起生活？",
            },
            {
                "title": "说一句异地里最难的点",
                "theme": "reveal",
                "objective": "把异地里的隐性消耗说清楚",
                "action": "各自说一句异地最难受的地方，不互相防御。",
                "reduce_load": "只说一件最主要的难点。",
                "deepen": "再补一句你最希望对方怎么支持你。",
                "stabilize": "只说体验，不急着找责任。",
                "success_signal": "难受的部分开始被看见而不是被带过。",
                "checkin_prompt": "对方听完后，你有被理解一点吗？",
            },
            {
                "title": "补一个确定性承诺",
                "theme": "certainty",
                "objective": "让关系更有“稳住”的感觉",
                "action": "约定一个下周继续保留的固定陪伴点。",
                "reduce_load": "频率先低一点，但一定要能做到。",
                "deepen": "在承诺里加入一句固定确认的话。",
                "stabilize": "不做超出现实的承诺。",
                "success_signal": "陪伴开始从随机变成有预期。",
                "checkin_prompt": "什么样的承诺最让你安心？",
            },
            {
                "title": "创造一点小期待",
                "theme": "anticipation",
                "objective": "让异地不只剩下维持",
                "action": "一起约一个值得期待的小主题，比如周末小约会或共同清单。",
                "reduce_load": "期待感先从很小的安排开始。",
                "deepen": "一起把主题说得更具体一点。",
                "stabilize": "别把期待变成压力。",
                "success_signal": "你们开始对下一次连接有点盼头。",
                "checkin_prompt": "这周最想一起完成的小期待是什么？",
            },
            {
                "title": "复盘最有陪伴感的一步",
                "theme": "review",
                "objective": "留下真正有效的异地补偿动作",
                "action": "一起复盘这周最有陪伴感的一步，并保留下周继续。",
                "reduce_load": "只保留最轻但最有效的一步。",
                "deepen": "再补一句下周想升级的方向。",
                "stabilize": "先留住有效动作，不急着做大。",
                "success_signal": "你们能明确保留一个最有感觉的节奏。",
                "checkin_prompt": "哪一步最像真正把距离拉近了？",
            },
        ],
    },
    "self_regulation_plan": {
        "title": "7天自我调节剧本",
        "summary": "先稳定自己，再决定怎么向关系里输出。",
        "days": [
            {
                "title": "先把节奏慢下来",
                "theme": "grounding",
                "objective": "先把自己稳住",
                "action": "今天先做一个10分钟的调节动作，比如散步、呼吸或写一句感受。",
                "reduce_load": "动作越小越好，只求开始。",
                "deepen": "调节后补一句“我现在比刚才更怎样了”。",
                "stabilize": "先不逼自己解释所有情绪。",
                "success_signal": "你能感觉到状态至少稍微慢下来一点。",
                "checkin_prompt": "什么动作最能让你先稳住？",
            },
            {
                "title": "识别今天最强的触发点",
                "theme": "trigger",
                "objective": "把混乱感变清楚一点",
                "action": "写下今天最强的一个触发点和它带来的身体或情绪反应。",
                "reduce_load": "只记一个触发点，不做长复盘。",
                "deepen": "再补一句“我其实在害怕什么”。",
                "stabilize": "重点是识别，不是立刻解决。",
                "success_signal": "你能说清今天最主要的触发点。",
                "checkin_prompt": "今天最容易把你带乱的是什么？",
            },
            {
                "title": "说出一个当下需求",
                "theme": "need",
                "objective": "让需要不再只停在心里",
                "action": "说出今天最需要的一件事，比如空间、安静、回应或陪伴。",
                "reduce_load": "如果难开口，就先写给自己。",
                "deepen": "再补一句这件需要为什么重要。",
                "stabilize": "需求不用完美，只要真。",
                "success_signal": "你能更诚实地看见自己的需要。",
                "checkin_prompt": "今天你最需要的到底是什么？",
            },
            {
                "title": "练习一个低压力表达",
                "theme": "expression",
                "objective": "把需求说得更容易被接住",
                "action": "试着用一句低压力表达把今天的状态说出来。",
                "reduce_load": "先用一句最短表达，不解释太多。",
                "deepen": "说完后补一句你希望对方怎么回应。",
                "stabilize": "只说此刻，不翻旧账。",
                "success_signal": "你说出口时没有明显更紧绷。",
                "checkin_prompt": "什么说法最让你觉得既真实又不费力？",
            },
            {
                "title": "留一个自我照顾锚点",
                "theme": "anchor",
                "objective": "让调节有固定支点",
                "action": "给自己留一个每天都能做的小照顾动作。",
                "reduce_load": "先选最容易坚持的一步。",
                "deepen": "再给这个动作固定时间或场景。",
                "stabilize": "别追求完整系统，先留下一个锚。",
                "success_signal": "你知道下次状态乱时先抓哪一步。",
                "checkin_prompt": "哪一个锚点最适合留到明天？",
            },
            {
                "title": "试一次边界表达",
                "theme": "boundary",
                "objective": "把自我照顾带进关系边界",
                "action": "如果需要，试着表达一个边界，比如“我想晚点再聊”。",
                "reduce_load": "边界先说得简单、短一点。",
                "deepen": "边界后补一句你并不是在拒绝关系。",
                "stabilize": "先守住边界，不急着解释太多。",
                "success_signal": "你能表达边界而不强烈内疚。",
                "checkin_prompt": "哪种边界最值得你练习说出口？",
            },
            {
                "title": "复盘最有用的调节动作",
                "theme": "review",
                "objective": "把真正有用的方法留下来",
                "action": "复盘这周哪一步最能帮你稳下来，并保留到下周。",
                "reduce_load": "只保留一个最轻的方法。",
                "deepen": "再补一句下周想怎么继续练。",
                "stabilize": "先看有效，不苛责自己做得不够。",
                "success_signal": "你开始有一套属于自己的稳定动作。",
                "checkin_prompt": "这周最值得留下来的自我调节动作是什么？",
            },
        ],
    },
}

BRANCH_LABELS = {
    "stabilize": "止损降温",
    "reduce_load": "减压保节奏",
    "steady": "按计划推进",
    "deepen": "趁势加深",
}


def _normalize_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _pick_branch(scorecard: dict) -> tuple[str, str]:
    risk_now = str(scorecard.get("risk_now") or "none")
    momentum = str(scorecard.get("momentum") or "mixed")
    completion_rate = float(scorecard.get("completion_rate") or 0.0)
    usefulness_avg = scorecard.get("usefulness_avg")
    friction_avg = scorecard.get("friction_avg")

    if risk_now in ("moderate", "severe"):
        return "stabilize", "当前风险仍在中高位，这一周先以止损和降温为主。"
    if (
        momentum == "stalled"
        or completion_rate < 0.34
        or (friction_avg is not None and float(friction_avg) >= 3.6)
    ):
        return "reduce_load", "最近执行阻力偏高，剧本会先减压，避免节奏再次断掉。"
    if (
        momentum == "improving"
        and completion_rate >= 0.5
        and risk_now in ("none", "mild")
        and (usefulness_avg is None or float(usefulness_avg) >= 4.0)
    ):
        return "deepen", "这轮动作开始起效了，可以在不打乱节奏的前提下往前再走半步。"
    return "steady", "先按当前节奏稳步推进，避免忽轻忽重。"


def _day_status(day_index: int, current_day: int) -> str:
    if day_index < current_day:
        return "done"
    if day_index == current_day:
        return "current"
    return "upcoming"


def _resolve_action(step: dict, branch_code: str) -> str:
    if branch_code == "stabilize":
        return step.get("stabilize") or step.get("reduce_load") or step["action"]
    if branch_code == "reduce_load":
        return step.get("reduce_load") or step["action"]
    if branch_code == "deepen":
        return step.get("deepen") or step["action"]
    return step["action"]


def _focus_tags(scorecard: dict) -> list[str]:
    raw = list(scorecard.get("focus") or [])
    deduped: list[str] = []
    for item in raw:
        value = str(item or "").strip()
        if value and value not in deduped:
            deduped.append(value)
    return deduped[:4]


def _current_day(start_date: date, end_date: date | None) -> int:
    today = date.today()
    total_days = max(((end_date or start_date) - start_date).days + 1, 1)
    delta = (today - start_date).days + 1
    return max(1, min(delta, total_days))


def _total_days(start_date: date, end_date: date | None, default_days: int) -> int:
    if end_date:
        return max((end_date - start_date).days + 1, 1)
    return max(default_days, 1)


async def build_relationship_playbook(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
) -> dict | None:
    normalized_pair_id = _normalize_uuid(pair_id)
    normalized_user_id = _normalize_uuid(user_id)
    if (normalized_pair_id is None) == (normalized_user_id is None):
        raise ValueError("build_relationship_playbook requires exactly one scope")

    scorecard = await build_intervention_scorecard(
        db,
        pair_id=normalized_pair_id,
        user_id=normalized_user_id,
    )
    if not scorecard or scorecard.get("status") != "active":
        return None

    template = PLAYBOOK_TEMPLATES.get(scorecard["plan_type"])
    if not template:
        return None

    branch_code, branch_reason = _pick_branch(scorecard)
    total_days = min(
        _total_days(
            scorecard["start_date"],
            scorecard.get("end_date"),
            len(template["days"]),
        ),
        len(template["days"]),
    )
    current_day = min(
        _current_day(scorecard["start_date"], scorecard.get("end_date")),
        total_days,
    )

    days: list[dict] = []
    for index, step in enumerate(template["days"][:total_days], start=1):
        days.append(
            {
                "day_index": index,
                "label": f"Day {index}",
                "title": step["title"],
                "theme": step["theme"],
                "objective": step["objective"],
                "action": _resolve_action(step, branch_code),
                "success_signal": step.get("success_signal"),
                "checkin_prompt": step.get("checkin_prompt"),
                "branch_mode": branch_code,
                "branch_mode_label": BRANCH_LABELS[branch_code],
                "status": _day_status(index, current_day),
            }
        )

    today_card = days[current_day - 1]
    return {
        "plan_id": scorecard["plan_id"],
        "pair_id": scorecard.get("pair_id"),
        "user_id": scorecard.get("user_id"),
        "plan_type": scorecard["plan_type"],
        "title": template["title"],
        "summary": template["summary"],
        "primary_goal": scorecard.get("primary_goal"),
        "momentum": scorecard["momentum"],
        "risk_level": scorecard.get("risk_now") or scorecard.get("risk_level"),
        "active_branch": branch_code,
        "active_branch_label": BRANCH_LABELS[branch_code],
        "branch_reason": branch_reason,
        "focus_tags": _focus_tags(scorecard),
        "model_family": "rule_engine_with_feedback_loop",
        "clinical_disclaimer": "当前剧本是基于关系心理学与行为科学启发的工程化干预方案，不替代正式心理治疗或临床判断。",
        "theory_basis": build_playbook_theory_basis(
            plan_type=scorecard["plan_type"],
            branch_code=branch_code,
        ),
        "current_day": current_day,
        "total_days": total_days,
        "today_card": today_card,
        "days": days,
    }
