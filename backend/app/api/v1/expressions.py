"""Explicit, owner-only saves. No sending, synthesis, or shared timeline writes."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DEMO_USER_ID, get_current_user, validate_pair_access
from app.core.database import get_db
from app.models import User
from app.services.saved_expressions import (
    check_existing, delete_expression, find_expression, list_expressions, save_expression,
)

router = APIRouter(prefix="/expressions", tags=["私密表达"])


class SaveExpressionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)
    pair_id: uuid.UUID | None = None

    @field_validator("text")
    @classmethod
    def strip_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("请先写下要保存的表达")
        return value


class SavedExpressionResponse(BaseModel):
    id: uuid.UUID
    pair_id: uuid.UUID | None
    text: str
    created_at: datetime


def serialize(row):
    return SavedExpressionResponse(id=row.id, pair_id=row.pair_id, text=row.text,
                                   created_at=row.created_at.replace(tzinfo=timezone.utc))


async def private_user(user: User = Depends(get_current_user)):
    if user.id == DEMO_USER_ID:
        raise HTTPException(status_code=403, detail="请登录自己的账号后保存")
    return user


@router.get("", response_model=list[SavedExpressionResponse])
async def get_saved_expressions(pair_id: uuid.UUID | None = None, limit: int = Query(default=20, ge=1, le=50),
                                user: User = Depends(private_user), db: AsyncSession = Depends(get_db)):
    rows = await list_expressions(db, user_id=user.id, pair_id=pair_id, limit=limit)
    return [serialize(row) for row in rows]


@router.put("/{expression_id}", response_model=SavedExpressionResponse)
async def put_saved_expression(expression_id: uuid.UUID, req: SaveExpressionRequest,
                               user: User = Depends(private_user), db: AsyncSession = Depends(get_db)):
    existing = await find_expression(db, expression_id)
    if existing:
        return serialize(check_existing(existing, user_id=user.id, pair_id=req.pair_id, text=req.text))
    if req.pair_id:
        await validate_pair_access(req.pair_id, user, db, require_active=True)
    row = await save_expression(db, expression_id=expression_id, user_id=user.id, pair_id=req.pair_id, text=req.text)
    return serialize(row)


@router.delete("/{expression_id}", status_code=204)
async def remove_saved_expression(expression_id: uuid.UUID, user: User = Depends(private_user),
                                  db: AsyncSession = Depends(get_db)):
    await delete_expression(db, expression_id=expression_id, user_id=user.id)
    return Response(status_code=204)
