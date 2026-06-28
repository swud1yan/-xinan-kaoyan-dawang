"""
应用配置 — 从环境变量 / .env 文件加载
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ---- JWT ----
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 小时

    # ---- 数据库 ----
    DATABASE_URL: str = "sqlite+aiosqlite:///./xinan_dawang.db"

    # ---- LLM ----
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_MODEL: str = "qwen-plus"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    LLM_PROVIDER: str = "deepseek"  # deepseek | dashscope | anthropic

    # ---- Admin ----
    ADMIN_TOKEN: str = "admin123"

    # ---- FCM (可选) ----
    FCM_SERVER_KEY: str = ""

    # ---- 服务器 ----
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
