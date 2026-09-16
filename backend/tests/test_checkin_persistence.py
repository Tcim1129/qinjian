import uuid
from pathlib import Path

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import checkins as checkins_api
from app.core.database import Base
from app.core.time import current_local_date
from app.models import Checkin, Report, ReportStatus, ReportType, User
from app.schemas import CheckinRequest


@pytest.fixture
async def db_factory():
    db_dir = Path(__file__).resolve().parents[2] / "tmp" / "tests"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_file = db_dir / f"checkins-{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_create_solo_checkin_is_visible_to_fresh_sessions(
    db_factory,
    monkeypatch,
):
    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(checkins_api, "record_relationship_event", noop)
    monkeypatch.setattr(checkins_api, "record_user_interaction_event", noop)
    monkeypatch.setattr(checkins_api, "refresh_profile_and_plan", noop)

    async with db_factory() as db:
        user = User(
            email="checkin-visible@example.com",
            nickname="visible",
            password_hash="hashed-password",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        await checkins_api.create_checkin(
            req=CheckinRequest(
                content="今天先把委屈写下来，再决定怎么开口。",
                mood_score=6,
                interaction_freq=3,
                interaction_initiative="me",
                deep_conversation=True,
                task_completed=False,
            ),
            background_tasks=BackgroundTasks(),
            mode="solo",
            user=user,
            db=db,
        )

    async with db_factory() as db:
        result = await db.execute(
            select(Checkin).where(Checkin.user_id == user.id)
        )
        stored = result.scalar_one_or_none()

    assert stored is not None
    assert stored.content == "今天先把委屈写下来，再决定怎么开口。"


@pytest.mark.anyio
async def test_create_solo_checkin_creates_pending_solo_report_immediately(
    db_factory,
    monkeypatch,
):
    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(checkins_api, "record_relationship_event", noop)
    monkeypatch.setattr(checkins_api, "record_user_interaction_event", noop)
    monkeypatch.setattr(checkins_api, "refresh_profile_and_plan", noop)

    async with db_factory() as db:
        user = User(
            email="checkin-report@example.com",
            nickname="pending-report",
            password_hash="hashed-password",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        await checkins_api.create_checkin(
            req=CheckinRequest(
                content="先记下这句，等会儿再回来看今天的状态。",
                mood_score=5,
                interaction_freq=2,
                interaction_initiative="equal",
                deep_conversation=False,
                task_completed=True,
            ),
            background_tasks=BackgroundTasks(),
            mode="solo",
            user=user,
            db=db,
        )

    async with db_factory() as db:
        result = await db.execute(
            select(Report).where(
                Report.user_id == user.id,
                Report.pair_id.is_(None),
                Report.report_date == current_local_date(),
                Report.type == ReportType.SOLO,
            )
        )
        stored = result.scalar_one_or_none()

    assert stored is not None
    assert stored.status == ReportStatus.PENDING


@pytest.mark.anyio
async def test_create_solo_checkin_persists_when_side_effects_fail(
    db_factory,
    monkeypatch,
):
    async def failing_record_relationship_event(*args, **kwargs):
        raise RuntimeError("relationship intelligence unavailable")

    monkeypatch.setattr(
        checkins_api,
        "record_relationship_event",
        failing_record_relationship_event,
    )

    async with db_factory() as db:
        user = User(
            email="checkin-side-effects@example.com",
            nickname="side-effects",
            password_hash="hashed-password",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = user.id

        response = await checkins_api.create_checkin(
            req=CheckinRequest(
                content="社交之后很开心，但作业没有做完有点焦虑。",
                mood_tags=["开心", "焦虑", "反思"],
                mood_score=9,
                interaction_freq=4,
                interaction_initiative="partner",
                deep_conversation=False,
                task_completed=False,
            ),
            background_tasks=BackgroundTasks(),
            mode="solo",
            user=user,
            db=db,
        )

    async with db_factory() as db:
        stored_checkin = await db.get(Checkin, response.id)
        result = await db.execute(
            select(Report).where(
                Report.user_id == user_id,
                Report.pair_id.is_(None),
                Report.report_date == current_local_date(),
                Report.type == ReportType.SOLO,
            )
        )
        stored_report = result.scalar_one_or_none()

    assert stored_checkin is not None
    assert stored_checkin.content == "社交之后很开心，但作业没有做完有点焦虑。"
    assert stored_report is not None
    assert stored_report.status == ReportStatus.PENDING


@pytest.mark.anyio
async def test_create_solo_checkin_rejects_incomplete_background(
    db_factory,
    monkeypatch,
):
    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(checkins_api, "record_relationship_event", noop)
    monkeypatch.setattr(checkins_api, "record_user_interaction_event", noop)
    monkeypatch.setattr(checkins_api, "refresh_profile_and_plan", noop)

    async with db_factory() as db:
        user = User(
            email="checkin-required-background@example.com",
            nickname="required-background",
            password_hash="hashed-password",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        with pytest.raises(HTTPException) as exc_info:
            await checkins_api.create_checkin(
                req=CheckinRequest(
                    content="今天先把最难受的那句写下来。",
                    mood_score=6,
                    interaction_freq=3,
                    interaction_initiative="partner",
                    deep_conversation=None,
                    task_completed=False,
                ),
                background_tasks=BackgroundTasks(),
                mode="solo",
                user=user,
                db=db,
            )

        result = await db.execute(
            select(Checkin).where(Checkin.user_id == user.id)
        )
        stored = result.scalar_one_or_none()

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "背景补充未完成：有没有深聊"
    assert stored is None


@pytest.mark.anyio
async def test_create_solo_checkin_rejects_upload_owned_by_another_user(
    db_factory,
    monkeypatch,
):
    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(checkins_api, "record_relationship_event", noop)
    monkeypatch.setattr(checkins_api, "record_user_interaction_event", noop)
    monkeypatch.setattr(checkins_api, "refresh_profile_and_plan", noop)

    async with db_factory() as db:
        user = User(
            email="checkin-media-owner@example.com",
            nickname="owner",
            password_hash="hashed-password",
        )
        other = User(
            email="checkin-media-other@example.com",
            nickname="other",
            password_hash="hashed-password",
            avatar_url="/uploads/images/other.png",
        )
        db.add_all([user, other])
        await db.commit()
        await db.refresh(user)

        with pytest.raises(HTTPException) as exc_info:
            await checkins_api.create_checkin(
                req=CheckinRequest(
                    content="今天先把委屈写下来，再决定怎么开口。",
                    image_url="/uploads/images/other.png",
                    mood_score=6,
                    interaction_freq=3,
                    interaction_initiative="me",
                    deep_conversation=True,
                    task_completed=False,
                ),
                background_tasks=BackgroundTasks(),
                mode="solo",
                user=user,
                db=db,
            )

    assert exc_info.value.status_code == 403
