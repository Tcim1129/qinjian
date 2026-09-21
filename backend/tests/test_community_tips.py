import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import community as community_api
from app.api.v1.community import (
    _compact_title,
    _fallback_tip,
    _parse_tip_response,
    _report_hint,
)
from app.core.database import Base
from app.core.time import current_local_date
from app.models import Pair, PairStatus, PairType, RelationshipProfileSnapshot, User
from app.services.relationship_intelligence import refresh_profile_snapshot
from app.services.request_cooldown_store import close_request_cooldown_store


def test_compact_title_trims_and_limits_to_15_chars():
    title = _compact_title("  明天 先给对方发一句真实近况再看看回应  ")

    assert title == "明天先给对方发一句真实近况再看"
    assert len(title) == 15


def test_fallback_tip_prefers_focus_mapping():
    tip = _fallback_tip(
        pair_type="bestfriend",
        focus_items=["increase_shared_checkins"],
        risk_summary={"current_level": "none", "trend": "watch"},
    )

    assert tip["title"] == "先补一次联系"
    assert "明天" in tip["description"]


def test_report_hint_picks_best_available_summary():
    hint = _report_hint(
        {
            "change_summary": "最近互动回暖了一点，建议先保持轻量联系。",
            "suggestion": "这条不该优先命中",
        }
    )

    assert hint == "最近互动回暖了一点，建议先保持轻量联系。"


def test_parse_tip_response_falls_back_when_json_invalid():
    fallback = {
        "title": "先做一个小动作",
        "description": "明天先做一步最轻的小动作。",
        "content": "明天先做一步最轻的小动作。",
        "source": "rule",
    }

    parsed = _parse_tip_response("这不是合法 JSON", fallback)

    assert parsed == fallback


def test_personalized_tip_uses_rule_fallback_when_ai_exceeds_page_budget(monkeypatch):
    async def fake_load_snapshot(*_args, **_kwargs):
        return None

    async def fake_recent_status_lines(*_args, **_kwargs):
        return []

    async def slow_chat_completion(*_args, **_kwargs):
        await asyncio.sleep(0.05)
        return '{"title":"这条不应等到","description":"页面预算内应该先返回规则建议。"}'

    monkeypatch.setattr(community_api, "_load_snapshot", fake_load_snapshot)
    monkeypatch.setattr(community_api, "_recent_status_lines", fake_recent_status_lines)
    monkeypatch.setattr(community_api, "chat_completion", slow_chat_completion)
    monkeypatch.setattr(community_api, "TIP_AI_TIMEOUT_SECONDS", 0.001, raising=False)

    tip = asyncio.run(
        community_api._generate_personalized_tip(
            object(),
            user=SimpleNamespace(id=uuid.uuid4()),
            pair_type="solo",
        )
    )

    assert tip["source"] == "built_in"
    assert tip["title"] == "先做一件小事"


def test_profile_refresh_uses_latest_snapshot_when_legacy_duplicates_exist():
    db_dir = Path(__file__).resolve().parents[1] / ".test-dbs"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"duplicate-profile-snapshot-{uuid.uuid4().hex}.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def exercise():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with sessionmaker() as db:
            user_a = User(email=f"tip-a-{uuid.uuid4().hex}@example.com", nickname="A", password_hash="unused")
            user_b = User(email=f"tip-b-{uuid.uuid4().hex}@example.com", nickname="B", password_hash="unused")
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
            await db.flush()
            older = RelationshipProfileSnapshot(
                pair_id=pair.id,
                user_id=None,
                window_days=7,
                snapshot_date=current_local_date(),
                metrics_json={},
                version="v1",
                created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1),
            )
            latest = RelationshipProfileSnapshot(
                pair_id=pair.id,
                user_id=None,
                window_days=7,
                snapshot_date=current_local_date(),
                metrics_json={},
                version="v1",
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.add_all([older, latest])
            await db.commit()
            latest_id = latest.id
            pair_id = pair.id

        async with sessionmaker() as db:
            refreshed = await refresh_profile_snapshot(db, pair_id=pair_id)
            assert refreshed.id == latest_id

        await engine.dispose()

    try:
        asyncio.run(exercise())
    finally:
        db_path.unlink(missing_ok=True)


def test_generate_ai_tip_rate_limits_repeated_requests(monkeypatch):
    asyncio.run(close_request_cooldown_store())
    user_id = uuid.uuid4()

    async def override_current_user():
        return SimpleNamespace(id=user_id)

    async def override_get_db():
        yield object()

    async def fake_resolve_tip_pair(*_args, **_kwargs):
        return None, "solo"

    async def fake_generate_personalized_tip(*_args, **_kwargs):
        return {
            "title": "先做一件小事",
            "description": "明天先完成一步最轻的小动作。",
            "content": "明天先完成一步最轻的小动作。",
            "source": "ai",
        }

    monkeypatch.setattr(community_api, "_resolve_tip_pair", fake_resolve_tip_pair)
    monkeypatch.setattr(community_api, "_generate_personalized_tip", fake_generate_personalized_tip)

    app = FastAPI()
    app.include_router(community_api.router)
    app.dependency_overrides[community_api.get_current_user] = override_current_user
    app.dependency_overrides[community_api.get_db] = override_get_db

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            responses = [
                client.post("/community/tips/generate", params={"pair_type": "solo"})
                for _ in range(3)
            ]

        assert [response.status_code for response in responses[:2]] == [200, 200]
        assert responses[2].status_code == 429, responses[2].text
        assert "秒后再试" in responses[2].json()["detail"]
    finally:
        asyncio.run(close_request_cooldown_store())
