import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.tools import execute_tool
from app.ai.tools import get_openai_tools_schema
from app.core.database import Base
from app.models import Pair, PairStatus, PairType, RelationshipTask, User


def test_solo_model_only_receives_tools_it_can_actually_use():
    names = {item['function']['name'] for item in get_openai_tools_schema(pair_available=False)}
    assert {'create_task', 'run_skill_analysis'} <= names
    assert not {'get_active_tasks', 'get_recent_events', 'save_relationship_memory'} & names
    assert get_openai_tools_schema(pair_available=False, allowed_names=['get_active_tasks']) == []


def test_solo_task_suggestion_requires_actor_and_never_creates_a_task():
    async def run():
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                owner = User(email='solo-proposal@example.test', nickname='QA本人', password_hash='x')
                other = User(email='other-proposal@example.test', nickname='QA其他', password_hash='x')
                db.add_all([owner, other])
                await db.flush()
                args = {'title': '今晚散步十分钟', 'description': '自己愿意时再去。'}
                proposed = await execute_tool('create_task', args, pair_id=None, user_id=str(owner.id), db=db)
                assert proposed.get('status') == 'success', proposed
                assert proposed['data']['requires_confirmation'] is True
                assert not (await db.execute(select(RelationshipTask))).scalars().all()
                denied = await execute_tool('create_task', args, user_id=str(uuid.uuid4()), db=db)
                assert denied.get('status') != 'success'
                pair = Pair(user_a_id=other.id, status=PairStatus.ACTIVE, type=PairType.FRIEND, invite_code='A3H7K8M9Q2')
                db.add(pair)
                await db.flush()
                denied_pair = await execute_tool('create_task', args, pair_id=str(pair.id), user_id=str(owner.id), db=db)
                assert denied_pair.get('status') != 'success'
        finally:
            await engine.dispose()
    asyncio.run(run())
