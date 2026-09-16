from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.insights_routes import timeline as timeline_api
from app.core.database import Base
from app.models import Checkin, Pair, PairStatus, PairType, RelationshipEvent, Report, ReportStatus, ReportType, User
from app.services.privacy_retention import run_privacy_retention_sweep
from app.services.timeline_archive import ensure_checkin_archive_fields


@pytest.fixture
async def archive_db_factory(monkeypatch):
    tmp_root = Path(__file__).resolve().parents[2] / "tmp" / f"timeline-archive-{uuid.uuid4().hex}"
    upload_root = tmp_root / "uploads"
    (upload_root / "images").mkdir(parents=True, exist_ok=True)
    (upload_root / "voices").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", str(upload_root))

    db_file = tmp_root / "archive.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield session_factory, upload_root
    finally:
        await engine.dispose()


def _make_local_app(db_override, current_user_override):
    app = FastAPI()
    app.include_router(timeline_api.router)
    app.dependency_overrides[timeline_api.get_db] = db_override
    app.dependency_overrides[timeline_api.get_current_user] = current_user_override
    return app


@pytest.mark.anyio
async def test_archive_route_mixes_owner_record_partner_placeholder_and_report(
    archive_db_factory,
):
    db_factory, upload_root = archive_db_factory
    owner_id = uuid.uuid4()
    partner_id = uuid.uuid4()
    pair_id = uuid.uuid4()
    record_id = uuid.uuid4()
    active_archive_date = timeline_api.date.today()

    (upload_root / "images" / "owner.png").write_bytes(b"image-bytes")
    (upload_root / "voices" / "owner.mp3").write_bytes(b"voice-bytes")

    async with db_factory() as db:
        owner = User(
            id=owner_id,
            email="owner@example.com",
            nickname="owner",
            password_hash="hash",
        )
        partner = User(
            id=partner_id,
            email="partner@example.com",
            nickname="partner",
            password_hash="hash",
        )
        pair = Pair(
            id=pair_id,
            user_a_id=owner_id,
            user_b_id=partner_id,
            type=PairType.COUPLE,
            status=PairStatus.ACTIVE,
            invite_code="A3H7K8M9Q2",
        )
        owner_checkin = Checkin(
            id=record_id,
            pair_id=pair_id,
            user_id=owner_id,
            content="今天我还是有点委屈，但也愿意慢慢说开。",
            image_url="/uploads/images/owner.png",
            voice_url="/uploads/voices/owner.mp3",
            mood_tags={"tags": ["委屈", "期待"]},
            client_context={
                "intent": "reflection",
                "risk_level": "watch",
                "source_type": "mixed",
                "upload_policy": "full",
                "device_meta": {
                    "image": {
                        "analysis": {
                            "scene_summary": "一张聊天截图，双方正在尝试修复误会。",
                            "mood_tags": ["委屈", "期待"],
                            "risk_level_label": "值得留意",
                            "privacy_sensitivity_label": "高敏感",
                            "retention_recommendation_label": "更适合只保留分析结果",
                        }
                    },
                    "voice": {
                        "duration_seconds": 8.4,
                        "silence_ratio": 0.21,
                    },
                },
            },
            checkin_date=active_archive_date,
        )
        ensure_checkin_archive_fields(owner_checkin)

        partner_checkin = Checkin(
            id=uuid.uuid4(),
            pair_id=pair_id,
            user_id=partner_id,
            content="我今天其实也想继续把误会说开。",
            mood_tags={"tags": ["期待"]},
            client_context={"intent": "daily", "risk_level": "none", "source_type": "text", "upload_policy": "full"},
            checkin_date=active_archive_date,
        )
        ensure_checkin_archive_fields(partner_checkin)

        report = Report(
            id=uuid.uuid4(),
            pair_id=pair_id,
            type=ReportType.DAILY,
            status=ReportStatus.COMPLETED,
            report_date=active_archive_date,
            content={
                "insight": "这一天更像在从防御走回修复。",
                "recommendations": ["先确认彼此都没有想退出", "只对齐一个误会点"],
            },
            health_score=78,
        )
        db.add_all([owner, partner, pair, owner_checkin, partner_checkin, report])
        await db.commit()

    async def override_get_db():
        async with db_factory() as session:
            yield session

    async def override_current_user():
        return SimpleNamespace(id=owner_id)

    app = _make_local_app(override_get_db, override_current_user)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/timeline/archive?pair_id={pair_id}")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["scope"] == "pair"
    assert payload["item_count"] == 3

    item_types = [item["item_type"] for item in payload["items"]]
    assert "record" in item_types
    assert "partner_record_placeholder" in item_types
    assert "report" in item_types

    owner_item = next(item for item in payload["items"] if item["item_type"] == "record")
    assert owner_item["has_raw_content"] is True
    assert owner_item["has_image_original"] is True
    assert owner_item["has_voice_original"] is True
    assert owner_item["record"]["content"] == "今天我还是有点委屈，但也愿意慢慢说开。"
    assert owner_item["record"]["image"]["access_url"] is None
    assert owner_item["record"]["voice"]["access_url"] is None
    assert owner_item["record"]["archive_insight"]["text_emotion"]["primary_mood"] == "委屈"

    partner_item = next(
        item for item in payload["items"] if item["item_type"] == "partner_record_placeholder"
    )
    assert partner_item["locked_reason"] == "原文和原媒体默认仅记录者本人可见。"
    assert partner_item["download_available"] is False
    assert partner_item.get("record") is None

    report_item = next(item for item in payload["items"] if item["item_type"] == "report")
    assert report_item["download_available"] is False
    assert report_item["report"]["summary"] == "这一天更像在从防御走回修复。"


@pytest.mark.anyio
async def test_archive_item_export_returns_owner_safe_json_and_denies_partner_raw_export(archive_db_factory):
    db_factory, _ = archive_db_factory
    owner_id = uuid.uuid4()
    partner_id = uuid.uuid4()
    pair_id = uuid.uuid4()
    record_id = uuid.uuid4()

    async with db_factory() as db:
        owner = User(id=owner_id, email="owner2@example.com", nickname="owner", password_hash="hash")
        partner = User(id=partner_id, email="partner2@example.com", nickname="partner", password_hash="hash")
        pair = Pair(
            id=pair_id,
            user_a_id=owner_id,
            user_b_id=partner_id,
            type=PairType.COUPLE,
            status=PairStatus.ACTIVE,
            invite_code="B4J8L9N2P3",
        )
        checkin = Checkin(
            id=record_id,
            pair_id=pair_id,
            user_id=owner_id,
            content="这条记录只应该被记录者导出。",
            client_context={"intent": "daily", "risk_level": "none", "source_type": "text", "upload_policy": "full"},
            checkin_date=timeline_api.date(2026, 4, 21),
        )
        ensure_checkin_archive_fields(checkin)
        db.add_all([owner, partner, pair, checkin])
        await db.commit()

    async def override_get_db():
        async with db_factory() as session:
            yield session

    current_user = {"id": owner_id}

    async def override_current_user():
        return SimpleNamespace(id=current_user["id"])

    app = _make_local_app(override_get_db, override_current_user)
    with TestClient(app, raise_server_exceptions=False) as client:
        owner_response = client.get(f"/timeline/archive/items/{record_id}/export?pair_id={pair_id}")
        current_user["id"] = partner_id
        partner_response = client.get(f"/timeline/archive/items/{record_id}/export?pair_id={pair_id}")

    assert owner_response.status_code == 200, owner_response.text
    assert "attachment" in owner_response.headers.get("content-disposition", "")
    owner_payload = owner_response.json()
    assert owner_payload["id"] == str(record_id)
    assert owner_payload["record"]["content"] == "这条记录只应该被记录者导出。"
    assert not any(str(key).startswith("__") for key in owner_payload)

    assert partner_response.status_code == 403, partner_response.text
    assert "原文" not in partner_response.text


@pytest.mark.anyio
async def test_archive_export_returns_safe_json_without_server_paths(archive_db_factory):
    db_factory, upload_root = archive_db_factory
    owner_id = uuid.uuid4()
    record_id = uuid.uuid4()

    (upload_root / "images" / "export.png").write_bytes(b"png-bytes")
    (upload_root / "voices" / "export.mp3").write_bytes(b"mp3-bytes")

    async with db_factory() as db:
        owner = User(
            id=owner_id,
            email="owner3@example.com",
            nickname="owner",
            password_hash="hash",
        )
        checkin = Checkin(
            id=record_id,
            user_id=owner_id,
            content="这条记录需要被导出。",
            image_url="/uploads/images/export.png",
            voice_url="/uploads/voices/export.mp3",
            client_context={"intent": "daily", "risk_level": "none", "source_type": "mixed", "upload_policy": "full"},
            checkin_date=timeline_api.date(2026, 4, 21),
        )
        ensure_checkin_archive_fields(checkin)
        db.add_all([owner, checkin])
        await db.commit()

    async def override_get_db():
        async with db_factory() as session:
            yield session

    async def override_current_user():
        return SimpleNamespace(id=owner_id)

    app = _make_local_app(override_get_db, override_current_user)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/timeline/archive/export?mode=solo&item_filter=mine")

    assert response.status_code == 200, response.text
    assert "attachment" in response.headers.get("content-disposition", "")
    payload = response.json()
    assert payload["scope"] == "solo"
    assert payload["item_count"] == 1
    assert payload["items"][0]["record"]["content"] == "这条记录需要被导出。"
    serialized = response.text
    assert "__image_upload_path" not in serialized
    assert "__voice_upload_path" not in serialized
    assert str(upload_root) not in serialized


@pytest.mark.anyio
async def test_retention_sweep_removes_media_only_and_keeps_text_and_summary(
    archive_db_factory,
):
    db_factory, upload_root = archive_db_factory
    owner_id = uuid.uuid4()

    image_path = upload_root / "images" / "expired.png"
    voice_path = upload_root / "voices" / "expired.mp3"
    image_path.write_bytes(b"expired-image")
    voice_path.write_bytes(b"expired-voice")

    async with db_factory() as db:
        owner = User(
            id=owner_id,
            email="owner4@example.com",
            nickname="owner",
            password_hash="hash",
        )
        checkin = Checkin(
            id=uuid.uuid4(),
            user_id=owner_id,
            content="这条原文会继续保留，只有媒体原件会在后台被清理。",
            image_url="/uploads/images/expired.png",
            voice_url="/uploads/voices/expired.mp3",
            client_context={"intent": "reflection", "risk_level": "watch", "source_type": "mixed", "upload_policy": "full"},
            checkin_date=timeline_api.date(2026, 4, 10),
            created_at=timeline_api.datetime(2026, 4, 10, 8, 0, 0),
        )
        db.add_all([owner, checkin])
        await db.commit()

        summary = await run_privacy_retention_sweep(
            db,
            dry_run=False,
            now=timeline_api.datetime(2026, 5, 21, 8, 0, 0),
        )
        await db.commit()

        refreshed = await db.get(Checkin, checkin.id)

    assert summary["expired_raw_checkins"] == 1
    assert summary["deleted_raw_uploads"] == 2
    assert refreshed is not None
    assert refreshed.content == "这条原文会继续保留，只有媒体原件会在后台被清理。"
    assert refreshed.image_url is None
    assert refreshed.voice_url is None
    assert refreshed.raw_deleted_at is not None
    assert refreshed.raw_retention_until == timeline_api.datetime(2026, 5, 9, 20, 0, 0)
    assert refreshed.archive_title
    assert refreshed.archive_summary
    assert refreshed.client_context["archive_insight"]["retention_policy"]["timezone"] == "Asia/Shanghai"
    assert refreshed.client_context["archive_insight"]["raw_deletion_snapshot"]["policy"]["cutoff_label"] == "北京时间每日 04:00"
    assert not image_path.exists()
    assert not voice_path.exists()


@pytest.mark.anyio
async def test_archive_pagination_keeps_items_with_same_timestamp(
    archive_db_factory,
):
    db_factory, _ = archive_db_factory
    owner_id = uuid.uuid4()
    shared_created_at = timeline_api.datetime(2026, 4, 21, 8, 0, 0)

    async with db_factory() as db:
        owner = User(
            id=owner_id,
            email="owner6@example.com",
            nickname="owner",
            password_hash="hash",
        )
        db.add(owner)
        for idx in range(7):
            checkin = Checkin(
                id=uuid.uuid4(),
                user_id=owner_id,
                content=f"同一时间点的第 {idx + 1} 条记录。",
                client_context={"intent": "daily", "risk_level": "none", "source_type": "text", "upload_policy": "full"},
                checkin_date=timeline_api.date(2026, 4, 21),
                created_at=shared_created_at,
            )
            ensure_checkin_archive_fields(checkin)
            db.add(checkin)
        await db.commit()

    async def override_get_db():
        async with db_factory() as session:
            yield session

    async def override_current_user():
        return SimpleNamespace(id=owner_id)

    app = _make_local_app(override_get_db, override_current_user)
    with TestClient(app, raise_server_exceptions=False) as client:
        first_page = client.get("/timeline/archive?mode=solo&limit=6")
        assert first_page.status_code == 200, first_page.text
        first_payload = first_page.json()
        assert first_payload["item_count"] == 6
        assert "|" in str(first_payload["next_before"])

        second_page = client.get(
            "/timeline/archive",
            params={"mode": "solo", "limit": 6, "before": first_payload["next_before"]},
        )

    assert second_page.status_code == 200, second_page.text
    second_payload = second_page.json()
    assert second_payload["item_count"] == 1

    first_ids = [item["id"] for item in first_payload["items"]]
    second_ids = [item["id"] for item in second_payload["items"]]
    assert len(set([*first_ids, *second_ids])) == 7


@pytest.mark.anyio
async def test_timeline_event_detail_locks_partner_checkin_raw_content(
    archive_db_factory,
):
    db_factory, _upload_root = archive_db_factory
    owner_id = uuid.uuid4()
    partner_id = uuid.uuid4()
    pair_id = uuid.uuid4()
    checkin_id = uuid.uuid4()
    event_id = uuid.uuid4()

    secret_content = "只有我自己知道的秘密心事，绝不能原样出现在对方的时间轴详情里。"

    async with db_factory() as db:
        owner = User(
            id=owner_id,
            email="owner5@example.com",
            nickname="owner",
            password_hash="hash",
        )
        partner = User(
            id=partner_id,
            email="partner5@example.com",
            nickname="partner",
            password_hash="hash",
        )
        pair = Pair(
            id=pair_id,
            user_a_id=owner_id,
            user_b_id=partner_id,
            type=PairType.COUPLE,
            status=PairStatus.ACTIVE,
            invite_code="D6M2N4P8Q1",
        )
        checkin = Checkin(
            id=checkin_id,
            pair_id=pair_id,
            user_id=partner_id,
            content=secret_content,
            mood_tags={"tags": ["委屈"]},
            mood_score=2,
            interaction_freq=3,
            checkin_date=timeline_api.date.today(),
        )
        event = RelationshipEvent(
            id=event_id,
            pair_id=pair_id,
            user_id=partner_id,
            event_type="checkin.created",
            entity_type="checkin",
            entity_id=str(checkin_id),
            payload={
                "mode": "pair",
                "mood_score": 2,
                "text_preview": secret_content[:20],
                "client_context": {"intent": "daily"},
            },
        )
        db.add_all([owner, partner, pair, checkin, event])
        await db.commit()

    async def override_get_db():
        async with db_factory() as session:
            yield session

    current_user = {"id": owner_id}

    async def override_current_user():
        return SimpleNamespace(id=current_user["id"])

    app = _make_local_app(override_get_db, override_current_user)
    with TestClient(app, raise_server_exceptions=False) as client:
        owner_response = client.get(f"/timeline/events/{event_id}")
        current_user["id"] = partner_id
        partner_response = client.get(f"/timeline/events/{event_id}")

    assert owner_response.status_code == 200, owner_response.text
    owner_detail = owner_response.json()
    assert secret_content not in owner_response.text
    cards = owner_detail.get("evidence_cards") or []
    assert any("仅记录者本人可见" in str(card.get("body", "")) for card in cards)
    assert not any(str(card.get("body", "")) == secret_content for card in cards)
    event_payload = (owner_detail.get("event") or {}).get("payload") or {}
    assert "text_preview" not in event_payload
    assert "client_context" not in event_payload

    assert partner_response.status_code == 200, partner_response.text
    assert secret_content in partner_response.text
