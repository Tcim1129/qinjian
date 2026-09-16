"""认证接口：注册 + 登录"""

import logging
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.time import current_local_date
from app.api.deps import get_current_user
from app.models import Pair, PairStatus, User
from app.schemas import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    UserUpdateRequest,
    PasswordChangeRequest,
    WechatLoginRequest,
    PhoneSendCodeRequest,
    PhoneLoginRequest,
    PasswordResetByPhoneRequest,
    ProfileUpdateCodeSendRequest,
    ProfileUpdateCodeConfirmRequest,
)
from app.core.config import settings
from app.services.phone_code_store import PhoneCodeEntry, get_phone_code_store
from app.services.product_prefs import normalize_product_prefs
from app.services.privacy_sandbox import sanitize_log_value
from app.services.task_planner import reset_unstarted_system_tasks
from app.services.test_accounts import is_relaxed_test_account
from app.services.upload_access import (
    actor_can_reference_upload,
    normalize_upload_storage_path,
)

from app.services.login_attempts import get_login_attempt_store, LoginAttemptEntry
from app.services.request_cooldown_store import consume_request_cooldown

router = APIRouter(prefix="/auth", tags=["认证"])
logger = logging.getLogger(__name__)

MIN_PASSWORD_LENGTH = 6
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

REGISTER_IP_WINDOW_SECONDS = 3600
REGISTER_IP_MAX_ATTEMPTS = 10
LOGIN_IP_FAILURE_THRESHOLD = 20
LOGIN_IP_LOCK_MINUTES = 15


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return str(request.client.host) if request.client else "unknown"


def _serialize_user_response(user: User) -> UserResponse:
    from app.services.upload_access import set_request_actor_user_id

    set_request_actor_user_id(str(user.id))
    payload = UserResponse.model_validate(user).model_dump()
    prefs = normalize_product_prefs(getattr(user, "product_prefs", None))
    payload["wechat_bound"] = bool(user.wechat_openid)
    payload["testing_unrestricted"] = is_relaxed_test_account(user)
    payload["ai_assist_enabled"] = bool(prefs["ai_assist_enabled"])
    payload["privacy_mode"] = "cloud"
    payload["preferred_entry"] = str(prefs["preferred_entry"])
    payload["preferred_language"] = str(prefs["preferred_language"])
    payload["tone_preference"] = str(prefs["tone_preference"])
    payload["response_length"] = str(prefs["response_length"])
    payload["habit_profile"] = prefs["habit_profile"]
    payload["relationship_space_theme"] = str(
        prefs["relationship_space_theme"]
    )
    payload["spiritual_support_enabled"] = bool(
        prefs["spiritual_support_enabled"]
    )
    payload["living_region"] = str(prefs.get("living_region") or "")
    payload["selected_pair_id"] = str(prefs.get("selected_pair_id") or "")
    payload["custom_mood_presets"] = list(prefs.get("custom_mood_presets") or [])
    payload["hidden_default_moods"] = list(prefs.get("hidden_default_moods") or [])
    payload["avatar_presentation"] = prefs.get("avatar_presentation") or {}
    payload["task_planner_defaults"] = prefs.get("task_planner_defaults") or {}
    return UserResponse(**payload)


def _normalize_wechat_avatar_url(value: str | None) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    normalized = normalize_upload_storage_path(raw)
    if normalized and normalized.startswith("/uploads/"):
        raise HTTPException(status_code=400, detail="微信头像地址无效")
    return raw


def _resolve_phone_code_store():
    try:
        return get_phone_code_store()
    except (RuntimeError, ValueError) as exc:
        logger.exception("Phone code store misconfigured")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _normalize_phone(phone: str) -> str:
    normalized = phone.strip()
    if not re.fullmatch(r"1\d{10}", normalized):
        raise HTTPException(status_code=400, detail="手机号格式错误")
    return normalized


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized):
        raise HTTPException(status_code=400, detail="邮箱格式错误")
    return normalized


def _build_phone_account_email(phone: str) -> str:
    return f"phone_{phone}@qinjian.local"


def _uses_phone_placeholder_email(user: User) -> bool:
    phone = (user.phone or "").strip()
    email = (user.email or "").strip().lower()
    return bool(phone and email == _build_phone_account_email(phone))


def _resolve_account_identifier(account: str | None) -> tuple[str, str]:
    normalized = (account or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="请输入邮箱或手机号")
    if re.fullmatch(r"1\d{10}", normalized):
        return "phone", normalized
    return "email", _normalize_email(normalized)


async def _find_user_by_account(
    db: AsyncSession, account_type: str, account_value: str
) -> User | None:
    if account_type == "phone":
        result = await db.execute(select(User).where(User.phone == account_value))
    else:
        result = await db.execute(
            select(User).where(func.lower(User.email) == account_value)
        )
    return result.scalar_one_or_none()


def _can_upgrade_phone_account(user: User, phone: str) -> bool:
    return bool(
        user
        and user.phone == phone
        and (user.email or "").lower() == _build_phone_account_email(phone)
    )


def _generate_phone_code() -> str:
    upper_bound = 10**settings.PHONE_CODE_LENGTH
    return str(secrets.randbelow(upper_bound)).zfill(settings.PHONE_CODE_LENGTH)


def _build_phone_code_entry(now: datetime, code: str) -> PhoneCodeEntry:
    return PhoneCodeEntry(
        code_hash=hash_password(code),
        requested_at=now,
        expires_at=now + timedelta(minutes=settings.PHONE_CODE_EXPIRE_MINUTES),
        attempts_left=settings.PHONE_CODE_MAX_ATTEMPTS,
    )


async def _issue_verification_code(
    store_key: str,
    *,
    log_message: str,
    log_value: str,
    log_kind: str,
) -> str:
    store = _resolve_phone_code_store()
    now = datetime.now(timezone.utc)
    existing = await store.get(store_key)
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
    await store.set(store_key, _build_phone_code_entry(now, code))

    if settings.DEBUG:
        logger.info(log_message, sanitize_log_value(log_value, kind=log_kind))

    return code


def _build_verification_delivery_payload() -> dict[str, str]:
    return {"message": "验证码已发送"}


def _ensure_demo_phone_code_route_enabled() -> None:
    if not settings.DEBUG or not settings.PHONE_CODE_TEST_POPUP_ENABLED:
        raise HTTPException(status_code=404, detail="测试验证码入口未开放")


async def _verify_stored_code_or_raise(store_key: str, code: str) -> None:
    store = _resolve_phone_code_store()
    entry = await store.get(store_key)
    if not entry:
        raise HTTPException(status_code=400, detail="验证码错误")

    now = datetime.now(timezone.utc)
    if entry.expires_at <= now:
        await store.delete(store_key)
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")

    if entry.attempts_left <= 0:
        await store.delete(store_key)
        raise HTTPException(status_code=400, detail="验证码尝试次数过多，请重新获取")

    if not verify_password(code.strip(), entry.code_hash):
        updated = await store.decrement_attempts(store_key)
        if updated and updated.attempts_left <= 0:
            await store.delete(store_key)
        raise HTTPException(status_code=400, detail="验证码错误")

    await store.delete(store_key)


async def _verify_phone_code_or_raise(phone: str, code: str) -> None:
    await _verify_stored_code_or_raise(phone, code)


def _profile_update_code_key(user_id: str, field: str, value: str) -> str:
    return f"profile-update:{user_id}:{field}:{value}"


def _profile_update_field_label(field: str) -> str:
    return "邮箱" if field == "email" else "手机号"


async def _validate_profile_update_value(
    field: str,
    value: str,
    *,
    user: User,
    db: AsyncSession,
) -> str:
    if field == "email":
        normalized = _normalize_email(value)
        if normalized.endswith("@qinjian.local"):
            raise HTTPException(status_code=400, detail="请填写常用邮箱")
        current_email = (user.email or "").strip().lower()
        if normalized == current_email:
            raise HTTPException(status_code=400, detail="新邮箱和现在的一样")
        result = await db.execute(
            select(User).where(func.lower(User.email) == normalized, User.id != user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该邮箱已被使用")
        return normalized

    if field == "phone":
        normalized = _normalize_phone(value)
        current_phone = (user.phone or "").strip()
        if normalized == current_phone:
            raise HTTPException(status_code=400, detail="新手机号和现在的一样")
        result = await db.execute(
            select(User).where(User.phone == normalized, User.id != user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该手机号已被使用")
        return normalized

    raise HTTPException(status_code=400, detail="暂不支持这种资料修改")


async def _persist_profile_update_value(
    field: str,
    value: str,
    *,
    user: User,
    db: AsyncSession,
) -> UserResponse:
    if field == "email":
        user.email = value
    elif field == "phone":
        if _uses_phone_placeholder_email(user):
            user.email = _build_phone_account_email(value)
        user.phone = value
    else:
        raise HTTPException(status_code=400, detail="暂不支持这种资料修改")

    await db.flush()
    return _serialize_user_response(user)


@router.post("/register", response_model=dict)
async def register(
    req: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """注册新用户"""
    await consume_request_cooldown(
        bucket="auth:register",
        scope_key=_client_ip(request),
        window_seconds=REGISTER_IP_WINDOW_SECONDS,
        max_attempts=REGISTER_IP_MAX_ATTEMPTS,
        limit_message="注册过于频繁",
    )
    account_type, account_value = _resolve_account_identifier(req.account or req.email)
    nickname = req.nickname.strip()

    if len(req.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"密码至少需要 {MIN_PASSWORD_LENGTH} 位",
        )
    if not nickname:
        raise HTTPException(status_code=400, detail="昵称不能为空")

    user = await _find_user_by_account(db, account_type, account_value)
    if user:
        if account_type == "phone" and _can_upgrade_phone_account(user, account_value):
            user.nickname = nickname
            user.password_hash = hash_password(req.password)
        else:
            detail = "该手机号已注册" if account_type == "phone" else "该邮箱已注册"
            raise HTTPException(status_code=400, detail=detail)
    else:
        user = User(
            email=account_value if account_type == "email" else _build_phone_account_email(account_value),
            phone=account_value if account_type == "phone" else None,
            nickname=nickname,
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
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """用户登录"""
    account_type, account_value = _resolve_account_identifier(req.account or req.email)
    if len(req.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"密码至少需要 {MIN_PASSWORD_LENGTH} 位",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    store = get_login_attempt_store()
    client_ip = _client_ip(request)
    ip_key = f"ip:{client_ip}"
    ip_attempt = await store.get(ip_key)
    if not ip_attempt:
        ip_attempt = LoginAttemptEntry(count=0, locked_until=None)

    if ip_attempt.locked_until and now < ip_attempt.locked_until:
        remaining = int((ip_attempt.locked_until - now).total_seconds() / 60)
        raise HTTPException(
            status_code=429,
            detail=f"当前网络登录失败次数过多，请 {max(1, remaining)} 分钟后再试",
        )
    if ip_attempt.locked_until and now >= ip_attempt.locked_until:
        ip_attempt.count = 0
        ip_attempt.locked_until = None

    attempt_key = f"{account_type}:{account_value}"
    attempt = await store.get(attempt_key)
    if not attempt:
        attempt = LoginAttemptEntry(count=0, locked_until=None)

    if attempt.locked_until and now < attempt.locked_until:
        remaining = int((attempt.locked_until - now).total_seconds() / 60)
        raise HTTPException(
            status_code=429,
            detail=f"密码错误次数过多，为了保护账号安全已被锁定，请 {max(1, remaining)} 分钟后再试",
        )
    if attempt.locked_until and now >= attempt.locked_until:
        attempt.count = 0
        attempt.locked_until = None

    user = await _find_user_by_account(db, account_type, account_value)
    if not user:
        raise HTTPException(status_code=404, detail="该账号尚未注册，请先注册")
    if not verify_password(req.password, user.password_hash):
        attempt.count += 1
        if attempt.count >= 5:
            attempt.locked_until = now + timedelta(minutes=15)
        await store.set(attempt_key, attempt)
        ip_attempt.count += 1
        if ip_attempt.count >= LOGIN_IP_FAILURE_THRESHOLD:
            ip_attempt.locked_until = now + timedelta(minutes=LOGIN_IP_LOCK_MINUTES)
        await store.set(ip_key, ip_attempt)
        raise HTTPException(status_code=401, detail="密码错误，请重新输入")

    await store.delete(attempt_key)
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
        raise HTTPException(status_code=400, detail="微信登录失败，请稍后再试")

    openid = data.get("openid")
    unionid = data.get("unionid")
    if not openid:
        raise HTTPException(status_code=400, detail="微信登录失败，未能获取微信身份信息")

    avatar_url = _normalize_wechat_avatar_url(req.avatar_url)
    result = await db.execute(select(User).where(User.wechat_openid == openid))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email=f"wx_{openid}@qinjian.local",
            nickname=req.nickname or "微信用户",
            password_hash=hash_password(secrets.token_urlsafe(32)),
            avatar_url=avatar_url,
            wechat_openid=openid,
            wechat_unionid=unionid,
            wechat_avatar=avatar_url,
        )
        db.add(user)
        await db.flush()
    else:
        updated = False
        if req.nickname and user.nickname != req.nickname:
            user.nickname = req.nickname
            updated = True
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            user.wechat_avatar = avatar_url
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
    """发送手机验证码。正式接口仅负责投递，不返回测试码。"""
    phone = _normalize_phone(req.phone)
    await _issue_verification_code(
        phone,
        log_message="Phone verification code generated for %s",
        log_value=phone,
        log_kind="phone",
    )
    return _build_verification_delivery_payload()


@router.post("/phone/send-code/demo", response_model=dict)
async def send_phone_code_demo(req: PhoneSendCodeRequest):
    """调试/演示使用的验证码接口，仅在 DEBUG 且显式开启时开放。"""
    _ensure_demo_phone_code_route_enabled()
    phone = _normalize_phone(req.phone)
    code = await _issue_verification_code(
        phone,
        log_message="Phone verification code generated for %s",
        log_value=phone,
        log_kind="phone",
    )
    return {
        "message": "测试验证码已生成",
        "delivery_mode": "test_popup",
        "test_code": code,
    }


@router.post("/me/update-code/send", response_model=dict)
async def send_profile_update_code(
    req: ProfileUpdateCodeSendRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发送资料修改验证码。正式接口仅负责投递，不返回测试码。"""
    normalized_value = await _validate_profile_update_value(
        req.field,
        req.value,
        user=user,
        db=db,
    )
    store_key = _profile_update_code_key(str(user.id), req.field, normalized_value)
    await _issue_verification_code(
        store_key,
        log_message="Profile update verification code generated for user=%s",
        log_value=str(user.id),
        log_kind="user_id",
    )
    return _build_verification_delivery_payload()


@router.post("/me/update-code/send/demo", response_model=dict)
async def send_profile_update_code_demo(
    req: ProfileUpdateCodeSendRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """调试/演示使用的资料修改验证码接口。"""
    _ensure_demo_phone_code_route_enabled()
    normalized_value = await _validate_profile_update_value(
        req.field,
        req.value,
        user=user,
        db=db,
    )
    store_key = _profile_update_code_key(str(user.id), req.field, normalized_value)
    code = await _issue_verification_code(
        store_key,
        log_message="Profile update verification code generated for user=%s",
        log_value=str(user.id),
        log_kind="user_id",
    )
    return {
        "message": f"{_profile_update_field_label(req.field)}测试验证码已生成",
        "delivery_mode": "test_popup",
        "test_code": code,
    }


@router.post("/me/update-code/confirm", response_model=UserResponse)
async def confirm_profile_update_code(
    req: ProfileUpdateCodeConfirmRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """校验资料修改验证码并正式保存新的邮箱或手机号。"""
    normalized_value = await _validate_profile_update_value(
        req.field,
        req.value,
        user=user,
        db=db,
    )
    store_key = _profile_update_code_key(str(user.id), req.field, normalized_value)
    await _verify_stored_code_or_raise(store_key, req.code)
    return await _persist_profile_update_value(
        req.field,
        normalized_value,
        user=user,
        db=db,
    )


@router.post("/phone/login", response_model=dict)
async def phone_login(req: PhoneLoginRequest, db: AsyncSession = Depends(get_db)):
    """手机号验证码登录"""
    phone = _normalize_phone(req.phone)
    await _verify_phone_code_or_raise(phone, req.code)

    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=_build_phone_account_email(phone),
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


@router.post("/password-reset/phone", response_model=dict)
async def reset_password_by_phone(
    req: PasswordResetByPhoneRequest,
    db: AsyncSession = Depends(get_db),
):
    """使用已绑定手机号验证码重置密码。"""
    phone = _normalize_phone(req.phone)
    if len(req.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"新密码至少需要 {MIN_PASSWORD_LENGTH} 位",
        )

    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="该手机号尚未注册")

    await _verify_phone_code_or_raise(phone, req.code)
    user.password_hash = hash_password(req.new_password)
    await db.flush()
    return {"message": "密码已重置，请用新密码登录"}


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

    if req.email is not None:
        raise HTTPException(status_code=400, detail="请先通过验证码确认新的邮箱")

    if req.phone is not None:
        raise HTTPException(status_code=400, detail="请先通过验证码确认新的手机号")

    if req.avatar_url is not None:
        avatar_url = normalize_upload_storage_path(req.avatar_url.strip()) or None
        if avatar_url and not await actor_can_reference_upload(
            db,
            avatar_url,
            actor_user_id=user.id,
        ):
            raise HTTPException(status_code=403, detail="无权使用这份头像文件")
        user.avatar_url = avatar_url

    if (
        req.avatar_presentation is not None
        or req.selected_pair_id is not None
        or req.ai_assist_enabled is not None
        or req.privacy_mode is not None
        or req.preferred_entry is not None
        or req.preferred_language is not None
        or req.tone_preference is not None
        or req.response_length is not None
        or req.habit_profile is not None
        or req.relationship_space_theme is not None
        or req.spiritual_support_enabled is not None
        or req.living_region is not None
        or req.custom_mood_presets is not None
        or req.hidden_default_moods is not None
        or req.task_planner_defaults is not None
    ):
        prefs = normalize_product_prefs(user.product_prefs)
        task_planner_changed = False
        if req.avatar_presentation is not None:
            prefs["avatar_presentation"] = req.avatar_presentation.model_dump()
        if req.ai_assist_enabled is not None:
            prefs["ai_assist_enabled"] = req.ai_assist_enabled
        if req.preferred_entry is not None:
            prefs["preferred_entry"] = req.preferred_entry
        if req.preferred_language is not None:
            prefs["preferred_language"] = req.preferred_language
        if req.tone_preference is not None:
            prefs["tone_preference"] = req.tone_preference
        if req.response_length is not None:
            prefs["response_length"] = req.response_length
        if req.habit_profile is not None:
            prefs["habit_profile"] = req.habit_profile.model_dump()
        if req.relationship_space_theme is not None:
            prefs["relationship_space_theme"] = req.relationship_space_theme
        if req.spiritual_support_enabled is not None:
            prefs["spiritual_support_enabled"] = req.spiritual_support_enabled
        if req.living_region is not None:
            prefs["living_region"] = req.living_region.strip()[:40]
        if req.selected_pair_id is not None:
            prefs["selected_pair_id"] = req.selected_pair_id.strip()[:64]
        if req.custom_mood_presets is not None:
            prefs["custom_mood_presets"] = req.custom_mood_presets
        if req.hidden_default_moods is not None:
            prefs["hidden_default_moods"] = req.hidden_default_moods
        if req.task_planner_defaults is not None:
            merged_defaults = dict(prefs.get("task_planner_defaults") or {})
            merged_defaults.update(req.task_planner_defaults.model_dump(exclude_unset=True))
            prefs["task_planner_defaults"] = merged_defaults
            task_planner_changed = True
        user.product_prefs = normalize_product_prefs(prefs)
        if task_planner_changed:
            today = current_local_date()
            tomorrow = today + timedelta(days=1)
            pair_result = await db.execute(
                select(Pair).where(
                    Pair.status == PairStatus.ACTIVE,
                    or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id),
                )
            )
            for pair in pair_result.scalars().all():
                await reset_unstarted_system_tasks(
                    db,
                    pair_id=pair.id,
                    target_dates=[today, tomorrow],
                )

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
