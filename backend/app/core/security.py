"""安全模块：密码哈希 + JWT"""
from datetime import datetime, timedelta, timezone
import uuid

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.core.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError:
        return False


def create_access_token(user_id: str, *, token_version: int = 0) -> str:
    issued_at = datetime.now(timezone.utc)
    expire = issued_at + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "type": "access",
        "tv": int(token_version or 0),
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token_payload(token: str) -> dict | None:
    """解码访问令牌，返回包含用户与令牌版本号的字典。"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp", "nbf", "iat"]},
        )
        if payload.get("type") not in (None, "access"):
            return None
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            return None
        try:
            token_version = int(payload.get("tv", 0) or 0)
        except (TypeError, ValueError):
            return None
        return {"user_id": subject, "token_version": token_version}
    except InvalidTokenError:
        return None


def decode_access_token(token: str) -> str | None:
    """解码JWT，返回user_id或None"""
    payload = decode_access_token_payload(token)
    return payload["user_id"] if payload else None


def create_realtime_ws_ticket(user_id: str, *, token_version: int = 0) -> str:
    """生成实时语音连接使用的临时访问令牌。"""
    issued_at = datetime.now(timezone.utc)
    expire = issued_at + timedelta(seconds=settings.REALTIME_ASR_TICKET_EXPIRE_SECONDS)
    payload = {
        "sub": user_id,
        "type": "realtime_ws",
        "tv": int(token_version or 0),
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expire,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_realtime_ws_ticket_payload(ticket: str) -> dict | None:
    """检查实时语音临时票据并返回完整声明。"""
    if not ticket:
        return None

    try:
        payload = jwt.decode(
            ticket,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp", "nbf", "iat", "jti"]},
        )
        if payload.get("type") != "realtime_ws":
            return None
        subject = payload.get("sub")
        jti = payload.get("jti")
        if (
            not isinstance(subject, str)
            or not subject.strip()
            or not isinstance(jti, str)
            or not jti.strip()
        ):
            return None
        try:
            token_version = int(payload.get("tv", 0) or 0)
        except (TypeError, ValueError):
            return None
        exp = payload.get("exp")
        remaining_seconds = max(1, int(exp - datetime.now(timezone.utc).timestamp())) if exp else 60
        return {
            "user_id": subject,
            "jti": jti,
            "token_version": token_version,
            "remaining_seconds": remaining_seconds,
        }
    except InvalidTokenError:
        return None


def decode_realtime_ws_ticket(ticket: str) -> str | None:
    """检查实时语音连接的临时访问令牌是否有效。"""
    payload = decode_realtime_ws_ticket_payload(ticket)
    return payload["user_id"] if payload else None


MEDIA_UPLOAD_TICKET_TTL_SECONDS = 600


def create_media_upload_ticket(
    *,
    user_id: str,
    media_kind: str,
    content_type: str,
    size_bytes: int,
    client_request_id: str,
) -> str:
    """生成一次性媒体上传票据，绑定上传者、类型与声明大小。"""
    issued_at = datetime.now(timezone.utc)
    expire = issued_at + timedelta(seconds=MEDIA_UPLOAD_TICKET_TTL_SECONDS)
    payload = {
        "sub": user_id,
        "type": "media_upload",
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expire,
        "jti": uuid.uuid4().hex,
        "media_kind": media_kind,
        "content_type": content_type,
        "size_bytes": int(size_bytes),
        "req": client_request_id,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_media_upload_ticket(ticket: str) -> dict | None:
    """校验媒体上传票据，返回其声明；无效或过期返回 None。"""
    if not ticket:
        return None
    try:
        payload = jwt.decode(
            ticket,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp", "nbf", "iat", "jti"]},
        )
    except InvalidTokenError:
        return None
    if payload.get("type") != "media_upload":
        return None
    if not str(payload.get("sub") or "").strip():
        return None
    return payload
