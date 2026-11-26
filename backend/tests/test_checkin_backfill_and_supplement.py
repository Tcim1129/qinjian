from datetime import timedelta
from pathlib import Path
import uuid

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import checkins as checkins_api
from app.api.v1 import reports as reports_api
from app.core.database import Base
from app.core.time import current_local_date
from app.models import Checkin, Pair, PairStatus, PairType, Report, ReportStatus, ReportType, User
from app.schemas import CheckinRequest


@pytest.fixture
async def db_factory():
    db_dir = Path(__file__).resolve().parents[2] / "tmp" / "tests"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_file = db_dir / f"checkins-backfill-{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield session_factory
    finally:
        await engine.dispose()
        db_file.unlink(missing_ok=True)


@pytest.mark.anyio
async def test_checkin_allows_backfill_within_30_days_and_blocks_future_or_expired(
    db_factory,
    monkeypatch,
):
    recorded_events = []

    async def capture_event(db, **kwargs):
        recorded_events.append(kwargs)
        return None

    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(checkins_api, "record_relationship_event", capture_event)
    monkeypatch.setattr(checkins_api, "record_user_interaction_event", noop)
    monkeypatch.setattr(checkins_api, "refresh_profile_and_plan", noop)

    today = current_local_date()
    five_days_ago = today - timedelta(days=5)
    thirty_days_ago = today - timedelta(days=30)
    thirty_one_days_ago = today - timedelta(days=31)
    tomorrow = today + timedelta(days=1)

    async with db_factory() as db:
        user = User(email="backfill-window@example.com", nickname="补记用户", password_hash="x")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # 未来日期禁止写入
        with pytest.raises(HTTPException) as future_exc:
            await checkins_api.create_checkin(
                req=CheckinRequest(content="未来的记录", checkin_date=tomorrow),
                background_tasks=BackgroundTasks(),
                mode="solo",
                user=user,
                db=db,
            )
        assert future_exc.value.status_code == 422
        assert "未来" in future_exc.value.detail

        # 超过 30 天禁止补记
        with pytest.raises(HTTPException) as expired_exc:
            await checkins_api.create_checkin(
                req=CheckinRequest(content="太久之前的记录", checkin_date=thirty_one_days_ago),
                background_tasks=BackgroundTasks(),
                mode="solo",
                user=user,
                db=db,
            )
        assert expired_exc.value.status_code == 422
        assert "30 天" in expired_exc.value.detail

        # 过去 5 天和正好 30 天前均允许补记
        res_5 = await checkins_api.create_checkin(
            req=CheckinRequest(content="补记五天前的散步感受", checkin_date=five_days_ago, mood_tags=["平静"]),
            background_tasks=BackgroundTasks(),
            mode="solo",
            user=user,
            db=db,
        )
        res_30 = await checkins_api.create_checkin(
            req=CheckinRequest(content="补记三十天前的聊天复盘", checkin_date=thirty_days_ago),
            background_tasks=BackgroundTasks(),
            mode="solo",
            user=user,
            db=db,
        )
        assert res_5.checkin_date == five_days_ago
        assert res_30.checkin_date == thirty_days_ago

        # 历史补记的 checkin.created 事件带有对应历史日期的 occurred_at，且对应报告落在该日期
        created_events = [e for e in recorded_events if e.get("event_type") == "checkin.created"]
        assert len(created_events) == 2
        assert all(e.get("occurred_at") is not None for e in created_events)

        reports = (
            await db.execute(select(Report).where(Report.user_id == user.id, Report.type == ReportType.SOLO))
        ).scalars().all()
        assert {r.report_date for r in reports} == {five_days_ago, thirty_days_ago}

        # 按日期查询状态可返回对应补记内容
        status_5 = await checkins_api.get_today_status(
            mode="solo", checkin_date=five_days_ago, user=user, db=db
        )
        assert status_5["date"] == str(five_days_ago)
        assert status_5["my_done"] is True
        assert status_5["my_checkin"]["id"] == str(res_5.id)
        assert status_5["my_checkin"]["content"] == "补记五天前的散步感受"


@pytest.mark.anyio
async def test_checkin_supplement_appends_content_merges_tags_resets_shared_summary_and_refreshes_report(
    db_factory,
    monkeypatch,
):
    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(checkins_api, "record_relationship_event", noop)
    monkeypatch.setattr(checkins_api, "record_user_interaction_event", noop)
    monkeypatch.setattr(checkins_api, "refresh_profile_and_plan", noop)

    target_day = current_local_date() - timedelta(days=2)

    async with db_factory() as db:
        ua = User(email="supp-a@example.com", nickname="林知夏", password_hash="x")
        ub = User(email="supp-b@example.com", nickname="陈屿", password_hash="x")
        db.add_all([ua, ub])
        await db.flush()
        pair = Pair(
            user_a_id=ua.id,
            user_b_id=ub.id,
            type=PairType.COUPLE,
            status=PairStatus.ACTIVE,
            invite_code="SUPP123456",
        )
        db.add(pair)
        await db.commit()
        await db.refresh(ua)
        await db.refresh(pair)

        first = await checkins_api.create_checkin(
            req=CheckinRequest(
                pair_id=pair.id,
                content="晚饭后聊了一会儿工作压力。",
                checkin_date=target_day,
                mood_tags=["疲惫"],
            ),
            background_tasks=BackgroundTasks(),
            user=ua,
            db=db,
        )

        # 模拟原记录已分享摘要、且个人简报已完成
        stored_checkin = await db.get(Checkin, first.id)
        stored_checkin.visibility_scope = "shared_summary"
        stored_checkin.visibility_version = 2
        existing_report = (
            await db.execute(
                select(Report).where(
                    Report.pair_id == pair.id,
                    Report.user_id == ua.id,
                    Report.report_date == target_day,
                    Report.type == ReportType.SOLO,
                )
            )
        ).scalar_one()
        existing_report.status = ReportStatus.COMPLETED
        existing_report.content = {"insight": "旧结论"}
        original_report_id = existing_report.id
        await db.commit()

        # 同一日期再次提交应自动转为补充，而不是报 400
        supplemented = await checkins_api.create_checkin(
            req=CheckinRequest(
                pair_id=pair.id,
                content="后来又散步了十分钟，心情缓和了不少。",
                checkin_date=target_day,
                mood_tags=["疲惫", "安心"],
            ),
            background_tasks=BackgroundTasks(),
            user=ua,
            db=db,
        )

        assert supplemented.id == first.id
        assert "晚饭后聊了一会儿工作压力。" in supplemented.content
        assert "补充：后来又散步了十分钟，心情缓和了不少。" in supplemented.content
        assert supplemented.mood_tags == {"tags": ["疲惫", "安心"]}
        # 隐私保护：补充新内容后收回为仅自己可见并递增版本，防止未经确认外泄
        assert supplemented.visibility_scope == "private"
        assert supplemented.visibility_version == 3

        refreshed_report = await db.get(Report, original_report_id)
        assert refreshed_report is not None
        assert refreshed_report.status == ReportStatus.PENDING


@pytest.mark.anyio
async def test_trigger_daily_report_supports_past_30_day_report_date(db_factory):
    today = current_local_date()
    past_day = today - timedelta(days=3)

    async with db_factory() as db:
        user = User(email="report-backfill@example.com", nickname="单人补报", password_hash="x")
        db.add(user)
        await db.flush()
        db.add(
            Checkin(
                pair_id=None,
                user_id=user.id,
                content="三天前补记的一段记录。",
                checkin_date=past_day,
            )
        )
        await db.commit()
        await db.refresh(user)

        with pytest.raises(HTTPException) as future_exc:
            await reports_api.trigger_daily_report(
                background_tasks=BackgroundTasks(),
                mode="solo",
                report_date=today + timedelta(days=1),
                user=user,
                db=db,
            )
        assert future_exc.value.status_code == 422

        report = await reports_api.trigger_daily_report(
            background_tasks=BackgroundTasks(),
            mode="solo",
            report_date=past_day,
            user=user,
            db=db,
        )
        assert report.report_date == past_day
        assert report.type == ReportType.SOLO
