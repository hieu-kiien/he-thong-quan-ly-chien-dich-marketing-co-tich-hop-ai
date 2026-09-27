import os
import logging
from pathlib import Path
from typing import Optional, Set
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

INSECURE_SECRET_PATTERNS: Set[str] = {
    "aia331-secret-key-change-in-production-super-secure",
    "aia331-super-secret-production-key-change-it",
    "your-super-secret-jwt-key",
    "change-me",
    "changethisinproduction",
    "secret",
    "admin",
    "12345678",
}


class Settings(BaseSettings):
    APP_NAME: str = "Marketing Campaign Management System with AI"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "aia331-secret-key-change-in-production-super-secure"
    JWT_SECRET_KEY: Optional[str] = None
    BYOK_ENCRYPTION_KEY: Optional[str] = None
    BYOK_ROTATION_KEYS: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # CORS Origins
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost",
        "http://localhost:80",
        "https://kienhieu.id.vn",
        "http://kienhieu.id.vn",
        "https://marketing.kienhieu.id.vn",
        "http://marketing.kienhieu.id.vn",
        "https://*.kienhieu.id.vn",
        "http://*.kienhieu.id.vn",
        "https://*.onrender.com"
    ]

    # Base directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATABASE_URL: str = "sqlite:///./marketing_campaigns.db"

    # AI Configuration
    AI_PROVIDER: str = "opencode"
    AI_BASE_URL: str = "https://api.opencode.ai/v1"
    AI_API_KEY: str = ""
    AI_MODEL: str = "muse-spark-1.3"
    AI_TIMEOUT_SECONDS: int = 10
    AI_MAX_RETRIES: int = 2
    AI_ENABLE_FALLBACK: bool = True

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        extra="allow"
    )


def validate_security_configuration(
    s: Optional[Settings] = None,
    enforce_production: Optional[bool] = None,
) -> bool:
    """Kiểm tra tính an toàn của cấu hình bảo mật.
    Từ chối khởi động (raise RuntimeError) nếu SECRET_KEY, JWT_SECRET_KEY hoặc BYOK_ENCRYPTION_KEY
    là giá trị placeholder không an toàn hoặc thiếu trong môi trường production.
    """
    target = s or settings
    is_prod = enforce_production if enforce_production is not None else (
        (str(target.APP_ENV).lower() == "production") or
        (os.getenv("APP_ENV", "").lower() == "production")
    )

    def _is_insecure(val: Optional[str]) -> bool:
        if not val or not str(val).strip():
            return True
        v = str(val).strip().lower()
        if v in {p.lower() for p in INSECURE_SECRET_PATTERNS}:
            return True
        if any(substr in v for substr in ["change-in-production", "change-it", "placeholder", "changeme"]):
            return True
        if len(str(val).strip()) < 32:
            return True
        return False

    # 1. Kiểm tra JWT Secret Key (hoặc fallback SECRET_KEY)
    effective_jwt = target.JWT_SECRET_KEY if (target.JWT_SECRET_KEY and target.JWT_SECRET_KEY.strip()) else target.SECRET_KEY
    if not effective_jwt or not str(effective_jwt).strip():
        if is_prod:
            raise RuntimeError("FATAL: JWT Secret Key hoặc SECRET_KEY không được để trống trong môi trường production!")
        logger.warning("[Security] JWT Secret Key / SECRET_KEY is empty in non-production mode.")
        return False

    if is_prod and _is_insecure(effective_jwt):
        raise RuntimeError(
            "FATAL: Không thể khởi động ứng dụng trên Production với JWT_SECRET_KEY / SECRET_KEY mặc định, "
            "chứa placeholder không an toàn hoặc độ dài nhỏ hơn 32 ký tự!"
        )

    # 2. Kiểm tra BYOK Encryption Key (hoặc fallback SECRET_KEY)
    effective_byok = target.BYOK_ENCRYPTION_KEY if (target.BYOK_ENCRYPTION_KEY and target.BYOK_ENCRYPTION_KEY.strip()) else target.SECRET_KEY
    if not effective_byok or not str(effective_byok).strip():
        if is_prod:
            raise RuntimeError("FATAL: BYOK_ENCRYPTION_KEY hoặc SECRET_KEY không được để trống trong môi trường production!")
        logger.warning("[Security] BYOK_ENCRYPTION_KEY / SECRET_KEY is empty in non-production mode.")
        return False

    if is_prod and _is_insecure(effective_byok):
        raise RuntimeError(
            "FATAL: Không thể khởi động ứng dụng trên Production với BYOK_ENCRYPTION_KEY / SECRET_KEY mặc định, "
            "chứa placeholder không an toàn hoặc độ dài nhỏ hơn 32 ký tự!"
        )

    return True


settings = Settings()
validate_security_configuration(settings)

