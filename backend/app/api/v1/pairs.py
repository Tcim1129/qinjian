"""配对系统接口"""

import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, Pair, PairType, PairStatus
from app.schemas import (
    PairCreateRequest,
    PairJoinRequest,
    PairResponse,
    PairSummaryResponse,
    UpdatePartnerNicknameRequest,
)

router = APIRouter(prefix="/pairs", tags=["配对"])
INVITE_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
INVITE_CODE_LENGTH = 10


def _generate_invite_code() -> str:
    return "".join(
        secrets.choice(INVITE_CODE_ALPHABET) for _ in range(INVITE_CODE_LENGTH)
    )


def _build_pair_response(
    pair: Pair, me: User, partner: User | None = None
) -> PairResponse:
    data = PairResponse.model_validate(pair).model_dump()
    if partner:
        # Determine which custom nickname field to use
        is_user_a = str(pair.user_a_id) == str(me.id)
        custom_nickname = (
            pair.custom_partner_nickname_a
            if is_user_a
            else pair.custom_partner_nickname_b
        )

        data.update(
            {
                "partner_id": partner.id,
                "partner_nickname": partner.nickname,
                "partner_avatar": partner.wechat_avatar or partner.avatar_url,
                "custom_partner_nickname": custom_nickname,
            }
        )
    return PairResponse(**data)


@router.post("/create", response_model=PairResponse)
async def create_pair(
    req: PairCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建配对，生成邀请码（支持多配对）"""
    invite_code = _generate_invite_code()
    for _ in range(4):
        existing = await db.execute(select(Pair.id).where(Pair.invite_code == invite_code))
        if not existing.scalar_one_or_none():
            break
        invite_code = _generate_invite_code()
    else:
        raise HTTPException(status_code=503, detail="邀请码生成繁忙，请稍后重试")

    pair = Pair(
        user_a_id=user.id,
        type=PairType(req.type),
        invite_code=invite_code,
    )
    db.add(pair)
    await db.flush()
    return _build_pair_response(pair, user)


@router.post("/join", response_model=PairResponse)
async def join_pair(
    req: PairJoinRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """通过邀请码加入配对"""
    normalized_invite_code = req.invite_code.strip().upper()
    result = await db.execute(
        select(Pair).where(
            Pair.invite_code == normalized_invite_code,
            Pair.status == PairStatus.PENDING,
        )
    )
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="无效的邀请码")
    if pair.user_a_id == user.id:
        raise HTTPException(status_code=400, detail="不能与自己配对")

    pair.user_b_id = user.id
    pair.status = PairStatus.ACTIVE
    await db.flush()

    partner = await db.get(User, pair.user_a_id)
    return _build_pair_response(pair, user, partner)


@router.get("/me", response_model=list[PairResponse])
async def get_my_pairs(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取当前用户的所有配对"""
    result = await db.execute(
        select(Pair).where(
            or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
            Pair.status.in_([PairStatus.PENDING, PairStatus.ACTIVE]),
        )
    )
    pairs = result.scalars().all()
    responses: list[PairResponse] = []
    for pair in pairs:
        partner_id = pair.user_b_id if pair.user_a_id == user.id else pair.user_a_id
        partner = await db.get(User, partner_id) if partner_id else None
        responses.append(_build_pair_response(pair, user, partner))
    return responses


@router.get("/summary", response_model=PairSummaryResponse)
async def get_pair_summary(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取当前用户配对摘要，便于前端统一同步绑定状态"""
    result = await db.execute(
        select(Pair).where(
            or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
            Pair.status.in_([PairStatus.PENDING, PairStatus.ACTIVE]),
        )
    )
    pairs = result.scalars().all()

    active_pairs = [pair for pair in pairs if pair.status == PairStatus.ACTIVE]
    pending_pairs = [pair for pair in pairs if pair.status == PairStatus.PENDING]

    active_pair = active_pairs[0] if active_pairs else None
    pair_response = None
    if active_pair:
        partner_id = (
            active_pair.user_b_id
            if active_pair.user_a_id == user.id
            else active_pair.user_a_id
        )
        partner = await db.get(User, partner_id) if partner_id else None
        pair_response = _build_pair_response(active_pair, user, partner)

    return PairSummaryResponse(
        is_paired=bool(active_pairs),
        active_pair=pair_response,
        active_count=len(active_pairs),
        pending_count=len(pending_pairs),
    )


# ── 解绑功能（计划书§9.1：双方确认或7天冷静期自动解绑）──


@router.post("/request-unbind", response_model=dict)
async def request_unbind(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发起解绑请求（对方需确认，或等待7天冷静期自动生效）"""
    result = await db.execute(
        select(Pair).where(
            Pair.id == pair_id,
            or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
            Pair.status == PairStatus.ACTIVE,
        )
    )
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="配对不存在")

    if pair.unbind_requested_by:
        raise HTTPException(status_code=400, detail="已有解绑请求进行中")

    pair.unbind_requested_by = user.id
    pair.unbind_requested_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()
    return {"message": "解绑请求已发起，等待对方确认（或7天后自动生效）"}


@router.post("/confirm-unbind", response_model=dict)
async def confirm_unbind(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """确认解绑（对方发起后确认，或发起方在冷静期后确认）"""
    result = await db.execute(
        select(Pair).where(
            Pair.id == pair_id,
            or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
            Pair.status == PairStatus.ACTIVE,
        )
    )
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="配对不存在")

    if not pair.unbind_requested_by:
        raise HTTPException(status_code=400, detail="没有待处理的解绑请求")

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 情况1：对方确认（非发起方点确认 → 立即解绑）
    if pair.unbind_requested_by != user.id:
        pair.status = PairStatus.ENDED
        pair.unbind_requested_by = None
        pair.unbind_requested_at = None
        await db.flush()
        return {"message": "双方确认，配对已解除"}

    # 情况2：发起方自己确认 → 需满7天冷静期
    if pair.unbind_requested_at and (now - pair.unbind_requested_at) >= timedelta(
        days=7
    ):
        pair.status = PairStatus.ENDED
        pair.unbind_requested_by = None
        pair.unbind_requested_at = None
        await db.flush()
        return {"message": "冷静期已过，配对已解除"}

    remaining = (
        7 - (now - pair.unbind_requested_at).days if pair.unbind_requested_at else 7
    )
    raise HTTPException(
        status_code=400, detail=f"冷静期未满，还需等待{remaining}天（或等待对方确认）"
    )


@router.post("/cancel-unbind", response_model=dict)
async def cancel_unbind(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """撤回解绑请求（仅发起方可撤回）"""
    result = await db.execute(
        select(Pair).where(
            Pair.id == pair_id,
            or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
            Pair.status == PairStatus.ACTIVE,
        )
    )
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="配对不存在")

    if pair.unbind_requested_by != user.id:
        raise HTTPException(status_code=403, detail="只有发起方可以撤回解绑请求")

    pair.unbind_requested_by = None
    pair.unbind_requested_at = None
    await db.flush()
    return {"message": "解绑请求已撤回"}


@router.get("/unbind-status", response_model=dict)
async def get_unbind_status(
    pair_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询当前解绑状态"""
    result = await db.execute(
        select(Pair).where(
            Pair.id == pair_id,
            or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
            Pair.status == PairStatus.ACTIVE,
        )
    )
    pair = result.scalar_one_or_none()
    if not pair:
        return {"has_request": False}

    if not pair.unbind_requested_by:
        return {"has_request": False}

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    days_elapsed = (
        (now - pair.unbind_requested_at).days if pair.unbind_requested_at else 0
    )
    return {
        "has_request": True,
        "requested_by_me": pair.unbind_requested_by == user.id,
        "days_elapsed": days_elapsed,
        "days_remaining": max(0, 7 - days_elapsed),
        "can_force_unbind": days_elapsed >= 7,
    }


@router.post("/{pair_id}/partner-nickname", response_model=PairResponse)
async def update_partner_nickname(
    pair_id: str,
    req: UpdatePartnerNicknameRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新给伴侣设置的备注名（自定义昵称）"""
    result = await db.execute(
        select(Pair).where(
            Pair.id == pair_id,
            or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
            Pair.status == PairStatus.ACTIVE,
        )
    )
    pair = result.scalar_one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="配对不存在")

    # Determine which field to update based on whether user is user_a or user_b
    if str(pair.user_a_id) == str(user.id):
        pair.custom_partner_nickname_a = req.custom_nickname
    else:
        pair.custom_partner_nickname_b = req.custom_nickname

    await db.flush()

    # Rebuild response with partner info
    partner_id = (
        pair.user_b_id if str(pair.user_a_id) == str(user.id) else pair.user_a_id
    )
    partner = await db.get(User, partner_id) if partner_id else None
    return _build_pair_response(pair, user, partner)
