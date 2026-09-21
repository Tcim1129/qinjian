"""Private confirmed text, exact retries, and erasure without model side effects."""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SavedExpression


async def find_expression(db: AsyncSession, expression_id: uuid.UUID):
    result = await db.execute(select(SavedExpression).where(SavedExpression.id == expression_id).with_for_update())
    return result.scalar_one_or_none()


def check_existing(row, *, user_id, pair_id, text):
    if row.user_id != user_id:
        raise HTTPException(status_code=404, detail="这条表达不存在")
    if row.deleted_at is not None:
        raise HTTPException(status_code=409, detail="这条表达已删除，请重新保存")
    if row.pair_id != pair_id or row.text != text:
        raise HTTPException(status_code=409, detail="保存内容已变更，请重新保存")
    return row


async def save_expression(db: AsyncSession, *, expression_id, user_id, pair_id, text):
    row = await find_expression(db, expression_id)
    if row:
        return check_existing(row, user_id=user_id, pair_id=pair_id, text=text)
    row = SavedExpression(id=expression_id, user_id=user_id, pair_id=pair_id, text=text)
    try:
        async with db.begin_nested():
            db.add(row)
            await db.flush()
    except IntegrityError:
        # The primary key is the idempotency key, including simultaneous inserts.
        existing = await find_expression(db, expression_id)
        if existing is None:
            raise
        return check_existing(existing, user_id=user_id, pair_id=pair_id, text=text)
    return row


async def list_expressions(db: AsyncSession, *, user_id, pair_id, limit=20):
    result = await db.execute(
        select(SavedExpression)
        .where(SavedExpression.user_id == user_id, SavedExpression.pair_id == pair_id,
               SavedExpression.deleted_at.is_(None))
        .order_by(SavedExpression.created_at.desc(), SavedExpression.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def delete_expression(db: AsyncSession, *, expression_id, user_id):
    row = await find_expression(db, expression_id)
    if not row or row.user_id != user_id:
        raise HTTPException(status_code=404, detail="这条表达不存在")
    if row.deleted_at is None:
        row.text = None
        row.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.flush()
