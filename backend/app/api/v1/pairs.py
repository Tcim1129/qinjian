"""配对系统接口"""
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, Pair, PairType, PairStatus
from app.schemas import PairCreateRequest, PairJoinRequest, PairResponse

router = APIRouter(prefix="/pairs", tags=["配对"])


@router.post("/create", response_model=PairResponse)
async def create_pair(req: PairCreateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """创建配对，生成邀请码"""
    # 检查是否已有活跃配对
    result = await db.execute(
        select(Pair).where(
            or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
            Pair.status.in_([PairStatus.PENDING, PairStatus.ACTIVE]),
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="你已有一个活跃的配对关系")

    pair = Pair(
        user_a_id=user.id,
        type=PairType(req.type),
        invite_code=secrets.token_urlsafe(6)[:8].upper(),
    )
    db.add(pair)
    await db.flush()
    return pair


@router.post("/join", response_model=PairResponse)
async def join_pair(req: PairJoinRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """通过邀请码加入配对"""
    result = await db.execute(
        select(Pair).where(Pair.invite_code == req.invite_code.upper(), Pair.status == PairStatus.PENDING)
    )
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="无效的邀请码")
    if pair.user_a_id == user.id:
        raise HTTPException(status_code=400, detail="不能与自己配对")

    pair.user_b_id = user.id
    pair.status = PairStatus.ACTIVE
    await db.flush()
    return pair


@router.get("/me", response_model=PairResponse | None)
async def get_my_pair(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取当前配对信息"""
    result = await db.execute(
        select(Pair).where(
            or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
            Pair.status.in_([PairStatus.PENDING, PairStatus.ACTIVE]),
        )
    )
    return result.scalar_one_or_none()
