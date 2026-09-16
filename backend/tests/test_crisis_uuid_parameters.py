from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import crisis as crisis_api
from app.core.database import Base
from app.core.time import current_local_date
from app.models import (
    Pair,
    PairStatus,
    PairType,
    RelationshipEvent,
    RelationshipProfileSnapshot,
    Report,
    ReportStatus,
    ReportType,
    User,
)


def _db_path_for(test_name: str) -> Path:
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    return db_dir / f"{test_name}-{uuid.uuid4().hex}.db"


def test_crisis_status_route_converts_path_pair_id_to_uuid():
    db_path = _db_path_for("crisis-status-uuid")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="crisis-status-a@example.com",
                nickname="Crisis A",
                password_hash="not-used",
            )
            user_b = User(
                email="crisis-status-b@example.com",
                nickname="Crisis B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="CRISISUUID",
            )
            db.add(pair)
            await db.flush()

            report = Report(
                pair_id=pair.id,
                type=ReportType.DAILY,
                status=ReportStatus.COMPLETED,
                content={"crisis_level": "high", "health_score": 61},
                health_score=61,
                report_date=current_local_date(),
            )
            db.add(report)
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

    app = FastAPI()
    app.include_router(crisis_api.router)
    app.dependency_overrides[crisis_api.get_db] = override_get_db
    app.dependency_overrides[crisis_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(f"/crisis/status/{state['pair_id']}")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["crisis_level"] == "high"
        assert payload["health_score"] == 61
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_repair_protocol_get_is_read_only():
    db_path = _db_path_for("repair-protocol-readonly")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="repair-protocol-a@example.com",
                nickname="Repair A",
                password_hash="not-used",
            )
            user_b = User(
                email="repair-protocol-b@example.com",
                nickname="Repair B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="REPAIRUUID",
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

    app = FastAPI()
    app.include_router(crisis_api.router)
    app.dependency_overrides[crisis_api.get_db] = override_get_db
    app.dependency_overrides[crisis_api.get_current_user] = override_current_user

    async def counts() -> tuple[int, int]:
        async with sessionmaker() as db:
            snapshot_result = await db.execute(
                select(func.count())
                .select_from(RelationshipProfileSnapshot)
                .where(RelationshipProfileSnapshot.pair_id == state["pair_id"])
            )
            event_result = await db.execute(
                select(func.count())
                .select_from(RelationshipEvent)
                .where(RelationshipEvent.event_type == "repair_protocol.requested")
            )
            return int(snapshot_result.scalar_one()), int(event_result.scalar_one())

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(f"/crisis/protocol/{state['pair_id']}")

        assert response.status_code == 200, response.text
        snapshot_count, event_count = asyncio.run(counts())
        assert snapshot_count == 0
        assert event_count == 0
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
