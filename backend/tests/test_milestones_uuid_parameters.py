from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import milestones as milestones_api
from app.core.database import Base
from app.core.time import current_local_date
from app.models import Milestone, Pair, PairStatus, PairType, User


def _db_path_for(test_name: str) -> Path:
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    return db_dir / f"{test_name}-{uuid.uuid4().hex}.db"


def test_get_milestones_route_converts_path_pair_id_to_uuid():
    db_path = _db_path_for("milestones-list-uuid")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="milestones-a@example.com",
                nickname="Milestone A",
                password_hash="not-used",
            )
            user_b = User(
                email="milestones-b@example.com",
                nickname="Milestone B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="MILESTONE1",
            )
            db.add(pair)
            await db.flush()

            milestone = Milestone(
                pair_id=pair.id,
                type="anniversary",
                title="First trip",
                date=current_local_date(),
            )
            db.add(milestone)
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
    app.include_router(milestones_api.router)
    app.dependency_overrides[milestones_api.get_db] = override_get_db
    app.dependency_overrides[milestones_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(f"/milestones/{state['pair_id']}")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["title"] == "First trip"
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
