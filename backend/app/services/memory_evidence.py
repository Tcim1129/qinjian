"""记忆的原文依据与对象匹配，不用字词相似度代替事实和授权。"""
import re


TIME_WORDS = re.compile(r'(?:这|本|下个?)?(?:周|星期)[一二三四五六日天]|\d{1,2}月\d{1,2}[日号]|今天|明天|后天|今晚|明早')


def authorized_fact_text(source):
    """先介绍多人、再明确指定记其中一项时，只取指定的原话。"""
    text = str(source or '').strip()
    selected = re.search(
        r'[。；;\n]\s*(?:先|只)?(?:请)?(?:帮我|替我)?'
        r'(?:长期记住|记住|记一下|记下来)\s*([^。；;\n]+)', text,
    )
    if selected:
        clauses = re.split(r'[，,]', selected.group(1))
        if len(clauses) > 1 and re.search(r'(?:不用|不要|别).{0,3}记', clauses[-1]):
            clauses.pop()
            return '，'.join(clauses).strip()
    return text


def compact(value):
    return re.sub(r'[\s，,。.！!？?、；;：:（）()“”\"\'’‘「」]', '', str(value or ''))


def fact_text(source):
    """只去掉保存动作的外壳，保留人名、否定、转述者和事实内容。"""
    text = str(source or '').strip()
    text = re.sub(r'^(?:(?:请|麻烦|帮我|请帮我|你帮我|给我)\s*)*(?:使用长期记忆保存|保存到长期记忆|长期记住|长期保存|记住|记一下|记下来|记着|保存一下)\s*[:：，,]?\s*', '', text)
    text = re.sub(r'[,，。]?\s*(?:这件事|这个|这事儿?|这些)?\s*(?:你得|你要|也|都|帮我|给我|你帮我|请|麻烦)?\s*(?:记着|记住|记一下|记下来|记好|保存下来|存起来)[吧了呗啊。！!]*$', '', text)
    text = re.sub(r'^(?:不对[，,]?|说错了[，,]?|记错了[，,]?|更正[：:，,]?)+\s*(?:是)?', '', text)
    return text.strip(' ，,。；;') or str(source or '').strip()


def _clause_key(text):
    text = re.sub(r'^用户(?:明确)?(?:表示|提到|说)?[：:]?', '我', str(text).strip())
    text = re.sub(
        r'^(?:(?:先|再|那就|请|麻烦|帮我|请帮我|你帮我|给我)\s*)*(?:使用长期记忆保存|保存到长期记忆|长期记住|长期保存|记住|记一下|记下来|记着|保存一下)\s*[:：]?\s*',
        '',
        text,
    )
    text = re.sub(r'^我', '', text)
    return compact(text)


def grounded_summary(candidate, source):
    """只接受逐句能对回原文的提炼；不能证明的改写退回去掉指令后的原文。"""
    fact = fact_text(source)
    clauses = {_clause_key(c) for c in re.split(r'[，,。；;\n]', fact) if _clause_key(c)}
    proposed = [_clause_key(c) for c in re.split(r'[，,。；;\n]', str(candidate or '')) if _clause_key(c)]
    if proposed and all(clause in clauses for clause in proposed):
        return str(candidate).strip()
    return fact


def grounded_subject(candidate, source, memory_type=None):
    named = re.search(r'主题(?:叫|是|为)?\s*[:：]?\s*[“"「]([^”"」]{1,100})[”"」]', str(source or ''))
    if named:
        return named.group(1).strip()
    fact = fact_text(source)
    if memory_type == 'person':
        # “球友小王”与“小王是我的球友”是同一姓名，身份仍分开留在各份原文里。
        declared = set(re.findall(r'(?:^|[，,。；;：:\s])(?:另一个|另一位)?([\u4e00-\u9fffA-Za-z·]{2,12}?)(?:是我的|是我|是)[^，,。；;\n]+', fact))
        if len(declared) == 1:
            return next(iter(declared))
    title = str(candidate or '').strip()
    reverses_negation = bool(title and re.search(r'(?:不|没|未|无|别|勿|不是|没有|不能|不会)' + re.escape(compact(title)), compact(fact)))
    if title and not reverses_negation and compact(title) in compact(fact):
        return title[:100]
    return re.sub(r'^我(?!们)', '', fact).strip()[:100]


def candidate_matches_source(subject, summary, source, memory_type=None):
    """拒绝拿本轮授权补存另一件事；相关内容才可以退回事实原文。"""
    fact = fact_text(source)
    resolved = grounded_subject(subject, source, memory_type)
    title = str(subject or '').strip()
    if title and resolved == title and compact(title) in compact(fact):
        return True
    base = re.sub(r'(?:安排|计划|记录|事项|情况|偏好|习惯|信息|档案)$', '', topic_without_time(title))
    if len(base) >= 2 and base in topic_without_time(fact):
        return True
    if memory_type == 'person' and resolved and compact(resolved) in compact(title) and compact(resolved) in compact(fact):
        return True
    clauses = {_clause_key(c) for c in re.split(r'[，,。；;\n]', fact) if _clause_key(c)}
    return any(_clause_key(c) in clauses for c in re.split(r'[，,。；;\n]', str(summary or '')) if _clause_key(c))


def topic_without_time(value):
    text = re.sub(r'（[^）]*）|\([^)]*\)', '', str(value or ''))
    return compact(TIME_WORDS.sub('', text))


def deletion_query(request):
    text = str(request or '').strip()
    text = re.sub(
        r'^(?:(?:那(?=[，,\s])|嗯|好吧|算了|还是|我还是|其实|我想|我要|先|再|重新|直接|就|请|请你|麻烦|帮我|你帮我|能不能|可不可以|能否|把|将)[，,\s]*)+',
        '',
        text,
    )
    text = re.sub(r'(?:不(?:用|要)(?:再)?记了?|别(?:再)?(?:留着|记|存)了?|不用留着了?|删除|删掉|删了|删去|删一下|撤销|忘掉|忘记|移除|去掉|清掉|清空|清除)', '', text)
    text = re.sub(r'(?:这|那)(?:一)?(?:条|件事|份|项)', '', text)
    text = compact(text)
    text = re.sub(r'(?:的)?(?:长期记忆|记忆|记录|资料|档案|安排)[了吧呗啊。！!]*$', '', text)
    text = re.sub(r'[了吧呗啊。！!]+$', '', text)
    return compact(re.sub(r'^我(?!们)', '', text))


def identifies_record(record, request):
    """对象必须能在本轮要求里定位；同一角色、部分重合不能授权另一个人或日期。"""
    subject = str(record.subject or '')
    content = record.content or {}
    request_times = set(TIME_WORDS.findall(str(request)))
    record_times = set(TIME_WORDS.findall(str(content.get('time_hint') or subject)))
    if request_times and record_times:
        weekdays = lambda words: {re.sub(r'^(?:这|本|下个?)', '', word).replace('星期', '周') for word in words}
        if not weekdays(request_times) & weekdays(record_times):
            return False
        if all(word.startswith(('下', '这', '本')) for word in request_times | record_times) and not request_times & record_times:
            return False
    key = compact(subject)
    if record.memory_type == 'person':
        if not key or key in {'用户', '人物', '朋友', '资料', '记忆'}:
            return False
        # 姓名必须完整；“小王子”和“小王的爸爸”都不能授权删除“小王”。
        suffix = r'(?=$|[\s，,。.！!？?、；;：:（）()]|(?:的)?(?:(?:这|那)(?:一)?条|(?:全部|所有)?(?:长期)?(?:记忆|资料|记录|档案)|相关(?:的)?(?:信息|资料))|删|忘掉|忘记|移除|不用记)'
        return bool(re.search(re.escape(subject) + suffix, str(request)))
    query = deletion_query(request)
    if len(query) < 2:
        return False
    targets = [subject, content.get('detail') or '', content.get('evidence_text') or '']
    return any(query in _clause_key(value) for value in targets)
