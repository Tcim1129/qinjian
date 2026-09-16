from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.time import current_local_date
from app.models import Pair, PairStatus, PairType, Report, ReportStatus, ReportType, User
from app.services.crisis_processor import process_crisis_from_report


def test_crisis_processor_uses_uuid_pair_id_for_auto_resolve():
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"crisis-uuid-{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def run_scenario():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(
                email="crisis-uuid-a@example.com",
                nickname="Crisis A",
                password_hash="not-used",
            )
            user_b = User(
                email="crisis-uuid-b@example.com",
                nickname="Crisis B",
                password_hash="not-used",
            )
            db.add_all([user_a, user_b])
            await db.flush()

            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="LKJHGFDSAQ",
            )
            db.add(pair)
            await db.flush()

            report = Report(
                pair_id=pair.id,
                type=ReportType.DAILY,
                status=ReportStatus.COMPLETED,
                content={"crisis_level": "none", "health_score": 88},
                health_score=88,
                report_date=current_local_date(),
            )
            db.add(report)
            await db.flush()

            result = await process_crisis_from_report(db, report, pair)
            await db.commit()
            return result

    try:
        result = asyncio.run(run_scenario())
        assert result is None
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
