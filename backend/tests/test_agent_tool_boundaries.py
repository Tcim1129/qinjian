import asyncio
import json
from types import SimpleNamespace

import pytest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai import agent_loop, multi_agent, tools
from app.core.database import Base
from app.core.time import current_local_date
from app.models import Checkin, CrisisLevel, Pair, PairType, PairStatus, RelationshipTask, User


@pytest.mark.parametrize("level,expected", [
    (CrisisLevel.MILD, 'low'),
    (CrisisLevel.MODERATE, 'medium'),
    (CrisisLevel.SEVERE, 'severe'),
    ('CrisisLevel.MILD', 'low'),
    ('CrisisLevel.MODERATE', 'medium'),
    ('severe', 'severe'),
])
def test_crisis_level_normalization_accepts_stored_enum_and_legacy_text(level, expected):
    assert tools._normalize_crisis_level(level) == expected


def test_tools_only_expose_visible_records_and_actor_tasks():
    async def run():
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                a = User(email='a@audit.test', nickname='A', password_hash='unused')
                b = User(email='b@audit.test', nickname='B', password_hash='unused')
                outsider = User(email='c@audit.test', nickname='C', password_hash='unused')
                db.add_all([a, b, outsider]); await db.flush()
                pair = Pair(user_a_id=a.id, user_b_id=b.id, type=PairType.COUPLE, status=PairStatus.ACTIVE, invite_code='AUDITTOOLS')
                db.add(pair); await db.flush()
                db.add(Checkin(pair_id=pair.id, user_id=b.id, content='私密原文 SECRET_RAW', archive_summary='愿意分享的摘要', checkin_date=current_local_date()))
                for owner, title in [(a.id, 'mine'), (b.id, 'partner-private'), (None, 'shared')]:
                    db.add(RelationshipTask(pair_id=pair.id, user_id=owner, title=title, description='', category='activity', due_date=current_local_date()))
                await db.flush()
                context = dict(pair_id=str(pair.id), user_id=str(a.id), db=db)
                recent = await tools.execute_tool('get_recent_events', {'user_id': str(b.id)}, **context)
                assert recent.get('status') == 'success', recent
                assert 'SECRET_RAW' not in json.dumps(recent, ensure_ascii=False)
                assert '这天更像在记录平静。' in json.dumps(recent, ensure_ascii=False)
                assert '愿意分享的摘要' not in json.dumps(recent, ensure_ascii=False)
                search = await tools.execute_tool('search_timeline', {'query': 'SECRET_RAW'}, **context)
                assert search['data'] == []
                tasks = await tools.execute_tool('get_active_tasks', {}, **context)
                assert {t['title'] for t in tasks['data']} == {'mine', 'shared'}
                denied = await tools.execute_tool('get_active_tasks', {}, pair_id=str(pair.id), user_id=str(outsider.id), db=db)
                assert denied.get('status') != 'success'
                proposal = await tools.execute_tool('create_task', {'title': '散步十分钟', 'description': '明天晚饭后'}, **context)
                assert proposal['status'] == 'success', proposal
                assert proposal['data']['requires_confirmation'] is True
                assert proposal['data']['due_date']
                assert len((await db.execute(select(RelationshipTask))).scalars().all()) == 3
        finally:
            await engine.dispose()
    asyncio.run(run())


def test_loop_enforces_allowlist_even_if_model_calls_an_unoffered_tool(monkeypatch):
    calls = []
    async def fake_completion(**kwargs):
        calls.append(kwargs)
        tc = SimpleNamespace(id='call-1', type='function', function=SimpleNamespace(name='extract_checkin_data', arguments='{}'))
        message = SimpleNamespace(content='结束' if len(calls) > 1 else None, tool_calls=None if len(calls) > 1 else [tc])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])
    monkeypatch.setattr(agent_loop, 'create_chat_completion', fake_completion)
    _, steps, extracted = asyncio.run(agent_loop.run_agent_loop(messages=[{'role': 'user', 'content': '聊聊'}], include_checkin_tool=False, allowed_tool_names=['analyze_behavior'], max_steps=2))
    assert extracted is False
    assert steps[0].tool_results[0]['result'].get('status') != 'success'
    assert tools.get_openai_tools_schema(allowed_names=[]) == []


def test_multi_agent_roles_can_use_tools_and_keep_action_results(monkeypatch):
    seen = []
    async def fake_loop(**kwargs):
        seen.append(kwargs)
        assert kwargs['max_steps'] >= 2
        index = len(seen) - 1
        step = agent_loop.AgentStep(step_index=0, thought='检查', tool_calls=[{'function': {'name': kwargs['allowed_tool_names'][0]}}], tool_results=[{'marker': index}], timestamp=0, duration_ms=1)
        return f'阶段{index}', [step], False
    monkeypatch.setattr(multi_agent, 'run_agent_loop', fake_loop)
    _, steps, swarm, _ = asyncio.run(multi_agent.run_multi_agent_flow([{'role': 'user', 'content': '想安排散步'}]))
    assert [s.role for s in swarm] == ['perception', 'analysis', 'action', 'companion']
    assert len(steps) == 4
    assert [s.step_index for s in steps] == [0, 1, 2, 3]
    assert '阶段0' in json.dumps(seen[1]['messages'], ensure_ascii=False)


def test_agent_loop_reuses_pair_access_validation(monkeypatch):
    # 同一个 ReAct 循环里多次调用工具，权限校验只应执行一次
    validations = {'count': 0}
    async def counting_validate(pair_id, user, db, require_active=True):
        validations['count'] += 1
        return None
    monkeypatch.setattr(tools, 'validate_pair_access', counting_validate)

    calls = []
    async def fake_completion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            tool = SimpleNamespace(name='get_active_tasks', arguments='{}')
        elif len(calls) == 2:
            tool = SimpleNamespace(name='get_crisis_status', arguments='{}')
        else:
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='完成', tool_calls=None))])
        tc = SimpleNamespace(id=f'call-{len(calls)}', type='function', function=tool)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[tc]))])
    monkeypatch.setattr(agent_loop, 'create_chat_completion', fake_completion)

    async def run():
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                a = User(email='cache-a@test.com', nickname='A', password_hash='unused')
                b = User(email='cache-b@test.com', nickname='B', password_hash='unused')
                db.add_all([a, b]); await db.flush()
                pair = Pair(user_a_id=a.id, user_b_id=b.id, type=PairType.COUPLE, status=PairStatus.ACTIVE, invite_code='CACHETEST')
                db.add(pair); await db.commit()
                await agent_loop.run_agent_loop(
                    messages=[{'role': 'user', 'content': '测试'}],
                    pair_id=str(pair.id), user_id=str(a.id), db=db,
                    allowed_tool_names=['get_active_tasks', 'get_crisis_status'],
                    max_steps=3,
                )
        finally:
            await engine.dispose()
    asyncio.run(run())
    assert validations['count'] == 1, f"权限校验应只执行一次，实际 {validations['count']} 次"

def test_relationship_status_tool_accepts_pair_and_user_together():
    """配对和个人同时传进来时不能崩，安全状态只按配对看。"""
    async def run():
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                a = User(email='scope-a@audit.test', nickname='A', password_hash='unused')
                db.add(a); await db.flush()
                pair = Pair(user_a_id=a.id, user_b_id=None, type=PairType.COUPLE, status=PairStatus.ACTIVE, invite_code='SCOPETOOL')
                db.add(pair); await db.flush()

                result = await tools._get_relationship_status(db, pair_id=pair.id, user_id=a.id)
                assert isinstance(result, dict)
                personal = await tools._get_relationship_status(db, user_id=a.id)
                assert isinstance(personal, dict)
                empty = await tools._get_relationship_status(db)
                assert empty['status'] == 'ok'
        finally:
            await engine.dispose()
    asyncio.run(run())
