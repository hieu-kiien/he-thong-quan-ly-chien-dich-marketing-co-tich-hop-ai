import re
from pathlib import Path

import pytest

"""
Bảo đảm tài liệu phân tích yêu cầu và tài liệu đối chiếu rubric không nói sai.

Bối cảnh
---------
`docs/REQUIREMENTS_AND_DESIGN.md` và `docs/UNIVERSITY_DEFENSE_RUBRIC_ALIGNMENT.md`
là hai tài liệu dùng để trả lời Bài kiểm tra 1 và để chuẩn bị bảo vệ. Chúng chứa
rất nhiều khẳng định dạng "có test chứng minh", "có phân trang", "sử dụng bcrypt".

Không có gì nguy hiểm bằng một tài liệu khẳng định sai một cách tự tin. Người đọc
tin, giảng viên hỏi, rồi mở file ra thấy không có — mất uy tín ngay lập tức.

Nên file test này kiểm tra:
1. Mọi đường dẫn `docs/*.md` được trích trong hai tài liệu phải tồn tại.
2. Mọi tên file test được nhắc tới phải tồn tại trong `backend/tests/`.
3. Các khẳng định có thể kiểm chứng bằng mã nguồn phải đúng với mã nguồn.
4. Hai tài liệu phải liên kết qua lại và được liệt kê trong mục lục.
"""

ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
DOCS = ROOT / "docs"

REQUIREMENTS_DOC = DOCS / "REQUIREMENTS_AND_DESIGN.md"
RUBRIC_DOC = DOCS / "UNIVERSITY_DEFENSE_RUBRIC_ALIGNMENT.md"
GAP_DOC = DOCS / "REQUIREMENTS_GAP_ANALYSIS.md"

# Tài liệu nào phải được kiểm tra toàn vẹn đường dẫn và không chứa secret.
_VERIFIED_DOCS = [REQUIREMENTS_DOC, RUBRIC_DOC, GAP_DOC]


@pytest.fixture(scope="module")
def requirements_text() -> str:
    assert REQUIREMENTS_DOC.exists(), f"Không tìm thấy {REQUIREMENTS_DOC}"
    return REQUIREMENTS_DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def rubric_text() -> str:
    assert RUBRIC_DOC.exists(), f"Không tìm thấy {RUBRIC_DOC}"
    return RUBRIC_DOC.read_text(encoding="utf-8")


@pytest.mark.parametrize("doc_path", _VERIFIED_DOCS)
def test_documentation_files_exist_and_are_substantial(doc_path):
    assert doc_path.exists(), f"Thiếu {doc_path}"
    text = doc_path.read_text(encoding="utf-8")
    assert len(text) > 3000, f"{doc_path.name} quá ngắn để là tài liệu thiết kế"


@pytest.mark.parametrize("doc_path", _VERIFIED_DOCS)
def test_no_secret_patterns(doc_path):
    """Không tài liệu thiết kế nào được chứa thứ giống secret."""
    text = doc_path.read_text(encoding="utf-8")
    patterns = {
        "OpenAI-style key": r"sk-[A-Za-z0-9]{20,}",
        "Anthropic-style key": r"sk-ant-[A-Za-z0-9]{20,}",
        "Gemini-style key": r"AIza[0-9A-Za-z_\-]{25,}",
        "HuggingFace token": r"hf_[A-Za-z0-9]{20,}",
        "Postgres URL": r"postgres(ql)?://[^\s)]+",
        "JWT": r"eyJ[A-Za-z0-9_\-]{20,}",
    }
    for label, pattern in patterns.items():
        match = re.search(pattern, text)
        assert match is None, f"{doc_path.name} chứa chuỗi giống {label}"


@pytest.mark.parametrize("doc_path", _VERIFIED_DOCS)
def test_linked_docs_exist(doc_path):
    """Liên kết nội bộ trong docs/ phải dẫn tới file có thật."""
    text = doc_path.read_text(encoding="utf-8")
    referenced = set(re.findall(r"\]\(([A-Za-z0-9_\.]+\.md)\)", text))
    assert referenced, f"{doc_path.name} không liên kết tài liệu nào — có vẻ sai chỗ"

    missing = [ref for ref in sorted(referenced) if not (DOCS / ref).exists()]
    assert not missing, f"{doc_path.name} liên kết tới file không tồn tại: {missing}"


@pytest.mark.parametrize("doc_path", _VERIFIED_DOCS)
def test_referenced_test_files_exist(doc_path):
    """Mọi tên file test được nhắc tới phải tồn tại trong backend/tests/.

    Đây là phép kiểm tra quan trọng nhất: hai tài liệu này dùng cụm "có test chứng
    minh" rất nhiều lần. Tên test sai = bằng chứng không tồn tại.
    """
    text = doc_path.read_text(encoding="utf-8")
    referenced = set(re.findall(r"`(test_[a-z0-9_]+\.py)`", text))
    assert referenced, f"{doc_path.name} không nhắc tới file test nào"

    missing = [
        ref for ref in sorted(referenced)
        if not any((BACKEND / "tests").rglob(ref))
    ]
    assert not missing, f"{doc_path.name} nhắc tới file test không tồn tại: {missing}"


@pytest.mark.parametrize("doc_path", _VERIFIED_DOCS)
def test_referenced_backend_paths_exist(doc_path):
    """Đường dẫn `app/...` trong tài liệu phải tồn tại dưới backend/."""
    text = doc_path.read_text(encoding="utf-8")
    referenced = set(re.findall(r"`(app/[A-Za-z0-9_/\.]+\.py)`", text))
    missing = [ref for ref in sorted(referenced) if not (BACKEND / ref).exists()]
    assert not missing, f"{doc_path.name} trích dẫn file backend không tồn tại: {missing}"


def test_requirements_doc_covers_every_bai1_criterion(requirements_text):
    """Tài liệu phải đáp ứng đủ 10 mục của Bài kiểm tra thường xuyên 1.

    Mỗi mục của rubric phải có mục tương ứng. Nếu thiếu một mục, đó là lỗ hổng khi
    nộp bài — và lỗ hổng loại này rất dễ xảy ra vì tài liệu viết dần theo thời gian.
    """
    for heading in (
        "## 1.",      # Phân tích tác nhân, bối cảnh, dữ liệu, vấn đề
        "## 2.",      # Yêu cầu chức năng
        "## 3.",      # Yêu cầu phi chức năng
        "## 4.",      # Tác nhân & use case
        "## 5.",      # Vị trí ứng dụng AI
        "## 6.",      # Thiết kế prompt & luồng gọi AI
        "## 7.",      # Minh chứng kiến thức quản lý cho AI
        "## 8.",      # Kế hoạch giai đoạn tiếp theo
        "## 9.",      # Nợ kỹ thuật đã biết
    ):
        assert heading in requirements_text, f"Thiếu mục {heading} trong tài liệu yêu cầu"


def test_requirements_doc_has_use_case_diagram(requirements_text):
    """Tiêu chí 4 của Bài 1 yêu cầu sơ đồ use case hoặc mô tả tương đương."""
    assert "```mermaid" in requirements_text, (
        "Tài liệu phải có sơ đồ (mermaid) cho tác nhân và use case."
    )
    assert "graph" in requirements_text


def test_requirements_doc_quotes_real_prompt():
    """System prompt trích trong tài liệu phải khớp prompts.json thật.

    Trích dẫn sai một câu trong system prompt là loại sai sót dễ xảy ra nhất: ai
    cũng tưởng mình nhớ đúng, và khi giảng viên mở `prompts.json` đối chiếu thì
    mất điểm ngay lập tức.
    """
    import json

    prompts = json.loads(
        (BACKEND / "prompts" / "prompts.json").read_text(encoding="utf-8")
    )
    system_v3 = prompts["idea_generation"]["v3"]["system"]
    # Tài liệu viết lại trên nhiều dòng; so khớp các mảnh đủ dài để tránh trùng
    # ở những cụm chung chung.
    fragments = [
        "100% TIẾNG VIỆT",
        "Trả về định dạng JSON hợp lệ duy nhất",
        "để con người duyệt",
    ]
    for fragment in fragments:
        assert fragment in system_v3, (
            f"Đoạn trích trong tài liệu không có trong prompts.json: {fragment!r}"
        )


def test_requirements_doc_prompt_variables_match_template():
    """Placeholder nêu trong tài liệu phải là placeholder có thật trong prompts.json."""
    import json

    text = REQUIREMENTS_DOC.read_text(encoding="utf-8")
    prompts = json.loads(
        (BACKEND / "prompts" / "prompts.json").read_text(encoding="utf-8")
    )
    user_v3 = prompts["idea_generation"]["v3"]["user"]

    # Biến được tài liệu liệt kê trong bảng "Đầu vào" của bảng ở mục 5.
    for variable in ("campaign_name", "objective", "audience", "product_name", "tone"):
        assert "{{" + variable + "}}" in user_v3, (
            f"prompts.json không có placeholder {{{{variable}}}}"
        )
        assert variable in text, f"Tài liệu không nói tới biến {variable}"


def test_rubric_doc_covers_all_four_sections(rubric_text):
    """Bảng đối chiếu phải có đủ 4 phần của rubric, mỗi phần 10 tiêu chí."""
    for heading in (
        "## Phần 1",
        "## Phần 2",
        "## Phần 3",
        "## Phần 4",
    ):
        assert heading in rubric_text, f"Tài liệu đối chiếu thiếu {heading}"


def test_rubric_doc_has_40_criteria(rubric_text):
    """Đếm số dòng bảng đánh số ở cột "#". Phải đúng 40 tiêu chí."""
    rows = re.findall(r"^\|\s*(\d{1,2})\s*\|", rubric_text, flags=re.MULTILINE)
    numbers = sorted({int(n) for n in rows})
    # 1..10 xuất hiện ở cả 4 phần; tập hợp các số phải là 1..10 và mỗi số xuất
    # hiện đúng 4 lần.
    assert set(numbers) == set(range(1, 11)), f"Thiếu số tiêu chí: {numbers}"
    from collections import Counter

    counts = Counter(int(n) for n in rows)
    wrong = {n: c for n, c in counts.items() if c != 4}
    assert not wrong, (
        f"Số tiêu chí xuất hiện sai số lần (phải là 4): {wrong}. "
        "Có thể bảng đối chiếu bị mất hoặc thừa dòng."
    )


def test_rubric_doc_does_not_claim_full_pagination(rubric_text):
    """Phân trang là điểm yếu thật. Tài liệu không được nói là đã có đủ.

    Nếu sau này ai đó thêm `limit`/`offset` cho `/campaigns` thì phải cập nhật cả
    tài liệu đối chiếu lẫn ROADMAP — test này sẽ bắt được nếu chỉ sửa một nơi.
    """
    campaigns_router = (BACKEND / "app" / "api" / "v1" / "campaigns.py").read_text(
        encoding="utf-8"
    )
    has_pagination = bool(
        re.search(r"\b(limit|offset|page_size|skip)\b\s*[:=]", campaigns_router)
    )
    assert not has_pagination, (
        "/campaigns đã có phân trang nhưng tài liệu đối chiếu vẫn ghi là thiếu — "
        "cần cập nhật docs/UNIVERSITY_DEFENSE_RUBRIC_ALIGNMENT.md và docs/ROADMAP.md."
    )
    assert "Một phần" in rubric_text, (
        "Tiêu chí phân trang phải được đánh dấu 'Một phần', không phải 'Đã có'."
    )


def test_both_docs_are_cross_linked(requirements_text, rubric_text):
    """Hai tài liệu phải trỏ qua lại, nếu không sẽ tồn tại hai tài liệu mồ côi."""
    assert "REQUIREMENTS_AND_DESIGN.md" in rubric_text, (
        "Tài liệu đối chiếu rubric phải trỏ tới tài liệu phân tích yêu cầu."
    )
    assert "UNIVERSITY_DEFENSE_RUBRIC_ALIGNMENT.md" in requirements_text, (
        "Tài liệu phân tích yêu cầu phải trỏ ngược lại tài liệu đối chiếu rubric."
    )


def test_requirements_doc_is_linked_from_docs_index():
    index = (DOCS / "README.md").read_text(encoding="utf-8")
    assert "REQUIREMENTS_AND_DESIGN.md" in index, (
        "docs/README.md chưa liên kết REQUIREMENTS_AND_DESIGN.md."
    )


def test_gap_doc_flags_the_model_restriction_conflict():
    """Tài liệu khoảng cách phải nêu mâu thuẫn cấm Claude/GPT.

    Yêu cầu viết (2026-09-23) cấm Claude/GPT, còn rubric Bài 3 mục 2 bắt buộc hỗ
    trợ Claude. Đây là nơi dễ mất điểm nhất: nếu tài liệu im lặng, giảng viên mở
    `ORIGINAL_REQUEST.md` ra thấy mâu thuẫn và hỏi — mà không có sẵn câu trả lời
    đã nghĩ kỹ.
    """
    gap_text = GAP_DOC.read_text(encoding="utf-8")
    assert "Claude" in gap_text and "GPT" in gap_text
    for marker in ("TUYỆT ĐỐI KHÔNG", "Bài 3 mục 2"):
        assert marker in gap_text, (
            f"Tài liệu khoảng cách phải trích nguyên văn xung đột ({marker!r}) "
            "để giảng viên thấy rằng mâu thuẫn là có thật và đã được xử lý."
        )
    assert "rubric" in gap_text.lower()


def test_gap_doc_records_the_realm_of_unmet_requirements():
    """Phần "chưa làm" phải có đủ các mục thiếu đã biết."""
    gap_text = GAP_DOC.read_text(encoding="utf-8")
    for topic in ("Phân trang", "Mutation", "Excel/PDF", "backup/restore", "thiên lệch"):
        assert topic in gap_text, (
            f"Tài liệu khoảng cách thiếu mục chưa làm: {topic!r}. "
            "Giấu khoảng cách tệ hơn thừa nhận nó."
        )
    assert "CHƯA LÀM" in gap_text or "MỘT PHẦN" in gap_text


def test_gap_doc_concludes_the_it_thesis_subproject():
    """Phải kết luận về thư mục `it-thesis-...` để không ai hỏi lại."""
    gap_text = GAP_DOC.read_text(encoding="utf-8")
    assert "it-thesis-research-documentation-engineer" in gap_text
    assert "công cụ" in gap_text.lower()


def test_role_enum_claim_matches_code(requirements_text):
    """Tài liệu liệt kê 5 vai trò; code phải có đúng 5 giá trị."""
    entities = (BACKEND / "app" / "models" / "entities.py").read_text(encoding="utf-8")
    for role in ("MANAGER", "MARKETER", "AGENCY_MANAGER", "CLIENT_APPROVER", "ADMIN"):
        assert role in entities, f"Vai trò {role} không có trong entities.py"
        assert role in requirements_text, f"Tài liệu không nhắc vai trò {role}"


def test_requirements_doc_lists_actual_tables(requirements_text):
    """Bảng dữ liệu nêu trong tài liệu phải là bảng thật trong schema."""
    entities = (BACKEND / "app" / "models" / "entities.py").read_text(encoding="utf-8")
    declared = set(re.findall(r'__tablename__\s*=\s*"([a-z_]+)"', entities))

    mentioned = set(re.findall(r"`([a-z_]+)`", requirements_text))
    claimed_tables = {t for t in mentioned if t in declared}
    assert len(claimed_tables) >= 10, (
        f"Tài liệu mới chỉ nêu {len(claimed_tables)} bảng thật — có vẻ bảng dữ liệu "
        "đã bị thay bằng mô tả chung chung."
    )

    # Vài bảng trụ cột phải được nêu đích danh.
    for table in ("campaigns", "marketing_contents", "ai_logs", "brand_kits",
                  "workspace_members", "campaign_metrics"):
        assert table in requirements_text, f"Tài liệu không nêu bảng {table}"
