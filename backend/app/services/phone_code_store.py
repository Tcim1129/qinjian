"""手机验证码存储服务（支持内存/Redis）"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class PhoneCodeEntry:
    code_hash: str
    requested_at: datetime
    expires_at: datetime
    attempts_left: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["requested_at"] = self.requested_at.isoformat()
        payload["expires_at"] = self.expires_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PhoneCodeEntry":
        return cls(
            code_hash=str(payload["code_hash"]),
            requested_at=datetime.fromisoformat(str(payload["requested_at"])),
            expires_at=datetime.fromisoformat(str(payload["expires_at"])),
            attempts_left=int(payload["attempts_left"]),
        )


class MemoryPhoneCodeStore:
    def __init__(self):
        self._cache: dict[str, PhoneCodeEntry] = {}

    async def get(self, phone: str) -> PhoneCodeEntry | None:
        return self._cache.get(phone)

    async def set(self, phone: str, entry: PhoneCodeEntry) -> None:
        self._cache[phone] = entry

    async def delete(self, phone: str) -> None:
        self._cache.pop(phone, None)

    async def decrement_attempts(self, phone: str) -> PhoneCodeEntry | None:
        entry = self._cache.get(phone)
        if not entry:
            return None
        updated = PhoneCodeEntry(
            code_hash=entry.code_hash,
            requested_at=entry.requested_at,
            expires_at=entry.expires_at,
            attempts_left=max(entry.attempts_left - 1, 0),
        )
        self._cache[phone] = updated
        return updated

    async def close(self) -> None:
        return None


class RedisPhoneCodeStore:
    def __init__(self, client: Any, *, key_prefix: str):
        self._client = client
        self._key_prefix = key_prefix

    def _key(self, phone: str) -> str:
        return f"{self._key_prefix}{phone}"

    async def get(self, phone: str) -> PhoneCodeEntry | None:
        payload = await self._client.get(self._key(phone))
        if not payload:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        return PhoneCodeEntry.from_dict(json.loads(payload))

    async def set(self, phone: str, entry: PhoneCodeEntry) -> None:
        ttl_seconds = max(int((entry.expires_at - _utcnow()).total_seconds()), 1)
        await self._client.set(
            self._key(phone),
            json.dumps(entry.to_dict(), ensure_ascii=False),
            ex=ttl_seconds,
        )

    async def delete(self, phone: str) -> None:
        await self._client.delete(self._key(phone))

    async def decrement_attempts(self, phone: str) -> PhoneCodeEntry | None:
        entry = await self.get(phone)
        if not entry:
            return None
        updated = PhoneCodeEntry(
            code_hash=entry.code_hash,
            requested_at=entry.requested_at,
            expires_at=entry.expires_at,
            attempts_left=max(entry.attempts_left - 1, 0),
        )
        await self.set(phone, updated)
        return updated

    async def close(self) -> None:
        close = getattr(self._client, "aclose", None)
        if close:
            await close()


_PHONE_CODE_STORE: MemoryPhoneCodeStore | RedisPhoneCodeStore | None = None


def build_phone_code_store(*, settings_obj=settings):
    backend = str(getattr(settings_obj, "PHONE_CODE_STORE", "memory") or "memory").lower()
    redis_url = str(getattr(settings_obj, "REDIS_URL", "") or "").strip()
    redis_prefix = str(
        getattr(settings_obj, "PHONE_CODE_REDIS_PREFIX", "qinjian:phone-code:") or "qinjian:phone-code:"
    )
    debug_enabled = bool(getattr(settings_obj, "DEBUG", True))

    if backend != "redis":
        if not debug_enabled:
            raise ValueError("Redis is required when DEBUG is disabled for PHONE_CODE_STORE")
        return MemoryPhoneCodeStore()

    if not redis_url:
        raise ValueError("REDIS_URL is required when PHONE_CODE_STORE=redis")

    try:
        from redis import asyncio as redis_asyncio
    except ImportError as exc:
        raise RuntimeError("Redis support requires the 'redis' package") from exc

    client = redis_asyncio.from_url(redis_url, decode_responses=True)
    return RedisPhoneCodeStore(client, key_prefix=redis_prefix)


def get_phone_code_store():
    global _PHONE_CODE_STORE
    if _PHONE_CODE_STORE is None:
        _PHONE_CODE_STORE = build_phone_code_store(settings_obj=settings)
    return _PHONE_CODE_STORE


async def close_phone_code_store() -> None:
    global _PHONE_CODE_STORE
    if _PHONE_CODE_STORE is None:
        return
    await _PHONE_CODE_STORE.close()
    _PHONE_CODE_STORE = None
