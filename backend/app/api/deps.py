"""API 依赖注入：获取当前用户"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User, Pair, PairStatus

security_scheme = HTTPBearer()


def _parse_uuid_or_raise(
    value: str | uuid.UUID | None,
    *,
    status_code: int,
    detail: str,
) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    if not value:
        raise HTTPException(status_code=status_code, detail=detail)
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status_code, detail=detail) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证令牌")
    normalized_user_id = _parse_uuid_or_raise(
        user_id,
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证令牌",
    )
    result = await db.execute(select(User).where(User.id == normalized_user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


async def validate_pair_access(
    pair_id: str,
    user: User,
    db: AsyncSession,
    *,
    require_active: bool = True,
) -> Pair:
    """验证当前用户是否属于指定配对。"""
    normalized_pair_id = _parse_uuid_or_raise(
        pair_id,
        status_code=status.HTTP_404_NOT_FOUND,
        detail="配对不存在",
    )
    result = await db.execute(select(Pair).where(Pair.id == normalized_pair_id))
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配对不存在")
    if require_active and pair.status != PairStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配对不存在或未激活")
    if str(user.id) not in (str(pair.user_a_id), str(pair.user_b_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该配对")
    return pair
