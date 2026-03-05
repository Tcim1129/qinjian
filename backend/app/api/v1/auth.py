"""认证接口：注册 + 登录"""

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
    TokenResponse,
    UserResponse,
    WechatLoginRequest,
    PhoneSendCodeRequest,
    PhoneLoginRequest,
)
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["认证"])

_phone_code_cache: dict[str, dict] = {}


@router.post("/register", response_model=TokenResponse)
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
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.post("/wechat/login", response_model=TokenResponse)
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
            password_hash=hash_password(openid),
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
    return TokenResponse(access_token=token)


@router.post("/phone/send-code", response_model=dict)
async def send_phone_code(req: PhoneSendCodeRequest):
    """发送手机验证码（测试环境：固定 123456）"""
    _phone_code_cache[req.phone] = {"code": "123456"}
    return {"message": "验证码已发送", "code": "123456"}


@router.post("/phone/login", response_model=TokenResponse)
async def phone_login(req: PhoneLoginRequest, db: AsyncSession = Depends(get_db)):
    """手机号验证码登录（测试环境）"""
    entry = _phone_code_cache.get(req.phone)
    if not entry or entry.get("code") != req.code:
        raise HTTPException(status_code=400, detail="验证码错误")

    result = await db.execute(select(User).where(User.phone == req.phone))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=f"phone_{req.phone}@qinjian.local",
            phone=req.phone,
            nickname=f"手机用户{req.phone[-4:]}",
            password_hash=hash_password(req.phone),
        )
        db.add(user)
        await db.flush()

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return user
