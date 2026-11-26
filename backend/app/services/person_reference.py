"""先确认用户没有说清楚的对象，不带着未知人物去查询或修改安排。"""
import json
import re

from app.services.draft_grounding import current_user_text


def person_direction_question(messages):
    text = current_user_text(messages)
    if not re.search(r'(?:改|调整|更新|挪).{0,12}(?:安排|时间|日期)|(?:改到|改成|挪到).{0,12}(?:周|明天|后天|号|日)', text):
        return None
    pronoun = re.search(r'我刚和([^。]{1,80})都聊过[。，,]?\s*[他她]说', text)
    if pronoun:
        names = list(dict.fromkeys(name.strip() for name in re.split(r'[、，,]', pronoun.group(1)) if name.strip()))
        if len(names) > 1:
            return '先确认一下，说要改期的是' + '，还是'.join(names) + '？'
    named = re.search(r'(?:^|[。；;\n])\s*([^，。\s]{1,20}?)说(?:要)?(?:改|调整|挪)', text)
    if not named:
        return None
    name = named.group(1)
    roles = set()
    for message in messages:
        content = message.get('content')
        if message.get('role') != 'user' or not isinstance(content, str):
            continue
        for prefix in re.findall(r'(?:^|[，。；;\n])\s*([\u4e00-\u9fff]{1,16}?)' + re.escape(name), content):
            if not re.search(r'请|帮|提醒|说|写|改|不是|不要|别', prefix):
                roles.add(prefix)
        start = content.find('[')
        if start < 0:
            continue
        try:
            records, _ = json.JSONDecoder().raw_decode(content[start:])
        except ValueError:
            continue
        if not isinstance(records, list):
            continue
        for row in records:
            if isinstance(row, dict) and row.get('name') == name and isinstance(row.get('role'), str):
                roles.add(row['role'][:40])
    if len(roles) > 1 and sum(role in text[named.end():] for role in roles) != 1:
        return '先确认一下，是' + '，还是'.join(role + name for role in sorted(roles)) + '说要改期？'
    return None
