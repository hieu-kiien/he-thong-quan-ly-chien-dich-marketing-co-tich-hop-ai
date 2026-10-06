"""Adapter gọi Anthropic Messages API.

Vì sao cần adapter riêng
-----------------------
Anthropic KHÔNG nói giao thức OpenAI. Ba khác biệt làm payload của
`/chat/completions` bị từ chối (HTTP 400):

1. **Endpoint**: `/v1/messages`, không phải `/v1/chat/completions`.
2. **Xác thực**: header `x-api-key` + header `anthropic-version`
   (bắt buộc), không phải `Authorization: Bearer`.
3. **Hình dạng payload**: `system` là trường top-level, không phải message có
   `role: "system"`; `max_tokens` là **bắt buộc** (OpenAI thì không);
   phản hồi trả `content: [{type: "text", text: ...}]`, không phải
   `choices[0].message.content`.

Module này chỉ lo phần "dựng payload + đọc phản hồi". Phần retry, timeout,
sanitize lỗi và fallback vẫn nằm trong `AIService._call_provider_with_retry`
để mọi provider có cùng một hành vi lỗi.

Nguyên tắc bất di bất dịch của adapter: không log, không trả về, không nhúng
vào message lỗi bất kỳ giá trị `api_key` nào. Lỗi đi ra là thông báo của
Anthropic đã đi qua `_sanitize_ai_error` ở tầng trên.
"""

from typing import Any, Dict, List, Optional

#: Phiên bản API bắt buộc theo tài liệu Anthropic Messages API.
ANTHROPIC_VERSION = "2023-06-01"

#: Trần token đầu ra cho một lần gọi. Bộ prompt của hệ thống yêu cầu JSON có
#: cấu trúc (kịch bản TikTok 4 cảnh + A/B email), nên trần thấp sẽ cắt mất
#: JSON và khiến bước validate schema rơi vào Smart Fallback. Giá trị này lớn
#: hơn nhiều mức tối đa thực tế của các prompt trong `prompts/prompts.json`.
ANTHROPIC_MAX_TOKENS = 8192


def build_messages_payload(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = ANTHROPIC_MAX_TOKENS,
) -> Dict[str, Any]:
    """Dựng body cho `POST /v1/messages`.

    `system_prompt` rỗng vẫn được gửi (chuỗi rỗng) để không phải rẽ nhánh payload
    — hai payload khác nhau chính là nguồn bug khó tái hiện nhất trong adapter.
    """
    return {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }


def build_headers(api_key: Optional[str]) -> Dict[str, str]:
    """Header bắt buộc của Anthropic.

    `Authorization` vẫn được gửi kèm để phòng trường hợp một proxy OpenAI-
    compatible nằm trước Anthropic đòi header đó; Anthropic bỏ qua thành phần
    không nhận biết nên việc gửi thêm không ảnh hưởng request thật. Header
    `x-api-key` KHÔNG được gửi khi không có khoá — một header rỗng khiến
    Anthropic trả 401 với thông báo gây hiểu nhầm là sai khoá.
    """
    headers = {
        "content-type": "application/json",
        "anthropic-version": ANTHROPIC_VERSION,
    }
    if api_key and api_key.strip():
        headers["x-api-key"] = api_key.strip()
    return headers


def extract_text(payload: Any) -> str:
    """Rút phần text từ phản hồi Messages API.

    Ném `ValueError` với thông báo có kiểm soát khi cấu trúc không như mong đợi,
    để tầng trên đánh dấu `SCHEMA_ERROR` thay vì `IndexError`/`KeyError` thô.
    """
    if not isinstance(payload, dict):
        raise ValueError("Phản hồi Anthropic không phải object JSON.")

    blocks = payload.get("content")
    if not isinstance(blocks, list) or not blocks:
        # `stop_reason: "max_tokens"` với content rỗng là nguyên nhân phổ biến
        # nhất. Nêu rõ để log dễ đọc thay vì "index out of range".
        stop_reason = payload.get("stop_reason")
        if stop_reason == "max_tokens":
            raise ValueError(
                "Anthropic dừng sinh vì chạm trần max_tokens; tăng ANTHROPIC_MAX_TOKENS "
                "hoặc dùng prompt ngắn hơn."
            )
        raise ValueError("Phản hồi Anthropic không có mảng `content`.")

    texts: List[str] = []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
            texts.append(block["text"])

    if not texts:
        raise ValueError("Phản hồi Anthropic không chứa khối text nào.")
    return "\n".join(texts)