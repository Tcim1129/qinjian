from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai import multi_agent, narrative_alignment
from app.api.v1 import agent as agent_api
from app.api.v1 import reports as reports_api
from app.api.v1 import tasks as tasks_api
from app.api.v1.insights_routes import alignment as alignment_api
from app.api.v1.insights_routes import assessments as assessments_api
from app.api.v1.insights_routes import shared as timeline_shared
from app.api.v1.insights_routes import timeline as timeline_api
from app.core.database import Base
from app.core.time import current_local_date
from app.models import (
    Checkin,
    CrisisAlert,
    CrisisAlertStatus,
    CrisisLevel,
    Pair,
    PairStatus,
    PairType,
    RelationshipEvent,
    RelationshipTask,
    Report,
    ReportStatus,
    ReportType,
    TaskStatus,
    User,
)
from app.services.assessment_item_bank import build_weekly_assessment_pack
from app.services.checkin_visibility import change_visibility
from app.services.privacy_audit import get_privacy_audit_context
from app.services.request_cooldown_store import close_request_cooldown_store


def _db_file(name: str) -> Path:
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    return db_dir / f"{name}-{uuid.uuid4().hex}.db"


# QJ-01: 撤回摘要导致旧日报失效，在存在 CrisisAlert 外键引用时恢复分享并重建日报不应 500
def test_qj01_revoke_restore_and_regenerate_daily_report_with_crisis_alert_fk(monkeypatch):
    db_path = _db_file("qj01-report-fk")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    @event.listens_for(engine.sync_engine, "connect")
    def enforce_fk(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    ids: dict[str, uuid.UUID] = {}

    async def seed():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as db:
            today = current_local_date()
            user_a = User(email="qj01-a@example.com", nickname="林知夏", password_hash="x")
            user_b = User(email="qj01-b@example.com", nickname="陈屿", password_hash="x")
            db.add_all([user_a, user_b])
            await db.flush()
            pair = Pair(
                user_a_id=user_a.id,
                user_b_id=user_b.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="QJ01FK1234",
            )
            db.add(pair)
            await db.flush()
            checkin_a = Checkin(
                pair_id=pair.id,
                user_id=user_a.id,
                content="今天有点忙，但还是想好好聊一聊。",
                checkin_date=today,
                visibility_scope="shared_summary",
                visibility_version=1,
            )
            checkin_b = Checkin(
                pair_id=pair.id,
                user_id=user_b.id,
                content="加班结束很累，想早点休息。",
                checkin_date=today,
                visibility_scope="shared_summary",
                visibility_version=1,
            )
            report = Report(
                pair_id=pair.id,
                type=ReportType.DAILY,
                status=ReportStatus.COMPLETED,
                content={"health_score": 58, "insight": "原日报内容"},
                health_score=58.0,
                report_date=today,
            )
            db.add_all([checkin_a, checkin_b, report])
            await db.flush()
            alert = CrisisAlert(
                pair_id=pair.id,
                report_id=report.id,
                level=CrisisLevel.MILD,
                status=CrisisAlertStatus.ACTIVE,
            )
            db.add(alert)
            await db.commit()
            ids.update(
                user_a=user_a.id,
                user_b=user_b.id,
                pair=pair.id,
                checkin_b=checkin_b.id,
                report=report.id,
                alert=alert.id,
            )

    asyncio.run(seed())

    async def revoke_and_restore():
        async with session_factory() as db:
            revoked = await change_visibility(
                db,
                record_id=ids["checkin_b"],
                actor_user_id=ids["user_b"],
                expected_version="1",
                target_scope="private",
            )
            assert revoked["reports_invalidated"] == 1
            restored = await change_visibility(
                db,
                record_id=ids["checkin_b"],
                actor_user_id=ids["user_b"],
                expected_version=revoked["version"],
                target_scope="shared_summary",
                sharing_confirmed=True,
            )
            assert restored["sharing_active"] is True
            await db.commit()

    asyncio.run(revoke_and_restore())

    async def override_get_db():
        async with session_factory() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def override_current_user():
        async with session_factory() as db:
            return await db.get(User, ids["user_a"])

    async def fake_generate_daily_report(**_kwargs):
        return {
            "health_score": 72,
            "insight": "恢复分享后的新日报结论。",
            "suggestion": "睡前留出十分钟对齐近况。",
            "crisis_level": "none",
        }

    monkeypatch.setattr(reports_api, "async_session", session_factory)
    monkeypatch.setattr(reports_api, "generate_daily_report", fake_generate_daily_report)

    app = FastAPI()
    app.include_router(reports_api.router)
    app.dependency_overrides[reports_api.get_db] = override_get_db
    app.dependency_overrides[reports_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(f"/reports/generate-daily?pair_id={ids['pair']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == str(ids["report"])

        async def verify():
            async with session_factory() as db:
                refreshed = await db.get(Report, ids["report"])
                alert = await db.get(CrisisAlert, ids["alert"])
                assert refreshed is not None
                assert refreshed.status == ReportStatus.COMPLETED
                assert refreshed.health_score == 72.0
                assert alert is not None
                assert alert.report_id == refreshed.id

        asyncio.run(verify())
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


# QJ-03: 双视角放宽超时窗口、跳过重复上下文包并传递快速交互截止时间
def test_qj03_alignment_uses_expanded_timeout_and_fast_budget(monkeypatch):
    assert narrative_alignment.ALIGNMENT_TIMEOUT_SECONDS >= 40
    captured = {}

    async def fake_chat_completion(model, messages, **kwargs):
        captured["model"] = model
        captured["kwargs"] = kwargs
        return """{
          "alignment_score": 80,
          "shared_story": "双方都提到最近工作忙、沟通少。",
          "view_a_summary": "希望下班后有十分钟连线。",
          "view_b_summary": "加班后精力有限。",
          "misread_risk": "疲惫沉默容易被当成疏远。",
          "divergence_points": ["联系时机不同"],
          "bridge_actions": ["提前约定通话时长"],
          "suggested_opening": "今天忙完后我们留十分钟随便聊聊？",
          "coach_note": "先照顾彼此精力，再谈安排。"
        }"""

    monkeypatch.setattr(narrative_alignment, "chat_completion", fake_chat_completion)
    result = asyncio.run(
        narrative_alignment.generate_narrative_alignment(
            context={"pair_type": "couple"},
            checkin_a={"content": "今天想聊十分钟"},
            checkin_b={"content": "今天加班很累"},
        )
    )
    assert result["is_fallback"] is False
    assert captured["kwargs"]["context_enabled"] is False
    assert captured["kwargs"]["request_timeout_seconds"] >= 25.0


def test_qj03_alignment_route_sets_chat_deadline_in_audit_scope(monkeypatch):
    asyncio.run(close_request_cooldown_store())
    db_path = _db_file("qj03-align-deadline")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    ids: dict[str, uuid.UUID] = {}
    observed = {}

    async def seed():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as db:
            today = current_local_date()
            ua = User(email="qj03-a@example.com", nickname="林知夏", password_hash="x")
            ub = User(email="qj03-b@example.com", nickname="陈屿", password_hash="x")
            db.add_all([ua, ub])
            await db.flush()
            pair = Pair(
                user_a_id=ua.id,
                user_b_id=ub.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="QJ03DL1234",
            )
            db.add(pair)
            await db.flush()
            db.add_all([
                Checkin(pair_id=pair.id, user_id=ua.id, content="想聊聊", checkin_date=today),
                Checkin(pair_id=pair.id, user_id=ub.id, content="有点累", checkin_date=today),
            ])
            await db.commit()
            ids.update(user=ua.id, pair=pair.id)

    asyncio.run(seed())

    async def override_get_db():
        async with session_factory() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def override_current_user():
        async with session_factory() as db:
            return await db.get(User, ids["user"])

    async def fake_generate_alignment(**_kwargs):
        observed["chat_deadline"] = get_privacy_audit_context().get("chat_deadline")
        return {
            "alignment_score": 78,
            "shared_story": "都在意沟通节奏。",
            "view_a_summary": "想被回应。",
            "view_b_summary": "需要先缓一下。",
            "misread_risk": "容易误解沉默。",
            "divergence_points": ["节奏不同"],
            "bridge_actions": ["提前说明时间"],
            "suggested_opening": "今晚十点聊十分钟好不好？",
            "coach_note": "先对齐节奏。",
            "source": "ai",
            "is_fallback": False,
        }

    monkeypatch.setattr(alignment_api, "generate_narrative_alignment", fake_generate_alignment)
    app = FastAPI()
    app.include_router(alignment_api.router)
    app.dependency_overrides[alignment_api.get_db] = override_get_db
    app.dependency_overrides[alignment_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(f"/alignment/generate?pair_id={ids['pair']}&force=true")
        assert resp.status_code == 200, resp.text
        assert observed.get("chat_deadline") is not None
    finally:
        asyncio.run(close_request_cooldown_store())
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


# QJ-04: 多智能体不重复分配 create_task，且近似候选任务合并去重
def test_qj04_companion_role_does_not_duplicate_create_task_and_proposals_dedupe():
    assert "create_task" in multi_agent.ACTION_TOOLS
    assert "create_task" not in multi_agent.COMPANION_TOOLS

    steps = [
        SimpleNamespace(
            tool_results=[
                {
                    "name": "create_task",
                    "result": {
                        "status": "success",
                        "data": {
                            "proposal_id": "p1",
                            "requires_confirmation": True,
                            "title": "今晚留十分钟聊近况",
                            "description": "放下手机聊十分钟彼此最近的状态",
                            "due_date": "2026-11-25",
                        },
                    },
                },
                {
                    "name": "create_task",
                    "result": {
                        "status": "success",
                        "data": {
                            "proposal_id": "p2",
                            "requires_confirmation": True,
                            "title": "定一件家务分工",
                            "description": "一起敲定本周谁负责洗碗",
                            "due_date": "2026-11-25",
                        },
                    },
                },
            ]
        ),
        SimpleNamespace(
            tool_results=[
                {
                    "name": "create_task",
                    "result": {
                        "status": "success",
                        "data": {
                            "proposal_id": "p3",
                            "requires_confirmation": True,
                            "title": "睡前留 10 分钟聊近况",
                            "description": "睡前专心听对方说十分钟近况",
                            "due_date": "2026-11-25",
                        },
                    },
                },
                {
                    "name": "create_task",
                    "result": {
                        "status": "success",
                        "data": {
                            "proposal_id": "p4",
                            "requires_confirmation": True,
                            "title": "一起定一件家务分工",
                            "description": "明确一件双方本周要做的家务",
                            "due_date": "2026-11-25",
                        },
                    },
                },
            ]
        ),
    ]
    deduped = agent_api._task_proposals_from_steps(steps)
    assert len(deduped) == 2
    assert [item["proposal_id"] for item in deduped] == ["p3", "p4"]


# QJ-06: 关系体检换一组题返回不同轮换题目
@pytest.mark.anyio
async def test_qj06_weekly_assessment_pack_rotates_items_when_excluding_current():
    class EmptySession:
        async def execute(self, *_args, **_kwargs):
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))

        async def get(self, _model, _pk):
            return SimpleNamespace(type=PairType.COUPLE, is_long_distance=False)

    pair_id = uuid.uuid4()
    first = await build_weekly_assessment_pack(EmptySession(), pair_id=pair_id)
    first_rotation = [item["item_id"] for item in first["items"] if item["track"] == "rotation"]
    assert len(first_rotation) == 4

    second = await build_weekly_assessment_pack(
        EmptySession(),
        pair_id=pair_id,
        exclude_item_ids=first_rotation,
        variant=1,
    )
    second_rotation = [item["item_id"] for item in second["items"] if item["track"] == "rotation"]
    assert len(second_rotation) == 4
    assert set(first_rotation).isdisjoint(set(second_rotation))

    third = await build_weekly_assessment_pack(
        EmptySession(),
        pair_id=pair_id,
        exclude_item_ids=second_rotation,
        variant=2,
    )
    third_rotation = [item["item_id"] for item in third["items"] if item["track"] == "rotation"]
    assert set(second_rotation).isdisjoint(set(third_rotation))


# QJ-07: 双方记录不足 5 条时，依恋分析必须如实返回 insufficient_data 和原因，不冒充分析成功
def test_qj07_pair_attachment_reports_insufficient_data_honestly(monkeypatch):
    asyncio.run(close_request_cooldown_store())
    db_path = _db_file("qj07-attachment-honest")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    ids: dict[str, uuid.UUID] = {}

    async def seed():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as db:
            ua = User(email="qj07-a@example.com", nickname="林知夏", password_hash="x")
            ub = User(email="qj07-b@example.com", nickname="陈屿", password_hash="x")
            db.add_all([ua, ub])
            await db.flush()
            pair = Pair(
                user_a_id=ua.id,
                user_b_id=ub.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="QJ07AT1234",
            )
            db.add(pair)
            await db.flush()
            db.add(
                Checkin(
                    pair_id=pair.id,
                    user_id=ua.id,
                    content="只有一条共享记录。",
                    checkin_date=current_local_date(),
                    visibility_scope="shared_summary",
                )
            )
            await db.commit()
            ids.update(user=ua.id, pair=pair.id)

    asyncio.run(seed())

    async def override_get_db():
        async with session_factory() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def override_current_user():
        async with session_factory() as db:
            return await db.get(User, ids["user"])

    monkeypatch.setattr(tasks_api, "is_relaxed_test_account", lambda _u: False)
    app = FastAPI()
    app.include_router(tasks_api.router)
    app.dependency_overrides[tasks_api.get_db] = override_get_db
    app.dependency_overrides[tasks_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(f"/tasks/attachment/{ids['pair']}/analyze")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["analysis_status"] == "insufficient_data"
        assert data["my_attachment"]["type"] == "unknown"
        assert data["partner_attachment"]["type"] == "unknown"
        assert data["analyzed_at"] is None
        assert "不足 5 条" in data["message"]
        assert "已共享 1 条" in data["reason"]
        assert data["sample_counts"] == {"my": 1, "partner": 0, "required": 5}
    finally:
        asyncio.run(close_request_cooldown_store())
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


# QJ-08: 关系日历列表与详情不再向普通用户暴露内部英文编码和算法版本号
@pytest.mark.anyio
async def test_qj08_timeline_list_and_detail_hide_internal_codes():
    events = [
        RelationshipEvent(
            id=uuid.uuid4(),
            event_type="alignment.generated",
            entity_type="narrative_alignment",
            source="system",
            occurred_at=datetime(2026, 11, 25, 8, 30, 0),
            payload={
                "alignment_score": 73,
                "history_sufficiency": "insufficient",
                "algorithm_version": "relationship_judgement_v2",
                "reaction_shift": "unknown",
                "risk_level": "none",
            },
        ),
        RelationshipEvent(
            id=uuid.uuid4(),
            event_type="report.completed",
            entity_type="report",
            source="system",
            occurred_at=datetime(2026, 11, 25, 8, 20, 0),
            payload={"report_type": "daily", "health_score": 68, "level": "mild"},
        ),
        RelationshipEvent(
            id=uuid.uuid4(),
            event_type="task.completed",
            entity_type="relationship_task",
            source="user",
            occurred_at=datetime(2026, 11, 25, 8, 10, 0),
            payload={"title": "聊十分钟", "category": "connection"},
        ),
        RelationshipEvent(
            id=uuid.uuid4(),
            event_type="assessment.weekly_submitted",
            entity_type="weekly_assessment",
            source="system",
            occurred_at=datetime(2026, 11, 25, 8, 5, 0),
            payload={"total_score": 80},
        ),
        RelationshipEvent(
            id=uuid.uuid4(),
            event_type="attachment.analyzed",
            entity_type="attachment_style",
            source="system",
            occurred_at=datetime(2026, 11, 25, 8, 0, 0),
            payload={},
        ),
    ]

    forbidden = [
        "insufficient",
        "none",
        "unknown",
        "connection",
        "daily",
        "mild",
        "relationship_judgement_v2",
        "assessment /",
        "attachment /",
    ]
    for ev in events:
        serialized = timeline_shared.serialize_timeline_event(ev)
        visible_text = " ".join([
            str(serialized.get("label") or ""),
            str(serialized.get("summary") or ""),
            str(serialized.get("detail") or ""),
            " ".join(serialized.get("tags") or []),
        ]).lower()
        for token in forbidden:
            assert token not in visible_text, f"{ev.event_type} leaked {token!r} in {visible_text!r}"

    assert timeline_shared.timeline_event_label("attachment.analyzed") == "依恋倾向分析已更新"
    assert timeline_shared.timeline_event_label("assessment.weekly_submitted") == "完成了一次关系体检"
    assert timeline_shared.timeline_source_label("system") == "系统记录"
