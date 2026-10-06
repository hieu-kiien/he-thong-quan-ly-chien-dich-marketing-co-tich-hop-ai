"""
Giao diện khong duoc quang cao mot ten model AI cu the
=====================================================

Vien canh
---------
AI trong he thong nay la **da nha cung cap**. Nguoi dung tu chon provider va model
trong trang Cai dat (BYOK), va backend tra ve `model_provider` / `model_used` de
giao dien hien thi dung nguon goc.

Nhung truoc day nhieu cho trong giao dien ghi cung mot ten model:

    "Model: Gemini 2.5 Flash - Production: marketflow-7vt.pages.dev"
    "1-Click Sang tao Da kenh (R2 - Gemini 2.5 Flash)"
    "Gemini 2.5 Flash se tu dong tao bai viet Facebook..."

Ca hai deu sai:

1. **Sai ve nguon goc.** Production chay `opencode / space-bunny-free`. Neu nguoi
   dung doi provider sang Anthropic roi Ollama, giao dien van khoe "Gemini 2.5
   Flash". Day chinh la tinh huong ma Bài 3 muc 10 ganh: "khong gay nham lan".
   Nguoi dung tin nhanh hon chinh xac, roi dung nhanh hon de quyet dinh.
2. **Sai ve mien trien khai.** `marketflow-7vt.pages.dev` la ten Cloudflare Pages
   cu. Frontend hien tai nam tren Cloudflare Worker tai `marketing.kienhieu.id.vn`.

Quy tac cua file nay
--------------------
1. KHONG `pytest.skip`.
2. Chi quet nhung file .tsx/.ts DUOC TAI LUU VAO BUNDLE -- dung file test thi
   duoc phep chua ten model vi no kiem tra bang chung.
3. Danh sach file duoc phep co ten model phai duoc khai bao ro rang, kem ly do.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = REPO_ROOT / "frontend" / "src"

# File duoc phep chua ten model vi ly do cu the.
#   Settings.tsx: danh muc model nguoi dung chon trong dropdown -- bat buoc phai
#                 liet ke model that.
#   AIStudio.tsx : ghi chu mo ta lich su cua mot bua sua UI da lam; xem mucc 2.
ALLOWED_FILES = {
    "pages/Settings.tsx",
    "pages/AIStudio.tsx",
}

# Ten model / nhan hieu nhu xuat hien trong UI.
MODEL_CLAIM_PATTERNS = {
    "gemini_model": re.compile(r"Gemini\s*\d", re.IGNORECASE),
    "gpt_model": re.compile(r"\bGPT-[\d4]", re.IGNORECASE),
    "claude_model": re.compile(r"Claude\s*[\d3]", re.IGNORECASE),
    "space_bunny": re.compile(r"space-bunny", re.IGNORECASE),
}

# Ten mien trien khai da liet ke trong README.
RETIRED_DOMAINS = ("pages.dev",)


@pytest.fixture(scope="module")
def frontend_source_files():
    """Danh sach (duong dan tuong doi, noi dung) cua file frontend duoc tai len bundle."""
    files = []
    for path in sorted(SRC.rglob("*")):
        if path.suffix not in (".ts", ".tsx"):
            continue
        files.append((path.relative_to(SRC).as_posix(), path.read_text(encoding="utf-8")))
    assert len(files) > 20, (
        f"Chi quet {len(files)} file frontend - co the quet sai pham vi repo."
    )
    return files


@pytest.mark.parametrize("domain", RETIRED_DOMAINS)
def test_no_retired_deployment_domain_in_ui(frontend_source_files, domain):
    """Khong duoc con ten mien cu trong chuoi hien thi cua giao dien."""
    offenders = []
    for rel, text in frontend_source_files:
        for line_no, line in enumerate(text.splitlines(), start=1):
            if domain in line:
                offenders.append(f"{rel}:{line_no}")
    assert not offenders, (
        f"Giao dien con chua ten mien cu '{domain}' (vi du Cloudflare Pages da bi the):\n  - "
        + "\n  - ".join(offenders)
    )


@pytest.mark.parametrize("claim_name,pattern", sorted(MODEL_CLAIM_PATTERNS.items()))
def test_no_hardcoded_model_claim_in_ui(frontend_source_files, claim_name, pattern):
    """Giao dien khong duoc hien thi mot ten model cu the.

    Chi mot so file duoc phep chua ten model, va chi vi ly do duoc ghi o
    ALLOWED_FILES. Moi truong khac phai noi "AI" hoac "nha cung cap theo cau hinh",
    con nguon goc that thi lay tu `model_provider` / `model_used` ma backend tra ve.
    """
    offenders = []
    for rel, text in frontend_source_files:
        if rel in ALLOWED_FILES:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            # Bo qua dong comment: ghi chu giai thich lich su moi duoc phep.
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
                continue
            if pattern.search(line):
                offenders.append(f"{rel}:{line_no}: {stripped[:90]}")

    assert not offenders, (
        f"Tim thay tuyen bien ten model ({claim_name}) trong giao dien:\n  - "
        + "\n  - ".join(offenders)
        + "\n\nGiao dien phai noi chung ('AI', 'nha cung cap theo cau hinh') va lay "
        "nguon goc that tu model_provider / model_used cua backend."
    )


def test_ai_origin_is_displayed_from_backend_response():
    """Can bang chuc nai: hien thi nguon goc AI phai lay tu backend, khong gan cung.

    File nao ghi ten model cung deu sai; nhung cach sua dung la doc
    `model_provider` / `model_used` tu phan hinh cua backend. Neu ca hai truong
    nay bien mat khoi schema hoac khoi giao dien, thay doi cua chung ta se khong
    con giup gi.
    """
    schema = (REPO_ROOT / "backend" / "app" / "schemas" / "schemas.py").read_text(
        encoding="utf-8"
    )
    for field in ("model_provider", "model_used"):
        assert field in schema, (
            f"Schema khong con truong `{field}`. Day la noi giao dien lay ten nha "
            "cung cap that; thieu no thi giao dien chi con cach hien thi ten model "
            "gan cung -- tuc sai."
        )

    ai_studio = (SRC / "pages" / "AIStudio.tsx").read_text(encoding="utf-8")
    assert "model_provider" in ai_studio, (
        "AIStudio.tsx phai doc model_provider tu phan hinh de hien thi nguon goc that."
    )


def test_workflow_canvas_status_bar_states_configurable_provider():
    """Thanh trang thai cua WorkflowCanvas phai noi provider la cau hinh duoc."""
    canvas = (SRC / "components" / "WorkflowCanvas.tsx").read_text(encoding="utf-8")
    assert "c\u1ea5u h\u00ecnh workspace" in canvas, (
        "Thanh trang thai duoi cua WorkflowCanvas phai noi AI dung nha cung cap "
        "theo cau hinh workspace, thay vi gan cung mot ten model."
    )


def test_offline_demo_fixtures_are_labelled_honestly():
    """Du lieu mau cua che do offline demo phai ghi ro KHONG co AI nao chay.

    Khi backend khong tra loi, frontend tra noi dung mau gan san. Do la nguon goc
    thu nam, va nhan phai la `offline-demo-fixture` chu khong phai ten model nao
    ca — neu gan ten model, nguoi dung se tin may da goi API that.
    """
    api_service = (SRC / "services" / "api.ts").read_text(encoding="utf-8")

    assert "OFFLINE_DEMO_PROVIDER = 'offline-demo-fixture'" in api_service, (
        "Phai khai bao OFFLINE_DEMO_PROVIDER = 'offline-demo-fixture' de danh tay "
        "nguon goc du lieu mau."
    )
    assert "OFFLINE_DEMO_MODEL_LABEL" in api_service
    # Nhan hieu du lieu mau phai noi ro khong goi AI.
    label_match = re.search(
        r"OFFLINE_DEMO_MODEL_LABEL\s*=\s*'([^']+)'", api_service
    )
    assert label_match, "Thiếu nhãn cho dữ liệu mẫu cục bộ."
    assert "không gọi AI" in label_match.group(1), (
        f"Nhan du lieu mau phai noi ro '{label_match.group(1)}' co ghi 'không gọi AI' "
        "hay khong, de nguoi dung khong nham noi dung mau la ket qua AI that."
    )
    # Moi phan hinh mau deu phai gan nhan + co is_fallback.
    assert api_service.count("model_provider: OFFLINE_DEMO_PROVIDER") >= 4, (
        "Cac phan hinh trong nhanh offline demo deu phai gan model_provider."
    )
    assert api_service.count("is_fallback: true") >= 4, (
        "Cac phan hinh trong nhanh offline demo deu phai gan is_fallback: true."
    )


def test_frontend_ai_types_declare_fallback_fields():
    """Khai bao TS phai khop hop dong backend.

    Trước đây `AIIdeaResponse` / `AIDraftResponse` / `AISummaryResponse` KHÔNG
    khai báo `is_fallback` và `model_provider`, dù backend luôn trả hai trường
    đó. Hậu quả: giao diên không có cách nào biết nội dung là dự phòng cho ba
    endpoint này — tức là im lặng trong lúc backend cảnh báo.
    """
    types = (SRC / "types" / "index.ts").read_text(encoding="utf-8")

    for name in ("AIIdeaResponse", "AIDraftResponse", "AISummaryResponse"):
        block_match = re.search(
            rf"export interface {name}\s*\{{(.*?)\n\}}", types, re.DOTALL
        )
        assert block_match, f"Khong tim thay interface {name} trong types/index.ts."
        block = block_match.group(1)
        assert "is_fallback" in block, (
            f"{name} phai khai bao `is_fallback`. Backend co tra truong nay; thieu "
            "khai bao thi giao dien khong the hien thi canh bao du phong."
        )
        assert "model_provider" in block, (
            f"{name} phai khai bao `model_provider` de hien thi nguon goc that."
        )

    schema = (REPO_ROOT / "backend" / "app" / "schemas" / "schemas.py").read_text(
        encoding="utf-8"
    )
    for name in ("AIIdeaResponse", "AIDraftResponse", "AISummaryResponse"):
        block_match = re.search(
            rf"class {name}\(BaseModel\):(.*?)(?=\nclass )", schema, re.DOTALL
        )
        assert block_match, f"Khong tim thay class {name} trong schemas.py."
        block = block_match.group(1)
        for field in ("is_fallback", "model_provider"):
            assert field in block, (
                f"Backend schema {name} mat truong `{field}`. Neu bo di, frontend "
                "khong con gi de hien thi nguon goc that cua noi dung AI."
            )
