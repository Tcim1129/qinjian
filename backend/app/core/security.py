"""安全模块：密码哈希 + JWT"""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.core.config import settings

ALGORITHM = "HS256"
REALTIME_ASR_TICKET_TYPE = "realtime_asr"


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError:
        return False


def _create_token(
    subject: str,
    *,
    token_type: str,
    expires_at: datetime,
    extra_payload: dict[str, Any] | None = None,
) -> str:
    issued_at = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expires_at,
    }
    if extra_payload:
        payload.update(extra_payload)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def _decode_subject(
    token: str,
    *,
    allowed_types: set[str | None],
) -> str | None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp", "nbf", "iat"]},
        )
        if payload.get("type") not in allowed_types:
            return None
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            return None
        return subject
    except InvalidTokenError:
        return None


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return _create_token(user_id, token_type="access", expires_at=expire)


def decode_access_token(token: str) -> str | None:
    """解码 JWT，返回 user_id 或 None。"""
    return _decode_subject(token, allowed_types={None, "access"})


def create_realtime_ws_ticket(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        seconds=max(30, settings.REALTIME_ASR_TICKET_EXPIRE_SECONDS)
    )
    return _create_token(
        user_id,
        token_type=REALTIME_ASR_TICKET_TYPE,
        expires_at=expire,
    )


def decode_realtime_ws_ticket(token: str) -> str | None:
    """验证实时 ASR 短期票据，返回 user_id 或 None。"""
    return _decode_subject(token, allowed_types={REALTIME_ASR_TICKET_TYPE})
