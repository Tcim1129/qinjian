from __future__ import annotations

import asyncio
import uuid
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import agent as agent_api
from app.core.database import Base
from app.core.time import current_local_date
from app.models import AgentChatSession, Pair, PairStatus, PairType, UploadAsset, User


def test_agent_chat_route_converts_url_session_id_to_uuid(monkeypatch):
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"agent-session-uuid-{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user = User(
                email="agent-session-uuid@example.com",
                nickname="Agent UUID",
                password_hash="not-used",
            )
            db.add(user)
            await db.flush()

            chat_session = AgentChatSession(
                user_id=user.id,
                pair_id=None,
                session_date=current_local_date(),
                status="active",
            )
            db.add(chat_session)
            await db.commit()
            state["user_id"] = user.id
            state["session_id"] = chat_session.id

    asyncio.run(setup_database())

    async def override_get_db():
        async with sessionmaker() as db:
            yield db

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, state["user_id"])

    async def fake_chat_completion(**_kwargs):
        message = SimpleNamespace(
            content="I hear the concern, and we can take it one steady step at a time.",
            tool_calls=None,
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    async def noop_record_event(*_args, **_kwargs):
        return None

    @contextmanager
    def noop_privacy_scope(**_kwargs):
        yield

    import app.ai.agent_loop as agent_loop_module
    monkeypatch.setattr(agent_loop_module, "create_chat_completion", fake_chat_completion)
    monkeypatch.setattr(agent_api, "record_user_interaction_event", noop_record_event)
    monkeypatch.setattr(agent_api, "privacy_audit_scope", noop_privacy_scope)

    app = FastAPI()
    app.include_router(agent_api.router)
    app.dependency_overrides[agent_api.get_db] = override_get_db
    app.dependency_overrides[agent_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/agent/sessions/{state['session_id']}/chat",
                json={"content": "Please respond gently."},
            )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["reply"] == "I hear the concern, and we can take it one steady step at a time."
        assert body["action"] == "chat"
        # trace 是 Agent 推理痕迹数组（即使是纯文本回复也会记录一步思考）
        assert isinstance(body["trace"], list)
        assert body["trace"][0]["thought"] == "I hear the concern, and we can take it one steady step at a time."
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_agent_chat_returns_error_without_preset_reply_when_ai_call_fails(monkeypatch):
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"agent-chat-fallback-{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user = User(
                email="agent-chat-fallback@example.com",
                nickname="Agent Fallback",
                password_hash="not-used",
            )
            db.add(user)
            await db.flush()

            chat_session = AgentChatSession(
                user_id=user.id,
                pair_id=None,
                session_date=current_local_date(),
                status="active",
            )
            db.add(chat_session)
            await db.commit()
            state["user_id"] = user.id
            state["session_id"] = chat_session.id

    asyncio.run(setup_database())

    async def override_get_db():
        async with sessionmaker() as db:
            yield db

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, state["user_id"])

    async def failing_chat_completion(**_kwargs):
        raise RuntimeError("upstream unavailable")

    async def noop_record_event(*_args, **_kwargs):
        return None

    @contextmanager
    def noop_privacy_scope(**_kwargs):
        yield

    import app.ai.agent_loop as agent_loop_module
    monkeypatch.setattr(agent_loop_module, "create_chat_completion", failing_chat_completion)
    monkeypatch.setattr(agent_api, "record_user_interaction_event", noop_record_event)
    monkeypatch.setattr(agent_api, "privacy_audit_scope", noop_privacy_scope)

    app = FastAPI()
    app.include_router(agent_api.router)
    app.dependency_overrides[agent_api.get_db] = override_get_db
    app.dependency_overrides[agent_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/agent/sessions/{state['session_id']}/chat",
                json={"content": "Please respond gently."},
            )

        assert response.status_code == 502, response.text
        assert 'reply' not in response.json()
        assert '重试' in response.json()['detail']
        async def assert_no_assistant_reply():
            from sqlalchemy import select
            from app.models import AgentChatMessage
            async with sessionmaker() as db:
                result = await db.execute(select(AgentChatMessage).where(AgentChatMessage.session_id == state['session_id'], AgentChatMessage.role == 'assistant'))
                assert result.scalars().all() == []
        asyncio.run(assert_no_assistant_reply())
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_pair_agent_session_route_converts_query_pair_id_to_uuid(monkeypatch):
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"agent-pair-session-uuid-{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="agent-pair-session-a@example.com",
                nickname="Agent Pair A",
                password_hash="not-used",
            )
            user_b = User(
                email="agent-pair-session-b@example.com",
                nickname="Agent Pair B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="AGENTUUID1",
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

    async def noop_record_event(*_args, **_kwargs):
        return None

    monkeypatch.setattr(agent_api, "record_user_interaction_event", noop_record_event)

    app = FastAPI()
    app.include_router(agent_api.router)
    app.dependency_overrides[agent_api.get_db] = override_get_db
    app.dependency_overrides[agent_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(f"/agent/sessions?pair_id={state['pair_id']}")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["session_id"]
        assert payload["has_extracted_checkin"] is False
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_agent_chat_surface_chat_persists_voice_evidence(monkeypatch):
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"agent-chat-voice-evidence-{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}
    seen = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user = User(
                email="agent-chat-voice-evidence@example.com",
                nickname="Agent Voice",
                password_hash="not-used",
            )
            db.add(user)
            await db.flush()
            db.add(
                UploadAsset(
                    storage_path="/uploads/voices/example.webm",
                    subdir="voices",
                    filename="example.webm",
                    owner_user_id=user.id,
                    scope="user",
                )
            )

            chat_session = AgentChatSession(
                user_id=user.id,
                pair_id=None,
                session_date=current_local_date(),
                status="active",
            )
            db.add(chat_session)
            await db.commit()
            state["user_id"] = user.id
            state["session_id"] = chat_session.id

    asyncio.run(setup_database())

    async def override_get_db():
        async with sessionmaker() as db:
            yield db

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, state["user_id"])

    async def fake_chat_completion(**kwargs):
        seen["tools"] = kwargs.get("tools")
        seen["tool_choice"] = kwargs.get("tool_choice")
        message = SimpleNamespace(
            content="我听见你这句里有委屈，我们先把它放稳。",
            tool_calls=None,
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    async def noop_record_event(*_args, **_kwargs):
        return None

    @contextmanager
    def noop_privacy_scope(**_kwargs):
        yield

    import app.ai.agent_loop as agent_loop_module
    monkeypatch.setattr(agent_loop_module, "create_chat_completion", fake_chat_completion)
    monkeypatch.setattr(agent_api, "record_user_interaction_event", noop_record_event)
    monkeypatch.setattr(agent_api, "privacy_audit_scope", noop_privacy_scope)

    app = FastAPI()
    app.include_router(agent_api.router)
    app.dependency_overrides[agent_api.get_db] = override_get_db
    app.dependency_overrides[agent_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/agent/sessions/{state['session_id']}/chat",
                json={
                    "content": "",
                    "surface": "chat",
                    "voice_evidence": {
                        "voice_url": "/uploads/voices/example.webm",
                        "transcript_text": "今天其实有点委屈。",
                        "duration_seconds": 4.2,
                        "source": "realtime",
                        "voice_emotion": {"code": "sad", "label": "难过"},
                        "content_emotion": {"sentiment": "negative", "mood_label": "委屈"},
                        "transcript_language": {"code": "zh", "label": "中文"},
                    },
                },
            )

            history = client.get(f"/agent/sessions/{state['session_id']}/messages")

        assert response.status_code == 200, response.text
        assert response.json()["action"] == "chat"
        # ReAct 循环在首轮会传入工具 schema（若非最后一步），因此 tools 应为非空 schema 列表。
        assert isinstance(seen["tools"], list) and len(seen["tools"]) > 0
        assert seen["tool_choice"] == "auto"

        assert history.status_code == 200, history.text
        payload = history.json()
        assert payload[0]["content"] == "今天其实有点委屈。"
        assert payload[0]["payload"]["surface"] == "chat"
        voice_evidence = payload[0]["payload"]["voice_evidence"]
        assert voice_evidence["transcript_text"] == "今天其实有点委屈。"
        assert voice_evidence["source"] == "realtime"
        assert "/api/v1/upload/access/voices/example.webm" in voice_evidence["voice_url"]
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_agent_chat_rejects_voice_evidence_owned_by_another_user(monkeypatch):
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"agent-chat-voice-owner-{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user = User(
                email="agent-chat-voice-owner@example.com",
                nickname="Agent Voice Owner",
                password_hash="not-used",
            )
            other = User(
                email="agent-chat-voice-other@example.com",
                nickname="Agent Voice Other",
                password_hash="not-used",
            )
            db.add_all([user, other])
            await db.flush()
            db.add(
                UploadAsset(
                    storage_path="/uploads/voices/other.webm",
                    subdir="voices",
                    filename="other.webm",
                    owner_user_id=other.id,
                    scope="user",
                )
            )

            chat_session = AgentChatSession(
                user_id=user.id,
                pair_id=None,
                session_date=current_local_date(),
                status="active",
            )
            db.add(chat_session)
            await db.commit()
            state["user_id"] = user.id
            state["session_id"] = chat_session.id

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

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/agent/sessions/{state['session_id']}/chat",
                json={
                    "content": "",
                    "surface": "chat",
                    "voice_evidence": {
                        "voice_url": "/uploads/voices/other.webm",
                        "transcript_text": "今天其实有点委屈。",
                        "source": "upload",
                    },
                },
            )

        assert response.status_code == 403, response.text
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_agent_chat_rejects_empty_content_without_voice_transcript(monkeypatch):
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"agent-chat-validation-{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user = User(
                email="agent-chat-validation@example.com",
                nickname="Agent Validation",
                password_hash="not-used",
            )
            db.add(user)
            await db.flush()

            chat_session = AgentChatSession(
                user_id=user.id,
                pair_id=None,
                session_date=current_local_date(),
                status="active",
            )
            db.add(chat_session)
            await db.commit()
            state["user_id"] = user.id
            state["session_id"] = chat_session.id

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

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/agent/sessions/{state['session_id']}/chat",
                json={
                    "content": "",
                    "surface": "chat",
                    "voice_evidence": {
                        "source": "upload",
                    },
                },
            )

        assert response.status_code == 422, response.text
        assert "文字内容和语音转写至少填写一项" in response.text
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
