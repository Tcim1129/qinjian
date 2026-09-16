from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import tree as tree_api
from app.core.time import current_local_date
from app.core import database as database_core
from app.core.database import Base
from app.models import (
    Checkin,
    Pair,
    PairStatus,
    PairType,
    RelationshipTask,
    RelationshipTree,
    TaskStatus,
    User,
)


def _db_path_for(test_name: str) -> Path:
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    return db_dir / f"{test_name}-{uuid.uuid4().hex}.db"


def test_tree_status_route_uses_parsed_pair_uuid():
    db_path = _db_path_for("tree-status-uuid")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="tree-status-a@example.com",
                nickname="Tree A",
                password_hash="not-used",
            )
            user_b = User(
                email="tree-status-b@example.com",
                nickname="Tree B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="QWERTYUIOP",
            )
            db.add(pair)
            await db.commit()
            state["user_id"] = user_a.id
            state["pair_id"] = pair.id

    asyncio.run(setup_database())

    async def override_get_db():
        async with sessionmaker() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, state["user_id"])

    app = FastAPI()
    app.include_router(tree_api.router)
    app.dependency_overrides[tree_api.get_db] = override_get_db
    app.dependency_overrides[tree_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(f"/tree/status?pair_id={state['pair_id']}")

        assert response.status_code == 200, response.text
        assert response.json()["growth_points"] == 0
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_tree_status_returns_energy_nodes_from_today_activity():
    db_path = _db_path_for("tree-energy-status")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        today = current_local_date()
        async with sessionmaker() as db:
            user_a = User(
                email="tree-energy-a@example.com",
                nickname="Tree Energy A",
                password_hash="not-used",
            )
            user_b = User(
                email="tree-energy-b@example.com",
                nickname="Tree Energy B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="ENERGYNODE",
            )
            db.add(pair)
            await db.flush()

            db.add_all(
                [
                    Checkin(
                        pair_id=pair.id,
                        user_id=user_a.id,
                        content="今天我愿意先记下来。",
                        checkin_date=today,
                    ),
                    Checkin(
                        pair_id=pair.id,
                        user_id=user_b.id,
                        content="我也同步一下今天的状态。",
                        task_completed=True,
                        checkin_date=today,
                    ),
                    RelationshipTask(
                        pair_id=pair.id,
                        title="说一句具体感谢",
                        status=TaskStatus.COMPLETED,
                        due_date=today,
                        completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    ),
                ]
            )
            await db.commit()
            state["user_id"] = user_a.id
            state["pair_id"] = pair.id

    asyncio.run(setup_database())

    async def override_get_db():
        async with sessionmaker() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, state["user_id"])

    app = FastAPI()
    app.include_router(tree_api.router)
    app.dependency_overrides[tree_api.get_db] = override_get_db
    app.dependency_overrides[tree_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(f"/tree/status?pair_id={state['pair_id']}")

        assert response.status_code == 200, response.text
        nodes = {node["key"]: node for node in response.json()["energy_nodes"]}
        assert nodes["my_record"] == {
            "key": "my_record",
            "label": "记录",
            "points": 10,
            "state": "available",
            "collected": False,
            "available": True,
            "hint": "点击收取成长值",
        }
        assert nodes["partner_record"]["available"] is True
        assert nodes["partner_record"]["points"] == 8
        assert nodes["small_repair"]["available"] is True
        assert nodes["small_repair"]["points"] == 12
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_collect_energy_node_adds_points_and_prevents_duplicate_collection():
    db_path = _db_path_for("tree-energy-collect")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        today = current_local_date()
        async with sessionmaker() as db:
            user_a = User(
                email="tree-collect-a@example.com",
                nickname="Tree Collect A",
                password_hash="not-used",
            )
            user_b = User(
                email="tree-collect-b@example.com",
                nickname="Tree Collect B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="COLLECT123",
            )
            db.add(pair)
            await db.flush()

            db.add(
                Checkin(
                    pair_id=pair.id,
                    user_id=user_a.id,
                    content="今天先把真实情况写下来。",
                    checkin_date=today,
                )
            )
            await db.commit()
            state["user_id"] = user_a.id
            state["pair_id"] = pair.id

    asyncio.run(setup_database())

    async def override_get_db():
        async with sessionmaker() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, state["user_id"])

    app = FastAPI()
    app.include_router(tree_api.router)
    app.dependency_overrides[tree_api.get_db] = override_get_db
    app.dependency_overrides[tree_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            first = client.post(
                f"/tree/collect?pair_id={state['pair_id']}",
                json={"node_key": "my_record"},
            )
            duplicate = client.post(
                f"/tree/collect?pair_id={state['pair_id']}",
                json={"node_key": "my_record"},
            )

        assert first.status_code == 200, first.text
        assert first.json()["points_added"] == 10
        assert first.json()["growth_points"] == 10
        nodes = {node["key"]: node for node in first.json()["energy_nodes"]}
        assert nodes["my_record"]["collected"] is True
        assert nodes["my_record"]["state"] == "collected"

        assert duplicate.status_code == 400
        assert "已经收过" in duplicate.json()["detail"]

        async def read_points():
            async with sessionmaker() as db:
                result = await db.execute(
                    select(RelationshipTree.growth_points).where(
                        RelationshipTree.pair_id == state["pair_id"]
                    )
                )
                return result.scalar_one()

        assert asyncio.run(read_points()) == 10
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_collect_energy_nodes_reset_on_new_day():
    db_path = _db_path_for("tree-energy-reset")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        today = current_local_date()
        async with sessionmaker() as db:
            user_a = User(
                email="tree-reset-a@example.com",
                nickname="Tree Reset A",
                password_hash="not-used",
            )
            user_b = User(
                email="tree-reset-b@example.com",
                nickname="Tree Reset B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="RESETNODE1",
            )
            db.add(pair)
            await db.flush()

            db.add_all(
                [
                    RelationshipTree(
                        pair_id=pair.id,
                        growth_points=20,
                        energy_state={
                            "date": "2026-01-01",
                            "collected": ["my_record"],
                        },
                    ),
                    Checkin(
                        pair_id=pair.id,
                        user_id=user_a.id,
                        content="新的一天也记录。",
                        checkin_date=today,
                    ),
                ]
            )
            await db.commit()
            state["user_id"] = user_a.id
            state["pair_id"] = pair.id

    asyncio.run(setup_database())

    async def override_get_db():
        async with sessionmaker() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, state["user_id"])

    app = FastAPI()
    app.include_router(tree_api.router)
    app.dependency_overrides[tree_api.get_db] = override_get_db
    app.dependency_overrides[tree_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(f"/tree/status?pair_id={state['pair_id']}")

        assert response.status_code == 200, response.text
        nodes = {node["key"]: node for node in response.json()["energy_nodes"]}
        assert nodes["my_record"]["available"] is True
        assert nodes["my_record"]["collected"] is False
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_grow_tree_on_checkin_keeps_points_for_collectable_nodes():
    db_path = _db_path_for("tree-grow-uuid")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="tree-grow-a@example.com",
                nickname="Grow A",
                password_hash="not-used",
            )
            user_b = User(
                email="tree-grow-b@example.com",
                nickname="Grow B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="ZXCVBNMASD",
            )
            db.add(pair)
            await db.commit()
            state["pair_id"] = pair.id

    asyncio.run(setup_database())
    original_async_session = database_core.async_session
    database_core.async_session = sessionmaker

    async def run_task_and_read_points():
        await tree_api.grow_tree_on_checkin(str(state["pair_id"]), both_done=True, streak=0)
        async with sessionmaker() as db:
            result = await db.execute(
                select(RelationshipTree.growth_points).where(
                    RelationshipTree.pair_id == state["pair_id"]
                )
            )
            return result.scalar_one()

    try:
        growth_points = asyncio.run(run_task_and_read_points())
        assert growth_points == 0
    finally:
        database_core.async_session = original_async_session
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
