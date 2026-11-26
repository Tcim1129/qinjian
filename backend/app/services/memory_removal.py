"""聊天中的记忆停用确认与受限追溯，不能由模型直接确认。"""
import base64
import hashlib
import hmac
import json
import re
import uuid
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from sqlalchemy import select,or_,update
from app.core.config import settings
from app.models import AgentChatMessage, AgentChatSession, RelationshipMemory, MemoryRemovalArchive
from app.services.chat_memory_permission import _verified_current_message
from app.services.relationship_memory import plan_memory_removal, _record_ref, _ordered_records, _person_role, fact_evidence


_DEICTIC = re.compile(r'(?:刚才|刚刚|上面|上一条|前一条|这条|那条|它|这个|那个)(?:记录|记忆|条目|东西|事)?')


async def _history_batches(db, *, user_id, pair_id):
    """按消息编号分批读取同一账号、同一关系的历史，避免整库驻留内存。"""
    scope = select(AgentChatSession.id).where(
        AgentChatSession.user_id == user_id, AgentChatSession.pair_id == pair_id)
    cursor = None
    while True:
        query = select(AgentChatMessage).where(AgentChatMessage.session_id.in_(scope))
        if cursor is not None:
            query = query.where(AgentChatMessage.id > cursor)
        batch = list((await db.execute(query.order_by(AgentChatMessage.id).limit(250))).scalars())
        if not batch:
            return
        cursor = batch[-1].id
        yield batch


async def _deictic_target(db, *, user_id, pair_id, session_id, current_message_id):
    """“刚才那条不用记了”指的是紧挨着上一轮存下的那条，只在这条唯一时成立。"""
    if not session_id:
        return None
    previous = (await db.execute(
        select(AgentChatMessage)
        .where(AgentChatMessage.session_id == session_id,
               AgentChatMessage.role == 'user',
               AgentChatMessage.id != current_message_id)
        .order_by(AgentChatMessage.created_at.desc())
        .limit(1)
    )).scalars().first()
    if previous is None:
        return None
    rows = (await db.execute(
        select(RelationshipMemory).where(RelationshipMemory.pair_id == uuid.UUID(str(pair_id)),
                                         RelationshipMemory.user_id == uuid.UUID(str(user_id)))
    )).scalars().all()
    from_previous = [row for row in rows
                     if str((row.content or {}).get('source_user_message_id') or '') == str(previous.id)]
    if len(from_previous) != 1:
        return None
    record = from_previous[0]
    return {'subject': record.subject, 'memory_type': record.memory_type, 'deictic': True}


async def resolve_explicit_target(db, *, user_id, pair_id, request_text, session_id=None, current_message_id=None):
    """只定位本轮已说清的对象；不替含糊代词或未知身份猜一个数据库标题。"""
    from app.services.memory_evidence import compact, deletion_query, identifies_record
    records=await _ordered_records(db,uuid.UUID(str(pair_id)),uuid.UUID(str(user_id)))
    matches=[record for record in records if identifies_record(record,request_text)]
    if len(matches)>1:
        return '这句话对应多条记忆，请先说明具体日期、姓名或身份。现在没有停用任何记录。'
    if not matches:
        # “刚才那条不用记了”“刚刚存的那条删掉”指向上一轮存下的一条，服务端自己接住。
        if _DEICTIC.search(str(request_text or '')):
            return await _deictic_target(db,user_id=user_id,pair_id=pair_id,session_id=session_id,current_message_id=current_message_id)
        return None
    record=matches[0]
    result={'subject':record.subject,'memory_type':record.memory_type}
    if record.memory_type=='person':
        query=deletion_query(request_text)
        selector=query.replace(compact(record.subject),'',1)
        selector=re.sub(r'(?:的)?(?:所有|全部|相关|长期记忆|记忆|资料|记录|信息)', '',selector)
        if selector:
            evidence=(record.content or {}).get('person_evidence') or [record.content or {}]
            if len(selector)<2 or selector not in request_text or not any(selector in _person_role(item.get('detail',''),record.subject) for item in evidence):
                return None
            result['person_selector']=selector
    return result


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _cipher():
    key=hmac.new(settings.SECRET_KEY.encode(),b'memory-removal-archive-v1',hashlib.sha256).digest()
    return Fernet(base64.urlsafe_b64encode(key))


async def prepare_removal(db, *, session_id, user_message_id, user_id, pair_id, **selection):
    verified=await _verified_current_message(db,session_id=session_id,user_message_id=user_message_id,user_id=user_id,pair_id=pair_id)
    if verified is None:
        return {'status':'error','removed':False,'message':'没有核对到本轮删除请求，记忆未改动。'}
    session,message=verified
    if re.search(r'彻底删除|永久删除|清除所有副本|不要.{0,6}(?:后台|副本).{0,6}保留',message.content):
        return {'status':'error','removed':False,'message':'这属于彻底清除数据，本次普通记忆停用未执行，也没有把它当成同意保留追溯副本。请在隐私设置中核对数据清除范围。'}
    plan=await plan_memory_removal(db,pair_id=pair_id,user_id=user_id,**selection)
    if not plan:
        if str(selection.get('person_selector') or '').strip():
            return {'status':'not_found','removed':False,'message':'没有对上你说明的那一位，未改动任何记录。可以说清是哪件事、或者哪句原话吗？'}
        return {'status':'not_found','removed':False,'message':'没有找到符合要求的记忆，未改动任何记录。'}
    existing=(message.payload or {}).get('memory_removal_request') or {}
    if existing.get('state')=='pending':
        if existing.get('plan')!=plan:
            return {'status':'error','removed':False,'message':'本轮已有待确认范围，不能在显示前换成另一组记录。请先处理已展示的范围。'}
        return {'status':'confirmation_required','removed':False,'request_message_id':str(message.id),'message':existing['message']}
    keep=max(1,int(settings.MEMORY_REMOVAL_RETENTION_DAYS));audit=max(keep,int(settings.MEMORY_REMOVAL_AUDIT_DAYS))
    pending={'state':'pending','plan':plan,'expires_at':(now()+timedelta(minutes=max(1,int(settings.MEMORY_REMOVAL_CONFIRM_MINUTES)))).isoformat(),
             'retention_days':keep,'audit_days':audit}
    labels='、'.join(item['label'] for item in plan)
    reply=(f'准备让这些内容退出 AI 记忆：{labels}，共 {len(plan)} 条。现在还没有停用。'
           f'确认后，AI 不再检索和引用这些内容；单独的加密追溯副本保留 {keep} 天，到期清除此副本内容，'
           f'不含原文、只含操作编号、账号归属和时间等信息的审计记录保留 {audit} 天。之前的聊天记录不受影响。'
           f'本次确认 {max(1,int(settings.MEMORY_REMOVAL_CONFIRM_MINUTES))} 分钟内有效。要继续请回复“确认删除”，不改动请回复“取消”。')
    message.payload={**(message.payload or {}),'memory_removal_request':{**pending,'message':reply}}
    await db.flush()
    return {'status':'confirmation_required','removed':False,'request_message_id':str(message.id),'message':reply}


async def _recent_pending_gone(db, *, session_id, current_id, lookback=6) -> bool:
    """用户说完确认后，前面几轮里是否曾经有过待确认范围（用来区分"失效"和"根本没发起"）。"""
    rows=(await db.execute(select(AgentChatMessage).where(AgentChatMessage.session_id==session_id,AgentChatMessage.role=='user',AgentChatMessage.id!=current_id)
                           .order_by(AgentChatMessage.created_at.desc(),AgentChatMessage.id.desc()).limit(lookback))).scalars().all()
    return any(((row.payload or {}).get('memory_removal_request') or {}).get('state') in {'pending','expired','cancelled','completed','changed'} for row in rows)


async def consume_confirmation(db, *, session_id, user_message_id, user_id, pair_id):
    verified=await _verified_current_message(db,session_id=session_id,user_message_id=user_message_id,user_id=user_id,pair_id=pair_id)
    if verified is None:
        return None
    session,current=verified
    text=current.content.strip().strip('。！!，, ')
    confirm=bool(re.fullmatch(r'确认(?:删除|停用|不再记住)?',text))
    cancel=text in {'取消','不删了','先不删','不要删','不要删除','保留','算了'}
    if not confirm and not cancel:
        return None
    source=(await db.execute(select(AgentChatMessage).where(AgentChatMessage.session_id==session.id,AgentChatMessage.role=='user',AgentChatMessage.id!=current.id)
                            .order_by(AgentChatMessage.created_at.desc(),AgentChatMessage.id.desc()).limit(1).with_for_update())).scalar_one_or_none()
    if source is None:
        return None
    pending=(source.payload or {}).get('memory_removal_request') or {}
    assistant=(await db.execute(select(AgentChatMessage).where(AgentChatMessage.session_id==session.id,AgentChatMessage.role=='assistant')
                               .order_by(AgentChatMessage.created_at.desc(),AgentChatMessage.id.desc()).limit(1))).scalar_one_or_none()
    if pending.get('state')!='pending' or assistant is None or (assistant.payload or {}).get('memory_removal_request_id')!=str(source.id):
        if confirm and await _recent_pending_gone(db, session_id=session.id, current_id=current.id):
            return '这次确认没有对应的待确认范围，可能已经取消或失效，记忆没有改动。要停用请重新说一次。'
        return None
    def state(value):
        request = {**pending, 'state': value}
        if value == 'completed':
            # 完成后的确认记录只留编号和条数，不再挂着待确认时的原文标签。
            request = {key: request[key] for key in ('state', 'retention_days', 'audit_days') if key in request}
            request['record_ids'] = [item['record_id'] for item in pending.get('plan', [])]
        source.payload = {**source.payload, 'memory_removal_request': request}
    if cancel:
        state('cancelled');await db.flush()
        return '已取消，记忆没有改动。'
    try:
        expired_at=datetime.fromisoformat(str(pending.get('expires_at') or ''))
    except ValueError:
        state('expired');await db.flush()
        return '这次确认已失效，记忆没有改动。需要的话请重新发起。'
    if expired_at<=now():
        state('expired');await db.flush()
        return '这次确认已过期，记忆没有改动。需要的话请重新发起。'
    records=[]
    for item in pending['plan']:
        row=await db.get(RelationshipMemory,uuid.UUID(item['record_id']),with_for_update=True,populate_existing=True)
        if row is None or row.user_id!=session.user_id or row.pair_id!=session.pair_id or _record_ref(row)!=item['version']:
            state('changed');await db.flush()
            return '待停用的记忆已经变化，未改动任何记录。请重新核对范围后确认。'
        records.append((row,item))
    stamp=now()
    sources=set()
    retired_ids = {str(row.id) for row, item in records}
    retired_facts = []
    for row,item in records:
        content=row.content or {}
        entries = [content, *fact_evidence(content)]
        if row.memory_type == 'person':
            entries = content.get('person_evidence') or [content]
            if item['remaining'] is not None:
                remaining_sources = {str(entry.get('source_user_message_id') or '')
                                     for entry in item['remaining'].get('person_evidence', [])}
                entries = [entry for entry in entries if str(entry.get('source_user_message_id') or '') not in remaining_sources]
        for entry in entries:
            detail = str(entry.get('detail') or '').split('；时间限定：', 1)[0]
            if detail:
                retired_facts.append(detail)
            for field in ('source_user_message_id','authorization_user_message_id'):
                if entry.get(field): sources.add(str(entry[field]))
        sources.update(str(value) for value in content.get('retired_source_ids', []) if value)
    # 所有版本先核对完，再在同一事务内留档和停用，接口失败时一起回滚。
    for row,item in records:
        snapshot={'subject':row.subject,'memory_type':row.memory_type,'content':row.content,'importance':row.importance,
                  'retired_scope':item['label'],'remaining_content':item['remaining'],
                  'source_session_id':str(row.source_session_id) if row.source_session_id else None,
                  'created_at':row.created_at.isoformat() if row.created_at else None}
        raw=json.dumps(snapshot,ensure_ascii=False,sort_keys=True).encode()
        db.add(MemoryRemovalArchive(user_id=session.user_id,pair_id=session.pair_id,memory_id=row.id,request_message_id=source.id,
                                   confirmation_message_id=current.id,snapshot_ciphertext=_cipher().encrypt(raw).decode(),
                                   content_digest=hashlib.sha256(raw).hexdigest(),created_at=stamp,
                                   retain_until=stamp+timedelta(days=pending['retention_days']),audit_until=stamp+timedelta(days=pending['audit_days'])))
        if item['remaining'] is None:
            await db.delete(row)
        else:
            row.content=item['remaining'];row.source_session_id=None;row.updated_at=stamp
    # 发起这次停用的那句请求也要退出模型上下文，否则同一句话下一轮又会被读回来。
    sources.add(str(source.id))
    # 只压掉承载了被停用原文的那几条消息：同名的无关对话不算停用范围。
    # 查询回复和取消过的范围预览也可能复述原文，必须跟随同一来源退出上下文。
    from app.services.memory_evidence import compact
    async for batch in _history_batches(db, user_id=session.user_id, pair_id=session.pair_id):
        for message in batch:
            payload = message.payload or {}
            request = payload.get('memory_removal_request') or {}
            preview_ids = {str(item['record_id']) for item in request.get('plan', [])} | set(request.get('record_ids') or [])
            recalled = set(payload.get('memory_recall_source_ids') or [])
            # 旧消息没有来源关联时，只兼容明确的记忆查询，不扩展到普通同名叙事。
            legacy_lookup = message.role == 'user' and bool(re.search(r'还记得|长期记忆|之前记的|记了什么|记了他们什么', message.content or ''))
            legacy_match = legacy_lookup and any(len(compact(fact).lstrip('我')) >= 4 and compact(fact).lstrip('我') in compact(message.content) for fact in retired_facts)
            if recalled & sources:
                reply_id = (payload.get('_delivery') or {}).get('reply_id')
                if reply_id:
                    sources.add(str(reply_id))
            if preview_ids & retired_ids or legacy_match:
                sources.add(str(message.id))
    async for batch in _history_batches(db, user_id=session.user_id, pair_id=session.pair_id):
        for message in batch:
            if str(message.id) in sources:
                reply_id = ((message.payload or {}).get('_delivery') or {}).get('reply_id')
                if reply_id:
                    sources.add(str(reply_id))
    touched_sessions=set()
    async for batch in _history_batches(db, user_id=session.user_id, pair_id=session.pair_id):
        for message in batch:
            preview = str((message.payload or {}).get('memory_removal_request_id') or '') in sources
            if str(message.id) in sources or preview:
                message.payload={**(message.payload or {}),'memory_suppressed_for_ai':True}
                touched_sessions.add(message.session_id)
    touched = list(touched_sessions)
    for offset in range(0, len(touched), 250):
        await db.execute(update(AgentChatSession).where(AgentChatSession.id.in_(touched[offset:offset+250]))
                         .values(summary_json=None, summary_updated_at=stamp))
    state('completed');await db.flush()
    return f'已确认，这 {len(records)} 条内容不再参与 AI 记忆检索和回复。单独的加密追溯副本保留 {pending["retention_days"]} 天，聊天记录仍按原规则保留，没有删除。'


async def read_archive(db, archive_id, *, user_id, pair_id):
    """供受控后台追溯使用，不注册为模型工具，也不合并进正常上下文。"""
    row=await db.get(MemoryRemovalArchive,archive_id)
    if row is None or str(row.user_id)!=str(user_id) or str(row.pair_id)!=str(pair_id) or row.retain_until<=now() or not row.snapshot_ciphertext:
        return None
    return json.loads(_cipher().decrypt(row.snapshot_ciphertext.encode()))


async def sweep_archives(db):
    rows=(await db.execute(select(MemoryRemovalArchive).where(MemoryRemovalArchive.retain_until<=now(),or_(MemoryRemovalArchive.snapshot_ciphertext.is_not(None),MemoryRemovalArchive.audit_until<=now())).order_by(MemoryRemovalArchive.retain_until).limit(500))).scalars().all()
    for row in rows:
        if row.audit_until<=now():
            await db.delete(row)
        else:
            row.snapshot_ciphertext=None
    await db.flush()
    return len(rows)
