from pydantic_settings import BaseSettings
from typing import List, Dict, Any


class Settings(BaseSettings):
    # LLM 配置
    llm_api_key: str
    llm_base_url: str = "https://api.openai.com/v1"  # 可改为 DeepSeek / Grok 等
    llm_model: str = "gpt-4o"

    # X (Twitter) 配置
    x_bearer_token: str
    x_api_key: str | None = None
    x_api_secret: str | None = None
    x_access_token: str | None = None
    x_access_secret: str | None = None

    # 白名单（用户名或用户ID）
    whitelist: List[str] = []

    # 基础策略
    policies: Dict[str, Any] = {
        "max_engage_per_hour": 8,
        "must_declare_ai": True,
        "respect_rate_limits": True,
    }

    # 记忆相关
    chroma_persist_dir: str = "data/chroma"
    sqlite_db_path: str = "data/sqlite/memory.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
