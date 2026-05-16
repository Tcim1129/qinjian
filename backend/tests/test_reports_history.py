import asyncio
import uuid
from datetime import date, datetime

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import checkins as checkins_api
from app.api.v1 import reports as reports_api
from app.core.database import Base
from app.models import (
    Checkin,
    Pair,
    PairStatus,
    PairType,
    Report,
    ReportStatus,
    ReportType,
    User,
)
from app.schemas import CheckinRequest


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
        invite_code="PAIRCODE1",
    )


async def _seed_pair_scope(db):
    user_a = _user("a@example.com")
    user_b = _user("b@example.com")
    pair = _pair(user_a, user_b)
    db.add_all([user_a, user_b, pair])
    await db.flush()
    return user_a, user_b, pair


def test_combine_checkin_contents_preserves_entry_order_and_labels():
    items = [
        Checkin(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            content="第二条补充",
            checkin_date=date(2026, 4, 11),
            created_at=datetime(2026, 4, 11, 9, 30),
        ),
        Checkin(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            content="第一条正式记录",
            checkin_date=date(2026, 4, 11),
            created_at=datetime(2026, 4, 11, 8, 0),
        ),
    ]

    assert checkins_api._combine_checkin_contents(items) == (
        "第 1 条记录：第一条正式记录\n\n"
        "第 2 条记录：第二条补充"
    )


def test_report_history_filters_by_business_date_range():
    async def scenario(db):
        user, _, pair = await _seed_pair_scope(db)
        for report_date in [date(2026, 4, 9), date(2026, 4, 10), date(2026, 4, 11)]:
            db.add(
                Report(
                    pair_id=pair.id,
                    type=ReportType.DAILY,
                    status=ReportStatus.COMPLETED,
                    content={"insight": report_date.isoformat()},
                    health_score=70,
                    report_date=report_date,
                    created_at=datetime.combine(report_date, datetime.min.time()),
                )
            )
        await db.flush()

        history = await reports_api.get_report_history(
            pair_id=str(pair.id),
            report_type="daily",
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 11),
            user=user,
            db=db,
        )

        assert [item.report_date for item in history] == [
            date(2026, 4, 11),
            date(2026, 4, 10),
        ]

    asyncio.run(_run_with_session(scenario))


def test_pair_report_aggregation_never_uses_partner_content_in_checkin_history():
    async def scenario(db):
        user, partner, pair = await _seed_pair_scope(db)
        shared_day = date(2026, 4, 11)
        db.add_all(
            [
                Checkin(
                    pair_id=pair.id,
                    user_id=user.id,
                    content="我的正式记录",
                    checkin_date=shared_day,
                    created_at=datetime(2026, 4, 11, 8, 0),
                ),
                Checkin(
                    pair_id=pair.id,
                    user_id=partner.id,
                    content="对方不应出现在我的历史里",
                    checkin_date=shared_day,
                    created_at=datetime(2026, 4, 11, 8, 5),
                ),
            ]
        )
        await db.flush()

        history = await checkins_api.get_checkin_history(
            pair_id=str(pair.id),
            start_date=shared_day,
            end_date=shared_day,
            user=user,
            db=db,
        )

        assert [item.content for item in history] == ["我的正式记录"]

    asyncio.run(_run_with_session(scenario))


async def _noop_event(*args, **kwargs):
    return None


async def _noop_profile(*args, **kwargs):
    return None, None


def test_supplement_resets_existing_solo_report_and_schedules_merged_content(monkeypatch):
    async def scenario(db):
        shared_day = date(2026, 4, 11)
        monkeypatch.setattr(checkins_api, "current_local_date", lambda: shared_day)
        monkeypatch.setattr(checkins_api, "record_relationship_event", _noop_event)
        monkeypatch.setattr(checkins_api, "refresh_profile_and_plan", _noop_profile)
        user = _user()
        db.add(user)
        await db.flush()
        db.add(
            Checkin(
                pair_id=None,
                user_id=user.id,
                content="第一条正式记录",
                checkin_date=shared_day,
                created_at=datetime(2026, 4, 11, 1, 0),
            )
        )
        report = Report(
            pair_id=None,
            user_id=user.id,
            type=ReportType.SOLO,
            status=ReportStatus.COMPLETED,
            content={"insight": "old"},
            health_score=70,
            report_date=shared_day,
            created_at=datetime(2026, 4, 11, 8, 1),
        )
        db.add(report)
        await db.flush()
        background_tasks = BackgroundTasks()

        await checkins_api.create_checkin(
            CheckinRequest(content="第二条补充"),
            background_tasks,
            mode="solo",
            user=user,
            db=db,
        )

        assert report.status == ReportStatus.PENDING
        assert report.content is None
        solo_tasks = [
            task
            for task in background_tasks.tasks
            if getattr(task.func, "__name__", "") == "_auto_generate_solo"
        ]
        assert len(solo_tasks) == 1
        assert solo_tasks[0].args[2] == (
            "第 1 条记录：第一条正式记录\n\n"
            "第 2 条记录：第二条补充"
        )

    asyncio.run(_run_with_session(scenario))
