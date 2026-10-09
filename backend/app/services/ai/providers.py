"""Sổ đăng ký nhà cung cấp AI (single source of truth cho toàn hệ thống).

Vì sao có module này
--------------------
Trước đây danh sách provider bị rải ở 5 nơi khác nhau:
`core/config.py` (whitelist + validate lúc khởi động), `schemas/schemas.py`
(regex `pattern` + 2 bản validator gần như giống hệt nhau), `api/v1/settings.py`
(endpoint ping từng provider), `services/ai/ai_service.py` (base_url/headers/payload)
và `frontend/src/pages/Settings.tsx` (UI chọn provider). Thêm provider mới phải
sửa cả 5 chỗ — và thiếu một chỗ là provider "được khai báo nhưng không chạy",
giống đúng lỗi `AI_PROVIDER=opencode` từng âm thầm rơi xuống template dự phòng.

Module này gom phần khai báo về một chỗ. `config.py`, `schemas.py`,
`settings.py`, `ai_service.py` cùng đọc từ đây, nên không thể xảy ra tình
huống backend hỗ trợ provider mà validator chặn (hoặc ngược lại).

Hai giao thức khác nhau
----------------------
* ``PROTOCOL_OPENAI`` — `POST {base_url}/chat/completions` với
  `Authorization: Bearer <key>`. Gemini, OpenRouter, OpenAI, opencode,
  HuggingFace router và Ollama đều nói giao thức này (Anthropic cũng có
  endpoint tương thích nhưng ta KHÔNG dùng vì nó không nằm trong yêu cầu và
  hạn chế khác nhau).
* ``PROTOCOL_ANTHROPIC`` — `POST {base_url}/messages` với header `x-api-key`
  và `anthropic-version`, ``system`` nằm ở top-level chứ không phải một message,
  và `max_tokens` là trường BẮT BUỘC. Gửi payload OpenAI sang Anthropic sẽ
  nhận 400, nên phải có adapter riêng.

Provider không cần API key
--------------------------
Ollama chạy cục bộ (`http://localhost:11434/v1`) và HuggingFace router phục vụ
model công khai không token. Với hai provider này, việc "không tìm thấy khoá" KHÔNG
phải tín hiệu phải chuyển sang Smart Fallback — nếu vậy tính năng demo offline
sẽ không bao giờ chạy được. `requires_api_key=False` làm `resolve_api_key`
trả về tầng `SYSTEM` với khoá rỗng, và `execute_task` gọi thẳng provider.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Giao thức hội thoại
PROTOCOL_OPENAI = "openai"
PROTOCOL_ANTHROPIC = "anthropic"

# Quy tắc kiểm tra tên model theo provider
MODEL_RULE_GEMINI = "gemini"        # phải bắt đầu bằng "gemini"
MODEL_RULE_OPENAI = "openai"        # phải bắt đầu bằng gpt-/o1/o3/text-embedding-/chatgpt-
MODEL_RULE_OPENROUTER = "openrouter"  # phải có dấu "/" (tác giả/tên-mô-hình)
MODEL_RULE_ANTHROPIC = "anthropic"  # phải bắt đầu bằng "claude"
MODEL_RULE_FREE = "free"            # slug tự do, chỉ kiểm tra độ dài tối thiểu


@dataclass(frozen=True)
class AIProviderSpec:
    """Khai báo một nhà cung cấp AI mà hệ thống biết cách gọi."""

    slug: str
    display_name: str
    protocol: str
    default_model: str
    model_rule: str
    base_url: str = ""
    requires_api_key: bool = True
    # Tên biến môi trường chứa khoá hệ thống, xét theo thứ tự.
    env_key_names: Tuple[str, ...] = ()
    # Ghi đè base_url bằng biến môi trường riêng.
    #
    # CỐ Ý DÙNG TÊN CÓ TIỀN TỐ `MARKETFLOW_`, KHÔNG dùng `ANTHROPIC_BASE_URL` /
    # `OLLAMA_BASE_URL` / `HF_BASE_URL` như tài liệu của các hãng gợi ý. Lý do
    # đo được ngay trên máy phát triển: biến `ANTHROPIC_BASE_URL` đã có sẵn
    # trong môi trường hệ thống của nhiều người dùng (đặc biệt là người cấu
    # hình công cụ AI cục bộ) và trỏ tới một endpoint hoàn toàn khác. Nếu đọc
    # tên thường, mọi lời gọi Claude của hệ thống sẽ bị âm thầm chuyển sang
    # endpoint đó mà không có cảnh báo nào — đúng loại lỗi "âm thầm" mà
    # `validate_security_configuration` sinh ra để chặn.
    base_url_env: Optional[str] = None
    # Alias được `validate_provider` chuẩn hoá về slug.
    aliases: Tuple[str, ...] = ()
    # base_url lấy từ settings.AI_BASE_URL thay vì ghim cứng (opencode zen).
    base_url_from_settings: bool = False
    # Header bổ sung gửi kèm cho OpenAI-protocol provider.
    extra_headers: Dict[str, str] = field(default_factory=dict)
    # Path ping dùng cho endpoint "Test API Connection".
    ping_path: str = "/models"
    min_model_len: int = 2

    def resolve_base_url(self, settings_base_url: Optional[str] = None) -> str:
        """Trả về base_url hiệu lực, đã bỏ dấu '/' cuối.

        Thứ tự: biến môi trường riêng (OLLAMA_BASE_URL) > settings.AI_BASE_URL
        (chỉ provider yêu cầu) > giá trị ghim trong registry.
        """
        import os

        if self.base_url_from_settings:
            return (settings_base_url or self.base_url).rstrip("/")
        if self.base_url_env:
            override = os.environ.get(self.base_url_env)
            if override and override.strip():
                return override.strip().rstrip("/")
        return self.base_url.rstrip("/")


#: Danh sách provider. Thứ tự quyết định thứ tự hiển thị trong UI.
PROVIDERS: Tuple[AIProviderSpec, ...] = (
    AIProviderSpec(
        slug="gemini",
        display_name="Google Gemini",
        protocol=PROTOCOL_OPENAI,
        default_model="gemini-2.5-flash",
        model_rule=MODEL_RULE_GEMINI,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        env_key_names=("GEMINI_API_KEY",),
        aliases=("google",),
        extra_headers={"HTTP-Referer": "http://localhost:5173", "X-Title": "MarketFlow AI"},
        ping_path="",  # ping dùng URL riêng, xem _ping_request_for()
    ),
    AIProviderSpec(
        slug="openrouter",
        display_name="OpenRouter",
        protocol=PROTOCOL_OPENAI,
        default_model="meta-llama/llama-3.3-70b-instruct",
        model_rule=MODEL_RULE_OPENROUTER,
        base_url="https://openrouter.ai/api/v1",
        env_key_names=("OPENROUTER_API_KEY",),
        extra_headers={"HTTP-Referer": "https://marketflow.ai", "X-Title": "MarketFlow AI"},
    ),
    AIProviderSpec(
        slug="openai",
        display_name="OpenAI",
        protocol=PROTOCOL_OPENAI,
        default_model="gpt-4o",
        model_rule=MODEL_RULE_OPENAI,
        base_url="https://api.openai.com/v1",
        env_key_names=("OPENAI_API_KEY",),
        aliases=("gpt",),
    ),
    AIProviderSpec(
        slug="anthropic",
        display_name="Anthropic (Claude)",
        protocol=PROTOCOL_ANTHROPIC,
        default_model="claude-3-5-haiku-latest",
        model_rule=MODEL_RULE_ANTHROPIC,
        base_url="https://api.anthropic.com/v1",
        env_key_names=("ANTHROPIC_API_KEY",),
        base_url_env="MARKETFLOW_ANTHROPIC_BASE_URL",
        aliases=("claude",),
    ),
    AIProviderSpec(
        slug="huggingface",
        display_name="Hugging Face",
        protocol=PROTOCOL_OPENAI,
        default_model="meta-llama/Llama-3.1-8B-Instruct",
        model_rule=MODEL_RULE_FREE,
        # Router OpenAI-compatible chính thức của HuggingFace. Có thể trỏ sang
        # endpoint suy luận tự phục vụ qua HF_BASE_URL.
        base_url="https://router.huggingface.co/v1",
        requires_api_key=False,
        env_key_names=("HUGGINGFACE_API_KEY", "HF_TOKEN", "HF_API_TOKEN"),
        base_url_env="MARKETFLOW_HF_BASE_URL",
        aliases=("hf", "hugging_face", "huggingface-inference"),
    ),
    AIProviderSpec(
        slug="ollama",
        display_name="Ollama (chạy cục bộ)",
        protocol=PROTOCOL_OPENAI,
        default_model="llama3.2",
        model_rule=MODEL_RULE_FREE,
        # Ollama mặc định nghe ở cổng 11434 và nói đúng giao thức OpenAI.
        base_url="http://localhost:11434/v1",
        requires_api_key=False,
        env_key_names=("OLLAMA_API_KEY",),  # thường rỗng, Ollama không cần khoá
        base_url_env="MARKETFLOW_OLLAMA_BASE_URL",
        aliases=("local", "llama"),
    ),
    AIProviderSpec(
        slug="opencode",
        display_name="OpenCode Zen",
        protocol=PROTOCOL_OPENAI,
        default_model="space-bunny-free",
        model_rule=MODEL_RULE_FREE,
        # Endpoint OpenAI-compatible của opencode zen, lấy từ cấu hình để có
        # thể trỏ sang endpoint opencode khác.
        base_url_from_settings=True,
        # OpenCode Zen t?n mi?n phí `space-bunny-free` ch?y KHÔNG c?n khoá.
        # Khai báo sai là bắt buộc key s? khi?n `ai_service` r? xu?ng fallback gia
        # ngay c? khi endpoint th?t s? g?i du?c. Key (n?u có) v?n dùng du?c.
        requires_api_key=False,
        env_key_names=("OPENCODE_API_KEY",),
        aliases=("oc", "zen"),
        extra_headers={"HTTP-Referer": "http://localhost:5173", "X-Title": "MarketFlow AI"},
    ),
)

_BY_SLUG: Dict[str, AIProviderSpec] = {p.slug: p for p in PROVIDERS}

#: Danh sách slug hợp lệ (thứ tự khai báo). `SUPPORTED_AI_PROVIDERS` trong
#: `core/config.py` lấy từ đây.
SUPPORTED_PROVIDER_SLUGS: List[str] = [p.slug for p in PROVIDERS]

#: Regex dùng cho `Field(pattern=...)` của Pydantic, sinh từ registry để không
#: bao giờ lệch với whitelist.
PROVIDER_PATTERN = r"^(" + "|".join(SUPPORTED_PROVIDER_SLUGS) + r")$"


def get_provider(slug: Optional[str]) -> Optional[AIProviderSpec]:
    """Trả về spec của provider, hoặc None nếu slug lạ/None."""
    if not slug:
        return None
    return _BY_SLUG.get(str(slug).lower().strip())


def require_provider(slug: Optional[str]) -> AIProviderSpec:
    """Giống `get_provider` nhưng ném lỗi nếu không tìm thấy."""
    spec = get_provider(slug)
    if spec is None:
        raise KeyError(slug)
    return spec


def normalize_provider_slug(value: Optional[str]) -> str:
    """Chuẩn hoá tên provider người dùng gõ về slug trong registry.

    Ném `ValueError` với thông báo tiếng Việt khi không khớp — validator của
    Pydantic bắt và trả về 422 thân thiện thay vì lỗi 500.
    """
    if not isinstance(value, str):
        supported = ", ".join(f"'{s}'" for s in SUPPORTED_PROVIDER_SLUGS)
        raise ValueError(
            f"Nhà cung cấp '{value}' không được hỗ trợ. Chỉ hỗ trợ {supported}."
        )
    candidate = value.lower().strip()
    if candidate in _BY_SLUG:
        return candidate
    for spec in PROVIDERS:
        if candidate in spec.aliases:
            return spec.slug
    supported = ", ".join(f"'{s}'" for s in SUPPORTED_PROVIDER_SLUGS)
    raise ValueError(
        f"Nhà cung cấp '{value}' không được hỗ trợ. Chỉ hỗ trợ {supported}."
    )


def default_model_for(slug: Optional[str]) -> str:
    """Model mặc định của provider; rơi về Gemini khi slug lạ (giữ hành vi cũ)."""
    spec = get_provider(slug)
    return spec.default_model if spec else _BY_SLUG["gemini"].default_model


def display_name_for(slug: Optional[str]) -> str:
    spec = get_provider(slug)
    return spec.display_name if spec else str(slug or "")


def validate_model_for(slug: str, model: Optional[str]) -> str:
    """Chuẩn hoá + kiểm tra tên model theo quy tắc của provider.

    Trả về chuẩn hoá (lowercase cho các provider dùng slug lowercase). Ném
    `ValueError` khi model không thuộc hệ sinh thái của provider.
    """
    spec = require_provider(slug)
    cleaned = (model or "").strip()
    if not cleaned:
        return spec.default_model

    lowered = cleaned.lower()
    rule = spec.model_rule

    if rule == MODEL_RULE_GEMINI:
        if not lowered.startswith("gemini"):
            raise ValueError(f"Mô hình '{model}' không thuộc hệ sinh thái Google Gemini.")
        return lowered
    if rule == MODEL_RULE_OPENAI:
        valid_prefixes = ("gpt-", "o1", "o3", "text-embedding-", "chatgpt-")
        if not any(lowered.startswith(p) for p in valid_prefixes):
            raise ValueError(f"Mô hình '{model}' không thuộc hệ sinh thái OpenAI.")
        return lowered
    if rule == MODEL_RULE_OPENROUTER:
        if "/" not in cleaned or len(cleaned) < 3:
            raise ValueError(
                f"Mô hình '{model}' không hợp lệ cho OpenRouter (cần định dạng tác giả/tên-mô-hình, "
                "ví dụ 'meta-llama/llama-3.3-70b-instruct')."
            )
        return cleaned
    if rule == MODEL_RULE_ANTHROPIC:
        if not lowered.startswith("claude"):
            raise ValueError(f"Mô hình '{model}' không thuộc hệ sinh thái Anthropic Claude.")
        return lowered
    # MODEL_RULE_FREE: slug tự do, chỉ kiểm tra độ dài tối thiểu.
    if len(cleaned) < spec.min_model_len:
        raise ValueError(f"Mô hình '{model}' không hợp lệ cho {spec.display_name}.")
    return cleaned