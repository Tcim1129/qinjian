from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import agent as agent_api
from app.core.database import Base
from app.models import Pair, PairStatus, PairType, RelationshipEvent, User


def _db_path_for(test_name: str) -> Path:
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    return db_dir / f"{test_name}-{uuid.uuid4().hex}.db"


def test_decision_feedback_route_updates_target_event_and_records_feedback(monkeypatch):
    db_path = _db_path_for("decision-feedback-uuid")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(email="feedback-a@example.com", nickname="Feedback A", password_hash="not-used")
            user_b = User(email="feedback-b@example.com", nickname="Feedback B", password_hash="not-used")
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="FEEDBACK1",
            )
            db.add(pair)
            await db.flush()

            target_event = RelationshipEvent(
                pair_id=pair.id,
                user_id=user_a.id,
                event_type="message.simulated",
                entity_type="message_simulation",
                payload={"feedback_status": "pending_feedback"},
            )
            db.add(target_event)
            await db.commit()
            state["user_id"] = user_a.id
            state["pair_id"] = pair.id
            state["event_id"] = target_event.id

    asyncio.run(setup_database())

    async def override_get_db():
        async with sessionmaker() as db:
            yield db

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, state["user_id"])

    app = FastAPI()
    app.include_router(agent_api.router)
    app.dependency_overrides[agent_api.get_db] = override_get_db
    app.dependency_overrides[agent_api.get_current_user] = override_current_user

    async def load_target_event():
        async with sessionmaker() as db:
            return await db.get(RelationshipEvent, state["event_id"])

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/agent/decision-feedback/{state['event_id']}",
                json={"feedback_type": "direction_off", "note": "方向有点偏"},
            )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["accepted"] is True
        assert payload["target_event_id"] == str(state["event_id"])
        assert payload["feedback_type"] == "direction_off"

        target_event = asyncio.run(load_target_event())
        assert target_event.payload["feedback_status"] == "direction_off"
        assert target_event.payload["feedback_label"] == "方向不对"
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
