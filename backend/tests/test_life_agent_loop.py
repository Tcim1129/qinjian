"""Real local routes, tools and SQLite persistence; only the model is replaced."""
import asyncio
import json
import uuid
from contextlib import contextmanager
from datetime import timedelta
from types import SimpleNamespace

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai import agent_loop
from app.api.v1 import agent, tasks
from app.core.database import Base
from app.core.time import current_local_date
from app.models import AgentChatMessage, AgentChatSession, Checkin, Pair, PairStatus, PairType, RelationshipTask, User
from app.schemas import AgentChatRequest, TaskFeedbackRequest


def test_scene_to_tool_proposal_confirmation_feedback_and_next_day(monkeypatch):
    calls = []
    tomorrow = (current_local_date() + timedelta(days=1)).isoformat()
    async def completion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            function = SimpleNamespace(name='create_task', arguments=json.dumps({'title': '问问方便的时间', 'description': '只问时间，具体的事以后再聊。'}))
        elif len(calls) == 3:
            function = SimpleNamespace(name='get_task_feedback', arguments='{}')
        elif len(calls) == 4:
            function = SimpleNamespace(name='create_task', arguments=json.dumps({'title': '留一句明天再聊', 'description': '先休息，不用今晚聊完。', 'due_date': tomorrow}))
        else:
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='先从这一小步开始，愿意的话再加入安排。', tool_calls=None))])
        tool = SimpleNamespace(id=f'tool-{len(calls)}', type='function', function=function)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[tool]))])
    async def noop(*args, **kwargs): pass
    @contextmanager
    def privacy_scope(**kwargs): yield
    monkeypatch.setattr(agent_loop, 'create_chat_completion', completion)
    monkeypatch.setattr(agent, 'record_user_interaction_event', noop)
    monkeypatch.setattr(agent, 'privacy_audit_scope', privacy_scope)
    monkeypatch.setattr(tasks, 'refresh_profile_and_plan', noop)

    async def run():
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                a = User(email='loop-a@test.com', nickname='A', password_hash='unused')
                b = User(email='loop-b@test.com', nickname='B', password_hash='unused')
                db.add_all([a, b]); await db.flush()
                pair = Pair(user_a_id=a.id, user_b_id=b.id, type=PairType.COUPLE, status=PairStatus.ACTIVE, invite_code='LOOPSCENE')
                db.add(pair); await db.flush()
                session = AgentChatSession(user_id=a.id, pair_id=pair.id, session_date=current_local_date())
                db.add(session); await db.commit()
                req = AgentChatRequest(content='先做点什么？', surface='chat', scene_context={'source_label': '我的记录', 'summary': '约定临时取消了。', 'intent': 'plan'})
                reply = await agent.chat_with_agent(session.id, req, BackgroundTasks(), a, db)
                assert len(reply.task_proposals) == 1
                assert not (await db.execute(select(RelationshipTask))).scalars().all()
                assert not (await db.execute(select(Checkin))).scalars().all()
                user_message = (await db.execute(select(AgentChatMessage).where(AgentChatMessage.role == 'user'))).scalar_one()
                assert user_message.content == '先做点什么？'
                assert user_message.payload['scene_context']['summary'] == '约定临时取消了。'
                assert '约定临时取消了。' in calls[0]['messages'][1]['content']
                proposal = uuid.UUID(reply.task_proposals[0]['proposal_id'])
                first = await agent.confirm_agent_task(session.id, reply.message_id, proposal, a, db)
                again = await agent.confirm_agent_task(session.id, reply.message_id, proposal, a, db)
                assert first['task']['id'] == again['task']['id']
                task = (await db.execute(select(RelationshipTask))).scalar_one()
                await tasks.submit_task_feedback(str(task.id), TaskFeedbackRequest(outcome='not_yet', note='今天太累，不想聊'), a, db)
                next_reply = await agent.chat_with_agent(session.id, AgentChatRequest(content='那明天呢？', surface='chat', scene_context={'intent': 'plan'}), BackgroundTasks(), a, db)
                assert next_reply.task_proposals[0]['due_date'] == tomorrow
                tool_messages = [message for message in calls[3]['messages'] if message['role'] == 'tool']
                assert '今天太累，不想聊' in json.dumps(tool_messages, ensure_ascii=False)
                assert task.status.value == 'pending'
                assert len((await db.execute(select(RelationshipTask))).scalars().all()) == 1
        finally: await engine.dispose()
    asyncio.run(run())
