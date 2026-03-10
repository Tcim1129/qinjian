"""认证接口：注册 + 登录"""

import logging
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user
from app.models import User
from app.schemas import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    WechatLoginRequest,
    PhoneSendCodeRequest,
    PhoneLoginRequest,
)
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["认证"])
logger = logging.getLogger(__name__)

_phone_code_cache: dict[str, dict] = {}


def _normalize_phone(phone: str) -> str:
    normalized = phone.strip()
    if not re.fullmatch(r"1\d{10}", normalized):
        raise HTTPException(status_code=400, detail="手机号格式错误")
    return normalized


def _generate_phone_code() -> str:
    upper_bound = 10 ** settings.PHONE_CODE_LENGTH
    return str(secrets.randbelow(upper_bound)).zfill(settings.PHONE_CODE_LENGTH)


@router.post("/register", response_model=dict)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """注册新用户"""
    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    user = User(
        email=req.email,
        nickname=req.nickname,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    await db.flush()

    token = create_access_token(str(user.id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user),
    }


@router.post("/login", response_model=dict)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="该邮箱尚未注册，请先注册")
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="密码错误，请重新输入")

    token = create_access_token(str(user.id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user),
    }


@router.post("/wechat/login", response_model=dict)
async def wechat_login(req: WechatLoginRequest, db: AsyncSession = Depends(get_db)):
    """微信一键登录（通过 code 获取 openid）"""
    if not settings.WECHAT_APPID or not settings.WECHAT_SECRET:
        raise HTTPException(status_code=500, detail="微信登录未配置")

    import httpx

    params = {
        "appid": settings.WECHAT_APPID,
        "secret": settings.WECHAT_SECRET,
        "js_code": req.code,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(settings.WECHAT_SESSION_URL, params=params)
        data = resp.json()

    if "errcode" in data:
        raise HTTPException(
            status_code=400, detail=f"微信登录失败: {data.get('errmsg', 'unknown')} "
        )

    openid = data.get("openid")
    unionid = data.get("unionid")
    if not openid:
        raise HTTPException(status_code=400, detail="微信登录失败: 未获取 openid")

    result = await db.execute(select(User).where(User.wechat_openid == openid))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email=f"wx_{openid}@qinjian.local",
            nickname=req.nickname or "微信用户",
            password_hash=hash_password(secrets.token_urlsafe(32)),
            avatar_url=req.avatar_url,
            wechat_openid=openid,
            wechat_unionid=unionid,
            wechat_avatar=req.avatar_url,
        )
        db.add(user)
        await db.flush()
    else:
        updated = False
        if req.nickname and user.nickname != req.nickname:
            user.nickname = req.nickname
            updated = True
        if req.avatar_url and user.avatar_url != req.avatar_url:
            user.avatar_url = req.avatar_url
            user.wechat_avatar = req.avatar_url
            updated = True
        if unionid and user.wechat_unionid != unionid:
            user.wechat_unionid = unionid
            updated = True
        if updated:
            await db.flush()

    token = create_access_token(str(user.id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user),
    }


@router.post("/phone/send-code", response_model=dict)
async def send_phone_code(req: PhoneSendCodeRequest):
    """发送手机验证码（当前使用内存缓存 + 频控，便于后续接短信网关）"""
    phone = _normalize_phone(req.phone)
    now = datetime.now(timezone.utc)
    existing = _phone_code_cache.get(phone)
    if existing and existing["requested_at"] + timedelta(seconds=settings.PHONE_CODE_RESEND_COOLDOWN_SECONDS) > now:
        remaining = int((existing["requested_at"] + timedelta(seconds=settings.PHONE_CODE_RESEND_COOLDOWN_SECONDS) - now).total_seconds())
        raise HTTPException(status_code=429, detail=f"发送过于频繁，请 {max(1, remaining)} 秒后再试")

    code = _generate_phone_code()
    _phone_code_cache[phone] = {
        "code_hash": hash_password(code),
        "requested_at": now,
        "expires_at": now + timedelta(minutes=settings.PHONE_CODE_EXPIRE_MINUTES),
        "attempts_left": settings.PHONE_CODE_MAX_ATTEMPTS,
    }

    if settings.DEBUG:
        logger.info("Phone verification code generated for %s: %s", phone, code)

    payload = {"message": "验证码已发送"}
    if settings.DEBUG and settings.PHONE_CODE_DEBUG_RETURN:
        payload["debug_code"] = code
    return payload


@router.post("/phone/login", response_model=dict)
async def phone_login(req: PhoneLoginRequest, db: AsyncSession = Depends(get_db)):
    """手机号验证码登录"""
    phone = _normalize_phone(req.phone)
    entry = _phone_code_cache.get(phone)
    if not entry:
        raise HTTPException(status_code=400, detail="验证码错误")

    now = datetime.now(timezone.utc)
    if entry["expires_at"] <= now:
        _phone_code_cache.pop(phone, None)
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")

    if entry["attempts_left"] <= 0:
        _phone_code_cache.pop(phone, None)
        raise HTTPException(status_code=400, detail="验证码尝试次数过多，请重新获取")

    if not verify_password(req.code.strip(), entry["code_hash"]):
        entry["attempts_left"] -= 1
        if entry["attempts_left"] <= 0:
            _phone_code_cache.pop(phone, None)
        raise HTTPException(status_code=400, detail="验证码错误")

    _phone_code_cache.pop(phone, None)

    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=f"phone_{phone}@qinjian.local",
            phone=phone,
            nickname=f"手机用户{phone[-4:]}",
            password_hash=hash_password(secrets.token_urlsafe(32)),
        )
        db.add(user)
        await db.flush()

    token = create_access_token(str(user.id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user),
    }


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return user
