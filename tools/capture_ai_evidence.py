"""Capture a deterministic, redacted AI fallback response for the submission appendix."""

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "marketing_management"))
from campaigns.ai_service import MarketingAIService  # noqa: E402


output = MarketingAIService(provider="fallback", api_key="").generate_content_ideas(
    campaign_brief="Ra mắt sản phẩm A cho sinh viên và người đi làm trẻ tại Thái Nguyên",
    channel_name="Facebook",
    tone="thân thiện, rõ ràng",
    count=5,
)

target = ROOT / "evidence" / "ai" / "AI-CAM-001-v1-response.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Wrote evidence/ai/AI-CAM-001-v1-response.json")
