"""聊天工具的长期记忆写入与删除检查，只认当前用户这一轮的原话。

写入判定给出的是"保存范围"：长期偏好/禁忌记成长久记忆，带具体日期的安排只记这一次的事，
不能把一次夜班自动升格成"每周夜班"的习惯。
"""
import re
import uuid

from sqlalchemy import select
from app.models import AgentChatMessage, AgentChatSession, RelationshipMemory
from app.services.memory_evidence import topic_without_time


_QUOTED = re.compile(r'“[^”]*”|「[^」]*」|『[^』]*』|"[^"]*"|‘[^’]*’')

# 用户真会说的保存请求，不要求出现在句首，也不要求只认产品术语。
_SAVE_VERB = re.compile(
    r'(?:记住|记一下|记下来|记着|记好|记上|记吧|记呗|记下|帮我记|给我记|存一下|保存到长期记忆|保存一下|保存下来|'
    r'存起来|长期记住|长期保存|使用长期记忆保存|长期记忆保存|留个记录|留个底|别忘了|不要忘记|'
    r'以后(?:都)?按这个(?:来|办|做)?|以后(?:就)?照这个)'
)

_DENY_SAVE = (
    # 明确否认保存
    r'(?:不要|不用|不必|不需要|不想|别|勿|禁止|不能|不可以|先别|先不用)(?!忘记|忘)'
    r'[^。！？\n]{0,20}(?:记住|记着|记下|保存|存起来|留个记录|留个底)',
    # 只在本轮用
    r'(?:只|仅)(?:在|供|限于)?(?:这次|本次|当前|这一轮|本轮|这段|本段)',
    # 问产品是什么意思，不是授权
    r'(?:长期记忆|记忆|保存|记住)[^。！？\n]{0,6}(?:是什么|什么意思|怎么用|干嘛用|有什么用)',
    r'(?:是什么|什么意思|怎么用|干嘛用)[^。！？\n]{0,6}(?:长期记忆|记录)',
    # 用户自己在说"我记得"
    r'^(?:我|我们|咱|咱们)(?:也|还|确实)?(?:记得|记住|记着)',
    # 征询要不要记
    r'(?:要不要|需不需要|该不该|用不用|是不是)\s*(?:记住|记下来|保存|存)',
    # 假设句
    r'(?:如果|假如|假设|要是|万一)[^。！？\n]{0,24}(?:记住|保存|存下来|存起来)',
)

# 认得出的时间限定，用来判断"这次的事"而不是"一直的习惯"。
_TIME_HINT = re.compile(
    r'(大后天|今天|明天|后天|今晚|明早|'
    r'这周[一二三四五六日天]|本周[一二三四五六日天]|下个?周[一二三四五六日天]|'
    r'周[一二三四五六日天]|\d{1,2}月\d{1,2}[日号]|\d{1,2}[日号])'
)

_LONG_TERM = re.compile(
    r'(长期|永久|一直|以后|每次|每周|每星期|每天|每月|每年|总是|习惯|偏好|忌口|雷区|底线|不喜欢|讨厌|受不了|'
    r'不能提|别再|永远|规矩|说好了)'
)

# 更正上一轮说过的内容：不算新的保存要求，也不算没授权。
_CORRECTION = re.compile(r'(不对|不是[^。！？\n]{1,12}是|改成|改到|改一下|应该是|记错了|说错|更正|纠正|换个说法)')


def memory_request_scope(text: str | None) -> dict | None:
    """判断这句话是不是保存请求，并说明该记成长期偏好还是一次性安排。"""
    raw = str(text or '')
    if not raw.strip():
        return None
    for pattern in _DENY_SAVE:
        if re.search(pattern, raw, re.M):
            return None

    plain = _QUOTED.sub('', raw)
    hint = _TIME_HINT.search(plain)
    if not _SAVE_VERB.search(plain):
        return None

    long_term = _LONG_TERM.search(plain)
    # “别忘了明天交房租”是提醒，不是要我长期记住：只有同句讲清长期才按保存处理。
    if re.search(r'别忘了|不要忘记', plain) and not long_term:
        return None

    if long_term:
        return {'scope': 'long_term', 'time_hint': None}
    if hint:
        return {'scope': 'dated', 'time_hint': hint.group(1)}
    return {'scope': 'long_term', 'time_hint': None}


def explicit_memory_request(text: str) -> bool:
    return memory_request_scope(text) is not None


async def _verified_current_message(db, *, session_id, user_message_id, user_id, pair_id):
    try:
        sid, mid, uid, pid = [uuid.UUID(str(value)) for value in (session_id, user_message_id, user_id, pair_id)]
    except (ValueError, TypeError, AttributeError):
        return None
    session = await db.get(AgentChatSession, sid)
    if session is None or session.user_id != uid or session.pair_id != pid:
        return None
    message = await db.get(AgentChatMessage, mid)
    if message is None or message.session_id != sid or message.role != 'user':
        return None
    latest = (await db.execute(select(AgentChatMessage.id).where(AgentChatMessage.session_id == sid, AgentChatMessage.role == 'user').order_by(AgentChatMessage.created_at.desc(), AgentChatMessage.id.desc()).limit(1))).scalar_one_or_none()
    if latest != mid:
        return None
    return session, message


async def verified_memory_request(db, **context):
    """返回保存授权：原话、保存范围、时间限定、来源消息。

    subject 和 content 由模型提炼，这里不再用原话覆盖，避免把整句用户发言当成记忆摘要。
    """
    verified = await _verified_current_message(db, **context)
    if verified is None:
        return None
    session, message = verified
    scope = memory_request_scope(message.content)
    target = await _verified_correction_target(db, session, message)
    if target is not None:
        hint = _TIME_HINT.search(_QUOTED.sub('', message.content))
        scope = {'scope':'correction','time_hint':hint.group(1) if hint else None}
    if scope is None:
        return None
    return {
        'evidence_text': message.content,
        'memory_scope': scope['scope'],
        'time_hint': scope['time_hint'],
        'source_session_id': session.id,
        'source_user_message_id': message.id,
        'correction_memory_id': target.id if target is not None else None,
    }


async def _verified_correction_target(db, session, message):
    plain = _QUOTED.sub('', message.content)
    if not _CORRECTION.search(plain) or any(re.search(pattern, message.content, re.M) for pattern in _DENY_SAVE):
        return None
    if re.search(r'这句|句话|话术|文案|措辞|说法|改写', plain):
        return None
    if not _TIME_HINT.search(plain) and not re.search(r'记忆|记录|记的|存的|不是.{1,12}是', plain):
        return None
    rows = (await db.execute(select(RelationshipMemory).where(
        RelationshipMemory.pair_id==session.pair_id, RelationshipMemory.user_id==session.user_id,
    ))).scalars().all()
    # 不使用模型给的主题或相似字组来决定修改谁。
    direct = [row for row in rows if len(topic_without_time(row.subject))>=2 and topic_without_time(row.subject) in topic_without_time(plain)]
    candidates = direct
    if not candidates:
        previous = (await db.execute(select(AgentChatMessage).where(
            AgentChatMessage.session_id==session.id, AgentChatMessage.role=='user', AgentChatMessage.id!=message.id,
        ).order_by(AgentChatMessage.created_at.desc(),AgentChatMessage.id.desc()).limit(1))).scalar_one_or_none()
        if previous is not None:
            candidates = [row for row in rows if row.source_session_id==session.id and (
                str((row.content or {}).get('authorization_user_message_id') or (row.content or {}).get('source_user_message_id'))==str(previous.id)
                or (len(topic_without_time(row.subject))>=2 and topic_without_time(row.subject) in topic_without_time(previous.content))
            )]
    if len(candidates)!=1:
        return None
    target = candidates[0]
    if target.memory_type=='person' and len((target.content or {}).get('person_evidence') or [])>1:
        return None
    return target


_REMOVAL_VERB = re.compile(
    r'(?:删除|删掉|删了|删去|删一下|撤销|(?<![别不勿莫千万])忘(?:掉|了)|(?<![别不勿莫千万])忘记|移除|去掉|清掉|清空|清除|'
    r'不用(?:再)?(?:记|存|留)(?:着|下来)?了|不必(?:再)?(?:记|存|留)(?:着|下来)?了|'
    r'(?<![分特])别(?:再)?(?:记|存|留)(?:着|下来)?了|不(?:要|想)再?(?:记|存|留)(?:着|下来)?了|'
    r'不要了|不想要了|别再留着|别留着|别留了|不留了)'
)

_DENY_REMOVAL = (
    r'(?:删(?:掉|除|了)?|清空|清除).{0,4}(?:什么|哪些|了吗|过吗)',
    r'(?:不要|不用|不必|不需要|不想|别|勿|禁止|不能|不可以)(?!忘记|忘了)[^。！？\n]{0,20}'
    r'(?:删除|删掉|删了|删去|撤销|忘掉|移除|去掉|清掉|清空|清除)',
    r'(?:如果|假如|假设|要是|万一)[^。！？\n]{0,30}(?:删除|删掉|删了|撤销|忘掉|移除|去掉|清掉)',
    r'(?:会怎样|会怎么样|会如何|该怎么办|怎么办|会有什么后果)\s*[？?]?\s*$',
    r'(?:要不要|该不该|需不需要|用不用)[^。！？\n]{0,14}(?:删除|删掉|删了|撤销|忘掉|移除|去掉|清)',
    # 拿不准的征询：我是不是该把他删了 / 我该不该删掉 / 我该删了吗
    r'(?:是不是|是否)[^。！？\n]{0,8}(?:该|要|得)[^。！？\n]{0,12}(?:删除|删掉|删了|删去|撤销|忘掉|移除|去掉|清掉|清空|清除)',
    r'^(?:我|我们)[^。！？\n]{0,10}(?:该|要不要|是不是)[^。！？\n]{0,12}(?:删除|删掉|删了|撤销|忘掉|移除|去掉|清掉|清空|清除)[^。！？\n]{0,3}(?:吗|呢|么)?\s*[？?]?\s*$',
    r'^(?:他|她|他们|她们|别人|对方)(?:想|要|说|觉得|希望|让我)',
    r'^(?:我|我们)(?:在)?(?:想|考虑|琢磨)(?:要不要|该不该|是否)',
    # 转述别人的意思：我朋友说不用记了，不等于我要删
    r'^(?:我|我们)(?:的)?(?:朋友|同事|同学|室友|对象|男朋友|女朋友|老公|老婆|闺蜜|兄弟|姐妹|家里人|家人|爸|妈|哥|姐|弟|妹|他|她)(?:他|她)?(?:说|讲|觉得|认为|希望|让我|叫我|建议)',
    # 还没定下来
    r'(?:我想想|我再想想|让我想想|再想想|考虑一下|琢磨一下|犹豫)[^。！？\n]{0,12}(?:删除|删掉|删了|撤销|忘掉|移除|去掉|清掉|清空|清除)',
)


def explicit_removal_request(text: str | None):
    """返回删除授权：用户这一轮真正说出口的删除要求及原话片段。"""
    raw = str(text or '')
    affirmative = []
    for clause in re.split(r'[，,。；;！？\n]', raw):
        plain = _QUOTED.sub('', clause).strip()
        if not plain:
            continue
        # “能不能删掉”是请求，“不能删”才是拒绝。
        asking = re.sub(r'(?:能不能|可不可以|可以不可以|能否)', '', plain)
        if any(re.search(pattern, asking) for pattern in _DENY_REMOVAL):
            continue
        if _REMOVAL_VERB.search(asking):
            affirmative.append(clause.strip())
    if not affirmative:
        return None
    request = '，'.join(affirmative)
    whole_scope = bool(re.search(r'^(?:(?:请|麻烦|帮我|把|我)\s*)*(?:(?:过去|之前|以前)(?:记|存|保存)的那些|(?:全部|所有)(?:长期)?(?:记忆|记录|条目))', request))
    if re.search(r'除了|除外|保留|留下|(?:别|不(?:要|用|能)?)(?:再)?删|但是|不过|唯独', raw):
        whole_scope = False
    return {
        'request_text': request,
        'all_requested': bool(re.search(
            r'(?:整个|整条)(?:人物)?(?:主题|记忆主题)|(?:全部|所有)同名人物', request)) or whole_scope,
        'all_scope_requested':whole_scope,
    }


async def verified_memory_removal(db, **context):
    verified = await _verified_current_message(db, **context)
    if verified is None:
        return None
    return explicit_removal_request(verified[1].content)


_SAVE_QUESTION = re.compile(
    r'(?:要不要|需不需要|用不用|该不该)[^。！？!?\n]{0,12}(?:记|存)'
    r'|(?:记下来吗|记着吗|记一下吗|存下来吗|记住吗)'
)


def _field(row, name: str) -> str:
    value = row.get(name) if isinstance(row, dict) else getattr(row, name, None)
    return str(value or '')


def save_question_guard(history) -> str | None:
    """模型刚问过"要不要记"、用户还没回答时，给一句交代，别再问第二遍。

    history 是本次请求的会话消息，dict 和消息对象都收。
    """
    recent = [row for row in (history or []) if not ((row.get('payload') if isinstance(row,dict) else getattr(row,'payload',None)) or {}).get('memory_suppressed_for_ai')][-8:]
    for index in range(len(recent) - 1, -1, -1):
        row = recent[index]
        content = _field(row, 'content')
        if _field(row, 'role') != 'assistant' or not _SAVE_QUESTION.search(content):
            continue
        asked_at = content.strip().splitlines()[0][:60]
        # 他问完以后，用户有没有再表态？说了记录/删除要求就算答过了。
        for later in recent[index + 1:]:
            if _field(later, 'role') != 'user':
                continue
            text = _field(later, 'content')
            if memory_request_scope(text) or explicit_removal_request(text):
                return None
            return (
                f'你上一轮已经问过他"{asked_at}"，他到现在没接这个话。'
                '这一轮别再问要不要记，也不要换个说法追着问；他要提就再说。'
            )
    return None
