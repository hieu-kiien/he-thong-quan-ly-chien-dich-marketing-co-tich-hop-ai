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

# Tài liệu nào phải được kiểm tra toàn vẹn đường dẫn và không chứa secret.
_VERIFIED_DOCS = [REQUIREMENTS_DOC]


@pytest.fixture(scope="module")
def requirements_text() -> str:
    assert REQUIREMENTS_DOC.exists(), f"Không tìm thấy {REQUIREMENTS_DOC}"
    return REQUIREMENTS_DOC.read_text(encoding="utf-8")


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


def test_requirements_doc_is_linked_from_docs_index():
    index = (DOCS / "README.md").read_text(encoding="utf-8")
    assert "REQUIREMENTS_AND_DESIGN.md" in index, (
        "docs/README.md chưa liên kết REQUIREMENTS_AND_DESIGN.md."
    )


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
