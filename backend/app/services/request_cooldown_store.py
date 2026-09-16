"""共享请求冷却存储：用于高成本接口的轻量滑动窗口限流。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_attempts(attempts: list[datetime]) -> list[str]:
    return [attempt.isoformat() for attempt in attempts]


def _deserialize_attempts(payload: str | bytes | None) -> list[datetime]:
    if not payload:
        return []
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    try:
        raw_attempts = json.loads(payload)
    except (TypeError, ValueError):
        return []
    if not isinstance(raw_attempts, list):
        return []
    attempts: list[datetime] = []
    for raw_attempt in raw_attempts:
        try:
            attempts.append(datetime.fromisoformat(str(raw_attempt)))
        except (TypeError, ValueError):
            continue
    return attempts


class MemoryRequestCooldownStore:
    def __init__(self):
        self._cache: dict[str, list[datetime]] = {}

    async def get(self, key: str) -> list[datetime]:
        return list(self._cache.get(key, []))

    async def set(self, key: str, attempts: list[datetime], *, ttl_seconds: int) -> None:
        self._cache[key] = list(attempts)

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    async def close(self) -> None:
        return None


class RedisRequestCooldownStore:
    def __init__(self, client: Any, *, key_prefix: str):
        self._client = client
        self._key_prefix = key_prefix

    def _key(self, key: str) -> str:
        return f"{self._key_prefix}{key}"

    async def get(self, key: str) -> list[datetime]:
        payload = await self._client.get(self._key(key))
        return _deserialize_attempts(payload)

    async def set(self, key: str, attempts: list[datetime], *, ttl_seconds: int) -> None:
        await self._client.set(
            self._key(key),
            json.dumps(_serialize_attempts(attempts), ensure_ascii=False),
            ex=max(int(ttl_seconds), 1),
        )

    async def delete(self, key: str) -> None:
        await self._client.delete(self._key(key))

    async def close(self) -> None:
        close = getattr(self._client, "aclose", None)
        if close:
            await close()


_REQUEST_COOLDOWN_STORE: MemoryRequestCooldownStore | RedisRequestCooldownStore | None = None


def build_request_cooldown_store(*, settings_obj=settings):
    backend = str(getattr(settings_obj, "PHONE_CODE_STORE", "memory") or "memory").lower()
    redis_url = str(getattr(settings_obj, "REDIS_URL", "") or "").strip()
    redis_timeout = max(
        0.05,
        float(getattr(settings_obj, "REQUEST_COOLDOWN_REDIS_TIMEOUT_SECONDS", 0.5) or 0.5),
    )
    redis_prefix = str(
        getattr(
            settings_obj,
            "REQUEST_COOLDOWN_REDIS_PREFIX",
            "qinjian:request-cooldown:",
        )
        or "qinjian:request-cooldown:"
    )

    if backend != "redis":
        return MemoryRequestCooldownStore()

    if not redis_url:
        return MemoryRequestCooldownStore()

    try:
        from redis import asyncio as redis_asyncio
    except ImportError as exc:
        raise RuntimeError("Redis support requires the 'redis' package") from exc

    client = redis_asyncio.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=redis_timeout,
        socket_timeout=redis_timeout,
        retry_on_timeout=False,
    )
    return RedisRequestCooldownStore(client, key_prefix=redis_prefix)


def get_request_cooldown_store():
    global _REQUEST_COOLDOWN_STORE
    if _REQUEST_COOLDOWN_STORE is None:
        _REQUEST_COOLDOWN_STORE = build_request_cooldown_store(settings_obj=settings)
    return _REQUEST_COOLDOWN_STORE


async def close_request_cooldown_store() -> None:
    global _REQUEST_COOLDOWN_STORE
    if _REQUEST_COOLDOWN_STORE is None:
        return
    await _REQUEST_COOLDOWN_STORE.close()
    _REQUEST_COOLDOWN_STORE = None


async def _fallback_to_memory_store(exc: Exception) -> MemoryRequestCooldownStore:
    global _REQUEST_COOLDOWN_STORE
    current_store = _REQUEST_COOLDOWN_STORE
    if isinstance(current_store, MemoryRequestCooldownStore):
        return current_store

    logger.warning(
        "request cooldown store unavailable, falling back to memory: %s",
        exc.__class__.__name__,
    )
    _REQUEST_COOLDOWN_STORE = MemoryRequestCooldownStore()
    if current_store is not None:
        try:
            await current_store.close()
        except Exception:
            logger.debug("failed to close request cooldown store", exc_info=True)
    return _REQUEST_COOLDOWN_STORE


def _prune_attempts(
    attempts: list[datetime], *, now: datetime, window_seconds: int
) -> list[datetime]:
    window = timedelta(seconds=max(1, int(window_seconds)))
    return [attempt for attempt in attempts if now - attempt < window]


async def _persist_attempts(
    key: str,
    attempts: list[datetime],
    *,
    ttl_seconds: int,
) -> None:
    store = get_request_cooldown_store()
    try:
        if attempts:
            await store.set(key, attempts, ttl_seconds=ttl_seconds)
            return
        await store.delete(key)
    except Exception as exc:
        fallback_store = await _fallback_to_memory_store(exc)
        if attempts:
            await fallback_store.set(key, attempts, ttl_seconds=ttl_seconds)
            return
        await fallback_store.delete(key)
        return


async def consume_request_cooldown(
    *,
    bucket: str,
    scope_key: str,
    window_seconds: int,
    max_attempts: int,
    limit_message: str,
    bypass: bool = False,
) -> None:
    if bypass:
        return

    safe_window_seconds = max(1, int(window_seconds))
    safe_max_attempts = max(1, int(max_attempts))
    now = _utcnow()
    key = f"{bucket}:{scope_key}"
    store = get_request_cooldown_store()
    try:
        stored_attempts = await store.get(key)
    except Exception as exc:
        store = await _fallback_to_memory_store(exc)
        stored_attempts = await store.get(key)

    attempts = _prune_attempts(
        stored_attempts,
        now=now,
        window_seconds=safe_window_seconds,
    )

    if len(attempts) >= safe_max_attempts:
        remaining = int(
            (attempts[0] + timedelta(seconds=safe_window_seconds) - now).total_seconds()
        )
        await _persist_attempts(key, attempts, ttl_seconds=safe_window_seconds)
        raise HTTPException(
            status_code=429,
            detail=f"{limit_message}，请 {max(1, remaining)} 秒后再试",
        )

    attempts.append(now)
    await _persist_attempts(key, attempts, ttl_seconds=safe_window_seconds)
