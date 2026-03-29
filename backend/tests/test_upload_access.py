import asyncio
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse
import uuid

from app.main import app
from app.schemas import CheckinResponse, UserResponse
from app.services.upload_access import (
    build_upload_access_url,
    build_upload_response_payload,
    build_scoped_upload_access_url,
    build_scoped_upload_response_payload,
    normalize_upload_storage_path,
    verify_upload_access,
)


def test_build_upload_access_url_signs_local_upload_path():
    storage_path = "/uploads/images/demo.png"

    access_url = build_upload_access_url(storage_path)

    parsed = urlparse(access_url)
    query = parse_qs(parsed.query)
    expires = int(query["expires"][0])
    signature = query["sig"][0]

    assert parsed.path == "/api/v1/upload/access/images/demo.png"
    assert verify_upload_access(storage_path, expires, signature) is True


def test_upload_response_payload_exposes_stable_storage_path_and_private_access_url():
    payload = build_upload_response_payload("/uploads/voices/demo.mp3", "demo.mp3", 123)

    assert payload["url"] == "/uploads/voices/demo.mp3"
    assert payload["filename"] == "demo.mp3"
    assert payload["size"] == 123
    assert payload["access_url"].startswith("/api/v1/upload/access/voices/demo.mp3?")


def test_scoped_upload_access_url_respects_user_scope(monkeypatch):
    owner_user_id = uuid.uuid4()

    async def fake_get_upload_owner_scope(db, upload_path):
        return {"scope": "user", "user_id": owner_user_id, "pair_id": None}

    monkeypatch.setattr(
        "app.services.upload_access.get_upload_owner_scope",
        fake_get_upload_owner_scope,
    )

    allowed = asyncio.run(
        build_scoped_upload_access_url(
            object(),
            "/uploads/images/private.png",
            actor_user_id=owner_user_id,
        )
    )
    denied = asyncio.run(
        build_scoped_upload_access_url(
            object(),
            "/uploads/images/private.png",
            actor_user_id=uuid.uuid4(),
        )
    )

    assert allowed.startswith("/api/v1/upload/access/images/private.png?")
    assert denied is None


def test_scoped_upload_response_payload_can_use_explicit_owner_scope():
    actor_user_id = uuid.uuid4()

    payload = asyncio.run(
        build_scoped_upload_response_payload(
            None,
            "/uploads/images/demo-owner.png",
            "demo-owner.png",
            456,
            actor_user_id=actor_user_id,
            owner_scope={"scope": "user", "user_id": actor_user_id, "pair_id": None},
        )
    )

    assert payload["url"] == "/uploads/images/demo-owner.png"
    assert payload["size"] == 456
    assert payload["access_url"].startswith(
        "/api/v1/upload/access/images/demo-owner.png?"
    )


def test_response_models_convert_local_uploads_to_signed_access_urls():
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    user = UserResponse(
        id=uuid.uuid4(),
        email="tester@example.com",
        nickname="tester",
        avatar_url="/uploads/images/avatar.png",
        wechat_avatar="https://example.com/avatar.png",
        created_at=now,
    )
    checkin = CheckinResponse(
        id=uuid.uuid4(),
        pair_id=None,
        user_id=uuid.uuid4(),
        content="hello",
        image_url="/uploads/images/checkin.png",
        voice_url="/uploads/voices/checkin.mp3",
        mood_tags=None,
        sentiment_score=None,
        mood_score=None,
        interaction_freq=None,
        interaction_initiative=None,
        deep_conversation=None,
        task_completed=None,
        checkin_date=now.date(),
        created_at=now,
    )

    assert user.avatar_url.startswith("/api/v1/upload/access/images/avatar.png?")
    assert user.wechat_avatar == "https://example.com/avatar.png"
    assert checkin.image_url.startswith("/api/v1/upload/access/images/checkin.png?")
    assert checkin.voice_url.startswith("/api/v1/upload/access/voices/checkin.mp3?")


def test_normalize_upload_storage_path_strips_querystring():
    assert (
        normalize_upload_storage_path("/uploads/images/demo.png?foo=bar")
        == "/uploads/images/demo.png"
    )


def test_openapi_includes_private_upload_access_route():
    schema = app.openapi()

    assert "/api/v1/upload/access/{subdir}/{filename}" in schema["paths"]
