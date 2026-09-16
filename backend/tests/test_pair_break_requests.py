import asyncio
import uuid
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import pairs as pairs_api
from app.core.database import Base
from app.models import (
    Pair,
    PairChangeRequest,
    PairChangeRequestMessage,
    PairChangeRequestPhase,
    PairChangeRequestResolutionReason,
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


def test_break_request_without_retention_auto_expires_and_ends_pair():
    db_path = _db_path_for("break-request-no-retention-timeout")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            requester = User(
                email="break-requester@example.com",
                nickname="发起方",
                password_hash="not-used",
            )
            partner = User(
                email="break-partner@example.com",
                nickname="对方",
                password_hash="not-used",
            )
            db.add_all([requester, partner])
            await db.flush()

            pair = Pair(
                user_a_id=requester.id,
                user_b_id=partner.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="A3H7K8M9Q2",
            )
            db.add(pair)
            await db.commit()

            state["pair_id"] = pair.id
            state["requester_id"] = requester.id
            state["partner_id"] = partner.id
            state["user_id"] = requester.id

    asyncio.run(setup_database())
    app = _build_test_app(sessionmaker, state)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            created = client.post(
                f"/pairs/{state['pair_id']}/break-request",
                json={"allow_retention": False},
            )

        assert created.status_code == 200, created.text
        request_id = created.json()["request"]["id"]

        async def expire_request():
            async with sessionmaker() as db:
                request = await db.get(PairChangeRequest, uuid.UUID(request_id))
                request.expires_at = request.expires_at - timedelta(hours=25)
                await db.commit()

        asyncio.run(expire_request())

        with TestClient(app, raise_server_exceptions=False) as client:
            pairs = client.get("/pairs/me")

        assert pairs.status_code == 200, pairs.text
        assert pairs.json() == []

        async def verify_state():
            async with sessionmaker() as db:
                pair = await db.get(Pair, state["pair_id"])
                request = await db.get(PairChangeRequest, uuid.UUID(request_id))
                assert pair.status == PairStatus.ENDED
                assert request.status == PairChangeRequestStatus.APPROVED
                assert (
                    request.resolution_reason
                    == PairChangeRequestResolutionReason.NO_RETENTION_TIMEOUT
                )

        asyncio.run(verify_state())
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_break_request_retention_accept_restores_active_pair_and_keeps_messages():
    db_path = _db_path_for("break-request-retention-accept")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            requester = User(
                email="retain-requester@example.com",
                nickname="发起方",
                password_hash="not-used",
            )
            partner = User(
                email="retain-partner@example.com",
                nickname="挽留方",
                password_hash="not-used",
            )
            db.add_all([requester, partner])
            await db.flush()

            pair = Pair(
                user_a_id=requester.id,
                user_b_id=partner.id,
                type=PairType.FRIEND,
                status=PairStatus.ACTIVE,
                invite_code="B4J8L9N2P3",
            )
            db.add(pair)
            await db.commit()

            state["pair_id"] = pair.id
            state["requester_id"] = requester.id
            state["partner_id"] = partner.id
            state["user_id"] = requester.id

    asyncio.run(setup_database())

    try:
        state["user_id"] = state["requester_id"]
        requester_app = _build_test_app(sessionmaker, state)
        with TestClient(requester_app, raise_server_exceptions=False) as client:
            created = client.post(
                f"/pairs/{state['pair_id']}/break-request",
                json={"allow_retention": True},
            )

        assert created.status_code == 200, created.text
        request_id = created.json()["request"]["id"]

        state["user_id"] = state["partner_id"]
        partner_app = _build_test_app(sessionmaker, state)
        with TestClient(partner_app, raise_server_exceptions=False) as client:
            retained = client.post(
                f"/pairs/{state['pair_id']}/change-requests/{request_id}/retain",
                json={"message": "我想先认真解释一下。"},
            )
            appended = client.post(
                f"/pairs/{state['pair_id']}/change-requests/{request_id}/messages",
                json={"message": "我也愿意把之前的问题改掉。"},
            )

        assert retained.status_code == 200, retained.text
        assert retained.json()["request"]["phase"] == "retaining"
        assert appended.status_code == 200, appended.text
        assert len(appended.json()["request"]["messages"]) == 2

        state["user_id"] = state["requester_id"]
        requester_app = _build_test_app(sessionmaker, state)
        with TestClient(requester_app, raise_server_exceptions=False) as client:
            decided = client.post(
                f"/pairs/{state['pair_id']}/change-requests/{request_id}/retention-decision",
                json={"decision": "accept"},
            )

        assert decided.status_code == 200, decided.text
        body = decided.json()
        assert body["pair"]["status"] == "active"
        assert body["pair"]["pending_change_request"] is None
        assert body["pair"]["latest_change_request"]["status"] == "rejected"
        assert body["pair"]["latest_change_request"]["resolution_reason"] == "retention_accepted"

        async def verify_state():
            async with sessionmaker() as db:
                pair = await db.get(Pair, state["pair_id"])
                request = await db.get(PairChangeRequest, uuid.UUID(request_id))
                messages = (
                    await db.execute(
                        select(PairChangeRequestMessage).where(
                            PairChangeRequestMessage.request_id == uuid.UUID(request_id)
                        )
                    )
                ).scalars().all()
                assert pair.status == PairStatus.ACTIVE
                assert request.status == PairChangeRequestStatus.REJECTED
                assert (
                    request.resolution_reason
                    == PairChangeRequestResolutionReason.RETENTION_ACCEPTED
                )
                assert len(messages) == 2

        asyncio.run(verify_state())
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_break_request_partner_can_decline_retention_and_end_pair_immediately():
    db_path = _db_path_for("break-request-partner-declines")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            requester = User(
                email="decline-requester@example.com",
                nickname="发起方",
                password_hash="not-used",
            )
            partner = User(
                email="decline-partner@example.com",
                nickname="对方",
                password_hash="not-used",
            )
            db.add_all([requester, partner])
            await db.flush()

            pair = Pair(
                user_a_id=requester.id,
                user_b_id=partner.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="C5K9M2Q4R7",
            )
            db.add(pair)
            await db.commit()

            state["pair_id"] = pair.id
            state["requester_id"] = requester.id
            state["partner_id"] = partner.id

    asyncio.run(setup_database())

    try:
        state["user_id"] = state["requester_id"]
        requester_app = _build_test_app(sessionmaker, state)
        with TestClient(requester_app, raise_server_exceptions=False) as client:
            created = client.post(
                f"/pairs/{state['pair_id']}/break-request",
                json={"allow_retention": True},
            )

        request_id = created.json()["request"]["id"]

        state["user_id"] = state["partner_id"]
        partner_app = _build_test_app(sessionmaker, state)
        with TestClient(partner_app, raise_server_exceptions=False) as client:
            decided = client.post(
                f"/pairs/{state['pair_id']}/change-requests/{request_id}/decline-break"
            )

        assert decided.status_code == 200, decided.text
        body = decided.json()
        assert body["pair"]["status"] == "ended"
        assert body["request"]["status"] == "approved"
        assert body["request"]["resolution_reason"] == "partner_declined"

        async def verify_state():
            async with sessionmaker() as db:
                pair = await db.get(Pair, state["pair_id"])
                request = await db.get(PairChangeRequest, uuid.UUID(request_id))
                assert pair.status == PairStatus.ENDED
                assert request.status == PairChangeRequestStatus.APPROVED
                assert (
                    request.resolution_reason
                    == PairChangeRequestResolutionReason.PARTNER_DECLINED
                )

        asyncio.run(verify_state())
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_break_request_retention_timeout_auto_ends_pair_on_next_read():
    db_path = _db_path_for("break-request-retention-timeout")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            requester = User(
                email="timeout-requester@example.com",
                nickname="发起方",
                password_hash="not-used",
            )
            partner = User(
                email="timeout-partner@example.com",
                nickname="挽留方",
                password_hash="not-used",
            )
            db.add_all([requester, partner])
            await db.flush()

            pair = Pair(
                user_a_id=requester.id,
                user_b_id=partner.id,
                type=PairType.FRIEND,
                status=PairStatus.ACTIVE,
                invite_code="D6N8Q3W4X5",
            )
            db.add(pair)
            await db.commit()

            state["pair_id"] = pair.id
            state["requester_id"] = requester.id
            state["partner_id"] = partner.id

    asyncio.run(setup_database())

    try:
        state["user_id"] = state["requester_id"]
        requester_app = _build_test_app(sessionmaker, state)
        with TestClient(requester_app, raise_server_exceptions=False) as client:
            created = client.post(
                f"/pairs/{state['pair_id']}/break-request",
                json={"allow_retention": True},
            )

        request_id = created.json()["request"]["id"]

        state["user_id"] = state["partner_id"]
        partner_app = _build_test_app(sessionmaker, state)
        with TestClient(partner_app, raise_server_exceptions=False) as client:
            retained = client.post(
                f"/pairs/{state['pair_id']}/change-requests/{request_id}/retain",
                json={"message": "再给我一次机会。"},
            )

        assert retained.status_code == 200, retained.text
        assert retained.json()["request"]["phase"] == "retaining"

        async def expire_request():
            async with sessionmaker() as db:
                request = await db.get(PairChangeRequest, uuid.UUID(request_id))
                request.expires_at = request.expires_at - timedelta(hours=13)
                await db.commit()

        asyncio.run(expire_request())

        state["user_id"] = state["requester_id"]
        requester_app = _build_test_app(sessionmaker, state)
        with TestClient(requester_app, raise_server_exceptions=False) as client:
            pairs = client.get("/pairs/me")

        assert pairs.status_code == 200, pairs.text
        assert pairs.json() == []

        async def verify_state():
            async with sessionmaker() as db:
                pair = await db.get(Pair, state["pair_id"])
                request = await db.get(PairChangeRequest, uuid.UUID(request_id))
                assert pair.status == PairStatus.ENDED
                assert request.status == PairChangeRequestStatus.APPROVED
                assert request.phase == PairChangeRequestPhase.RETAINING
                assert (
                    request.resolution_reason
                    == PairChangeRequestResolutionReason.RETENTION_TIMEOUT
                )

        asyncio.run(verify_state())
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
