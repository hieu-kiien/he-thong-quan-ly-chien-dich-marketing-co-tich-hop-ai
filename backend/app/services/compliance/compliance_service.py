import re
import json
import unicodedata
from typing import Optional, List, Dict, Set, Any
from sqlalchemy.orm import Session
from app.models.entities import BrandKit
from app.schemas.schemas import ViolationItem, ComplianceCheckResponse


def strip_accents(text: str) -> str:
    """Loại bỏ dấu tiếng Việt (NFD accent stripping) và chuẩn hóa đ/Đ."""
    if not text:
        return ""
    text_nfd = unicodedata.normalize('NFD', text)
    cleaned = "".join(c for c in text_nfd if unicodedata.category(c) != 'Mn')
    return cleaned.replace('đ', 'd').replace('Đ', 'D')


# Danh mục chính sách quảng cáo chuẩn Meta & TikTok Ads (FEAT-BE-14)
AD_POLICY_RULES: List[Dict[str, str]] = [
    # HIGH severity: Cam kết kết quả tuyệt đối sai sự thật & lừa đảo tài chính / y tế
    {
        "phrase": "cam kết 100% việc làm",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Hỗ trợ kết nối việc làm', 'Đồng hành sát sao cùng học viên'"
    },
    {
        "phrase": "cam kết 100% lương",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Mục tiêu đạt mức thu nhập mong muốn', 'Đào tạo kỹ năng thực chiến'"
    },
    {
        "phrase": "cam kết 100%",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Cam kết đồng hành', 'Hỗ trợ tối đa người học/khách hàng'"
    },
    {
        "phrase": "cam kết hoàn tiền",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Nêu rõ chính sách và điều kiện áp dụng minh bạch"
    },
    {
        "phrase": "cam kết không rủi ro",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Nêu rõ phương án đồng hành và bảo đảm an toàn cho khách hàng"
    },
    {
        "phrase": "hoàn vốn ngay lập tức",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Cơ hội tối ưu chi phí và hoàn vốn theo lộ trình rõ ràng'"
    },
    {
        "phrase": "hoàn tiền nếu không thành công",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Nêu rõ điều kiện chính sách hỗ trợ minh bạch"
    },
    {
        "phrase": "hoàn tiền không lý do",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Nêu rõ điều khoản đổi trả minh bạch"
    },
    {
        "phrase": "chữa khỏi dứt điểm",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Hỗ trợ cải thiện', 'Giúp nâng cao sức khỏe'"
    },
    {
        "phrase": "chữa dứt điểm",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Hỗ trợ cải thiện', 'Liệu trình chăm sóc chuyên sâu'"
    },
    {
        "phrase": "trị dứt điểm",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Hỗ trợ giảm thiểu triệu chứng an toàn'"
    },
    {
        "phrase": "thuốc trị dứt",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Sản phẩm hỗ trợ sức khỏe'"
    },
    {
        "phrase": "khỏi hẳn 100%",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Cải thiện rõ rệt khi tuân thủ liệu trình'"
    },
    {
        "phrase": "trắng da cấp tốc",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Lộ trình chăm sóc an toàn', 'Dưỡng da khoa học'"
    },
    {
        "phrase": "giảm cân cấp tốc",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Lộ trình giảm cân an toàn, lành mạnh'"
    },
    {
        "phrase": "trị mụn cấp tốc",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Phương pháp chăm sóc da mụn khoa học'"
    },
    {
        "phrase": "làm giàu nhanh",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Mô tả cơ hội học tập, kỹ năng thực tế có căn cứ"
    },
    {
        "phrase": "kiếm tiền tỷ",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Mô tả triển vọng tài chính dựa trên nỗ lực và kết quả thực tế"
    },
    {
        "phrase": "thu nhập thụ động 100 triệu",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Mô tả tiềm năng thu nhập dựa trên số liệu thực tế"
    },
    {
        "phrase": "đa cấp",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng mô hình phân phối hoặc đối tác kinh doanh hợp pháp"
    },
    {
        "phrase": "lãi suất siêu tưởng",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Nêu rõ tỷ suất sinh lời kỳ vọng thực tế"
    },
    {
        "phrase": "việc nhẹ lương cao",
        "severity": "HIGH",
        "category": "AD_POLICY",
        "suggestion": "Mô tả chi tiết yêu cầu công việc và chế độ đãi ngộ"
    },

    # MEDIUM severity: Cạnh tranh giá không lành mạnh / Tuyên bố so sánh nhất
    {
        "phrase": "bán phá giá",
        "severity": "MEDIUM",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Ưu đãi đặc quyền', 'Chương trình trợ giá độc quyền'"
    },
    {
        "phrase": "xả kho sập giá",
        "severity": "MEDIUM",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Chương trình tri ân khách hàng', 'Ưu đãi số lượng có hạn'"
    },
    {
        "phrase": "giá rẻ như cho",
        "severity": "MEDIUM",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Chi phí cực kỳ hợp lý', 'Mức giá ưu đãi đặc biệt'"
    },
    {
        "phrase": "rẻ nhất thị trường",
        "severity": "MEDIUM",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Mức giá tối ưu cho người dùng', 'Chi phí cạnh tranh'"
    },
    {
        "phrase": "rẻ nhất quả đất",
        "severity": "MEDIUM",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Mức giá tối ưu', 'Chi phí tiết kiệm vượt trội'"
    },
    {
        "phrase": "rẻ nhất",
        "severity": "MEDIUM",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Chi phí tối ưu', 'Giá cả hợp lý'"
    },
    {
        "phrase": "tốt nhất hiện nay",
        "severity": "MEDIUM",
        "category": "AD_POLICY",
        "suggestion": "Dùng 'Giải pháp hàng đầu trong phân khúc', 'Được khách hàng tin cậy'"
    },
    {
        "phrase": "độc quyền duy nhất",
        "severity": "MEDIUM",
        "category": "AD_POLICY",
        "suggestion": "Thay bằng 'Giải pháp độc quyền của thương hiệu'"
    },
    {
        "phrase": "số một",
        "severity": "MEDIUM",
        "category": "AD_POLICY",
        "suggestion": "Dùng 'Giải pháp hàng đầu trong phân khúc', 'Được khách hàng tin cậy'"
    },
    {
        "phrase": "số 1",
        "severity": "MEDIUM",
        "category": "AD_POLICY",
        "suggestion": "Dùng 'Giải pháp hàng đầu trong phân khúc', 'Được khách hàng tin cậy'"
    },

    # LOW severity: Giật gân / Clickbait quá đà
    {
        "phrase": "sốc",
        "severity": "LOW",
        "category": "AD_POLICY",
        "suggestion": "Điều chỉnh văn phong sang trọng, tinh tế, đúng định vị thương hiệu"
    },
    {
        "phrase": "kinh hoàng",
        "severity": "LOW",
        "category": "AD_POLICY",
        "suggestion": "Điều chỉnh văn phong chuyên nghiệp, chuẩn mực"
    },
    {
        "phrase": "bật ngửa",
        "severity": "LOW",
        "category": "AD_POLICY",
        "suggestion": "Dùng từ ngữ ấn tượng, thanh lịch"
    },
    {
        "phrase": "chấn động",
        "severity": "LOW",
        "category": "AD_POLICY",
        "suggestion": "Dùng từ ngữ tinh tế, kích thích tương tác tích cực"
    },
]


class ComplianceScanner:
    """Bộ thẩm định và kiểm tra tuân thủ đa tầng (Compliance & Policy Guardrail - R3)."""

    @classmethod
    def _match_phrase(cls, phrase: str, raw_text: str, stripped_text: str) -> bool:
        """Kiểm tra sự xuất hiện của từ khóa/cụm từ trong văn bản cả có dấu và không dấu,
        có bảo vệ ranh giới từ để tránh false positive (ví dụ: không bắt 'số 10', 'số 1.000' khi tìm 'số 1',
        không bắt 'chăm sóc' khi tìm 'sốc', không bắt 'đa cấp độ' khi tìm 'đa cấp').
        """
        phrase_clean = phrase.strip()
        if not phrase_clean:
            return False

        phrase_raw = unicodedata.normalize('NFC', phrase_clean).lower()
        phrase_stripped = strip_accents(phrase_raw)

        # 1. Xử lý đặc thù cho từ nhạy cảm 'sốc' để tránh đụng độ với từ vựng thông dụng ('chăm sóc', 'kẻ sọc', v.v.)
        check_raw = raw_text
        check_stripped = stripped_text
        if phrase_raw in ["sốc", "soc"] or phrase_stripped == "soc":
            safe_phrases_raw = [
                r"(?<![\wÀ-ỹ])chăm\s+sóc(?![\wÀ-ỹ])",
                r"(?<![\wÀ-ỹ])sóc\s+trăng(?![\wÀ-ỹ])",
                r"(?<![\wÀ-ỹ])(?:áo\s+)?kẻ\s+sọc(?![\wÀ-ỹ])",
                r"(?<![\wÀ-ỹ])sọc\s+caro(?![\wÀ-ỹ])",
                r"(?<![\wÀ-ỹ])con\s+sóc(?![\wÀ-ỹ])",
                r"(?<![\wÀ-ỹ])sóc\s+chuột(?![\wÀ-ỹ])",
                r"(?<![\wÀ-ỹ])sọc\s+dưa(?![\wÀ-ỹ])",
            ]
            safe_phrases_stripped = [
                r"(?<!\w)cham\s+soc(?!\w)",
                r"(?<!\w)soc\s+trang(?!\w)",
                r"(?<!\w)(?:ao\s+)?ke\s+soc(?!\w)",
                r"(?<!\w)soc\s+caro(?!\w)",
                r"(?<!\w)con\s+soc(?!\w)",
                r"(?<!\w)soc\s+chuot(?!\w)",
                r"(?<!\w)soc\s+dua(?!\w)",
            ]
            for p in safe_phrases_raw:
                check_raw = re.sub(p, " ", check_raw, flags=re.IGNORECASE)
            for p in safe_phrases_stripped:
                check_stripped = re.sub(p, " ", check_stripped, flags=re.IGNORECASE)

        # 2. Xây dựng regex bảo vệ ranh giới từ tiếng Việt & ký tự chữ số
        if phrase_raw in ["đa cấp", "da cap"] or phrase_stripped == "da cap":
            pattern_raw = rf"(?<![\wÀ-ỹ])đa\s*cấp(?![\s_]+(?:độ|do|bậc|bac))(?![\wÀ-ỹ])"
            pattern_stripped = rf"(?<!\w)da\s*cap(?![\s_]+(?:độ|do|bậc|bac))(?!\w)"
        elif phrase_raw in ["số 1", "so 1"] or phrase_stripped == "so 1":
            pattern_raw = rf"(?<![\wÀ-ỹ])số\s*1(?![.,\d])(?![\wÀ-ỹ])"
            pattern_stripped = rf"(?<!\w)so\s*1(?![.,\d])(?!\w)"
        else:
            pattern_raw = rf"(?<![\wÀ-ỹ]){re.escape(phrase_raw)}(?![\wÀ-ỹ])"
            pattern_stripped = rf"(?<!\w){re.escape(phrase_stripped)}(?!\w)"

        if re.search(pattern_raw, check_raw, re.IGNORECASE):
            return True
        if re.search(pattern_stripped, check_stripped, re.IGNORECASE):
            return True
        return False

    @classmethod
    def scan(
        cls,
        title: Optional[str] = "",
        body: Optional[str] = "",
        cta: Optional[str] = None,
        workspace_id: Optional[int] = None,
        db: Optional[Session] = None,
        custom_banned_keywords: Optional[List[str]] = None
    ) -> ComplianceCheckResponse:
        """Quét toàn diện nội dung Marketing đối chiếu Brand Blacklist & Ad Policy."""
        combined = f"{title or ''} {body or ''} {cta or ''}".strip()
        if not combined:
            return ComplianceCheckResponse(
                status="PASSED",
                score=100,
                can_submit=True,
                violations=[]
            )

        raw_lower = unicodedata.normalize('NFC', combined).lower()
        stripped_lower = strip_accents(raw_lower)

        violations: List[ViolationItem] = []
        matched_normalized_words: Set[str] = set()

        # 1. Quét Lớp 1: Brand Kit Blacklist (Multi-tenant Workspace)
        banned_keywords: List[str] = []
        if custom_banned_keywords:
            banned_keywords.extend(custom_banned_keywords)

        if db is not None and workspace_id is not None:
            brand_kit = db.query(BrandKit).filter(BrandKit.workspace_id == workspace_id).first()
            if brand_kit and brand_kit.banned_keywords_json:
                try:
                    kws = json.loads(brand_kit.banned_keywords_json)
                    if isinstance(kws, list):
                        for k in kws:
                            if k and str(k).strip():
                                banned_keywords.append(str(k).strip())
                except Exception:
                    pass

        # Quét các từ cấm Brand Kit (Mức HIGH)
        for kw in banned_keywords:
            norm_kw = strip_accents(kw.lower().strip())
            if norm_kw in matched_normalized_words:
                continue

            if cls._match_phrase(kw, raw_lower, stripped_lower):
                matched_normalized_words.add(norm_kw)
                violations.append(ViolationItem(
                    category="BRAND_BANNED",
                    severity="HIGH",
                    word=kw,
                    suggestion=f"Thay thế hoặc loại bỏ từ khóa '{kw}' theo quy chuẩn thương hiệu"
                ))

        # 2. Quét Lớp 2: Ad Policy Guidelines (Meta & TikTok Ads)
        for rule in AD_POLICY_RULES:
            phrase = rule["phrase"]
            norm_phrase = strip_accents(phrase.lower().strip())
            if norm_phrase in matched_normalized_words:
                continue

            if cls._match_phrase(phrase, raw_lower, stripped_lower):
                matched_normalized_words.add(norm_phrase)
                violations.append(ViolationItem(
                    category=rule["category"],
                    severity=rule["severity"],
                    word=phrase,
                    suggestion=rule["suggestion"]
                ))

        # 3. Tính điểm tuân thủ & trạng thái
        total_penalty = 0
        for v in violations:
            if v.severity == "HIGH":
                total_penalty += 35
            elif v.severity == "MEDIUM":
                total_penalty += 15
            elif v.severity == "LOW":
                total_penalty += 5

        score = max(0, min(100, 100 - total_penalty))
        has_high = any(v.severity == "HIGH" for v in violations)
        has_violations = len(violations) > 0

        if has_high:
            status = "VIOLATION"
            can_submit = False
        elif has_violations:
            status = "WARNING"
            can_submit = True
        else:
            status = "PASSED"
            score = 100
            can_submit = True

        return ComplianceCheckResponse(
            status=status,
            score=score,
            can_submit=can_submit,
            violations=violations
        )
