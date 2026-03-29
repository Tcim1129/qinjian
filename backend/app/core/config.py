"""应用配置 - 通过环境变量加载"""

from urllib.parse import urlparse

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "亲健 API"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ADMIN_EMAILS: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    ENABLE_API_DOCS: bool = False
    ADDITIONAL_TRUSTED_HOSTS: str = ""
    PHONE_CODE_EXPIRE_MINUTES: int = 5
    PHONE_CODE_RESEND_COOLDOWN_SECONDS: int = 60
    PHONE_CODE_MAX_ATTEMPTS: int = 5
    PHONE_CODE_LENGTH: int = 6
    PHONE_CODE_DEBUG_RETURN: bool = False
    PHONE_CODE_STORE: str = "memory"
    REDIS_URL: str = ""
    PHONE_CODE_REDIS_PREFIX: str = "qinjian:phone-code:"

    # 数据库
    DATABASE_URL: str = "postgresql+psycopg://qinjian:qinjian@localhost:5432/qinjian"

    # 前端来源
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # AI - 通用 OpenAI 兼容网关
    AI_API_KEY: str = ""
    AI_BASE_URL: str = ""
    AI_TIMEOUT_SECONDS: int = 60
    ASR_PROVIDER: str = "whisper"
    REALTIME_ASR_PROVIDER: str = "qwen3"
    REALTIME_ASR_TICKET_EXPIRE_SECONDS: int = 120
    QWEN_ASR_API_KEY: str = ""
    QWEN_ASR_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_ASR_FILE_MODEL: str = "qwen3-asr-flash"
    QWEN_ASR_REALTIME_MODEL: str = "qwen3-asr-flash-realtime-2026-02-10"
    XFYUN_RTASR_APP_ID: str = ""
    XFYUN_RTASR_API_KEY: str = ""
    XFYUN_RTASR_API_SECRET: str = ""
    XFYUN_RTASR_WS_URL: str = "wss://office-api-ast-dx.iflyaisol.com/ast/communicate/v1"
    XFYUN_RTASR_LANG: str = "autodialect"
    PRIVACY_SANDBOX_ENABLED: bool = True
    PRIVACY_MASK_LOGS: bool = True
    PRIVACY_REDACT_LLM_INPUT: bool = True
    PRIVACY_AUDIT_ENABLED: bool = True
    PRIVACY_AUDIT_RETENTION_DAYS: int = 180
    PRIVACY_DELETE_GRACE_DAYS: int = 7
    PRIVACY_TEMP_FILE_RETENTION_HOURS: int = 24
    PRIVACY_TRANSCRIPTION_TEMP_DIR: str = "./uploads/tmp_transcriptions"
    PRIVACY_AUDIT_SUMMARY_CHARS: int = 240

    # AI - 硅基流动（兼容旧配置）
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    # 多模态模型（图片+文本分析）
    AI_MULTIMODAL_MODEL: str = "moonshot/kimi-k2.5"
    # 文本模型（情感分析，性价比高）
    AI_TEXT_MODEL: str = "Pro/deepseek-ai/DeepSeek-V3.2"

    # 文件上传
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_PUBLIC_ACCESS_ENABLED: bool = False
    UPLOAD_SIGNED_URL_EXPIRE_MINUTES: int = 60
    UPLOAD_SIGNING_KEY: str = ""

    # 微信登录
    WECHAT_APPID: str = ""
    WECHAT_SECRET: str = ""
    WECHAT_SESSION_URL: str = "https://api.weixin.qq.com/sns/jscode2session"

    model_config = {"env_file": ".env", "extra": "ignore"}

    def trusted_hosts(self) -> list[str]:
        hosts = {"localhost", "127.0.0.1", "backend", "web"}
        parsed_origin = urlparse(self.FRONTEND_ORIGIN or "")
        if parsed_origin.hostname:
            hosts.add(parsed_origin.hostname)

        raw_extra = (self.ADDITIONAL_TRUSTED_HOSTS or "").replace(";", ",")
        for item in raw_extra.split(","):
            host = item.strip()
            if host:
                hosts.add(host)

        return sorted(hosts)

    def cors_allowed_origins(self) -> list[str]:
        origins: list[str] = []
        frontend_origin = (self.FRONTEND_ORIGIN or "").strip().rstrip("/")
        if frontend_origin:
            origins.append(frontend_origin)

        parsed_origin = urlparse(frontend_origin)
        if parsed_origin.hostname in {"localhost", "127.0.0.1"}:
            loopback_alias = "127.0.0.1" if parsed_origin.hostname == "localhost" else "localhost"
            alias_host = loopback_alias
            if parsed_origin.port:
                alias_host = f"{alias_host}:{parsed_origin.port}"
            origins.append(f"{parsed_origin.scheme}://{alias_host}")
            origins.append("null")

        return list(dict.fromkeys(origins))

    def api_docs_enabled(self) -> bool:
        return bool(self.DEBUG or self.ENABLE_API_DOCS)


settings = Settings()
