"""亲健 API 应用入口"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import auth, pairs, checkins, reports, upload, tree


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建表（开发环境用，生产环境用 Alembic）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 创建上传目录
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "images"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "voices"), exist_ok=True)
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# CORS - 允许 Web 前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件：上传的图片/语音
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# API 路由
app.include_router(auth.router, prefix="/api/v1")
app.include_router(pairs.router, prefix="/api/v1")
app.include_router(checkins.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(tree.router, prefix="/api/v1")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
