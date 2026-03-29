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
    UserUpdateRequest,
    PasswordChangeRequest,
    WechatLoginRequest,
    PhoneSendCodeRequest,
    PhoneLoginRequest,
)
from app.core.config import settings
from app.services.phone_code_store import PhoneCodeEntry, get_phone_code_store
from app.services.product_prefs import normalize_product_prefs
from app.services.privacy_sandbox import sanitize_log_value

router = APIRouter(prefix="/auth", tags=["认证"])
logger = logging.getLogger(__name__)

_login_attempts: dict[str, dict] = {}
MIN_PASSWORD_LENGTH = 8
INVALID_LOGIN_DETAIL = "邮箱或密码错误"
DUMMY_PASSWORD_HASH = hash_password("qinjian.invalid-login-placeholder")


def _serialize_user_response(user: User) -> UserResponse:
    payload = UserResponse.model_validate(user).model_dump()
    prefs = normalize_product_prefs(getattr(user, "product_prefs", None))
    payload["wechat_bound"] = bool(user.wechat_openid)
    payload["ai_assist_enabled"] = bool(prefs["ai_assist_enabled"])
    payload["privacy_mode"] = str(prefs["privacy_mode"])
    payload["preferred_entry"] = str(prefs["preferred_entry"])
    return UserResponse(**payload)


def _resolve_phone_code_store():
    try:
        return get_phone_code_store()
    except (RuntimeError, ValueError) as exc:
        logger.exception("Phone code store misconfigured")
        raise HTTPException(
            status_code=503,
            detail="验证码服务暂时不可用，请稍后再试",
        ) from exc


def _normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def _raise_invalid_login_error() -> None:
    raise HTTPException(status_code=401, detail=INVALID_LOGIN_DETAIL)


def _normalize_phone(phone: str) -> str:
    normalized = phone.strip()
    if not re.fullmatch(r"1\d{10}", normalized):
        raise HTTPException(status_code=400, detail="手机号格式错误")
    return normalized


def _generate_phone_code() -> str:
    upper_bound = 10**settings.PHONE_CODE_LENGTH
    return str(secrets.randbelow(upper_bound)).zfill(settings.PHONE_CODE_LENGTH)


@router.post("/register", response_model=dict)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """注册新用户"""
    normalized_email = _normalize_email(req.email)
    if len(req.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"密码至少需要 {MIN_PASSWORD_LENGTH} 位",
        )

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == normalized_email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    user = User(
        email=normalized_email,
        nickname=req.nickname,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    await db.flush()

    token = create_access_token(str(user.id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _serialize_user_response(user),
    }


@router.post("/login", response_model=dict)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    normalized_email = _normalize_email(req.email)
    now = datetime.now(timezone.utc)
    attempt = _login_attempts.setdefault(
        normalized_email, {"count": 0, "locked_until": None}
    )
    if attempt["locked_until"] and now < attempt["locked_until"]:
        remaining = int((attempt["locked_until"] - now).total_seconds() / 60)
        raise HTTPException(
            status_code=429,
            detail=f"密码错误次数过多，为了保护账号安全已被锁定，请 {max(1, remaining)} 分钟后再试",
        )
    if attempt["locked_until"] and now >= attempt["locked_until"]:
        attempt["count"] = 0
        attempt["locked_until"] = None

    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()
    if not user:
        verify_password(req.password, DUMMY_PASSWORD_HASH)
        _raise_invalid_login_error()
    if not verify_password(req.password, user.password_hash):
        attempt["count"] += 1
        if attempt["count"] >= 5:
            attempt["locked_until"] = now + timedelta(minutes=15)
        _raise_invalid_login_error()

    _login_attempts.pop(normalized_email, None)
    token = create_access_token(str(user.id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _serialize_user_response(user),
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
        "user": _serialize_user_response(user),
    }


@router.post("/phone/send-code", response_model=dict)
async def send_phone_code(req: PhoneSendCodeRequest):
    """发送手机验证码（支持内存或 Redis 存储，便于后续接短信网关）"""
    phone = _normalize_phone(req.phone)
    store = _resolve_phone_code_store()
    now = datetime.now(timezone.utc)
    existing = await store.get(phone)
    if (
        existing
        and existing.requested_at
        + timedelta(seconds=settings.PHONE_CODE_RESEND_COOLDOWN_SECONDS)
        > now
    ):
        remaining = int(
            (
                existing.requested_at
                + timedelta(seconds=settings.PHONE_CODE_RESEND_COOLDOWN_SECONDS)
                - now
            ).total_seconds()
        )
        raise HTTPException(
            status_code=429, detail=f"发送过于频繁，请 {max(1, remaining)} 秒后再试"
        )

    code = _generate_phone_code()
    await store.set(
        phone,
        PhoneCodeEntry(
            code_hash=hash_password(code),
            requested_at=now,
            expires_at=now + timedelta(minutes=settings.PHONE_CODE_EXPIRE_MINUTES),
            attempts_left=settings.PHONE_CODE_MAX_ATTEMPTS,
        ),
    )

    if settings.DEBUG:
        logger.info(
            "Phone verification code generated for %s",
            sanitize_log_value(phone, kind="phone"),
        )

    payload = {"message": "验证码已发送"}
    if settings.DEBUG and settings.PHONE_CODE_DEBUG_RETURN:
        payload["debug_code"] = code
    return payload


@router.post("/phone/login", response_model=dict)
async def phone_login(req: PhoneLoginRequest, db: AsyncSession = Depends(get_db)):
    """手机号验证码登录"""
    phone = _normalize_phone(req.phone)
    store = _resolve_phone_code_store()
    entry = await store.get(phone)
    if not entry:
        raise HTTPException(status_code=400, detail="验证码错误")

    now = datetime.now(timezone.utc)
    if entry.expires_at <= now:
        await store.delete(phone)
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")

    if entry.attempts_left <= 0:
        await store.delete(phone)
        raise HTTPException(status_code=400, detail="验证码尝试次数过多，请重新获取")

    if not verify_password(req.code.strip(), entry.code_hash):
        updated = await store.decrement_attempts(phone)
        if updated and updated.attempts_left <= 0:
            await store.delete(phone)
        raise HTTPException(status_code=400, detail="验证码错误")

    await store.delete(phone)

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
        "user": _serialize_user_response(user),
    }


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return _serialize_user_response(user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    req: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户资料"""
    if req.nickname is not None:
        nickname = req.nickname.strip()
        if len(nickname) < 1:
            raise HTTPException(status_code=400, detail="昵称不能为空")
        if len(nickname) > 50:
            raise HTTPException(status_code=400, detail="昵称长度不能超过50个字符")
        user.nickname = nickname

    if req.avatar_url is not None:
        user.avatar_url = req.avatar_url.strip() or None

    if (
        req.ai_assist_enabled is not None
        or req.privacy_mode is not None
        or req.preferred_entry is not None
    ):
        prefs = normalize_product_prefs(user.product_prefs)
        if req.ai_assist_enabled is not None:
            prefs["ai_assist_enabled"] = req.ai_assist_enabled
        if req.privacy_mode is not None:
            prefs["privacy_mode"] = req.privacy_mode
        if req.preferred_entry is not None:
            prefs["preferred_entry"] = req.preferred_entry
        user.product_prefs = prefs

    await db.flush()
    return _serialize_user_response(user)


@router.post("/change-password", response_model=dict)
async def change_password(
    req: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改当前用户密码"""
    if not verify_password(req.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码错误")

    if len(req.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"新密码至少需要 {MIN_PASSWORD_LENGTH} 位",
        )

    if req.new_password == req.current_password:
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")

    user.password_hash = hash_password(req.new_password)
    await db.flush()
    return {"message": "密码修改成功"}
