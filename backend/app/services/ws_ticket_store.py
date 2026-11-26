"""一次性 WebSocket 临时票据的防重放存储。"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class MemoryWsTicketStore:
    def __init__(self, max_entries: int = 10000):
        self._consumed: dict[str, float] = {}
        self._max_entries = max_entries

    def _prune(self, now: float) -> None:
        expired = [key for key, expires_at in self._consumed.items() if expires_at <= now]
        for key in expired:
            self._consumed.pop(key, None)
        if len(self._consumed) >= self._max_entries:
            oldest = sorted(self._consumed.items(), key=lambda item: item[1])
            for key, _ in oldest[: max(1, len(oldest) // 4)]:
                self._consumed.pop(key, None)

    async def consume_once(self, jti: str, ttl_seconds: int) -> bool:
        now = time.monotonic()
        self._prune(now)
        if jti in self._consumed:
            return False
        self._consumed[jti] = now + max(1, int(ttl_seconds))
        return True

    async def close(self) -> None:
        self._consumed.clear()


class RedisWsTicketStore:
    def __init__(self, client: Any, *, key_prefix: str = "qinjian:ws-ticket:"):
        self._client = client
        self._key_prefix = key_prefix

    def _key(self, jti: str) -> str:
        return f"{self._key_prefix}{jti}"

    async def consume_once(self, jti: str, ttl_seconds: int) -> bool:
        result = await self._client.set(
            self._key(jti),
            "1",
            nx=True,
            ex=max(1, int(ttl_seconds)),
        )
        return bool(result)

    async def close(self) -> None:
        await self._client.aclose()


_WS_TICKET_STORE: MemoryWsTicketStore | RedisWsTicketStore | None = None


def build_ws_ticket_store(*, settings_obj=settings) -> MemoryWsTicketStore | RedisWsTicketStore:
    backend = str(getattr(settings_obj, "PHONE_CODE_STORE", "memory") or "memory").lower()
    redis_url = str(getattr(settings_obj, "REDIS_URL", "") or "").strip()
    if backend == "redis" and redis_url:
        try:
            from redis import asyncio as redis_asyncio

            client = redis_asyncio.from_url(redis_url, decode_responses=True)
            return RedisWsTicketStore(client)
        except Exception:
            logger.warning("redis unavailable for ws ticket store, falling back to memory")
    return MemoryWsTicketStore()


def get_ws_ticket_store() -> MemoryWsTicketStore | RedisWsTicketStore:
    global _WS_TICKET_STORE
    if _WS_TICKET_STORE is None:
        _WS_TICKET_STORE = build_ws_ticket_store(settings_obj=settings)
    return _WS_TICKET_STORE


async def close_ws_ticket_store() -> None:
    global _WS_TICKET_STORE
    if _WS_TICKET_STORE is None:
        return
    await _WS_TICKET_STORE.close()
    _WS_TICKET_STORE = None
