"""长期关系记忆服务 — 跨会话的人物/事件/策略/模式存储与检索

核心能力：
- store_memory:    写入记忆（去重合并同一 subject）
- recall_memories: 模糊检索（关键词匹配 + 重要度排序）
- batch_store_from_skill: 批量写入 Skill 提取的记忆
- decay_memories:  衰减低重要度且长期未引用的记忆
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, desc, or_, cast, String, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RelationshipMemory

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_uuid(value: Any) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except (ValueError, TypeError):
            return None
    return None


async def store_memory(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    memory_type: str,
    subject: str,
    content: dict[str, Any],
    importance: int = 3,
    source_session_id: uuid.UUID | str | None = None,
) -> RelationshipMemory:
    """写入或更新一条长期记忆。

    如果同一 pair_id + user_id + subject 已存在同类记忆，合并更新。
    """
    pid = _normalize_uuid(pair_id)
    uid = _normalize_uuid(user_id)
    if not pid or not uid:
        raise ValueError("pair_id 和 user_id 不能为空")

    subject = str(subject or "").strip()[:100]
    if not subject:
        raise ValueError("记忆主题不能为空")

    memory_type = str(memory_type or "event").strip().lower()
    if memory_type not in ("person", "event", "strategy", "pattern"):
        memory_type = "event"

    importance = max(1, min(5, int(importance or 3)))

    # 查找是否已有同 subject 的同类记忆
    existing = await db.execute(
        select(RelationshipMemory).where(
            RelationshipMemory.pair_id == pid,
            RelationshipMemory.user_id == uid,
            RelationshipMemory.memory_type == memory_type,
            RelationshipMemory.subject == subject,
        ).limit(1)
    )
    record = existing.scalar_one_or_none()

    if record:
        # 合并更新：保留旧内容，追加新信息
        old_content = record.content or {}
        merged = {**old_content, **content}
        record.content = merged
        record.importance = max(record.importance, importance)
        record.updated_at = _utcnow()
        if source_session_id:
            record.source_session_id = _normalize_uuid(source_session_id)
    else:
        record = RelationshipMemory(
            pair_id=pid,
            user_id=uid,
            memory_type=memory_type,
            subject=subject,
            content=content,
            importance=importance,
            source_session_id=_normalize_uuid(source_session_id),
        )
        db.add(record)

    await db.flush()
    return record


async def recall_memories(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    query: str = "",
    memory_types: list[str] | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """检索相关的长期记忆。

    根据关键词模糊匹配 subject 和 content，按重要度 + 最近引用排序。
    """
    pid = _normalize_uuid(pair_id)
    uid = _normalize_uuid(user_id)
    if not pid or not uid:
        return []

    stmt = select(RelationshipMemory).where(
        RelationshipMemory.pair_id == pid,
        RelationshipMemory.user_id == uid,
    )

    if memory_types:
        stmt = stmt.where(RelationshipMemory.memory_type.in_(memory_types))

    # 关键词匹配（支持完整匹配及中文长句核心词抽取匹配）
    keyword = str(query or "").strip()
    if keyword:
        pattern = f"%{keyword}%"
        conditions = [
            RelationshipMemory.subject.ilike(pattern),
            cast(RelationshipMemory.content, String).ilike(pattern),
        ]

        # 若 query 较长，提取其中的非停用核心词段，提升自然长句的召回率
        import re
        tokens = [t for t in re.split(r"[\s,，。？！!?、~—]+", keyword) if len(t) >= 2]
        for t in tokens:
            if t != keyword:
                conditions.append(RelationshipMemory.subject.ilike(f"%{t}%"))
                conditions.append(cast(RelationshipMemory.content, String).ilike(f"%{t}%"))

        stop_words = set("的一了是在有我你他她它我们他们这个那个怎么怎么办什么如果因为所以而且但是")
        clean_kw = "".join(c for c in keyword if c not in stop_words)
        for i in range(len(clean_kw) - 1):
            sub = clean_kw[i : i + 2]
            if len(sub) == 2:
                conditions.append(RelationshipMemory.subject.ilike(f"%{sub}%"))
                conditions.append(cast(RelationshipMemory.content, String).ilike(f"%{sub}%"))

        stmt = stmt.where(or_(*conditions))

    stmt = stmt.order_by(
        desc(RelationshipMemory.importance),
        desc(RelationshipMemory.last_referenced_at),
        desc(RelationshipMemory.updated_at),
    ).limit(max(1, min(limit, 20)))

    result = await db.execute(stmt)
    records = result.scalars().all()

    # 更新 last_referenced_at
    now = _utcnow()
    for r in records:
        r.last_referenced_at = now

    return [
        {
            "id": str(r.id),
            "type": r.memory_type,
            "subject": r.subject,
            "content": r.content,
            "importance": r.importance,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in records
    ]


async def batch_store_from_skill(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    memories: list[dict[str, Any]],
    source_session_id: uuid.UUID | str | None = None,
) -> int:
    """批量写入 Skill 提取的记忆。

    memories 格式：[{"type": "person", "subject": "小林", "content": "...", "importance": 3}]
    返回成功写入的条数。
    """
    count = 0
    for item in memories:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject", "")).strip()
        if not subject:
            continue
        try:
            await store_memory(
                db,
                pair_id=pair_id,
                user_id=user_id,
                memory_type=str(item.get("type", "event")),
                subject=subject,
                content={"detail": str(item.get("content", ""))},
                importance=int(item.get("importance", 3)),
                source_session_id=source_session_id,
            )
            count += 1
        except Exception as exc:
            logger.warning("Failed to store memory '%s': %s", subject, exc)
    return count


async def list_all_memories(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """列出所有长期记忆（管理用）。"""
    pid = _normalize_uuid(pair_id)
    uid = _normalize_uuid(user_id)
    if not pid or not uid:
        return []

    result = await db.execute(
        select(RelationshipMemory).where(
            RelationshipMemory.pair_id == pid,
            RelationshipMemory.user_id == uid,
        ).order_by(
            desc(RelationshipMemory.importance),
            desc(RelationshipMemory.updated_at),
        ).limit(max(1, min(limit, 100)))
    )
    return [
        {
            "id": str(r.id),
            "type": r.memory_type,
            "subject": r.subject,
            "content": r.content,
            "importance": r.importance,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in result.scalars().all()
    ]


async def decay_memories(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | str,
    older_than_days: int = 90,
) -> int:
    """衰减长期未引用的低重要度记忆。

    将超过 older_than_days 未引用且重要度 <= 2 的记忆降低重要度。
    """
    pid = _normalize_uuid(pair_id)
    if not pid:
        return 0

    cutoff = _utcnow() - timedelta(days=older_than_days)
    result = await db.execute(
        update(RelationshipMemory).where(
            RelationshipMemory.pair_id == pid,
            RelationshipMemory.importance <= 2,
            or_(
                RelationshipMemory.last_referenced_at.is_(None),
                RelationshipMemory.last_referenced_at < cutoff,
            ),
            RelationshipMemory.updated_at < cutoff,
        ).values(importance=1)
    )
    return result.rowcount or 0
