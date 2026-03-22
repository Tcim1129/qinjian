from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.phone_code_store import (
    MemoryPhoneCodeStore,
    PhoneCodeEntry,
    RedisPhoneCodeStore,
    build_phone_code_store,
)


class FakeRedis:
    def __init__(self):
        self.data: dict[str, str] = {}
        self.closed = False
        self.last_expiry: int | None = None

    async def get(self, key: str):
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.data[key] = value
        self.last_expiry = ex

    async def delete(self, key: str):
        self.data.pop(key, None)

    async def aclose(self):
        self.closed = True


@pytest.mark.anyio
async def test_memory_phone_code_store_round_trip_and_decrement():
    store = MemoryPhoneCodeStore()
    now = datetime.now(timezone.utc)
    entry = PhoneCodeEntry(
        code_hash="hashed",
        requested_at=now,
        expires_at=now + timedelta(minutes=5),
        attempts_left=3,
    )

    await store.set("13800138000", entry)
    loaded = await store.get("13800138000")
    assert loaded == entry

    updated = await store.decrement_attempts("13800138000")
    assert updated is not None
    assert updated.attempts_left == 2

    await store.delete("13800138000")
    assert await store.get("13800138000") is None


@pytest.mark.anyio
async def test_redis_phone_code_store_serializes_with_prefix_and_expiry():
    client = FakeRedis()
    store = RedisPhoneCodeStore(client, key_prefix="qj:test:")
    now = datetime.now(timezone.utc)
    entry = PhoneCodeEntry(
        code_hash="hashed",
        requested_at=now,
        expires_at=now + timedelta(minutes=5),
        attempts_left=4,
    )

    await store.set("13800138000", entry)

    assert "qj:test:13800138000" in client.data
    assert client.last_expiry is not None

    loaded = await store.get("13800138000")
    assert loaded == entry

    updated = await store.decrement_attempts("13800138000")
    assert updated is not None
    assert updated.attempts_left == 3

    await store.close()
    assert client.closed is True


def test_build_phone_code_store_defaults_to_memory_backend():
    store = build_phone_code_store(
        settings_obj=SimpleNamespace(
            PHONE_CODE_STORE="memory",
            REDIS_URL="",
            PHONE_CODE_REDIS_PREFIX="qinjian:phone-code:",
        )
    )

    assert isinstance(store, MemoryPhoneCodeStore)


def test_build_phone_code_store_requires_redis_url_when_enabled():
    with pytest.raises(ValueError, match="REDIS_URL"):
        build_phone_code_store(
            settings_obj=SimpleNamespace(
                PHONE_CODE_STORE="redis",
                REDIS_URL="",
                PHONE_CODE_REDIS_PREFIX="qinjian:phone-code:",
            )
        )
