import asyncio
import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import checkins as checkins_api
from app.core.database import Base
from app.models import Checkin, Pair, PairStatus, PairType, User
from app.schemas import CheckinRequest


TODAY = date(2026, 4, 11)


async def _noop_event(*args, **kwargs):
    return None


async def _noop_profile(*args, **kwargs):
    return None, None


async def _run_with_session(work):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with Session() as db:
            return await work(db)
    finally:
        await engine.dispose()


def _user(email="me@example.com") -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        nickname=email.split("@", 1)[0],
        password_hash="hash",
    )


def _pair(user_a: User, user_b: User) -> Pair:
    return Pair(
        id=uuid.uuid4(),
        user_a_id=user_a.id,
        user_b_id=user_b.id,
        type=PairType.COUPLE,
        status=PairStatus.ACTIVE,
        invite_code="ABC12345",
    )


async def _seed_pair_scope(db):
    user_a = _user("a@example.com")
    user_b = _user("b@example.com")
    pair = _pair(user_a, user_b)
    db.add_all([user_a, user_b, pair])
    await db.flush()
    return user_a, user_b, pair


def test_pair_checkin_allows_one_primary_and_two_supplements(monkeypatch):
    async def scenario(db):
        monkeypatch.setattr(checkins_api, "current_local_date", lambda: TODAY)
        monkeypatch.setattr(checkins_api, "record_relationship_event", _noop_event)
        monkeypatch.setattr(checkins_api, "refresh_profile_and_plan", _noop_profile)
        user, _, pair = await _seed_pair_scope(db)

        for index in range(1, 4):
            response = await checkins_api.create_checkin(
                CheckinRequest(pair_id=pair.id, content=f"第 {index} 条"),
                BackgroundTasks(),
                user=user,
                db=db,
            )

            assert response.entry_index == index
            assert response.daily_entry_limit == 3

        with pytest.raises(HTTPException) as exc_info:
            await checkins_api.create_checkin(
                CheckinRequest(pair_id=pair.id, content="第 4 条"),
                BackgroundTasks(),
                user=user,
                db=db,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "今天最多 1 条正式记录和 2 条补充记录"

    asyncio.run(_run_with_session(scenario))


def test_solo_and_pair_daily_limits_are_counted_separately(monkeypatch):
    async def scenario(db):
        monkeypatch.setattr(checkins_api, "current_local_date", lambda: TODAY)
        monkeypatch.setattr(checkins_api, "record_relationship_event", _noop_event)
        monkeypatch.setattr(checkins_api, "refresh_profile_and_plan", _noop_profile)
        user, _, pair = await _seed_pair_scope(db)

        for index in range(3):
            await checkins_api.create_checkin(
                CheckinRequest(pair_id=pair.id, content=f"pair {index}"),
                BackgroundTasks(),
                user=user,
                db=db,
            )

        solo_response = await checkins_api.create_checkin(
            CheckinRequest(content="solo still allowed"),
            BackgroundTasks(),
            mode="solo",
            user=user,
            db=db,
        )

        assert solo_response.pair_id is None
        assert solo_response.entry_index == 1

    asyncio.run(_run_with_session(scenario))


def test_today_status_returns_all_my_entries_and_remaining_count(monkeypatch):
    async def scenario(db):
        monkeypatch.setattr(checkins_api, "current_local_date", lambda: TODAY)
        user, _, pair = await _seed_pair_scope(db)

        empty_status = await checkins_api.get_today_status(
            pair_id=str(pair.id),
            user=user,
            db=db,
        )
        assert empty_status["my_entry_count"] == 0
        assert empty_status["my_remaining_supplements"] == 2

        for index in range(3):
            db.add(
                Checkin(
                    pair_id=pair.id,
                    user_id=user.id,
                    content=f"entry {index + 1}",
                    checkin_date=TODAY,
                    created_at=datetime(2026, 4, 11, 8 + index, tzinfo=timezone.utc).replace(tzinfo=None),
                )
            )
        await db.flush()

        status = await checkins_api.get_today_status(
            pair_id=str(pair.id),
            user=user,
            db=db,
        )

        assert status["my_done"] is True
        assert status["my_entry_count"] == 3
        assert status["my_entry_limit"] == 3
        assert status["my_remaining_supplements"] == 0
        assert [item["content"] for item in status["my_checkins"]] == [
            "entry 1",
            "entry 2",
            "entry 3",
        ]
        assert status["my_checkin"]["content"] == "entry 1"

    asyncio.run(_run_with_session(scenario))


def test_checkin_history_filters_by_business_date_range(monkeypatch):
    async def scenario(db):
        user, _, pair = await _seed_pair_scope(db)
        for checkin_date in [date(2026, 4, 9), date(2026, 4, 10), date(2026, 4, 11)]:
            db.add(
                Checkin(
                    pair_id=pair.id,
                    user_id=user.id,
                    content=f"entry {checkin_date.isoformat()}",
                    checkin_date=checkin_date,
                    created_at=datetime.combine(checkin_date, datetime.min.time()),
                )
            )
        await db.flush()

        history = await checkins_api.get_checkin_history(
            pair_id=str(pair.id),
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 11),
            user=user,
            db=db,
        )

        assert [item.checkin_date for item in history] == [
            date(2026, 4, 11),
            date(2026, 4, 10),
        ]

    asyncio.run(_run_with_session(scenario))
