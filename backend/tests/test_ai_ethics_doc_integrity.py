import re
from pathlib import Path

import pytest

"""
Bảo đảm tài liệu đạo đức AI không trở thành lời hứa suông.

Vấn đề mà file test này chặn
---------------------------
`docs/AI_ETHICS_AND_HUMAN_OVERSIGHT.md` là tài liệu dùng để bảo vệ. Nếu nó trích
dẫn một cơ chế đã bị xoá, hoặc trích dẫn một test không tồn tại, thì nó tệ hơn
là không có tài liệu: người đọc tin vào nó rồi đi tìm và không thấy.

Vì vậy: mỗi đường dẫn file và mỗi tên hàm test được trích trong tài liệu phải
tồn tại thật. Test này kiểm tra đúng điều đó.

Ngoài ra: tài liệu phải có mục "không thể khẳng định". Tài liệu đạo đức chỉ
liệt kê điều tốt là dấu hiệu của tài liệu quảng cáo, không phải tài liệu kỹ thuật.
"""

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DOC_PATH = ROOT_DIR / "docs" / "AI_ETHICS_AND_HUMAN_OVERSIGHT.md"
BACKEND = ROOT_DIR / "backend"
FRONTEND = ROOT_DIR / "frontend"


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Không tìm thấy {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_document_exists(doc_text):
    assert len(doc_text) > 2000, "Tài liệu quá ngắn — có vẻ chỉ là khung"


def test_document_has_required_sections(doc_text):
    """Các mục rubric mục 5 (chất lượng chức năng AI) và mục 6 (đạo đức AI)."""
    for heading in (
        "## 1.",
        "## 2.",
        "## 3.",
        "## 4.",
        "## 5.",
        "## 6.",
        "## 7.",
        "## 8.",
        "## 9.",
        "## 10.",
    ):
        assert heading in doc_text, f"Tài liệu thiếu mục {heading}"


def test_document_states_what_it_cannot_claim(doc_text):
    """Bắt buộc có phần nêu rõ giới hạn.

    Tài liệu đạo đức chỉ liệt kê điều tốt là dấu hiệu tài liệu quảng cáo. Mục 8
    của tài liệu này liệt kê những gì không có cơ sở để khẳng định — nếu ai đó
    xoá đi, test này đỏ.
    """
    assert "KHÔNG có cơ sở để khẳng định" in doc_text, (
        "Tài liệu phải có phần nêu rõ điều KHÔNG thể khẳng định."
    )
    for forbidden_claim in ("không bao giờ", "tuyệt đối an toàn", "hoàn hảo"):
        # Cụm này chỉ được xuất hiện trong phần giới hạn, dạng phủ định.
        occurrences = doc_text.count(forbidden_claim)
        assert occurrences <= 3, (
            f"Cụm tuyên bố tuyệt đối {forbidden_claim!r} xuất hiện {occurrences} lần — "
            "nhiều quá cho một tài liệu trung thực."
        )


def test_no_secret_patterns_in_document(doc_text):
    """Tài liệu không được chứa gì giống secret."""
    patterns = {
        "OpenAI-style key": r"sk-[A-Za-z0-9]{20,}",
        "Anthropic-style key": r"sk-ant-[A-Za-z0-9]{20,}",
        "Gemini-style key": r"AIza[0-9A-Za-z_\-]{25,}",
        "HuggingFace token": r"hf_[A-Za-z0-9]{20,}",
        "Postgres URL": r"postgres(ql)?://[^\s]+",
        "JWT": r"eyJ[A-Za-z0-9_\-]{20,}",
    }
    for label, pattern in patterns.items():
        match = re.search(pattern, doc_text)
        assert match is None, (
            f"Tài liệu chứa chuỗi giống {label}: {match.group(0)[:20]}..."
            if match else ""
        )


def test_all_referenced_backend_paths_exist(doc_text):
    """Mọi đường dẫn `app/...` trích trong tài liệu phải tồn tại."""
    referenced = set(re.findall(r"`(app/[A-Za-z0-9_/\.]+\.py)`", doc_text))
    assert referenced, "Tài liệu không trích dẫn file backend nào — có vẻ sai chỗ"

    missing = []
    for ref in sorted(referenced):
        if not (BACKEND / ref).exists():
            missing.append(ref)
    assert not missing, "Tài liệu trích dẫn file không tồn tại:\n  " + "\n  ".join(missing)


def test_all_referenced_frontend_paths_exist(doc_text):
    """Mọi đường dẫn `frontend/src/...` phải tồn tại."""
    referenced = set(re.findall(r"`(frontend/src/[A-Za-z0-9_/\.]+\.tsx?)`", doc_text))
    assert referenced, "Tài liệu không trích dẫn file frontend nào"

    missing = []
    for ref in sorted(referenced):
        if not (ROOT_DIR / ref).exists():
            missing.append(ref)
    assert not missing, "Tài liệu trích dẫn file frontend không tồn tại:\n  " + "\n  ".join(missing)


def test_all_referenced_test_names_exist(doc_text):
    """Mọi tên test được trích dẫn phải có thật trong bộ test backend.

    Đây là phép kiểm tra quan trọng nhất: tài liệu bảo vệ dựa trên các test cụ thể,
    nên một tên test sai là một tuyên bố không có bằng chứng.
    """
    referenced = set(re.findall(r"`(test_[a-z0-9_]+\.py)::([a-zA-Z0-9_]+)`", doc_text))
    assert referenced, "Tài liệu không trích dẫn test cụ thể nào theo dạng file::test"

    all_test_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (BACKEND / "tests").rglob("test_*.py")
    )

    missing = []
    for filename, funcname in sorted(referenced):
        if f"def {funcname}(" not in all_test_text:
            missing.append(f"{filename}::{funcname}")

    assert not missing, (
        "Tài liệu trích dẫn test không tồn tại:\n  " + "\n  ".join(missing)
    )


def test_referenced_test_files_exist(doc_text):
    """Mọi tên file test được nhắc tới phải tồn tại trong `backend/tests/`."""
    referenced = set(re.findall(r"`(test_[a-z0-9_]+\.py)`", doc_text))
    assert referenced, "Tài liệu không nhắc tới file test nào"

    missing = [
        ref for ref in sorted(referenced)
        if not (BACKEND / "tests" / ref).exists()
        and not any((BACKEND / "tests").rglob(ref))
    ]
    assert not missing, "Tài liệu nhắc tới file test không tồn tại:\n  " + "\n  ".join(missing)


def test_referenced_docs_exist(doc_text):
    """Liên kết nội bộ trong tài liệu phải dẫn tới file có thật."""
    referenced = set(re.findall(r"\]\(([A-Z_]+\.md)\)", doc_text))
    for ref in sorted(referenced):
        assert (ROOT_DIR / "docs" / ref).exists(), (
            f"Tài liệu liên kết tới docs/{ref} nhưng file không tồn tại"
        )


def test_key_claims_match_code_behaviour():
    """Ba tuyên bố trụ cột của tài liệu phải đúng với mã nguồn hiện tại.

    Đây là các mệnh đề dễ trôi chảy theo thời gian nhất: người khác sửa code và
    quên cập nhật tài liệu.
    """
    # 1. `is_fallback` và `model_provider` phải còn tồn tại trong hợp đồng schema.
    schemas = (BACKEND / "app" / "schemas" / "schemas.py").read_text(encoding="utf-8")
    assert "is_fallback" in schemas, (
        "Tài liệu nói 'mọi phản hồi AI mang cờ is_fallback' nhưng schema không còn trường này."
    )

    # 2. `compliance_score` phải Optional (không còn mặc định 100).
    assert "compliance_score: Optional[int]" in schemas, (
        "Tài liệu mục 3 nói compliance_score được đo thật và có thể là None; "
        "schema đang khai báo khác."
    )
    assert "compliance_score: int = 100" not in schemas, (
        "compliance_score lại quay về mặc định 100 — tuyên bố ở tài liệu mục 3 "
        "không còn đúng."
    )

    # 3. Cơ chế chấm điểm phải tồn tại trong router AI.
    ai_router = (BACKEND / "app" / "api" / "v1" / "ai.py").read_text(encoding="utf-8")
    assert "_score_omnichannel_compliance" in ai_router, (
        "Tài liệu mục 3 trích dẫn _score_omnichannel_compliance nhưng hàm không còn trong ai.py."
    )

    # 4. AI Doctor phải còn cờ dữ liệu thưa.
    doctor = (BACKEND / "app" / "services" / "ai" / "ai_doctor.py").read_text(encoding="utf-8")
    assert "is_sparse_data" in doctor, (
        "Tài liệu mục 5 nói AI Doctor cảnh báo dữ liệu thưa; cờ is_sparse_data không còn."
    )

    # 5. Trình soạn thảo thủ công phải tồn tại — đó là bằng chứng cho luận điểm
    #    "người không dùng AI vẫn làm được việc".
    composer = FRONTEND / "src" / "components" / "ManualContentComposer.tsx"
    assert composer.exists(), (
        "Tài liệu mục 10 dẫn tới ManualContentComposer.tsx nhưng file không tồn tại."
    )
    assert "không có bước sinh nội dung tự động" in composer.read_text(encoding="utf-8").lower(), (
        "Trình soạn thảo thủ công phải nói rõ với người dùng rằng không dùng AI."
    )


def test_document_is_linked_from_docs_index():
    """Tài liệu phải được liệt kê trong mục lục, nếu không sẽ không ai tìm thấy."""
    index = (ROOT_DIR / "docs" / "README.md").read_text(encoding="utf-8")
    assert "AI_ETHICS_AND_HUMAN_OVERSIGHT.md" in index, (
        "docs/README.md chưa liên kết tới AI_ETHICS_AND_HUMAN_OVERSIGHT.md — "
        "tài liệu sẽ không ai đọc."
    )


def test_document_is_linked_from_root_readme():
    """README gốc phải dẫn tới tài liệu."""
    readme = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
    assert "AI_ETHICS_AND_HUMAN_OVERSIGHT.md" in readme, (
        "README.md chưa liên kết tới AI_ETHICS_AND_HUMAN_OVERSIGHT.md."
    )