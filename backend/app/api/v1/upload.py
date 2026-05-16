import os
import uuid
import mimetypes
import logging
import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User
from app.ai import transcribe_audio
from app.services.privacy_audit import log_privacy_event, privacy_audit_scope
from app.services.upload_access import (
    build_scoped_upload_response_payload,
    guess_upload_media_type,
    resolve_upload_file_path,
    verify_upload_access,
)

router = APIRouter(prefix="/upload", tags=["文件上传"])
logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VOICE_TYPES = {
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "audio/webm",
    "audio/mp4",
    "audio/aac",
}


async def _verify_magic_bytes(file: UploadFile, allowed_types: set) -> bool:
    try:
        chunk = await file.read(2048)
        await file.seek(0)
    except Exception:
        return False
    if not chunk:
        return False

    if "image/jpeg" in allowed_types and chunk.startswith(b"\xff\xd8\xff"):
        return True
    if "image/png" in allowed_types and chunk.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if "image/gif" in allowed_types and (
        chunk.startswith(b"GIF87a") or chunk.startswith(b"GIF89a")
    ):
        return True
    if (
        "image/webp" in allowed_types
        and chunk.startswith(b"RIFF")
        and chunk[8:12] == b"WEBP"
    ):
        return True

    if "audio/mpeg" in allowed_types and (
        chunk.startswith(b"ID3")
        or chunk.startswith(b"\xff\xfb")
        or chunk.startswith(b"\xff\xf3")
        or chunk.startswith(b"\xff\xf2")
    ):
        return True
    if (
        "audio/wav" in allowed_types
        and chunk.startswith(b"RIFF")
        and chunk[8:12] == b"WAVE"
    ):
        return True
    if "audio/ogg" in allowed_types and chunk.startswith(b"OggS"):
        return True
    if "audio/webm" in allowed_types and chunk.startswith(b"\x1aE\xdf\xa3"):
        return True
    if "audio/mp4" in allowed_types and b"ftyp" in chunk[4:12]:
        return True
    if "audio/aac" in allowed_types and (
        chunk.startswith(b"\xff\xf1") or chunk.startswith(b"\xff\xf9")
    ):
        return True
    return False


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传图片，返回相对URL"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400, detail=f"不支持的图片格式：{file.content_type}"
        )
    if not await _verify_magic_bytes(file, ALLOWED_IMAGE_TYPES):
        raise HTTPException(
            status_code=400, detail="图片格式检验失败，可能是不合法的文件实体"
        )
    payload = await _save_file(file, "images", db=db, actor_user_id=user.id)
    await log_privacy_event(
        db,
        event_type="privacy.upload.created",
        user_id=user.id,
        entity_type="upload_image",
        entity_id=payload["filename"],
        payload={
            "scope": "solo",
            "subdir": "images",
            "size": payload["size"],
        },
        summary="保存了一份私有图片上传。",
    )
    await db.commit()
    return payload


@router.post("/voice")
async def upload_voice(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传语音，返回相对URL"""
    if file.content_type not in ALLOWED_VOICE_TYPES:
        raise HTTPException(
            status_code=400, detail=f"不支持的音频格式：{file.content_type}"
        )
    if not await _verify_magic_bytes(file, ALLOWED_VOICE_TYPES):
        raise HTTPException(
            status_code=400, detail="音频格式检验失败，可能是不合法的文件实体"
        )
    payload = await _save_file(file, "voices", db=db, actor_user_id=user.id)
    await log_privacy_event(
        db,
        event_type="privacy.upload.created",
        user_id=user.id,
        entity_type="upload_voice",
        entity_id=payload["filename"],
        payload={
            "scope": "solo",
            "subdir": "voices",
            "size": payload["size"],
        },
        summary="保存了一份私有语音上传。",
    )
    await db.commit()
    return payload


async def _save_file(
    file: UploadFile,
    subdir: str,
    *,
    db: AsyncSession,
    actor_user_id,
) -> dict:
    """保存文件到本地并返回URL（流式写入，防止大文件导致OOM）"""
    ext = mimetypes.guess_extension(file.content_type)
    if not ext:
        ext = os.path.splitext(file.filename or "file")[1] or ".bin"

    filename = f"{uuid.uuid4().hex}{ext}"
    dir_path = os.path.join(settings.UPLOAD_DIR, subdir)
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, filename)

    total_size = 0
    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 每次读取 1MB
            total_size += len(chunk)
            if total_size > settings.MAX_FILE_SIZE:
                # 清除已写入的残缺文件
                os.remove(file_path)
                raise HTTPException(
                    status_code=400,
                    detail=f"文件大小超过限制 ({settings.MAX_FILE_SIZE // 1024 // 1024}MB)",
                )
            await f.write(chunk)

    storage_path = f"/uploads/{subdir}/{filename}"
    return await build_scoped_upload_response_payload(
        db,
        storage_path,
        filename,
        total_size,
        actor_user_id=actor_user_id,
        owner_scope={"scope": "user", "user_id": actor_user_id, "pair_id": None},
    )


@router.get("/access/{subdir}/{filename}")
async def access_uploaded_file(
    subdir: str,
    filename: str,
    expires: int,
    sig: str,
    db: AsyncSession = Depends(get_db),
):
    """通过签名 URL 访问私有上传文件。"""
    upload_path = f"/uploads/{subdir}/{filename}"
    if not verify_upload_access(upload_path, expires, sig):
        await log_privacy_event(
            db,
            event_type="privacy.upload.access_denied",
            user_id=None,
            pair_id=None,
            entity_type="upload_access",
            entity_id=f"{subdir}/{filename}",
            payload={"subdir": subdir},
            summary="拦截了一次无效或过期的上传访问签名。",
        )
        await db.commit()
        raise HTTPException(status_code=403, detail="文件访问签名无效或已过期")

    try:
        file_path = resolve_upload_file_path(upload_path)
        media_type = guess_upload_media_type(upload_path)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="文件不存在") from exc

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        file_path,
        media_type=media_type,
        filename=filename,
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.post("/transcribe")
async def transcribe_voice(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传语音文件并转录为文字 - 使用 Whisper API"""
    # 验证文件类型
    if file.content_type not in ALLOWED_VOICE_TYPES:
        raise HTTPException(
            status_code=400, detail=f"不支持的音频格式：{file.content_type}"
        )
    if not await _verify_magic_bytes(file, ALLOWED_VOICE_TYPES):
        raise HTTPException(
            status_code=400, detail="音频格式检验失败，可能是不合法的文件实体"
        )

    # 保存文件到临时位置
    ext = mimetypes.guess_extension(file.content_type) or ".mp3"
    filename = f"{uuid.uuid4().hex}{ext}"
    dir_path = os.path.abspath(settings.PRIVACY_TRANSCRIPTION_TEMP_DIR)
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, filename)

    try:
        # 保存文件
        total_size = 0
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 每次读取 1MB
                total_size += len(chunk)
                if total_size > settings.MAX_FILE_SIZE:
                    os.remove(file_path)
                    raise HTTPException(
                        status_code=400,
                        detail=f"文件大小超过限制 ({settings.MAX_FILE_SIZE // 1024 // 1024}MB)",
                    )
                await f.write(chunk)

        # 调用 Whisper 转录
        with privacy_audit_scope(
            db=db,
            user_id=user.id,
            scope="solo",
            run_type="voice_transcription",
        ):
            text = await transcribe_audio(file_path)

        # 删除临时文件
        os.remove(file_path)

        await log_privacy_event(
            db,
            event_type="privacy.upload.created",
            user_id=user.id,
            entity_type="upload_transcription_source",
            entity_id=filename,
            payload={"scope": "solo", "subdir": "tmp_transcriptions", "size": total_size},
            summary="保存了一份待转录的临时语音文件。",
        )
        await db.commit()

        return {"text": text, "size": total_size}

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("voice transcription failed")
        raise HTTPException(
            status_code=503,
            detail="语音转录服务暂时不可用，请稍后再试",
        ) from exc
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
