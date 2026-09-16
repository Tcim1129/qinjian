from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import request_cooldown_store
from app.services.request_cooldown_store import (
    close_request_cooldown_store,
    consume_request_cooldown,
)


def test_request_cooldown_store_blocks_after_limit():
    asyncio.run(close_request_cooldown_store())
    try:
        asyncio.run(
            consume_request_cooldown(
                bucket="test-bucket",
                scope_key="demo-user",
                window_seconds=60,
                max_attempts=2,
                limit_message="测试请求太频繁了",
            )
        )
        asyncio.run(
            consume_request_cooldown(
                bucket="test-bucket",
                scope_key="demo-user",
                window_seconds=60,
                max_attempts=2,
                limit_message="测试请求太频繁了",
            )
        )

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                consume_request_cooldown(
                    bucket="test-bucket",
                    scope_key="demo-user",
                    window_seconds=60,
                    max_attempts=2,
                    limit_message="测试请求太频繁了",
                )
            )

        assert exc.value.status_code == 429
        assert "秒后再试" in exc.value.detail
    finally:
        asyncio.run(close_request_cooldown_store())


def test_request_cooldown_store_can_be_bypassed_for_relaxed_test_accounts():
    asyncio.run(close_request_cooldown_store())
    try:
        for _ in range(5):
            asyncio.run(
                consume_request_cooldown(
                    bucket="test-bypass-bucket",
                    scope_key="demo-test-account",
                    window_seconds=60,
                    max_attempts=1,
                    limit_message="测试请求太频繁了",
                    bypass=True,
                )
            )

        asyncio.run(
            consume_request_cooldown(
                bucket="test-bypass-bucket",
                scope_key="demo-test-account",
                window_seconds=60,
                max_attempts=1,
                limit_message="测试请求太频繁了",
            )
        )
    finally:
        asyncio.run(close_request_cooldown_store())


def test_request_cooldown_store_falls_back_when_backend_times_out():
    class TimeoutStore:
        async def get(self, key: str):
            raise TimeoutError("redis timed out")

        async def set(self, key: str, attempts: list, *, ttl_seconds: int) -> None:
            raise TimeoutError("redis timed out")

        async def delete(self, key: str) -> None:
            raise TimeoutError("redis timed out")

        async def close(self) -> None:
            return None

    asyncio.run(close_request_cooldown_store())
    request_cooldown_store._REQUEST_COOLDOWN_STORE = TimeoutStore()
    try:
        asyncio.run(
            consume_request_cooldown(
                bucket="timeout-bucket",
                scope_key="demo-user",
                window_seconds=60,
                max_attempts=2,
                limit_message="测试请求太频繁了",
            )
        )
        asyncio.run(
            consume_request_cooldown(
                bucket="timeout-bucket",
                scope_key="demo-user",
                window_seconds=60,
                max_attempts=2,
                limit_message="测试请求太频繁了",
            )
        )

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                consume_request_cooldown(
                    bucket="timeout-bucket",
                    scope_key="demo-user",
                    window_seconds=60,
                    max_attempts=2,
                    limit_message="测试请求太频繁了",
                )
            )

        assert exc.value.status_code == 429
    finally:
        asyncio.run(close_request_cooldown_store())


def test_request_cooldown_redis_client_uses_short_socket_timeouts(monkeypatch):
    calls = {}

    def fake_from_url(url, **kwargs):
        calls["url"] = url
        calls["kwargs"] = kwargs
        return SimpleNamespace()

    monkeypatch.setitem(
        sys.modules,
        "redis",
        SimpleNamespace(asyncio=SimpleNamespace(from_url=fake_from_url)),
    )

    settings_obj = SimpleNamespace(
        PHONE_CODE_STORE="redis",
        REDIS_URL="redis://example.invalid:6379/0",
        REQUEST_COOLDOWN_REDIS_PREFIX="test:",
        REQUEST_COOLDOWN_REDIS_TIMEOUT_SECONDS=0.25,
    )

    request_cooldown_store.build_request_cooldown_store(settings_obj=settings_obj)

    assert calls["kwargs"]["decode_responses"] is True
    assert calls["kwargs"]["socket_connect_timeout"] == 0.25
    assert calls["kwargs"]["socket_timeout"] == 0.25
