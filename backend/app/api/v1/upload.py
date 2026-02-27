import os
import uuid
import mimetypes
import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.core.config import settings
from app.api.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/upload", tags=["文件上传"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VOICE_TYPES = {"audio/mpeg", "audio/wav", "audio/ogg", "audio/webm", "audio/mp4", "audio/aac"}


@router.post("/image")
async def upload_image(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """上传图片，返回相对URL"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式：{file.content_type}")
    return await _save_file(file, "images")


@router.post("/voice")
async def upload_voice(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """上传语音，返回相对URL"""
    if file.content_type not in ALLOWED_VOICE_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的音频格式：{file.content_type}")
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
                raise HTTPException(status_code=400, detail=f"文件大小超过限制 ({settings.MAX_FILE_SIZE // 1024 // 1024}MB)")
            await f.write(chunk)

    url = f"/uploads/{subdir}/{filename}"
    return {"url": url, "filename": filename, "size": total_size}
