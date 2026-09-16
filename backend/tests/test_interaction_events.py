import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models import User, UserInteractionEvent
from app.services.interaction_events import (
    build_interaction_payload,
    record_user_interaction_event,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_record_user_interaction_event_persists_standardized_payload():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            email="events@example.com",
            nickname="events",
            password_hash="hashed-password",
        )
        session.add(user)
        await session.flush()

        payload = build_interaction_payload(
            {"title": "关系简报"},
            text="你怎么又不回我，我真的很烦。",
            risk_level="high",
        )
        event = await record_user_interaction_event(
            session,
            event_type="page.view",
            user_id=user.id,
            source="client",
            page="report",
            path="/report",
            payload=payload,
        )
        await session.commit()

        result = await session.execute(
            select(UserInteractionEvent).where(UserInteractionEvent.id == event.id)
        )
        stored = result.scalar_one()

        assert stored.page == "report"
        assert stored.payload["inferred_tone"]
        assert stored.payload["message_length_bucket"]
        assert stored.payload["risk_level"] == "high"

    await engine.dispose()


@pytest.mark.anyio
async def test_record_user_interaction_event_sanitizes_direct_payload_text():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            email="sanitize-events@example.com",
            nickname="sanitize",
            password_hash="hashed-password",
        )
        session.add(user)
        await session.flush()

        event = await record_user_interaction_event(
            session,
            event_type="agent.chat.assistant_reply",
            user_id=user.id,
            source="agent",
            payload={
                "reply_preview": "邮箱 tester@example.com，口令 SECRET_CASE_123",
                "session_id": "session-keep",
            },
        )
        await session.commit()

        result = await session.execute(
            select(UserInteractionEvent).where(UserInteractionEvent.id == event.id)
        )
        stored = result.scalar_one()

        assert stored.payload["reply_preview"] == "邮箱 t***@example.com，口令 [SENSITIVE]"
        assert stored.payload["session_id"] == "session-keep"

    await engine.dispose()
