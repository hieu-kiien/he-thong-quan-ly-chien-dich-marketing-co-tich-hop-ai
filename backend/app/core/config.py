import os
import logging
from pathlib import Path
from typing import List, Optional, Set
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.services.ai.providers import SUPPORTED_PROVIDER_SLUGS

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

    # Email cua tai khoan ADMIN duoc bootstrap. Xem app/core/bootstrap_admin.py.
    # Rong (mac dinh) => khong tao gi, he thong chay ma khong co ADMIN.
    BOOTSTRAP_ADMIN_EMAIL: Optional[str] = None
    BOOTSTRAP_ADMIN_PASSWORD: Optional[str] = None
    BOOTSTRAP_ADMIN_NAME: str = "Platform Admin"
    
    # CORS Origins
    # 4173 la cong `vite preview` mac dinh cua Playwright. Workflow CI cap rieng
    # mot port cho MOI invocation (4173 mock, 4174 live, 4175 probes, 4180 WCAG)
    # de cac lan chay khong trung port, nen danh sach origin E2E phai bao phu
    # tap cac cong do. Neu thieu, moi request API cua bo test E2E chay tren
    # backend that (E2E_MODE=live) se bi CORS chan.
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        # Cong rieng cho cac invocation Playwright khac trong CI (xem .github/workflows/ci.yml).
        "http://localhost:4174",
        "http://127.0.0.1:4174",
        "http://localhost:4175",
        "http://127.0.0.1:4175",
        "http://localhost:4180",
        "http://127.0.0.1:4180",
        "http://localhost",
        "http://localhost:80",
        "https://kienhieu.id.vn",
        "http://kienhieu.id.vn",
        "https://marketing.kienhieu.id.vn",
        "http://marketing.kienhieu.id.vn",
        # Ghi chú: CORSMiddleware của Starlette so khớp `origin in allow_origins`
        # theo chuỗi CHÍNH XÁC. Mẫu "https://*.kienhieu.id.vn" / "https://*.onrender.com"
        # ở đây KHÔNG BAO GIỜ khớp được — chúng trông như có phủ nhưng thực tế
        # không cho phép origin nào cả. Nếu cần hỗ trợ subdomain, hãy dùng
        # `allow_origin_regex` bên dưới, đừng thêm wildcard vào danh sách này.
    ]

    # Regex CORS cho subdomain. Starlette CHỈ dùng `allow_origins` khi regex rỗng,
    # nên đây là cách duy nhất để `https://*.kienhieu.id.vn` thật sự được phép.
    ALLOWED_ORIGIN_REGEXES: List[str] = [
        r"^https://([a-z0-9-]+\.)*kienhieu\.id\.vn$",
        r"^http://([a-z0-9-]+\.)*kienhieu\.id\.vn$",
        r"^https://([a-z0-9-]+\.)*onrender\.com$",
    ]

    # Base directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATABASE_URL: str = "sqlite:///./marketing_campaigns.db"

    # AI Configuration.
    # AI_PROVIDER mặc định PHẢI là một provider mà ai_service thật sự xử lý
    # (gemini/openrouter/openai). Trước đây mặc định là "opencode", không khớp
    # nhánh nào trong ai_service -> env_key = None -> rơi im lặng xuống template
    # dự phòng Tier 4. Người dùng tưởng đang gọi AI thật nhưng thực ra nhận nội
    # dung mẫu, và .env.example (openrouter) + docker-compose (gemini) lại chỉ định
    # hai giá trị khác nữa. Nay cả ba nơi thống nhất và giá trị hợp lệ được validate
    # ngay khi khởi động.
    AI_PROVIDER: str = "gemini"
    AI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    AI_API_KEY: str = ""
    AI_MODEL: str = "gemini-2.5-flash"
    AI_TIMEOUT_SECONDS: int = 10
    AI_MAX_RETRIES: int = 2
    AI_ENABLE_FALLBACK: bool = True
    # Trần token đầu ra cho adapter Anthropic. Chỉ có tác dụng khi
    # AI_PROVIDER=anthropic; xem app/services/ai/anthropic_adapter.py.
    ANTHROPIC_MAX_TOKENS: int = 8192
    # Ghi đè base URL của provider chạy cục bộ.
    #
    # Cố ý dùng tiền tố `MARKETFLOW_`. Biến `ANTHROPIC_BASE_URL` /
    # `OLLAMA_BASE_URL` / `HF_BASE_URL` không có tiền tố bắt buộc, và chúng
    # từng được đặt sẵn trong môi trường hệ thống của nhiều máy (kể cả các
    # cấu hình công cụ AI cục bộ) và trỏ tới một endpoint khác. Đọc tên thường
    # sẽ khiến mọi lời gọi Claude của hệ thống bị âm thầm chuyển sang đúng
    # endpoint đó mà không có cảnh báo nào.
    #
    # Registry đọc biến đã có tiền tố: MARKETFLOW_OLLAMA_BASE_URL,
    # MARKETFLOW_ANTHROPIC_BASE_URL, MARKETFLOW_HF_BASE_URL. Các khai báo ở
    # đây giữ cho chúng hiện diện trong `settings` nhưng KHÔNG được dùng để
    # định tuyến.
    OLLAMA_BASE_URL: Optional[str] = None
    ANTHROPIC_BASE_URL: Optional[str] = None
    HF_BASE_URL: Optional[str] = None
    # "opencode" là endpoint OpenAI-compatible của chính opencode
    # (https://opencode.ai/zen/v1), được `ai_service` xử lý như một provider
    # thường: chỉ khác ở chỗ không ghim base_url cứng. Nhờ vậy backend có thể
    # dùng đúng những model opencode đang cấu hình mà không cần mua credits.
    #
    # DANH SÁCH này lấy từ `app/services/ai/providers.py` — một danh sách duy
    # nhất cho config, schema, endpoint kiểm tra kết nối, dispatcher và UI.
    # Không thêm provider mới ở đây: thêm vào registry, mọi nơi tự nhận.
    SUPPORTED_AI_PROVIDERS: List[str] = list(SUPPORTED_PROVIDER_SLUGS)

    # Scheduler nền trong tiến trình. Xem giải thích ở `on_startup` (main.py):
    # trên Cloudflare, scheduler trong container ghi thẳng vào SQLite mà không
    # qua HTTP nên không được snapshot lên R2, dẫn tới mất dữ liệu khi container
    # bị evict. Đặt false cho môi trường đó.
    SCHEDULER_ENABLED: bool = True

    # Secret nội bộ để Durable Object trên Cloudflare gọi
    # POST /api/v1/schedules/trigger-worker (xem cloudflare/src/index.ts).
    # Để trống thì đường gọi bằng secret bị tắt và endpoint chỉ nhận Bearer token.
    SCHEDULER_SECRET: str = ""

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

    # 0. SECRET_KEY phải tự nó an toàn trong production.
    # Nó không chỉ là fallback: get_multi_fernet() dùng nó làm legacy decryption
    # key (xem app/core/crypto.py), nên SECRET_KEY yếu vẫn là lỗ hổng dù
    # JWT_SECRET_KEY / BYOK_ENCRYPTION_KEY đã được tách riêng và an toàn.
    if is_prod and _is_insecure(target.SECRET_KEY):
        raise RuntimeError(
            "FATAL: SECRET_KEY không được để trống, dùng giá trị mặc định, "
            "chứa placeholder không an toàn hoặc độ dài nhỏ hơn 32 ký tự trên Production!"
        )

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

    # 3. Validate AI_PROVIDER ngay khi khởi động.
    # Provider không hợp lệ khiến ai_service rơi im lặng vào template dự phòng
    # (người dùng tưởng đang gọi AI thật). Báo lỗi ngay ở khởi động thay vì để
    # lỗi "âm thầm" này tồn tại tới khi ai đó hỏi vì sao kết quả giống mẫu.
    provider = str(getattr(target, "AI_PROVIDER", "") or "").strip().lower()
    supported = [str(p).strip().lower() for p in (getattr(target, "SUPPORTED_AI_PROVIDERS", None) or [])]
    if supported and provider not in supported:
        raise RuntimeError(
            f"FATAL: AI_PROVIDER='{provider}' không hợp lệ. "
            f"Các provider được hỗ trợ: {', '.join(supported)}."
        )

    # 4. Ngoài production: KHÔNG được âm thầm dùng SECRET_KEY mặc định đã công khai.
    # `SECRET_KEY` mặc định được ship trong .env.example, tức là BẤT KỲ AI cũng biết.
    # Trước đây việc dùng nó ở mọi môi trường chỉ sinh một dòng warning, nên một bản
    # demo/staging cài ra internet là token JWT có thể được forge tùy ý.
    if not is_prod:
        for label, value in (("JWT_SECRET_KEY/SECRET_KEY", effective_jwt), ("BYOK_ENCRYPTION_KEY/SECRET_KEY", effective_byok)):
            if _is_insecure(value):
                logger.warning(
                    "[Security] %s đang dùng giá trị mặc định/placeholder yếu. "
                    "Hệ thống vẫn khởi động để phục vụ demo, nhưng token JWT và khoá vault "
                    "có thể bị forge/decrypt nếu giá trị này bị lộ. "
                    "Hãy đặt các biến trong .env (xem .env.example) trước khi triển khai.",
                    label,
                )

    return True


settings = Settings()
validate_security_configuration(settings)

