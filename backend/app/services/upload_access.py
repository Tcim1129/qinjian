"""私有上传文件签名访问校验服务"""

from __future__ import annotations

import base64
import hashlib
import hmac
import mimetypes
import os
import time
from contextvars import ContextVar
from urllib.parse import urlencode, urlparse

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

UPLOAD_STORAGE_PREFIX = "/uploads/"
UPLOAD_ACCESS_PREFIX = "/api/v1/upload/access"
ALLOWED_UPLOAD_SUBDIRS = {"images", "voices"}

# 当前请求用户 ID：由认证依赖在请求上下文中写入，序列化器签发上传 URL 时绑定 actor
CURRENT_ACTOR_USER_ID: ContextVar[str | None] = ContextVar(
    "qinjian_upload_access_actor", default=None
)


def set_request_actor_user_id(user_id: str | None) -> None:
    CURRENT_ACTOR_USER_ID.set(str(user_id) if user_id else None)


def public_upload_access_enabled() -> bool:
    return bool(settings.UPLOAD_PUBLIC_ACCESS_ENABLED)


def normalize_upload_storage_path(value: str | None) -> str | None:
    if not value:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    parsed = urlparse(raw)
    candidate = parsed.path if parsed.scheme or parsed.netloc else raw.split("?", 1)[0]
    if candidate.startswith(UPLOAD_STORAGE_PREFIX):
        return candidate

    access_prefix = f"{UPLOAD_ACCESS_PREFIX}/"
    if candidate.startswith(access_prefix):
        relative_path = candidate[len(access_prefix) :].strip("/")
        if relative_path:
            return f"{UPLOAD_STORAGE_PREFIX}{relative_path}"

    return raw


def is_local_upload_path(value: str | None) -> bool:
    normalized = normalize_upload_storage_path(value)
    return bool(normalized and normalized.startswith(UPLOAD_STORAGE_PREFIX))


def build_upload_access_url(
    upload_path: str | None,
    *,
    actor_user_id=None,
    owner_scope: dict | None = None,
) -> str | None:
    normalized = normalize_upload_storage_path(upload_path)
    if not normalized or not normalized.startswith(UPLOAD_STORAGE_PREFIX):
        return upload_path

    relative_path = normalized[len(UPLOAD_STORAGE_PREFIX) :]
    expires_at = int(time.time()) + max(60, settings.UPLOAD_SIGNED_URL_EXPIRE_MINUTES * 60)
    scope = str((owner_scope or {}).get("scope") or "") or None
    owner_user_id = (owner_scope or {}).get("user_id")
    pair_id = (owner_scope or {}).get("pair_id")
    signature = _build_signature(
        normalized,
        expires_at,
        actor_user_id=actor_user_id,
        scope=scope,
        owner_user_id=owner_user_id,
        pair_id=pair_id,
    )
    query = {"expires": str(expires_at), "sig": signature}
    if actor_user_id is not None:
        query["actor"] = str(actor_user_id)
    if scope:
        query["scope"] = scope
    if owner_user_id is not None:
        query["owner"] = str(owner_user_id)
    if pair_id is not None:
        query["pair"] = str(pair_id)
    return f"{UPLOAD_ACCESS_PREFIX}/{relative_path}?{urlencode(query)}"


async def record_upload_asset_owner(
    db: AsyncSession | None,
    storage_path: str | None,
    *,
    actor_user_id,
    owner_scope: dict | None = None,
) -> None:
    normalized = normalize_upload_storage_path(storage_path)
    if db is None or not normalized or not normalized.startswith(UPLOAD_STORAGE_PREFIX):
        return

    relative_path = normalized[len(UPLOAD_STORAGE_PREFIX) :]
    parts = [part for part in relative_path.split("/") if part]
    if len(parts) != 2:
        return

    owner = owner_scope or {"scope": "user", "user_id": actor_user_id, "pair_id": None}
    from app.models import UploadAsset

    result = await db.execute(
        select(UploadAsset).where(UploadAsset.storage_path == normalized)
    )
    asset = result.scalar_one_or_none()
    owner_user_id = owner.get("user_id") or actor_user_id
    pair_id = owner.get("pair_id")
    scope = str(owner.get("scope") or "user")
    if asset:
        asset.owner_user_id = owner_user_id
        asset.pair_id = pair_id
        asset.scope = scope
    else:
        db.add(
            UploadAsset(
                storage_path=normalized,
                subdir=parts[0],
                filename=parts[1],
                owner_user_id=owner_user_id,
                pair_id=pair_id,
                scope=scope,
            )
        )
    await db.flush()


async def get_upload_owner_scope(
    db: AsyncSession,
    upload_path: str | None,
) -> dict | None:
    normalized = normalize_upload_storage_path(upload_path)
    if not normalized or not normalized.startswith(UPLOAD_STORAGE_PREFIX):
        return None

    from app.models import Checkin, Pair, UploadAsset, User

    asset_result = await db.execute(
        select(UploadAsset).where(UploadAsset.storage_path == normalized)
    )
    asset = asset_result.scalar_one_or_none()
    if asset:
        if asset.scope == "pair" and asset.pair_id is not None:
            pair = await db.get(Pair, asset.pair_id)
            if pair:
                return {
                    "scope": "pair",
                    "user_id": None,
                    "pair_id": pair.id,
                    "member_ids": [pair.user_a_id, pair.user_b_id],
                }
        return {
            "scope": "user",
            "user_id": asset.owner_user_id,
            "pair_id": asset.pair_id,
        }

    user_result = await db.execute(
        select(User).where(
            or_(User.avatar_url == normalized, User.wechat_avatar == normalized)
        )
    )
    user = user_result.scalar_one_or_none()
    if user:
        return {"scope": "user", "user_id": user.id, "pair_id": None}

    checkin_result = await db.execute(
        select(Checkin).where(
            or_(Checkin.image_url == normalized, Checkin.voice_url == normalized)
        )
    )
    checkin = checkin_result.scalar_one_or_none()
    if not checkin:
        return None

    if checkin.pair_id is None:
        return {"scope": "user", "user_id": checkin.user_id, "pair_id": None}

    pair = await db.get(Pair, checkin.pair_id)
    if not pair:
        return None
    return {
        "scope": "pair",
        "user_id": None,
        "pair_id": pair.id,
        "member_ids": [pair.user_a_id, pair.user_b_id],
    }


async def build_scoped_upload_access_url(
    db: AsyncSession | None,
    upload_path: str | None,
    *,
    actor_user_id,
    owner_scope: dict | None = None,
) -> str | None:
    normalized = normalize_upload_storage_path(upload_path)
    if not normalized or not normalized.startswith(UPLOAD_STORAGE_PREFIX):
        return upload_path

    owner = owner_scope
    if owner is None and db is not None:
        owner = await get_upload_owner_scope(db, normalized)
    if not owner:
        return None

    actor_str = str(actor_user_id)
    if owner["scope"] == "user":
        return (
            build_upload_access_url(
                normalized,
                actor_user_id=actor_user_id,
                owner_scope=owner,
            )
            if str(owner["user_id"]) == actor_str
            else None
        )

    member_ids = [str(item) for item in owner.get("member_ids") or [] if item]
    return (
        build_upload_access_url(
            normalized,
            actor_user_id=actor_user_id,
            owner_scope=owner,
        )
        if actor_str in member_ids
        else None
    )


def upload_owner_allows_actor(owner: dict | None, actor_user_id) -> bool:
    if not owner:
        return False
    actor_str = str(actor_user_id)
    if owner.get("scope") == "user":
        return str(owner.get("user_id")) == actor_str
    member_ids = [str(item) for item in owner.get("member_ids") or [] if item]
    return actor_str in member_ids


async def actor_can_reference_upload(
    db: AsyncSession | None,
    upload_path: str | None,
    *,
    actor_user_id,
) -> bool:
    normalized = normalize_upload_storage_path(upload_path)
    if not normalized or not normalized.startswith(UPLOAD_STORAGE_PREFIX):
        return True
    if db is None:
        return False
    owner = await get_upload_owner_scope(db, normalized)
    return upload_owner_allows_actor(owner, actor_user_id)


async def build_scoped_upload_response_payload(
    db: AsyncSession | None,
    storage_path: str,
    filename: str,
    size: int,
    *,
    actor_user_id,
    owner_scope: dict | None = None,
) -> dict:
    return {
        "url": storage_path,
        "access_url": await build_scoped_upload_access_url(
            db,
            storage_path,
            actor_user_id=actor_user_id,
            owner_scope=owner_scope,
        ),
        "filename": filename,
        "size": size,
    }


def to_client_upload_url(value: str | None) -> str | None:
    if not is_local_upload_path(value):
        return value
    actor_user_id = CURRENT_ACTOR_USER_ID.get()
    return build_upload_access_url(value, actor_user_id=actor_user_id)


def verify_upload_access(
    upload_path: str,
    expires_at: int,
    signature: str,
    *,
    actor_user_id=None,
    scope: str | None = None,
    owner_user_id=None,
    pair_id=None,
) -> bool:
    if expires_at < int(time.time()):
        return False
    expected = _build_signature(
        upload_path,
        expires_at,
        actor_user_id=actor_user_id,
        scope=scope,
        owner_user_id=owner_user_id,
        pair_id=pair_id,
    )
    return hmac.compare_digest(expected, signature or "")


def resolve_upload_file_path(upload_path: str) -> str:
    normalized = normalize_upload_storage_path(upload_path)
    if not normalized or not normalized.startswith(UPLOAD_STORAGE_PREFIX):
        raise ValueError("invalid upload path")

    relative_path = normalized[len(UPLOAD_STORAGE_PREFIX) :]
    parts = [part for part in relative_path.split("/") if part]
    if len(parts) != 2:
        raise ValueError("invalid upload path")

    subdir, filename = parts
    if subdir not in ALLOWED_UPLOAD_SUBDIRS:
        raise ValueError("unsupported upload subdir")

    base_dir = os.path.abspath(settings.UPLOAD_DIR)
    file_path = os.path.abspath(os.path.join(base_dir, subdir, filename))
    if os.path.commonpath([base_dir, file_path]) != base_dir:
        raise ValueError("invalid upload path")

    return file_path


def guess_upload_media_type(upload_path: str) -> str:
    file_path = resolve_upload_file_path(upload_path)
    media_type, _ = mimetypes.guess_type(file_path)
    return media_type or "application/octet-stream"


def build_upload_response_payload(storage_path: str, filename: str, size: int) -> dict:
    return {
        "url": storage_path,
        "access_url": build_upload_access_url(storage_path),
        "filename": filename,
        "size": size,
    }


def _build_signature(
    upload_path: str,
    expires_at: int,
    *,
    actor_user_id=None,
    scope: str | None = None,
    owner_user_id=None,
    pair_id=None,
) -> str:
    payload = "|".join(
        [
            upload_path,
            str(expires_at),
            str(actor_user_id or ""),
            str(scope or ""),
            str(owner_user_id or ""),
            str(pair_id or ""),
        ]
    )
    digest = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
