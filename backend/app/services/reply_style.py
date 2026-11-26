"""把回复里的客套前言和多余尾巴去掉，只留能直接看的话。"""

from __future__ import annotations

import re

# 行首的“可以回：”“建议你说：”这类提示语
_DRAFT_PREFIX = re.compile(
    r'^[ \t]*(?:你)?(?:可以|建议|不妨|不如|或者)?[ \t]*'
    r'(?:这样|这么|直接)?[ \t]*(?:回|说|发|讲)(?:他|她|对方|她妈|他妈|他爸|她爸|妈|爸)?[ \t]*[：:][ \t]*'
)

_PREFIX_ONLY = re.compile(
    r'^[ \t]*(?:你)?(?:可以|建议|不妨|不如|或者)?[ \t]*(?:这样|这么|直接)?[ \t]*'
    r'(?:回|说|发|讲)(?:他|她|对方|妈|爸)?[ \t]*[：:][ \t]*$'
)

# 末尾多余的征询与推销
_TAIL_OFFER = re.compile(
    r'(你看这样(?:说|回)?(?:行不行|可以吗|行吗)|'
    r'要不要我(?:帮你)?(?:再)?(?:调整|改|换个说法|说软一点|调软一点|软化一点)'
    r'(?:一下)?(?:语气|说法|这个说法|这句|这句话)?|'
    r'想再软(?:一点)?(?:就跟我说|跟我说|我可以帮你)|'
    r'(?:想|要)(?:再)?(?:软|硬|客气|直接|温和)(?:一点|点儿|点)(?:的话)?'
    r'[，,]?[ \t]*(?:就把|就把那句|把)[^。！？\n]{0,12}(?:换|改)成[^。！？\n]{0,16}|'
    r'我可以帮你(?:调整|改|调软)(?:语气|说法)?)'
)


def _strip_prefix(line: str) -> str:
    if '：' not in line and ':' not in line:
        return line
    head, sep, rest = line.partition('：') if '：' in line else line.partition(':')
    if not rest.strip():
        return line
    if _DRAFT_PREFIX.match(line) and len(head) <= 12:
        return rest.strip()
    return line


# 草稿后面又补的一段点评，留着就把“给完就收”破了
_COMMENTARY_HEAD = re.compile(
    r'^[ \t]*(?:这么问是|这么说是|这么回是|这样问是|这样说是|这样回是|'
    r'这句的好处|这句话的作用|这个说法的好处)'
)


def _drop_trailing_commentary(lines: list[str]) -> list[str]:
    """草稿之后紧跟的一两句点评去掉，只留能发的话。"""
    while len(lines) > 1:
        last = lines[-1].strip()
        if not last:
            lines.pop()
            continue
        if _COMMENTARY_HEAD.match(last) and len(last) <= 60:
            lines.pop()
            while lines and not lines[-1].strip():
                lines.pop()
            continue
        break
    return lines


# 偶发模型内部标签或自问自答续写泄露（例如多步工具调用后的 system_warning / 伪造下一轮对话）
_FAKE_TURN_BEFORE_WARNING = re.compile(
    r'\n{2,}[ \t]*(?:You|User|用户)[^\n]{0,120}\n+[ \t]*<system_warning>.*',
    re.DOTALL,
)
_SYSTEM_WARNING_TAIL = re.compile(
    r'(?:\n{1,}[ \t]*)?<system_warning>.*?(?:</system_warning>)?(?:\s*Nothing urgent\.[^\n]*)?.*',
    re.DOTALL,
)
_THINKING_TAG = re.compile(
    r'<(?P<tag>thinking|thought|system_warning)>.*?</(?P=tag)>',
    re.DOTALL | re.IGNORECASE,
)


def sanitize_model_artifacts(text: str | None) -> str:
    """清理模型偶发泄露的内部提示标签或伪造的多轮续写，防止展示到用户气泡。"""
    if not text:
        return ''
    cleaned = str(text)
    if '<system_warning>' in cleaned:
        cleaned = _FAKE_TURN_BEFORE_WARNING.sub('', cleaned)
        cleaned = _SYSTEM_WARNING_TAIL.sub('', cleaned)
    cleaned = _THINKING_TAG.sub('', cleaned)
    return cleaned.strip()


def polish_reply(text: str | None, *, draft_requested: bool = False) -> str:
    """清理内部泄露标签；用户明确要草稿时再整理前后提示，普通回答保留正文。"""
    cleaned = sanitize_model_artifacts(text)
    if not cleaned:
        return ''
    if not draft_requested:
        return cleaned
    lines = []
    for line in cleaned.split('\n'):
        if _PREFIX_ONLY.match(line):
            continue
        lines.append(_strip_prefix(line))
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and _TAIL_OFFER.fullmatch(lines[-1].strip().rstrip('。！？!?')):
        lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()
    lines = _drop_trailing_commentary(lines)
    return '\n'.join(lines).strip()
