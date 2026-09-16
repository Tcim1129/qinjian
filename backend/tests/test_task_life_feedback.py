import asyncio
from datetime import timedelta

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import tasks
from app.core.database import Base
from app.core.time import current_local_date
from app.models import Pair, PairStatus, PairType, RelationshipTask, TaskStatus, User
from app.schemas import TaskFeedbackRequest
from app.services.task_feedback import get_latest_task_feedback_map


def test_quick_feedback_does_not_invent_ratings():
    req = TaskFeedbackRequest(outcome='not_yet', note='今天没空')
    assert req.usefulness_score is None
    assert req.relationship_shift_score is None
    with pytest.raises(ValidationError):
        TaskFeedbackRequest()
    with pytest.raises(ValidationError):
        TaskFeedbackRequest(outcome='not_yet', usefulness_score=8)
    legacy = TaskFeedbackRequest(usefulness_score=4, friction_score=2, relationship_shift_score=0)
    assert legacy.outcome is None
    assert TaskFeedbackRequest(note='聊了一会儿，还不知道有没有帮助').outcome is None
    with pytest.raises(ValidationError):
        TaskFeedbackRequest(note='   ')


def test_pending_feedback_is_saved_without_completing_and_is_owner_scoped(monkeypatch):
    async def noop(*args, **kwargs): pass
    monkeypatch.setattr(tasks, 'refresh_profile_and_plan', noop)
    async def run():
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                a = User(email='life-a@test.com', nickname='A', password_hash='unused')
                b = User(email='life-b@test.com', nickname='B', password_hash='unused')
                db.add_all([a, b]); await db.flush()
                pair = Pair(user_a_id=a.id, user_b_id=b.id, type=PairType.COUPLE, status=PairStatus.ACTIVE, invite_code='LIFELOOP')
                db.add(pair); await db.flush()
                task = RelationshipTask(pair_id=pair.id, user_id=a.id, title='约时间聊聊', due_date=current_local_date())
                db.add(task); await db.commit()
                request = TaskFeedbackRequest(outcome='not_yet', note='今天没空')
                with pytest.raises(HTTPException):
                    await tasks.submit_task_feedback(str(task.id), request, b, db)
                result = await tasks.submit_task_feedback(str(task.id), request, a, db)
                assert result.outcome == 'not_yet'
                assert task.status == TaskStatus.PENDING
                feedback = await get_latest_task_feedback_map(db, pair_id=pair.id, user_id=a.id)
                assert feedback[str(task.id)]['outcome'] == 'not_yet'
                assert feedback[str(task.id)]['usefulness_score'] is None
                from app.ai.tools import execute_tool
                mine = await execute_tool('get_task_feedback', {}, db=db, pair_id=str(pair.id), user_id=str(a.id))
                assert mine['status'] == 'success'
                assert mine['data'][0]['outcome'] == 'not_yet'
                other = await execute_tool('get_task_feedback', {'user_id': str(a.id)}, db=db, pair_id=str(pair.id), user_id=str(b.id))
                assert other['data'] == []
                from app.services.task_planner import _build_recent_status_lines
                own_lines = await _build_recent_status_lines(db, pair_id=pair.id, user_id=a.id)
                other_lines = await _build_recent_status_lines(db, pair_id=pair.id, user_id=b.id)
                assert any('还没做' in line for line in own_lines)
                assert not any('还没做' in line for line in other_lines)
                assert not any('今天没空' in line for line in own_lines + other_lines)
                from app.services.ai_context import _load_recent_events
                other_events = await _load_recent_events(db, pair_id=str(pair.id), user_id=str(b.id), limit=10)
                assert not any((event.payload or {}).get('note') == '今天没空' for event in other_events)
                with pytest.raises(HTTPException):
                    await tasks.submit_task_feedback(str(task.id), TaskFeedbackRequest(outcome='helped'), a, db)
                task.status = TaskStatus.COMPLETED
                await db.flush()
                result = await tasks.submit_task_feedback(str(task.id), TaskFeedbackRequest(outcome='helped'), a, db)
                assert result.outcome == 'helped'
                with pytest.raises(HTTPException):
                    await tasks.reopen_task(str(task.id), b, db)
                reopened = await tasks.reopen_task(str(task.id), a, db)
                assert reopened['task']['status'] == 'pending'
                assert task.completed_at is None
                await tasks.reopen_task(str(task.id), a, db)
                result = await tasks.submit_task_feedback(str(task.id), request, a, db)
                assert result.outcome == 'not_yet'
                task.due_date = current_local_date() + timedelta(days=1)
                task.status = TaskStatus.PENDING
                await db.flush()
                with pytest.raises(HTTPException):
                    await tasks.submit_task_feedback(str(task.id), request, a, db)
                with pytest.raises(HTTPException):
                    await tasks.complete_task(str(task.id), a, db)
                task.due_date = current_local_date()
                await tasks.complete_task(str(task.id), a, db)
                completed_at = task.completed_at
                await tasks.complete_task(str(task.id), a, db)
                assert task.completed_at == completed_at
        finally: await engine.dispose()
    asyncio.run(run())
