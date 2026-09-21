"""测试长期关系记忆服务（RelationshipMemory）的存储、合并、检索、衰减及上下文关联。"""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models import User, Pair, PairType, PairStatus, RelationshipMemory
from app.services.relationship_memory import (
    store_memory,
    recall_memories,
    batch_store_from_skill,
    list_all_memories,
    decay_memories,
)
from app.services.ai_context import build_context_pack, format_context_pack_message


@pytest.mark.asyncio
async def test_relationship_memory_crud_and_merge():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        user = User(email="test_mem@qinjian.com", nickname="用户A", password_hash="pwd")
        partner = User(email="partner_mem@qinjian.com", nickname="用户B", password_hash="pwd")
        db.add_all([user, partner])
        await db.flush()

        pair = Pair(
            user_a_id=user.id,
            user_b_id=partner.id,
            type=PairType.COUPLE,
            status=PairStatus.ACTIVE,
            invite_code="MEMTESTCODE1",
        )
        db.add(pair)
        await db.commit()

        pair_id = pair.id
        user_id = user.id

        # 1. 存储一条新记忆
        mem1 = await store_memory(
            db,
            pair_id=pair_id,
            user_id=user_id,
            memory_type="person",
            subject="小林",
            content={"role": "伴侣", "temperament": "内向敏感"},
            importance=4,
        )
        assert mem1.id is not None
        assert mem1.subject == "小林"
        assert mem1.importance == 4

        # 2. 存储同 subject 的记忆，触发自动合并
        mem2 = await store_memory(
            db,
            pair_id=pair_id,
            user_id=user_id,
            memory_type="person",
            subject="小林",
            content={"favorite": "喜欢安静的咖啡馆"},
            importance=5,
        )
        assert mem2.id == mem1.id
        assert mem2.content["temperament"] == "内向敏感"
        assert mem2.content["favorite"] == "喜欢安静的咖啡馆"
        assert mem2.importance == 5

        # 3. 批量存储
        batch_count = await batch_store_from_skill(
            db,
            pair_id=pair_id,
            user_id=user_id,
            memories=[
                {"type": "event", "subject": "云南旅行", "content": "因为行程紧凑吵了一架，后面改成了自由行", "importance": 4},
                {"type": "strategy", "subject": "降温沟通法", "content": "情绪激动时先各自喝杯水独处15分钟有效", "importance": 5},
                {"type": "pattern", "subject": "周末安排习惯", "content": "周六上午通常需要补觉，不宜安排早起出行", "importance": 3},
            ],
        )
        assert batch_count == 3

        # 4. 模糊关键词检索
        recalled = await recall_memories(
            db,
            pair_id=pair_id,
            user_id=user_id,
            query="旅行",
            limit=5,
        )
        assert len(recalled) >= 1
        assert any(r["subject"] == "云南旅行" for r in recalled)

        # 按人物关键词检索
        recalled_person = await recall_memories(
            db,
            pair_id=pair_id,
            user_id=user_id,
            query="小林",
            limit=5,
        )
        assert len(recalled_person) >= 1
        assert recalled_person[0]["subject"] == "小林"
        assert recalled_person[0]["importance"] == 5

        # 5. 全量列表
        all_memories = await list_all_memories(db, pair_id=pair_id, user_id=user_id)
        assert len(all_memories) == 4

        # 6. 测试与 build_context_pack 的自动关联
        context_pack = await build_context_pack(
            db,
            user=user,
            pair_id=str(pair_id),
            user_id=str(user_id),
            current_input={"text": "上次和她去旅行吵架了怎么办"},
        )
        assert "relationship_memories" in context_pack
        recalled_in_pack = context_pack["relationship_memories"]
        assert len(recalled_in_pack) > 0
        assert any("旅行" in str(m.get("subject")) or "旅行" in str(m.get("content")) for m in recalled_in_pack)

        # 检查 format_context_pack_message 是否正确格式化了记忆
        formatted_msg = format_context_pack_message(context_pack)
        assert "已关联的长期关系记忆与历史经验" in formatted_msg["content"]
        assert "云南旅行" in formatted_msg["content"]

        # 7. 测试衰减逻辑
        # 手动将一条记忆的更新时间和最后引用时间推到 100 天前，且重要度设为 2
        low_mem = await store_memory(
            db,
            pair_id=pair_id,
            user_id=user_id,
            memory_type="event",
            subject="某次点外卖口味不合",
            content={"detail": "芝麻小事"},
            importance=2,
        )
        old_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=100)
        low_mem.updated_at = old_time
        low_mem.last_referenced_at = old_time
        await db.commit()

        decayed_count = await decay_memories(db, pair_id=pair_id, older_than_days=90)
        assert decayed_count >= 1
        await db.refresh(low_mem)
        assert low_mem.importance == 1
