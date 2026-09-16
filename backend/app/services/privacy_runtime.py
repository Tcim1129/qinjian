"""Runtime helpers for automatic privacy maintenance."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Any

from app.core.config import settings
from app.core.database import async_session
from app.services.privacy_retention import (
    process_due_deletion_requests,
    run_privacy_retention_sweep,
)
from app.services.timeline_archive import backfill_archive_checkins

logger = logging.getLogger(__name__)


async def run_privacy_maintenance_cycle(*, reason: str) -> dict[str, Any]:
    batch_size = max(int(settings.PRIVACY_RETENTION_BACKFILL_BATCH_SIZE or 0), 1)
    backfilled = 0

    async with async_session() as db:
        # Backfill a bounded batch first so old records participate in retention
        # and archive rendering without needing a one-off manual script.
        for _ in range(3):
            processed = await backfill_archive_checkins(db, limit=batch_size)
            backfilled += processed
            if processed:
                await db.flush()
            if processed < batch_size:
                break

        retention_summary = await run_privacy_retention_sweep(db, dry_run=False)
        due_summary = await process_due_deletion_requests(db, dry_run=False)
        await db.commit()

    summary = {
        "reason": reason,
        "archive_backfilled_checkins": backfilled,
        **retention_summary,
        "due_requests": due_summary["due_requests"],
        "executed_deletions": due_summary["executed"],
        "manual_review_requests": due_summary["manual_review"],
    }
    logger.info(
        "隐私维护完成 reason=%s backfilled=%s expired_raw=%s deleted_uploads=%s due=%s",
        reason,
        backfilled,
        retention_summary.get("expired_raw_checkins", 0),
        retention_summary.get("deleted_raw_uploads", 0),
        due_summary["due_requests"],
    )
    return summary


async def run_privacy_maintenance_loop() -> None:
    interval_seconds = max(
        int(settings.PRIVACY_RETENTION_SWEEP_INTERVAL_MINUTES or 0) * 60,
        300,
    )
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await run_privacy_maintenance_cycle(reason="scheduled")
        except Exception as exc:  # pragma: no cover - defensive runtime logging
            logger.warning("定时隐私维护失败，已跳过: %s", exc.__class__.__name__)


async def stop_privacy_maintenance_loop(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
