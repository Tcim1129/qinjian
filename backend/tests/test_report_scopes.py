from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import reports as reports_api
from app.core.database import Base
from app.models import (
    Pair,
    PairStatus,
    PairType,
    RelationshipProfileSnapshot,
    Report,
    ReportStatus,
    ReportType,
    User,
)


def _build_test_app(sessionmaker, user_id):
    async def override_get_db():
        async with sessionmaker() as db:
            yield db

    async def override_current_user():
        async with sessionmaker() as db:
            return await db.get(User, user_id)

    app = FastAPI()
    app.include_router(reports_api.router)
    app.dependency_overrides[reports_api.get_db] = override_get_db
    app.dependency_overrides[reports_api.get_current_user] = override_current_user
    return app


def test_report_scopes_sorts_active_pairs_and_refreshes_missing_snapshots(monkeypatch):
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"report-scopes-{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state: dict[str, object] = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            viewer = User(
                email="viewer@example.com",
                nickname="Viewer",
                password_hash="not-used",
            )
            partner_a = User(
                email="partner-a@example.com",
                nickname="林夏",
                password_hash="not-used",
            )
            partner_b = User(
                email="partner-b@example.com",
                nickname="周宁",
                password_hash="not-used",
            )
            db.add_all([viewer, partner_a, partner_b])
            await db.flush()

            pair_a = Pair(
                user_a_id=viewer.id,
                user_b_id=partner_a.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="A3H7K8M9Q2",
                custom_partner_nickname_a="小夏",
                created_at=datetime(2026, 4, 10, 9, 0, 0),
            )
            pair_b = Pair(
                user_a_id=viewer.id,
                user_b_id=partner_b.id,
                type=PairType.FRIEND,
                status=PairStatus.ACTIVE,
                invite_code="B4J8L9N2P3",
                created_at=datetime(2026, 4, 12, 9, 0, 0),
            )
            db.add_all([pair_a, pair_b])
            await db.flush()

            db.add(
                RelationshipProfileSnapshot(
                    pair_id=pair_a.id,
                    user_id=None,
                    window_days=7,
                    snapshot_date=date(2026, 4, 22),
                    metrics_json={
                        "checkin_count": 12,
                        "interaction_overlap_rate": 0.85,
                        "report_health_avg": 74,
                    },
                    risk_summary={"current_level": "none", "trend": "stable"},
                    attachment_summary={"attachment_a": "unknown", "attachment_b": "unknown"},
                    suggested_focus={"items": []},
                    behavior_summary={},
                    generated_from_event_at=datetime(2026, 4, 22, 8, 30, 0),
                )
            )
            db.add_all(
                [
                    Report(
                        pair_id=pair_a.id,
                        type=ReportType.DAILY,
                        status=ReportStatus.COMPLETED,
                        content={"insight": "双方最近都还在回应。"},
                        health_score=82,
                        report_date=date(2026, 4, 20),
                        created_at=datetime(2026, 4, 20, 21, 0, 0),
                    ),
                    Report(
                        pair_id=pair_b.id,
                        type=ReportType.DAILY,
                        status=ReportStatus.COMPLETED,
                        content={"insight": "最近也有记录。"},
                        health_score=68,
                        report_date=date(2026, 4, 21),
                        created_at=datetime(2026, 4, 21, 21, 0, 0),
                    ),
                ]
            )
            await db.commit()

            state["user_id"] = viewer.id
            state["pair_a_id"] = pair_a.id
            state["pair_b_id"] = pair_b.id

    asyncio.run(setup_database())

    refresh_calls: list[str] = []

    async def fake_refresh_profile_snapshot(db, *, pair_id=None, user_id=None, window_days=7, snapshot_date=None, version="v1"):
        assert user_id is None
        assert window_days == 7
        refresh_calls.append(str(pair_id))
        snapshot = RelationshipProfileSnapshot(
            pair_id=pair_id,
            user_id=None,
            window_days=7,
            snapshot_date=date(2026, 4, 23),
            metrics_json={
                "checkin_count": 8,
                "interaction_overlap_rate": 0.60,
                "report_health_avg": 65,
            },
            risk_summary={"current_level": "none", "trend": "watch"},
            attachment_summary={"attachment_a": "unknown", "attachment_b": "unknown"},
            suggested_focus={"items": []},
            behavior_summary={},
            generated_from_event_at=datetime(2026, 4, 23, 8, 0, 0),
            version=version,
        )
        db.add(snapshot)
        await db.flush()
        return snapshot

    monkeypatch.setattr(reports_api, "refresh_profile_snapshot", fake_refresh_profile_snapshot)

    app = _build_test_app(sessionmaker, state["user_id"])

    try:
      with TestClient(app, raise_server_exceptions=False) as client:
          response = client.get("/reports/scopes?report_type=daily")

      assert response.status_code == 200, response.text
      payload = response.json()

      assert [item["pair_id"] for item in payload] == [
          str(state["pair_a_id"]),
          str(state["pair_b_id"]),
      ]
      assert refresh_calls == [str(state["pair_b_id"])]

      assert payload[0]["partner_label"] == "小夏"
      assert payload[0]["sort_score"] == 85
      assert payload[0]["activity_score"] == 86
      assert payload[0]["dual_activity_score"] == 85
      assert payload[0]["health_score"] == 82
      assert payload[0]["reason_tags"] == ["双方最近都活跃", "近期分数较高", "最近有记录"]

      assert payload[1]["partner_label"] == "周宁"
      assert payload[1]["sort_score"] == 61
      assert payload[1]["activity_score"] == 57
      assert payload[1]["dual_activity_score"] == 60
      assert payload[1]["health_score"] == 68
      assert payload[1]["reason_tags"] == ["双方最近都活跃", "最近有记录"]
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)


def test_report_endpoints_normalize_ab_copy_for_viewer_and_partner(monkeypatch):
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"report-normalize-{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    state: dict[str, object] = {}

    async def setup_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            viewer = User(
                email="viewer-b@example.com",
                nickname="Viewer B",
                password_hash="not-used",
            )
            partner = User(
                email="partner-c@example.com",
                nickname="林夏",
                password_hash="not-used",
            )
            db.add_all([viewer, partner])
            await db.flush()

            pair = Pair(
                user_a_id=viewer.id,
                user_b_id=partner.id,
                type=PairType.COUPLE,
                status=PairStatus.ACTIVE,
                invite_code="C5K9M2Q4R7",
                custom_partner_nickname_a="小夏",
                created_at=datetime(2026, 4, 10, 9, 0, 0),
            )
            db.add(pair)
            await db.flush()

            report = Report(
                pair_id=pair.id,
                type=ReportType.DAILY,
                status=ReportStatus.COMPLETED,
                content={
                    "insight": "A方想靠近，B方也没退出。",
                    "highlights": ["A方与B方都还在回应"],
                    "concerns": ["B方比A方更需要空间"],
                },
                health_score=73,
                report_date=date(2026, 4, 22),
                created_at=datetime(2026, 4, 22, 21, 0, 0),
            )
            db.add(report)
            await db.commit()

            state["user_id"] = viewer.id
            state["pair_id"] = pair.id

    asyncio.run(setup_database())

    async def fake_build_safety_status(*_args, **_kwargs):
        return {
            "evidence_summary": ["A方和B方都还在回应"],
            "limitation_note": "A方先别急着追问B方",
            "handoff_recommendation": "先听听B方真正担心什么",
        }

    monkeypatch.setattr(reports_api, "build_safety_status", fake_build_safety_status)

    app = _build_test_app(sessionmaker, state["user_id"])

    try:
      with TestClient(app, raise_server_exceptions=False) as client:
          latest_response = client.get(
              f"/reports/latest?pair_id={state['pair_id']}&report_type=daily"
          )
          history_response = client.get(
              f"/reports/history?pair_id={state['pair_id']}&report_type=daily"
          )

      assert latest_response.status_code == 200, latest_response.text
      latest_payload = latest_response.json()

      assert latest_payload["content"]["insight"] == "你想靠近，小夏也没退出。"
      assert latest_payload["content"]["highlights"][0] == "双方都还在回应"
      assert latest_payload["content"]["concerns"][0] == "小夏比你更需要空间"
      assert latest_payload["evidence_summary"] == ["双方都还在回应"]
      assert latest_payload["limitation_note"] == "你先别急着追问小夏"
      assert latest_payload["safety_handoff"] == "先听听小夏真正担心什么"
      assert "A方" not in latest_response.text
      assert "B方" not in latest_response.text

      assert history_response.status_code == 200, history_response.text
      history_payload = history_response.json()
      assert history_payload[0]["content"]["insight"] == "你想靠近，小夏也没退出。"
      assert history_payload[0]["content"]["highlights"][0] == "双方都还在回应"
      assert history_payload[0]["content"]["concerns"][0] == "小夏比你更需要空间"
      assert "A方" not in history_response.text
      assert "B方" not in history_response.text
    finally:
        asyncio.run(engine.dispose())
        db_path.unlink(missing_ok=True)
