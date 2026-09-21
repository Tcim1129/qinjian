import asyncio
import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import agent, tasks
from app.core.database import Base
from app.core.time import current_local_date
from app.models import AgentChatMessage, AgentChatSession, Pair, PairStatus, PairType, RelationshipTask, User


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
