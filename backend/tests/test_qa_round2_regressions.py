import asyncio
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai import multi_agent
from app.api.v1 import agent as agent_api
from app.api.v1.insights_routes.shared import serialize_timeline_event
from app.api.v1.insights_routes.timeline import build_timeline_event_detail
from app.core.database import Base
from app.models import AgentChatSession, RelationshipEvent, User
from app.services.weekly_assessments import submit_weekly_assessment


def _db_file(prefix: str) -> Path:
    return Path(tempfile.gettempdir()) / f"{prefix}-{uuid.uuid4().hex[:8]}.db"


# BUG-03: 多智能体第 4 角色“陪伴”摘要不再在 80 字符处生硬截断
def test_bug03_multi_agent_companion_summary_is_not_truncated(monkeypatch):
    long_companion_reply = (
        "我听见你这几天其实一直挺在意他的回应，也憋了不少委屈。"
        "现在先别急着把所有情绪一口气摊开，可以先选一个轻松一点的空档，"
        "把你最想被照顾到的那一点温和地说出来。顺便问一句，你们这周末怎么安排会更舒服一些？"
    )
    assert len(long_companion_reply) > 80

    async def fake_memory_control(**_kwargs):
        return None

    async def fake_run_agent_loop(*, messages, allowed_tool_names=None, include_checkin_tool=True, **_kwargs):
        if include_checkin_tool:
            return long_companion_reply, [], False
        return "阶段观察已完成。", [], False

    monkeypatch.setattr(multi_agent, "handle_memory_control_turn", fake_memory_control)
    monkeypatch.setattr(multi_agent, "run_agent_loop", fake_run_agent_loop)

    final_reply, _steps, swarm, _extracted = asyncio.run(
        multi_agent.run_multi_agent_flow(
            messages=[{"role": "user", "content": "最近总觉得他回复变慢了，心里有点难受"}],
            user_id=str(uuid.uuid4()),
        )
    )

    companion_step = next(step for step in swarm if step.role == "companion")
    assert final_reply == long_companion_reply
    assert companion_step.summary == long_companion_reply
    assert companion_step.summary.endswith("周末怎么安排会更舒服一些？")


# BUG-04: 关系体检综合分与五维雷达均值保持同一口径（五维均衡汇总）
def test_bug04_weekly_assessment_total_score_matches_five_dimension_average():
    db_path = _db_file("bug04-weekly-score")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def run_check():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as db:
            user = User(email="bug04-score@example.com", nickname="体检测试", password_hash="x")
            db.add(user)
            await db.flush()

            # 模拟 10 题不均匀分布：connection(50,75->62)、trust(75,75->75)、
            # repair(75,75->75)、shared_future(100->100)、vitality(75,75,75->75)
            # 旧口径按 10 题均值 = 75，五维均值 = (62+75+75+100+75)/5 = 77.4 -> 77
            answers = [
                {"item_id": "c1", "dim": "connection", "score": 50},
                {"item_id": "c2", "dim": "connection", "score": 75},
                {"item_id": "t1", "dim": "trust", "score": 75},
                {"item_id": "t2", "dim": "trust", "score": 75},
                {"item_id": "r1", "dim": "repair", "score": 75},
                {"item_id": "r2", "dim": "repair", "score": 75},
                {"item_id": "f1", "dim": "shared_future", "score": 100},
                {"item_id": "v1", "dim": "vitality", "score": 75},
                {"item_id": "v2", "dim": "vitality", "score": 75},
                {"item_id": "v3", "dim": "vitality", "score": 75},
            ]
            point = await submit_weekly_assessment(db, user_id=user.id, answers=answers)
            dim_scores = [item["score"] for item in point["dimension_scores"] if item["score"] is not None]
            radar_average = round(sum(dim_scores) / len(dim_scores))
            assert dim_scores == [62, 75, 75, 100, 75]
            assert point["total_score"] == radar_average == 77

    try:
        asyncio.run(run_check())
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


# BUG-05: 主动巡查文案映射为自然中文风险等级，不暴露原始英文「low」
@pytest.mark.parametrize("coded_recommendation", [False, True])
def test_bug05_active_checkup_maps_risk_level_to_chinese(monkeypatch, coded_recommendation):
    db_path = _db_file("bug05-checkup")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    ids: dict[str, uuid.UUID] = {}

    async def seed():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as db:
            user = User(email="bug05@example.com", nickname="巡查测试", password_hash="x")
            db.add(user)
            await db.flush()
            session = AgentChatSession(user_id=user.id, pair_id=None)
            db.add(session)
            await db.commit()
            ids.update(user=user.id, session=session.id)

    asyncio.run(seed())

    async def override_get_db():
        async with session_factory() as db:
            yield db

    async def override_current_user():
        async with session_factory() as db:
            return await db.get(User, ids["user"])

    async def fake_safety_status(**_kwargs):
        return {"health_score": 82}

    async def fake_intervention_eval(**_kwargs):
        if coded_recommendation:
            return {
                "recommendation": "collect_more_data",
                "recommendation_label": "继续观察并补数据",
                "recommendation_reason": "双方最近的记录还不够。",
            }
        return {"reason": "", "recommendation": "继续保持轻松自然的记录节奏。"}

    async def fake_crisis_status(**_kwargs):
        return {"highest_level": "low"}

    async def fake_active_tasks(**_kwargs):
        return []

    import app.services.safety_summary as safety_summary
    import app.services.intervention_evaluation as intervention_eval
    import app.ai.tools as ai_tools

    monkeypatch.setattr(safety_summary, "build_safety_status", fake_safety_status)
    monkeypatch.setattr(intervention_eval, "build_intervention_evaluation", fake_intervention_eval)
    monkeypatch.setattr(ai_tools, "_get_crisis_status", fake_crisis_status)
    monkeypatch.setattr(ai_tools, "_get_active_tasks", fake_active_tasks)

    app = FastAPI()
    app.include_router(agent_api.router)
    app.dependency_overrides[agent_api.get_db] = override_get_db
    app.dependency_overrides[agent_api.get_current_user] = override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(f"/agent/sessions/{ids['session']}/checkup")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "low" not in body["report"].lower()
        assert "「" not in body["report"]
        assert "低风险（整体平稳）" in body["report"]
        if coded_recommendation:
            assert "collect_more_data" not in body["report"]
            assert "继续观察并补数据" in body["report"]
            assert "双方最近的记录还不够。" in body["report"]
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


# BUG-06: 关系日历中的体检事件不暴露 assessment / weekly submitted / none 等原始英文
def test_bug06_timeline_assessment_events_render_chinese_without_none():
    db_path = _db_file("bug06-timeline")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def run_check():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as db:
            user = User(email="bug06@example.com", nickname="日历测试", password_hash="x")
            db.add(user)
            await db.flush()

            submitted_event = RelationshipEvent(
                id=uuid.uuid4(),
                user_id=user.id,
                pair_id=None,
                event_type="assessment.weekly_submitted",
                entity_type="weekly_assessment",
                source="system",
                occurred_at=datetime(2026, 11, 25, 10, 0, 0),
                payload={
                    "scope": "solo",
                    "total_score": 77,
                    "risk_level": "none",
                    "change_summary": "这是你的第一次周评估，下次填写后可以对比变化。",
                    "dimension_scores": [
                        {"id": "connection", "label": "连接与表达", "score": 62},
                        {"id": "trust", "label": "信任与安全", "score": 75},
                        {"id": "repair", "label": "修复能力", "score": 75},
                        {"id": "shared_future", "label": "共同愿景", "score": 100},
                        {"id": "vitality", "label": "关系活力", "score": 75},
                    ],
                },
            )
            stable_event = RelationshipEvent(
                id=uuid.uuid4(),
                user_id=user.id,
                pair_id=None,
                event_type="assessment.weekly_stable_band_detected",
                entity_type="weekly_assessment_profile_signal",
                source="system",
                occurred_at=datetime(2026, 11, 25, 10, 1, 0),
                payload={
                    "summary": "最近两次关系体检总分接近，可以先看看得分最低的项目。",
                    "risk_level": "none",
                },
            )

            serialized_submitted = serialize_timeline_event(submitted_event)
            serialized_stable = serialize_timeline_event(stable_event)

            for serialized in (serialized_submitted, serialized_stable):
                assert serialized["category_label"] == "体检"
                joined = " ".join(
                    [
                        str(serialized["label"]),
                        str(serialized["summary"]),
                        str(serialized["detail"] or ""),
                        *serialized["tags"],
                    ]
                ).lower()
                assert "assessment" not in joined
                assert "weekly submitted" not in joined
                assert "none" not in joined

            detail = await build_timeline_event_detail(db, submitted_event, viewer=user)
            metric_labels = [getattr(m, "label", m["label"] if isinstance(m, dict) else "") for m in detail["metrics"]]
            card_titles = [getattr(c, "title", c["title"] if isinstance(c, dict) else "") for c in detail["evidence_cards"]]
            assert "体检范围" in metric_labels
            assert "综合分" in metric_labels
            assert "连接与表达" in metric_labels
            assert "变化说明" in card_titles

    try:
        asyncio.run(run_check())
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
