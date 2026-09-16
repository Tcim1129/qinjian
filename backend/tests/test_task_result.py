import asyncio
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import tasks
from app import schemas
from app.core.database import Base
from app.core.time import current_local_date
from app.models import Pair, PairStatus, PairType, RelationshipTask, TaskStatus, User
from app.services.task_feedback import get_latest_task_feedback_map


def test_task_result_keeps_completion_and_actual_effect_separate(monkeypatch):
    async def noop(*args, **kwargs):
        pass
    monkeypatch.setattr(tasks, 'refresh_profile_and_plan', noop)

    async def run():
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                a = User(email='result-a@test.com', nickname='A', password_hash='unused')
                b = User(email='result-b@test.com', nickname='B', password_hash='unused')
                db.add_all([a, b])
                await db.flush()
                pair = Pair(user_a_id=a.id, user_b_id=b.id, type=PairType.COUPLE, status=PairStatus.ACTIVE, invite_code='RESULT')
                db.add(pair)
                await db.flush()
                task = RelationshipTask(pair_id=pair.id, user_id=a.id, title='聊聊近况', due_date=current_local_date())
                db.add(task)
                await db.commit()
                request = schemas.TaskResultRequest(status='completed', feedback=None)
                with pytest.raises(HTTPException):
                    await tasks.save_task_result(str(task.id), request, b, db)
                result = await tasks.save_task_result(str(task.id), request, a, db)
                assert result['task']['status'] == 'completed'
                assert result['task']['needs_feedback'] is True
                assert result['task']['feedback'] is None
                original_time = task.completed_at
                unsure = schemas.TaskResultRequest(status='completed', feedback={'outcome': 'uncertain', 'note': '聊了，但还不知道有没有帮助'})
                result = await tasks.save_task_result(str(task.id), unsure, a, db)
                assert result['task']['feedback']['outcome'] == 'uncertain'
                assert result['task']['feedback']['usefulness_score'] is None
                assert task.completed_at == original_time
                result = await tasks.save_task_result(str(task.id), request, a, db)
                assert result['task']['feedback'] is None
                feedback = await get_latest_task_feedback_map(db, pair_id=pair.id, user_id=a.id)
                assert str(task.id) not in feedback
                pending = schemas.TaskResultRequest(status='pending', feedback={'outcome': 'not_yet', 'note': '记错了，还没做'})
                result = await tasks.save_task_result(str(task.id), pending, a, db)
                assert result['task']['status'] == 'pending'
                assert result['task']['feedback']['note'] == '记错了，还没做'
                assert task.completed_at is None
                task.due_date = current_local_date() + timedelta(days=1)
                await db.flush()
                with pytest.raises(HTTPException):
                    await tasks.save_task_result(str(task.id), request, a, db)
                assert task.status == TaskStatus.PENDING
                task.due_date = current_local_date()
                await db.commit()
                task_id = task.id
                async def failed_feedback(*args, **kwargs):
                    raise HTTPException(status_code=503, detail='test save failure')
                monkeypatch.setattr(tasks, 'submit_task_feedback', failed_feedback)
                with pytest.raises(HTTPException):
                    await tasks.save_task_result(str(task_id), unsure, a, db)
                await db.refresh(task)
                assert task.status == TaskStatus.PENDING
                assert task.completed_at is None
        finally:
            await engine.dispose()
    asyncio.run(run())
