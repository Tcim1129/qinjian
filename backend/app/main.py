"""亲健 API 应用入口"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import make_url

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.services.phone_code_store import close_phone_code_store
from app.services.upload_access import public_upload_access_enabled

APP_DESCRIPTION = """
亲健 API 面向关系健康场景，覆盖账号认证、关系打卡、危机预警、关系智能画像、
干预计划、剧本运行时、策略审计和叙事对齐等核心能力。
"""

OPENAPI_TAGS = [
    {"name": "认证", "description": "注册、登录、手机号验证码与账号资料维护。"},
    {"name": "配对", "description": "关系配对、绑定、解绑与配对状态管理。"},
    {"name": "打卡", "description": "每日/个人打卡、情绪与互动信息采集。"},
    {"name": "报告", "description": "日报、周报等关系报告生成与查询。"},
    {"name": "文件上传", "description": "图片、语音等上传资源管理。"},
    {"name": "关系树", "description": "关系树数据结构与节点内容查询。"},
    {"name": "危机预警", "description": "风险识别、危机告警与修复协议。"},
    {"name": "关系任务", "description": "关系任务生成、执行与反馈回收。"},
    {"name": "异地关系", "description": "异地陪伴、补偿活动与专项能力。"},
    {"name": "里程碑", "description": "关系里程碑、成长节点与回顾能力。"},
    {"name": "社群", "description": "社群内容与互动入口。"},
    {"name": "智能陪伴", "description": "Agent 会话、聊天引导与发消息前预演。"},
    {
        "name": "关系智能",
        "description": "关系画像、时间轴、干预计划、策略审计与叙事对齐接口。",
    },
    {"name": "隐私沙盒", "description": "隐私状态、删除请求、审计与保留治理接口。"},
    {"name": "admin", "description": "策略发布台、版本审计、回滚与管理接口。"},
]


UPLOAD_ROOT = os.path.abspath(settings.UPLOAD_DIR)


def _ensure_upload_dirs() -> None:
    os.makedirs(UPLOAD_ROOT, exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_ROOT, "images"), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_ROOT, "voices"), exist_ok=True)


def _is_using_weak_database_secret() -> bool:
    try:
        db_url = make_url(settings.DATABASE_URL)
    except Exception:
        return False

    weak_passwords = {"qinjian", "qinjian_dev_123", "change-me-in-production"}
    return str(db_url.password or "").strip() in weak_passwords


def _is_secret_key_strong_enough(secret_key: str) -> bool:
    return len(secret_key.encode("utf-8")) >= 32


_ensure_upload_dirs()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.DEBUG and settings.SECRET_KEY == "change-me-in-production":
        raise RuntimeError(
            "CRITICAL SECURITY ERROR: 检测到非 DEBUG 环境下使用了默认弱密钥！"
            "生产环境必须通过 SECRET_KEY 环境变量修改密钥以保证 JWT 安全。"
        )
    if not settings.DEBUG and not _is_secret_key_strong_enough(settings.SECRET_KEY):
        raise RuntimeError("生产环境 SECRET_KEY 长度不足 32 字节，拒绝启动。")
    if not settings.DEBUG and settings.PHONE_CODE_DEBUG_RETURN:
        raise RuntimeError("生产环境禁止返回验证码调试字段。")
    if not settings.DEBUG and _is_using_weak_database_secret():
        raise RuntimeError("生产环境检测到默认数据库密码，请立即替换 DB_PASSWORD。")
    # Alembic 负责迁移；create_all 仅在表完全不存在时兜底
    # 注意：create_all 不会修改已有表结构，所以不会和 Alembic 冲突
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 创建上传目录
    _ensure_upload_dirs()
    try:
        yield
    finally:
        await close_phone_code_store()

api_docs_enabled = settings.api_docs_enabled()
app = FastAPI(
    title=settings.APP_NAME,
    description=APP_DESCRIPTION.strip(),
    version="2026.03",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
    docs_url="/docs" if api_docs_enabled else None,
    redoc_url="/redoc" if api_docs_enabled else None,
    openapi_url="/openapi.json" if api_docs_enabled else None,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts(),
)

# CORS - 允许 Web 前端跨域 (收紧为仅允许明确的前端源)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件：仅在显式开启兼容模式时公开暴露上传目录
if public_upload_access_enabled():
    app.mount("/uploads", StaticFiles(directory=UPLOAD_ROOT), name="uploads")

# API 路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/api/health", tags=["admin"], summary="服务健康检查")
async def health_check():
    return {"status": "ok"}
