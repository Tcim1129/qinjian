import asyncio
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import reports as reports_api
from app.core.database import Base
from app.core.time import current_local_date
from app.models import (
    Checkin, CrisisAlert, CrisisLevel, Pair, PairStatus, PairType,
    Report, ReportStatus, ReportType, User,
)


@pytest.mark.parametrize('report_type', ['daily', 'weekly', 'monthly'])
def test_failed_report_retry_preserves_references_and_is_shared_between_actors(
    tmp_path, monkeypatch, report_type,
):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'retry.db'}")

    @event.listens_for(engine.sync_engine, 'connect')
    def enforce_foreign_keys(connection, _record):
        connection.execute('PRAGMA foreign_keys=ON')

    factory = async_sessionmaker(engine, expire_on_commit=False)
    ids = {}
    jobs = []

    async def seed():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as db:
            users = [User(email=f'retry-{side}@example.com', nickname=side,
                          password_hash='unused') for side in ['a', 'b']]
            db.add_all(users)
            await db.flush()
            pair = Pair(user_a_id=users[0].id, user_b_id=users[1].id,
                        type=PairType.COUPLE, status=PairStatus.ACTIVE,
                        invite_code=uuid.uuid4().hex[:10])
            db.add(pair)
            await db.flush()
            report = Report(pair_id=pair.id, type=ReportType(report_type),
                            status=ReportStatus.FAILED, content=None,
                            report_date=current_local_date())
            db.add(report)
            await db.flush()
            alert = CrisisAlert(pair_id=pair.id, report_id=report.id,
                                level=CrisisLevel.MILD)
            db.add(alert)
            db.add_all([Checkin(pair_id=pair.id, user_id=user.id, content='今天很累。',
                               checkin_date=current_local_date()) for user in users])
            await db.commit()
            ids.update(pair=pair.id, report=report.id, alert=alert.id,
                       a=users[0].id, b=users[1].id)

    asyncio.run(seed())
    actor = {'id': ids['a']}

    async def current_user():
        async with factory() as db:
            return await db.get(User, actor['id'])

    async def database():
        async with factory() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def process(*args, **kwargs):
        jobs.append((args, kwargs))

    monkeypatch.setattr(reports_api, f'_process_{report_type}_report', process)
    monkeypatch.setattr(reports_api, 'is_relaxed_test_account', lambda _user: True)
    app = FastAPI()
    app.include_router(reports_api.router)
    app.dependency_overrides[reports_api.get_current_user] = current_user
    app.dependency_overrides[reports_api.get_db] = database

    async def check_rows():
        async with factory() as db:
            report = await db.get(Report, ids['report'])
            alert = await db.get(CrisisAlert, ids['alert'])
            rows = (await db.execute(select(Report).where(
                Report.pair_id == ids['pair'], Report.type == ReportType(report_type),
            ))).scalars().all()
            assert len(rows) == 1
            assert report.status == ReportStatus.PENDING
            assert report.content is None
            assert alert.report_id == report.id

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            url = f"/reports/generate-{report_type}?pair_id={ids['pair']}"
            response = client.post(url)
            assert response.status_code == 200, response.text
            assert response.json()['id'] == str(ids['report'])
            assert response.json()['status'] == 'pending'
            actor['id'] = ids['b']
            second = client.post(url)
            assert second.status_code == 200, second.text
            assert second.json()['id'] == response.json()['id']
            assert len(jobs) == 1
        asyncio.run(check_rows())
    finally:
        asyncio.run(engine.dispose())


@pytest.mark.parametrize('report_type', ['daily', 'weekly', 'monthly'])
@pytest.mark.parametrize('provider_failed', [False, True, 'queued'])
def test_old_report_job_does_not_overwrite_a_new_retry(tmp_path, monkeypatch, report_type, provider_failed):
    from app.services import crisis_processor

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'generation.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    ids = {}
    original_time = datetime(2026, 11, 25, 8)
    newer_time = original_time + timedelta(seconds=1)
    provider_calls = []

    async def seed():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as db:
            users = [User(email=f'generation-{side}@example.com', nickname=side,
                          password_hash='unused') for side in ['a', 'b']]
            db.add_all(users)
            await db.flush()
            pair = Pair(user_a_id=users[0].id, user_b_id=users[1].id,
                        type=PairType.COUPLE, status=PairStatus.ACTIVE,
                        invite_code=uuid.uuid4().hex[:10])
            db.add(pair)
            await db.flush()
            report = Report(pair_id=pair.id, type=ReportType(report_type),
                            status=ReportStatus.PENDING, content=None,
                            report_date=current_local_date(), created_at=original_time)
            db.add(report)
            await db.commit()
            ids.update(pair=pair.id, report=report.id)

    async def provider(*args, **kwargs):
        provider_calls.append(True)
        async with factory() as db:
            report = await db.get(Report, ids['report'])
            report.created_at = newer_time
            report.status = ReportStatus.PENDING
            report.content = None
            await db.commit()
        if provider_failed is True:
            raise TimeoutError('old generation timed out')
        return {'health_score': 11, 'insight': '这是旧任务的结果。'}

    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(reports_api, 'async_session', factory)
    monkeypatch.setattr(reports_api, f'generate_{report_type}_report', provider)
    monkeypatch.setattr(reports_api, 'record_relationship_event', noop)
    monkeypatch.setattr(reports_api, 'refresh_profile_and_plan', noop)
    monkeypatch.setattr(crisis_processor, 'process_crisis_from_report', noop)

    async def run():
        await seed()
        if provider_failed == 'queued':
            async with factory() as db:
                report = await db.get(Report, ids['report'])
                report.created_at = newer_time
                await db.commit()
        generation_options = {'generation_created_at': original_time}
        if report_type == 'daily':
            await reports_api._process_daily_report(ids['report'], ids['pair'], 'couple', 'a', 'b', **generation_options)
        else:
            worker = getattr(reports_api, f'_process_{report_type}_report')
            await worker(ids['report'], ids['pair'], 'couple', [{'health_score': 58}], **generation_options)
        assert len(provider_calls) == (0 if provider_failed == 'queued' else 1)
        async with factory() as db:
            report = await db.get(Report, ids['report'])
            assert report.created_at == newer_time
            assert report.status == ReportStatus.PENDING
            assert report.content is None

    try:
        asyncio.run(run())
    finally:
        asyncio.run(engine.dispose())
