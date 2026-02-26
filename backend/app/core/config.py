"""应用配置 - 通过环境变量加载"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "亲健 API"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://qinjian:qinjian@localhost:5432/qinjian"

    # AI - 硅基流动
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    # 多模态模型（图片+文本分析）
    AI_MULTIMODAL_MODEL: str = "moonshot/kimi-k2.5"
    # 文本模型（情感分析，性价比高）
    AI_TEXT_MODEL: str = "deepseek-ai/DeepSeek-V3"

    # 文件上传
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
