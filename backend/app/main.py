"""亲健——基于生成式智能的泛亲密关系智能感知与维系平台应用入口"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.services.login_attempts import build_login_attempt_store
from app.services.phone_code_store import close_phone_code_store
from app.services.phone_code_store import build_phone_code_store
from app.services.request_cooldown_store import close_request_cooldown_store
from app.services.privacy_runtime import (
    run_privacy_maintenance_cycle,
    run_privacy_maintenance_loop,
    stop_privacy_maintenance_loop,
)
from app.services.task_planner import (
    run_task_planner_reminder_cycle,
    run_task_planner_reminder_loop,
    stop_task_planner_reminder_loop,
)
from app.services.upload_access import public_upload_access_enabled

APP_DESCRIPTION = """
亲健——基于生成式智能的泛亲密关系智能感知与维系平台。
面向泛亲密关系健康场景，深度集成大模型能力，提供情感感知、危机识别与维系干预等全链路闭环方案。
涵盖账号认证、关系打卡、危机预警、关系智能画像、干预计划、剧本运行时、策略审计和叙事对齐等核心能力。
"""

OPENAPI_TAGS = [
    {"name": "认证", "description": "注册、登录、手机号验证码与账号资料维护。"},
    {"name": "配对", "description": "关系配对、绑定、解绑与配对状态管理。"},
    {"name": "打卡", "description": "每日/个人打卡、情绪与互动信息采集。"},
    {"name": "报告", "description": "日报、周报等关系报告生成与查询。"},
    {"name": "文件上传", "description": "图片、语音等上传资源管理。"},
    {"name": "关系树", "description": "关系树数据结构与节点内容查询。"},
    {"name": "危机预警", "description": "风险识别、危机提醒与修复方案。"},
    {"name": "关系任务", "description": "关系任务生成、执行与反馈回收。"},
    {"name": "异地关系", "description": "异地陪伴、补偿活动与专项能力。"},
    {"name": "里程碑", "description": "关系里程碑、成长节点与回顾能力。"},
    {"name": "社群", "description": "社群内容与互动入口。"},
    {"name": "智能陪伴", "description": "助手会话、聊天引导与发消息前预演。"},
    {
        "name": "关系智能",
        "description": "关系画像、时间轴、干预计划、策略审计与叙事对齐接口。",
    },
    {"name": "隐私沙盒", "description": "隐私状态、删除请求、审计与保留治理接口。"},
    {"name": "admin", "description": "策略发布台、版本审计、回滚与管理接口。"},
]


UPLOAD_ROOT = os.path.abspath(settings.UPLOAD_DIR)
logger = logging.getLogger(__name__)

SQLITE_ADDITIVE_SCHEMA_COLUMNS = {
    "pairs": {
        "task_planner_settings": "JSON",
    },
    "user_notifications": {
        "target_path": "VARCHAR(255)",
    },
    "pair_change_requests": {
        "allow_retention": "BOOLEAN NOT NULL DEFAULT 0",
        "phase": "VARCHAR(50)",
        "expires_at": "DATETIME",
        "resolution_reason": "VARCHAR(50)",
    },
    "relationship_tasks": {
        "importance_level": "VARCHAR(20) NOT NULL DEFAULT 'medium'",
    },
}


def _ensure_upload_dirs() -> None:
    os.makedirs(UPLOAD_ROOT, exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_ROOT, "images"), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_ROOT, "voices"), exist_ok=True)


def _ensure_sqlite_additive_schema(sync_conn) -> None:
    if sync_conn.dialect.name != "sqlite":
        return

    inspector = inspect(sync_conn)
    table_names = set(inspector.get_table_names())
    for table_name, column_defs in SQLITE_ADDITIVE_SCHEMA_COLUMNS.items():
        if table_name not in table_names:
            continue
        existing_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        for column_name, column_definition in column_defs.items():
            if column_name in existing_columns:
                continue
            sync_conn.execute(
                text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
            )


def _is_using_weak_database_secret() -> bool:
    try:
        db_url = make_url(settings.DATABASE_URL)
    except Exception:
        return False

    weak_passwords = {"qinjian", "qinjian_dev_123", "change-me-in-production"}
    return str(db_url.password or "").strip() in weak_passwords


def _is_secret_key_strong_enough(secret_key: str) -> bool:
    return len(secret_key.encode("utf-8")) >= 32


def _validate_production_runtime_settings() -> None:
    if settings.PHONE_CODE_TEST_POPUP_ENABLED:
        raise RuntimeError("生产环境禁止开启验证码测试弹窗。")

    if settings.PHONE_CODE_DEBUG_RETURN:
        raise RuntimeError("生产环境禁止返回验证码调试字段。")

    build_phone_code_store(settings_obj=settings)
    build_login_attempt_store(settings_obj=settings)


_ensure_upload_dirs()


@asynccontextmanager
async def lifespan(app: FastAPI):
    privacy_task: asyncio.Task | None = None
    task_planner_task: asyncio.Task | None = None
    if not settings.DEBUG and settings.SECRET_KEY == "change-me-in-production":
        raise RuntimeError(
            "CRITICAL SECURITY ERROR: 检测到非 DEBUG 环境下使用了默认弱密钥！"
            "生产环境必须通过 SECRET_KEY 环境变量修改密钥以保证 JWT 安全。"
        )
    if not settings.DEBUG and not _is_secret_key_strong_enough(settings.SECRET_KEY):
        raise RuntimeError("生产环境 SECRET_KEY 长度不足 32 字节，拒绝启动。")
    if not settings.DEBUG:
        _validate_production_runtime_settings()
    if not settings.DEBUG and _is_using_weak_database_secret():
        raise RuntimeError("生产环境检测到默认数据库密码，请立即替换 DB_PASSWORD。")
    if not settings.DEBUG and settings.ALLOW_DEMO_AGENT:
        logger.warning(
            "安全提醒：生产环境启用了 ALLOW_DEMO_AGENT，"
            "任何人都可以使用字面量 'demo-mode' 令牌进入内置演示账号。"
            "仅建议在路演/演示环境使用，正式环境请关闭。"
        )
    # Alembic 负责迁移；create_all 仅在表完全不存在时兜底
    # 注意：create_all 不会修改已有表结构，所以不会和 Alembic 冲突
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_sqlite_additive_schema)
    # 创建上传目录
    _ensure_upload_dirs()
    if settings.PRIVACY_RETENTION_SWEEP_ENABLED:
        try:
            await run_privacy_maintenance_cycle(reason="startup")
        except Exception as exc:  # pragma: no cover - startup logging
            logger.warning("启动时隐私维护失败，已跳过: %s", exc.__class__.__name__)
        privacy_task = asyncio.create_task(
            run_privacy_maintenance_loop(),
            name="privacy-maintenance-loop",
        )
    if settings.TASK_PLANNER_REMINDER_ENABLED:
        if settings.TASK_PLANNER_REMINDER_STARTUP_ENABLED:
            try:
                await run_task_planner_reminder_cycle()
            except Exception as exc:  # pragma: no cover - startup logging
                logger.warning("启动时任务提醒检查失败，已跳过: %s", exc.__class__.__name__)
        task_planner_task = asyncio.create_task(
            run_task_planner_reminder_loop(),
            name="task-planner-reminder-loop",
        )
    try:
        yield
    finally:
        await stop_privacy_maintenance_loop(privacy_task)
        await stop_task_planner_reminder_loop(task_planner_task)
        await close_request_cooldown_store()
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
    allow_origins=settings.frontend_origins(),
    allow_origin_regex=settings.frontend_origin_regex(),
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
