import asyncio
import uuid
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import agent, tasks
from app.ai.agent_loop import _next_week_reminder_date
from app.core.database import Base
from app.core.time import current_local_date
from app.models import AgentChatMessage, AgentChatSession, Pair, PairStatus, PairType, RelationshipTask, User


def test_single_explicit_next_week_reminder_uses_business_calendar():
    today = date(2026, 11, 18)
    request = '提醒我下周六给妈妈打电话，但先给我看一下建议，我再决定加不加。'
    assert _next_week_reminder_date([{'role': 'user', 'content': request}], today) == date(2026, 11, 28)
    assert _next_week_reminder_date([{'role': 'user', 'content': '我朋友说“提醒我下周六散步”'}], today) is None
    assert _next_week_reminder_date([{'role': 'user', 'content': '提醒我下周六或周日去散步'}], today) is None
    assert _next_week_reminder_date([{'role': 'user', 'content': request}, {'role': 'user', 'content': '等我再想想'}], today) is None


def test_task_proposals_deduplicate_only_the_same_details():
    def step(number, due_date):
        data = {'title': '打电话', 'description': '给妈妈', 'requires_confirmation': True,
                'due_date': due_date, 'proposal_id': str(number)}
        return SimpleNamespace(tool_results=[{'name': 'create_task', 'result': {'status': 'success', 'data': data}}])

    proposals = agent._task_proposals_from_steps([step(1, '2026-11-28'), step(2, '2026-11-28'), step(3, '2026-12-05')])
    assert [p['proposal_id'] for p in proposals] == ['2', '3']


def test_confirm_requires_owned_saved_proposal_and_is_idempotent(monkeypatch):
    async def noop(*args, **kwargs): pass
    monkeypatch.setattr(tasks, 'refresh_profile_and_plan', noop)

    async def run():
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                a = User(email='confirm-a@test.com', nickname='A', password_hash='unused')
                b = User(email='confirm-b@test.com', nickname='B', password_hash='unused')
                db.add_all([a, b]); await db.flush()
                pair = Pair(user_a_id=a.id, user_b_id=b.id, type=PairType.COUPLE, status=PairStatus.ACTIVE, invite_code='CONFIRMACT')
                db.add(pair); await db.flush()
                session = AgentChatSession(user_id=a.id, pair_id=pair.id, session_date=current_local_date())
                db.add(session); await db.flush()
                proposal_id = uuid.uuid4()
                due_date = current_local_date() + timedelta(days=1)
                message = AgentChatMessage(session_id=session.id, role='assistant', content='要加入明日安排吗？', payload={'task_proposals': [{
                    'proposal_id': str(proposal_id), 'title': '一起散步', 'description': '饭后十分钟', 'due_date': due_date.isoformat(), 'requires_confirmation': True,
                }]})
                db.add(message); await db.commit()
                assert not (await db.execute(select(RelationshipTask))).scalars().all()
                with pytest.raises(HTTPException) as denied:
                    await agent.confirm_agent_task(session.id, message.id, proposal_id, b, db)
                assert denied.value.status_code == 404
                with pytest.raises(HTTPException):
                    await agent.confirm_agent_task(session.id, message.id, uuid.uuid4(), a, db)
                first = await agent.confirm_agent_task(session.id, message.id, proposal_id, a, db)
                again = await agent.confirm_agent_task(session.id, message.id, proposal_id, a, db)
                assert first['task']['id'] == again['task']['id']
                saved = (await db.execute(select(RelationshipTask))).scalars().all()
                assert len(saved) == 1
                assert saved[0].due_date == due_date
                assert saved[0].user_id == a.id
                assert saved[0].status.value == 'pending'
                assert message.payload['task_proposals'][0]['confirmed_task_id'] == str(saved[0].id)
                pair.status = PairStatus.ENDED
                await db.commit()
                with pytest.raises(HTTPException):
                    await agent.confirm_agent_task(session.id, message.id, proposal_id, a, db)
        finally: await engine.dispose()
    asyncio.run(run())


def test_solo_user_can_confirm_a_reminder_for_themselves(monkeypatch):
    """单人模式没有对方，给自己建提醒也应该能确认。"""
    async def noop(*args, **kwargs): pass
    monkeypatch.setattr(tasks, 'refresh_profile_and_plan', noop)

    async def run():
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                solo = User(email='solo@test.com', nickname='Solo', password_hash='unused')
                db.add(solo); await db.flush()
                pair = Pair(user_a_id=solo.id, user_b_id=None, type=PairType.COUPLE, status=PairStatus.ACTIVE, invite_code='SOLOACT')
                db.add(pair); await db.flush()
                session = AgentChatSession(user_id=solo.id, pair_id=pair.id, session_date=current_local_date())
                db.add(session); await db.flush()
                proposal_id = uuid.uuid4()
                due_date = current_local_date() + timedelta(days=1)
                message = AgentChatMessage(session_id=session.id, role='assistant', content='要加到安排里吗？', payload={'task_proposals': [{
                    'proposal_id': str(proposal_id), 'title': '去医院复查', 'description': '周五下午三点',
                    'due_date': due_date.isoformat(), 'requires_confirmation': True,
                }]})
                db.add(message); await db.commit()

                result = await agent.confirm_agent_task(session.id, message.id, proposal_id, solo, db)
                assert result['task']['id']
                saved = (await db.execute(select(RelationshipTask))).scalars().all()
                assert len(saved) == 1 and saved[0].user_id == solo.id

                # 涉及两个人的安排仍然要求配对完整。
                with pytest.raises(HTTPException) as denied:
                    await tasks.create_manual_task(pair.id, tasks.TaskCreateRequest(
                        title='一起散步', description='', due_date=due_date, target_scope='both',
                    ), user=solo, db=db)
                assert denied.value.status_code == 400
        finally: await engine.dispose()
    asyncio.run(run())
