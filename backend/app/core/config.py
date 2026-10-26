from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="结构健康监测平台", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/resistance_db",
        alias="DATABASE_URL",
    )
    cors_origins: str = Field(
        default="http://127.0.0.1:5174,http://localhost:5174",
        alias="CORS_ORIGINS",
    )
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="CHANGE_ME", alias="ADMIN_PASSWORD")
    # 签发登录令牌用的密钥，长度不少于 32 字节
    secret_key: str = Field(
        default="resistance-platform-dev-secret-key-change-in-production",
        alias="SECRET_KEY",
    )
    # 0 表示不限制条数
    max_received_rows: int = Field(default=200000, alias="MAX_RECEIVED_ROWS")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
