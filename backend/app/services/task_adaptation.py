"""Adaptive daily-task shaping based on intervention momentum."""

import random
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intervention_effectiveness import build_intervention_scorecard
from app.services.task_feedback import build_feedback_preference_profile
from app.services.intervention_theory import build_task_strategy_theory_basis


def _task(
    *,
    title: str,
    description: str,
    category: str,
    target: str = "both",
) -> dict:
    return {
        "title": title,
        "description": description,
        "target": target,
        "category": category,
    }


def _normalize_uuid(value: str | uuid.UUID) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _anchor_task_for_plan(plan_type: str | None, intensity: str) -> dict | None:
    anchors = {
        "low_connection_recovery": {
            "light": {
                "title": "只做一次低压力连接",
                "description": "今晚只约一个 10 分钟的小连接，不追求聊深，只先把节奏接上。",
                "target": "both",
                "category": "connection",
            },
            "steady": {
                "title": "恢复一次稳定连线",
                "description": "安排一段不会被打断的 10 到 15 分钟交流，先把今天最想被理解的一点说清楚。",
                "target": "both",
                "category": "communication",
            },
            "stretch": {
                "title": "完成一次高质量连线",
                "description": "今晚做一次 15 分钟高质量交流，除了近况，也补一句最近最感谢对方的地方。",
                "target": "both",
                "category": "communication",
            },
        },
        "conflict_repair_plan": {
            "light": {
                "title": "先暂停升级",
                "description": "今天先不求讲清全部问题，只保留一个降温动作，比如暂停争执或确认稍后再聊。",
                "target": "both",
                "category": "repair",
            },
            "steady": {
                "title": "只对齐一个分歧点",
                "description": "选一个最核心的误会来讲，先说感受，再说需求，不顺手带出第二件事。",
                "target": "both",
                "category": "repair",
            },
            "stretch": {
                "title": "做一次结构化修复对话",
                "description": "安排一次 15 分钟修复对话，按事实、感受、需求的顺序说，并在最后确认下一步。",
                "target": "both",
                "category": "repair",
            },
        },
        "distance_compensation_plan": {
            "light": {
                "title": "先固定一次陪伴动作",
                "description": "今天先定下一次可兑现的异地陪伴，不需要复杂，只要可执行。",
                "target": "both",
                "category": "activity",
            },
            "steady": {
                "title": "补一次远程陪伴",
                "description": "今晚完成一次短但稳定的远程陪伴，比如视频、共看或同步吃饭。",
                "target": "both",
                "category": "activity",
            },
            "stretch": {
                "title": "做一次带仪式感的异地连接",
                "description": "把远程交流升级成一次有主题的小约会，并在结束时约好下一次节奏。",
                "target": "both",
                "category": "activity",
            },
        },
        "self_regulation_plan": {
            "light": {
                "title": "先做一件最轻的自我照顾",
                "description": "今天先完成一个 10 分钟的自我调节动作，比如散步、深呼吸或写一句感受。",
                "target": "both",
                "category": "reflection",
            },
            "steady": {
                "title": "记录并照顾自己的节律",
                "description": "今天先看见自己最容易被触发的时刻，再配一个可以执行的稳定动作。",
                "target": "both",
                "category": "reflection",
            },
            "stretch": {
                "title": "完成一次带复盘的自我调节",
                "description": "今天做完调节动作后，再记一句什么方式最能让自己慢下来。",
                "target": "both",
                "category": "reflection",
            },
        },
    }
    plan_anchors = anchors.get(plan_type or "")
    if not plan_anchors:
        return None
    return dict(plan_anchors.get(intensity, plan_anchors.get("steady")))


SYSTEM_TASK_PACKS = {
    "default": {
        "light": [
            _task(
                title="先把今天的连接留出来",
                description="约一个 10 分钟能兑现的小窗口，先不用聊很多。",
                category="connection",
            ),
            _task(
                title="只说一句真实感受",
                description="只说一句今天最真实的感受，不解释对错。",
                category="communication",
            ),
            _task(
                title="记下一句有用的话",
                description="做完后写一句，留住今天最容易被听进去的表达。",
                category="reflection",
            ),
        ],
        "steady": [
            _task(
                title="完成一次 10 分钟连线",
                description="留一段不会被打断的 10 分钟，先把节奏接上。",
                category="connection",
            ),
            _task(
                title="说清一个小需要",
                description="只说一个最需要被看见的小需要，不顺手扩到第二件事。",
                category="communication",
            ),
            _task(
                title="补一句简单复盘",
                description="结束后各自留一句，看看哪种说法最自然。",
                category="reflection",
            ),
        ],
        "stretch": [
            _task(
                title="做一次稳定连线",
                description="安排 10 到 15 分钟交流，先把今天最重要的一点说清楚。",
                category="connection",
            ),
            _task(
                title="补一句感谢或确认",
                description="在表达之后，再补一句感谢或确认，让关系别只围着问题转。",
                category="communication",
            ),
            _task(
                title="留住今天有效的一步",
                description="写一句今天最值得保留的动作，明天还能继续沿用。",
                category="reflection",
            ),
        ],
    },
    "low_connection_recovery": {
        "light": [
            _task(
                title="先约一个轻连接时间",
                description="今晚先约一个 10 分钟窗口，只求能兑现。",
                category="connection",
            ),
            _task(
                title="各说一句真实感受",
                description="只说一句今天最真实的感受，不急着讲道理。",
                category="communication",
            ),
            _task(
                title="记下哪句话更靠近",
                description="做完后留一句，看看哪种表达更容易让关系回温。",
                category="reflection",
            ),
        ],
        "steady": [
            _task(
                title="完成一次 10 分钟连接",
                description="安排一段 10 分钟交流，先把联系接回来。",
                category="connection",
            ),
            _task(
                title="对齐一个小误会",
                description="只挑一件最容易误会的小事，先讲版本，不翻旧账。",
                category="communication",
            ),
            _task(
                title="留住一个可继续的小动作",
                description="写一句下次还愿意继续做的小动作，保持节奏就够了。",
                category="reflection",
            ),
        ],
        "stretch": [
            _task(
                title="做一次高质量连线",
                description="留出 10 到 15 分钟，把今天最想被理解的一点说清楚。",
                category="connection",
            ),
            _task(
                title="补一句感谢",
                description="在交流后补一句感谢，让关系不只停在修复上。",
                category="communication",
            ),
            _task(
                title="写下最想保留的节奏",
                description="留一句今天最有效的节奏，明天继续按这个强度走。",
                category="reflection",
            ),
        ],
    },
    "conflict_repair_plan": {
        "light": [
            _task(
                title="先停 10 分钟",
                description="先暂停升级，给彼此 10 分钟缓一缓。",
                category="connection",
            ),
            _task(
                title="只讲一个点",
                description="只说这次最卡的一件事，不顺手带第二件。",
                category="repair",
            ),
            _task(
                title="记下下次怎么更早停",
                description="做完后留一句，下次出现同样情况时怎么更早刹车。",
                category="reflection",
            ),
        ],
        "steady": [
            _task(
                title="先确认还能继续聊",
                description="先确认一个 10 分钟的回到对话时间，不急着现在讲完。",
                category="connection",
            ),
            _task(
                title="按感受和需要说一个点",
                description="只说一个分歧点，先讲感受，再讲需要。",
                category="repair",
            ),
            _task(
                title="写下今天有效的修复动作",
                description="留一句今天哪种做法最能让局面慢下来。",
                category="reflection",
            ),
        ],
        "stretch": [
            _task(
                title="安排一次短修复对话",
                description="留 10 到 15 分钟，只处理这次最核心的误会。",
                category="connection",
            ),
            _task(
                title="补一个可兑现的小修复",
                description="在表达之后，确认一个今天就能做到的小修复动作。",
                category="repair",
            ),
            _task(
                title="记下以后怎么避免重复",
                description="留一句下次遇到类似情况时，最值得先做的第一步。",
                category="reflection",
            ),
        ],
    },
    "distance_compensation_plan": {
        "light": [
            _task(
                title="先定一次远程连接",
                description="先约一次 10 分钟能兑现的远程陪伴，不用复杂。",
                category="connection",
            ),
            _task(
                title="发一个低压力陪伴动作",
                description="补一个轻动作，比如一张照片、一句晚安或一段语音。",
                category="activity",
            ),
            _task(
                title="记下什么最有陪伴感",
                description="做完后留一句，看看什么最像真的靠近了一点。",
                category="reflection",
            ),
        ],
        "steady": [
            _task(
                title="完成一次短陪伴",
                description="留 10 分钟做一次稳定陪伴，比如语音、共看或同步吃饭。",
                category="connection",
            ),
            _task(
                title="分享一个今天的小瞬间",
                description="只分享一个小片段，让联系更像一起过日常。",
                category="activity",
            ),
            _task(
                title="写下下次还想继续什么",
                description="留一句今天最值得延续的陪伴方式。",
                category="reflection",
            ),
        ],
        "stretch": [
            _task(
                title="做一次有主题的陪伴",
                description="安排 10 到 15 分钟远程陪伴，给这次联系一个简单主题。",
                category="connection",
            ),
            _task(
                title="补一个值得期待的小安排",
                description="在结束前顺手约一个下次还愿意做的小安排。",
                category="activity",
            ),
            _task(
                title="记下最能拉近距离的环节",
                description="留一句今天最像一起生活的一步，后面继续保留。",
                category="reflection",
            ),
        ],
    },
    "self_regulation_plan": {
        "light": [
            _task(
                title="先给自己 10 分钟缓冲",
                description="先做一个 10 分钟的稳定动作，比如散步或深呼吸。",
                category="connection",
            ),
            _task(
                title="说一句现在的状态",
                description="只说一句你现在的状态，不要求一次讲透。",
                category="communication",
            ),
            _task(
                title="记下什么最能稳住自己",
                description="做完后留一句，方便下次状态起伏时直接用。",
                category="reflection",
            ),
        ],
        "steady": [
            _task(
                title="做一次稳定节律动作",
                description="留出 10 分钟做一个让自己慢下来的动作。",
                category="connection",
            ),
            _task(
                title="表达一个边界或需要",
                description="只表达一个现在最需要被照顾的边界或需要。",
                category="communication",
            ),
            _task(
                title="留一句自我复盘",
                description="写一句今天哪种方式最能让自己恢复节律。",
                category="reflection",
            ),
        ],
        "stretch": [
            _task(
                title="先把自己稳住再进入关系",
                description="先做一个稳定动作，再进入今天最想说的一件事。",
                category="connection",
            ),
            _task(
                title="说清一个小需要",
                description="只提一个小需要，让对方知道怎样回应你。",
                category="communication",
            ),
            _task(
                title="记下以后还能继续用的做法",
                description="留一句最适合下次复用的自我调节方法。",
                category="reflection",
            ),
        ],
    },
}


def _dedupe_tasks(tasks: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[str] = set()
    for task in tasks:
        title = str(task.get("title") or "").strip()
        key = title.lower()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(task)
    return deduped


def build_simple_daily_tasks(strategy: dict) -> list[dict]:
    plan_type = str(strategy.get("plan_type") or "default").strip() or "default"
    intensity = str(strategy.get("intensity") or "steady").strip() or "steady"
    plan_pack = SYSTEM_TASK_PACKS.get(plan_type) or SYSTEM_TASK_PACKS["default"]
    tasks = plan_pack.get(intensity) or plan_pack.get("steady") or []
    return [dict(task) for task in tasks[:3]]


MAX_DAILY_NOTE_LENGTH = 28


def clamp_daily_note_length(note: str, max_chars: int = MAX_DAILY_NOTE_LENGTH) -> str:
    cleaned = str(note or "").strip()
    if not cleaned:
        return "今天挑两三件没负担的小事，慢慢找回舒服节奏~"
    if len(cleaned) <= max_chars:
        return cleaned
    truncated = cleaned[:max_chars - 1].rstrip("，,、；;。.~ ") + "~"
    return truncated


DAILY_NOTE_POOLS: dict[tuple[str, str], list[str]] = {
    ("conflict_repair_plan", "light"): [
        "今天先做轻一点的三步，先把局面慢下来。",
        "累了就先各自缓一缓，不用急着在今天把话说满~",
        "先给彼此留点呼吸空间，温暖比争高下更重要~",
        "今天挑最轻巧的小事做，先不急着争论对错呀~",
    ],
    ("conflict_repair_plan", "stretch"): [
        "今天先稳住，再把一个修复动作真正落地。",
        "气氛缓和后，试着轻轻递个温暖的小台阶~",
        "今天把心里的委屈放下，做个温馨的抱抱收尾~",
        "就事论事聊聊感受，多听听对方心里的软肋~",
    ],
    ("conflict_repair_plan", "steady"): [
        "今天就按这三步来，先把一个分歧点说清楚。",
        "一次只聊眼前这一件，不顺带翻以前的小账本~",
        "先把手头的小结巴解开，别让情绪带着自己走~",
        "心软是最好的降温药，语气放柔事情更好办~",
    ],
    ("low_connection_recovery", "light"): [
        "今天先把联系接回来，不用一次聊很多。",
        "随手发个可爱表情包，给对方留点小挂念~",
        "不用长篇大论，互道一句晚安就很安心啦~",
        "今天先轻轻打个招呼，舒服的节奏慢慢找回~",
    ],
    ("low_connection_recovery", "stretch"): [
        "今天可以在稳住联系的基础上，再多说深一点。",
        "聊聊今天遇到的小趣事，把生活的烟火气接上~",
        "分享一首好听的歌，让彼此的感觉悄悄靠近~",
        "抽空通个十分钟电话，听听声音就会安心很多~",
    ],
    ("low_connection_recovery", "steady"): [
        "今天先把节奏接上，再慢慢把话说开。",
        "找回熟悉的默契，从今天一个小问候开始~",
        "生活琐碎有人分享，平淡日子也会闪闪发光~",
        "今天挑个轻松的由头，给彼此递一句热络的话~",
    ],
    ("distance_compensation_plan", "light"): [
        "今天先保住陪伴感，不用把安排做得太满。",
        "隔着屏幕也留一点挂念，随手丢个表情包就很好~",
        "异地不慌，把今天的晚饭拍给对方看看吧~",
        "各自忙完互道辛苦，平平淡淡也是长久陪伴~",
    ],
    ("distance_compensation_plan", "stretch"): [
        "今天先把陪伴做实，再顺手留一点期待。",
        "约个周末同频看电影，给距离添点甜甜的仪式感~",
        "虽然隔着距离，睡前听听声音就能充上电啦~",
        "商量一下下次见面的小计划，日子顿时有盼头~",
    ],
    ("distance_compensation_plan", "steady"): [
        "今天就按这三步来，先把远程连接做稳。",
        "分享彼此眼前的天空，心在一起就不算遥远~",
        "把今天的碎碎念留给对方，想念有了落脚的地方~",
        "异地的默契就是各自努力、随时有回应~",
    ],
    ("default", "light"): [
        "今天先做轻一点的三步，完成就已经很好了。",
        "今天挑两三件没负担的小事，慢慢找回舒服节奏~",
        "慢慢来最舒服，不用逼自己一下做到满分状态~",
        "做一件最顺手的小行动，心里就会踏实很多呀~",
    ],
    ("default", "stretch"): [
        "今天可以在稳住节奏的基础上，多走半步。",
        "今天状态挺不错，试着多做一点用心的表达~",
        "把今天最重要的小事完成，剩下的交给明天就好~",
        "多给彼此一点耐心，好关系是在细节里长出来的~",
    ],
    ("default", "steady"): [
        "今天就做这三步，慢慢来就好。",
        "今天先顺着彼此的步调走，多一点包容与默契~",
        "先照顾好各自的心情，再开开心心一起做事~",
        "把日子过舒服，从今天这件小小的举动开始~",
    ],
}


def build_daily_task_note(
    strategy: dict,
    *,
    randomize: bool = False,
    choice_index: int | None = None,
) -> str:
    plan_type = str(strategy.get("plan_type") or "default").strip().lower()
    intensity = str(strategy.get("intensity") or "steady").strip().lower()

    key = (plan_type, intensity)
    pool = (
        DAILY_NOTE_POOLS.get(key)
        or DAILY_NOTE_POOLS.get(("default", intensity))
        or DAILY_NOTE_POOLS[("default", "steady")]
    )

    if choice_index is not None:
        note = pool[choice_index % len(pool)]
    elif randomize:
        note = random.choice(pool)
    else:
        note = pool[0]

    return clamp_daily_note_length(note)


def build_daily_pack_label(strategy: dict) -> str:
    intensity = str(strategy.get("intensity") or "steady").strip().lower()
    if intensity == "light":
        return "今天先轻一点"
    if intensity == "stretch":
        return "今天多走半步"
    return "今天就做这三步"


def _with_copy_preference(strategy: dict, profile: dict | None) -> dict:
    updated = dict(strategy)
    profile = profile or {}
    updated["copy_mode"] = profile.get("copy_mode")
    updated["copy_feedback_count"] = int(profile.get("copy_feedback_count") or 0)
    updated["copy_usefulness_avg"] = profile.get("usefulness_avg")
    updated["copy_friction_avg"] = profile.get("friction_avg")
    updated["category_preferences"] = dict(profile.get("category_preferences") or {})
    updated["theory_basis"] = build_task_strategy_theory_basis(
        plan_type=updated.get("plan_type"),
        intensity=updated.get("intensity", "steady"),
        copy_mode=updated.get("copy_mode"),
    )
    updated["clinical_disclaimer"] = (
        "任务引擎当前基于行为科学与反馈闭环做强度调整，不等于正式治疗方案，重点是提升真实执行和关系修复概率。"
    )
    return updated


def compose_task_adaptation_strategy(
    scorecard: dict | None,
    profile: dict | None = None,
) -> dict:
    return _with_copy_preference(
        build_task_adaptation_strategy(scorecard),
        profile,
    )


def build_task_adaptation_strategy(scorecard: dict | None) -> dict:
    if not scorecard:
        return {
            "intensity": "steady",
            "label": "稳定版",
            "momentum": "none",
            "task_limit": 3,
            "plan_type": None,
            "reason": "当前还没有明确干预计划，先按正常节奏给出日常任务。",
            "support_message": "先保持稳定记录和轻量互动，系统会随着你们的数据越来越懂节奏。",
        }

    momentum = scorecard.get("momentum") or "mixed"
    risk_now = str(scorecard.get("risk_now") or "none")
    plan_type = scorecard.get("plan_type")
    completion_rate = float(scorecard.get("completion_rate") or 0.0)
    usefulness_avg = scorecard.get("usefulness_avg")
    friction_avg = scorecard.get("friction_avg")
    feedback_count = int(scorecard.get("feedback_count") or 0)

    if (
        momentum == "stalled"
        or risk_now in ("moderate", "severe")
        or (feedback_count >= 2 and friction_avg is not None and float(friction_avg) >= 3.6)
        or (feedback_count >= 2 and usefulness_avg is not None and float(usefulness_avg) <= 2.8)
    ):
        return {
            "intensity": "light",
            "label": "减压版",
            "momentum": momentum,
            "task_limit": 3,
            "plan_type": plan_type,
            "reason": "最近执行阻力或主观效果不理想，系统会先把动作减轻，优先让这轮计划重新跑起来。",
            "support_message": "今天不用贪多，只把最小的一步完成就够了。",
        }

    if (
        momentum == "improving"
        and risk_now in ("none", "mild")
        and completion_rate >= 0.5
        and (usefulness_avg is None or float(usefulness_avg) >= 4.0)
        and (friction_avg is None or float(friction_avg) <= 2.8)
    ):
        return {
            "intensity": "stretch",
            "label": "进阶版",
            "momentum": momentum,
            "task_limit": 3,
            "plan_type": plan_type,
            "reason": "这轮动作已经开始起效，而且主观反馈也不错，可以在不打乱节奏的前提下，把任务稍微做深一点。",
            "support_message": "现在最适合保留有效动作，再往前多走半步。",
        }

    return {
        "intensity": "steady",
        "label": "稳定版",
        "momentum": momentum,
        "task_limit": 3,
        "plan_type": plan_type,
        "reason": "系统会继续沿着当前计划稳步推进，避免忽轻忽重。",
        "support_message": "先把稳定执行做出来，效果通常会比频繁换方向更好。",
    }


def _compact_task_description(description: str) -> str:
    text = (description or "").strip()
    if not text:
        return ""

    first_sentence = re.split(r"[。！？!?]", text)[0].strip()
    duration_match = re.search(r"(\d+\s*分钟)", text)
    if duration_match and duration_match.group(1) not in first_sentence:
        first_sentence = f"{first_sentence}（{duration_match.group(1)}）"
    return f"{first_sentence}。"


def _example_opening(task: dict, strategy: dict) -> str:
    category = str(task.get("category") or "")
    plan_type = str(strategy.get("plan_type") or "")
    if category == "repair" or plan_type == "conflict_repair_plan":
        return "我想先把今天最容易误会的那一点说清楚。"
    if category == "reflection" or plan_type == "self_regulation_plan":
        return "我现在的状态是这样，我想先照顾好自己再继续。"
    if category == "activity" or plan_type == "distance_compensation_plan":
        return "今晚我们先约一个能兑现的小陪伴，好吗？"
    return "我想先花十分钟认真和你连一下。"


def personalize_task_payloads(tasks: list[dict], strategy: dict) -> list[dict]:
    personalized: list[dict] = []
    category_preferences = strategy.get("category_preferences") or {}
    for task in tasks:
        updated = dict(task)
        category = str(updated.get("category") or "").strip().lower()
        category_preference = category_preferences.get(category) or {}
        copy_mode = category_preference.get("copy_mode") or strategy.get("copy_mode")
        if not copy_mode:
            personalized.append(updated)
            continue

        description = str(updated.get("description") or "").strip()
        if copy_mode == "clear" and description:
            updated["description"] = f"先只做这一件事：{description.rstrip('。')}。做到这一步就算完成。"
        elif copy_mode == "gentle" and description:
            updated["description"] = f"{description.rstrip('。')}。如果今天状态一般，做到一半也算推进。"
        elif copy_mode == "compact":
            updated["description"] = _compact_task_description(description)
        elif copy_mode == "example":
            example = _example_opening(updated, strategy)
            if description:
                updated["description"] = f"{description.rstrip('。')}。可以直接这样开口：{example}"
            else:
                updated["description"] = example

        updated["copy_mode"] = copy_mode
        updated["copy_mode_source"] = "category" if category_preference.get("copy_mode") else "global"
        personalized.append(updated)

    return personalized


def adapt_daily_tasks(tasks_data: list[dict], strategy: dict) -> list[dict]:
    tasks = build_simple_daily_tasks(strategy)
    if not tasks:
        tasks = [dict(task) for task in (tasks_data or []) if isinstance(task, dict)]
        anchor = _anchor_task_for_plan(
            strategy.get("plan_type"),
            strategy.get("intensity", "steady"),
        )
        if anchor:
            tasks.insert(0, anchor)
        tasks = _dedupe_tasks(tasks)[:3]

    intensity = strategy.get("intensity", "steady")
    adapted: list[dict] = []
    for index, task in enumerate(tasks):
        updated = dict(task)
        description = str(updated.get("description") or "").strip()
        if intensity == "light":
            if index == 0:
                updated["description"] = (
                    f"{description.rstrip('。') or '先把这一步做完'}。今天只要先做到这一件，就已经算有效推进。"
                )
            else:
                updated["description"] = (
                    f"{description.rstrip('。') or '把动作尽量做轻一点'}。如果今天状态一般，只完成前一项也可以。"
                )
        elif intensity == "stretch" and index == len(tasks) - 1:
            updated["description"] = (
                f"{description.rstrip('。') or '做完后多复盘一句'}。完成后再补一句什么方式最容易被听进去。"
            )
        adapted.append(updated)

    return adapted[:3]


def merge_task_insight(base_insight: str, strategy: dict) -> str:
    base = (base_insight or "").strip()
    support = str(strategy.get("support_message") or "").strip()
    if base and support:
        return f"{base} {support}"
    return base or support


async def build_pair_task_adaptation(
    db: AsyncSession,
    *,
    pair_id: str | uuid.UUID,
    user_id: str | uuid.UUID | None = None,
) -> tuple[dict, dict | None]:
    normalized_pair_id = _normalize_uuid(pair_id)
    scorecard = await build_intervention_scorecard(db, pair_id=normalized_pair_id)
    profile = await build_feedback_preference_profile(
        db,
        pair_id=normalized_pair_id,
        user_id=user_id,
    )
    strategy = compose_task_adaptation_strategy(
        scorecard,
        profile,
    )
    from app.services.policy_selection import apply_experiment_policy_selection

    strategy = await apply_experiment_policy_selection(
        db,
        pair_id=normalized_pair_id,
        viewer_user_id=_normalize_uuid(user_id) if user_id else None,
        scorecard=scorecard,
        base_strategy=strategy,
    )
    from app.services.policy_scheduling import build_policy_schedule_preview

    schedule_preview = build_policy_schedule_preview(
        scorecard=scorecard,
        strategy=strategy,
    )
    if schedule_preview:
        strategy["policy_schedule"] = schedule_preview
    return strategy, scorecard
