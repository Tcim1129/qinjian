"""Configurable storage for login attempts to prevent brute-force attacks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class LoginAttemptEntry:
    count: int
    locked_until: datetime | None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.locked_until:
            payload["locked_until"] = self.locked_until.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LoginAttemptEntry":
        locked_until_str = payload.get("locked_until")
        return cls(
            count=int(payload.get("count", 0)),
            locked_until=datetime.fromisoformat(locked_until_str) if locked_until_str else None,
        )


class MemoryLoginAttemptStore:
    def __init__(self):
        self._cache: dict[str, LoginAttemptEntry] = {}

    async def get(self, key: str) -> LoginAttemptEntry | None:
        return self._cache.get(key)

    async def set(self, key: str, entry: LoginAttemptEntry) -> None:
        self._cache[key] = entry

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)


class RedisLoginAttemptStore:
    def __init__(self, client: Any, *, key_prefix: str):
        self._client = client
        self._key_prefix = key_prefix

    def _key(self, key: str) -> str:
        return f"{self._key_prefix}{key}"

    async def get(self, key: str) -> LoginAttemptEntry | None:
        payload = await self._client.get(self._key(key))
        if not payload:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        return LoginAttemptEntry.from_dict(json.loads(payload))

    async def set(self, key: str, entry: LoginAttemptEntry) -> None:
        # 默认保存 24 小时
        ttl_seconds = 86400
        if entry.locked_until:
            ttl_seconds = max(int((entry.locked_until - _utcnow()).total_seconds()), 1)
        
        await self._client.set(
            self._key(key),
            json.dumps(entry.to_dict(), ensure_ascii=False),
            ex=ttl_seconds,
        )

    async def delete(self, key: str) -> None:
        await self._client.delete(self._key(key))


_LOGIN_ATTEMPT_STORE: MemoryLoginAttemptStore | RedisLoginAttemptStore | None = None


def build_login_attempt_store(*, settings_obj=settings):
    # 复用手机验证码的底层存储配置，或者默认使用 memory
    backend = str(getattr(settings_obj, "PHONE_CODE_STORE", "memory") or "memory").lower()
    redis_url = str(getattr(settings_obj, "REDIS_URL", "") or "").strip()
    redis_prefix = "qinjian:login-attempt:"
    debug_enabled = bool(getattr(settings_obj, "DEBUG", True))

    if backend != "redis":
        if not debug_enabled:
            raise ValueError(
                "Redis is required when DEBUG is disabled for login attempt storage"
            )
        return MemoryLoginAttemptStore()

    if not redis_url:
        raise ValueError("REDIS_URL is required when PHONE_CODE_STORE=redis")

    try:
        from redis import asyncio as redis_asyncio
        client = redis_asyncio.from_url(redis_url, decode_responses=True)
        return RedisLoginAttemptStore(client, key_prefix=redis_prefix)
    except ImportError as exc:
        raise RuntimeError("Redis support requires the 'redis' package") from exc


def get_login_attempt_store():
    global _LOGIN_ATTEMPT_STORE
    if _LOGIN_ATTEMPT_STORE is None:
        _LOGIN_ATTEMPT_STORE = build_login_attempt_store(settings_obj=settings)
    return _LOGIN_ATTEMPT_STORE
