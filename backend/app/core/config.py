import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Marketing Campaign Management System with AI"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "aia331-secret-key-change-in-production-super-secure"
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
        "https://marketflow.ictu.edu.vn",
        "http://marketflow.ictu.edu.vn",
        "https://*.ictu.edu.vn",
        "http://*.ictu.edu.vn"
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

settings = Settings()
