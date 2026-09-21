import os
import uuid
import mimetypes
import logging
import tempfile
import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.api.deps import DEMO_MODE_TOKEN, get_current_user
from app.models import User
from app.ai import transcribe_audio_result
from app.ai.reporter import analyze_image
from app.services.behavior_judgement import infer_language, summarize_text_emotion
from app.services.display_labels import emotion_label, language_label
from app.services.privacy_audit import log_privacy_event, privacy_audit_scope
from app.services.request_cooldown_store import consume_request_cooldown
from app.services.test_accounts import is_relaxed_test_account
from app.services.upload_access import (
    build_scoped_upload_response_payload,
    guess_upload_media_type,
    record_upload_asset_owner,
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
IMAGE_STORAGE_MODE_LABELS = {
    "analysis_only": "已生成分析结果，原图不会通过分析接口回传",
}
IMAGE_RETENTION_RECOMMENDATION_LABELS = {
    "persist": "适合提交后按私有媒体保留",
    "analysis_only": "更适合只保留分析结果",
}
IMAGE_PRIVACY_SENSITIVITY_LABELS = {
    "low": "低敏感",
    "medium": "中等敏感",
    "high": "高敏感",
}
IMAGE_RISK_LEVEL_LABELS = {
    "none": "未见明显风险",
    "watch": "值得留意",
    "high": "需要谨慎处理",
}
IMAGE_ANALYSIS_WINDOW_SECONDS = 60
IMAGE_ANALYSIS_MAX_ATTEMPTS = 2


def _normalize_content_type(content_type: str | None) -> str:
    return str(content_type or "").split(";", 1)[0].strip().lower()


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
    normalized_content_type = _normalize_content_type(file.content_type)
    if normalized_content_type not in ALLOWED_IMAGE_TYPES:
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


def _normalize_image_analysis(raw: dict | None) -> dict:
    payload = dict(raw or {})
    payload.setdefault("scene_summary", "暂时还没看清这张图里发生了什么")
    payload.setdefault("mood", "暂未识别")
    full_mood_tags = _unique_string_list(payload.get("mood_tags"), limit=8)
    emotion_weights = _normalize_emotion_weights(payload.get("emotion_weights"))
    weighted_tags = _unique_string_list(
        [item.get("tag") for item in emotion_weights],
        limit=8,
    )
    all_mood_tags = _unique_string_list([*weighted_tags, *full_mood_tags], limit=8)
    display_mood_tags = _unique_string_list(
        payload.get("display_mood_tags") or all_mood_tags,
        limit=3,
    )
    primary_mood = str(
        payload.get("primary_mood") or (display_mood_tags[0] if display_mood_tags else "")
    ).strip()
    secondary_moods = _unique_string_list(
        payload.get("secondary_moods") or all_mood_tags[1:],
        limit=5,
    )
    emotion_blend_summary = str(payload.get("emotion_blend_summary") or "").strip()
    if not emotion_blend_summary:
        emotion_blend_summary = (
            f"这张图更像是{primary_mood}里夹着{'、'.join(secondary_moods[:2])}。"
            if primary_mood and secondary_moods
            else f"这张图最明显的情绪线索是{primary_mood}。"
            if primary_mood
            else "图片线索还不够稳定，先只保留最关键的观察。"
        )
    payload["mood_tags"] = display_mood_tags
    payload["display_mood_tags"] = display_mood_tags
    payload["primary_mood"] = primary_mood or payload.get("mood") or "待判断"
    payload["secondary_moods"] = secondary_moods
    payload["emotion_weights"] = emotion_weights
    payload["emotion_blend_summary"] = emotion_blend_summary
    payload["user_facing"] = {
        "display_mood_tags": display_mood_tags,
        "blend_summary": emotion_blend_summary,
    }
    payload["emotion_profile"] = {
        "all_mood_tags": all_mood_tags,
        "primary_mood": payload["primary_mood"],
        "secondary_moods": secondary_moods,
        "emotion_weights": emotion_weights,
        "blend_summary": emotion_blend_summary,
    }
    payload.setdefault("relationship_stage", "待判断")
    payload.setdefault("interaction_signal", "暂时无法确认双方互动状态")
    payload.setdefault("social_signal", "暂时还没得到稳定结论")
    payload.setdefault("risk_level", "none")
    payload["risk_flags"] = list(payload.get("risk_flags") or [])[:3]
    payload["care_points"] = list(payload.get("care_points") or [])[:3]
    payload.setdefault("privacy_sensitivity", "medium")
    payload["privacy_reasons"] = list(payload.get("privacy_reasons") or [])[:3]
    payload.setdefault("retention_recommendation", "analysis_only")
    payload.setdefault("retention_reason", "当前更适合先保留分析结果，不急着长期保存原图。")
    score = payload.get("score")
    try:
        payload["score"] = max(1, min(10, int(score)))
    except (TypeError, ValueError):
        payload["score"] = 5
    payload["privacy_sensitivity_label"] = IMAGE_PRIVACY_SENSITIVITY_LABELS.get(
        str(payload.get("privacy_sensitivity") or "medium"),
        "中等敏感",
    )
    payload["risk_level_label"] = IMAGE_RISK_LEVEL_LABELS.get(
        str(payload.get("risk_level") or "none"),
        "未见明显风险",
    )
    payload["retention_recommendation_label"] = (
        IMAGE_RETENTION_RECOMMENDATION_LABELS.get(
            str(payload.get("retention_recommendation") or "analysis_only"),
            "更适合只保留分析结果",
        )
    )
    return payload


def _unique_string_list(value, *, limit: int) -> list[str]:
    items = value if isinstance(value, list) else []
    result: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _normalize_emotion_weights(value) -> list[dict]:
    items = value if isinstance(value, list) else []
    normalized: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        tag = str(item.get("tag") or "").strip()
        if not tag:
            continue
        try:
            score = float(item.get("score") or 0)
        except (TypeError, ValueError):
            score = 0.0
        normalized.append(
            {
                "tag": tag,
                "score": round(max(0.0, min(1.0, score)), 2),
                "tone": str(item.get("tone") or "neutral").strip() or "neutral",
            }
        )
    return normalized[:8]


def _derive_image_storage_mode(analysis: dict) -> tuple[str, str]:
    recommendation = str(analysis.get("retention_recommendation") or "analysis_only")
    if recommendation == "persist":
        return (
            "analysis_only",
            "分析接口只返回结果；如果你随后提交记录，原图会改为私有上传并仅在后台短期保留。",
        )
    return (
        "analysis_only",
        str(
            analysis.get("retention_reason")
            or "当前只返回分析结果，不会向前台返回原图访问入口。"
        ),
    )


async def _promote_temp_file(
    source_path: str,
    *,
    subdir: str,
    total_size: int,
    db: AsyncSession,
    actor_user_id,
) -> dict:
    ext = os.path.splitext(source_path)[1] or ".bin"
    filename = f"{uuid.uuid4().hex}{ext}"
    dir_path = os.path.join(settings.UPLOAD_DIR, subdir)
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, filename)
    os.replace(source_path, file_path)

    storage_path = f"/uploads/{subdir}/{filename}"
    owner_scope = {"scope": "user", "user_id": actor_user_id, "pair_id": None}
    await record_upload_asset_owner(
        db,
        storage_path,
        actor_user_id=actor_user_id,
        owner_scope=owner_scope,
    )
    return await build_scoped_upload_response_payload(
        db,
        storage_path,
        filename,
        total_size,
        actor_user_id=actor_user_id,
        owner_scope=owner_scope,
    )


async def _save_temp_file(file: UploadFile, subdir: str) -> tuple[str, str, int]:
    normalized_content_type = _normalize_content_type(file.content_type)
    ext = mimetypes.guess_extension(normalized_content_type) or ".bin"
    dir_path = os.path.join(settings.UPLOAD_DIR, subdir)
    os.makedirs(dir_path, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=ext,
        dir=dir_path,
    ) as temp_file:
        temp_path = temp_file.name

    total_size = 0
    async with aiofiles.open(temp_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            total_size += len(chunk)
            if total_size > settings.MAX_FILE_SIZE:
                os.remove(temp_path)
                raise HTTPException(
                    status_code=400,
                    detail=f"文件大小超过限制 ({settings.MAX_FILE_SIZE // 1024 // 1024}MB)",
                )
            await f.write(chunk)

    filename = os.path.basename(temp_path)
    storage_path = f"/uploads/{subdir}/{filename}"
    return temp_path, storage_path, total_size


@router.post("/image/analyze")
async def analyze_uploaded_image(
    file: UploadFile = File(...),
    context: str = Form(""),
    persist: bool = Form(False),
    privacy_mode: str = Form("cloud"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """分析图片中的关系线索，仅返回结果层信息。"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400, detail=f"不支持的图片格式：{file.content_type}"
        )
    if not await _verify_magic_bytes(file, ALLOWED_IMAGE_TYPES):
        raise HTTPException(
            status_code=400, detail="图片格式检验失败，可能是不合法的文件实体"
        )
    await consume_request_cooldown(
        bucket="image-analysis",
        scope_key=str(user.id),
        window_seconds=IMAGE_ANALYSIS_WINDOW_SECONDS,
        max_attempts=IMAGE_ANALYSIS_MAX_ATTEMPTS,
        limit_message="图片分析得有点频繁了",
        bypass=is_relaxed_test_account(user),
    )

    _ = persist
    _ = privacy_mode
    temp_path = None
    analysis_path = None
    total_size = 0

    try:
        temp_path, analysis_path, total_size = await _save_temp_file(
            file,
            "tmp_image_analysis",
        )

        with privacy_audit_scope(
            db=db,
            user_id=user.id,
            scope="solo",
            run_type="image_analysis",
        ):
            analysis = _normalize_image_analysis(
                await analyze_image(analysis_path, context=context)
            )

        storage_mode, storage_reason = _derive_image_storage_mode(analysis)

        await db.commit()
        return {
            "analysis": analysis,
            "storage": {
                "mode": storage_mode,
                "label": IMAGE_STORAGE_MODE_LABELS.get(storage_mode, "只保留分析结果"),
                "reason": storage_reason,
                "retention_recommendation": analysis["retention_recommendation"],
                "retention_recommendation_label": analysis["retention_recommendation_label"],
                "media_retention_days": 30,
                "download_available": False,
            },
            "size": total_size,
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/voice")
async def upload_voice(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传语音，返回相对URL"""
    normalized_content_type = _normalize_content_type(file.content_type)
    if normalized_content_type not in ALLOWED_VOICE_TYPES:
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
    normalized_content_type = _normalize_content_type(file.content_type)
    ext = mimetypes.guess_extension(normalized_content_type)
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
    owner_scope = {"scope": "user", "user_id": actor_user_id, "pair_id": None}
    await record_upload_asset_owner(
        db,
        storage_path,
        actor_user_id=actor_user_id,
        owner_scope=owner_scope,
    )
    return await build_scoped_upload_response_payload(
        db,
        storage_path,
        filename,
        total_size,
        actor_user_id=actor_user_id,
        owner_scope=owner_scope,
    )


@router.get("/access/{subdir}/{filename}")
async def access_uploaded_file(
    subdir: str,
    filename: str,
    expires: int,
    sig: str,
    actor: str | None = None,
    scope: str | None = None,
    owner: str | None = None,
    pair: str | None = None,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
):
    """通过签名 URL 访问私有上传文件。"""
    upload_path = f"/uploads/{subdir}/{filename}"
    if not verify_upload_access(
        upload_path,
        expires,
        sig,
        actor_user_id=actor,
        scope=scope,
        owner_user_id=owner,
        pair_id=pair,
    ):
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

    # 签名绑定了 actor 时，若请求携带有效凭据则校验身份一致；
    # 未携带凭据（浏览器 <img>/<audio> 直连）保持签名校验即可。
    if actor is not None and credentials is not None:
        token_user_id = None
        if credentials.credentials != DEMO_MODE_TOKEN:
            token_user_id = decode_access_token(credentials.credentials)
        if not token_user_id or str(token_user_id) != actor:
            await log_privacy_event(
                db,
                event_type="privacy.upload.access_denied",
                user_id=None,
                pair_id=None,
                entity_type="upload_access",
                entity_id=f"{subdir}/{filename}",
                payload={"subdir": subdir, "actor_mismatch": True},
                summary="拦截了一次 actor 与请求身份不一致的上传访问。",
            )
            await db.commit()
            raise HTTPException(status_code=403, detail="文件访问身份校验失败")

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
    """上传语音文件并转录为文字。"""
    # 验证文件类型
    normalized_content_type = _normalize_content_type(file.content_type)
    if normalized_content_type not in ALLOWED_VOICE_TYPES:
        raise HTTPException(
            status_code=400, detail=f"不支持的音频格式：{file.content_type}"
        )
    if not await _verify_magic_bytes(file, ALLOWED_VOICE_TYPES):
        raise HTTPException(
            status_code=400, detail="音频格式检验失败，可能是不合法的文件实体"
        )

    # 保存文件到临时位置
    ext = mimetypes.guess_extension(normalized_content_type) or ".mp3"
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

        # 调用统一 ASR Provider 转录
        with privacy_audit_scope(
            db=db,
            user_id=user.id,
            scope="solo",
            run_type="voice_transcription",
        ):
            transcription = await transcribe_audio_result(file_path)
            text = transcription.text
            audio_info = dict(transcription.audio_info or {})
            emotion_summary = summarize_text_emotion(text)
            language_code = str(audio_info.get("language") or infer_language(text))
            emotion_code = str(
                audio_info.get("emotion")
                or emotion_summary.get("sentiment")
                or "neutral"
            )
            if audio_info:
                if audio_info.get("language") is not None:
                    audio_info["language_label"] = language_label(audio_info.get("language"))
                if audio_info.get("emotion") is not None:
                    audio_info["emotion_label"] = emotion_label(audio_info.get("emotion"))

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

        return {
            "text": text,
            "size": total_size,
            "audio_info": audio_info or None,
            "emotion": emotion_label(emotion_code),
            "emotion_code": emotion_code,
            "emotion_summary": emotion_summary,
            "language": language_label(language_code),
            "language_code": language_code,
            "voice_emotion": {
                "code": emotion_code,
                "label": emotion_label(emotion_code),
            },
            "content_emotion": emotion_summary,
            "transcript_language": {
                "code": language_code,
                "label": language_label(language_code),
            },
        }

    except ValueError as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        await db.commit()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 确保清理临时文件
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.warning("voice transcription failed: %s", e.__class__.__name__)
        await db.commit()
        raise HTTPException(status_code=500, detail="语音转录暂不可用，请稍后再试")
