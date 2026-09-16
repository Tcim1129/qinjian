"""Client turn identity and conservative retry admission; no generated fallback."""
import uuid

from fastapi import HTTPException
from sqlalchemy import select

from app.models import AgentChatMessage
from app.schemas import AgentChatResponse


async def prepare_chat_turn(db, *, session_id, client_message_id, content, payload):
    # The caller locks the owned session until this admission is committed.
    previous = await db.get(AgentChatMessage, client_message_id) if client_message_id else None
    if previous is not None:
        if previous.session_id != session_id or previous.role != 'user':
            raise HTTPException(status_code=409, detail='这条消息不属于当前聊天，请重新发送。')
        old_payload = previous.payload or {}
        if previous.content != content or any(old_payload.get(key) != payload.get(key) for key in ('surface', 'scene_context', 'voice_evidence')):
            raise HTTPException(status_code=409, detail='这条消息已经修改，请作为新消息发送。')
        delivery = old_payload.get('_delivery', {})
        if delivery.get('state') == 'completed':
            reply = await db.get(AgentChatMessage, uuid.UUID(delivery['reply_id']))
            if reply is None or reply.session_id != session_id or reply.role != 'assistant':
                raise HTTPException(status_code=409, detail='回复暂时无法读取，请重新打开聊天。')
            return previous, AgentChatResponse(
                reply=reply.content, action=delivery.get('action', 'chat'), message_id=reply.id,
                task_proposals=(reply.payload or {}).get('task_proposals', []),
            ), False
        if delivery.get('state') != 'failed':
            # Do not re-run a possibly active request, even after a client timeout.
            raise HTTPException(status_code=409, detail='上一条请求还在处理中，请稍后重试。', headers={'Retry-After': '3'})
        newer = (await db.execute(select(AgentChatMessage.id).where(
            AgentChatMessage.session_id == session_id,
            AgentChatMessage.role == 'user', AgentChatMessage.created_at > previous.created_at,
        ).limit(1))).scalar_one_or_none()
        if newer is not None:
            raise HTTPException(status_code=409, detail='这之后已有新的聊天，请重新编辑后发送。')
        previous.payload = {**old_payload, '_delivery': {'state': 'processing'}}
        return previous, None, False
    message = AgentChatMessage(
        id=client_message_id or uuid.uuid4(), session_id=session_id, role='user', content=content,
        payload={**payload, '_delivery': {'state': 'processing'}},
    )
    db.add(message)
    return message, None, True


def complete_chat_turn(message, *, reply_id, action):
    message.payload = {**(message.payload or {}), '_delivery': {
        'state': 'completed', 'reply_id': str(reply_id), 'action': action,
    }}


async def fail_chat_turn(db, message_id):
    message = await db.get(AgentChatMessage, message_id, populate_existing=True, with_for_update=True)
    if message is not None and (message.payload or {}).get('_delivery', {}).get('state') == 'processing':
        message.payload = {**(message.payload or {}), '_delivery': {'state': 'failed'}}
        await db.commit()
