"""统一的亲健陪聊风格、个人习惯档案与关系语境装配服务。

同一位始终记得你和往事的亲健伙伴，根据用户所选的陪聊风格、个人中心习惯档案
以及当前正在处理的关系类型（伴侣、朋友、家人、独处），在聊一聊、多智能体、
后台分析与发前看看之间保持一致的话风与默契，不出现“换个页面就换个人”的割裂感。
"""

from __future__ import annotations

import re
from typing import Any

from app.services.crisis_processor import chat_crisis_level
from app.services.product_prefs import (
    VALID_EXPRESSION_INTENSITIES,
    VALID_TONE_PREFERENCES,
    normalize_product_prefs,
)
from app.services.tone_preference import guide_text as tone_profile_guide_text
from app.services.tone_preference import is_default as tone_profile_is_default

# 四个区分度清晰、共用同一套安全与事实底线的陪聊风格。
# 兼容历史字段值 "gentle"（映射到暖心树洞，与 "warm" 同属温柔共情档）。
COMPANION_STYLE_DEFINITIONS: dict[str, dict[str, str]] = {
    "warm": {
        "key": "warm",
        "label": "暖心树洞",
        "tagline": "真站你这边先接住委屈，软糯亲近、说话不生硬",
        "sample": "一周被临时改约两次，空出来的时间和好心情全泡汤了，换谁心里都堵得慌。先喘口气，想跟他说的话咱可以写成“下回时间有变早点跟我讲一声嘛”。",
        "instruction": (
            "当前陪聊风格是「暖心树洞」：像半夜肯听你倒苦水、稳稳护着你的知心好友。"
            "先贴着细节接住委屈、疲惫或两难，绝不端客服腔或居高临下安慰；"
            "和亲近的人提要求或商量时，把生硬的“……吗？”换成更自然亲近的“嘛 / 呀 / 啦 / 好不好”，"
            "既有柔软商量感，又不委屈自己把底线让掉。"
        ),
    },
    "direct": {
        "key": "direct",
        "label": "清醒军师",
        "tagline": "护短直给、拆穿暗刺，拒绝自证直接帮把球踢回去",
        "sample": "一周临门一脚改两次，换谁都火大。别憋着自己消化，也别卑微追问“能提前说吗”，直接把规矩立清：以后时间有变早点说，别让人干等。",
        "instruction": (
            "当前陪聊风格是「清醒军师」：先一句直击要害点破最让人憋屈的坑（有温度、护着用户、绝不当理中客），"
            "随后不绕弯、不和稀泥、不劝人当老好人。遇到阴阳怪气、甩锅或反复放鸽子时，"
            "直接帮用户拆穿对方话里的刺，拒绝陷入自证清白，利落给出反客为主、把皮球踢回去或直亮底线的做法。"
        ),
    },
    "playful": {
        "key": "playful",
        "label": "轻松嘴替",
        "tagline": "大胆放开活人幽默与俏皮拿捏，笑里带刺帮你顺气",
        "sample": "一周临时变卦两次，这是把你的档期当候补席呢？难怪越想越堵。真要回他也不用苦大仇深，一句“这周都鸽我两回啦，下回临时变卦早点吱一声呗”就能把场子拿回来。",
        "instruction": (
            "当前陪聊风格是「轻松嘴替」：大胆放开生活烟火气、机灵吐槽和四两拨千斤的嘴替感，"
            "绝不拘谨保守。少用闷闷的“我挺堵的”这种直白套话，多用带调侃、生活比喻或俏皮拉扯的活人表达，"
            "善用“呗 / 呀 / 啦 / 嘛 / 嗷 / 好哇”营造松弛微信感；"
            "亲密关系里可以带俏皮拿捏，回怼阴阳怪气可以笑里带刺把球抛回去（但绝不替用户擅自揽活）。"
            "不硬凹烂梗，不用叠字装嫩；如果用户正在崩溃大哭或遇到危机，立刻收起玩笑、稳稳托住。"
        ),
    },
    "concise": {
        "key": "concise",
        "label": "清爽整理",
        "tagline": "半句立住立场，不啰嗦不套话，直接给利落方案",
        "sample": "一周两次临时改约确实打乱安排。两条路：温和提个醒（下回早点吱一声呗），或者直接立规矩（以后临时改提前说，别让我白等）。",
        "instruction": (
            "当前陪聊风格是「清爽整理」：半句平实接住处境并亮明站在用户这边，不煽情、不黏糊、不写长篇分析、"
            "不写客服套话，严禁替用户补没说过的对话经过；用最短、最利落的篇幅把卡点、可选态度和能直接发的话讲清楚。"
        ),
    },
}

EXPRESSION_INTENSITY_DEFINITIONS: dict[str, dict[str, str]] = {
    "soft": {
        "key": "soft",
        "label": "温和留余地",
        "tagline": "真正放软、先给台阶，敏感对方也受得了，自己发出去不心慌",
        "instruction": (
            "当前表达力度档位是「温和留余地」：这是给容易起防备的对方、或自己不敢说重话的用户准备的“真软档”。"
            "硬性要求：温和档写给对方的话，绝不用“这周两次都……我心里挺堵的/不舒服”“你又……”这种数落算账式开头，"
            "也绝不用“行吧”“那你去吧”“随便你”这类暗含赌气或冷脸的起手！"
            "先化掉控诉感——按当前关系类型给出真正低防御的软话：情侣就往轻软、轻微撒娇/盼着见面的甜软方向走（让对方听完反而心软想哄）；"
            "夫妻就往过日子的体谅、留面子和商量错开安排走（平实不腻歪、不让用户发着尴尬，也让对方完全没有被审问的感觉）；"
            "朋友或挚友就用自然热络的口语递台阶。尽量避开生硬的“吗”，善用“嘛 / 呀 / 啦 / 好不好”或平缓体谅句；遇到内涵优先装傻直译接住或轻巧换题，不卑微认错。"
        ),
    },
    "balanced": {
        "key": "balanced",
        "label": "自然有态度",
        "tagline": "活人微信感，兼顾对方承受度与自己不委屈",
        "instruction": (
            "当前表达力度档位是「自然有态度」：像平时反应快、有分寸的真人回微信。"
            "少用死板客服式的“……吗？”，日常沟通按关系亲疏善用“嘛 / 呗 / 呀 / 啦 / 呐 / 嗷”；"
            "态度清楚但不刻意扎人、不刻薄，既不委屈自己当老好人，也不平白把对方逼进防御态。"
        ),
    },
    "sharp": {
        "key": "sharp",
        "label": "硬气不吃亏",
        "tagline": "大胆直球、拒绝自证，反客为主把球踢回去",
        "instruction": (
            "当前表达力度档位是「硬气不吃亏」：大胆放开、鲜明护短、绝不替用户委屈求全！"
            "遇到阴阳怪气、职场拉踩、甩锅或反复不守约时，坚决拒绝陷入“自证清白”陷阱，"
            "优先用冷静反问、四两拨千斤反讽或直白亮底线把皮球踢回给对方，让对方自己圆场；"
            "在硬气档位下不要用“嘛 / 好不好 / 呀”把锋芒揉软，也不要在末尾补“不是不想理你”这类弱化底线的讨好解释；"
            "写给对方的话必须像真人在微信上发的利落大白话——不要写“这让我很不高兴”“我很不满；”这类书面翻译腔，"
            "不要直接把用户的吐槽复述一遍，也不用“我同意了你再决定”这种居高临下命令句，直接把具体时段或共同商量的规矩干脆摊在明面上。"
            "硬气不等于失控：绝不骂脏话、不人身侮辱、不威胁恐吓、不泄露隐私，也不编造事实或替用户揽活。"
        ),
    },
}

_STYLE_ALIAS_MAP: dict[str, str] = {
    "gentle": "warm",
    "warm": "warm",
    "direct": "direct",
    "playful": "playful",
    "concise": "concise",
}

RELATIONSHIP_CONTEXT_GUIDES: dict[str, str] = {
    "couple": (
        "当前处理的是「情侣/恋爱伴侣」关系：恋爱期重情绪流动、被偏爱感与轻松拉扯，不要写成已婚开家庭会的说教腔。"
        "温和档可以真软、带一点轻撒娇或盼着见面的温度（仅作语感参考，不编未发生细节：“好想见你呀，白期待了半天，下回临时有事早点跟我吱一声好不好”）；"
        "自然档带轻松互动感（如“都放我鸽子啦，下回早点吱一声呗”）；硬气档则直亮个人时间与恋爱里的平等尊重，干脆不内耗。"
        "留意“你忙吧”“行吧”“没事”及突然改用冷句号等语境变化（结合用户说明判断，不盲目套用反话公式）。"
    ),
    "spouse": (
        "当前处理的是「夫妻/婚姻共同生活」关系：夫妻过日子和谈恋爱完全不同！重长久体面、日常精力成本、家里协作与实在沟通。"
        "严禁套用“人家”“小失落嘛”“哄我”这类小情侣腻歪撒娇腔（老夫老妻发出去用户自己先受不了、会尴尬），也别写成翻旧账审问。"
        "温和档要写成“过日子的实诚软话”——先体谅对方临时有事不容易、给足面子，再平和商量错开安排（仅作语感参考：“知道你临时有事也没办法，就是我这边空出时间有点措手不及，下回有变你早点发个消息通个气，咱俩也好各自把事错开”）；"
        "自然与硬气档直接落到过日子的时间配合与具体规矩上（注意不替用户编造未提及的“提前一天”等具体时长），就事论事不翻陈年旧账。"
    ),
    "parent": (
        "当前处理的是「夫妻·共同育儿」关系：带娃和日常琐事极易耗竭，双方都像绷紧的弦，最忌居高临下指责“你不管家”。"
        "温和档先看见彼此都累、用并肩扛事的商量口吻轻声开口；硬气档则直白摊开哪段带娃或家务时段需要谁顶上，把分工落到具体时间。"
    ),
    "friend": (
        "当前处理的是「朋友」关系：看重平权、不扫兴、留台阶与体面边界，"
        "对委婉拒绝（如“改天”“最近忙”）或明褒暗贬（如“真羡慕你准时下班”）保持敏锐，同时保留熟人互损的语境余地。"
        "帮用户拒绝免费帮忙或温和催还钱时，用熟人自然口语直接说清情况，避开“想跟你提一下”“你看看还有没有其他办法”这类生硬疏离的套话，也别替对方或自己瞎编未来承诺。"
    ),
    "bestfriend": (
        "当前处理的是「挚友」关系：熟悉度高但同样需要边界和被尊重，留意玩笑过界或期待落差，"
        "回应自然松弛，不端着、不赌气说反话（温和档别写“行吧那你去吧”）。"
    ),
    "family": (
        "当前处理的是「家人」关系：常夹杂“我是为你好”的关心压力和不好撕破脸的为难，"
        "先体谅这份两难（不拿“滞销货”等扎心比喻加重用户难受），给表达建议时侧重温和但稳住底线，避免硬顶冲突。"
        "特别注意：1）对爸爸妈妈全程一律用“你 / 你们”，整段回复绝不出现疏离的“您”；"
        "2）给亲戚挡催婚或盘问的话术，绝不凭空编造用户没提过的亲戚（如“表哥”）、厨艺或事件，只用自然通用的暖场与轻巧转题。"
    ),
    "solo": (
        "当前处于「独处/单人梳理」模式：只围绕用户本轮说出的经历和个人习惯陪伴、理清边界或比较选择，"
        "绝不要求用户先绑定伴侣，也不编造不存在的伴侣信息。"
    ),
}

RESPONSE_LENGTH_GUIDES: dict[str, str] = {
    "short": "用户偏好简短回答：尽量精炼，直击重点，减少铺垫。",
    "medium": "",
    "long": "用户不介意稍微展开：需要拆解或比较时，可以把前因后果和取舍讲透一点，但仍保持口语自然，不要写成公文。",
}

_DISTRESS_CUE_PATTERN = re.compile(
    r"(?:哭了|一直在哭|好想哭|手还在抖|喘不过气|心碎|彻底绝望|太痛苦|难受死了|好绝望|受不了了|不想活|想死|崩溃|撑不住)"
)


def normalize_style_key(raw_style: str | None) -> str:
    cleaned = str(raw_style or "").strip().lower()
    return _STYLE_ALIAS_MAP.get(cleaned, "warm")


def normalize_intensity_key(raw_intensity: str | None) -> str:
    cleaned = str(raw_intensity or "").strip().lower()
    return cleaned if cleaned in VALID_EXPRESSION_INTENSITIES else "balanced"


def list_companion_styles() -> list[dict[str, str]]:
    """供个人中心和聊一聊顶部切换条展示的 4 种陪聊风格元数据。"""
    return [
        {
            "key": meta["key"],
            "label": meta["label"],
            "tagline": meta["tagline"],
            "sample": meta["sample"],
        }
        for meta in COMPANION_STYLE_DEFINITIONS.values()
    ]


def list_expression_intensities() -> list[dict[str, str]]:
    """供用户按心情与场合调节的 3 档表达力度（温和/自然/硬气）。"""
    return [
        {
            "key": meta["key"],
            "label": meta["label"],
            "tagline": meta["tagline"],
        }
        for meta in EXPRESSION_INTENSITY_DEFINITIONS.values()
    ]


def is_high_distress_or_crisis(text: str | None) -> bool:
    body = str(text or "").strip()
    if not body:
        return False
    if chat_crisis_level(body) != "none":
        return True
    return bool(_DISTRESS_CUE_PATTERN.search(body))


def _normalize_pair_type(pair: Any) -> str:
    if pair is None:
        return "solo"
    raw = getattr(pair, "type", pair) if not isinstance(pair, str) else pair
    if hasattr(raw, "value"):
        raw = raw.value
    cleaned = str(raw or "").strip().lower()
    return cleaned if cleaned in RELATIONSHIP_CONTEXT_GUIDES else "couple"


def resolve_companion_context(
    user: Any,
    *,
    pair: Any = None,
    pair_id: Any = None,
    requested_style: str | None = None,
    requested_intensity: str | None = None,
    current_text: str | None = None,
) -> dict[str, Any]:
    """汇总当前用户的陪聊风格、表达力度、个人习惯档案与关系类型。"""
    prefs = normalize_product_prefs(getattr(user, "product_prefs", None) if user is not None else None)
    pair_key = str(pair_id or getattr(pair, "id", "") or "").strip()
    pair_styles = prefs.get("pair_tone_preferences") if isinstance(prefs.get("pair_tone_preferences"), dict) else {}

    raw_selected = None
    if requested_style and str(requested_style).strip() in VALID_TONE_PREFERENCES:
        raw_selected = str(requested_style).strip()
    elif pair_key and pair_key in pair_styles:
        raw_selected = str(pair_styles[pair_key]).strip()
    else:
        raw_selected = str(prefs.get("tone_preference") or "warm").strip()

    style_key = normalize_style_key(raw_selected)
    raw_intensity = (
        str(requested_intensity).strip()
        if requested_intensity and str(requested_intensity).strip() in VALID_EXPRESSION_INTENSITIES
        else str(prefs.get("expression_intensity") or "balanced").strip()
    )
    intensity_key = normalize_intensity_key(raw_intensity)

    in_distress = is_high_distress_or_crisis(current_text)
    distress_guard = style_key == "playful" and in_distress
    effective_style_key = "warm" if distress_guard else style_key
    effective_intensity_key = "balanced" if (in_distress and intensity_key == "sharp") else intensity_key
    style_meta = COMPANION_STYLE_DEFINITIONS[effective_style_key]
    intensity_meta = EXPRESSION_INTENSITY_DEFINITIONS[effective_intensity_key]

    pair_type = _normalize_pair_type(pair)
    habit = prefs.get("habit_profile") if isinstance(prefs.get("habit_profile"), dict) else {}
    habit_taboos = [str(item).strip() for item in (habit.get("taboos") or []) if str(item).strip()]
    comfort_prefs = [str(item).strip() for item in (habit.get("comfort_preferences") or []) if str(item).strip()]
    custom_notes = str(habit.get("custom_notes") or "").strip()
    response_length = str(prefs.get("response_length") or "medium").strip()

    tone_profile = prefs.get("tone_profile")
    learned_tone_guide = ""
    if isinstance(tone_profile, dict) and not tone_profile_is_default(tone_profile):
        learned_tone_guide = tone_profile_guide_text(tone_profile)

    return {
        "requested_style_key": style_key,
        "style_key": effective_style_key,
        "style_label": style_meta["label"],
        "style_instruction": style_meta["instruction"],
        "requested_intensity_key": intensity_key,
        "intensity_key": effective_intensity_key,
        "intensity_label": intensity_meta["label"],
        "intensity_instruction": intensity_meta["instruction"],
        "distress_guard_triggered": distress_guard or (in_distress and intensity_key == "sharp"),
        "pair_type": pair_type,
        "relationship_guide": RELATIONSHIP_CONTEXT_GUIDES.get(pair_type, ""),
        "response_length": response_length,
        "response_length_guide": RESPONSE_LENGTH_GUIDES.get(response_length, ""),
        "habit_taboos": habit_taboos,
        "comfort_preferences": comfort_prefs,
        "custom_notes": custom_notes,
        "learned_tone_guide": learned_tone_guide,
    }


def merge_taboos(habit_taboos: list[str] | None, memory_taboos: list[str] | None) -> list[str]:
    """合并个人中心雷点与长期记忆 taboo，保序去重。"""
    merged: list[str] = []
    seen: set[str] = set()
    for source in (habit_taboos or [], memory_taboos or []):
        for item in source:
            text = str(item or "").strip()
            if not text:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(text)
    return merged


def build_companion_style_prompt(companion_ctx: dict[str, Any] | None) -> str:
    """生成注入到对话系统提示词里的风格、关系语境与习惯档案区块。"""
    if not companion_ctx:
        return ""
    lines = ["## 当前陪聊风格与相处语境（只调说话姿态与默契，不能覆盖事实、安全与授权红线）"]
    style_instruction = str(companion_ctx.get("style_instruction") or "").strip()
    if style_instruction:
        lines.append(f"- {style_instruction}")
    intensity_instruction = str(companion_ctx.get("intensity_instruction") or "").strip()
    if intensity_instruction:
        lines.append(f"- {intensity_instruction}")
    if companion_ctx.get("distress_guard_triggered"):
        lines.append("- 本轮用户情绪明显低落或难受，已自动收起轻松玩笑与过锐语气，改为稳重温和地托住。")
    rel_guide = str(companion_ctx.get("relationship_guide") or "").strip()
    if rel_guide:
        lines.append(f"- {rel_guide}")
    length_guide = str(companion_ctx.get("response_length_guide") or "").strip()
    if length_guide:
        lines.append(f"- {length_guide}")
    comfort = companion_ctx.get("comfort_preferences") or []
    if comfort:
        lines.append("- 用户在个人中心勾过的舒适偏好：" + "；".join(comfort[:8]))
    notes = str(companion_ctx.get("custom_notes") or "").strip()
    if notes:
        lines.append(f"- 用户补充的私人习惯参考：{notes}")
    learned = str(companion_ctx.get("learned_tone_guide") or "").strip()
    if learned:
        lines.append(f"- 近期累计语气微调：{learned}")
    return "\n".join(lines)


def build_simulation_style_context(
    companion_ctx: dict[str, Any] | None,
    *,
    pair_taboos: list[str] | None = None,
) -> dict[str, Any]:
    """给“发前看看”和后台紧凑分析使用的轻量风格与偏好摘要。"""
    if not companion_ctx:
        return {}
    taboos = merge_taboos(companion_ctx.get("habit_taboos"), pair_taboos)
    payload: dict[str, Any] = {
        "style_key": companion_ctx.get("style_key", "warm"),
        "style_label": companion_ctx.get("style_label", "暖心树洞"),
        "expression_intensity": companion_ctx.get("intensity_key", "balanced"),
        "intensity_label": companion_ctx.get("intensity_label", "自然有态度"),
        "pair_type": companion_ctx.get("pair_type", "solo"),
    }
    if companion_ctx.get("comfort_preferences"):
        payload["comfort_preferences"] = list(companion_ctx["comfort_preferences"])[:8]
    if companion_ctx.get("custom_notes"):
        payload["custom_notes"] = str(companion_ctx["custom_notes"])
    if taboos:
        payload["taboos"] = taboos[:12]
    return payload
