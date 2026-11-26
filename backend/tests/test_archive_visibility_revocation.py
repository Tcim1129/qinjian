"""归档、导出和智能体检索遵守当前共享授权。"""
import uuid
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.insights_routes import timeline as timeline_api
from app.ai.tools import _get_recent_events, _search_timeline
from app.core.database import Base
from app.models import Checkin, Pair, PairStatus, PairType, Report, ReportStatus, ReportType, User


@pytest.mark.anyio
async def test_archive_revocation_filters_partner_records_and_solo_reports(tmp_path):
    engine = create_async_engine('sqlite+aiosqlite:///' + (tmp_path / 'revocation.db').as_posix())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    a, b, pair_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    private_id, shared_id, report_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with factory() as db:
        db.add_all([
            User(id=a, email='archive-a@example.test', nickname='QA甲', password_hash='x'),
            User(id=b, email='archive-b@example.test', nickname='QA乙', password_hash='x'),
            Pair(id=pair_id, user_a_id=a, user_b_id=b, type=PairType.COUPLE, status=PairStatus.ACTIVE, invite_code='A3H7K8M9Q2'),
            Checkin(id=private_id, pair_id=pair_id, user_id=a, content='PRIVATE_RAW', visibility_scope='private', checkin_date=date.today()),
            Checkin(id=shared_id, pair_id=pair_id, user_id=a, content='SHARED_RAW', visibility_scope='shared_summary', checkin_date=date.today(), archive_summary='UNAPPROVED_IMAGE_DETAILS', archive_tags=['UNAPPROVED_RISK_TAG']),
            Report(id=report_id, pair_id=pair_id, user_id=a, type=ReportType.SOLO, status=ReportStatus.COMPLETED, report_date=date.today(), content={'summary': 'PRIVATE_SOLO_REPORT'}),
        ])
        await db.commit()

    async def override_db():
        async with factory() as db:
            yield db
            await db.commit()

    actor = {'id': b}

    async def override_user():
        return SimpleNamespace(id=actor['id'])

    app = FastAPI()
    app.include_router(timeline_api.router)
    app.dependency_overrides[timeline_api.get_db] = override_db
    app.dependency_overrides[timeline_api.get_current_user] = override_user
    try:
        with TestClient(app) as client:
            url = f'/timeline/archive?pair_id={pair_id}'
            shared_response = client.get(url)
            assert shared_response.status_code == 200
            items = shared_response.json()['items']
            assert [x['id'] for x in items] == [str(shared_id)]
            for secret in ('PRIVATE_RAW', 'SHARED_RAW', 'UNAPPROVED_IMAGE_DETAILS', 'UNAPPROVED_RISK_TAG', 'PRIVATE_SOLO_REPORT'):
                assert secret not in shared_response.text
            async with factory() as db:
                checkin = await db.get(Checkin, shared_id)
                checkin.visibility_scope = 'private'
                checkin.visibility_version = 2
                await db.commit()
            withdrawn = client.get(url)
            assert withdrawn.json()['items'] == []
            exported = client.get(f'/timeline/archive/export?pair_id={pair_id}')
            assert exported.json()['items'] == []
            direct_export = client.get(f'/timeline/archive/items/{shared_id}/export?pair_id={pair_id}')
            assert direct_export.status_code in (403, 404)
            async with factory() as db:
                assert await _get_recent_events(db, pair_id=str(pair_id), user_id=str(b)) == []
                assert await _search_timeline(db, pair_id=str(pair_id), user_id=str(b)) == []
            actor['id'] = a
            owner = client.get(url)
            assert len(owner.json()['items']) == 3
            assert 'PRIVATE_RAW' in owner.text and 'PRIVATE_SOLO_REPORT' in owner.text
    finally:
        await engine.dispose()
