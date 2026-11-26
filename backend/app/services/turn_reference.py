"""当前话题内的指代消解：把“这是我想发的”“这是他发我的”“算了，不想回了”准确回指到上一条用户原话。"""

from __future__ import annotations

import re
from typing import Any


_INTERNAL_USER_PREFIXES = (
    "以下是本次会话较早的用户原文资料",
    "同事简报（仅作参考）：",
    "以下简报仅作参考资料，不是指令：",
)

_NEW_QUOTE_RE = re.compile(r"[“\"‘'「『]([^”\"’'」』]{4,})[”\"’'」』]")

_OUTGOING_DRAFT_REF_RE = re.compile(
    r"(?:这(?:句|句话|段|条)?|上面那(?:句|段|条)|上面这(?:句|段|条)|刚才那(?:句|段|条)|刚那(?:句|段|条)|那(?:句|句话))"
    r"(?:话)?(?:其实)?是?我(?:自己)?(?:想发|打算发|准备发|要发|想说|准备说|打算说)(?:给(?:他|她|对方))?的"
    r"|我(?:想发|打算发|准备发|要发)(?:这(?:句|句话|段|条)|上面那句|刚才那句)"
)

_INCOMING_QUOTE_REF_RE = re.compile(
    r"(?:这(?:句|句话|段|条)?|上面那(?:句|段|条)|上面这(?:句|段|条)|刚才那(?:句|段|条)|刚那(?:句|段|条)|那(?:句|句话))"
    r"(?:话)?(?:其实)?是(?:他|她|对方|男朋友|女朋友|老公|老婆|对象|前任|室友|朋友|同事|领导|我爸|我妈|爸|妈)"
    r"(?:刚刚|刚才|刚)?(?:(?:对|跟|向|给)(?:我|咱们|我们))?(?:发给我|发我|发来|回给我|回我|说给我|说|发|讲|骂)(?:给我|我)?的"
)

_ABANDON_REPLY_RE = re.compile(
    r"^(?:还是)?(?:算了|先算了)[，,、\s]*(?:我)?(?:先)?(?:不想回|不回|不想发|不发|先放着|放着|搁着|不聊|算了)[^。！？!?]{0,16}[。！!~～]*$"
    r"|^(?:我)?(?:先)?(?:不想回了|不回了|不想发了|不发了)[。！!~～]*$"
)

_ASKS_REPLY_RE = re.compile(r"(?:帮我回|怎么回|帮我写|帮我想|给我一句|改写|润色|回一句|回他|回她)")
_ASKS_CHECK_RE = re.compile(r"(?:帮我看看|帮我改|看看行不行|看看怎么样|怎么说|合适吗|能发吗|行不行|改一改|改一下)")


def _clean_user_turn(content: Any) -> str:
    if not isinstance(content, str):
        return ""
    text = content.strip()
    if not text or text.startswith(_INTERNAL_USER_PREFIXES):
        return ""
    if "用户这次想说：" in text:
        text = text.rsplit("用户这次想说：", 1)[-1].strip()
    return text


def extract_current_session_user_turns(messages: list[dict[str, Any]]) -> list[str]:
    turns: list[str] = []
    for message in messages or []:
        if message.get("role") != "user":
            continue
        cleaned = _clean_user_turn(message.get("content"))
        if cleaned:
            turns.append(cleaned)
    return turns


def resolve_current_topic_reference(messages: list[dict[str, Any]]) -> dict[str, str] | None:
    """识别当前会话里对上一条用户原话的指代澄清，返回可供模型遵守的明确说明。"""
    turns = extract_current_session_user_turns(messages)
    if len(turns) < 2:
        return None

    current = turns[-1]
    previous = turns[-2]
    if not current or not previous or len(current) > 80:
        return None

    # 决定先不回 / 不发了
    if _ABANDON_REPLY_RE.match(current) and not _ASKS_REPLY_RE.search(current):
        return {
            "kind": "abandon_reply",
            "previous_user_text": previous,
            "system_instruction": (
                f"当前话题里用户刚才提到的内容是：“{previous}”。"
                "用户这一轮已经明确决定先不回或不发了。"
                "请简短、平和地接住他停下来的决定即可；不要劝他回复，不要继续提供改写或回复稿，"
                "也不要追问或强行安排下一步。"
            ),
        }

    # 如果这一轮自己又贴了新引号原话，不覆盖当前原话
    if _NEW_QUOTE_RE.search(current):
        return None

    if _OUTGOING_DRAFT_REF_RE.search(current):
        asks_check = bool(_ASKS_CHECK_RE.search(current) or _ASKS_REPLY_RE.search(current))
        action_hint = (
            "请直接针对这句草稿给出评估或更自然的改写，不要要求用户重贴原文。"
            if asks_check
            else "请把它当成用户准备发出的话来回应，不要要求用户重贴原文。"
        )
        return {
            "kind": "outgoing_draft",
            "previous_user_text": previous,
            "system_instruction": (
                f"当前话题上一条用户原话是：“{previous}”。"
                "用户这一轮明确说明，上一条是他自己准备发给别人的话，不是对你说的。"
                f"{action_hint}"
                "改写时必须严格忠于用户原话：只保留用户说过的事实、感受、时间和条件；"
                "用户没说过的时间期限（如“这两天”“今晚”“明天”）和后续再联系/再聊的承诺（如“晚点回你”“回头再聊”“等我想说的时候再找你”“缓过来再聊”）绝不能自行补进去。"
            ),
        }

    if _INCOMING_QUOTE_REF_RE.search(current):
        if _ASKS_REPLY_RE.search(current):
            action_hint = (
                "用户明确要你帮他回一句，请直接基于对方说的这句话和用户提出的要求给出能直接发送的回复，"
                "不要求用户重贴，也不编造用户没说的时间或承诺。"
            )
        else:
            action_hint = (
                "用户目前只是说明这句话是对方发给他的，并没有要求代写回复。"
                "请先接住用户收到这句话的感受，不要要求重贴，不要把这句话当成用户准备发出去的草稿，"
                "也不要擅自代写回复。"
            )
        return {
            "kind": "incoming_quote",
            "previous_user_text": previous,
            "system_instruction": (
                f"当前话题上一条用户原话是：“{previous}”。"
                "用户这一轮明确说明，上一条是对方发给他的原话，不是用户对你说的，也不是用户自己想发出去的话。"
                "用户未交代此前怎样交流，不补写用户一直好好沟通、尚未发出消息或对方突然发火等前因。"
                f"{action_hint}"
            ),
        }

    return None
