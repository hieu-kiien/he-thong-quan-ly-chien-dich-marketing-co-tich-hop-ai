import json
import os
from urllib import request


PROMPT_VERSION = "AI-CAM-001-v1"


class MarketingAIService:
    """Provider adapter with a deterministic offline fallback for classroom demos."""

    def __init__(self, api_key=None, provider=None, model=None, base_url=None):
        self.api_key = api_key if api_key is not None else os.getenv("AI_API_KEY", "")
        self.provider = provider or os.getenv("AI_PROVIDER", "mock")
        self.model = model or os.getenv("AI_MODEL", "")
        self.base_url = base_url or os.getenv("AI_BASE_URL", "")

    @staticmethod
    def build_prompt(campaign_brief, channel_name, tone):
        return {
            "version": PROMPT_VERSION,
            "system": (
                "Bạn là trợ lý marketing. Chỉ tạo nội dung nháp dựa trên dữ liệu được cung cấp. "
                "Không bịa cam kết, số liệu hoặc tuyên bố chưa được xác nhận. "
                "Mọi kết quả phải được con người duyệt trước khi sử dụng."
            ),
            "user": (
                f"Chiến dịch: {campaign_brief}\nKênh: {channel_name}\nGiọng điệu: {tone}\n"
                "Hãy đề xuất 5 ý tưởng nội dung, mỗi ý tưởng có hook, nội dung ngắn và CTA."
            ),
        }

    def generate_content_ideas(self, campaign_brief, channel_name, tone="thân thiện", count=5):
        count = max(1, min(int(count), 5))
        prompt = self.build_prompt(campaign_brief, channel_name, tone)
        if self.provider not in {"mock", "fallback"} and self.api_key and self.base_url:
            try:
                result = self._call_openai_compatible(prompt, count)
                if self._valid_result(result, count):
                    return result
            except (OSError, ValueError, json.JSONDecodeError, KeyError):
                pass
        return self._fallback_ideas(campaign_brief, channel_name, tone, count)

    @staticmethod
    def _valid_result(result, count):
        required = {"title", "channel", "hook", "draft", "cta"}
        ideas = result.get("ideas") if isinstance(result, dict) else None
        return bool(
            isinstance(ideas, list)
            and len(ideas) == count
            and all(isinstance(idea, dict) and required.issubset(idea) for idea in ideas)
            and result.get("needs_human_approval") is True
            and result.get("prompt_version") == PROMPT_VERSION
        )

    def _fallback_ideas(self, campaign_brief, channel_name, tone, count):
        angles = [
            "Nêu vấn đề thường gặp của khách hàng",
            "Giải thích lợi ích bằng một tình huống ngắn",
            "Đưa ra checklist thực hành nhanh",
            "Kể câu chuyện trải nghiệm của người dùng",
            "Mời khách hàng tham gia ưu đãi hoặc thử nghiệm",
        ]
        ideas = []
        for index, angle in enumerate(angles[: max(1, min(count, 5))], start=1):
            ideas.append(
                {
                    "title": f"Ý tưởng {index}: {angle}",
                    "channel": channel_name,
                    "hook": f"Bạn đang quan tâm đến {campaign_brief.lower()}?",
                    "draft": f"Nội dung nháp theo giọng {tone}, tập trung vào: {angle.lower()}.",
                    "cta": "Tìm hiểu thêm và liên hệ để được tư vấn.",
                }
            )
        return {
            "provider": "fallback",
            "prompt_version": PROMPT_VERSION,
            "ideas": ideas,
            "needs_human_approval": True,
            "warning": "Đây là nội dung nháp; cần kiểm tra sự thật và duyệt trước khi sử dụng.",
        }

    def _call_openai_compatible(self, prompt, count):
        payload = {
            "model": self.model,
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]},
            ],
        }
        endpoint = self.base_url.rstrip("/") + "/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            endpoint,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
        text = body["choices"][0]["message"]["content"]
        parsed = text if isinstance(text, dict) else json.loads(text)
        ideas = parsed["ideas"]
        if not isinstance(ideas, list) or len(ideas) != count:
            raise ValueError("Provider output must contain exactly the requested number of ideas.")
        if not all(isinstance(idea, dict) for idea in ideas):
            raise ValueError("Provider output ideas must be objects.")
        return {
            "provider": self.provider,
            "prompt_version": PROMPT_VERSION,
            "ideas": ideas,
            "needs_human_approval": True,
            "warning": "Kết quả từ provider phải được kiểm tra và duyệt trước khi sử dụng.",
            "requested_count": count,
        }
