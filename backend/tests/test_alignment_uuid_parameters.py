from __future__ import annotations

import asyncio
import uuid
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.insights_routes import alignment as alignment_api
from app.core.database import Base
from app.core.time import current_local_date
from app.models import Checkin, Pair, PairStatus, PairType, RelationshipEvent, User
from app.services.request_cooldown_store import close_request_cooldown_store


def _db_path_for(test_name: str) -> Path:
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    return db_dir / f"{test_name}-{uuid.uuid4().hex}.db"


def test_alignment_generate_route_converts_query_pair_id_to_uuid_and_caches_result(
    monkeypatch,
):
    asyncio.run(close_request_cooldown_store())
    db_path = _db_path_for("alignment-uuid")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}
    calls = {"generate": 0}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="alignment-a@example.com",
                nickname="Alignment A",
                password_hash="not-used",
            )
            user_b = User(
                email="alignment-b@example.com",
                nickname="Alignment B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="ALIGNUUID1",
            )
            db.add(pair)
            await db.flush()

            today = current_local_date()
            db.add_all(
                [
                    Checkin(
                        pair_id=pair.id,
                        user_id=user_a.id,
                        content="我觉得自己没有被认真听见。",
                        mood_score=5,
                        checkin_date=today,
                    ),
                    Checkin(
                        pair_id=pair.id,
                        user_id=user_b.id,
                        content="我其实是想先冷静一下再回应。",
                        mood_score=6,
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
            yield db

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, state["user_id"])

    async def fake_generate_narrative_alignment(**_kwargs):
        calls["generate"] += 1
        return {
            "event_id": None,
            "alignment_score": 74,
            "shared_story": "双方都想把关系稳住，只是回应节奏不同。",
            "view_a_summary": "A方更在意被及时回应。",
            "view_b_summary": "B方更想先降温再解释。",
            "misread_risk": "冷静可能被听成冷淡。",
            "divergence_points": ["回应速度的期待不同"],
            "bridge_actions": ["先说明需要冷静多久"],
            "suggested_opening": "我想先确认我们各自怎么理解这件事。",
            "coach_note": "先对齐版本，再谈调整。",
            "algorithm_version": "relationship_judgement_v2",
            "confidence": 0.74,
            "decision_trace": {"layer": "alignment"},
            "focus_labels": ["回应节奏", "缓冲空间"],
            "risk_score": 0.26,
            "baseline_delta": 20,
            "fallback_reason": None,
            "shadow_result": None,
            "feedback_status": "pending_feedback",
            "source": "ai",
            "is_fallback": False,
        }

    async def fake_refresh_profile_snapshot(*_args, **_kwargs):
        return SimpleNamespace(
            behavior_summary=None,
            risk_summary={"current_level": "none", "trend": "stable"},
            attachment_summary={},
            suggested_focus={"items": []},
        )

    async def fake_refresh_profile_and_plan(*_args, **_kwargs):
        return (
            SimpleNamespace(
                risk_summary={"current_level": "none", "trend": "stable"},
            ),
            None,
        )

    @contextmanager
    def noop_privacy_scope(**_kwargs):
        yield

    monkeypatch.setattr(
        alignment_api,
        "generate_narrative_alignment",
        fake_generate_narrative_alignment,
    )
    monkeypatch.setattr(
        alignment_api,
        "refresh_profile_snapshot",
        fake_refresh_profile_snapshot,
    )
    monkeypatch.setattr(
        alignment_api,
        "refresh_profile_and_plan",
        fake_refresh_profile_and_plan,
    )
    monkeypatch.setattr(alignment_api, "privacy_audit_scope", noop_privacy_scope)

    app = FastAPI()
    app.include_router(alignment_api.router)
    app.dependency_overrides[alignment_api.get_db] = override_get_db
    app.dependency_overrides[alignment_api.get_current_user] = override_current_user

    async def count_alignment_events() -> int:
        async with sessionmaker() as db:
            result = await db.execute(
                select(func.count())
                .select_from(RelationshipEvent)
                .where(RelationshipEvent.event_type == "alignment.generated")
            )
            return int(result.scalar_one())

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            missing_response = client.get(f"/alignment/latest?pair_id={state['pair_id']}")
            generate_response = client.post(
                f"/alignment/generate?pair_id={state['pair_id']}"
            )
            cached_response = client.get(f"/alignment/latest?pair_id={state['pair_id']}")

        assert missing_response.status_code == 200, missing_response.text
        assert missing_response.json() is None

        assert generate_response.status_code == 200, generate_response.text
        payload = generate_response.json()
        assert payload["pair_id"] == str(state["pair_id"])
        assert payload["alignment_score"] == 74
        assert payload["source"] == "ai"
        assert payload["is_fallback"] is False
        assert payload["algorithm_version"] == "relationship_judgement_v2"
        assert payload["confidence"] == 0.74
        assert payload["feedback_status"] == "pending_feedback"
        assert payload["event_id"] is not None

        assert cached_response.status_code == 200, cached_response.text
        cached_payload = cached_response.json()
        assert cached_payload["shared_story"] == payload["shared_story"]
        assert cached_payload["generated_at"] == payload["generated_at"]
        assert calls["generate"] == 1
        assert asyncio.run(count_alignment_events()) == 1
    finally:
        asyncio.run(close_request_cooldown_store())
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_alignment_force_generate_rate_limits_repeated_runs(monkeypatch):
    asyncio.run(close_request_cooldown_store())
    db_path = _db_path_for("alignment-rate-limit")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="alignment-limit-a@example.com",
                nickname="Alignment Limit A",
                password_hash="not-used",
            )
            user_b = User(
                email="alignment-limit-b@example.com",
                nickname="Alignment Limit B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="ALIMIT001",
            )
            db.add(pair)
            await db.flush()

            today = current_local_date()
            db.add_all(
                [
                    Checkin(
                        pair_id=pair.id,
                        user_id=user_a.id,
                        content="我希望这次能说清楚。",
                        mood_score=5,
                        checkin_date=today,
                    ),
                    Checkin(
                        pair_id=pair.id,
                        user_id=user_b.id,
                        content="我也想把误会放下来。",
                        mood_score=6,
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
            yield db

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, state["user_id"])

    async def fake_generate_narrative_alignment(**_kwargs):
        return {
            "alignment_score": 78,
            "shared_story": "双方都想修复，只是节奏不同。",
            "view_a_summary": "A方希望尽快回应。",
            "view_b_summary": "B方希望先缓一下。",
            "misread_risk": "缓一下容易被听成不在意。",
            "divergence_points": ["回应节奏不同"],
            "bridge_actions": ["先说明多久后回来聊"],
            "suggested_opening": "我们先对齐一下各自理解。",
            "coach_note": "先确认善意，再处理细节。",
            "algorithm_version": "relationship_judgement_v2",
            "confidence": 0.78,
            "decision_trace": {},
            "focus_labels": [],
            "risk_score": 0.22,
            "baseline_delta": 12,
            "feedback_status": "pending_feedback",
            "source": "ai",
            "is_fallback": False,
        }

    async def fake_refresh_profile_snapshot(*_args, **_kwargs):
        return SimpleNamespace(
            behavior_summary=None,
            risk_summary={"current_level": "none", "trend": "stable"},
            attachment_summary={},
            suggested_focus={"items": []},
        )

    async def fake_refresh_profile_and_plan(*_args, **_kwargs):
        return (
            SimpleNamespace(risk_summary={"current_level": "none", "trend": "stable"}),
            None,
        )

    @contextmanager
    def noop_privacy_scope(**_kwargs):
        yield

    monkeypatch.setattr(alignment_api, "generate_narrative_alignment", fake_generate_narrative_alignment)
    monkeypatch.setattr(alignment_api, "refresh_profile_snapshot", fake_refresh_profile_snapshot)
    monkeypatch.setattr(alignment_api, "refresh_profile_and_plan", fake_refresh_profile_and_plan)
    monkeypatch.setattr(alignment_api, "privacy_audit_scope", noop_privacy_scope)

    app = FastAPI()
    app.include_router(alignment_api.router)
    app.dependency_overrides[alignment_api.get_db] = override_get_db
    app.dependency_overrides[alignment_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            responses = [
                client.post(f"/alignment/generate?pair_id={state['pair_id']}&force=true")
                for _ in range(3)
            ]

        assert [response.status_code for response in responses[:2]] == [200, 200]
        assert responses[2].status_code == 429, responses[2].text
        assert "秒后再试" in responses[2].json()["detail"]
    finally:
        asyncio.run(close_request_cooldown_store())
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_relaxed_test_account_can_generate_alignment_without_dual_checkins(
    monkeypatch,
):
    asyncio.run(close_request_cooldown_store())
    db_path = _db_path_for("alignment-relaxed-insufficient")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="alignment-relaxed-a@example.com",
                nickname="Relaxed A",
                password_hash="not-used",
            )
            user_b = User(
                email="alignment-relaxed-b@example.com",
                nickname="Relaxed B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="ARELAX001",
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

    async def unexpected_generate_narrative_alignment(**_kwargs):
        raise AssertionError("insufficient relaxed alignment should use placeholder")

    monkeypatch.setattr(alignment_api, "is_relaxed_test_account", lambda _user: True)
    monkeypatch.setattr(
        alignment_api,
        "generate_narrative_alignment",
        unexpected_generate_narrative_alignment,
    )

    app = FastAPI()
    app.include_router(alignment_api.router)
    app.dependency_overrides[alignment_api.get_db] = override_get_db
    app.dependency_overrides[alignment_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(f"/alignment/generate?pair_id={state['pair_id']}")

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["pair_id"] == str(state["pair_id"])
        assert payload["source"] == "fallback"
        assert payload["is_fallback"] is True
        assert "测试账号" in payload["shared_story"]
    finally:
        asyncio.run(close_request_cooldown_store())
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
