"""Retry behavior against real routes and SQLite; model calls are replaced."""
import asyncio
import uuid
from contextlib import contextmanager

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import agent
from app.core.database import Base
from app.core.time import current_local_date
from app.models import AgentChatMessage, AgentChatSession, User
from app.schemas import AgentChatRequest


def test_failed_turn_retry_reuses_user_message_and_completed_reply(monkeypatch):
    calls = []

    async def model(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise RuntimeError('provider unavailable')
        if any(message.get('content') == '空回复' for message in kwargs['messages']):
            return '', [], False
        return '明天方便的时候再聊吧。', [], False

    async def noop(*args, **kwargs):
        pass

    @contextmanager
    def privacy_scope(**kwargs):
        yield

    monkeypatch.setattr(agent, 'run_agent_loop', model)
    monkeypatch.setattr(agent, 'record_user_interaction_event', noop)
    monkeypatch.setattr(agent, 'privacy_audit_scope', privacy_scope)

    async def run():
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                user = User(email='delivery@test.com', nickname='测试', password_hash='unused')
                db.add(user)
                await db.flush()
                session = AgentChatSession(user_id=user.id, session_date=current_local_date())
                db.add(session)
                await db.commit()
                session_id, user_id = session.id, user.id
                message_id = uuid.uuid4()
                request = AgentChatRequest(content='我今天不想聊太久', surface='chat', client_message_id=message_id)
                with pytest.raises(HTTPException) as failure:
                    await agent.chat_with_agent(session_id, request, BackgroundTasks(), user, db)
                assert failure.value.status_code == 502
                user = await db.get(User, user_id)
                result = await agent.chat_with_agent(session_id, request, BackgroundTasks(), user, db)
                replay = await agent.chat_with_agent(session_id, request, BackgroundTasks(), user, db)
                messages = (await db.execute(select(AgentChatMessage))).scalars().all()
                assert [m.id for m in messages if m.role == 'user'] == [message_id]
                assert len([m for m in messages if m.role == 'assistant']) == 1
                assert replay.message_id == result.message_id
                assert replay.reply == result.reply
                assert len(calls) == 2
                with pytest.raises(HTTPException) as conflict:
                    await agent.chat_with_agent(session_id, AgentChatRequest(content='不同的内容', client_message_id=message_id), BackgroundTasks(), user, db)
                assert conflict.value.status_code == 409
                assert len(calls) == 2

                second_session = AgentChatSession(user_id=user.id, session_date=current_local_date())
                db.add(second_session)
                await db.commit()
                with pytest.raises(HTTPException) as wrong_session:
                    await agent.chat_with_agent(second_session.id, request, BackgroundTasks(), user, db)
                assert wrong_session.value.status_code == 409
                assert len(calls) == 2
                waiting_id = uuid.uuid4()
                db.add(AgentChatMessage(id=waiting_id, session_id=second_session.id, role='user', content='仍在等待', payload={'surface': 'chat', '_delivery': {'state': 'processing'}}))
                await db.commit()
                with pytest.raises(HTTPException) as waiting:
                    await agent.chat_with_agent(second_session.id, AgentChatRequest(content='仍在等待', surface='chat', client_message_id=waiting_id), BackgroundTasks(), user, db)
                assert waiting.value.status_code == 409
                assert len(calls) == 2
                empty_id = uuid.uuid4()
                second_id = second_session.id
                for _ in range(2):
                    user = await db.get(User, user_id)
                    with pytest.raises(HTTPException) as empty:
                        await agent.chat_with_agent(second_id, AgentChatRequest(content='空回复', surface='chat', client_message_id=empty_id), BackgroundTasks(), user, db)
                    assert empty.value.status_code == 502
                all_messages = (await db.execute(select(AgentChatMessage))).scalars().all()
                assert len([message for message in all_messages if message.id == empty_id]) == 1
                assert len([message for message in all_messages if message.role == 'assistant']) == 1
        finally:
            await engine.dispose()

    asyncio.run(run())
