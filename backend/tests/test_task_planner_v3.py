from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import pairs as pairs_api
from app.api.v1 import tasks as tasks_api
from app import ai as ai_module
from app.services import task_adaptation
from app.services import task_planner as planner_service
from app.core.database import Base
from app.core.time import current_local_date, current_local_datetime
from app.models import (
    Pair,
    PairStatus,
    PairType,
    RelationshipEvent,
    RelationshipTask,
    TaskStatus,
    User,
    UserNotification,
)
from app.services.task_planner import (
    MAX_MANUAL_TASKS_PER_DATE,
    resolve_effective_task_planner_settings,
)
from app.services.request_cooldown_store import close_request_cooldown_store


def _db_path_for(test_name: str) -> Path:
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    return db_dir / f"{test_name}-{uuid.uuid4().hex}.db"


def _make_app(sessionmaker, state: dict):
    app = FastAPI()
    app.include_router(tasks_api.router)
    app.include_router(pairs_api.router)

    async def override_get_db():
        async with sessionmaker() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, state["user_id"])

    app.dependency_overrides[tasks_api.get_db] = override_get_db
    app.dependency_overrides[tasks_api.get_current_user] = override_current_user
    app.dependency_overrides[pairs_api.get_db] = override_get_db
    app.dependency_overrides[pairs_api.get_current_user] = override_current_user
    return app


async def _seed_pair(sessionmaker, *, product_prefs: dict | None = None):
    async with sessionmaker() as db:
        user_a = User(
            email=f"planner-a-{uuid.uuid4().hex}@example.com",
            nickname="Planner A",
            password_hash="not-used",
            product_prefs=product_prefs,
        )
        user_b = User(
            email=f"planner-b-{uuid.uuid4().hex}@example.com",
            nickname="Planner B",
            password_hash="not-used",
            product_prefs=product_prefs,
        )
        db.add_all([user_a, user_b])
        await db.flush()
        pair = Pair(
            user_a_id=user_a.id,
            user_b_id=user_b.id,
            type=PairType.COUPLE,
            status=PairStatus.ACTIVE,
            invite_code=uuid.uuid4().hex[:10].upper(),
        )
        db.add(pair)
        await db.commit()
        return {"user_id": user_a.id, "partner_id": user_b.id, "pair_id": pair.id}


def test_daily_tasks_generates_tomorrow_layer_with_configured_count(monkeypatch):
    db_path = _db_path_for("planner-daily")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state: dict = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        state.update(
            await _seed_pair(
                sessionmaker,
                product_prefs={
                    "task_planner_defaults": {
                        "daily_ai_task_count": 4,
                        "reminder_enabled": True,
                        "reminder_time": "20:30",
                    }
                },
            )
        )

    asyncio.run(setup_database())
    call_count = {"value": 0}

    async def fake_strategy(*_args, **_kwargs):
        return {"intensity": "steady", "support_message": "明天先轻一点。"}, None

    async def fake_generate_pack(*_args, **kwargs):
        call_count["value"] += 1
        task_count = int(kwargs["effective_settings"]["daily_ai_task_count"])
        return {
            "tasks": [
                {
                    "title": f"明天安排{i + 1}",
                    "description": "做到一句话确认就好。",
                    "category": "connection",
                }
                for i in range(task_count)
            ],
            "daily_note": "明天先排好。",
            "planning_note": "明天已排好，可先调顺优先级。",
            "daily_pack_label": "明天轻安排",
            "date_scope": "tomorrow",
        }

    monkeypatch.setattr(tasks_api, "build_pair_task_adaptation", fake_strategy)
    monkeypatch.setattr(tasks_api, "generate_ai_task_pack", fake_generate_pack)
    async def fake_feedback_map(*_args, **_kwargs):
        return {}

    monkeypatch.setattr(tasks_api, "get_latest_task_feedback_map", fake_feedback_map)
    monkeypatch.setattr(tasks_api, "personalize_task_payloads", lambda payloads, _strategy: payloads)

    app = _make_app(sessionmaker, state)
    tomorrow = current_local_date() + timedelta(days=1)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(f"/tasks/daily/{state['pair_id']}?for_date={tomorrow}")
            second_response = client.get(f"/tasks/daily/{state['pair_id']}?for_date={tomorrow}")
            scope_response = client.get(
                f"/tasks/daily/{state['pair_id']}?date_scope=tomorrow"
            )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["date_scope"] == "tomorrow"
        assert payload["effective_settings"]["daily_ai_task_count"] == 4
        assert payload["planning_note"] == "明天已排好，可先调顺优先级。"
        assert len(payload["tasks"]) == 4
        assert second_response.status_code == 200
        assert scope_response.status_code == 200
        assert scope_response.json()["date_scope"] == "tomorrow"
        assert call_count["value"] == 1

        async def read_plan_view_keys():
            async with sessionmaker() as db:
                result = await db.execute(
                    select(RelationshipEvent.idempotency_key).where(
                        RelationshipEvent.event_type == "task.plan_viewed"
                    )
                )
                return [key for key in result.scalars().all() if key]

        idempotency_keys = asyncio.run(read_plan_view_keys())
        assert idempotency_keys
        assert all(len(key) <= 100 for key in idempotency_keys)
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_task_pack_ai_call_respects_page_budget(monkeypatch):
    async def fake_snapshot(*_args, **_kwargs):
        return None

    async def fake_status_lines(*_args, **_kwargs):
        return []

    async def slow_chat_completion(*_args, **_kwargs):
        await asyncio.sleep(0.05)
        return '{"daily_note":"不应等到","daily_pack_label":"慢响应","tasks":[]}'

    monkeypatch.setattr(planner_service, "_load_or_refresh_snapshot", fake_snapshot)
    monkeypatch.setattr(planner_service, "_build_recent_status_lines", fake_status_lines)
    monkeypatch.setattr(ai_module, "chat_completion", slow_chat_completion)
    monkeypatch.setattr(
        planner_service,
        "TASK_PLANNER_AI_TIMEOUT_SECONDS",
        0.001,
        raising=False,
    )

    with pytest.raises(planner_service.TaskPlannerError, match="planner ai call failed"):
        asyncio.run(
            planner_service.generate_ai_task_pack(
                object(),
                pair=SimpleNamespace(id=uuid.uuid4(), type=PairType.COUPLE),
                for_date=current_local_date() + timedelta(days=1),
                strategy={"intensity": "steady"},
                scorecard=None,
                effective_settings={
                    "daily_ai_task_count": 5,
                    "reminder_time": "21:00",
                },
            )
        )


def test_pair_task_settings_override_and_clear():
    db_path = _db_path_for("planner-settings")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state: dict = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        state.update(await _seed_pair(sessionmaker))

    asyncio.run(setup_database())
    app = _make_app(sessionmaker, state)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            patch_response = client.patch(
                f"/pairs/{state['pair_id']}/task-settings",
                json={
                    "daily_ai_task_count": 7,
                    "reminder_enabled": False,
                    "reminder_time": "19:45",
                },
            )
            reset_response = client.patch(
                f"/pairs/{state['pair_id']}/task-settings",
                json={
                    "daily_ai_task_count": None,
                    "reminder_enabled": None,
                    "reminder_time": None,
                },
            )

        assert patch_response.status_code == 200, patch_response.text
        assert patch_response.json()["effective_settings"]["daily_ai_task_count"] == 7
        assert patch_response.json()["effective_settings"]["reminder_enabled"] is False
        assert reset_response.status_code == 200, reset_response.text
        assert reset_response.json()["overrides"] == {
            "daily_ai_task_count": None,
            "reminder_enabled": None,
            "reminder_time": None,
            "reminder_timezone": None,
        }
        assert reset_response.json()["effective_settings"]["daily_ai_task_count"] == 5
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_task_refresh_rejects_manual_and_only_updates_target_system(monkeypatch):
    asyncio.run(close_request_cooldown_store())
    db_path = _db_path_for("planner-refresh")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state: dict = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        state.update(await _seed_pair(sessionmaker))
        async with sessionmaker() as db:
            today = current_local_date()
            system_a = RelationshipTask(
                pair_id=state["pair_id"],
                title="旧系统任务",
                description="旧说明",
                category="connection",
                due_date=today,
                source="system",
            )
            system_b = RelationshipTask(
                pair_id=state["pair_id"],
                title="保留系统任务",
                description="不应该变化",
                category="repair",
                due_date=today,
                source="system",
            )
            manual = RelationshipTask(
                pair_id=state["pair_id"],
                user_id=state["user_id"],
                created_by_user_id=state["user_id"],
                title="手动任务",
                description="不能刷新",
                category="activity",
                due_date=today,
                source="manual",
            )
            db.add_all([system_a, system_b, manual])
            await db.commit()
            state["system_a_id"] = system_a.id
            state["system_b_id"] = system_b.id
            state["manual_id"] = manual.id

    asyncio.run(setup_database())

    async def fake_strategy(*_args, **_kwargs):
        return {"intensity": "steady"}, None

    async def fake_refresh(*_args, **_kwargs):
        return {
            "title": "新系统任务",
            "description": "新的说明",
            "category": "communication",
        }

    monkeypatch.setattr(tasks_api, "build_pair_task_adaptation", fake_strategy)
    monkeypatch.setattr(tasks_api, "generate_ai_task_refresh", fake_refresh)

    app = _make_app(sessionmaker, state)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            manual_response = client.post(f"/tasks/{state['manual_id']}/refresh")
            system_response = client.post(f"/tasks/{state['system_a_id']}/refresh")

        assert manual_response.status_code == 400
        assert system_response.status_code == 200, system_response.text
        assert system_response.json()["task"]["title"] == "新系统任务"

        async def read_tasks():
            async with sessionmaker() as db:
                system_a = await db.get(RelationshipTask, state["system_a_id"])
                system_b = await db.get(RelationshipTask, state["system_b_id"])
                return system_a, system_b

        system_a, system_b = asyncio.run(read_tasks())
        assert system_a.title == "新系统任务"
        assert system_b.title == "保留系统任务"
    finally:
        asyncio.run(close_request_cooldown_store())
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_task_refresh_rate_limits_repeated_requests(monkeypatch):
    asyncio.run(close_request_cooldown_store())
    db_path = _db_path_for("planner-refresh-rate-limit")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state: dict = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        state.update(await _seed_pair(sessionmaker))
        async with sessionmaker() as db:
            today = current_local_date()
            system_task = RelationshipTask(
                pair_id=state["pair_id"],
                title="旧系统任务",
                description="旧说明",
                category="connection",
                due_date=today,
                source="system",
            )
            db.add(system_task)
            await db.commit()
            state["system_task_id"] = system_task.id

    asyncio.run(setup_database())

    async def fake_strategy(*_args, **_kwargs):
        return {"intensity": "steady"}, None

    async def fake_refresh(*_args, **_kwargs):
        return {
            "title": "新系统任务",
            "description": "新的说明",
            "category": "communication",
        }

    monkeypatch.setattr(tasks_api, "build_pair_task_adaptation", fake_strategy)
    monkeypatch.setattr(tasks_api, "generate_ai_task_refresh", fake_refresh)

    app = _make_app(sessionmaker, state)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            responses = [
                client.post(f"/tasks/{state['system_task_id']}/refresh")
                for _ in range(3)
            ]

        assert [response.status_code for response in responses[:2]] == [200, 200]
        assert responses[2].status_code == 429, responses[2].text
        assert "秒后再试" in responses[2].json()["detail"]
    finally:
        asyncio.run(close_request_cooldown_store())
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_manual_task_limit_and_system_importance_update(monkeypatch):
    db_path = _db_path_for("planner-manual-limit")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state: dict = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        state.update(await _seed_pair(sessionmaker))
        async with sessionmaker() as db:
            today = current_local_date()
            system_task = RelationshipTask(
                pair_id=state["pair_id"],
                title="系统任务",
                description="可以调重要度",
                category="connection",
                due_date=today,
                source="system",
            )
            db.add(system_task)
            for index in range(MAX_MANUAL_TASKS_PER_DATE):
                db.add(
                    RelationshipTask(
                        pair_id=state["pair_id"],
                        user_id=state["user_id"],
                        created_by_user_id=state["user_id"],
                        title=f"手动任务{index + 1}",
                        description="",
                        category="activity",
                        due_date=today,
                        source="manual",
                    )
                )
            await db.commit()
            state["system_task_id"] = system_task.id

    asyncio.run(setup_database())
    app = _make_app(sessionmaker, state)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            limit_response = client.post(
                f"/tasks/manual/{state['pair_id']}",
                json={
                    "title": "第 11 条",
                    "description": "",
                    "category": "activity",
                    "target_scope": "self",
                },
            )
            importance_response = client.patch(
                f"/tasks/{state['system_task_id']}",
                json={"importance_level": "high"},
            )
            complete_response = client.post(
                f"/tasks/{state['system_task_id']}/complete",
            )
            edit_system_response = client.patch(
                f"/tasks/{state['system_task_id']}",
                json={"title": "不允许改标题"},
            )

        assert limit_response.status_code == 400
        assert "最多" in limit_response.json()["detail"]
        assert importance_response.status_code == 200, importance_response.text
        assert importance_response.json()["task"]["importance_level"] == "high"
        assert complete_response.status_code == 200, complete_response.text
        assert complete_response.json()["task"]["importance_level"] == "high"
        assert edit_system_response.status_code == 400
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_reminder_cycle_generates_tomorrow_tasks_and_dedupes(monkeypatch):
    db_path = _db_path_for("planner-reminder")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state: dict = {}
    now = datetime(2026, 4, 24, 13, 0, tzinfo=timezone.utc)
    due_time = current_local_datetime(now).strftime("%H:%M")
    tomorrow = current_local_datetime(now).date() + timedelta(days=1)

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        state.update(
            await _seed_pair(
                sessionmaker,
                product_prefs={
                    "task_planner_defaults": {
                        "daily_ai_task_count": 3,
                        "reminder_enabled": True,
                        "reminder_time": due_time,
                    }
                },
            )
        )
        async with sessionmaker() as db:
            db.add(
                RelationshipEvent(
                    pair_id=state["pair_id"],
                    user_id=state["user_id"],
                    event_type="task.plan_viewed",
                    entity_type="daily_task_batch",
                    entity_id=f"{state['pair_id']}:{tomorrow.isoformat()}",
                    payload={"for_date": tomorrow.isoformat(), "layer": "tomorrow"},
                )
            )
            await db.commit()

    asyncio.run(setup_database())

    async def fake_strategy(*_args, **_kwargs):
        return {"intensity": "steady"}, None

    async def fake_pack(*_args, **_kwargs):
        return {
            "tasks": [
                {
                    "title": f"提醒安排{index + 1}",
                    "description": "提醒生成的任务。",
                    "category": "connection",
                }
                for index in range(3)
            ],
            "daily_note": "明天先排好。",
            "planning_note": "明天安排已排好。",
            "daily_pack_label": "提醒预排",
        }

    monkeypatch.setattr(planner_service, "async_session", sessionmaker)
    monkeypatch.setattr(task_adaptation, "build_pair_task_adaptation", fake_strategy)
    monkeypatch.setattr(planner_service, "generate_ai_task_pack", fake_pack)

    try:
        first = asyncio.run(planner_service.run_task_planner_reminder_cycle(now=now))
        second = asyncio.run(planner_service.run_task_planner_reminder_cycle(now=now))

        async def read_counts():
            async with sessionmaker() as db:
                task_result = await db.execute(select(RelationshipTask))
                notification_result = await db.execute(select(UserNotification))
                return (
                    len(task_result.scalars().all()),
                    len(notification_result.scalars().all()),
                )

        task_count, notification_count = asyncio.run(read_counts())
        assert first == {"reminded_users": 1, "reminded_pairs": 1}
        assert second == {"reminded_users": 0, "reminded_pairs": 0}
        assert task_count == 3
        assert notification_count == 1
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_effective_settings_pair_override_wins_over_user_defaults():
    effective = resolve_effective_task_planner_settings(
        {"task_planner_defaults": {"daily_ai_task_count": 4, "reminder_time": "20:00"}},
        {"daily_ai_task_count": 8, "reminder_enabled": False},
    )

    assert effective["daily_ai_task_count"] == 8
    assert effective["reminder_enabled"] is False
    assert effective["reminder_time"] == "20:00"
