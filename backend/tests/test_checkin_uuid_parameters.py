from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import checkins as checkins_api
from app.core import database as database_core
from app.core.database import Base
from app.core.time import current_local_date
from app.models import Checkin, Pair, PairStatus, PairType, Report, ReportStatus, ReportType, User


def _db_path_for(test_name: str) -> Path:
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    return db_dir / f"{test_name}-{uuid.uuid4().hex}.db"


def test_pair_today_route_converts_query_pair_id_to_uuid():
    db_path = _db_path_for("pair-today-uuid")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="pair-today-a@example.com",
                nickname="Pair A",
                password_hash="not-used",
            )
            user_b = User(
                email="pair-today-b@example.com",
                nickname="Pair B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="ABCDEFGHJK",
            )
            db.add(pair)
            await db.flush()

            checkin = Checkin(
                pair_id=pair.id,
                user_id=user_a.id,
                content="Pair route UUID check.",
                checkin_date=current_local_date(),
            )
            db.add(checkin)
            db.add(
                Report(
                    pair_id=pair.id,
                    user_id=user_a.id,
                    type=ReportType.SOLO,
                    status=ReportStatus.PENDING,
                    report_date=current_local_date(),
                )
            )
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
    app.include_router(checkins_api.router)
    app.dependency_overrides[checkins_api.get_db] = override_get_db
    app.dependency_overrides[checkins_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(f"/checkins/today?pair_id={state['pair_id']}")

        assert response.status_code == 200, response.text
        assert response.json()["my_done"] is True
        assert response.json()["partner_done"] is False
        assert response.json()["has_solo_report"] is True
        assert response.json()["solo_report_status"] == "pending"
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_sentiment_background_task_accepts_string_checkin_id(monkeypatch):
    db_path = _db_path_for("sentiment-checkin-uuid")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user = User(
                email="sentiment-checkin@example.com",
                nickname="Sentiment",
                password_hash="not-used",
            )
            db.add(user)
            await db.flush()

            checkin = Checkin(
                user_id=user.id,
                content="Background UUID check.",
                checkin_date=current_local_date(),
            )
            db.add(checkin)
            await db.commit()
            state["checkin_id"] = checkin.id

    asyncio.run(setup_database())

    async def fake_analyze_sentiment(_content: str):
        return {"score": 8.5}

    monkeypatch.setattr(checkins_api, "analyze_sentiment", fake_analyze_sentiment)
    original_async_session = database_core.async_session
    database_core.async_session = sessionmaker

    async def run_task_and_read_score():
        await checkins_api._run_sentiment_analysis(
            str(state["checkin_id"]),
            "Background UUID check.",
        )
        async with sessionmaker() as db:
            result = await db.execute(
                select(Checkin.sentiment_score).where(
                    Checkin.id == state["checkin_id"]
                )
            )
            return result.scalar_one()

    try:
        score = asyncio.run(run_task_and_read_score())
        assert score == 8.5
    finally:
        database_core.async_session = original_async_session
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
