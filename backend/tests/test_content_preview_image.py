"""
Test Suite: Milestone 4 (R4) - High-Fidelity Social Preview Engine & Action Tools
Comprehensive Unit & Integration Tests covering:
- FEAT-BE-18: MarketingContent image_url field, Pydantic validation, sanitization
- Anti-Tampering: State downgrade on content/image editing for APPROVED & PUBLISHED
- Campaign Content Listing & Export endpoint (GET /campaigns/{id}/contents)
- Zero Migration & SQLite compatibility
- Byte-level Unicode NFC & Emoji preservation for 1-Click Copy
- RBAC record-level access control on campaign contents
"""

import pytest
from fastapi.testclient import TestClient
from app.models.entities import MarketingContent, Campaign, User


def get_auth_headers(client: TestClient, email: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def get_marketer_headers(client: TestClient) -> dict:
    return get_auth_headers(client, "marketer@ictu.edu.vn", "Marketer@123")


def get_manager_headers(client: TestClient) -> dict:
    return get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")


class TestContentPreviewImageUnit:
    """16 chuyên đề kiểm thử toàn diện cho Milestone 4 Backend."""

    def test_01_create_content_with_valid_image_url(self, client: TestClient):
        """1. Tạo content với image_url HTTPS hợp lệ -> 201 Created, image_url lưu đúng."""
        headers = get_marketer_headers(client)
        img_url = "https://images.unsplash.com/photo-1516321318423-f06f85e504b3"
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Chiến dịch Hè 2026",
            "body": "Nội dung bài viết Facebook kèm hình ảnh banner",
            "image_url": img_url,
            "status": "DRAFT"
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["image_url"] == img_url
        assert data["title"] == "Chiến dịch Hè 2026"
        assert data["id"] > 0

    def test_02_create_content_with_ftp_url_handled_safely(self, client: TestClient):
        """2. Tạo content với image_url FTP -> 201 Created, xử lý an toàn không 500 (test_t2_r4_01)."""
        headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Kiểm thử FTP Image URL",
            "body": "Nội dung kiểm thử giao thức FTP",
            "image_url": "ftp://files.example.com/assets/banner.png",
            "status": "DRAFT"
        }, headers=headers)
        assert resp.status_code in (201, 422)
        if resp.status_code == 201:
            assert resp.json()["image_url"] == "ftp://files.example.com/assets/banner.png"

    def test_03_create_content_without_image_defaults_none(self, client: TestClient):
        """3. Tạo content không có image_url -> mặc định None sạch sẽ (test_t2_r4_03)."""
        headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết thuần văn bản",
            "body": "Nội dung không đính kèm bất kỳ hình ảnh nào",
            "status": "DRAFT"
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data.get("image_url") is None

    def test_04_create_content_rejects_unsafe_javascript_uri(self, client: TestClient):
        """4. Chặn URI scheme nguy hiểm javascript:... với HTTP 422."""
        headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Tấn công XSS qua image_url",
            "body": "Payload kiểm thử bảo mật",
            "image_url": "javascript:alert(document.cookie)",
            "status": "DRAFT"
        }, headers=headers)
        assert resp.status_code == 422
        assert "không an toàn" in resp.text or "giao thức nguy hiểm" in resp.text

    def test_05_create_content_rejects_oversized_image_url(self, client: TestClient):
        """5. Chặn URL vượt quá 1024 ký tự với HTTP 422."""
        headers = get_marketer_headers(client)
        oversized_url = "https://example.com/images/" + ("a" * 1010) + ".jpg"  # > 1024 chars
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "URL siêu dài",
            "body": "Nội dung kiểm tra biên độ dài URL",
            "image_url": oversized_url,
            "status": "DRAFT"
        }, headers=headers)
        assert resp.status_code == 422

    def test_06_create_content_rejects_oversized_title(self, client: TestClient):
        """6. Chặn tiêu đề vượt quá 255 ký tự với HTTP 422 (test_t2_r4_04)."""
        headers = get_marketer_headers(client)
        oversized_title = "A" * 256
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": oversized_title,
            "body": "Nội dung hợp lệ",
            "status": "DRAFT"
        }, headers=headers)
        assert resp.status_code == 422

    def test_07_update_content_image_url_on_draft(self, client: TestClient):
        """7. Cập nhật image_url trên bài viết DRAFT -> 200 OK, image_url cập nhật, version_no tăng 1."""
        headers = get_marketer_headers(client)
        # Tạo bài viết ban đầu
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết chuẩn bị cập nhật ảnh",
            "body": "Thân bài gốc",
            "status": "DRAFT"
        }, headers=headers)
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]
        v_before = create_resp.json()["version_no"]

        # Cập nhật ảnh mới
        new_img = "https://images.unsplash.com/photo-banner-new.jpg"
        update_resp = client.put(f"/api/v1/contents/{cid}", json={
            "image_url": new_img
        }, headers=headers)
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["image_url"] == new_img
        assert data["version_no"] == v_before + 1
        assert data["status"] == "DRAFT"

    def test_08_update_image_on_approved_resets_to_ai_draft(self, client: TestClient):
        """8. Cập nhật image_url trên bài APPROVED tự động hoàn trả về AI_DRAFT (Anti-Tampering)."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        # 1. Tạo và submit
        c_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết kiểm thử Anti-Tampering",
            "body": "Nội dung chất lượng cao",
            "image_url": "https://example.com/initial.jpg",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = c_resp.json()["id"]
        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)

        # 2. Manager Approve
        appr_resp = client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)
        assert appr_resp.status_code == 200
        assert appr_resp.json()["status"] == "APPROVED"

        # 3. Marketer sửa image_url -> Bắt buộc hạ về AI_DRAFT
        edit_resp = client.put(f"/api/v1/contents/{cid}", json={
            "image_url": "https://example.com/malicious_replaced.jpg"
        }, headers=mkt_headers)
        assert edit_resp.status_code == 200
        assert edit_resp.json()["status"] == "AI_DRAFT"
        assert edit_resp.json()["image_url"] == "https://example.com/malicious_replaced.jpg"

    def test_09_update_image_on_published_resets_to_ai_draft(self, client: TestClient):
        """9. Cập nhật image_url trên bài PUBLISHED tự động hoàn trả về AI_DRAFT."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        c_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết để xuất bản",
            "body": "Nội dung xuất bản chuẩn",
            "image_url": "https://example.com/img1.jpg",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = c_resp.json()["id"]
        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)
        pub_resp = client.post(f"/api/v1/contents/{cid}/publish", headers=mgr_headers)
        assert pub_resp.status_code == 200
        assert pub_resp.json()["status"] == "PUBLISHED"

        # Sửa image_url -> hạ về AI_DRAFT
        edit_resp = client.put(f"/api/v1/contents/{cid}", json={
            "image_url": "https://example.com/img_changed.jpg"
        }, headers=mkt_headers)
        assert edit_resp.status_code == 200
        assert edit_resp.json()["status"] == "AI_DRAFT"

    def test_10_get_content_returns_full_image_url(self, client: TestClient):
        """10. GET /contents/{id} trả về đầy đủ image_url cho Social Preview."""
        headers = get_marketer_headers(client)
        img_url = "https://images.unsplash.com/photo-facebook-card.jpg"
        c_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Xem chi tiết bài viết Social",
            "body": "Khảo sát siêu dữ liệu preview",
            "image_url": img_url,
            "status": "DRAFT"
        }, headers=headers)
        cid = c_resp.json()["id"]

        get_resp = client.get(f"/api/v1/contents/{cid}", headers=headers)
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["image_url"] == img_url
        assert data["title"] == "Xem chi tiết bài viết Social"

    def test_11_get_campaign_contents_endpoint(self, client: TestClient):
        """11. GET /campaigns/{id}/contents trả về danh sách có image_url."""
        mgr_headers = get_manager_headers(client)
        resp = client.get("/api/v1/campaigns/1/contents", headers=mgr_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Seed content 1 có image_url
        c1 = next((c for c in data if c["id"] == 1), None)
        assert c1 is not None
        assert "image_url" in c1

    def test_12_get_campaign_contents_empty_campaign_returns_200(self, client: TestClient):
        """12. GET /campaigns/{id}/contents cho chiến dịch trống trả về [] status 200 (test_t2_r4_05)."""
        mgr_headers = get_manager_headers(client)
        resp = client.get("/api/v1/campaigns/2/contents", headers=mgr_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data == []

    def test_13_get_campaign_contents_not_found(self, client: TestClient):
        """13. GET /campaigns/99999/contents trả về 404 Not Found."""
        mgr_headers = get_manager_headers(client)
        resp = client.get("/api/v1/campaigns/99999/contents", headers=mgr_headers)
        assert resp.status_code == 404
        assert "Chiến dịch không tồn tại" in resp.json()["detail"]

    def test_14_preserves_unicode_emoji_and_linebreaks(self, client: TestClient):
        """14. Bảo toàn nguyên vẹn Unicode emoji và ngắt dòng (test_t1_r4_05, test_t2_r4_02)."""
        headers = get_marketer_headers(client)
        complex_text = "🎉 CHÚC MỪNG!\n\n\t• Điểm 1: Tuyệt vời ✨\n\t• Điểm 2: Tiện ích 🚀\n\nLink: https://ai.vn"
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "🚀 Test Emoji & Format",
            "body": complex_text,
            "image_url": "https://example.com/banner.png",
            "status": "DRAFT"
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["body"] == complex_text
        assert data["title"] == "🚀 Test Emoji & Format"

    def test_15_compliance_check_compatibility_with_image(self, client: TestClient):
        """15. Tương thích với ComplianceScanner (quét tuân thủ an toàn bình thường)."""
        headers = get_marketer_headers(client)
        payload = {
            "workspace_id": 1,
            "channel": "facebook",
            "title": "Khóa học AI chuyên sâu đính kèm hình ảnh",
            "body": "Nâng cao năng lực công nghệ thông tin cùng các chuyên gia hàng đầu."
        }
        resp = client.post("/api/v1/contents/compliance-check", json=payload, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] in ("PASSED", "PASS")

    def test_16_campaign_contents_rbac_authorization(self, client: TestClient):
        """16. Phân quyền truy cập campaign contents: Marketer chỉ thấy nội dung chiến dịch được cấp phép."""
        # Đăng ký tài khoản Marketer mới thuộc workspace khác
        client.post("/api/v1/auth/register", json={
            "email": "external_marketer@agency.com",
            "password": "Password@123",
            "full_name": "External Marketer",
            "role": "MARKETER"
        })
        ext_headers = get_auth_headers(client, "external_marketer@agency.com", "Password@123")

        # Tạo workspace mới cho external marketer
        ws_resp = client.post("/api/v1/workspaces", json={
            "name": "External Workspace",
            "description": "Workspace độc lập"
        }, headers=ext_headers)
        ext_ws_id = ws_resp.json()["id"]

        # Quản lý ICTU tạo campaign trong workspace 1
        mgr_headers = get_manager_headers(client)
        # External marketer thử truy cập campaign thuộc workspace khác (> 1) -> 403
        # Tạo campaign trong workspace 2
        camp_resp = client.post("/api/v1/campaigns", json={
            "workspace_id": ext_ws_id,
            "product_id": 1,
            "name": "Campaign Riêng Của External",
            "objective": "Mục tiêu riêng",
            "audience": "Target",
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
            "budget": 1000000.0
        }, headers=ext_headers)
        ext_camp_id = camp_resp.json()["id"]

        # Marketer ICTU thử đọc contents của campaign thuộc external workspace -> 403
        mkt_headers = get_marketer_headers(client)
        forbidden_resp = client.get(f"/api/v1/campaigns/{ext_camp_id}/contents", headers=mkt_headers)
        assert forbidden_resp.status_code == 403
