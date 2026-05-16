"""Signed access helpers for private uploaded files."""

from __future__ import annotations

import base64
import hashlib
import hmac
import mimetypes
import os
import time
from urllib.parse import urlparse

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

UPLOAD_STORAGE_PREFIX = "/uploads/"
UPLOAD_ACCESS_PREFIX = "/api/v1/upload/access"
ALLOWED_UPLOAD_SUBDIRS = {"images", "voices"}


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
    if not candidate.startswith(UPLOAD_STORAGE_PREFIX):
        return raw
    return candidate


def is_local_upload_path(value: str | None) -> bool:
    normalized = normalize_upload_storage_path(value)
    return bool(normalized and normalized.startswith(UPLOAD_STORAGE_PREFIX))


def build_upload_access_url(upload_path: str | None) -> str | None:
    normalized = normalize_upload_storage_path(upload_path)
    if not normalized or not normalized.startswith(UPLOAD_STORAGE_PREFIX):
        return upload_path

    relative_path = normalized[len(UPLOAD_STORAGE_PREFIX) :]
    expires_at = int(time.time()) + max(60, settings.UPLOAD_SIGNED_URL_EXPIRE_MINUTES * 60)
    signature = _build_signature(normalized, expires_at)
    return f"{UPLOAD_ACCESS_PREFIX}/{relative_path}?expires={expires_at}&sig={signature}"


async def get_upload_owner_scope(
    db: AsyncSession,
    upload_path: str | None,
) -> dict | None:
    normalized = normalize_upload_storage_path(upload_path)
    if not normalized or not normalized.startswith(UPLOAD_STORAGE_PREFIX):
        return None

    from app.models import Checkin, Pair, User

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
        return build_upload_access_url(normalized)

    actor_str = str(actor_user_id)
    if owner["scope"] == "user":
        return (
            build_upload_access_url(normalized)
            if str(owner["user_id"]) == actor_str
            else None
        )

    member_ids = [str(item) for item in owner.get("member_ids") or [] if item]
    return build_upload_access_url(normalized) if actor_str in member_ids else None


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
    return build_upload_access_url(value)


def verify_upload_access(upload_path: str, expires_at: int, signature: str) -> bool:
    if expires_at < int(time.time()):
        return False
    expected = _build_signature(upload_path, expires_at)
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


def _build_signature(upload_path: str, expires_at: int) -> str:
    digest = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"{upload_path}:{expires_at}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
