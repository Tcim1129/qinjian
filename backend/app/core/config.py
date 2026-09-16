"""应用配置 - 通过环境变量加载"""

from urllib.parse import urlparse

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "亲健——基于生成式AI的泛亲密关系智能感知与维系平台"
    APP_TIMEZONE: str = "Asia/Shanghai"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ADMIN_EMAILS: str = ""
    RELAXED_TEST_ACCOUNT_EMAILS: str = ""
    ALLOW_DEMO_AGENT: bool = False
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8小时
    ENABLE_API_DOCS: bool = False
    ADDITIONAL_TRUSTED_HOSTS: str = ""
    PHONE_CODE_EXPIRE_MINUTES: int = 5
    PHONE_CODE_RESEND_COOLDOWN_SECONDS: int = 60
    PHONE_CODE_MAX_ATTEMPTS: int = 5
    PHONE_CODE_LENGTH: int = 4
    PAIR_INVITE_REFRESH_WINDOW_SECONDS: int = 60
    PAIR_INVITE_REFRESH_MAX_ATTEMPTS: int = 3
    PHONE_CODE_TEST_POPUP_ENABLED: bool = False
    PHONE_CODE_DEBUG_RETURN: bool = False
    PHONE_CODE_STORE: str = "memory"
    REDIS_URL: str = ""
    PHONE_CODE_REDIS_PREFIX: str = "qinjian:phone-code:"
    REQUEST_COOLDOWN_REDIS_PREFIX: str = "qinjian:request-cooldown:"
    REQUEST_COOLDOWN_REDIS_TIMEOUT_SECONDS: float = 0.5

    # 数据库
    DATABASE_URL: str = "postgresql+psycopg://qinjian:qinjian@localhost:5432/qinjian"

    # 前端来源
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    ADDITIONAL_FRONTEND_ORIGINS: str = ""
    ALLOW_FILE_ORIGIN_IN_DEBUG: bool = True

    # AI - 通用 OpenAI 兼容网关
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.deepseek.com"
    AI_TIMEOUT_SECONDS: int = 60
    AGENT_SESSION_TTL_HOURS: int = 12
    AGENT_CHAT_HISTORY_LIMIT: int = 8
    ASR_PROVIDER: str = "qwen3"
    OPENAI_COMPATIBLE_ASR_MODEL: str = "whisper-1"
    REALTIME_ASR_PROVIDER: str = "qwen3"
    REALTIME_ASR_TICKET_EXPIRE_SECONDS: int = 120
    REALTIME_ASR_MAX_SESSION_SECONDS: int = 60
    REALTIME_ASR_STOP_TIMEOUT_SECONDS: int = 20
    PRIVACY_SANDBOX_ENABLED: bool = True
    PRIVACY_MASK_LOGS: bool = True
    PRIVACY_REDACT_LLM_INPUT: bool = True
    PRIVACY_AUDIT_ENABLED: bool = True
    PRIVACY_TEXT_PROXY_ENABLED: bool = False
    PRIVACY_BENCHMARK_ENABLED: bool = True
    PRIVACY_SERVER_PROFILE: str = "2c2g_text_proxy"
    PRIVACY_AUDIO_PIPELINE_MODE: str = "cloud_transcription"
    PRIVACY_AUDIT_RETENTION_DAYS: int = 180
    PRIVACY_DELETE_GRACE_DAYS: int = 7
    PRIVACY_RETENTION_SWEEP_ENABLED: bool = True
    PRIVACY_RETENTION_SWEEP_INTERVAL_MINUTES: int = 60
    PRIVACY_RETENTION_BACKFILL_BATCH_SIZE: int = 200
    PRIVACY_RETENTION_CUTOFF_HOUR_LOCAL: int = 4
    PRIVACY_TEMP_FILE_RETENTION_HOURS: int = 24
    PRIVACY_TRANSCRIPTION_TEMP_DIR: str = "./uploads/tmp_transcriptions"
    PRIVACY_AUDIT_SUMMARY_CHARS: int = 240
    PRIVACY_EXTRA_SENSITIVE_TERMS: str = ""
    TASK_PLANNER_REMINDER_ENABLED: bool = True
    TASK_PLANNER_REMINDER_STARTUP_ENABLED: bool = False

    # AI - 硅基流动（兼容旧配置）
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    # Qwen3 ASR
    QWEN_ASR_API_KEY: str = ""
    QWEN_ASR_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_ASR_FILE_MODEL: str = "qwen3-asr-flash"
    QWEN_ASR_REALTIME_MODEL: str = "qwen3-asr-flash-realtime"
    # 讯飞实时语音转写大模型
    XFYUN_RTASR_APP_ID: str = ""
    XFYUN_RTASR_API_KEY: str = ""
    XFYUN_RTASR_API_SECRET: str = ""
    XFYUN_RTASR_WS_URL: str = "wss://office-api-ast-dx.iflyaisol.com/ast/communicate/v1"
    XFYUN_RTASR_LANG: str = "autodialect"
    # 多模态模型（图片+文本分析，默认走硅基流动 Kimi 2.6）
    AI_MULTIMODAL_MODEL: str = "qwen3.8-flash"
    # 文本模型（情感分析，性价比高）
    AI_TEXT_MODEL: str = "deepseek-v4.1-flash"
    AI_TEXT_FALLBACK_MODEL: str = "deepseek-v4.1-flash"
    AI_MULTIMODAL_FALLBACK_MODEL: str = "qwen3.8-flash"

    # 文件上传
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_PUBLIC_ACCESS_ENABLED: bool = False
    UPLOAD_SIGNED_URL_EXPIRE_MINUTES: int = 15

    # 微信登录
    WECHAT_APPID: str = ""
    WECHAT_SECRET: str = ""
    WECHAT_SESSION_URL: str = "https://api.weixin.qq.com/sns/jscode2session"

    model_config = {"env_file": (".env", ".env.local"), "extra": "ignore"}

    def frontend_origins(self) -> list[str]:
        origins = {
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            (self.FRONTEND_ORIGIN or "").strip(),
        }

        raw_extra = (self.ADDITIONAL_FRONTEND_ORIGINS or "").replace(";", ",")
        for item in raw_extra.split(","):
            origin = item.strip()
            if origin:
                origins.add(origin)

        if self.DEBUG and self.ALLOW_FILE_ORIGIN_IN_DEBUG:
            origins.add("null")

        return sorted(origin for origin in origins if origin)

    def frontend_origin_regex(self) -> str | None:
        if not self.DEBUG:
            return None
        return r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    def trusted_hosts(self) -> list[str]:
        hosts = {"localhost", "127.0.0.1", "backend", "web"}
        for origin in self.frontend_origins():
            if origin == "null":
                continue

            parsed_origin = urlparse(origin)
            if parsed_origin.hostname:
                hosts.add(parsed_origin.hostname)

        raw_extra = (self.ADDITIONAL_TRUSTED_HOSTS or "").replace(";", ",")
        for item in raw_extra.split(","):
            host = item.strip()
            if host:
                hosts.add(host)

        return sorted(hosts)

    def api_docs_enabled(self) -> bool:
        return bool(self.DEBUG or self.ENABLE_API_DOCS)


settings = Settings()
