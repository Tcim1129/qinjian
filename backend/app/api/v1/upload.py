import os
import uuid
import mimetypes
import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.core.config import settings
from app.api.deps import get_current_user
from app.models import User
from app.ai import transcribe_audio

router = APIRouter(prefix="/upload", tags=["文件上传"])

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
    file: UploadFile = File(...), user: User = Depends(get_current_user)
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
    return await _save_file(file, "images")


@router.post("/voice")
async def upload_voice(
    file: UploadFile = File(...), user: User = Depends(get_current_user)
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
    return await _save_file(file, "voices")


async def _save_file(file: UploadFile, subdir: str) -> dict:
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

    url = f"/uploads/{subdir}/{filename}"
    return {"url": url, "filename": filename, "size": total_size}


@router.post("/transcribe")
async def transcribe_voice(
    file: UploadFile = File(...), user: User = Depends(get_current_user)
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
    dir_path = os.path.join(settings.UPLOAD_DIR, "voices")
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
        text = await transcribe_audio(file_path)

        # 删除临时文件
        os.remove(file_path)

        return {"text": text, "size": total_size}

    except Exception as e:
        # 确保清理临时文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"转录失败：{str(e)}")
