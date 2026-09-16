from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

import app.main as main_module
from app.core.config import settings


class _DummyConnection:
    async def run_sync(self, fn):
        return fn(None)


class _DummyEngineBegin:
    async def __aenter__(self):
        return _DummyConnection()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _DummyEngine:
    def begin(self):
        return _DummyEngineBegin()


@pytest.mark.anyio
async def test_lifespan_rejects_test_popup_in_non_debug_mode(monkeypatch):
    monkeypatch.setattr(main_module.settings, "DEBUG", False)
    monkeypatch.setattr(main_module.settings, "PHONE_CODE_TEST_POPUP_ENABLED", True)
    monkeypatch.setattr(main_module.settings, "PHONE_CODE_DEBUG_RETURN", False)
    monkeypatch.setattr(main_module.settings, "SECRET_KEY", "0123456789abcdef0123456789abcdef")
    monkeypatch.setattr(main_module.settings, "DATABASE_URL", "postgresql+psycopg://safe:safe@localhost:5432/qinjian")
    monkeypatch.setattr(main_module, "engine", _DummyEngine())
    monkeypatch.setattr(main_module.Base.metadata, "create_all", lambda _conn: None)

    with pytest.raises(RuntimeError, match="验证码测试弹窗"):
        async with main_module.lifespan(main_module.app):
            pass


def test_localhost_cors_regex_is_debug_only(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    assert settings.frontend_origin_regex() is None

    monkeypatch.setattr(settings, "DEBUG", True)
    assert "localhost" in settings.frontend_origin_regex()
