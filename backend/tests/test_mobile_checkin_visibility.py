"""移动端打卡可见性：权限矩阵、伴侣投影、乐观并发、幂等、撤回失效。"""
import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import get_current_user
from app.core.database import Base, get_db
from app.core.time import current_local_date
from app.models import (
    Checkin,
    Pair,
    PairStatus,
    PairType,
    RelationshipEvent,
    RelationshipMemory,
    RelationshipProfileSnapshot,
    Report,
    ReportStatus,
    ReportType,
    User,
)


@pytest.fixture
def workspace():
    from app.api.v1.mobile import router

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    ids = {key: uuid.uuid4() for key in ["alice", "bob", "outsider", "pair"]}
    actor = {"id": ids["alice"]}

    async def seed():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as db:
            for name in ["alice", "bob", "outsider"]:
                db.add(
                    User(
                        id=ids[name],
                        email=f"{name}@test.invalid",
                        nickname=name,
                        password_hash="unused",
                    )
                )
            db.add(
                Pair(
                    id=ids["pair"],
                    user_a_id=ids["alice"],
                    user_b_id=ids["bob"],
                    type=PairType.COUPLE,
                    status=PairStatus.ACTIVE,
                    invite_code="visibility-test",
                )
            )
            await db.commit()

    asyncio.run(seed())

    async def db_override():
        async with factory() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def user_override():
        async with factory() as db:
            return await db.get(User, actor["id"])

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_current_user] = user_override
    with TestClient(app) as client:
        yield client, ids, actor, factory
    asyncio.run(engine.dispose())


def _create(client, ids, *, content="今天有点累，但还好。", visibility=None, confirmed=False, context=None):
    payload = {
        "scope": "relationship",
        "relationship_space_id": str(ids["pair"]),
        "client_request_id": f"mini_{uuid.uuid4().hex}",
        "content": content,
        "sharing_confirmed": confirmed,
        "client_context": context,
    }
    if visibility:
        payload["visibility_scope"] = visibility
    return client.post("/api/v1/mobile/checkins", json=payload)


def test_default_scope_is_shared_summary_and_partner_sees_projection(workspace):
    client, ids, actor, _ = workspace
    created = _create(client, ids, content="今天有点累，但还好。", confirmed=True)
    assert created.status_code == 200, created.text
    record_id = created.json()["record_id"]
    assert created.json()["visibility_scope"] == "shared_summary"

    owner_view = client.post(
        "/api/v1/mobile/checkins/detail", json={"record_id": record_id}
    ).json()
    assert owner_view["is_owner"] is True
    assert owner_view["content"] == "今天有点累，但还好。"

    actor["id"] = ids["bob"]
    partner_view = client.post(
        "/api/v1/mobile/checkins/detail", json={"record_id": record_id}
    ).json()
    assert partner_view["is_owner"] is False
    assert partner_view["content"] is None
    assert partner_view["image_url"] is None
    assert partner_view["voice_url"] is None
    assert partner_view["locked_reason"]
    # 伴侣投影不得包含原文，也不得包含风险标签
    assert "今天有点累" not in partner_view["summary"]
    assert "值得留意" not in partner_view["summary"]
    assert "需要谨慎处理" not in partner_view["summary"]
    assert "需要保护" not in partner_view["summary"]

    actor["id"] = ids["outsider"]
    assert (
        client.post("/api/v1/mobile/checkins/detail", json={"record_id": record_id}).status_code
        == 404
    )


def test_private_hides_even_the_summary_and_outsider_gets_404(workspace):
    client, ids, actor, _ = workspace
    created = _create(client, ids, visibility="private")
    assert created.status_code == 200, created.text
    record_id = created.json()["record_id"]
    assert created.json()["visibility_scope"] == "private"

    actor["id"] = ids["bob"]
    assert (
        client.post("/api/v1/mobile/checkins/detail", json={"record_id": record_id}).status_code
        == 404
    )
    actor["id"] = ids["alice"]
    assert (
        client.post("/api/v1/mobile/checkins/detail", json={"record_id": record_id}).json()["content"]
        == "今天有点累，但还好。"
    )


def test_sharing_requires_explicit_confirmation_and_pair(workspace):
    client, ids, _, _ = workspace
    assert _create(client, ids, visibility="shared_summary", confirmed=False).status_code == 422
    # 决策 D1 落地：shared_original 无论是否确认，一律被 422 拒绝
    assert _create(client, ids, visibility="shared_original", confirmed=False).status_code == 422
    assert _create(client, ids, visibility="shared_original", confirmed=True).status_code == 422

    solo = client.post(
        "/api/v1/mobile/checkins",
        json={
            "scope": "solo",
            "client_request_id": f"mini_{uuid.uuid4().hex}",
            "content": "只给自己看。",
            "visibility_scope": "shared_summary",
            "sharing_confirmed": True,
        },
    )
    assert solo.status_code == 422


def test_visibility_change_rejects_shared_original(workspace):
    client, ids, _, _ = workspace
    created = _create(client, ids, confirmed=True).json()
    record_id = created["record_id"]
    state = client.post("/api/v1/mobile/checkins/visibility", json={"record_id": record_id}).json()

    # 试图修改为 shared_original 必须 422 拒绝
    resp = client.post(
        "/api/v1/mobile/checkins/visibility/change",
        json={
            "record_id": record_id,
            "expected_version": state["version"],
            "visibility_scope": "shared_original",
            "sharing_confirmed": True,
        },
    )
    assert resp.status_code == 422


def test_create_is_idempotent_per_client_request_id(workspace):
    client, ids, _, _ = workspace
    request_id = f"mini_{uuid.uuid4().hex}"
    payload = {
        "scope": "relationship",
        "relationship_space_id": str(ids["pair"]),
        "client_request_id": request_id,
        "content": "今天有点累，但还好。",
        "sharing_confirmed": True,
    }
    first = client.post("/api/v1/mobile/checkins", json=payload)
    assert first.status_code == 200
    assert first.json()["deduplicated"] is False

    second = client.post("/api/v1/mobile/checkins", json=payload)
    assert second.status_code == 200
    assert second.json()["deduplicated"] is True
    assert second.json()["record_id"] == first.json()["record_id"]

    conflict = client.post(
        "/api/v1/mobile/checkins", json={**payload, "client_request_id": f"mini_{uuid.uuid4().hex}"}
    )
    assert conflict.status_code == 409


def test_visibility_read_and_change_use_optimistic_version(workspace):
    client, ids, actor, _ = workspace
    record_id = _create(client, ids, confirmed=True).json()["record_id"]

    state = client.post("/api/v1/mobile/checkins/visibility", json={"record_id": record_id}).json()
    assert state["visibility_scope"] == "shared_summary"
    assert state["sharing_active"] is True
    assert state["partner_can_use_summary"] is True
    assert state["partner_can_read_original"] is False
    version = state["version"]

    stale = client.post(
        "/api/v1/mobile/checkins/visibility/change",
        json={"record_id": record_id, "expected_version": "999", "visibility_scope": "private"},
    )
    assert stale.status_code == 409

    changed = client.post(
        "/api/v1/mobile/checkins/visibility/change",
        json={"record_id": record_id, "expected_version": version, "visibility_scope": "private"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["visibility_scope"] == "private"
    assert changed.json()["sharing_revoked"] is True
    assert changed.json()["sharing_active"] is False
    assert changed.json()["version"] != version

    actor["id"] = ids["bob"]
    assert (
        client.post("/api/v1/mobile/checkins/visibility", json={"record_id": record_id}).status_code
        == 404
    )


def test_revoke_invalidates_derived_artifacts_and_is_idempotent(workspace):
    client, ids, _, factory = workspace
    record_id = _create(client, ids, confirmed=True).json()["record_id"]
    checkin_id = uuid.UUID(record_id)

    async def seed_derived():
        async with factory() as db:
            checkin = await db.get(__import__("app.models", fromlist=["Checkin"]).Checkin, checkin_id)
            db.add(
                RelationshipEvent(
                    pair_id=ids["pair"],
                    user_id=ids["alice"],
                    event_type="alignment.generated",
                    payload={"cache_key": f"alignment:{ids['pair']}:{checkin_id}:{checkin_id}"},
                    idempotency_key=f"alignment:{uuid.uuid4().hex}",
                )
            )
            db.add(
                Report(
                    pair_id=ids["pair"],
                    type=ReportType.DAILY,
                    status=ReportStatus.COMPLETED,
                    content={"summary": "包含了她的原文线索"},
                    health_score=80.0,
                    report_date=checkin.checkin_date,
                )
            )
            db.add(
                RelationshipProfileSnapshot(
                    pair_id=ids["pair"],
                    window_days=7,
                    snapshot_date=checkin.checkin_date,
                    metrics_json={"x": 1},
                )
            )
            db.add(
                RelationshipMemory(
                    pair_id=ids["pair"],
                    user_id=ids["alice"],
                    memory_type="event",
                    subject="由记录派生",
                    content={"note": "derived"},
                    created_at=checkin.created_at,
                )
            )
            await db.commit()

    asyncio.run(seed_derived())

    state = client.post("/api/v1/mobile/checkins/visibility", json={"record_id": record_id}).json()
    request_id = f"mini_{uuid.uuid4().hex}"
    revoked = client.post(
        "/api/v1/mobile/checkins/visibility/change",
        json={
            "record_id": record_id,
            "expected_version": state["version"],
            "visibility_scope": "private",
            "client_request_id": request_id,
        },
    )
    assert revoked.status_code == 200, revoked.text
    body = revoked.json()
    assert body["alignment_results_invalidated"] == 1
    assert body["reports_invalidated"] == 1
    assert body["snapshots_invalidated"] == 1
    assert body["derived_insights_invalidated"] == 1

    retry = client.post(
        "/api/v1/mobile/checkins/visibility/change",
        json={
            "record_id": record_id,
            "expected_version": state["version"],
            "visibility_scope": "private",
            "client_request_id": request_id,
        },
    )
    assert retry.status_code == 200
    assert retry.json()["deduplicated"] is True

    async def inspect():
        async with factory() as db:
            events = (
                await db.execute(
                    select(RelationshipEvent).where(
                        RelationshipEvent.event_type == "alignment.generated"
                    )
                )
            ).scalars().all()
            assert events == []
            report = (await db.execute(select(Report))).scalars().one()
            assert report.content is None
            assert report.status == ReportStatus.PENDING
            assert (await db.execute(select(RelationshipProfileSnapshot))).scalars().all() == []
            assert (await db.execute(select(RelationshipMemory))).scalars().all() == []

    asyncio.run(inspect())


def test_preflight_bootstrap_and_today_boot_the_client(workspace):
    client, ids, _, _ = workspace
    preflight = client.post(
        "/api/v1/mobile/preflight", json={"client_type": "app", "platform": "android"}
    )
    assert preflight.status_code == 200, preflight.text
    assert preflight.json()["client_type"] == "app"
    assert preflight.json()["adult_confirmation_required"] is True
    assert preflight.json()["service_terms_version"]

    bootstrap = client.post("/api/v1/mobile/bootstrap", json={})
    assert bootstrap.status_code == 200, bootstrap.text
    body = bootstrap.json()
    assert body["state_version"]
    assert body["account"]["user_id"] == str(ids["alice"])
    assert [item["space_id"] for item in body["relationships"]] == [str(ids["pair"])]
    assert body["realtime_voice"]["available"] is False

    repeat = client.post(
        "/api/v1/mobile/bootstrap", json={"known_state_version": body["state_version"]}
    )
    assert repeat.json()["not_modified"] is True

    today = client.post(
        "/api/v1/mobile/today",
        json={"scope": "relationship", "relationship_space_id": str(ids["pair"])},
    )
    assert today.status_code == 200, today.text
    assert today.json()["relationship_ready"] is True
    assert today.json()["checkin"]["my_completed"] is False
    assert today.json()["checkin"]["can_submit"] is True


def test_realtime_voice_ticket_requires_local_buffer_confirmation(workspace):
    client, _, _, _ = workspace
    issued = client.post(
        "/api/v1/mobile/realtime-voice/tickets",
        json={"reason": "initial", "local_buffer_confirmed": True},
    )
    assert issued.status_code == 200, issued.text
    body = issued.json()
    assert body["ticket"]
    assert body["expires_in"] >= 30
    assert body["local_buffer_required"] is True
    assert body["websocket_path"] == "/api/v1/agent/asr/realtime"

    missing = client.post(
        "/api/v1/mobile/realtime-voice/tickets", json={"reason": "initial"}
    )
    assert missing.status_code == 422


def test_timeline_excludes_private_partner_records(workspace):
    client, ids, actor, _ = workspace
    mine = _create(client, ids, visibility="private").json()["record_id"]

    actor["id"] = ids["bob"]
    partner_private = _create(client, ids, visibility="private").json()["record_id"]

    actor["id"] = ids["alice"]
    page = client.post(
        "/api/v1/mobile/timeline",
        json={"scope": "relationship", "relationship_space_id": str(ids["pair"])},
    )
    assert page.status_code == 200, page.text
    ids_on_page = {item["item_id"] for item in page.json()["items"]}
    assert mine in ids_on_page
    assert partner_private not in ids_on_page

    repeat = client.post(
        "/api/v1/mobile/timeline",
        json={
            "scope": "relationship",
            "relationship_space_id": str(ids["pair"]),
            "known_page_version": page.json()["page_version"],
        },
    )
    assert repeat.json()["not_modified"] is True


def test_timeline_shows_partner_summary_without_original(workspace):
    client, ids, actor, _ = workspace
    actor["id"] = ids["bob"]
    partner_record = _create(
        client, ids, content="今天有点累，但还好。", confirmed=True
    ).json()["record_id"]

    actor["id"] = ids["alice"]
    page = client.post(
        "/api/v1/mobile/timeline",
        json={"scope": "relationship", "relationship_space_id": str(ids["pair"])},
    )
    items = {item["item_id"]: item for item in page.json()["items"]}
    assert partner_record in items
    entry = items[partner_record]
    assert entry["kind"] == "partner_summary"
    assert entry["is_mine"] is False
    assert entry["can_manage_visibility"] is False
    assert entry["original_available"] is False
    assert entry["visibility_scope"] == "shared_summary"
    assert "今天有点累" not in entry["summary"]


def test_media_preflight_upload_access_and_discard(workspace):
    client, ids, actor, _ = workspace
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

    rejected = client.post(
        "/api/v1/mobile/media/preflight",
        json={
            "client_request_id": f"mini_{uuid.uuid4().hex}",
            "media_kind": "image",
            "content_type": "application/pdf",
            "size_bytes": len(png),
            "private_storage_confirmed": True,
        },
    )
    assert rejected.status_code == 400

    oversized = client.post(
        "/api/v1/mobile/media/preflight",
        json={
            "client_request_id": f"mini_{uuid.uuid4().hex}",
            "media_kind": "image",
            "content_type": "image/png",
            "size_bytes": 99 * 1024 * 1024,
            "private_storage_confirmed": True,
        },
    )
    assert oversized.status_code == 400

    preflight = client.post(
        "/api/v1/mobile/media/preflight",
        json={
            "client_request_id": f"mini_{uuid.uuid4().hex}",
            "media_kind": "image",
            "content_type": "image/png",
            "size_bytes": len(png),
            "private_storage_confirmed": True,
        },
    )
    assert preflight.status_code == 200, preflight.text
    ticket = preflight.json()["upload_ticket"]
    assert preflight.json()["visibility_scope"] == "private"

    mismatched = client.post(
        "/api/v1/mobile/media/upload",
        data={"upload_ticket": ticket},
        files={"file": ("a.png", png, "image/jpeg")},
    )
    assert mismatched.status_code == 400

    uploaded = client.post(
        "/api/v1/mobile/media/upload",
        data={"upload_ticket": ticket},
        files={"file": ("a.png", png, "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    media_id = uploaded.json()["media_id"]
    assert media_id.startswith("images/")
    assert uploaded.json()["size_bytes"] == len(png)
    assert uploaded.json()["access_url"]

    actor["id"] = ids["bob"]
    assert (
        client.post("/api/v1/mobile/media/access", json={"media_id": media_id}).status_code == 404
    )
    assert (
        client.post(
            "/api/v1/mobile/media/discard",
            json={
                "media_id": media_id,
                "client_request_id": f"mini_{uuid.uuid4().hex}",
                "discard_confirmed": True,
            },
        ).status_code
        == 404
    )

    actor["id"] = ids["alice"]
    access = client.post("/api/v1/mobile/media/access", json={"media_id": media_id})
    assert access.status_code == 200, access.text
    assert access.json()["access_url"]

    discarded = client.post(
        "/api/v1/mobile/media/discard",
        json={
            "media_id": media_id,
            "client_request_id": f"mini_{uuid.uuid4().hex}",
            "discard_confirmed": True,
        },
    )
    assert discarded.status_code == 200, discarded.text
    assert discarded.json()["file_removed"] is True
    assert discarded.json()["upload_grants_removed"] >= 1
    assert (
        client.post("/api/v1/mobile/media/access", json={"media_id": media_id}).status_code == 404
    )


def test_media_upload_rejects_foreign_ticket(workspace):
    client, ids, actor, _ = workspace
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    preflight = client.post(
        "/api/v1/mobile/media/preflight",
        json={
            "client_request_id": f"mini_{uuid.uuid4().hex}",
            "media_kind": "image",
            "content_type": "image/png",
            "size_bytes": len(png),
            "private_storage_confirmed": True,
        },
    ).json()

    actor["id"] = ids["bob"]
    stolen = client.post(
        "/api/v1/mobile/media/upload",
        data={"upload_ticket": preflight["upload_ticket"]},
        files={"file": ("a.png", png, "image/png")},
    )
    assert stolen.status_code == 403

    forged = client.post(
        "/api/v1/mobile/media/upload",
        data={"upload_ticket": "not-a-ticket"},
        files={"file": ("a.png", png, "image/png")},
    )
    assert forged.status_code == 403


def test_correct_checkin_bumps_version_and_invalidates(workspace):
    client, ids, actor, _ = workspace
    record_id = _create(client, ids, confirmed=True).json()["record_id"]
    state = client.post("/api/v1/mobile/checkins/visibility", json={"record_id": record_id}).json()

    stale = client.post(
        "/api/v1/mobile/checkins/correct",
        json={
            "record_id": record_id,
            "expected_detail_version": "999",
            "client_request_id": f"mini_{uuid.uuid4().hex}",
            "content": "改过的内容。",
        },
    )
    assert stale.status_code == 409

    corrected = client.post(
        "/api/v1/mobile/checkins/correct",
        json={
            "record_id": record_id,
            "expected_detail_version": state["version"],
            "client_request_id": f"mini_{uuid.uuid4().hex}",
            "content": "改过的内容，今天还行。",
        },
    )
    assert corrected.status_code == 200, corrected.text
    body = corrected.json()
    assert body["corrected_fields"] == ["content"]
    assert body["detail_version"] != state["version"]

    detail = client.post(
        "/api/v1/mobile/checkins/detail", json={"record_id": record_id}
    ).json()
    assert detail["content"] == "改过的内容，今天还行。"

    empty = client.post(
        "/api/v1/mobile/checkins/correct",
        json={
            "record_id": record_id,
            "expected_detail_version": body["detail_version"],
            "client_request_id": f"mini_{uuid.uuid4().hex}",
        },
    )
    assert empty.status_code == 422


def test_delete_checkin_revokes_sharing_and_clears_content(workspace):
    client, ids, actor, factory = workspace
    record_id = _create(client, ids, confirmed=True).json()["record_id"]
    state = client.post("/api/v1/mobile/checkins/visibility", json={"record_id": record_id}).json()

    deleted = client.post(
        "/api/v1/mobile/checkins/delete",
        json={
            "record_id": record_id,
            "expected_detail_version": state["version"],
            "client_request_id": f"mini_{uuid.uuid4().hex}",
            "deletion_confirmed": True,
        },
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["shared_access_revoked"] is True

    actor["id"] = ids["bob"]
    assert (
        client.post("/api/v1/mobile/checkins/detail", json={"record_id": record_id}).status_code
        == 404
    )

    async def inspect():
        from app.models import Checkin

        async with factory() as db:
            row = await db.get(Checkin, uuid.UUID(record_id))
            assert row.content == ""
            assert row.visibility_scope == "private"
            assert row.raw_deleted_at is not None

    asyncio.run(inspect())


def test_notifications_list_read_and_read_all(workspace):
    client, ids, actor, factory = workspace

    async def seed():
        from app.models import UserNotification

        async with factory() as db:
            for index in range(3):
                db.add(
                    UserNotification(
                        user_id=ids["alice"],
                        type="task",
                        content=f"提醒 {index}",
                        is_read=False,
                    )
                )
            db.add(
                UserNotification(
                    user_id=ids["bob"], type="task", content="别人的提醒", is_read=False
                )
            )
            await db.commit()

    asyncio.run(seed())

    listing = client.post("/api/v1/mobile/notifications/list", json={"limit": 10})
    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert body["unread_count"] == 3
    assert len(body["items"]) == 3
    assert all(item["is_read"] is False for item in body["items"])

    first_id = body["items"][0]["notification_id"]
    read = client.post(
        "/api/v1/mobile/notifications/read",
        json={"notification_ids": [first_id], "read_confirmed": True},
    )
    assert read.status_code == 200, read.text
    assert read.json()["updated_count"] == 1
    assert read.json()["unread_count"] == 2

    actor["id"] = ids["bob"]
    foreign = client.post(
        "/api/v1/mobile/notifications/read",
        json={"notification_ids": [first_id], "read_confirmed": True},
    )
    assert foreign.json()["updated_count"] == 0

    actor["id"] = ids["alice"]
    all_read = client.post(
        "/api/v1/mobile/notifications/read-all", json={"read_all_confirmed": True}
    )
    assert all_read.json()["unread_count"] == 0


def test_weekly_summary_status_and_not_modified(workspace):
    client, ids, actor, factory = workspace
    missing = client.post(
        "/api/v1/mobile/reports/weekly-summary",
        json={"relationship_space_id": str(ids["pair"])},
    )
    assert missing.status_code == 200, missing.text
    assert missing.json()["status"] == "not_available"

    async def seed():
        async with factory() as db:
            db.add(
                Report(
                    pair_id=ids["pair"],
                    type=ReportType.WEEKLY,
                    status=ReportStatus.COMPLETED,
                    content={
                        "summary": "这周整体在变好。",
                        "highlights": ["多了两次深聊"],
                        "trend": "improving",
                    },
                    report_date=datetime.now(timezone.utc).date(),
                )
            )
            await db.commit()

    asyncio.run(seed())

    summary = client.post(
        "/api/v1/mobile/reports/weekly-summary",
        json={"relationship_space_id": str(ids["pair"])},
    )
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["status"] == "ready"
    assert body["trend"] == "improving"
    assert body["summary"] == "这周整体在变好。"
    assert body["highlights"] == ["多了两次深聊"]

    repeat = client.post(
        "/api/v1/mobile/reports/weekly-summary",
        json={
            "relationship_space_id": str(ids["pair"]),
            "known_summary_version": body["summary_version"],
        },
    )
    assert repeat.json()["not_modified"] is True

    actor["id"] = ids["outsider"]
    assert (
        client.post(
            "/api/v1/mobile/reports/weekly-summary",
            json={"relationship_space_id": str(ids["pair"])},
        ).status_code
        == 403
    )


def test_media_status_and_cancel_follow_the_preflight_session(workspace):
    client, ids, actor, _ = workspace
    request_id = f"mini_{uuid.uuid4().hex}"
    preflight = client.post(
        "/api/v1/mobile/media/preflight",
        json={
            "client_request_id": request_id,
            "media_kind": "image",
            "content_type": "image/png",
            "size_bytes": 128,
            "private_storage_confirmed": True,
        },
    )
    assert preflight.status_code == 200, preflight.text

    status = client.post(
        "/api/v1/mobile/media/status", json={"client_request_id": request_id}
    )
    assert status.status_code == 200, status.text
    assert status.json()["status"] == "ready"
    assert status.json()["upload_required"] is True

    actor["id"] = ids["bob"]
    assert (
        client.post(
            "/api/v1/mobile/media/status", json={"client_request_id": request_id}
        ).status_code
        == 404
    )

    actor["id"] = ids["alice"]
    cancelled = client.post(
        "/api/v1/mobile/media/cancel",
        json={
            "upload_ticket": preflight.json()["upload_ticket"],
            "cancellation_confirmed": True,
        },
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["cancelled"] is True
    again = client.post(
        "/api/v1/mobile/media/cancel",
        json={
            "upload_ticket": preflight.json()["upload_ticket"],
            "cancellation_confirmed": True,
        },
    )
    assert again.json()["deduplicated"] is True
    assert (
        client.post(
            "/api/v1/mobile/media/status", json={"client_request_id": request_id}
        ).json()["status"]
        == "cancelled"
    )


def test_actions_list_complete_and_feedback(workspace):
    client, ids, actor, factory = workspace

    async def seed():
        from app.models import RelationshipTask, TaskImportance, TaskStatus

        async with factory() as db:
            db.add(
                RelationshipTask(
                    pair_id=ids["pair"],
                    user_id=None,
                    title="一起散步 20 分钟",
                    category="activity",
                    importance_level=TaskImportance.MEDIUM,
                    status=TaskStatus.PENDING,
                    due_date=datetime.now(timezone.utc).date(),
                )
            )
            await db.commit()

    asyncio.run(seed())

    listing = client.post(
        "/api/v1/mobile/actions",
        json={"scope": "relationship", "relationship_space_id": str(ids["pair"])},
    )
    assert listing.status_code == 200, listing.text
    assert len(listing.json()) == 1
    action_id = listing.json()[0]["action_id"]
    assert listing.json()[0]["status"] == "pending"
    assert listing.json()[0]["target_scope"] == "both"

    completed = client.post(
        "/api/v1/mobile/actions/complete",
        json={"relationship_space_id": str(ids["pair"]), "action_id": action_id},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"

    feedback = client.post(
        "/api/v1/mobile/actions/feedback",
        json={
            "relationship_space_id": str(ids["pair"]),
            "action_id": action_id,
            "usefulness_score": 4,
            "friction_score": 1,
            "relationship_shift_score": 3,
        },
    )
    assert feedback.status_code == 200, feedback.text
    assert feedback.json()["feedback_version"]

    actor["id"] = ids["outsider"]
    assert (
        client.post(
            "/api/v1/mobile/actions",
            json={"scope": "relationship", "relationship_space_id": str(ids["pair"])},
        ).status_code
        == 403
    )


def test_runtime_privacy_guard_and_release_check(workspace):
    client, _, _, _ = workspace
    guard = client.post(
        "/api/v1/mobile/runtime/privacy-guard-policy",
        json={
            "platform": "android",
            "biometric_state": "enrolled",
            "device_credential_available": True,
            "screen_capture_protection_supported": True,
        },
    )
    assert guard.status_code == 200, guard.text
    assert guard.json()["access_mode"] == "full"
    assert guard.json()["unlock_method"] == "biometric"
    assert guard.json()["screen_capture_policy"] == "block"
    assert guard.json()["biometric_data_collected"] is False

    unavailable = client.post(
        "/api/v1/mobile/runtime/privacy-guard-policy",
        json={
            "platform": "ios",
            "biometric_state": "locked_out",
            "device_credential_available": False,
            "screen_capture_protection_supported": False,
        },
    )
    assert unavailable.json()["access_mode"] == "restricted"
    assert unavailable.json()["unlock_method"] == "unavailable"

    release = client.post(
        "/api/v1/mobile/runtime/release-check",
        json={"platform": "android", "app_version": "1.0.0", "build_number": 1},
    )
    assert release.status_code == 200, release.text
    assert release.json()["status"] in {"supported", "policy_unavailable"}


def test_notification_preferences_use_optimistic_version(workspace):
    client, _, _, _ = workspace
    status = client.post("/api/v1/mobile/notification-preferences/status", json={})
    assert status.status_code == 200, status.text
    prefs = status.json()["preferences"]
    assert len(prefs) == 5
    target = next(item for item in prefs if item["category"] == "task_reminder")

    stale = client.post(
        "/api/v1/mobile/notification-preferences/change",
        json={
            "category": "task_reminder",
            "base_version": "stale",
            "enabled": False,
            "update_confirmed": True,
        },
    )
    assert stale.status_code == 409

    changed = client.post(
        "/api/v1/mobile/notification-preferences/change",
        json={
            "category": "task_reminder",
            "base_version": target["preference_version"],
            "enabled": False,
            "daily_limit": 2,
            "update_confirmed": True,
        },
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["preference"]["enabled"] is False
    assert changed.json()["preference"]["daily_limit"] == 2
    assert changed.json()["preference"]["preference_version"] != target["preference_version"]

    refreshed = client.post(
        "/api/v1/mobile/notification-preferences/status", json={}
    ).json()["preferences"]
    assert next(
        item for item in refreshed if item["category"] == "task_reminder"
    )["enabled"] is False


def test_notification_preference_subscription_roundtrip(workspace):
    client, _, _, _ = workspace
    prefs = client.post("/api/v1/mobile/notification-preferences/status", json={}).json()[
        "preferences"
    ]
    target = next(item for item in prefs if item["category"] == "milestone")

    subscribed = client.post(
        "/api/v1/mobile/notification-preferences/subscription",
        json={
            "category": "milestone",
            "base_version": target["preference_version"],
            "action": "resubscribe",
            "subscription_change_confirmed": True,
        },
    )
    assert subscribed.status_code == 200, subscribed.text
    assert subscribed.json()["preference"]["subscription_state"] == "active"
    assert subscribed.json()["preference"]["wechat_subscription_enabled"] is True

    stale = client.post(
        "/api/v1/mobile/notification-preferences/subscription",
        json={
            "category": "milestone",
            "base_version": target["preference_version"],
            "action": "unsubscribe",
            "subscription_change_confirmed": True,
        },
    )
    assert stale.status_code == 409


def test_runtime_diagnostics_requires_consent_and_is_idempotent(workspace):
    client, _, _, _ = workspace
    event_id = f"evt_{uuid.uuid4().hex}"
    base = {
        "client_event_id": event_id,
        "event_type": "performance",
        "platform": "android",
        "app_version": "1.0.0",
        "build_number": 1,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "metric_name": "cold_start_ms",
        "metric_value": 812.0,
    }

    denied = client.post(
        "/api/v1/mobile/runtime/diagnostics", json={**base, "diagnostics_consent": False}
    )
    assert denied.status_code == 200
    assert denied.json()["accepted"] is False
    assert denied.json()["reason"] == "diagnostics_consent_required"

    accepted = client.post(
        "/api/v1/mobile/runtime/diagnostics", json={**base, "diagnostics_consent": True}
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["accepted"] is True
    assert accepted.json()["deduplicated"] is False

    repeat = client.post(
        "/api/v1/mobile/runtime/diagnostics", json={**base, "diagnostics_consent": True}
    )
    assert repeat.json()["deduplicated"] is True

    off = client.post("/api/v1/mobile/runtime/diagnostics-preference/status", json={})
    assert off.json()["diagnostics_enabled"] is False
    on = client.post(
        "/api/v1/mobile/runtime/diagnostics-preference/change",
        json={"diagnostics_enabled": True},
    )
    assert on.json()["diagnostics_enabled"] is True
    assert (
        client.post(
            "/api/v1/mobile/runtime/diagnostics-preference/status", json={}
        ).json()["diagnostics_enabled"]
        is True
    )


def test_checkin_media_change_attaches_and_revokes(workspace):
    client, ids, actor, _ = workspace
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    preflight = client.post(
        "/api/v1/mobile/media/preflight",
        json={
            "client_request_id": f"mini_{uuid.uuid4().hex}",
            "media_kind": "image",
            "content_type": "image/png",
            "size_bytes": len(png),
            "private_storage_confirmed": True,
        },
    ).json()
    uploaded = client.post(
        "/api/v1/mobile/media/upload",
        data={"upload_ticket": preflight["upload_ticket"]},
        files={"file": ("a.png", png, "image/png")},
    ).json()

    record_id = _create(client, ids, confirmed=True).json()["record_id"]
    state = client.post("/api/v1/mobile/checkins/visibility", json={"record_id": record_id}).json()

    attached = client.post(
        "/api/v1/mobile/checkins/media/change",
        json={
            "record_id": record_id,
            "expected_detail_version": state["version"],
            "client_request_id": f"mini_{uuid.uuid4().hex}",
            "media_kind": "image",
            "operation": "attach",
            "replacement_media_id": uploaded["media_id"],
        },
    )
    assert attached.status_code == 200, attached.text
    assert attached.json()["media_id"] == uploaded["media_id"]
    assert attached.json()["detail_version"] != state["version"]

    removed = client.post(
        "/api/v1/mobile/checkins/media/change",
        json={
            "record_id": record_id,
            "expected_detail_version": attached.json()["detail_version"],
            "client_request_id": f"mini_{uuid.uuid4().hex}",
            "media_kind": "image",
            "operation": "remove",
        },
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["access_revoked"] is True
    assert removed.json()["media_files_removed"] == 1

    detail = client.post(
        "/api/v1/mobile/checkins/detail", json={"record_id": record_id}
    ).json()
    assert detail["image_url"] is None


def test_repair_guidance_returns_steps_and_not_modified(workspace):
    client, ids, _, _ = workspace
    guidance = client.post(
        "/api/v1/mobile/communication/repair-guidance",
        json={"scope": "relationship", "relationship_space_id": str(ids["pair"])},
    )
    assert guidance.status_code == 200, guidance.text
    body = guidance.json()
    assert body["status"] in {"ready", "safety_handoff"}
    assert body["guidance_version"]
    assert body["title"]

    repeat = client.post(
        "/api/v1/mobile/communication/repair-guidance",
        json={
            "scope": "relationship",
            "relationship_space_id": str(ids["pair"]),
            "known_guidance_version": body["guidance_version"],
        },
    )
    assert repeat.json()["not_modified"] is True


def test_offline_drafts_sync_pull_list_discard_and_adopt(workspace):
    client, ids, actor, _ = workspace
    draft_id = f"draft_{uuid.uuid4().hex}"
    payload = {
        "client_draft_id": draft_id,
        "base_revision": 0,
        "local_updated_at": datetime.now(timezone.utc).isoformat(),
        "upload_confirmed": True,
        "draft": {
            "relationship_space_id": str(ids["pair"]),
            "content": "草稿：今晚想说的话。",
            "mood_score": 3,
            "visibility_scope": "private",
        },
    }

    created = client.post("/api/v1/mobile/offline-drafts/sync", json=payload)
    assert created.status_code == 200, created.text
    assert created.json()["revision"] == 1
    assert created.json()["visibility_scope"] == "private"

    dedup = client.post(
        "/api/v1/mobile/offline-drafts/sync",
        json={**payload, "base_revision": 1},
    )
    assert dedup.json()["deduplicated"] is True

    stale = client.post(
        "/api/v1/mobile/offline-drafts/sync",
        json={
            **payload,
            "base_revision": 1,
            "draft": {**payload["draft"], "content": "改过的草稿"},
        },
    )
    assert stale.status_code == 200
    assert stale.json()["revision"] == 2

    pulled = client.post(
        "/api/v1/mobile/offline-drafts/pull", json={"client_draft_id": draft_id}
    )
    assert pulled.status_code == 200, pulled.text
    assert pulled.json()["draft"]["content"] == "改过的草稿"

    listed = client.post(
        "/api/v1/mobile/offline-drafts/list",
        json={"relationship_space_id": str(ids["pair"])},
    )
    assert listed.status_code == 200
    assert len(listed.json()["drafts"]) == 1

    actor["id"] = ids["bob"]
    assert (
        client.post(
            "/api/v1/mobile/offline-drafts/pull", json={"client_draft_id": draft_id}
        ).status_code
        == 404
    )
    actor["id"] = ids["alice"]

    adopted = client.post(
        "/api/v1/mobile/offline-drafts/adopt",
        json={
            "client_draft_id": draft_id,
            "base_revision": 2,
            "adopt_confirmed": True,
        },
    )
    assert adopted.status_code == 200, adopted.text
    assert adopted.json()["status"] == "discarded"
    assert (
        client.post(
            "/api/v1/mobile/offline-drafts/pull", json={"client_draft_id": draft_id}
        ).json()["status"]
        == "discarded"
    )


def test_offline_draft_discard_clears_payload(workspace):
    client, ids, _, _ = workspace
    draft_id = f"draft_{uuid.uuid4().hex}"
    client.post(
        "/api/v1/mobile/offline-drafts/sync",
        json={
            "client_draft_id": draft_id,
            "base_revision": 0,
            "local_updated_at": datetime.now(timezone.utc).isoformat(),
            "upload_confirmed": True,
            "draft": {"content": "不想留的草稿", "visibility_scope": "private"},
        },
    )
    discarded = client.post(
        "/api/v1/mobile/offline-drafts/discard",
        json={
            "client_draft_id": draft_id,
            "base_revision": 1,
            "discard_confirmed": True,
        },
    )
    assert discarded.status_code == 200, discarded.text
    assert discarded.json()["status"] == "discarded"
    assert discarded.json()["payload_hash"] is None
    pulled = client.post(
        "/api/v1/mobile/offline-drafts/pull", json={"client_draft_id": draft_id}
    )
    assert pulled.json()["draft"] is None


def test_push_status_permission_sync_and_receipts(workspace):
    client, _, _, _ = workspace
    installation = f"inst_{uuid.uuid4().hex}"

    status = client.post(
        "/api/v1/mobile/push/status", json={"installation_id": installation}
    )
    assert status.status_code == 200, status.text
    assert status.json()["registration_state"] == "unregistered"
    assert status.json()["next_action"] == "register"

    denied = client.post(
        "/api/v1/mobile/push/permission-sync",
        json={
            "installation_id": installation,
            "platform": "android",
            "provider": "unipush",
            "permission_state": "denied",
            "permission_status_confirmed": True,
        },
    )
    assert denied.status_code == 200, denied.text
    assert denied.json()["permission_state"] == "denied"
    assert denied.json()["next_action"] == "request_permission"

    authorized = client.post(
        "/api/v1/mobile/push/permission-sync",
        json={
            "installation_id": installation,
            "platform": "android",
            "provider": "unipush",
            "permission_state": "authorized",
            "permission_status_confirmed": True,
        },
    )
    assert authorized.json()["permission_state"] == "authorized"

    receipt = client.post(
        "/api/v1/mobile/push/receipts",
        json={"installation_id": installation, "receipt_type": "delivered"},
    )
    assert receipt.status_code == 200, receipt.text
    assert receipt.json()["accepted"] is True


def test_narrative_alignment_and_feedback(workspace):
    client, ids, actor, factory = workspace
    missing = client.post(
        "/api/v1/mobile/communication/alignment",
        json={"relationship_space_id": str(ids["pair"])},
    )
    assert missing.status_code == 200, missing.text
    assert missing.json()["status"] == "not_available"

    async def seed():
        async with factory() as db:
            db.add(
                RelationshipEvent(
                    pair_id=ids["pair"],
                    user_id=ids["alice"],
                    event_type="alignment.generated",
                    payload={
                        "summary": "你们都提到最近有点累。",
                        "divergent_points": ["谁先开口"],
                        "bridge_actions": ["晚饭后聊十分钟"],
                        "confidence": 0.7,
                        "source": "ai",
                    },
                    idempotency_key=f"alignment:{uuid.uuid4().hex}",
                )
            )
            await db.commit()

    asyncio.run(seed())

    alignment = client.post(
        "/api/v1/mobile/communication/alignment",
        json={"relationship_space_id": str(ids["pair"])},
    )
    assert alignment.status_code == 200, alignment.text
    body = alignment.json()
    assert body["status"] == "ready"
    assert body["shared_story"] == "你们都提到最近有点累。"
    assert body["bridge_actions"] == ["晚饭后聊十分钟"]
    assert body["ai_generated"] is True

    repeat = client.post(
        "/api/v1/mobile/communication/alignment",
        json={
            "relationship_space_id": str(ids["pair"]),
            "known_alignment_version": body["alignment_version"],
        },
    )
    assert repeat.json()["not_modified"] is True

    feedback = client.post(
        "/api/v1/mobile/communication/alignment/feedback",
        json={
            "relationship_space_id": str(ids["pair"]),
            "alignment_id": body["alignment_id"],
            "feedback_type": "accurate",
        },
    )
    assert feedback.status_code == 200, feedback.text
    assert feedback.json()["feedback_label"] == "说得准"

    retry = client.post(
        "/api/v1/mobile/communication/alignment/feedback",
        json={
            "relationship_space_id": str(ids["pair"]),
            "alignment_id": body["alignment_id"],
            "feedback_type": "accurate",
        },
    )
    assert retry.json()["deduplicated"] is True

    actor["id"] = ids["outsider"]
    assert (
        client.post(
            "/api/v1/mobile/communication/alignment",
            json={"relationship_space_id": str(ids["pair"])},
        ).status_code
        == 403
    )


def test_migration_roundtrip_on_temporary_database():
    import importlib.util
    from pathlib import Path

    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/2026_09_22_b3d5f7a9c1e2_add_checkin_visibility.py"
    )
    spec = importlib.util.spec_from_file_location("checkin_visibility_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE checkins (id CHAR(36) PRIMARY KEY)")
        conn.exec_driver_sql("CREATE TABLE users (id CHAR(36) PRIMARY KEY)")
        conn.exec_driver_sql("CREATE TABLE pairs (id CHAR(36) PRIMARY KEY)")
        conn.exec_driver_sql("INSERT INTO checkins (id) VALUES ('sentinel-checkin')")
        migration.op = Operations(MigrationContext.configure(conn))
        migration.upgrade()
        inspector = sa.inspect(conn)
        assert inspector.has_table("checkin_visibility_events")
        # 任务 0.3：补充移动端 3 张新表的 upgrade 存在性断言
        assert inspector.has_table("mobile_media_uploads")
        assert inspector.has_table("mobile_offline_drafts")
        assert inspector.has_table("mobile_push_registrations")

        columns = {column["name"] for column in inspector.get_columns("checkins")}
        assert {"visibility_scope", "visibility_version", "sharing_confirmed_at", "visibility_updated_at"} <= columns
        assert inspector.get_columns("checkins")[1]["default"] is not None

        migration.downgrade()
        inspector = sa.inspect(conn)
        assert not inspector.has_table("checkin_visibility_events")
        # 任务 0.3：补充移动端 3 张新表的 downgrade 回滚清理断言
        assert not inspector.has_table("mobile_media_uploads")
        assert not inspector.has_table("mobile_offline_drafts")
        assert not inspector.has_table("mobile_push_registrations")

        assert {c["name"] for c in inspector.get_columns("checkins")} == {"id"}
        assert conn.exec_driver_sql("SELECT id FROM checkins").scalar_one() == "sentinel-checkin"

        migration.upgrade()
        inspector_again = sa.inspect(conn)
        assert inspector_again.has_table("checkin_visibility_events")
        assert inspector_again.has_table("mobile_media_uploads")
        assert inspector_again.has_table("mobile_offline_drafts")
        assert inspector_again.has_table("mobile_push_registrations")
    engine.dispose()


@pytest.fixture
def reports_workspace(monkeypatch):
    from app.api.v1 import reports as reports_api

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    ids = {key: uuid.uuid4() for key in ["alice", "bob", "pair"]}
    captured: list[dict] = []

    async def fake_process(report_id, pair_id, pair_type, content_a, content_b, *args, **kwargs):
        captured.append({"content_a": content_a, "content_b": content_b})

    monkeypatch.setattr(reports_api, "_process_daily_report", fake_process)

    async def seed():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as db:
            for name in ["alice", "bob"]:
                db.add(
                    User(
                        id=ids[name],
                        email=f"{name}@test.invalid",
                        nickname=name,
                        password_hash="unused",
                    )
                )
            db.add(
                Pair(
                    id=ids["pair"],
                    user_a_id=ids["alice"],
                    user_b_id=ids["bob"],
                    type=PairType.COUPLE,
                    status=PairStatus.ACTIVE,
                    invite_code="report-test",
                )
            )
            today = current_local_date()
            db.add(
                Checkin(
                    pair_id=ids["pair"],
                    user_id=ids["alice"],
                    content="这是爱丽丝的私密原文",
                    checkin_date=today,
                    visibility_scope="private",
                    visibility_version=1,
                    mood_score=3,
                    interaction_freq=3,
                    interaction_initiative="me",
                    deep_conversation=True,
                    task_completed=True,
                )
            )
            db.add(
                Checkin(
                    pair_id=ids["pair"],
                    user_id=ids["bob"],
                    content="这是鲍勃的共享原文",
                    checkin_date=today,
                    visibility_scope="shared_summary",
                    visibility_version=1,
                    mood_score=3,
                    interaction_freq=3,
                    interaction_initiative="me",
                    deep_conversation=True,
                    task_completed=True,
                )
            )
            await db.commit()

    asyncio.run(seed())

    async def db_override():
        async with factory() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def user_override():
        async with factory() as db:
            return await db.get(User, ids["alice"])

    app = FastAPI()
    app.include_router(reports_api.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_current_user] = user_override
    with TestClient(app) as client:
        yield client, ids, captured
    asyncio.run(engine.dispose())


def test_private_checkin_never_enters_pair_daily_report(reports_workspace):
    from app.services.checkin_visibility import PARTNER_HIDDEN_REPORT_PLACEHOLDER

    client, ids, captured = reports_workspace
    response = client.post(f"/api/v1/reports/generate-daily?pair_id={ids['pair']}")
    assert response.status_code == 200, response.text
    assert captured, "日报生成任务应已被排入后台"
    payload = captured[0]
    assert payload["content_a"] == PARTNER_HIDDEN_REPORT_PLACEHOLDER
    assert "这是爱丽丝的私密原文" not in payload["content_a"]
    # shared_summary 只使用过滤后的共享摘要，原文同样不进入生成任务
    assert "这是鲍勃的共享原文" not in payload["content_b"]
    assert payload["content_b"]


def test_partner_tags_exclude_crisis_and_image_labels(workspace):
    client, ids, actor, _ = workspace
    created = _create(
        client,
        ids,
        content="今天有点累，但还好。",
        confirmed=True,
        context={"source_type": "text", "intent": "crisis", "risk_level": "high"},
    )
    assert created.status_code == 200, created.text
    record_id = created.json()["record_id"]

    owner = client.post("/api/v1/mobile/checkins/detail", json={"record_id": record_id}).json()
    assert "需要保护" in owner["tags"]

    actor["id"] = ids["bob"]
    partner = client.post(
        "/api/v1/mobile/checkins/detail", json={"record_id": record_id}
    ).json()
    for forbidden in ["需要保护", "需要谨慎处理", "值得留意", "冲突处理中"]:
        assert forbidden not in partner["tags"]
        assert forbidden not in partner["summary"]
    assert "今天有点累" not in partner["summary"]


def test_revoke_invalidates_monthly_report(workspace):
    client, ids, _, factory = workspace
    record_id = _create(client, ids, confirmed=True).json()["record_id"]
    checkin_id = uuid.UUID(record_id)

    async def seed():
        async with factory() as db:
            checkin = await db.get(Checkin, checkin_id)
            db.add(
                Report(
                    pair_id=ids["pair"],
                    type=ReportType.MONTHLY,
                    status=ReportStatus.COMPLETED,
                    content={"summary": "月报里包含了她的原文线索"},
                    health_score=70.0,
                    report_date=checkin.checkin_date,
                )
            )
            await db.commit()

    asyncio.run(seed())

    state = client.post(
        "/api/v1/mobile/checkins/visibility", json={"record_id": record_id}
    ).json()
    revoked = client.post(
        "/api/v1/mobile/checkins/visibility/change",
        json={
            "record_id": record_id,
            "expected_version": state["version"],
            "visibility_scope": "private",
        },
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["reports_invalidated"] >= 1

    async def inspect():
        async with factory() as db:
            report = (
                await db.execute(select(Report).where(Report.type == ReportType.MONTHLY))
            ).scalars().one()
            assert report.content is None
            assert report.status == ReportStatus.PENDING

    asyncio.run(inspect())


def test_shared_summary_report_uses_filtered_summary_not_original(workspace):
    client, ids, actor, factory = workspace
    created = _create(
        client, ids, content="鲍勃今天很累，还说想一个人静静。", confirmed=True
    )
    record_id = uuid.UUID(created.json()["record_id"])

    async def content_for_report():
        from app.services.checkin_visibility import pair_report_content

        async with factory() as db:
            checkin = await db.get(Checkin, record_id)
            return pair_report_content(checkin)

    text = asyncio.run(content_for_report())
    assert "想一个人静静" not in text
    assert "鲍勃今天很累" not in text
    assert "疲惫" in text


def test_private_checkin_never_affects_pair_profile(workspace):
    client, ids, actor, factory = workspace
    _create(client, ids, content="爱丽丝私密：今天很累。", visibility="private")
    actor["id"] = ids["bob"]
    _create(client, ids, content="鲍勃共享：今天还行。", confirmed=True)
    actor["id"] = ids["alice"]

    async def metrics_now():
        from app.services.relationship_intelligence import refresh_profile_snapshot

        async with factory() as db:
            snapshot = await refresh_profile_snapshot(
                db, pair_id=ids["pair"], window_days=7
            )
            await db.commit()
            return dict(snapshot.metrics_json or {})

    first = asyncio.run(metrics_now())
    assert first.get("checkin_count") == 1

    async def delete_and_rebuild():
        from sqlalchemy import delete as sql_delete

        from app.services.relationship_intelligence import refresh_profile_snapshot

        async with factory() as db:
            await db.execute(
                sql_delete(RelationshipProfileSnapshot).where(
                    RelationshipProfileSnapshot.pair_id == ids["pair"]
                )
            )
            await db.commit()
        async with factory() as db:
            snapshot = await refresh_profile_snapshot(
                db, pair_id=ids["pair"], window_days=7
            )
            await db.commit()
            return dict(snapshot.metrics_json or {})

    rebuilt = asyncio.run(delete_and_rebuild())
    assert rebuilt.get("checkin_count") == 1


@pytest.fixture
def report_task_workspace(monkeypatch):
    """把 reports 模块的后台 session 指向临时库，用于验证任务作废逻辑。"""
    from app.api.v1 import reports as reports_api

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    ids = {key: uuid.uuid4() for key in ["alice", "bob", "pair"]}

    async def seed():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as db:
            for name in ["alice", "bob"]:
                db.add(
                    User(
                        id=ids[name],
                        email=f"{name}@test.invalid",
                        nickname=name,
                        password_hash="unused",
                    )
                )
            db.add(
                Pair(
                    id=ids["pair"],
                    user_a_id=ids["alice"],
                    user_b_id=ids["bob"],
                    type=PairType.COUPLE,
                    status=PairStatus.ACTIVE,
                    invite_code="report-task-test",
                )
            )
            await db.commit()

    asyncio.run(seed())
    monkeypatch.setattr(reports_api, "async_session", factory)
    yield ids, factory
    asyncio.run(engine.dispose())


def test_revoked_source_discards_queued_report(report_task_workspace):
    ids, factory = report_task_workspace

    async def scenario():
        from app.api.v1.reports import _process_daily_report
        from app.services.checkin_visibility import report_sources_authorized

        today = current_local_date()
        async with factory() as db:
            checkin = Checkin(
                pair_id=ids["pair"],
                user_id=ids["alice"],
                content="撤回前的原文",
                checkin_date=today,
                visibility_scope="private",  # 已撤回
                visibility_version=2,
            )
            db.add(checkin)
            report = Report(
                pair_id=ids["pair"],
                type=ReportType.DAILY,
                status=ReportStatus.PENDING,
                content=None,
                report_date=today,
            )
            db.add(report)
            await db.commit()
            await db.refresh(checkin)
            await db.refresh(report)
            checkin_id, report_id = checkin.id, report.id

        # 入队时快照（当时是共享态、版本 1）
        source_versions = [[str(checkin_id), 1]]
        async with factory() as db:
            assert await report_sources_authorized(db, source_versions) is False

        await _process_daily_report(
            report_id,
            ids["pair"],
            "couple",
            "撤回前的原文",
            "对方内容",
            str(ids["alice"]),
            "cloud",
            source_versions=source_versions,
        )

        async with factory() as db:
            row = await db.get(Report, report_id)
            assert row.status == ReportStatus.PENDING
            assert row.content is None
            discarded = (
                await db.execute(
                    select(RelationshipEvent).where(
                        RelationshipEvent.event_type == "report.discarded"
                    )
                )
            ).scalars().all()
            assert len(discarded) == 1
            assert discarded[0].payload["reason"] == "source_revoked_before_run"

    asyncio.run(scenario())


def test_revoked_source_during_run_discards_result(report_task_workspace, monkeypatch):
    ids, factory = report_task_workspace

    async def scenario():
        from app.api.v1 import reports as reports_api

        today = current_local_date()
        async with factory() as db:
            checkin = Checkin(
                pair_id=ids["pair"],
                user_id=ids["alice"],
                content="运行期间的原文",
                checkin_date=today,
                visibility_scope="shared_summary",
                visibility_version=1,
            )
            db.add(checkin)
            report = Report(
                pair_id=ids["pair"],
                type=ReportType.DAILY,
                status=ReportStatus.PENDING,
                content=None,
                report_date=today,
            )
            db.add(report)
            await db.commit()
            await db.refresh(checkin)
            await db.refresh(report)
            checkin_id, report_id = checkin.id, report.id

        source_versions = [[str(checkin_id), 1]]

        async def fake_generate(pair_type, content_a, content_b):
            # 模拟"生成过程中用户撤回共享"
            async with factory() as db:
                row = await db.get(Checkin, checkin_id)
                row.visibility_scope = "private"
                row.visibility_version = 2
                await db.commit()
            return {"health_score": 80.0, "summary": "不该被写回的内容"}

        monkeypatch.setattr(reports_api, "generate_daily_report", fake_generate)

        await reports_api._process_daily_report(
            report_id,
            ids["pair"],
            "couple",
            "运行期间的原文",
            "对方内容",
            str(ids["alice"]),
            "cloud",
            source_versions=source_versions,
        )

        async with factory() as db:
            row = await db.get(Report, report_id)
            assert row.status == ReportStatus.PENDING
            assert row.content is None
            discarded = (
                await db.execute(
                    select(RelationshipEvent).where(
                        RelationshipEvent.event_type == "report.discarded"
                    )
                )
            ).scalars().all()
            assert discarded[0].payload["reason"] == "source_revoked_during_run"

    asyncio.run(scenario())


def test_alignment_excludes_private_checkin_from_dual_sources(workspace):
    client, ids, actor, factory = workspace
    _create(client, ids, content="爱丽丝私密原文", visibility="private")
    actor["id"] = ids["bob"]
    _create(client, ids, content="鲍勃共享原文", confirmed=True)
    actor["id"] = ids["alice"]

    async def dual():
        from app.api.v1.insights_routes.shared import get_latest_dual_checkins

        async with factory() as db:
            pair = await db.get(Pair, ids["pair"])
            return await get_latest_dual_checkins(db, pair)

    checkin_a, checkin_b = asyncio.run(dual())
    # private 被过滤后，当天不再构成"双方都有记录"
    assert checkin_a is None and checkin_b is None


def test_alignment_serializes_filtered_summary_not_original(workspace):
    client, ids, actor, factory = workspace
    _create(client, ids, content="爱丽丝今天很累，想一个人静静。", confirmed=True)
    actor["id"] = ids["bob"]
    _create(client, ids, content="鲍勃还行。", confirmed=True)
    actor["id"] = ids["alice"]

    async def payloads():
        from app.api.v1.insights_routes.shared import (
            get_latest_dual_checkins,
            serialize_checkin,
        )

        async with factory() as db:
            pair = await db.get(Pair, ids["pair"])
            checkin_a, checkin_b = await get_latest_dual_checkins(db, pair)
            return serialize_checkin(checkin_a, "A"), serialize_checkin(checkin_b, "B")

    payload_a, payload_b = asyncio.run(payloads())
    assert "想一个人静静" not in payload_a["content"]
    assert "爱丽丝今天很累" not in payload_a["content"]
    assert "疲惫" in payload_a["content"]
