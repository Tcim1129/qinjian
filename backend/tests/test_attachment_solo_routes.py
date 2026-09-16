from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import tasks as tasks_api
from app.core.database import Base
from app.core.time import current_local_date
from app.models import Checkin, Pair, PairStatus, PairType, RelationshipProfileSnapshot, User
from app.services.request_cooldown_store import close_request_cooldown_store


def _db_path_for(test_name: str) -> Path:
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    return db_dir / f"{test_name}-{uuid.uuid4().hex}.db"


def test_solo_attachment_routes_support_real_single_mode(monkeypatch):
    asyncio.run(close_request_cooldown_store())
    db_path = _db_path_for("attachment-solo")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user = User(
                email="attachment-solo@example.com",
                nickname="Attachment Solo",
                password_hash="not-used",
            )
            db.add(user)
            await db.flush()

            for index in range(5):
                db.add(
                    Checkin(
                        user_id=user.id,
                        pair_id=None,
                        content=f"Solo attachment note {index}",
                        mood_score=4 + index,
                        interaction_freq=6,
                        interaction_initiative="me" if index % 2 == 0 else "equal",
                        deep_conversation=index % 2 == 0,
                        checkin_date=current_local_date(),
                    )
                )

            await db.commit()
            state["user_id"] = user.id

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

    async def fake_analyze_attachment_style(**_kwargs):
        return {
            "primary_type": "anxious",
            "confidence": 0.82,
            "analysis": "更容易担心关系失去回应。",
            "growth_suggestion": "先把担心说成需求。",
        }

    monkeypatch.setattr(
        tasks_api,
        "analyze_attachment_style",
        fake_analyze_attachment_style,
    )

    app = FastAPI()
    app.include_router(tasks_api.router)
    app.dependency_overrides[tasks_api.get_db] = override_get_db
    app.dependency_overrides[tasks_api.get_current_user] = override_current_user

    async def read_snapshot_summary():
        async with sessionmaker() as db:
            result = await db.execute(
                select(RelationshipProfileSnapshot)
                .where(
                    RelationshipProfileSnapshot.user_id == state["user_id"],
                    RelationshipProfileSnapshot.pair_id.is_(None),
                )
                .order_by(RelationshipProfileSnapshot.created_at.desc())
                .limit(1)
            )
            snapshot = result.scalar_one()
            return snapshot.attachment_summary

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            post_response = client.post("/tasks/attachment/analyze", params={"mode": "solo"})
            get_response = client.get("/tasks/attachment", params={"mode": "solo"})

        assert post_response.status_code == 200, post_response.text
        post_payload = post_response.json()
        assert post_payload["scope"] == "solo"
        assert post_payload["my_attachment"]["type"] == "anxious"
        assert post_payload["my_attachment"]["label"] == "焦虑型"
        assert post_payload["my_attachment"]["confidence"] == 0.82

        assert get_response.status_code == 200, get_response.text
        get_payload = get_response.json()
        assert get_payload["my_attachment"]["type"] == "anxious"
        assert get_payload["partner_attachment"] is None

        summary = asyncio.run(read_snapshot_summary())
        assert summary["attachment_a"] == "anxious"
        assert summary["growth_suggestion"] == "先把担心说成需求。"
    finally:
        asyncio.run(close_request_cooldown_store())
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_solo_attachment_analysis_rate_limits_repeated_runs(monkeypatch):
    asyncio.run(close_request_cooldown_store())
    db_path = _db_path_for("attachment-solo-rate-limit")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user = User(
                email="attachment-solo-limit@example.com",
                nickname="Attachment Solo Limit",
                password_hash="not-used",
            )
            db.add(user)
            await db.flush()

            for index in range(5):
                db.add(
                    Checkin(
                        user_id=user.id,
                        pair_id=None,
                        content=f"Solo attachment limit note {index}",
                        mood_score=4 + index,
                        interaction_freq=6,
                        interaction_initiative="me" if index % 2 == 0 else "equal",
                        deep_conversation=index % 2 == 0,
                        checkin_date=current_local_date(),
                    )
                )

            await db.commit()
            state["user_id"] = user.id

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

    async def fake_analyze_attachment_style(**_kwargs):
        return {
            "primary_type": "secure",
            "confidence": 0.91,
            "analysis": "整体比较稳定。",
            "growth_suggestion": "保持现在的表达方式。",
        }

    monkeypatch.setattr(
        tasks_api,
        "analyze_attachment_style",
        fake_analyze_attachment_style,
    )

    app = FastAPI()
    app.include_router(tasks_api.router)
    app.dependency_overrides[tasks_api.get_db] = override_get_db
    app.dependency_overrides[tasks_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            responses = [
                client.post("/tasks/attachment/analyze", params={"mode": "solo"})
                for _ in range(3)
            ]

        assert [response.status_code for response in responses[:2]] == [200, 200]
        assert responses[2].status_code == 429, responses[2].text
        assert "秒后再试" in responses[2].json()["detail"]
    finally:
        asyncio.run(close_request_cooldown_store())
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_relaxed_test_account_can_analyze_solo_attachment_without_five_checkins(
    monkeypatch,
):
    asyncio.run(close_request_cooldown_store())
    db_path = _db_path_for("attachment-solo-relaxed")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user = User(
                email="relaxed-attachment-solo@example.com",
                nickname="Relaxed Attachment Solo",
                password_hash="not-used",
            )
            db.add(user)
            await db.commit()
            state["user_id"] = user.id

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

    async def fake_analyze_attachment_style(**kwargs):
        assert kwargs["mood_scores"] == []
        assert kwargs["content_summary"]
        return {
            "primary_type": "secure",
            "confidence": 0.5,
            "analysis": "测试账号可在样本不足时先生成参考分析。",
            "growth_suggestion": "继续补充记录。",
        }

    monkeypatch.setattr(tasks_api, "is_relaxed_test_account", lambda _user: True)
    monkeypatch.setattr(
        tasks_api,
        "analyze_attachment_style",
        fake_analyze_attachment_style,
    )

    app = FastAPI()
    app.include_router(tasks_api.router)
    app.dependency_overrides[tasks_api.get_db] = override_get_db
    app.dependency_overrides[tasks_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/tasks/attachment/analyze", params={"mode": "solo"})

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["scope"] == "solo"
        assert payload["my_attachment"]["type"] == "secure"
        assert payload["my_attachment"]["analysis"] == "测试账号可在样本不足时先生成参考分析。"
    finally:
        asyncio.run(close_request_cooldown_store())
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_relaxed_test_account_can_analyze_pair_attachment_without_five_each(
    monkeypatch,
):
    asyncio.run(close_request_cooldown_store())
    db_path = _db_path_for("attachment-pair-relaxed")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="relaxed-attachment-a@example.com",
                nickname="Relaxed Attachment A",
                password_hash="not-used",
            )
            user_b = User(
                email="relaxed-attachment-b@example.com",
                nickname="Relaxed Attachment B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="RELAXATT1",
            )
            db.add(pair)
            await db.flush()

            db.add(
                Checkin(
                    pair_id=pair.id,
                    user_id=user_a.id,
                    content="只有一条记录，也要允许测试号跑依恋分析。",
                    mood_score=6,
                    interaction_freq=5,
                    interaction_initiative="me",
                    deep_conversation=True,
                    checkin_date=current_local_date(),
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

    calls = {"count": 0}

    async def fake_analyze_attachment_style(**_kwargs):
        calls["count"] += 1
        return {
            "primary_type": "secure",
            "confidence": 0.51,
            "analysis": "测试账号可跳过双方各五条记录门槛。",
            "growth_suggestion": "继续补充双方样本。",
        }

    monkeypatch.setattr(tasks_api, "is_relaxed_test_account", lambda _user: True)
    monkeypatch.setattr(
        tasks_api,
        "analyze_attachment_style",
        fake_analyze_attachment_style,
    )

    app = FastAPI()
    app.include_router(tasks_api.router)
    app.dependency_overrides[tasks_api.get_db] = override_get_db
    app.dependency_overrides[tasks_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(f"/tasks/attachment/{state['pair_id']}/analyze")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["scope"] == "pair"
        assert payload["attachment_a"]["type"] == "secure"
        assert payload["attachment_b"]["type"] == "secure"
        assert calls["count"] == 2
    finally:
        asyncio.run(close_request_cooldown_store())
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
