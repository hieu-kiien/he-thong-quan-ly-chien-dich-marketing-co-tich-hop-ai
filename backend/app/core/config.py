"""Cấu hình ứng dụng đọc từ biến môi trường / file `.env` (pydantic-settings)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

DEFAULT_JWT_SECRET = "dev-only-insecure-secret-change-me"
DEFAULT_DATABASE_URL = f"sqlite:///{(BACKEND_DIR / 'data' / 'marketflow.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "MarketFlow"
    APP_ENV: str = "development"  # development | test | production
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = DEFAULT_DATABASE_URL

    JWT_SECRET: str = DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 8 * 60
    BCRYPT_ROUNDS: int = 12

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    AI_RUNNER_URL: str = ""
    AI_RUNNER_TOKEN: str = ""

    LOGIN_MAX_FAILURES: int = 5
    LOGIN_WINDOW_SECONDS: int = 5 * 60

    @field_validator("APP_ENV")
    @classmethod
    def _normalize_env(cls, value: str) -> str:
        return (value or "development").strip().lower()

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def validate_for_runtime(self) -> None:
        """Từ chối khởi động production với bí mật mặc định / thiếu cấu hình."""
        if not self.is_production:
            return
        problems: list[str] = []
        if not self.JWT_SECRET or self.JWT_SECRET == DEFAULT_JWT_SECRET or len(self.JWT_SECRET) < 32:
            problems.append("JWT_SECRET phải được đặt (>= 32 ký tự, khác giá trị mặc định)")
        if self.DATABASE_URL.startswith("sqlite"):
            problems.append("DATABASE_URL production phải là PostgreSQL")
        if self.AI_RUNNER_URL and not self.AI_RUNNER_TOKEN:
            problems.append("AI_RUNNER_TOKEN phải được đặt khi có AI_RUNNER_URL")
        if problems:
            raise RuntimeError("Cấu hình production không hợp lệ: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
