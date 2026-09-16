from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import tasks as tasks_api
from app.core.database import Base
from app.core.time import current_local_date
from app.models import Pair, PairStatus, PairType, RelationshipTask, User


def _db_path_for(test_name: str) -> Path:
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    return db_dir / f"{test_name}-{uuid.uuid4().hex}.db"


def test_daily_tasks_route_converts_path_pair_id_to_uuid(monkeypatch):
    db_path = _db_path_for("tasks-daily-uuid")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="tasks-daily-a@example.com",
                nickname="Tasks A",
                password_hash="not-used",
            )
            user_b = User(
                email="tasks-daily-b@example.com",
                nickname="Tasks B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="TASKSUUID1",
            )
            db.add(pair)
            await db.flush()

            task = RelationshipTask(
                pair_id=pair.id,
                title="UUID route task",
                description="Should load without a 500.",
                due_date=current_local_date(),
            )
            db.add(task)
            await db.commit()
            state["user_id"] = user_a.id
            state["pair_id"] = pair.id

    asyncio.run(setup_database())

    async def override_get_db():
        async with sessionmaker() as db:
            yield db

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, state["user_id"])

    async def fake_build_pair_task_adaptation(*_args, **_kwargs):
        return {}, {}

    async def fake_get_latest_task_feedback_map(*_args, **_kwargs):
        return {}

    monkeypatch.setattr(
        tasks_api,
        "build_pair_task_adaptation",
        fake_build_pair_task_adaptation,
    )
    monkeypatch.setattr(
        tasks_api,
        "get_latest_task_feedback_map",
        fake_get_latest_task_feedback_map,
    )
    monkeypatch.setattr(
        tasks_api,
        "personalize_task_payloads",
        lambda payloads, _strategy: payloads,
    )

    app = FastAPI()
    app.include_router(tasks_api.router)
    app.dependency_overrides[tasks_api.get_db] = override_get_db
    app.dependency_overrides[tasks_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(f"/tasks/daily/{state['pair_id']}")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["date"] == str(current_local_date())
        assert len(payload["tasks"]) == 1
        assert payload["tasks"][0]["title"] == "UUID route task"
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_daily_tasks_route_falls_back_when_strategy_build_fails(monkeypatch):
    db_path = _db_path_for("tasks-daily-fallback")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="tasks-fallback-a@example.com",
                nickname="Fallback A",
                password_hash="not-used",
            )
            user_b = User(
                email="tasks-fallback-b@example.com",
                nickname="Fallback B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="TASKSAFE01",
            )
            db.add(pair)
            await db.commit()
            state["user_id"] = user_a.id
            state["pair_id"] = pair.id

    asyncio.run(setup_database())

    async def override_get_db():
        async with sessionmaker() as db:
            yield db

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, state["user_id"])

    async def exploding_build_pair_task_adaptation(*_args, **_kwargs):
        raise RuntimeError("strategy unavailable")

    monkeypatch.setattr(
        tasks_api,
        "build_pair_task_adaptation",
        exploding_build_pair_task_adaptation,
    )

    app = FastAPI()
    app.include_router(tasks_api.router)
    app.dependency_overrides[tasks_api.get_db] = override_get_db
    app.dependency_overrides[tasks_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(f"/tasks/daily/{state['pair_id']}")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["date"] == str(current_local_date())
        assert payload["tasks"], payload
        assert payload["adaptive_strategy"]["intensity"] == "steady"
        assert payload["plan_scorecard"] is None
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
