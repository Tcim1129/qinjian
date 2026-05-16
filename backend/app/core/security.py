"""安全模块：密码哈希 + JWT"""
from datetime import datetime, timedelta, timezone

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


def create_access_token(user_id: str) -> str:
    issued_at = datetime.now(timezone.utc)
    expire = issued_at + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """解码JWT，返回user_id或None"""
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
        return subject
    except InvalidTokenError:
        return None
