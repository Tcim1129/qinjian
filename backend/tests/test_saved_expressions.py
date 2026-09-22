"""Private expression API behavior against SQLite, without model/provider calls."""
import asyncio
import importlib.util
import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import DEMO_USER_ID, get_current_user
from app.core.database import Base, get_db
from app.models import Pair, PairStatus, PairType, User


@pytest.fixture
def workspace():
    from app.api.v1.expressions import router

    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    factory = async_sessionmaker(engine, expire_on_commit=False)
    ids = {key: uuid.uuid4() for key in ['alice', 'bob', 'outsider', 'pair']}
    actor = {'id': ids['alice']}

    async def seed():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as db:
            for name in ['alice', 'bob', 'outsider']:
                db.add(User(id=ids[name], email=f'{name}@test.invalid', nickname=name, password_hash='unused'))
            db.add(User(id=DEMO_USER_ID, email='sample@test.invalid', nickname='sample', password_hash='unused'))
            db.add(Pair(id=ids['pair'], user_a_id=ids['alice'], user_b_id=ids['bob'], type=PairType.COUPLE,
                        status=PairStatus.ACTIVE, invite_code='expression-test'))
            await db.commit()

    asyncio.run(seed())

    async def db_override():
        async with factory() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def user_override():
        async with factory() as db:
            return await db.get(User, actor['id'])

    app = FastAPI()
    app.include_router(router, prefix='/api/v1')
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_current_user] = user_override
    with TestClient(app) as client:
        yield client, ids, actor, factory
    asyncio.run(engine.dispose())


def test_save_exact_final_text_retry_list_and_owner_isolation(workspace):
    client, ids, actor, _ = workspace
    key = str(uuid.uuid4())
    path = f'/api/v1/expressions/{key}'
    text = '我今晚想自己待一会儿。\n明天再聊，不代表我不在意。'
    payload = {'text': text, 'pair_id': str(ids['pair'])}
    first = client.put(path, json=payload)
    assert first.status_code == 200, first.text
    assert first.json()['text'] == text
    assert first.json()['created_at'].endswith('Z')
    assert client.put(path, json=payload).json() == first.json()
    assert client.put(path, json={**payload, 'text': '更改内容'}).status_code == 409
    items = client.get('/api/v1/expressions', params={'pair_id': str(ids['pair'])}).json()
    assert len(items) == 1
    assert client.get('/api/v1/expressions').json() == []  # solo/pair separation

    actor['id'] = ids['bob']  # relationship membership never grants access
    assert client.get('/api/v1/expressions', params={'pair_id': str(ids['pair'])}).json() == []
    assert client.delete(path).status_code == 404
    assert client.put(path, json=payload).status_code == 404
    actor['id'] = ids['alice']
    assert client.get('/api/v1/expressions', params={'pair_id': str(ids['pair'])}).json()[0]['text'] == text


def test_deleted_text_is_erased_and_late_save_retry_cannot_restore_it(workspace):
    from app.models import SavedExpression
    client, _, _, factory = workspace
    key = str(uuid.uuid4())
    path = f'/api/v1/expressions/{key}'
    payload = {'text': '只保存自己确认的这一句。'}
    assert client.put(path, json=payload).status_code == 200
    assert client.delete(path).status_code == 204
    assert client.delete(path).status_code == 204
    assert client.get('/api/v1/expressions').json() == []
    assert client.put(path, json=payload).status_code == 409

    async def inspect():
        async with factory() as db:
            row = await db.get(SavedExpression, uuid.UUID(key))
            assert row.text is None
            assert row.deleted_at is not None
    asyncio.run(inspect())


def test_invalid_and_demo_writes_never_create_saved_records(workspace):
    client, ids, actor, _ = workspace
    path = f'/api/v1/expressions/{uuid.uuid4()}'
    for text in ['', '   ', '字' * 2001]:
        assert client.put(path, json={'text': text}).status_code == 422
    actor['id'] = ids['outsider']
    assert client.put(path, json={'text': '测试', 'pair_id': str(ids['pair'])}).status_code == 403
    actor['id'] = DEMO_USER_ID
    assert client.put(path, json={'text': '不能保存到公用样例账号'}).status_code == 403
    assert client.get('/api/v1/expressions').status_code == 403
    assert client.delete(path).status_code == 403
    actor['id'] = ids['alice']
    assert client.get('/api/v1/expressions').json() == []


def test_privacy_deletion_clears_own_solo_and_pair_expressions_only(workspace):
    from app.models import SavedExpression
    from app.services.privacy_retention import _purge_user_private_data
    client, ids, actor, factory = workspace
    client.put(f'/api/v1/expressions/{uuid.uuid4()}', json={'text': '私密记录'})
    client.put(f'/api/v1/expressions/{uuid.uuid4()}', json={'text': '关系中的私密表达', 'pair_id': str(ids['pair'])})
    actor['id'] = ids['bob']
    client.put(f'/api/v1/expressions/{uuid.uuid4()}', json={'text': '另一个人的表达'})

    async def purge():
        async with factory() as db:
            counts = await _purge_user_private_data(db, user_id=ids['alice'])
            await db.commit()
            remaining = (await db.execute(select(SavedExpression))).scalars().all()
            assert counts['saved_expressions'] == 2
            assert [row.user_id for row in remaining] == [ids['bob']]
    asyncio.run(purge())


def test_expression_migration_roundtrip_on_temporary_database():
    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration_path = Path(__file__).resolve().parents[1] / 'alembic/versions/2026_09_22_0044_add_saved_expressions.py'
    spec = importlib.util.spec_from_file_location('expression_migration', migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine('sqlite:///:memory:')
    with engine.begin() as conn:
        conn.exec_driver_sql('CREATE TABLE users (id CHAR(36) PRIMARY KEY)')
        conn.exec_driver_sql('CREATE TABLE pairs (id CHAR(36) PRIMARY KEY)')
        conn.exec_driver_sql("INSERT INTO users (id) VALUES ('sentinel-user')")
        migration.op = Operations(MigrationContext.configure(conn))
        migration.upgrade()
        inspector = sa.inspect(conn)
        assert inspector.has_table('saved_expressions')
        assert {column['name'] for column in inspector.get_columns('saved_expressions')} == {'id', 'user_id', 'pair_id', 'text', 'created_at', 'deleted_at'}
        assert len(inspector.get_foreign_keys('saved_expressions')) == 2
        migration.downgrade()
        assert not sa.inspect(conn).has_table('saved_expressions')
        assert conn.exec_driver_sql('SELECT id FROM users').scalar_one() == 'sentinel-user'
        migration.upgrade()
        assert sa.inspect(conn).has_table('saved_expressions')
    engine.dispose()
