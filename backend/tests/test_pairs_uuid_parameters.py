from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import pairs as pairs_api
from app.core.database import Base
from app.models import (
    Pair,
    PairChangeRequest,
    PairChangeRequestKind,
    PairChangeRequestStatus,
    PairStatus,
    PairType,
    User,
)


def _db_path_for(test_name: str) -> Path:
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    return db_dir / f"{test_name}-{uuid.uuid4().hex}.db"


def _build_test_app(sessionmaker, state: dict) -> FastAPI:
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

    app = FastAPI()
    app.include_router(pairs_api.router)
    app.dependency_overrides[pairs_api.get_db] = override_get_db
    app.dependency_overrides[pairs_api.get_current_user] = override_current_user
    return app


def test_update_pair_type_route_converts_path_pair_id_to_uuid_and_creates_pending_request():
    db_path = _db_path_for("pair-type-update")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="pair-type-a@example.com",
                nickname="Pair A",
                password_hash="not-used",
            )
            user_b = User(
                email="pair-type-b@example.com",
                nickname="Pair B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.FRIEND,
                status=PairStatus.ACTIVE,
                invite_code="ABCDEFGHJK",
            )
            db.add(pair)
            await db.commit()

            state["user_id"] = user_a.id
            state["pair_id"] = pair.id

    asyncio.run(setup_database())
    app = _build_test_app(sessionmaker, state)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.patch(f"/pairs/{state['pair_id']}/type", json={"type": "couple"})

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["pair"]["type"] == "friend"
        assert body["pair"]["pending_change_request"]["kind"] == "type_change"
        assert body["request"]["requested_type"] == "couple"
        assert body["request"]["status"] == "pending"
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_join_request_decision_flow_requires_second_party_confirmation():
    db_path = _db_path_for("pair-join-request")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            inviter = User(
                email="inviter@example.com",
                nickname="发起方",
                password_hash="not-used",
            )
            joiner = User(
                email="joiner@example.com",
                nickname="加入方",
                password_hash="not-used",
            )
            db.add_all([inviter, joiner])
            await db.flush()

            pair = Pair(
                user_a_id=inviter.id,
                user_b_id=None,
                type=None,
                status=PairStatus.PENDING,
                invite_code="A3H7K8M9Q2",
            )
            db.add(pair)
            await db.commit()

            state["inviter_id"] = inviter.id
            state["joiner_id"] = joiner.id
            state["pair_id"] = pair.id

    asyncio.run(setup_database())

    try:
        state["user_id"] = state["joiner_id"]
        joiner_app = _build_test_app(sessionmaker, state)
        with TestClient(joiner_app, raise_server_exceptions=False) as client:
            preview = client.post("/pairs/join/preview", json={"invite_code": "a3h7k8m9q2"})
            submit = client.post("/pairs/join", json={"invite_code": "a3h7k8m9q2", "type": "spouse"})

        assert preview.status_code == 200, preview.text
        assert submit.status_code == 200, submit.text
        submit_body = submit.json()
        request_id = submit_body["request"]["id"]
        assert submit_body["pair"]["status"] == "pending"
        assert submit_body["pair"]["type"] is None
        assert submit_body["request"]["kind"] == "join_request"

        state["user_id"] = state["inviter_id"]
        inviter_app = _build_test_app(sessionmaker, state)
        with TestClient(inviter_app, raise_server_exceptions=False) as client:
            decision = client.post(
                f"/pairs/{state['pair_id']}/change-requests/{request_id}/decision",
                json={"decision": "approve"},
            )

        assert decision.status_code == 200, decision.text
        decision_body = decision.json()
        assert decision_body["pair"]["status"] == "active"
        assert decision_body["pair"]["type"] == "spouse"
        assert decision_body["request"]["status"] == "approved"

        async def verify_saved_request():
            async with sessionmaker() as db:
                request = await db.get(PairChangeRequest, uuid.UUID(request_id))
                pair = await db.get(Pair, state["pair_id"])
                assert request.kind == PairChangeRequestKind.JOIN_REQUEST
                assert pair.status == PairStatus.ACTIVE
                assert pair.type == PairType.SPOUSE

        asyncio.run(verify_saved_request())
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_refresh_pair_invite_code_updates_code_without_resetting_pending_request():
    db_path = _db_path_for("pair-refresh-invite-code")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            inviter = User(
                email="refresh-owner@example.com",
                nickname="邀请码发起方",
                password_hash="not-used",
            )
            joiner = User(
                email="refresh-joiner@example.com",
                nickname="待确认加入方",
                password_hash="not-used",
            )
            other_user = User(
                email="refresh-other@example.com",
                nickname="后续尝试加入的人",
                password_hash="not-used",
            )
            db.add_all([inviter, joiner, other_user])
            await db.flush()

            pair = Pair(
                user_a_id=inviter.id,
                user_b_id=joiner.id,
                type=None,
                status=PairStatus.PENDING,
                invite_code="A3H7K8M9Q2",
            )
            db.add(pair)
            await db.flush()

            change_request = PairChangeRequest(
                pair_id=pair.id,
                kind=PairChangeRequestKind.JOIN_REQUEST,
                status=PairChangeRequestStatus.PENDING,
                requested_type=PairType.FRIEND,
                requester_user_id=joiner.id,
                approver_user_id=inviter.id,
            )
            db.add(change_request)
            await db.commit()

            state["pair_id"] = pair.id
            state["owner_id"] = inviter.id
            state["joiner_id"] = joiner.id
            state["other_user_id"] = other_user.id
            state["old_code"] = pair.invite_code
            state["request_id"] = change_request.id

    asyncio.run(setup_database())

    try:
        state["user_id"] = state["owner_id"]
        owner_app = _build_test_app(sessionmaker, state)
        with TestClient(owner_app, raise_server_exceptions=False) as client:
            refresh = client.post(f"/pairs/{state['pair_id']}/invite-code/refresh")

        assert refresh.status_code == 200, refresh.text
        body = refresh.json()
        new_code = body["invite_code"]
        assert new_code != state["old_code"]
        assert body["status"] == "pending"
        assert body["type"] is None
        assert body["pending_change_request"]["id"] == str(state["request_id"])
        assert body["pending_change_request"]["status"] == "pending"

        state["user_id"] = state["other_user_id"]
        other_user_app = _build_test_app(sessionmaker, state)
        with TestClient(other_user_app, raise_server_exceptions=False) as client:
            old_preview = client.post("/pairs/join/preview", json={"invite_code": state["old_code"]})
            new_preview = client.post("/pairs/join/preview", json={"invite_code": new_code})

        assert old_preview.status_code == 404, old_preview.text
        assert new_preview.status_code == 409, new_preview.text

        async def verify_saved_state():
            async with sessionmaker() as db:
                pair = await db.get(Pair, state["pair_id"])
                request = await db.get(PairChangeRequest, state["request_id"])
                assert pair.invite_code == new_code
                assert pair.user_b_id == state["joiner_id"]
                assert pair.status == PairStatus.PENDING
                assert pair.type is None
                assert request.status == PairChangeRequestStatus.PENDING
                assert request.kind == PairChangeRequestKind.JOIN_REQUEST

        asyncio.run(verify_saved_state())
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_refresh_pair_invite_code_rejects_non_owner():
    db_path = _db_path_for("pair-refresh-invite-code-non-owner")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            owner = User(
                email="refresh-owner-only@example.com",
                nickname="发起方",
                password_hash="not-used",
            )
            viewer = User(
                email="refresh-viewer@example.com",
                nickname="查看者",
                password_hash="not-used",
            )
            db.add_all([owner, viewer])
            await db.flush()

            pair = Pair(
                user_a_id=owner.id,
                user_b_id=None,
                type=None,
                status=PairStatus.PENDING,
                invite_code="B4J8L9N2P3",
            )
            db.add(pair)
            await db.commit()

            state["pair_id"] = pair.id
            state["user_id"] = viewer.id

    asyncio.run(setup_database())
    app = _build_test_app(sessionmaker, state)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(f"/pairs/{state['pair_id']}/invite-code/refresh")

        assert response.status_code == 403, response.text
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_refresh_pair_invite_code_rejects_non_pending_pair():
    db_path = _db_path_for("pair-refresh-invite-code-active")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            owner = User(
                email="refresh-active-owner@example.com",
                nickname="发起方",
                password_hash="not-used",
            )
            partner = User(
                email="refresh-active-partner@example.com",
                nickname="已建立关系对象",
                password_hash="not-used",
            )
            db.add_all([owner, partner])
            await db.flush()

            pair = Pair(
                user_a_id=owner.id,
                user_b_id=partner.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="C5K9M2Q4R7",
            )
            db.add(pair)
            await db.commit()

            state["pair_id"] = pair.id
            state["user_id"] = owner.id

    asyncio.run(setup_database())
    app = _build_test_app(sessionmaker, state)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(f"/pairs/{state['pair_id']}/invite-code/refresh")

        assert response.status_code == 409, response.text
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_refresh_pair_invite_code_rate_limits_repeated_refreshes():
    db_path = _db_path_for("pair-refresh-invite-code-rate-limit")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            owner = User(
                email="refresh-rate-owner@example.com",
                nickname="发起方",
                password_hash="not-used",
            )
            db.add(owner)
            await db.flush()

            pair = Pair(
                user_a_id=owner.id,
                user_b_id=None,
                type=None,
                status=PairStatus.PENDING,
                invite_code="F7R9T2Y4U6",
            )
            db.add(pair)
            await db.commit()

            state["pair_id"] = pair.id
            state["user_id"] = owner.id

    asyncio.run(setup_database())
    app = _build_test_app(sessionmaker, state)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            responses = [
                client.post(f"/pairs/{state['pair_id']}/invite-code/refresh")
                for _ in range(4)
            ]

        assert [response.status_code for response in responses[:3]] == [200, 200, 200]
        assert responses[3].status_code == 429, responses[3].text
        assert "秒后再试" in responses[3].json()["detail"]
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_update_partner_nickname_route_trims_input_and_allows_clearing():
    db_path = _db_path_for("pair-partner-nickname")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            owner = User(
                email="nickname-owner@example.com",
                nickname="备注发起方",
                password_hash="not-used",
            )
            partner = User(
                email="nickname-partner@example.com",
                nickname="被备注的人",
                password_hash="not-used",
            )
            db.add_all([owner, partner])
            await db.flush()

            pair = Pair(
                user_a_id=owner.id,
                user_b_id=partner.id,
                type=PairType.FRIEND,
                status=PairStatus.ACTIVE,
                invite_code="D6N8Q3W4X5",
            )
            db.add(pair)
            await db.commit()

            state["pair_id"] = pair.id
            state["user_id"] = owner.id

    asyncio.run(setup_database())
    app = _build_test_app(sessionmaker, state)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            update = client.post(
                f"/pairs/{state['pair_id']}/partner-nickname",
                json={"custom_nickname": "  宝宝  "},
            )
            clear = client.post(
                f"/pairs/{state['pair_id']}/partner-nickname",
                json={"custom_nickname": "   "},
            )

        assert update.status_code == 200, update.text
        assert update.json()["custom_partner_nickname"] == "宝宝"

        assert clear.status_code == 200, clear.text
        assert clear.json()["custom_partner_nickname"] is None

        async def verify_database_state():
            async with sessionmaker() as db:
                pair = await db.get(Pair, state["pair_id"])
                assert pair is not None
                assert pair.custom_partner_nickname_a is None

        asyncio.run(verify_database_state())
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
