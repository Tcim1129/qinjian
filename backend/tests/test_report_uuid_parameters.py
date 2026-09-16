from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import reports as reports_api
from app.core.database import Base
from app.core.time import current_local_date
from app.models import Checkin, Pair, PairStatus, PairType, User


def _new_report_test_db(name: str):
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"{name}-{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    return db_path, engine, sessionmaker


def test_generate_daily_route_converts_query_pair_id_to_uuid(monkeypatch):
    db_path, engine, sessionmaker = _new_report_test_db("report-pair-uuid")
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="report-pair-a@example.com",
                nickname="Report A",
                password_hash="not-used",
            )
            user_b = User(
                email="report-pair-b@example.com",
                nickname="Report B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="HJKMNPQRST",
            )
            db.add(pair)
            await db.flush()

            db.add_all(
                [
                    Checkin(
                        pair_id=pair.id,
                        user_id=user_a.id,
                        content="Report route UUID check A.",
                        checkin_date=current_local_date(),
                    ),
                    Checkin(
                        pair_id=pair.id,
                        user_id=user_b.id,
                        content="Report route UUID check B.",
                        checkin_date=current_local_date(),
                    ),
                ]
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

    async def noop_process_daily_report(*_args, **_kwargs):
        return None

    monkeypatch.setattr(reports_api, "_process_daily_report", noop_process_daily_report)

    app = FastAPI()
    app.include_router(reports_api.router)
    app.dependency_overrides[reports_api.get_db] = override_get_db
    app.dependency_overrides[reports_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/reports/generate-daily?pair_id={state['pair_id']}"
            )

        assert response.status_code == 200, response.text
        assert response.json()["type"] == "daily"
        assert response.json()["status"] == "pending"
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_relaxed_test_account_can_generate_pair_daily_without_both_checkins(monkeypatch):
    db_path, engine, sessionmaker = _new_report_test_db("report-pair-relaxed")
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="relaxed-daily-a@example.com",
                nickname="Relaxed Daily A",
                password_hash="not-used",
            )
            user_b = User(
                email="relaxed-daily-b@example.com",
                nickname="Relaxed Daily B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="DAILYTST01",
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

    async def noop_process_daily_report(*_args, **_kwargs):
        return None

    monkeypatch.setattr(reports_api, "_process_daily_report", noop_process_daily_report)
    monkeypatch.setattr(
        reports_api, "is_relaxed_test_account", lambda _user: True, raising=False
    )

    app = FastAPI()
    app.include_router(reports_api.router)
    app.dependency_overrides[reports_api.get_db] = override_get_db
    app.dependency_overrides[reports_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/reports/generate-daily?pair_id={state['pair_id']}"
            )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["type"] == "daily"
        assert payload["status"] == "pending"
        assert payload["pair_id"] == str(state["pair_id"])
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_relaxed_test_account_can_generate_solo_daily_without_checkin(monkeypatch):
    db_path, engine, sessionmaker = _new_report_test_db("report-solo-relaxed")
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user = User(
                email="relaxed-report@example.com",
                nickname="Relaxed Report",
                password_hash="not-used",
            )
            db.add(user)
            await db.commit()
            state["user_id"] = user.id

    asyncio.run(setup_database())

    async def override_get_db():
        async with sessionmaker() as db:
            yield db

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, state["user_id"])

    async def noop_process_daily_report(*_args, **_kwargs):
        return None

    monkeypatch.setattr(reports_api, "_process_daily_report", noop_process_daily_report)
    monkeypatch.setattr(
        reports_api, "is_relaxed_test_account", lambda _user: True, raising=False
    )

    app = FastAPI()
    app.include_router(reports_api.router)
    app.dependency_overrides[reports_api.get_db] = override_get_db
    app.dependency_overrides[reports_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/reports/generate-daily?mode=solo")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["type"] == "solo"
        assert payload["status"] == "pending"
        assert payload["user_id"] == str(state["user_id"])
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_relaxed_test_account_can_generate_weekly_without_three_daily_reports(monkeypatch):
    db_path, engine, sessionmaker = _new_report_test_db("report-weekly-relaxed")
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="relaxed-weekly-a@example.com",
                nickname="Relaxed Weekly A",
                password_hash="not-used",
            )
            user_b = User(
                email="relaxed-weekly-b@example.com",
                nickname="Relaxed Weekly B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="WEEKLYTST1",
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

    async def noop_process_weekly_report(*_args, **_kwargs):
        return None

    monkeypatch.setattr(reports_api, "_process_weekly_report", noop_process_weekly_report)
    monkeypatch.setattr(
        reports_api, "is_relaxed_test_account", lambda _user: True, raising=False
    )

    app = FastAPI()
    app.include_router(reports_api.router)
    app.dependency_overrides[reports_api.get_db] = override_get_db
    app.dependency_overrides[reports_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/reports/generate-weekly?pair_id={state['pair_id']}"
            )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["type"] == "weekly"
        assert payload["status"] == "pending"
        assert payload["pair_id"] == str(state["pair_id"])
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_relaxed_test_account_can_generate_monthly_without_two_weekly_reports(monkeypatch):
    db_path, engine, sessionmaker = _new_report_test_db("report-monthly-relaxed")
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="relaxed-monthly-a@example.com",
                nickname="Relaxed Monthly A",
                password_hash="not-used",
            )
            user_b = User(
                email="relaxed-monthly-b@example.com",
                nickname="Relaxed Monthly B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="MONTHLYT1",
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

    async def noop_process_monthly_report(*_args, **_kwargs):
        return None

    monkeypatch.setattr(reports_api, "_process_monthly_report", noop_process_monthly_report)
    monkeypatch.setattr(
        reports_api, "is_relaxed_test_account", lambda _user: True, raising=False
    )

    app = FastAPI()
    app.include_router(reports_api.router)
    app.dependency_overrides[reports_api.get_db] = override_get_db
    app.dependency_overrides[reports_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/reports/generate-monthly?pair_id={state['pair_id']}"
            )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["type"] == "monthly"
        assert payload["status"] == "pending"
        assert payload["pair_id"] == str(state["pair_id"])
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
