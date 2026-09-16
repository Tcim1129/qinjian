import asyncio
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import uuid
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1 import upload as upload_api
from app.ai.asr import ASRTranscriptionResult
from app.schemas import CheckinResponse, UserResponse
from app.services.request_cooldown_store import close_request_cooldown_store
from app.services.upload_access import (
    build_upload_access_url,
    build_upload_response_payload,
    build_scoped_upload_access_url,
    build_scoped_upload_response_payload,
    get_upload_owner_scope,
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


def test_scoped_upload_access_url_denies_unknown_local_upload():
    denied = asyncio.run(
        build_scoped_upload_access_url(
            None,
            "/uploads/images/orphan.png",
            actor_user_id=uuid.uuid4(),
        )
    )

    assert denied is None


def test_scoped_upload_access_url_binds_actor_to_signature(monkeypatch):
    actor_user_id = uuid.uuid4()

    async def fake_get_upload_owner_scope(db, upload_path):
        return {"scope": "user", "user_id": actor_user_id, "pair_id": None}

    monkeypatch.setattr(
        "app.services.upload_access.get_upload_owner_scope",
        fake_get_upload_owner_scope,
    )

    access_url = asyncio.run(
        build_scoped_upload_access_url(
            object(),
            "/uploads/images/private.png",
            actor_user_id=actor_user_id,
        )
    )
    parsed = urlparse(access_url)
    query = parse_qs(parsed.query)

    assert query["actor"][0] == str(actor_user_id)
    assert verify_upload_access(
        "/uploads/images/private.png",
        int(query["expires"][0]),
        query["sig"][0],
        actor_user_id=actor_user_id,
        scope=query["scope"][0],
        owner_user_id=query["owner"][0],
    )
    assert not verify_upload_access(
        "/uploads/images/private.png",
        int(query["expires"][0]),
        query["sig"][0],
        actor_user_id=uuid.uuid4(),
        scope=query["scope"][0],
        owner_user_id=query["owner"][0],
    )


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
        client_context={
            "source_type": "text",
            "intent": "daily",
            "archive_insight": {
                "title": "先记最关键的一句",
                "recommendations": ["只对齐一个点"],
            },
        },
        client_precheck={
            "source_type": "text",
            "intent": "daily",
            "archive_insight": {
                "title": "先记最关键的一句",
                "recommendations": ["只对齐一个点"],
            },
        },
        checkin_date=now.date(),
        created_at=now,
    )

    assert user.avatar_url.startswith("/api/v1/upload/access/images/avatar.png?")
    assert user.wechat_avatar == "https://example.com/avatar.png"
    assert checkin.image_url.startswith("/api/v1/upload/access/images/checkin.png?")
    assert checkin.voice_url.startswith("/api/v1/upload/access/voices/checkin.mp3?")
    assert checkin.client_context.archive_insight["title"] == "先记最关键的一句"
    assert checkin.client_precheck.archive_insight["recommendations"] == ["只对齐一个点"]


@pytest.mark.anyio
async def test_save_file_records_owner_scope_for_fresh_upload(monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.database import Base
    from app.models import User

    upload_root = (
        Path(__file__).resolve().parents[1]
        / "tmp"
        / "test-uploads"
        / uuid.uuid4().hex
    )
    monkeypatch.setattr(upload_api.settings, "UPLOAD_DIR", str(upload_root))

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    class FakeUpload:
        content_type = "image/png"
        filename = "demo.png"

        def __init__(self):
            self._chunks = [b"abc"]

        async def read(self, _size):
            if self._chunks:
                return self._chunks.pop(0)
            return b""

    try:
        async with session_factory() as db:
            user = User(
                email="fresh-upload-owner@example.com",
                nickname="owner",
                password_hash="not-used",
            )
            db.add(user)
            await db.flush()

            payload = await upload_api._save_file(
                FakeUpload(),
                "images",
                db=db,
                actor_user_id=user.id,
            )
            owner = await get_upload_owner_scope(db, payload["url"])

            assert owner is not None
            assert owner["scope"] == "user"
            assert str(owner["user_id"]) == str(user.id)
    finally:
        await engine.dispose()


def test_normalize_upload_storage_path_strips_querystring():
    assert (
        normalize_upload_storage_path("/uploads/images/demo.png?foo=bar")
        == "/uploads/images/demo.png"
    )


def test_normalize_upload_storage_path_accepts_signed_access_url():
    assert (
        normalize_upload_storage_path(
            "/api/v1/upload/access/images/demo.png?expires=1&sig=test"
        )
        == "/uploads/images/demo.png"
    )


def test_normalize_image_analysis_keeps_full_emotion_profile_but_limits_display():
    payload = upload_api._normalize_image_analysis(
        {
            "scene_summary": "聊天截图里双方在修复误会",
            "mood": "委屈里带着想靠近",
            "mood_tags": ["委屈", "期待", "防御", "疲惫"],
            "display_mood_tags": ["委屈", "期待", "克制"],
            "primary_mood": "委屈",
            "secondary_moods": ["期待", "防御", "疲惫"],
            "emotion_weights": [
                {"tag": "委屈", "score": 0.42, "tone": "negative"},
                {"tag": "期待", "score": 0.26, "tone": "positive"},
                {"tag": "防御", "score": 0.18, "tone": "protective"},
                {"tag": "疲惫", "score": 0.14, "tone": "negative"},
            ],
            "emotion_blend_summary": "委屈里带着想修复的期待。",
        }
    )

    assert payload["mood_tags"] == ["委屈", "期待", "克制"]
    assert payload["user_facing"]["display_mood_tags"] == ["委屈", "期待", "克制"]
    assert payload["emotion_profile"]["all_mood_tags"] == ["委屈", "期待", "防御", "疲惫"]
    assert len(payload["emotion_profile"]["emotion_weights"]) == 4
    assert payload["emotion_blend_summary"] == "委屈里带着想修复的期待。"


def test_openapi_includes_private_upload_access_route():
    schema = app.openapi()

    assert "/api/v1/upload/access/{subdir}/{filename}" in schema["paths"]


def test_transcribe_route_returns_chinese_language_and_emotion_labels(monkeypatch):
    async def override_current_user():
        return SimpleNamespace(id=uuid.uuid4())

    class DummyDB:
        async def commit(self):
            return None

    async def override_get_db():
        yield DummyDB()

    async def fake_transcribe_audio_result(_file_path):
        return ASRTranscriptionResult(
            text="今天我其实不是想吵架，我只是希望对方能先听懂我的委屈。",
            provider="qwen3",
            model="qwen3-asr-flash",
            audio_info={"language": "zh", "emotion": "neutral"},
        )

    async def noop_log_privacy_event(*_args, **_kwargs):
        return None

    @contextmanager
    def noop_privacy_scope(**_kwargs):
        yield

    monkeypatch.setattr(upload_api, "transcribe_audio_result", fake_transcribe_audio_result)
    monkeypatch.setattr(upload_api, "log_privacy_event", noop_log_privacy_event)
    monkeypatch.setattr(upload_api, "privacy_audit_scope", noop_privacy_scope)

    local_app = FastAPI()
    local_app.include_router(upload_api.router)
    local_app.dependency_overrides[upload_api.get_current_user] = override_current_user
    local_app.dependency_overrides[upload_api.get_db] = override_get_db

    wav_stub = b"RIFF\x24\x00\x00\x00WAVEfmt "

    with TestClient(local_app, raise_server_exceptions=False) as client:
        response = client.post(
            "/upload/transcribe",
            files={"file": ("demo.wav", wav_stub, "audio/wav")},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["language"] == "中文"
    assert payload["language_code"] == "zh"
    assert payload["emotion"] == "平稳"
    assert payload["emotion_code"] == "neutral"
    assert payload["emotion_summary"]["sentiment_label"] == "偏负向"
    assert payload["emotion_summary"]["mood_label"] == "委屈"
    assert payload["emotion_summary"]["score"] >= 5
    assert payload["audio_info"]["language_label"] == "中文"
    assert payload["audio_info"]["emotion_label"] == "平稳"
    assert payload["transcript_language"] == {
        "code": "zh",
        "label": "中文",
    }
    assert payload["voice_emotion"] == {
        "code": "neutral",
        "label": "平稳",
    }
    assert payload["content_emotion"]["sentiment"] == "negative"
    assert payload["content_emotion"]["sentiment_label"] == "偏负向"
    assert payload["content_emotion"]["mood_label"] == "委屈"


def test_upload_image_route_accepts_png_and_returns_private_payload(monkeypatch):
    async def override_current_user():
        return SimpleNamespace(id=uuid.uuid4())

    class DummyDB:
        async def commit(self):
            return None

    async def override_get_db():
        yield DummyDB()

    async def fake_save_file(file, subdir, **kwargs):
        assert subdir == "images"
        assert kwargs["actor_user_id"] is not None
        return {
            "url": "/uploads/images/demo.png",
            "filename": "demo.png",
            "size": 128,
            "access_url": "/api/v1/upload/access/images/demo.png?expires=1&sig=test",
        }

    async def noop_log_privacy_event(*_args, **_kwargs):
        return None

    @contextmanager
    def noop_privacy_scope(**_kwargs):
        yield

    monkeypatch.setattr(upload_api, "_save_file", fake_save_file)
    monkeypatch.setattr(upload_api, "log_privacy_event", noop_log_privacy_event)
    monkeypatch.setattr(upload_api, "privacy_audit_scope", noop_privacy_scope)

    local_app = FastAPI()
    local_app.include_router(upload_api.router)
    local_app.dependency_overrides[upload_api.get_current_user] = override_current_user
    local_app.dependency_overrides[upload_api.get_db] = override_get_db

    png_stub = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 32)

    with TestClient(local_app, raise_server_exceptions=False) as client:
        response = client.post(
            "/upload/image",
            files={"file": ("demo.png", png_stub, "image/png")},
        )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "url": "/uploads/images/demo.png",
        "filename": "demo.png",
        "size": 128,
        "access_url": "/api/v1/upload/access/images/demo.png?expires=1&sig=test",
    }


def test_upload_voice_route_accepts_webm_with_codec_parameter(monkeypatch):
    async def override_current_user():
        return SimpleNamespace(id=uuid.uuid4())

    class DummyDB:
        async def commit(self):
            return None

    async def override_get_db():
        yield DummyDB()

    async def fake_save_file(file, subdir, **kwargs):
        assert subdir == "voices"
        assert file.content_type == "audio/webm;codecs=opus"
        assert kwargs["actor_user_id"] is not None
        return {
            "url": "/uploads/voices/demo.webm",
            "filename": "demo.webm",
            "size": 256,
            "access_url": "/api/v1/upload/access/voices/demo.webm?expires=1&sig=test",
        }

    async def noop_log_privacy_event(*_args, **_kwargs):
        return None

    @contextmanager
    def noop_privacy_scope(**_kwargs):
        yield

    monkeypatch.setattr(upload_api, "_save_file", fake_save_file)
    monkeypatch.setattr(upload_api, "log_privacy_event", noop_log_privacy_event)
    monkeypatch.setattr(upload_api, "privacy_audit_scope", noop_privacy_scope)

    local_app = FastAPI()
    local_app.include_router(upload_api.router)
    local_app.dependency_overrides[upload_api.get_current_user] = override_current_user
    local_app.dependency_overrides[upload_api.get_db] = override_get_db

    webm_stub = b"\x1aE\xdf\xa3" + (b"\x00" * 32)

    with TestClient(local_app, raise_server_exceptions=False) as client:
        response = client.post(
            "/upload/voice",
            files={"file": ("demo.webm", webm_stub, "audio/webm;codecs=opus")},
        )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "url": "/uploads/voices/demo.webm",
        "filename": "demo.webm",
        "size": 256,
        "access_url": "/api/v1/upload/access/voices/demo.webm?expires=1&sig=test",
    }


def test_transcribe_voice_accepts_webm_with_codec_parameter(monkeypatch):
    async def override_current_user():
        return SimpleNamespace(id=uuid.uuid4())

    class DummyDB:
        async def commit(self):
            return None

    async def override_get_db():
        yield DummyDB()

    async def fake_transcribe_audio_result(_file_path):
        return ASRTranscriptionResult(
            text="这段录音来自浏览器实时录音。",
            provider="qwen3",
            model="qwen3-asr-flash",
            audio_info={"language": "zh", "emotion": "neutral"},
        )

    async def noop_log_privacy_event(*_args, **_kwargs):
        return None

    @contextmanager
    def noop_privacy_scope(**_kwargs):
        yield

    monkeypatch.setattr(upload_api, "transcribe_audio_result", fake_transcribe_audio_result)
    monkeypatch.setattr(upload_api, "log_privacy_event", noop_log_privacy_event)
    monkeypatch.setattr(upload_api, "privacy_audit_scope", noop_privacy_scope)

    local_app = FastAPI()
    local_app.include_router(upload_api.router)
    local_app.dependency_overrides[upload_api.get_current_user] = override_current_user
    local_app.dependency_overrides[upload_api.get_db] = override_get_db

    webm_stub = b"\x1aE\xdf\xa3" + (b"\x00" * 32)

    with TestClient(local_app, raise_server_exceptions=False) as client:
        response = client.post(
            "/upload/transcribe",
            files={"file": ("demo.webm", webm_stub, "audio/webm;codecs=opus")},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["text"] == "这段录音来自浏览器实时录音。"
    assert payload["language_code"] == "zh"
    assert payload["emotion_code"] == "neutral"


def test_analyze_image_route_returns_storage_strategy_without_persist(monkeypatch):
    asyncio.run(close_request_cooldown_store())
    async def override_current_user():
        return SimpleNamespace(id=uuid.uuid4())

    class DummyDB:
        async def commit(self):
            return None

    async def override_get_db():
        yield DummyDB()

    async def fake_save_temp_file(file, subdir):
        assert subdir == "tmp_image_analysis"
        return (
            "C:/tmp/demo.png",
            "/uploads/tmp_image_analysis/demo.png",
            256,
        )

    async def fake_analyze_image(image_path, context=""):
        assert image_path == "/uploads/tmp_image_analysis/demo.png"
        assert "聊天截图" in context
        return {
            "scene_summary": "一张情侣聊天截图，双方在修复误会。",
            "mood": "温柔里带着一点委屈",
            "mood_tags": ["委屈", "期待"],
            "relationship_stage": "修复中",
            "interaction_signal": "双方都在放低防御。",
            "social_signal": "出现了安抚与确认回应。",
            "risk_level": "watch",
            "risk_flags": ["情绪还比较脆弱"],
            "care_points": ["适合记录被理解的瞬间"],
            "privacy_sensitivity": "high",
            "privacy_reasons": ["包含聊天截图"],
            "retention_recommendation": "analysis_only",
            "retention_reason": "更适合只保留分析结果。",
            "score": 8,
        }

    @contextmanager
    def noop_privacy_scope(**_kwargs):
        yield

    monkeypatch.setattr(upload_api, "_save_temp_file", fake_save_temp_file)
    monkeypatch.setattr(upload_api, "analyze_image", fake_analyze_image)
    monkeypatch.setattr(upload_api, "privacy_audit_scope", noop_privacy_scope)

    local_app = FastAPI()
    local_app.include_router(upload_api.router)
    local_app.dependency_overrides[upload_api.get_current_user] = override_current_user
    local_app.dependency_overrides[upload_api.get_db] = override_get_db

    png_stub = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 32)
    with TestClient(local_app, raise_server_exceptions=False) as client:
        response = client.post(
            "/upload/image/analyze",
            data={
                "context": "聊天截图，想看看图里透露了什么",
                "persist": "false",
                "privacy_mode": "local_first",
            },
            files={"file": ("demo.png", png_stub, "image/png")},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "saved_upload" not in payload
    assert payload["analysis"]["scene_summary"] == "一张情侣聊天截图，双方在修复误会。"
    assert payload["analysis"]["privacy_sensitivity_label"] == "高敏感"
    assert payload["storage"]["mode"] == "analysis_only"
    assert payload["storage"]["retention_recommendation"] == "analysis_only"
    assert payload["storage"]["download_available"] is False
    asyncio.run(close_request_cooldown_store())


def test_analyze_image_route_only_returns_result_layer_even_when_persist_requested(monkeypatch):
    asyncio.run(close_request_cooldown_store())
    async def override_current_user():
        return SimpleNamespace(id=uuid.uuid4())

    class DummyDB:
        async def commit(self):
            return None

    async def override_get_db():
        yield DummyDB()

    async def fake_save_temp_file(file, subdir):
        assert subdir == "tmp_image_analysis"
        return (
            "C:/tmp/persisted.png",
            "/uploads/tmp_image_analysis/persisted.png",
            512,
        )

    async def fake_analyze_image(image_path, context=""):
        assert image_path == "/uploads/tmp_image_analysis/persisted.png"
        return {
            "scene_summary": "两个人坐在一起平静聊天。",
            "mood": "平静而靠近",
            "mood_tags": ["平静", "期待"],
            "relationship_stage": "日常靠近",
            "interaction_signal": "互动比较稳定。",
            "social_signal": "没有明显的防御信号。",
            "risk_level": "none",
            "risk_flags": [],
            "care_points": ["适合记录这类平稳时刻"],
            "privacy_sensitivity": "low",
            "privacy_reasons": [],
            "retention_recommendation": "persist",
            "retention_reason": "这张图适合连同记录一起保存。",
            "score": 7,
        }

    @contextmanager
    def noop_privacy_scope(**_kwargs):
        yield

    monkeypatch.setattr(upload_api, "_save_temp_file", fake_save_temp_file)
    monkeypatch.setattr(upload_api, "analyze_image", fake_analyze_image)
    monkeypatch.setattr(upload_api, "privacy_audit_scope", noop_privacy_scope)

    local_app = FastAPI()
    local_app.include_router(upload_api.router)
    local_app.dependency_overrides[upload_api.get_current_user] = override_current_user
    local_app.dependency_overrides[upload_api.get_db] = override_get_db

    png_stub = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 32)
    with TestClient(local_app, raise_server_exceptions=False) as client:
        response = client.post(
            "/upload/image/analyze",
            data={
                "context": "普通合照",
                "persist": "true",
                "privacy_mode": "cloud",
            },
            files={"file": ("demo.png", png_stub, "image/png")},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "saved_upload" not in payload
    assert payload["storage"]["mode"] == "analysis_only"
    assert payload["storage"]["label"] == "已生成分析结果，原图不会通过分析接口回传"
    assert "私有上传" in payload["storage"]["reason"]
    asyncio.run(close_request_cooldown_store())


def test_analyze_image_route_rate_limits_repeated_requests(monkeypatch):
    asyncio.run(close_request_cooldown_store())
    user_id = uuid.uuid4()

    async def override_current_user():
        return SimpleNamespace(id=user_id)

    class DummyDB:
        async def commit(self):
            return None

    async def override_get_db():
        yield DummyDB()

    async def fake_save_temp_file(file, subdir):
        return (
            "C:/tmp/rate-limit.png",
            "/uploads/tmp_image_analysis/rate-limit.png",
            256,
        )

    async def fake_analyze_image(image_path, context=""):
        return {
            "scene_summary": "一张普通合照。",
            "mood": "平静",
            "mood_tags": ["平静"],
            "relationship_stage": "日常",
            "interaction_signal": "互动稳定。",
            "social_signal": "没有明显异常。",
            "risk_level": "none",
            "risk_flags": [],
            "care_points": ["可以保留这类时刻"],
            "privacy_sensitivity": "low",
            "privacy_reasons": [],
            "retention_recommendation": "analysis_only",
            "retention_reason": "当前只保留分析结果更稳妥。",
            "score": 7,
        }

    @contextmanager
    def noop_privacy_scope(**_kwargs):
        yield

    monkeypatch.setattr(upload_api, "_save_temp_file", fake_save_temp_file)
    monkeypatch.setattr(upload_api, "analyze_image", fake_analyze_image)
    monkeypatch.setattr(upload_api, "privacy_audit_scope", noop_privacy_scope)

    local_app = FastAPI()
    local_app.include_router(upload_api.router)
    local_app.dependency_overrides[upload_api.get_current_user] = override_current_user
    local_app.dependency_overrides[upload_api.get_db] = override_get_db

    png_stub = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 32)
    try:
        with TestClient(local_app, raise_server_exceptions=False) as client:
            responses = [
                client.post(
                    "/upload/image/analyze",
                    data={
                        "context": "普通合照",
                        "persist": "false",
                        "privacy_mode": "cloud",
                    },
                    files={"file": ("demo.png", png_stub, "image/png")},
                )
                for _ in range(3)
            ]

        assert [response.status_code for response in responses[:2]] == [200, 200]
        assert responses[2].status_code == 429, responses[2].text
        assert "秒后再试" in responses[2].json()["detail"]
    finally:
        asyncio.run(close_request_cooldown_store())
