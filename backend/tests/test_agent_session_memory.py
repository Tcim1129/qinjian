from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import agent as agent_api
from app.core.database import Base
from app.core.time import current_local_date
from app.models import AgentChatMessage, AgentChatSession, User
from app.services.ai_context import build_context_pack


def _test_db_path(prefix: str) -> Path:
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    return db_dir / f"{prefix}-{uuid.uuid4().hex}.db"


async def _create_schema(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _seed_user_and_session(
    sessionmaker,
    *,
    email_prefix: str,
    status: str = "active",
    expires_at: datetime | None = None,
    summary_json: dict | None = None,
    summary_updated_at: datetime | None = None,
) -> dict[str, object]:
    async with sessionmaker() as db:
        user = User(
            email=f"{email_prefix}@example.com",
            nickname=email_prefix,
            password_hash="not-used",
        )
        db.add(user)
        await db.flush()

        session = AgentChatSession(
            user_id=user.id,
            pair_id=None,
            session_date=current_local_date(),
            status=status,
            expires_at=expires_at,
            summary_json=summary_json,
            summary_updated_at=summary_updated_at,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        return {
            "user_id": user.id,
            "session_id": session.id,
            "expires_at": expires_at,
            "summary_json": summary_json,
            "summary_updated_at": summary_updated_at,
        }


async def _list_sessions(sessionmaker, user_id) -> list[AgentChatSession]:
    async with sessionmaker() as db:
        result = await db.execute(
            select(AgentChatSession)
            .where(AgentChatSession.user_id == user_id)
            .order_by(AgentChatSession.created_at.asc())
        )
        return list(result.scalars().all())


async def _build_context_pack_for_session(
    sessionmaker,
    *,
    user_id,
    session_id,
):
    async with sessionmaker() as db:
        user = await db.get(User, user_id)
        return await build_context_pack(
            db,
            user=user,
            user_id=str(user_id),
            session_id=str(session_id),
        )


def _make_agent_client(monkeypatch, sessionmaker, user_id) -> TestClient:
    async def override_get_db():
        async with sessionmaker() as db:
            yield db

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, user_id)

    async def noop_record_event(*_args, **_kwargs):
        return None

    monkeypatch.setattr(agent_api, "record_user_interaction_event", noop_record_event)

    app = FastAPI()
    app.include_router(agent_api.router)
    app.dependency_overrides[agent_api.get_db] = override_get_db
    app.dependency_overrides[agent_api.get_current_user] = override_current_user
    return TestClient(app, raise_server_exceptions=False)


def test_post_agent_sessions_reuses_still_active_session_in_same_scope(monkeypatch):
    db_path = _test_db_path("agent-session-memory-reuse")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    active_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=20)

    try:
        asyncio.run(_create_schema(engine))
        state = asyncio.run(
            _seed_user_and_session(
                sessionmaker,
                email_prefix="agent-session-memory-reuse",
                expires_at=active_until,
            )
        )

        with _make_agent_client(monkeypatch, sessionmaker, state["user_id"]) as client:
            response = client.post("/agent/sessions")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["session_id"] == str(state["session_id"])
        assert payload["reused"] is True

        sessions = asyncio.run(_list_sessions(sessionmaker, state["user_id"]))
        assert len(sessions) == 1
        assert str(sessions[0].id) == str(state["session_id"])
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_post_agent_sessions_force_new_creates_new_session(monkeypatch):
    db_path = _test_db_path("agent-session-memory-force-new")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    active_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=20)

    try:
        asyncio.run(_create_schema(engine))
        state = asyncio.run(
            _seed_user_and_session(
                sessionmaker,
                email_prefix="agent-session-memory-force-new",
                expires_at=active_until,
            )
        )

        with _make_agent_client(monkeypatch, sessionmaker, state["user_id"]) as client:
            response = client.post("/agent/sessions?force_new=true")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["session_id"] != str(state["session_id"])
        assert payload["reused"] is False

        sessions = asyncio.run(_list_sessions(sessionmaker, state["user_id"]))
        assert len(sessions) == 2
        assert {str(session.id) for session in sessions} == {
            str(state["session_id"]),
            payload["session_id"],
        }
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_get_agent_sessions_lists_real_topics_and_latest_messages(monkeypatch):
    db_path = _test_db_path("agent-session-memory-list")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def seed():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with sessionmaker() as db:
            user = User(email="agent-session-list@example.com", nickname="会话用户", password_hash="not-used")
            db.add(user)
            await db.flush()
            first = AgentChatSession(
                user_id=user.id,
                pair_id=None,
                session_date=current_local_date(),
                status="active",
                summary_json={"topic": "关于周末计划的沟通"},
            )
            second = AgentChatSession(
                user_id=user.id,
                pair_id=None,
                session_date=current_local_date(),
                status="archived",
            )
            db.add_all([first, second])
            await db.flush()
            db.add_all([
                AgentChatMessage(session_id=first.id, role="user", content="我担心周末安排又变了。"),
                AgentChatMessage(session_id=first.id, role="assistant", content="先说清楚你最在意的部分。"),
                AgentChatMessage(session_id=second.id, role="user", content="我想梳理一下最近的情绪。"),
            ])
            await db.commit()
            return {"user_id": user.id, "first_id": first.id, "second_id": second.id}

    try:
        state = asyncio.run(seed())
        with _make_agent_client(monkeypatch, sessionmaker, state["user_id"]) as client:
            response = client.get("/agent/sessions?limit=10")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert {item["session_id"] for item in payload} == {str(state["first_id"]), str(state["second_id"])}
        summarized = next(item for item in payload if item["session_id"] == str(state["first_id"]))
        assert summarized["topic"] == "关于周末计划的沟通"
        assert summarized["last_message"] == "先说清楚你最在意的部分。"
        derived = next(item for item in payload if item["session_id"] == str(state["second_id"]))
        assert derived["topic"] == "我想梳理一下最近的情绪。"
        assert derived["message_count"] == 1
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_build_context_pack_exposes_current_session_summary_metadata():
    db_path = _test_db_path("agent-session-memory-context")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    summary_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session_summary = {
        "headline": "The user already explained the conflict about delayed replies.",
        "next_step": "Keep the response grounded and avoid asking them to repeat details.",
        "open_questions": ["What happened right before the silence started?"],
    }

    try:
        asyncio.run(_create_schema(engine))
        state = asyncio.run(
            _seed_user_and_session(
                sessionmaker,
                email_prefix="agent-session-memory-context",
                summary_json=session_summary,
                summary_updated_at=summary_updated_at,
            )
        )

        context_pack = asyncio.run(
            _build_context_pack_for_session(
                sessionmaker,
                user_id=state["user_id"],
                session_id=state["session_id"],
            )
        )

        current_session = context_pack["current_session"]
        assert current_session["session_id"] == str(state["session_id"])
        assert current_session["status"] == "active"
        assert current_session["summary"] == session_summary
        assert current_session["summary_updated_at"] == summary_updated_at.isoformat()
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
