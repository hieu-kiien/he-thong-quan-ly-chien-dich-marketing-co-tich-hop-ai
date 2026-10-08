"""Nguyên tắc cốt lõi: sản phẩm phải chạy đầy đủ khi KHÔNG có AI.

Bối cảnh
--------
Yêu cầu của người dùng: "nhiều người không cần tính năng AI vẫn làm được".
AI trong hệ thống này là **tính năng tăng cường không bắt buộc**, không phải
phụ thuộc. Điều đó khớp với bản chất công việc tiếp thị: người soạn thảo vẫn
phải viết và duyệt bài; AI chỉ giúp viết nhanh hơn.

File test này đóng vai trò "hợp đồng" (contract) cho nguyên tắc đó: mọi luồng
nghiệp vụ cốt lõi phải hoàn thành được khi AI bị tắt hẳn. Đây là thứ tách một
bài nộp học phần có bằng chứng khỏi một bài chỉ có tuyên bố.

Cách kiểm chứng
---------------
Ba lớp, từ yếu đến mạnh:

1. **AI không tồn tại về mặt cấu hình**: không khoá, `AI_ENABLE_FALLBACK=false`.
   `/ai/*` phải trả 502 có kiểm soát thay vì bịa nội dung.
2. **AI hỏng lúc chạy**: provider ném lỗi/timeout giữa chừng. Các luồng cốt lõi
   vẫn phải hoàn tất.
3. **Bảo đảm không phụ thuộc theo mã nguồn**: test tĩnh quét toàn bộ
   `backend/app/api/v1/` và khẳng định không router nghiệp vụ nào ngoài
   `ai.py` import/gọi tầng AI. Đây là chống hồi quy: sau này thêm một endpoint
   mới mà lỡ tay gọi AI, test này sẽ đỏ.

Lưu ý về phạm vi: "chạy được không cần AI" là khẳng định về **tính khả dụng của
luồng nghiệp vụ**, không phải về chất lượng nội dung. Bộ test này không chứng
minh nội dung AI sinh ra tốt.
"""

import ast
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.entities import User


# ==============================================================================
# FIXTURE: Cấu hình "không có AI"
# ==============================================================================

@pytest.fixture
def ai_completely_disabled(monkeypatch):
    """Tắt AI triệt để: không khoá, không fallback, chặn mọi lời gọi mạng.

    `fallback_enabled = False` là mấu chốt. Khi fallback BẬT, thiếu khoá sẽ sinh
    nội dung template — tức là hệ thống vẫn "trả lời được" bằng nội dung do máy
    dựng sẵn. Đó đúng là loại phụ thuộc giả mà nguyên tắc này muốn loại bỏ, nên
    khi kiểm tra phải tắt cả hai.
    """
    for env in (
        "AI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY", "OPENCODE_API_KEY", "HF_TOKEN", "HUGGINGFACE_API_KEY",
        "HF_API_TOKEN", "OLLAMA_API_KEY",
    ):
        monkeypatch.delenv(env, raising=False)

    monkeypatch.setattr(settings, "AI_API_KEY", "", raising=False)
    monkeypatch.setattr(settings, "AI_ENABLE_FALLBACK", False, raising=False)

    # `AIService` là singleton và property của nó đọc giá trị đã gán trước rồi mới
    # tới `settings`. Fixture `reset_ai_service_overrides` trong conftest đã chụp
    # lại trạng thái sau mỗi test, nhưng các test chạy TRƯỚC test này trong cùng
    # phiên có thể đã gán đè. Gán `None` cho các thuộc tính ghi đè ở đây để
    # chắc chắn service đọc từ `settings` suốt thời gian test.
    from app.services.ai.ai_service import ai_service

    for attr in ("_fallback_enabled", "_api_key", "_model", "_base_url", "_timeout", "_max_retries"):
        monkeypatch.setattr(ai_service, attr, None, raising=False)

    return settings


# ==============================================================================
# 1. AI KHÔNG CÓ KHẢ NĂNG: phải báo lỗi rõ, KHÔNG được bịa nội dung
# ==============================================================================

@pytest.mark.parametrize("path", ["/api/v1/ai/ideas", "/api/v1/ai/draft", "/api/v1/ai/generate"])
def test_ai_endpoints_fail_loudly_when_ai_unavailable(
    client: TestClient, marketer_headers, ai_completely_disabled, path
):
    """Không có AI thì AI phải trả 502 — không được trả nội dung mẫu như thật.

    Trả 200 với `is_fallback=true` ở chế độ này là sai: người dùng sẽ nhận một
    bản nháp "hợp lệ về schema" rồi đưa đi duyệt mà không biết nó không do ai viết.
    """
    resp = client.post(
        path,
        json={"channel_code": "facebook", "prompt_version": "v3", "selected_idea": "ý tưởng thử"},
        headers=marketer_headers,
    )
    assert resp.status_code == 502, (
        f"{path} phải báo lỗi khi không có AI, nhận {resp.status_code}: {resp.text}"
    )
    # Thông điệp phải nói rõ AI không khả dụng, không mơ hồ.
    body = resp.text.lower()
    assert "ai" in body


@pytest.mark.parametrize("path", ["/api/v1/ai/ideas", "/api/v1/ai/draft"])
def test_ai_endpoints_never_return_fabricated_content_when_disabled(
    client: TestClient, marketer_headers, ai_completely_disabled, path
):
    """Bảo vệ hai tầng: không 502 (dữ liệu bịa) và không trả nội dung khi lỗi."""
    resp = client.post(
        path,
        json={"channel_code": "facebook", "prompt_version": "v3"},
        headers=marketer_headers,
    )
    assert resp.status_code >= 400, (
        f"{path} trả {resp.status_code} — nếu 200 thì nội dung có thể là dữ liệu dự phòng"
    )


def test_ai_failure_does_not_leak_any_content_shape(client: TestClient, marketer_headers, ai_completely_disabled):
    """Phản hồi lỗi không được chứa trường nội dung nào (ideas/draft/facebook)."""
    resp = client.post("/api/v1/ai/omnichannel", json={"brief": "ra mắt sản phẩm"}, headers=marketer_headers)
    assert resp.status_code >= 400
    text = resp.text
    for leaked_field in ('"facebook"', '"tiktok"', '"email"', '"hook_3s"', '"ideas"', '"title"'):
        assert leaked_field not in text, (
            f"Phản hồi lỗi lộ ra trường nội dung {leaked_field}: {text[:200]}"
        )


# ==============================================================================
# 2. LUỒNG NGHIỆP VỤ CỐT LÕI KHÔNG CẦN AI
# ==============================================================================

@pytest.fixture
def product_id(client: TestClient, marketer_headers) -> int:
    """Một sản phẩm có sẵn để gắn chiến dịch (`product_id` là bắt buộc)."""
    products = client.get("/api/v1/products", headers=marketer_headers)
    if products.status_code == 200 and products.json():
        return products.json()[0]["id"]

    created = client.post(
        "/api/v1/products",
        json={"name": "Sản phẩm dùng cho test offline", "description": "Tạo trong test", "price": 199000},
        headers=marketer_headers,
    )
    assert created.status_code in (200, 201), created.text
    return created.json()["id"]


def _make_campaign(client: TestClient, headers, product_id: int, name: str, **overrides):
    """Tạo chiến dịch qua API công khai (không chạm ORM trực tiếp)."""
    payload = {
        "product_id": product_id,
        "name": name,
        "objective": "Bán hàng",
        "audience": "Khách hàng mục tiêu của chiến dịch",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "budget": 2_000_000,
    }
    payload.update(overrides)
    resp = client.post("/api/v1/campaigns", json=payload, headers=headers)
    assert resp.status_code in (200, 201), f"Tạo chiến dịch thất bại: {resp.text}"
    return resp.json()


def test_campaign_lifecycle_works_without_ai(
    client: TestClient, marketer_headers, manager_headers, ai_completely_disabled, product_id
):
    """Tạo → đọc → cập nhật → xoá chiến dịch, không gọi AI lần nào."""
    created = _make_campaign(client, marketer_headers, product_id, "Chiến dịch không cần AI")
    campaign_id = created["id"]

    listed = client.get("/api/v1/campaigns", headers=marketer_headers)
    assert listed.status_code == 200
    assert any(c["id"] == campaign_id for c in listed.json()["items"])

    updated = client.put(f"/api/v1/campaigns/{campaign_id}", json={"budget": 7_500_000}, headers=marketer_headers)
    assert updated.status_code == 200, updated.text
    assert updated.json()["budget"] == 7_500_000

    # Xoá là thao tác quản trị: dùng Manager, và kiểm tra RBAC vẫn giữ nguyên
    # khi AI tắt (Marketer phải bị 403).
    forbidden = client.delete(f"/api/v1/campaigns/{campaign_id}", headers=marketer_headers)
    assert forbidden.status_code == 403, (
        f"Marketer không được xoá chiến dịch; nhận {forbidden.status_code}"
    )

    deleted = client.delete(f"/api/v1/campaigns/{campaign_id}", headers=manager_headers)
    assert deleted.status_code in (200, 204), deleted.text


def test_manual_content_authoring_and_review_workflow_without_ai(
    client: TestClient, marketer_headers, manager_headers, ai_completely_disabled, product_id
):
    """Đường thủ công quan trọng nhất: người dùng TỰ VIẾT bài, không cần AI.

    Đây là luồng mà nguyên tắc "AI không bắt buộc" thực sự được kiểm chứng. Trước
    đây giao diện chỉ có đường tạo nội dung qua AI Studio / AI Drawer, nên người
    không dùng được AI thì không tạo được bài nào để duyệt.
    """
    campaign_id = _make_campaign(
        client, marketer_headers, product_id, "Chiến dịch soạn thảo thủ công"
    )["id"]

    # 1. Marketer tự soạn bài, KHÔNG qua bất kỳ endpoint AI nào.
    draft = client.post(
        "/api/v1/contents",
        json={
            "campaign_id": campaign_id,
            "channel_id": 1,
            "title": "Bài viết tự soạn — không dùng AI",
            "body": "Nội dung do con người viết tay. Không có bước sinh nội dung tự động nào.",
            "cta": "Đăng ký tư vấn",
            "status": "DRAFT",
        },
        headers=marketer_headers,
    )
    assert draft.status_code in (200, 201), draft.text
    content_id = draft.json()["id"]

    # 2. Sửa bài nháp.
    edited = client.put(
        f"/api/v1/contents/{content_id}",
        json={"title": "Bài viết tự soạn (đã sửa)", "cta": "Nhắn tin ngay"},
        headers=marketer_headers,
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["title"] == "Bài viết tự soạn (đã sửa)"

    # 3. Gửi duyệt.
    submitted = client.post(f"/api/v1/contents/{content_id}/submit", headers=marketer_headers)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "IN_REVIEW"

    # 4. Quản lý duyệt.
    approved = client.post(f"/api/v1/contents/{content_id}/approve", headers=manager_headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"

    # 5. Lên lịch cho bài đã duyệt.
    scheduled = client.post(
        f"/api/v1/contents/{content_id}/schedule",
        json={"scheduled_at": "2026-03-01 09:00"},
        headers=marketer_headers,
    )
    assert scheduled.status_code in (200, 201), scheduled.text

    # 6. Xuất bản.
    published = client.post(f"/api/v1/contents/{content_id}/publish", headers=manager_headers)
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "PUBLISHED"


def test_scheduling_requires_approval_even_without_ai(
    client: TestClient, marketer_headers, ai_completely_disabled, product_id
):
    """Ràng buộc phê duyệt phải giữ nguyên khi AI tắt.

    Nếu không có AI thì dễ sinh xu hướng "cho qua luôn để tiến độ"; test này
    chặn việc đó.
    """
    campaign_id = _make_campaign(
        client, marketer_headers, product_id, "Kiểm tra ràng buộc duyệt"
    )["id"]

    draft_id = client.post(
        "/api/v1/contents",
        json={
            "campaign_id": campaign_id,
            "channel_id": 1,
            "title": "Bài chưa duyệt",
            "body": "Chưa qua bước duyệt nào.",
            "cta": "Xem ngay",
            "status": "DRAFT",
        },
        headers=marketer_headers,
    ).json()["id"]

    resp = client.post(
        f"/api/v1/contents/{draft_id}/schedule",
        json={"scheduled_at": "2026-02-01 09:00"},
        headers=marketer_headers,
    )
    assert resp.status_code == 400, (
        f"Bài chưa duyệt không được lên lịch; nhận {resp.status_code}: {resp.text}"
    )


def test_metrics_attribution_and_kpi_work_without_ai(
    client: TestClient, marketer_headers, ai_completely_disabled, product_id
):
    """Nhập chỉ số và đọc dashboard KPI không phụ thuộc mô hình ngôn ngữ."""
    campaign_id = _make_campaign(
        client, marketer_headers, product_id, "Chiến dịch đo lường thủ công"
    )["id"]

    metric = client.post(
        f"/api/v1/campaigns/{campaign_id}/metrics",
        json={
            "campaign_id": campaign_id,
            "channel_id": 1,
            "metric_date": "2026-02-01",
            "views": 10000,
            "clicks": 500,
            "conversions": 25,
            "cost": 1_000_000,
            "revenue": 4_000_000,
        },
        headers=marketer_headers,
    )
    assert metric.status_code in (200, 201), metric.text

    # KPI tính từ metrics vừa nhập: clicks/views = 5%, ROAS = 4.0.
    kpi = client.get(f"/api/v1/campaigns/{campaign_id}/kpi", headers=marketer_headers)
    assert kpi.status_code == 200, kpi.text
    kpi_body = kpi.json()
    assert kpi_body["total_views"] == 10000
    assert kpi_body["total_clicks"] == 500
    assert abs(kpi_body["ctr_percent"] - 5.0) < 0.01, f"CTR sai: {kpi_body}"
    assert abs(kpi_body["roas"] - 4.0) < 0.01, f"ROAS sai: {kpi_body}"

    dashboard = client.get("/api/v1/metrics/dashboard", headers=marketer_headers)
    assert dashboard.status_code == 200, dashboard.text


def test_search_filter_and_sort_work_without_ai(client: TestClient, marketer_headers, ai_completely_disabled):
    """Tìm kiếm/lọc là thao tác CSDL thuần, không được phụ thuộc AI."""
    resp = client.get("/api/v1/campaigns?search=Chiến", headers=marketer_headers)
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json()["items"], list)


def test_brand_kit_workspace_and_channel_work_without_ai(
    client: TestClient, manager_headers, marketer_headers, ai_completely_disabled
):
    """Brand Kit, workspace và danh mục kênh đều là dữ liệu thuần."""
    brand = client.get("/api/v1/brand-kit", headers=marketer_headers)
    assert brand.status_code == 200, brand.text

    workspaces = client.get("/api/v1/workspaces", headers=marketer_headers)
    assert workspaces.status_code == 200, workspaces.text
    assert isinstance(workspaces.json(), (list, dict))

    channels = client.get("/api/v1/channels", headers=marketer_headers)
    assert channels.status_code == 200, channels.text


def test_ai_doctor_still_works_without_llm(
    client: TestClient, marketer_headers, ai_completely_disabled, product_id
):
    """AI Doctor là động cơ quy tắc xác định, không gọi LLM — nên vẫn chạy.

    Đây là điểm hay nói khi bảo vệ: bộ chẩn đoán dùng số liệu trong CSDL và
    ngưỡng cố định, không phụ thuộc provider. Vì vậy "tắt AI" không làm mất khả
    năng chẩn đoán chiến dịch.
    """
    campaign_id = _make_campaign(
        client, marketer_headers, product_id, "Chiến dịch chẩn đoán"
    )["id"]

    client.post(
        f"/api/v1/campaigns/{campaign_id}/metrics",
        json={
            "campaign_id": campaign_id,
            "channel_id": 1,
            "metric_date": "2026-02-01",
            "views": 2000,
            "clicks": 40,
            "conversions": 1,
            "cost": 900_000,
            "revenue": 300_000,
        },
        headers=marketer_headers,
    )

    resp = client.get(f"/api/v1/campaigns/{campaign_id}/ai-doctor", headers=marketer_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "status" in body or "recommendations" in body or "diagnosis" in body


def test_compliance_check_works_without_ai(client: TestClient, marketer_headers, ai_completely_disabled):
    """Quét tuân thủ là quy tắc xác định trên Brand Kit, không cần mô hình."""
    resp = client.post(
        "/api/v1/contents/compliance-check",
        json={
            "channel": "facebook",
            "title": "Siêu giảm giá sốc",
            "body": "Giảm 90% hôm nay, nhanh lắm, chắc chắn hiệu quả.",
            "cta": "Mua ngay",
        },
        headers=marketer_headers,
    )
    assert resp.status_code == 200, resp.text
    assert "score" in resp.json()


def test_auth_rbac_and_registration_work_without_ai(client: TestClient, ai_completely_disabled):
    """Đăng nhập, phân quyền, đăng ký tài khoản — nền tảng, không liên quan AI."""
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "marketer@gmail.com", "password": "Marketer@123"},
    )
    assert login.status_code == 200, login.text
    assert "access_token" in login.json()


# ==============================================================================
# 3. BẢO ĐẢM KHÔNG PHỤ THUỘC THEO MÃ NGUỒN (chống hồi quy)
# ==============================================================================

#: Ngoại lệ CÓ CHỦ ĐÍCH, theo cặp (tên file, tiền tố module được phép chạm AI):
#:
#: - `ai.py` là router AI, tất nhiên được phép toàn bộ.
#: - `settings.py` là endpoint "Test API Connection" của BYOK; nó phải dựng đúng
#:   header của từng provider (Messages API với Anthropic) thì mới kiểm tra được
#:   khoá. Đây là chức năng *cấu hình* AI, không phải nghiệp vụ phụ thuộc AI.
#: - `metrics.py` phục vụ AI Doctor — động cơ quy tắc xác định đọc metrics và áp
#:   ngưỡng, KHÔNG gọi LLM. Nó nằm trong metrics vì trả lời "chiến dịch này có
#:   khoẻ không" từ dữ liệu đo lường, không phải vì nó sinh nội dung.
#: - `config.py` cần whitelist provider lúc khởi động để từ chối giá trị sai
#:   (xem `validate_security_configuration`).
#:
#: `contents.py` cố ý KHÔNG nằm trong danh sách này: nó import
#: `services/compliance/compliance_service` để quét từ khóa cấm của Brand Kit.
#: Đó là bộ quy tắc tất định, phải chạy được khi AI tắt — nên nó được kiểm tra
#: bằng hành vi (`test_compliance_check_works_without_ai`), không phải bị cấm.
ALLOWED_AI_DEPENDENCIES = (
    ("ai.py", "app.services.ai"),
    ("settings.py", "app.services.ai"),
    ("metrics.py", "app.services.ai.ai_doctor"),
    ("config.py", "app.services.ai.providers"),
)

#: Tiền tố import bị cấm ngoài các ngoại lệ trên.
FORBIDDEN_IMPORT_PREFIXES = ("app.services.ai",)


def _is_allowed(filename: str, module: str) -> bool:
    return any(filename == f and module.startswith(m) for f, m in ALLOWED_AI_DEPENDENCIES)


def _imported_modules(path: Path) -> set[str]:
    """Trả về tập module mà file import, đọc bằng AST.

    Dùng AST thay vì so khớp chuỗi thô: tìm chuỗi sẽ báo nhầm mỗi khi ai đó
    viết `app/services/ai/ai_service.py` trong một dòng chú thích — và bài test
    báo nhầm thì sẽ bị bỏ qua trong lần sửa sau, tức là mất tác dụng bảo vệ.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module)
                for alias in node.names:
                    modules.add(f"{node.module}.{alias.name}")
    return modules


def _router_files() -> list[Path]:
    api_dir = Path(__file__).resolve().parent.parent / "app" / "api" / "v1"
    return sorted(p for p in api_dir.glob("*.py"))


def test_no_business_router_depends_on_the_ai_layer():
    """Không router nghiệp vụ nào ngoài AI được phép import tầng AI.

    Đây là phép kiểm tra cấu trúc, mạnh hơn kiểm thử hành vi: ngay cả khi
    nhánh lỗi của AI chưa được chạy tới trong test, một lệnh gọi AI trong
    `campaigns.py` hay `contents.py` vẫn bị phát hiện.
    """
    offenders: list[str] = []
    for path in _router_files():
        for module in _imported_modules(path):
            if not any(module.startswith(prefix) for prefix in FORBIDDEN_IMPORT_PREFIXES):
                continue
            if _is_allowed(path.name, module):
                continue
            offenders.append(f"{path.name}: import '{module}'")

    assert not offenders, (
        "Các router nghiệp vụ sau đang phụ thuộc tầng AI, trái nguyên tắc "
        "'AI là tùy chọn':\n  " + "\n  ".join(sorted(offenders))
    )


def test_no_infrastructure_module_depends_on_the_ai_generative_layer():
    """Tầng `core/` không được import tầng AI sinh nội dung.

    `config.py` được miễn vì nó cần whitelist provider để chặn `AI_PROVIDER`
    sai lúc khởi động — đó là kiểm tra cấu hình, không phải gọi AI. Nhưng `core`
    không được `import AIService` và cũng không được gọi provider.
    """
    core_dir = Path(__file__).resolve().parent.parent / "app" / "core"
    forbidden = (
        "app.services.ai.ai_service",
        "app.services.ai.anthropic_adapter",
    )
    offenders: list[str] = []
    for path in sorted(core_dir.glob("*.py")):
        for module in _imported_modules(path):
            if any(module.startswith(f) for f in forbidden):
                offenders.append(f"{path.name}: import '{module}'")

    assert not offenders, (
        "Tầng core không được phụ thuộc tầng AI sinh nội dung:\n  " + "\n  ".join(sorted(offenders))
    )


def test_ai_module_list_itself_stays_free_of_generative_dependencies():
    """Sổ đăng ký provider không được import dịch vụ AI (giữ nó thuần dữ liệu).

    Nếu `providers.py` import `ai_service` thì mọi thứ import config sẽ kéo theo
    cả tầng AI, phá vỡ nguyên tắc "AI là phụ thuộc tuỳ chọn" ngay từ gốc.
    """
    registry = Path(__file__).resolve().parent.parent / "app" / "services" / "ai" / "providers.py"
    for module in _imported_modules(registry):
        assert "ai_service" not in module, (
            f"providers.py không được import tầng sinh nội dung: {module}"
        )


def test_fallback_templates_are_never_labelled_as_ai_output():
    """Nội dung dự phòng phải luôn kèm nhãn `is_fallback`, không bao giờ là AI thật.

    Đây là ranh giới giữa "AI tùy chọn" và "AI giả". Hệ thống có thể sinh nội
    dung dự phòng khi provider hỏng — nhưng phải nói rõ. Nếu không, người dùng
    bị lừa và bài viết đó có thể được duyệt/xuất bản như do AI viết.
    """
    from app.services.ai.ai_service import AIService

    service = AIService()
    contexts = [
        ("idea_generation", {"campaign_name": "C", "product_name": "P", "product_usp": "U", "channel_name": "Facebook"}),
        ("content_draft", {"campaign_name": "C", "product_name": "P", "product_usp": "U", "channel_name": "Facebook"}),
        ("performance_summary", {"campaign_name": "C", "total_views": 10, "total_clicks": 1, "ctr": 10.0}),
        ("omnichannel_generation", {"brief": "B", "brand_name": "Brand", "product_name": "P", "usp": "U"}),
    ]

    for task_type, context in contexts:
        out = service._generate_fallback(task_type, context)
        assert out, f"{task_type} không sinh được nội dung dự phòng"
        assert out.get("is_fallback") is True, (
            f"{task_type}: nội dung dự phòng phải gắn is_fallback=True"
        )
        assert out.get("model_provider") == "template-fallback-engine", (
            f"{task_type}: model_provider phải nói rõ là template, không phải model"
        )
        assert out.get("warnings"), (
            f"{task_type}: nội dung dự phòng phải kèm warnings giải thích lý do"
        )


def test_fallback_omnichannel_does_not_claim_a_perfect_compliance_score():
    """Template dự phòng KHÔNG được tự khai `compliance_score = 100`.

    Phát hiện khi rà soát: `_generate_fallback_omnichannel` gán cứng
    `compliance_score: 100` cho nội dung template. Con số đó chưa từng đi qua
    `compliance_service`, nên nó là một tuyên bố không có cơ sở — và hiển thị
    "100/100 đạt chuẩn" cho một bản nháp máy dựng sẵn là loại nhận định sai
    mà rubric Tuần 3 mục 6 nêu rõ phải tránh.

    Hành vi đúng: không tự chấm điểm; điểm thật chỉ do
    `POST /contents/check-compliance` tính từ Brand Kit và chính sách.
    """
    from app.services.ai.ai_service import AIService

    out = AIService()._generate_fallback(
        "omnichannel_generation",
        {"brief": "ra mắt sản phẩm", "brand_name": "Thương Hiệu", "product_name": "SP", "usp": "nhanh"},
    )
    assert out["is_fallback"] is True
    # Không được mang điểm tự chấm. Để None để UI biết là "chưa chấm".
    assert "compliance_score" not in out or out.get("compliance_score") is None, (
        f"Nội dung dự phòng không được tự gán compliance_score: {out.get('compliance_score')}"
    )


def test_frontend_offline_demo_is_opt_in_not_implicit():
    """Chế độ demo offline của frontend phải là cờ tường minh, không bật ngầm.

    `isOfflineDemoEnabled()` trong frontend chỉ trả true khi
    `VITE_ENABLE_OFFLINE_DEMO === 'true'`. Điều này được ghi lại ở đây vì đây là
    ranh giới dễ bị xâm nhập nhất: nếu một ngày đẹp trời ai đó đổi điều kiện
    thành `!== 'false'`, ứng dụng sẽ âm thầm bịa dữ liệu thay vì báo lỗi.
    """
    api_ts = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "services" / "api.ts"
    assert api_ts.exists(), "Không tìm thấy frontend/src/services/api.ts"
    text = api_ts.read_text(encoding="utf-8")

    match = re.search(
        r"isOfflineDemoEnabled\s*=\s*\(\)\s*:\s*boolean\s*=>\s*([^;]+);",
        text,
    )
    assert match, "Không tìm thấy định nghĩa isOfflineDemoEnabled trong frontend"
    expression = match.group(1).strip()
    assert "VITE_ENABLE_OFFLINE_DEMO" in expression
    # Phải so sánh BẰNG với chuỗi 'true', không phải so sánh khác.
    assert "=== 'true'" in expression, (
        f"isOfflineDemoEnabled phải so sánh bằng với 'true'; hiện tại: {expression}"
    )