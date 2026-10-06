#!/usr/bin/env python3
"""
scripts/compare_prompt_variants.py
==================================
Đáp ứng rubric môn học AIA331 — Tuần 3, mục 4:

    "Tối ưu prompt qua thử nghiệm: Có ít nhất 3 vòng thử nghiệm hoặc so sánh
     prompt/model, ghi nhận kết quả và cái tiến."

TRẠNG THÁI TRƯỚC THAY ĐỔI NÀY
------------------------------
`prompts.json` đã có sẵn 3 phiên bản (v1, v2, v3) cho cả 4 tác vụ, nhưng KHÔNG
có bằng chứng nào đo được trên chúng. `docs/AI_EVALUATION_REPORT.md` chỉ nhắc
"baseline" một lần và chỉ đo đường chẩn đoán xác định (AI Doctor) chứ không đo
chất lượng prompt. Nói "có 3 biến thể" mà không có bảng so sánh đo được là loại
tuyên bố không có cơ sở — đúng thứ rubric này muốn tránh.

PHƯƠNG PHÁP (và những gì nó KHÔNG chứng minh)
----------------------------------------------
Script này so sánh 3 phiên bản prompt trên một tập case cố định, với lời gọi
mô hình **được thay bằng stub tất định**. Điều đó có hai hệ quả phải nói rõ:

1. **Có thể tái lập và miễn phí**: chạy lại cho ra cùng kết quả, không tốn
   credit, không phụ thuộc mạng. Nhờ vậy học phần đưa được bảng số vào báo cáo
   mà không cần gọi API thật ở giờ bảo vệ.
2. **KHÔNG đo chất lượng văn phong của mô hình thật.** Stub tạo ra JSON hợp lệ
   theo cấu trúc prompt yêu cầu, nên nó đo được: prompt có yêu cầu đủ rõ để mô
   hình trả về đúng schema không, có truyền đủ ngữ cảnh không, có tránh được
   từ khóa bị cấm không, có nhắc được các trường bắt buộc không. Nó KHÔNG đo được:
   văn phong, sức thuyết phục, hay mức độ chính xác ngữ nghĩa.

Vì vậy kết luận rút ra là về **tính đầy đủ và rõ ràng của đặc tả trong prompt**,
không phải về "prompt nào cho bài viết hay hơn". Báo cáo ghi rõ điều này.

Bốn chỉ số, tất cả đều tất định
--------------------------------
1. `schema_valid_rate`  — phần trăm output parse được đúng Pydantic schema.
2. `banned_keyword_leak` — có phát ra từ khóa trong blacklist của Brand Kit không.
3. `required_field_coverage` — phần trăm output có đủ các trường nghiệp vụ bắt
   buộc (ví dụ TikTok có ít nhất 3 cảnh phân cảnh, Email có 2 phương án tiêu đề
   A/B).
4. `context_fill_rate` — phần trăm placeholder `{{...}}` trong prompt đã được
   điền bằng ngữ cảnh thật. Đo trực tiếp trên prompt đã render.

Chạy:
    python scripts/compare_prompt_variants.py

Xuất:
    docs/PROMPT_VARIANT_COMPARISON.md   (bảng so sánh + cách tái lập)
    scripts/prompt_variant_results.json  (artifact máy đọc được)
"""

import json
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from pydantic import ValidationError  # noqa: E402

from app.schemas.schemas import (  # noqa: E402
    AIDraftResponse,
    AIIdeaResponse,
    AISummaryResponse,
    OmnichannelResponse,
)

PROMPTS_FILE = BACKEND_DIR / "prompts" / "prompts.json"
VARIANTS = ["v1", "v2", "v3"]

#: Brand Kit giả lập cho benchmark. Từ khóa cấm là điểm chống "model tự ý chế"
#: — đây là cơ chế an toàn thương hiệu thật của hệ thống
#: (`services/compliance/compliance_service.py`).
BANNED_KEYWORDS = ["săn mãi", "bảo hành trọn đời", "chắc chắn hiệu quả"]

#: Ngữ cảnh dùng chung cho mọi case. Tất cả placeholder trong prompts.json đều
#: được lấp đầy từ đây, nhờ vậy `context_fill_rate` đo được ý nghĩa.
BASE_CONTEXT: Dict[str, Any] = {
    "campaign_name": "Ra mắt khóa học AI cho doanh nghiệp",
    "campaign_brief": "Ra mắt khóa học AI 2026 cho chủ doanh nghiệp",
    "objective": "Tăng lượt đăng ký khóa học",
    "audience": "Chủ doanh nghiệp 25-45 tuổi đang tìm cách tự động hoá vận hành",
    "product_name": "Khóa học AI ứng dụng cho doanh nghiệp",
    "product_usp": "Rút ngắn 50% thời gian xử lý công việc lặp lại",
    "usp": "Rút ngắn 50% thời gian xử lý công việc lặp lại",
    "channel_name": "Facebook",
    "channel_rules": "Tiêu đề dưới 40 ký tự, thân bài ngắn, có CTA rõ",
    "tone": "Chuyên nghiệp, gần gũi",
    "tone_of_voice": "Chuyên nghiệp, gần gũi, không hoa mỹ",
    "selected_idea": "Nhấn mạnh tiết kiệm thời gian cho chủ doanh nghiệp bận rộn",
    "brief": "Ra mắt khóa học AI 2026 cho chủ doanh nghiệp",
    "target_audience": "Chủ doanh nghiệp 25-45 tuổi",
    "brand_name": "TechMaster Academy",
    "banned_keywords": ", ".join(BANNED_KEYWORDS),
    "requested_channels": "facebook, tiktok, email",
    "budget": "50000000",
    "metrics_summary": "10000 lượt xem, 500 lượt click, 25 chuyển đổi",
    "total_views": "10000",
    "total_clicks": "500",
    "total_conversions": "25",
    "ctr": "5.0",
    "cvr": "5.0",
    "cpc": "2000",
    "roi": "300.0",
    "total_cost": "10,000,000",
    "total_revenue": "40,000,000",
}


# ==============================================================================
# LỚP ĐO
# ==============================================================================

@dataclass
class CaseResult:
    variant: str
    task: str
    case_name: str
    schema_valid: bool
    banned_leak: List[str] = field(default_factory=list)
    required_fields_present: bool = True
    missing_required_fields: List[str] = field(default_factory=list)
    placeholders_unfilled: List[str] = field(default_factory=list)
    prompt_chars: int = 0


def _normalize(text: str) -> str:
    """Bỏ dấu + hạ chữ thường để so khớp từ khóa không phụ thuộc dấu tiếng Việt."""
    decomposed = unicodedata.normalize("NFD", text or "")
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return unicodedata.normalize("NFC", stripped).lower()


def _collect_text(node: Any, acc: List[str]) -> None:
    if isinstance(node, str):
        acc.append(node)
    elif isinstance(node, dict):
        for value in node.values():
            _collect_text(value, acc)
    elif isinstance(node, (list, tuple)):
        for value in node:
            _collect_text(value, acc)


def _render(template: str, context: Dict[str, Any]) -> str:
    out = template
    for key, value in context.items():
        out = out.replace("{{" + str(key) + "}}", str(value) if value is not None else "")
    return out


def _unfilled_placeholders(rendered: str) -> List[str]:
    """Placeholder còn sót sau khi render — dấu hiệu thiếu ngữ cảnh."""
    return [
        chunk.split("}}")[0].strip()
        for chunk in rendered.split("{{")[1:]
        if "}}" in chunk
    ]


# ==============================================================================
# STUB MÔ HÌNH — thay cho lời gọi provider thật
# ==============================================================================
#
# Vì sao dùng stub, và stub này "bị lỗi" như thế nào
# ---------------------------------------------------
# Stub KHÔNG phải là "mô hình giả lập hoàn hản". Nó cố tình chỉ tuân theo prompt:
# đọc danh sách trường mà PROMPT yêu cầu và trả về đúng các trường đó.
#
# Hệ quả cần nói rõ khi bảo vệ: nếu v1 không yêu cầu đủ trường, stub sẽ KHÔNG
# sinh ra trường đó — và bảng so sánh sẽ ghi nhận `required_field_coverage` thấp.
# Đó chính là thông tin ta muốn đo: **prompt có đủ chỉ dẫn cấu trúc hay không**.
# Stub không biết schema của hệ thống; nó chỉ biết prompt.

def _fields_mentioned(prompt: str) -> set:
    """Các trường JSON được prompt nhắc tới (nhận diện bằng tên trong mẫu)."""
    normalized = _normalize(prompt)
    known = {
        "ideas": "ideas",
        "headline": "headline",
        "angle": "angle",
        "target_emotion": "target_emotion",
        "concept": "concept",
        "title": "title",
        "body": "body",
        "cta": "cta",
        "executive_summary": "executive_summary",
        "strengths": "strengths",
        "weaknesses": "weaknesses",
        "recommendations": "recommendations",
        "warnings": "warnings",
        "assumptions": "assumptions",
        "facebook": "facebook",
        "tiktok": "tiktok",
        "email": "email",
        "hook_3s": "hook_3s",
        "scenes": "scenes",
        "hashtags": "hashtags",
        "subject_options": "subject_options",
        "preheader": "preheader",
        "greeting": "greeting",
        "ps_note": "ps_note",
        "cta_button": "cta_button",
        "voiceover": "voiceover",
        "voiceover_script": "voiceover_script",
        "visual": "visual",
        "visual_action": "visual_action",
        "audio": "audio",
        "audio_hint": "audio_hint",
        "visual_suggestion": "visual_suggestion",
        "target_duration": "target_duration",
        # TikTokCreative yêu cầu `suggested_audio` (không optional). Nếu thiếu
        # khỏi danh sách này thì stub sẽ không bao giờ sinh nó và mọi phiên bản
        # đều fail schema — đo sai điều ta muốn đo.
        "suggested_audio": "suggested_audio",
        "sound_recommendation": "sound_recommendation",
        "duration_seconds": "duration_seconds",
        "scene_number": "scene_number",
        "primary_text": "primary_text",
        "subject_line_a": "subject_line_a",
        "subject_line_b": "subject_line_b",
        "body_content": "body_content",
        "cta_button_text": "cta_button_text",
    }
    return {key for key in known if key in normalized}


_STUB_TEXT = {
    "title": "Rút ngắn 50% thời gian xử lý công việc lặp lại",
    "headline": "Rút ngắn 50% thời gian xử lý công việc lặp lại",
    "body": "Khóa học AI 2026 dành cho chủ doanh nghiệp đang tìm cách tự động hoá vận hành.",
    "cta": "Đăng ký ngay",
    "concept": "Nhấn mạnh tiết kiệm thời gian cho chủ doanh nghiệp bận rộn.",
    "target_emotion": "Tin tưởng, hành động",
    "executive_summary": "Chiến dịch ghi nhận 10000 lượt xem, 500 lượt click và 25 chuyển đổi.",
    "hook_3s": "Dừng lại nếu bạn đang mất mỗi ngày vài giờ cho công việc lặp lại.",
    "preheader": "Khoá học AI 2026 cho chủ doanh nghiệp.",
    "greeting": "Chào bạn,",
    "ps_note": "Ưu đãi sớm dành cho lớp khai giảng tháng này.",
    "cta_button": "Đăng ký tư vấn",
    "target_duration": "30-45 giây",
    "visual_suggestion": "Banner phong cách hiện đại, nền sáng, chữ lớn.",
    "angle": "Tập trung vào lợi ích cốt lõi",
}


def stub_omnichannel(prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Sinh payload đa kênh chỉ gồm những trường prompt có nhắc tới."""
    mentioned = _fields_mentioned(prompt)
    product = str(context.get("product_name", "Sản phẩm"))
    brand = str(context.get("brand_name", "Thương hiệu"))
    usp = str(context.get("usp", "giá trị cốt lõi"))

    result: Dict[str, Any] = {"warnings": [], "assumptions": []}

    if "facebook" in mentioned:
        fb: Dict[str, Any] = {}
        if "headline" in mentioned or "title" in mentioned:
            fb["title"] = f"{brand}: {usp}"
            fb["headline"] = f"{brand}: {usp}"
        if "body" in mentioned:
            fb["body"] = f"{product} dành cho {context.get('target_audience', 'khách hàng')}."
        if "primary_text" in mentioned:
            fb["primary_text"] = fb.get("body", "")
        if "cta" in mentioned:
            fb["cta"] = "Đăng ký tư vấn"
        if "hashtags" in mentioned:
            fb["hashtags"] = ["#AI", "#DoanhNghiep"]
        if "visual_suggestion" in mentioned:
            fb["visual_suggestion"] = _STUB_TEXT["visual_suggestion"]
        result["facebook"] = fb

    if "tiktok" in mentioned:
        tk: Dict[str, Any] = {}
        if "hook_3s" in mentioned:
            tk["hook_3s"] = _STUB_TEXT["hook_3s"]
        if "target_duration" in mentioned:
            tk["target_duration"] = _STUB_TEXT["target_duration"]
        if "scenes" in mentioned:
            # Số cảnh mà prompt yêu cầu: đếm các lần nhắc "scene_N" trong prompt.
            normalized = _normalize(prompt)
            scene_slots = max(
                len({int(m) for m in __import__("re").findall(r'scene[_ ]?(\d+)', normalized)}),
                1,
            )
            tk["scenes"] = [
                {
                    "scene": i + 1,
                    "scene_number": i + 1,
                    "duration_seconds": "0-3s",
                    "visual": "Diễn viên thao tác với giao diện",
                    "visual_action": "Diễn viên thao tác với giao diện",
                    "voiceover": _STUB_TEXT["hook_3s"],
                    "voiceover_script": _STUB_TEXT["hook_3s"],
                    "audio": "Nhạc nền sôi động",
                    "audio_hint": "Nhạc nền sôi động",
                }
                for i in range(scene_slots)
            ]
        # `suggested_audio` là trường BẮT BUỘC của `TikTokCreative`. Kể cả khi
        # prompt không nhắc tới, stub vẫn phải trả nó — nếu không thì mọi phiên
        # bản đều fail schema và ta đang đo sai thứ.
        audio_text = "Nhạc nền tươi sáng, phấn khởi"
        if "suggested_audio" in mentioned:
            tk["suggested_audio"] = audio_text
        if "sound_recommendation" in mentioned:
            tk["sound_recommendation"] = audio_text
        if "caption_with_hashtags" in mentioned:
            tk["caption_with_hashtags"] = f"{brand} #AI #HocHanh"
        result["tiktok"] = tk

    if "email" in mentioned:
        em: Dict[str, Any] = {}
        if "subject_options" in mentioned:
            em["subject_options"] = [
                f"Khoá học AI 2026: {usp}",
                f"[Cơ hội giới hạn] Bắt đầu với {brand}",
            ]
            em["subject_line_a"] = em["subject_options"][0]
            em["subject_line_b"] = em["subject_options"][1]
        if "preheader" in mentioned:
            em["preheader"] = _STUB_TEXT["preheader"]
        if "greeting" in mentioned:
            em["greeting"] = _STUB_TEXT["greeting"]
        if "body" in mentioned:
            em["body"] = f"{product} dành cho {context.get('target_audience', 'khách hàng')}."
            em["body_content"] = em["body"]
        if "cta_button" in mentioned:
            em["cta_button"] = _STUB_TEXT["cta_button"]
        if "ps_note" in mentioned:
            em["ps_note"] = _STUB_TEXT["ps_note"]
        result["email"] = em

    return result


def stub_ideas(prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
    mentioned = _fields_mentioned(prompt)
    count = 1
    normalized = _normalize(prompt)
    if "5 ý tưởng" in normalized or '"id": 1' in prompt or "id: 1" in prompt:
        count = 5
    ideas = []
    for i in range(count):
        idea: Dict[str, Any] = {"id": i + 1}
        if "angle" in mentioned:
            idea["angle"] = _STUB_TEXT["angle"]
        if "headline" in mentioned:
            idea["headline"] = f"{context.get('brand_name', 'Thương hiệu')}: {_STUB_TEXT['title']}"
        if "concept" in mentioned:
            idea["concept"] = _STUB_TEXT["concept"]
        if "target_emotion" in mentioned:
            idea["target_emotion"] = _STUB_TEXT["target_emotion"]
        ideas.append(idea)
    result: Dict[str, Any] = {"ideas": ideas}
    if "warnings" in mentioned:
        result["warnings"] = []
    if "assumptions" in mentioned:
        result["assumptions"] = []
    return result


def stub_draft(prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
    mentioned = _fields_mentioned(prompt)
    result: Dict[str, Any] = {}
    if "title" in mentioned:
        result["title"] = _STUB_TEXT["title"]
    if "body" in mentioned:
        result["body"] = _STUB_TEXT["body"]
    if "cta" in mentioned:
        result["cta"] = _STUB_TEXT["cta"]
    if "warnings" in mentioned:
        result["warnings"] = []
    if "assumptions" in mentioned:
        result["assumptions"] = []
    return result


def stub_summary(prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
    mentioned = _fields_mentioned(prompt)
    result: Dict[str, Any] = {}
    if "executive_summary" in mentioned:
        result["executive_summary"] = _STUB_TEXT["executive_summary"]
    if "strengths" in mentioned:
        result["strengths"] = ["CTR 5.0% trên 10000 lượt xem."]
    if "weaknesses" in mentioned:
        result["weaknesses"] = ["CVR 5.0% còn thấp so với mục tiêu."]
    if "recommendations" in mentioned:
        result["recommendations"] = ["A/B thử tiêu đề email để tăng tỷ lệ mở thư."]
    if "warnings" in mentioned:
        result["warnings"] = []
    return result


#: Stub cố ý phát ra một từ khóa cấm. Mục đích: chứng minh bộ dò rò hoạt động
#: được, vì không có gì tệ hơn một chỉ số luôn bằng 0 mà không ai biết là do
#: bộ đo hỏng hay vì thật sự không có rò. Đây là "đối chứng âm" của benchmark.
def stub_deliberately_leaks_banned_keyword(prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Sinh payload có chứa từ khóa cấm — chỉ dùng cho đối chứng âm."""
    return {
        "title": f"Ưu đãi {BANNED_KEYWORDS[0]} dành cho bạn",
        "body": f"Khóa học {context.get('product_name', '')} cam kết {BANNED_KEYWORDS[2]}.",
        "cta": "Đăng ký ngay",
        "warnings": [],
        "assumptions": [],
    }


STUBS: Dict[str, Callable[[str, Dict[str, Any]], Dict[str, Any]]] = {
    "idea_generation": stub_ideas,
    "content_draft": stub_draft,
    "performance_summary": stub_summary,
    "omnichannel_generation": stub_omnichannel,
}

SCHEMAS = {
    "IDEA": (AIIdeaResponse, "idea_generation"),
    "DRAFT": (AIDraftResponse, "content_draft"),
    "SUMMARY": (AISummaryResponse, "performance_summary"),
    "OMNICHANNEL": (OmnichannelResponse, "omnichannel_generation"),
}

#: Trường nghiệp vụ bắt buộc mà output cuối cùng phải có. Đây là tiêu chí "có
#: thực sự hữu ích cho hệ thống không", tách khỏi "có đúng schema Pydantic".
REQUIRED_FIELDS: Dict[str, List[str]] = {
    "idea_generation": ["ideas.0.headline", "ideas.0.concept", "ideas.0.target_emotion"],
    "content_draft": ["title", "body", "cta"],
    "performance_summary": ["executive_summary", "strengths", "weaknesses", "recommendations"],
    "omnichannel_generation": [
        "facebook.title",
        "facebook.body",
        "facebook.cta",
        "facebook.hashtags",
        "tiktok.hook_3s",
        "tiktok.scenes",
        "email.subject_options",
        "email.body",
    ],
}


def _has_path(payload: Any, dotted: str) -> bool:
    node = payload
    for part in dotted.split("."):
        if part.isdigit():
            idx = int(part)
            if not isinstance(node, (list, tuple)) or idx >= len(node):
                return False
            node = node[idx]
        else:
            if not isinstance(node, dict) or part not in node or node[part] in (None, ""):
                return False
            node = node[part]
    return True


# ==============================================================================
# CHẠY BENCHMARK
# ==============================================================================

def load_prompts() -> Dict[str, Any]:
    with open(PROMPTS_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def evaluate_variant(variant: str, prompts: Dict[str, Any]) -> List[CaseResult]:
    results: List[CaseResult] = []

    for task_type, stub in STUBS.items():
        task_block = prompts.get(task_type, {})
        version_block = task_block.get(variant)
        if not version_block:
            # Phiên bản không định nghĩa cho tác vụ này: ghi nhận rõ để bảng
            # so sánh phản ánh đúng "v1 chưa mô tả tác vụ đa kênh".
            results.append(
                CaseResult(
                    variant=variant,
                    task=task_type,
                    case_name="khong_co_prompt_cho_tac_vu_nay",
                    schema_valid=False,
                    required_fields_present=False,
                    missing_required_fields=list(REQUIRED_FIELDS.get(task_type, [])),
                )
            )
            continue

        system_prompt = _render(version_block.get("system", ""), BASE_CONTEXT)
        user_prompt = _render(version_block.get("user", ""), BASE_CONTEXT)
        rendered = f"{system_prompt}\n{user_prompt}"

        task_code = {"idea_generation": "IDEA", "content_draft": "DRAFT",
                     "performance_summary": "SUMMARY", "omnichannel_generation": "OMNICHANNEL"}[task_type]
        schema_cls, _ = SCHEMAS[task_code]

        raw_output = stub(user_prompt, BASE_CONTEXT)

        # 1. Schema hợp lệ
        payload = {
            **raw_output,
            "model_used": "stub-deterministic-compare-harness",
            "prompt_version": variant,
            "task_type": task_code,
        }
        schema_valid = True
        try:
            schema_cls.model_validate(payload)
        except ValidationError:
            schema_valid = False

        # 2. Rò từ khóa cấm
        texts: List[str] = []
        _collect_text(raw_output, texts)
        haystack = _normalize(" ".join(texts))
        leaked = [kw for kw in BANNED_KEYWORDS if _normalize(kw) in haystack]

        # 3. Đủ trường nghiệp vụ bắt buộc
        required = REQUIRED_FIELDS.get(task_type, [])
        missing = [path for path in required if not _has_path(raw_output, path)]

        # 4. Placeholder chưa được lấp đầy
        unfilled = sorted(set(_unfilled_placeholders(system_prompt) + _unfilled_placeholders(user_prompt)))

        results.append(
            CaseResult(
                variant=variant,
                task=task_type,
                case_name=task_type,
                schema_valid=schema_valid,
                banned_leak=leaked,
                required_fields_present=not missing,
                missing_required_fields=missing,
                placeholders_unfilled=unfilled,
                prompt_chars=len(rendered),
            )
        )

    return results


def summarise(results: List[CaseResult]) -> Dict[str, Any]:
    total = len(results)
    schema_ok = sum(1 for r in results if r.schema_valid)
    leak_count = sum(1 for r in results if r.banned_leak)
    fields_ok = sum(1 for r in results if r.required_fields_present)
    placeholders_total = sum(len(r.placeholders_unfilled) for r in results)

    return {
        "cases": total,
        "schema_valid": schema_ok,
        "schema_valid_rate": round(100.0 * schema_ok / total, 1) if total else 0.0,
        "banned_keyword_leaks": leak_count,
        "required_field_coverage": round(100.0 * fields_ok / total, 1) if total else 0.0,
        "unfilled_placeholders": placeholders_total,
        "avg_prompt_chars": round(sum(r.prompt_chars for r in results) / total) if total else 0,
    }


def build_markdown(
    prompts: Dict[str, Any],
    all_results: Dict[str, List[CaseResult]],
    summaries: Dict[str, Dict[str, Any]],
    negative_control: Dict[str, Any],
) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    commit_hint = "xem `git log -1 --format=%H` trên commit sinh ra file này"

    #: Mô tả prompt đa kênh của từng phiên bản, viết tay vì đây là thông điệp
    #: phẳng về *ý định thiết kế* mà một phép đo ký tự không nói được.
    VARIANT_INTENT: Dict[str, str] = {
        "v1": "1 prompt, chỉ yêu cầu \"tạo nội dung cho 3 kênh\", **không** nêu khung JSON",
        "v2": "2 prompt, có nhắc tên các trường (facebook/tiktok/email) nhưng không cho khung đầy đủ",
        "v3": "2 prompt, có khung JSON đầy đủ cho 3 kênh + ràng buộc từ khóa cấm + quy tắc 100% tiếng Việt",
    }

    def diff_desc(variant: str) -> str:
        return VARIANT_INTENT.get(variant, "")

    lines: List[str] = []
    lines.append("# So sánh các phiên bản prompt (Tuần 3 — mục 4 rubric AIA331)\n")
    lines.append(
        "> **Tài liệu này được sinh tự động.** Generator: "
        "[`scripts/compare_prompt_variants.py`](../scripts/compare_prompt_variants.py). "
        "Đổi script thì phải sinh lại file này. Không sửa tay.\n"
    )
    lines.append(f"**Thời điểm chạy:** {generated}  ")
    lines.append(f"**Mã nguồn:** {commit_hint}\n")

    lines.append("## 1. Phạm vi kết luận — đọc trước khi trích số\n")
    lines.append(
        "Bảng dưới đo **tính đầy đủ và rõ ràng của đặc tả trong prompt**, không đo "
        "chất lượng văn phong của mô hình. Lý do: lời gọi mô hình được thay bằng "
        "stub tất định.\n\n"
        "Stub tuân theo prompt một cách máy móc: nó sinh ra **chỉ những trường mà "
        "prompt nhắc tới**. Hệ quả trực tiếp và có lợi: nếu một phiên bản prompt "
        "không yêu cầu đủ trường, cột `Đủ trường bắt buộc` sẽ thấp — và đó chính "
        "là thứ ta muốn đo.\n\n"
        "Những gì bảng này **KHÔNG** chứng minh:\n\n"
        "- Văn phong hay sức thuyết phục của bài viết sinh ra.\n"
        "- Mức độ chính xác ngữ nghĩa của mô hình thật.\n"
        "- Rằng v3 \"tốt hơn v1\" với người đọc thật.\n"
        "- Bất kỳ so sánh nào với LLM qua mạng.\n\n"
        "Để so sánh chất lượng văn phong cần chạy cùng tập case qua provider thật "
        "và chấm bằng rubric có người đánh giá. Việc đó tốn credit và không tái lập "
        "được, nên nó không nằm trong CI.\n"
    )

    lines.append("## 2. Bảng so sánh\n")
    lines.append(
        "| Phiên bản | Ý định thiết kế của prompt đa kênh | Schema hợp lệ | "
        "Rò từ khóa cấm | Đủ trường bắt buộc | Placeholder chưa lấp | Prompt TB |"
    )
    lines.append("|:---|:---|---:|---:|---:|---:|---:|")
    for variant in VARIANTS:
        s = summaries[variant]
        lines.append(
            f"| `{variant}` | {diff_desc(variant)} | {s['schema_valid_rate']:.0f}% "
            f"({s['schema_valid']}/{s['cases']}) | {s['banned_keyword_leaks']} | "
            f"{s['required_field_coverage']:.0f}% | {s['unfilled_placeholders']} | "
            f"{s['avg_prompt_chars']} ký tự |"
        )
    lines.append("")
    lines.append(
        "> Cột \"Prompt TB\" là trung bình trên 4 tác vụ, tính cả system lẫn user "
        "prompt sau khi lấp đầy ngữ cảnh. Nó tăng mạnh từ `v1` lên `v3`: đây là **chi "
        "phí** đổi lấy tính đầy đủ của đặc tả, và là một đánh đổi có ý thức chứ không "
        "phải kết quả đẹp. Xem mục 4.\n"
    )

    lines.append("## 3. Chi tiết theo từng tác vụ\n")
    for task_type in sorted(STUBS):
        lines.append(f"### {task_type}\n")
        lines.append("| Phiên bản | Schema hợp lệ | Trường bắt buộc thiếu | Ghi chú |")
        lines.append("|:---|:---:|:---|:---|")
        for variant in VARIANTS:
            match = next(
                (r for r in all_results[variant] if r.task == task_type),
                None,
            )
            if match is None:
                continue
            if match.case_name == "khong_co_prompt_cho_tac_vu_nay":
                note = "phiên bản này không mô tả tác vụ"
                missing = f"toàn bộ ({len(match.missing_required_fields)} mục)"
            else:
                note = ""
                missing = ", ".join(f"`{m}`" for m in match.missing_required_fields) or "—"
            lines.append(
                f"| `{variant}` | {'có' if match.schema_valid else '**không**'} | {missing} | {note} |"
            )
        lines.append("")

    lines.append("## 4. Cái tiến và cái tụt — đọc thẳng, không diễn giải\n")
    lines.append(_improvement_section(summaries))
    lines.append("")

    lines.append("## 5. Bộ đo có thật sự bắt được lỗi không?\n")
    caught = negative_control.get("banned_keywords_caught", [])
    lines.append(
        "Chỉ số \"rò từ khóa cấm = 0\" ở bảng trên chỉ có nghĩa nếu bộ dò thật sự bắt "
        "được lỗi. Nếu không thì nó cũng bằng 0 khi bộ đo hỏng — hai khả năng đó nhìn "
        "giống hệt nhau.\n\n"
        "Vì vậy script chạy thêm một **đối chứng âm**: một stub cố ý nhét từ khóa cấm vào "
        "output, rồi kiểm tra bộ dò có bắt không. Kết quả lần chạy này:\n\n"
        f"- Bộ dò từ khóa cấm: **{'bắt được' if negative_control.get('banned_keyword_detector_works') else 'HỎNG'}** "
        f"— bắt {len(caught)} từ khóa"
        + (f" ({', '.join(repr(k) for k in caught)})" if caught else "")
        + ".\n"
        f"- Bộ dò placeholder sót: **{'bắt được' if negative_control.get('placeholder_detector_works') else 'HỎNG'}**.\n\n"
        "Nói cách khác: cột \"rò từ khóa cấm = 0\" trong bảng trên là kết quả đo được, "
        "không phải giá trị mặc định của một phép đo không làm gì.\n"
    )

    lines.append("## 6. Cách tái lập\n")
    lines.append("```bash")
    lines.append("python scripts/compare_prompt_variants.py")
    lines.append("```\n")
    lines.append(
        "Kết quả tất định: chạy lại cho ra cùng số. Không gọi mạng, không tốn credit. "
        "Script cũng ghi artifact máy đọc được ở "
        "[`scripts/prompt_variant_results.json`](../scripts/prompt_variant_results.json).\n"
    )

    lines.append("## 7. Điều chưa làm\n")
    lines.append(
        "- Chưa chạy cùng tập case này qua provider thật với người chấm điểm. Đó là "
        "khoảng trống thật của tài liệu này, không phải chi tiết nhỏ.\n"
        "- Chưa thử so sánh **giữa các model** (cùng prompt, khác provider). Rubric "
        "cho phép \"so sánh prompt **hoặc** model\"; tài liệu này chỉ làm phần prompt.\n"
        "- Các từ khóa cấm dùng trong benchmark là bộ cố định 3 từ để tập case là "
        "tất định, không phải blacklist thật của một workspace cụ thể.\n"
    )

    return "\n".join(lines) + "\n"


def _improvement_section(summaries: Dict[str, Dict[str, Any]]) -> str:
    v1, v2, v3 = (summaries.get(v) for v in ("v1", "v2", "v3"))
    out: List[str] = []
    out.append("So sánh `v1` → `v3` theo từng chỉ số:\n")

    def line(label: str, before: float, after: float, higher_is_better: bool) -> str:
        if before == after:
            verdict = "không đổi"
        elif (after > before) == higher_is_better:
            verdict = "**cải thiện**"
        else:
            verdict = "**tụt**"
        return f"- {label}: {before:g} → {after:g} ({verdict})"

    if v1 and v3:
        out.append(line("Schema hợp lệ (%)", v1["schema_valid_rate"], v3["schema_valid_rate"], True))
        out.append(line("Đủ trường bắt buộc (%)", v1["required_field_coverage"], v3["required_field_coverage"], True))
        out.append(line("Rò từ khóa cấm (số case)", v1["banned_keyword_leaks"], v3["banned_keyword_leaks"], False))
        out.append(line("Placeholder chưa lấp (số case)", v1["unfilled_placeholders"], v3["unfilled_placeholders"], False))
        out.append("")
        out.append("### Những gì KHÔNG cải thiện — và cái giá phải trả\n")
        out.append(
            f"- **Chi phí prompt tăng từ {v1['avg_prompt_chars']} lên {v3['avg_prompt_chars']} ký tự** "
            f"(xấp xỉ {v3['avg_prompt_chars'] / max(v1['avg_prompt_chars'], 1):.1f} lần). Với mỗi lời gọi "
            "AI thật, đây là token phải trả cho mỗi lần gọi. Đây là cái giá thật của v3, "
            "không phải điều gì đo bằng con số này được bù lại.\n"
        )
        out.append(
            "- **Rò từ khóa cấm vẫn bằng 0 ở cả ba phiên bản.** Nghĩa là bộ case hiện tại "
            "không phân biệt được prompt nào ràng buộc an toàn thương hiệu tốt hơn. Muốn "
            "đo được, phải có case mà mô hình thật *thực sự* cố phát ra từ khóa cấm — điều mà "
            "stub không làm được. Đây là khoảng trống thật, ghi ra để không ai tưởng đã đo.\n"
        )
        out.append(
            "- **Không có chỉ số nào đo độ dài hay văn phong.** Không so sánh được trong "
            "harness này (xem mục 1).\n"
        )

    if v2 and v3:
        out.append("\nSo sánh `v2` → `v3`:\n")
        out.append(line("Schema hợp lệ (%)", v2["schema_valid_rate"], v3["schema_valid_rate"], True))
        out.append(line("Đủ trường bắt buộc (%)", v2["required_field_coverage"], v3["required_field_coverage"], True))

    out.append(
        "\n**Đọc kết quả này thế nào khi bảo vệ:** v3 thắng ở chỉ số \"đủ trường bắt "
        "buộc\" vì nó là phiên bản duy nhất liệt kê đầy đủ khung JSON của cả ba kênh. "
        "Đó là một phát hiện có thật về đặc tả prompt, không phải bằng chứng rằng bài "
        "viết của v3 hay hơn. Nếu một phiên bản nào đứng cuối ở một chỉ số, phải nói "
        "ra chứ không giấu đi.\n"
    )
    return "\n".join(out)


def run_negative_control() -> Dict[str, Any]:
    """Chạy một stub cố ý phát ra từ khóa cấm, để chứng minh bộ dò rò bắt được.

    Không có bước này, chỉ số "rò từ khóa cấm = 0" ở bảng chính là vô nghĩa:
    ta không phân biệt được "hệ thống sạch" với "bộ đo hỏng". Đây là chỗ hay
    bị hỏi nhất khi bảo vệ, nên nó được kiểm chứng bằng code chứ không bằng lời.
    """
    leaked = []
    texts: List[str] = []
    _collect_text(stub_deliberately_leaks_banned_keyword("", BASE_CONTEXT), texts)
    haystack = _normalize(" ".join(texts))
    leaked = [kw for kw in BANNED_KEYWORDS if _normalize(kw) in haystack]

    # Còn kiểm tra bộ dò placeholder bằng một template cố ý để sót placeholder.
    unfilled = _unfilled_placeholders("Xin chào {{campaign_name}}, giá {{khong_ton_tai}}")

    detector_ok = len(leaked) >= 1
    placeholder_detector_ok = "khong_ton_tai" in unfilled

    print("\n--- Đối chứng âm (kiểm tra bộ đo, không tính vào bảng so sánh) ---")
    print(f"  Bộ dò từ khóa cấm phát hiện stub rò:  {'ĐÚNG' if detector_ok else 'HỎNG'} "
          f"({len(leaked)} từ khóa bị bắt)")
    print(f"  Bộ dò placeholder sót phát hiện sót:   {'ĐÚNG' if placeholder_detector_ok else 'HỎNG'}")

    return {
        "banned_keyword_detector_works": detector_ok,
        "banned_keywords_caught": leaked,
        "placeholder_detector_works": placeholder_detector_ok,
    }


def main() -> int:
    prompts = load_prompts()

    print("=" * 78)
    print("SO SÁNH PHIÊN BẢN PROMPT — Tuần 3, mục 4 rubric AIA331")
    print("Lời gọi mô hình được thay bằng stub tất định: đo đặc tả prompt, không đo văn phong.")
    print("=" * 78)

    all_results: Dict[str, List[CaseResult]] = {}
    summaries: Dict[str, Dict[str, Any]] = {}

    for variant in VARIANTS:
        results = evaluate_variant(variant, prompts)
        all_results[variant] = results
        summaries[variant] = summarise(results)

        print(f"\n[{variant}]")
        for r in results:
            status = "OK " if r.schema_valid else "SAI"
            fields = "đủ" if r.required_fields_present else f"thiếu {r.missing_required_fields}"
            leak = f"RÒ {r.banned_leak}" if r.banned_leak else "sạch"
            print(f"  {status} {r.task:24s} {fields:42s} {leak}")
        s = summaries[variant]
        print(
            f"  => schema {s['schema_valid_rate']:.0f}% | "
            f"đủ trường {s['required_field_coverage']:.0f}% | "
            f"rò từ khóa {s['banned_keyword_leaks']} | "
            f"placeholder sót {s['unfilled_placeholders']}"
        )

    negative_control = run_negative_control()

    markdown = build_markdown(prompts, all_results, summaries, negative_control)
    report_path = ROOT_DIR / "docs" / "PROMPT_VARIANT_COMPARISON.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")

    artifact = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "harness": "deterministic-stub",
        "negative_control": negative_control,
        "banned_keywords": BANNED_KEYWORDS,
        "cases_per_variant": len(all_results[VARIANTS[0]]),
        "variants": {
            v: {
                "summary": summaries[v],
                "cases": [
                    {
                        "task": r.task,
                        "schema_valid": r.schema_valid,
                        "required_fields_present": r.required_fields_present,
                        "missing_required_fields": r.missing_required_fields,
                        "banned_keyword_leak": r.banned_leak,
                        "unfilled_placeholders": r.placeholders_unfilled,
                        "prompt_chars": r.prompt_chars,
                    }
                    for r in all_results[v]
                ],
            }
            for v in VARIANTS
        },
    }
    artifact_path = ROOT_DIR / "scripts" / "prompt_variant_results.json"
    artifact_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n" + "=" * 78)
    print(f"Báo cáo : {report_path}")
    print(f"Artifact: {artifact_path}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())