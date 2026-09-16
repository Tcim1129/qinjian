"""API 依赖注入：获取当前用户"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User, Pair, PairStatus, PairType
from app.services.upload_access import set_request_actor_user_id

security_scheme = HTTPBearer()

DEMO_MODE_TOKEN = "demo-mode"
DEMO_USER_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
DEMO_PAIR_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")


DEMO_PERSONA_PAIRS = [
    (uuid.UUID("22222222-2222-4222-8222-222222222222"), PairType.COUPLE, "DEMO-LX"),
    (uuid.UUID("77777777-7777-4777-8777-777777777777"), PairType.FRIEND, "DEMO-ZN"),
    (uuid.UUID("99999999-9999-4999-8999-999999999999"), PairType.FRIEND, "DEMO-GY"),
    (DEMO_PAIR_ID, PairType.COUPLE, "DEMO2026"),
]

async def _ensure_demo_fixtures(db: AsyncSession) -> User:
    """确保内置样例用户与全部样例人物配对存在（仅 ALLOW_DEMO_AGENT 开启时调用）。"""
    user = (
        await db.execute(select(User).where(User.id == DEMO_USER_ID))
    ).scalar_one_or_none()
    if not user:
        user = User(
            id=DEMO_USER_ID,
            email="demo-agent@qinjian.local",
            nickname="演示协作用户",
            password_hash="demo-only",
            product_prefs={
                "habit_profile": {
                    "taboos": ["反感长篇说教", "疲惫时不喜被追问细节", "讨厌做家务时居高临下邀功"],
                    "comfort_preferences": ["疲惫时只要安静陪伴", "有事直接给解决方案不用绕弯"],
                    "custom_notes": "下班回家需要先放空20分钟，不想立刻谈复杂事情。"
                }
            }
        )
        db.add(user)

    for pair_id, pair_type, invite_code in DEMO_PERSONA_PAIRS:
        p = (
            await db.execute(select(Pair).where(Pair.id == pair_id))
        ).scalar_one_or_none()
        if not p:
            p = Pair(
                id=pair_id,
                user_a_id=DEMO_USER_ID,
                user_b_id=None,
                type=pair_type,
                status=PairStatus.ACTIVE,
                invite_code=invite_code,
            )
            db.add(p)

    await db.commit()
    return user


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
    if credentials.credentials == DEMO_MODE_TOKEN:
        if not settings.ALLOW_DEMO_AGENT:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证令牌"
            )
        user = await _ensure_demo_fixtures(db)
        set_request_actor_user_id(str(user.id))
        return user
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
    set_request_actor_user_id(str(user.id))
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
