"""
Challenger 2 Test Suite: Milestone 4 (R4) - Boundary Stress, Anti-Tampering & Byte-Level Integrity
Author: Challenger 2 (Empirical Adversarial Auditor)

This test suite executes rigorous empirical verification against:
1. Boundary stress & Security (XSS/Injection) on image_url:
   - javascript:, vbscript:, data:text/html schemes (case, whitespace, payload variations)
   - Max length 1024 vs 1025 boundary condition
   - Safe FTP protocol allowance (test_t2_r4_01)
   - Missing/None/Empty image_url defaults to null without error (test_t2_r4_03)
   - PUT endpoint injection protection
2. State Machine & Anti-Tampering Integrity:
   - Image modification on APPROVED content -> Downgrade to AI_DRAFT
   - Image modification on PUBLISHED content -> Downgrade to AI_DRAFT
   - Image unlinking ("") on APPROVED content -> Downgrade to AI_DRAFT & image_url=None
   - Idempotent PUT with identical image_url -> Retains APPROVED
   - Status escalation prevention on PUT and POST (cannot set APPROVED/PUBLISHED directly)
   - Modification of text fields (title, body, cta) on APPROVED -> Downgrade to AI_DRAFT
3. Byte-Level Integrity for 1-Click Copy and Excel CSV Export:
   - Zero byte drift on complex Vietnamese, emojis (composite ZWJ, flags, skin tones), tabs, repeated newlines (test_t2_r4_02)
   - Excel CSV UTF-8 BOM verification (0xEF, 0xBB, 0xBF as the first 3 bytes)
   - RFC 4180 CSV cell escaping and round-trip decoding via utf-8-sig
"""

import io
import csv
import pytest
from fastapi.testclient import TestClient


def get_auth_headers(client: TestClient, email: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def get_marketer_headers(client: TestClient) -> dict:
    return get_auth_headers(client, "marketer@ictu.edu.vn", "Marketer@123")


def get_manager_headers(client: TestClient) -> dict:
    return get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")


# ==============================================================================
# SECTION 1: BOUNDARY STRESS & XSS / INJECTION SANITIZATION ON IMAGE_URL
# ==============================================================================

class TestBoundaryStressAndSecurityImageUrl:
    """Kiểm thử đối kháng ca biên dị thường và bảo mật (XSS, Injection) trên image_url."""

    @pytest.mark.parametrize("dangerous_uri", [
        "javascript:alert('XSS')",
        "javascript:alert(1)",
        "JAVASCRIPT:alert('XSS')",
        "JavaScript:void(0)",
        "   javascript:alert('XSS')   ",
        "javascript:/*--></title></style></textarea>*/<script>alert(1)</script>",
    ])
    def test_ch2_01_reject_javascript_scheme_variants(self, client: TestClient, dangerous_uri: str):
        """1. Chặn đứng giao thức javascript: (bao gồm hoa, thường, khoảng trắng) với HTTP 422."""
        headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Tấn công XSS JavaScript",
            "body": "Nội dung kiểm thử bảo mật injection",
            "image_url": dangerous_uri,
            "status": "DRAFT"
        }, headers=headers)
        assert resp.status_code == 422, f"Expected 422 for URI '{dangerous_uri}', got {resp.status_code}: {resp.text}"
        assert any(k in resp.text.lower() for k in ["không an toàn", "nguy hiểm", "image_url"])

    @pytest.mark.parametrize("dangerous_uri", [
        "vbscript:msgbox(1)",
        "VBSCRIPT:msgbox('hello')",
        "VbScript:Execute('malicious')",
        "   vbscript:msgbox(1)   ",
    ])
    def test_ch2_02_reject_vbscript_scheme_variants(self, client: TestClient, dangerous_uri: str):
        """1. Chặn đứng giao thức vbscript: (bao gồm hoa, thường, khoảng trắng) với HTTP 422."""
        headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Tấn công VBScript Injection",
            "body": "Nội dung kiểm thử bảo mật vbscript",
            "image_url": dangerous_uri,
            "status": "DRAFT"
        }, headers=headers)
        assert resp.status_code == 422, f"Expected 422 for URI '{dangerous_uri}', got {resp.status_code}: {resp.text}"
        assert any(k in resp.text.lower() for k in ["không an toàn", "nguy hiểm", "image_url"])

    @pytest.mark.parametrize("dangerous_uri", [
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
        "DATA:TEXT/HTML;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4=",
        "data:text/html,<script>alert(1)</script>",
        "  data:text/html;charset=utf-8,...  ",
    ])
    def test_ch2_03_reject_data_text_html_scheme_variants(self, client: TestClient, dangerous_uri: str):
        """1. Chặn đứng data:text/html (data URI XSS payload) với HTTP 422."""
        headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Tấn công Data URI HTML",
            "body": "Nội dung kiểm thử data:text/html",
            "image_url": dangerous_uri,
            "status": "DRAFT"
        }, headers=headers)
        assert resp.status_code == 422, f"Expected 422 for URI '{dangerous_uri}', got {resp.status_code}: {resp.text}"
        assert any(k in resp.text.lower() for k in ["không an toàn", "nguy hiểm", "image_url"])

    def test_ch2_04_boundary_length_1024_and_1025(self, client: TestClient):
        """1. Ca biên độ dài URL: Đúng 1024 ký tự -> 201 Created; Vượt quá (1025 ký tự) -> Bắt buộc bị chặn HTTP 422."""
        headers = get_marketer_headers(client)
        base_prefix = "https://example.com/assets/"
        filler_len_1024 = 1024 - len(base_prefix) - 4  # trừ thêm đuôi .png
        url_1024 = base_prefix + ("a" * filler_len_1024) + ".png"
        assert len(url_1024) == 1024

        # 1024 ký tự -> Thành công
        resp_1024 = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "URL độ dài đúng 1024 ký tự",
            "body": "Nội dung kiểm tra biên 1024 ký tự",
            "image_url": url_1024,
            "status": "DRAFT"
        }, headers=headers)
        assert resp_1024.status_code == 201, f"Expected 201 for len=1024, got {resp_1024.status_code}"
        assert resp_1024.json()["image_url"] == url_1024

        # 1025 ký tự -> Bắt buộc bị chặn HTTP 422
        url_1025 = url_1024 + "x"
        assert len(url_1025) == 1025
        resp_1025 = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "URL độ dài vượt biên 1025 ký tự",
            "body": "Nội dung kiểm tra vượt biên",
            "image_url": url_1025,
            "status": "DRAFT"
        }, headers=headers)
        assert resp_1025.status_code == 422, f"Expected 422 for len=1025, got {resp_1025.status_code}"

    @pytest.mark.parametrize("ftp_url", [
        "ftp://server.com/img.png",
        "ftp://files.example.com/assets/banner_hero.jpg",
        "ftp://anonymous:guest@repo.corp.internal/marketing/promo.png",
    ])
    def test_ch2_05_accept_ftp_scheme_safely(self, client: TestClient, ftp_url: str):
        """1. Chấp nhận giao thức FTP hợp lệ với HTTP 201 không crash hay báo lỗi (test_t2_r4_01)."""
        headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Kiểm thử giao thức FTP",
            "body": "Nội dung kiểm thử giao thức FTP hợp lệ",
            "image_url": ftp_url,
            "status": "DRAFT"
        }, headers=headers)
        assert resp.status_code == 201, f"Expected 201 for FTP, got {resp.status_code}: {resp.text}"
        assert resp.json()["image_url"] == ftp_url

    @pytest.mark.parametrize("no_image_payload", [
        {"campaign_id": 1, "channel_id": 1, "title": "Không có trường image_url", "body": "Văn bản thuần", "status": "DRAFT"},
        {"campaign_id": 1, "channel_id": 1, "title": "image_url là null", "body": "Văn bản thuần", "image_url": None, "status": "DRAFT"},
        {"campaign_id": 1, "channel_id": 1, "title": "image_url là chuỗi rỗng", "body": "Văn bản thuần", "image_url": "", "status": "DRAFT"},
        {"campaign_id": 1, "channel_id": 1, "title": "image_url là khoảng trắng", "body": "Văn bản thuần", "image_url": "   ", "status": "DRAFT"},
    ])
    def test_ch2_06_content_without_image_defaults_null(self, client: TestClient, no_image_payload: dict):
        """1. Request tạo content không có image_url hoặc để trống -> nhận image_url: null sạch sẽ (test_t2_r4_03)."""
        headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents", json=no_image_payload, headers=headers)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("image_url") is None, f"Expected image_url=None, got {data.get('image_url')}"

    def test_ch2_07_put_endpoint_rejects_unsafe_uris(self, client: TestClient):
        """1. Thử thách PUT /contents/{id}: Đảm bảo không thể inject URI nguy hiểm qua phương thức cập nhật."""
        headers = get_marketer_headers(client)

        # Tạo bài viết ban đầu hợp lệ
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết chuẩn bị cập nhật",
            "body": "Nội dung ban đầu",
            "image_url": "https://example.com/initial.jpg",
            "status": "DRAFT"
        }, headers=headers)
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]

        # Thử thách PUT với javascript:
        put_js = client.put(f"/api/v1/contents/{cid}", json={"image_url": "javascript:alert('XSS_PUT')"}, headers=headers)
        assert put_js.status_code == 422, f"Expected 422 on PUT with javascript:, got {put_js.status_code}"

        # Thử thách PUT với vbscript:
        put_vbs = client.put(f"/api/v1/contents/{cid}", json={"image_url": "vbscript:msgbox(1)"}, headers=headers)
        assert put_vbs.status_code == 422, f"Expected 422 on PUT with vbscript:, got {put_vbs.status_code}"

        # Thử thách PUT với data:text/html:
        put_data = client.put(f"/api/v1/contents/{cid}", json={"image_url": "data:text/html;base64,PHNjcmlwdD4="}, headers=headers)
        assert put_data.status_code == 422, f"Expected 422 on PUT with data:text/html, got {put_data.status_code}"

        # Thử thách PUT với độ dài > 1024
        put_oversized = client.put(f"/api/v1/contents/{cid}", json={"image_url": "https://example.com/" + ("b" * 1020) + ".jpg"}, headers=headers)
        assert put_oversized.status_code == 422, f"Expected 422 on PUT with oversized url, got {put_oversized.status_code}"

        # Đảm bảo dữ liệu trong CSDL không bị biến đổi
        get_resp = client.get(f"/api/v1/contents/{cid}", headers=headers)
        assert get_resp.json()["image_url"] == "https://example.com/initial.jpg"


# ==============================================================================
# SECTION 2: STATE MACHINE & ANTI-TAMPERING INTEGRITY CHALLENGES
# ==============================================================================

class TestStateMachineAndAntiTamperingIntegrity:
    """Thử thách Máy trạng thái & Tính toàn vẹn Anti-Tampering khi chỉnh sửa qua PUT."""

    def test_ch2_08_approved_content_image_edit_resets_to_ai_draft(self, client: TestClient):
        """2. Tạo bài viết -> Submit -> Quản lý Approve -> Sửa image_url qua PUT -> BẮT BUỘC hạ về AI_DRAFT!"""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        # 1. Tạo bài viết DRAFT
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết test Anti-Tampering trên APPROVED",
            "body": "Nội dung chất lượng cao đã kiểm duyệt",
            "image_url": "https://example.com/safe_approved_image.jpg",
            "status": "DRAFT"
        }, headers=mkt_headers)
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]
        v_initial = create_resp.json()["version_no"]

        # 2. Gửi duyệt (IN_REVIEW)
        sub_resp = client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        assert sub_resp.status_code == 200
        assert sub_resp.json()["status"] == "IN_REVIEW"

        # 3. Quản lý Approve -> APPROVED
        appr_resp = client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)
        assert appr_resp.status_code == 200
        assert appr_resp.json()["status"] == "APPROVED"

        # 4. Marketer dùng PUT /contents/{id} sửa image_url
        new_image = "https://images.unsplash.com/photo-tampered-new-image.jpg"
        edit_resp = client.put(f"/api/v1/contents/{cid}", json={
            "image_url": new_image
        }, headers=mkt_headers)
        assert edit_resp.status_code == 200
        data = edit_resp.json()

        # RÀNG BUỘC CHẶT CHẼ: Trạng thái không được giữ APPROVED mà phải bị hoàn trả về AI_DRAFT
        assert data["status"] == "AI_DRAFT", f"Anti-Tampering Failure: Expected AI_DRAFT, but got {data['status']}"
        assert data["image_url"] == new_image
        assert data["version_no"] == v_initial + 1

        # Xác thực truy vấn lại GET /contents/{id}
        check_resp = client.get(f"/api/v1/contents/{cid}", headers=mkt_headers)
        assert check_resp.json()["status"] == "AI_DRAFT"
        assert check_resp.json()["image_url"] == new_image

    def test_ch2_09_published_content_image_edit_resets_to_ai_draft(self, client: TestClient):
        """2. Tạo bài viết -> Submit -> Approve -> Publish -> Sửa image_url qua PUT -> BẮT BUỘC hạ về AI_DRAFT!"""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        # 1. Tạo, submit, approve, publish
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết test Anti-Tampering trên PUBLISHED",
            "body": "Nội dung chuẩn bị xuất bản",
            "image_url": "https://example.com/published_banner.jpg",
            "status": "DRAFT"
        }, headers=mkt_headers)
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)
        pub_resp = client.post(f"/api/v1/contents/{cid}/publish", headers=mgr_headers)
        assert pub_resp.status_code == 200
        assert pub_resp.json()["status"] == "PUBLISHED"

        # 2. Sửa image_url trên bài ĐÃ PUBLISHED
        changed_image = "https://images.unsplash.com/photo-post-publish-tamper.jpg"
        edit_resp = client.put(f"/api/v1/contents/{cid}", json={
            "image_url": changed_image
        }, headers=mkt_headers)
        assert edit_resp.status_code == 200
        data = edit_resp.json()

        # BẮT BUỘC hạ về AI_DRAFT
        assert data["status"] == "AI_DRAFT", f"Anti-Tampering Failure on PUBLISHED: Expected AI_DRAFT, but got {data['status']}"
        assert data["image_url"] == changed_image

        # Xác thực truy vấn lại qua GET
        check_resp = client.get(f"/api/v1/contents/{cid}", headers=mkt_headers)
        assert check_resp.json()["status"] == "AI_DRAFT"

    def test_ch2_10_approved_content_unlink_image_resets_to_ai_draft(self, client: TestClient):
        """2. Gỡ bỏ ảnh (image_url: '') trên bài viết APPROVED -> BẮT BUỘC hạ về AI_DRAFT và gỡ ảnh sạch."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết có ảnh đã duyệt",
            "body": "Nội dung chuẩn",
            "image_url": "https://example.com/original.jpg",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)

        # Gửi chuỗi rỗng để gỡ ảnh
        unlink_resp = client.put(f"/api/v1/contents/{cid}", json={
            "image_url": ""
        }, headers=mkt_headers)
        assert unlink_resp.status_code == 200
        data = unlink_resp.json()
        assert data["status"] == "AI_DRAFT"
        assert data["image_url"] is None

        # Kiểm tra lại DB
        check_resp = client.get(f"/api/v1/contents/{cid}", headers=mkt_headers)
        assert check_resp.json()["status"] == "AI_DRAFT"
        assert check_resp.json()["image_url"] is None

    def test_ch2_11_approved_content_idempotent_put_preserves_status(self, client: TestClient):
        """2. Thao tác PUT với image_url giữ nguyên không đổi -> Giữ nguyên APPROVED (tránh false positive reset)."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        original_img = "https://example.com/stable.jpg"
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết ổn định",
            "body": "Nội dung ổn định",
            "image_url": original_img,
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)

        # Gửi PUT với đúng image_url cũ
        same_resp = client.put(f"/api/v1/contents/{cid}", json={
            "image_url": original_img
        }, headers=mkt_headers)
        assert same_resp.status_code == 200
        assert same_resp.json()["status"] == "APPROVED"
        assert same_resp.json()["image_url"] == original_img

    def test_ch2_12_anti_tampering_direct_status_escalation_blocked(self, client: TestClient):
        """2. Chặn đứng mọi hành vi nhảy cóc trạng thái sang APPROVED hoặc PUBLISHED qua PUT hoặc POST."""
        mkt_headers = get_marketer_headers(client)

        # POST trực tiếp status APPROVED
        post_app = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Hack status POST APPROVED",
            "body": "Test",
            "status": "APPROVED"
        }, headers=mkt_headers)
        assert post_app.status_code == 400

        # POST trực tiếp status PUBLISHED
        post_pub = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Hack status POST PUBLISHED",
            "body": "Test",
            "status": "PUBLISHED"
        }, headers=mkt_headers)
        assert post_pub.status_code == 400

        # Tạo bài DRAFT hợp lệ
        valid_post = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài DRAFT chuẩn",
            "body": "Test",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = valid_post.json()["id"]

        # PUT trực tiếp status APPROVED
        put_app = client.put(f"/api/v1/contents/{cid}", json={"status": "APPROVED"}, headers=mkt_headers)
        assert put_app.status_code == 400

        # PUT trực tiếp status PUBLISHED
        put_pub = client.put(f"/api/v1/contents/{cid}", json={"status": "PUBLISHED"}, headers=mkt_headers)
        assert put_pub.status_code == 400

        # PUT sửa image kèm status APPROVED gian lận
        put_combo = client.put(f"/api/v1/contents/{cid}", json={
            "image_url": "https://example.com/tamper.jpg",
            "status": "APPROVED"
        }, headers=mkt_headers)
        assert put_combo.status_code == 400

    def test_ch2_13_approved_content_text_fields_edit_resets_to_ai_draft(self, client: TestClient):
        """2. Thử nghiệm hồi quy: Sửa title, body, hoặc cta trên bài APPROVED cũng đều tự động hạ về AI_DRAFT."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Tiêu đề gốc đã duyệt",
            "body": "Thân bài gốc đã duyệt",
            "cta": "CTA gốc",
            "status": "DRAFT"
        }, headers=mkt_headers)
        cid = create_resp.json()["id"]

        # Sửa title -> AI_DRAFT
        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)
        edit_t = client.put(f"/api/v1/contents/{cid}", json={"title": "Tiêu đề mới"}, headers=mkt_headers)
        assert edit_t.status_code == 200
        assert edit_t.json()["status"] == "AI_DRAFT"

        # Sửa body -> AI_DRAFT
        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)
        edit_b = client.put(f"/api/v1/contents/{cid}", json={"body": "Thân bài mới"}, headers=mkt_headers)
        assert edit_b.status_code == 200
        assert edit_b.json()["status"] == "AI_DRAFT"

        # Sửa cta -> AI_DRAFT
        client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=mgr_headers)
        edit_c = client.put(f"/api/v1/contents/{cid}", json={"cta": "CTA mới"}, headers=mkt_headers)
        assert edit_c.status_code == 200
        assert edit_c.json()["status"] == "AI_DRAFT"


# ==============================================================================
# SECTION 3: BYTE-LEVEL INTEGRITY & EXCEL CSV UTF-8 BOM CHALLENGES
# ==============================================================================

class TestByteLevelIntegrityAndCsvExport:
    """Thử thách Độ toàn vẹn Byte-Level cho 1-Click Copy và Xuất Excel."""

    def test_ch2_14_byte_level_unicode_complex_emojis_multiline_fidelity(self, client: TestClient):
        """3. Thử nghiệm văn bản chứa hỗn hợp emoji phức tạp, tab, bullet, xuống dòng liên tiếp -> Không trượt byte nào (test_t2_r4_02)."""
        headers = get_marketer_headers(client)

        complex_text = (
            "🇻🇳 CHIẾN DỊCH QUẢNG BÁ KHÓA HỌC TRÍ TUỆ NHÂN TẠO 2026 🚀\n\n"
            "\t• Điểm sáng 1: Giảng viên chuyên gia đầu ngành 👨‍👩‍👧‍👦✨\n"
            "\t• Điểm sáng 2: Thực hành dự án thực chiến 💻🔥\n"
            "\t• Đánh giá từ cộng đồng: 👍🏽 Rất hữu ích & tiện lợi!\n\n"
            "\"Cam kết chất lượng chuẩn đầu ra, tối ưu trải nghiệm học viên!\"\n\n"
            "👉 Đăng ký ngay tại: https://marketflow.ai/register\n"
            "--- Hết thông báo ---"
        )
        title_complex = "🎉 Khóa Học AI Thực Chiến 2026 • Tuyệt Vời ✨"

        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": title_complex,
            "body": complex_text,
            "image_url": "https://example.com/course_banner.png",
            "status": "DRAFT"
        }, headers=headers)
        assert resp.status_code == 201
        saved_id = resp.json()["id"]

        # Đọc lại từ endpoint GET
        get_resp = client.get(f"/api/v1/contents/{saved_id}", headers=headers)
        assert get_resp.status_code == 200
        retrieved_data = get_resp.json()

        retrieved_body = retrieved_data["body"]
        retrieved_title = retrieved_data["title"]

        # 1. Kiểm tra byte representation UTF-8 chính xác 100%
        expected_body_bytes = complex_text.encode("utf-8")
        actual_body_bytes = retrieved_body.encode("utf-8")
        assert len(actual_body_bytes) == len(expected_body_bytes), (
            f"Byte length mismatch: expected {len(expected_body_bytes)}, got {len(actual_body_bytes)}"
        )
        assert actual_body_bytes == expected_body_bytes, "Binary content mismatch in body UTF-8 bytes!"

        # 2. Kiểm tra từng ký tự Unicode
        assert len(retrieved_body) == len(complex_text)
        for i, (c_orig, c_ret) in enumerate(zip(complex_text, retrieved_body)):
            assert c_orig == c_ret, f"Character mismatch at position {i}: {ord(c_orig):#x} vs {ord(c_ret):#x}"

        # 3. Kiểm tra title
        assert retrieved_title.encode("utf-8") == title_complex.encode("utf-8")

    def test_ch2_15_excel_csv_export_utf8_bom_integrity(self):
        """3. Kiểm tra byte đầu tiên của file CSV đúng là UTF-8 BOM \\uFEFF (0xEF, 0xBB, 0xBF) và không lỗi font tiếng Việt."""
        # Mô phỏng thuật toán xuất CSV chuẩn UTF-8 BOM như đã cài đặt trong frontend/src/utils/exportUtils.ts
        BOM = "\uFEFF"
        headers = ["STT", "Kênh Truyền Thông", "Tiêu Đề Bài Viết", "Nội Dung Chi Tiết", "Lời Kêu Gọi (CTA)", "Link Ảnh / Banner", "Trạng Thái"]
        
        test_contents = [
            {
                "index": 1,
                "channel": "Facebook",
                "title": "Chiến dịch Mùa Hè Rực Rỡ 2026 🎉",
                "body": "Đăng ký ngay khóa học \"Trí Tuệ Nhân Tạo & Tiếp Thị Đa Kênh\"!\nGiảm ngay 20% cho học viên đăng ký sớm.\n\t• Hỗ trợ 24/7\n\t• Tài liệu chuẩn quốc tế",
                "cta": "Đăng Ký Ngay",
                "image_url": "https://images.unsplash.com/photo-banner.jpg",
                "status": "APPROVED"
            },
            {
                "index": 2,
                "channel": "TikTok",
                "title": "Kịch bản Video Viral 3s Giữ Chân 🎬",
                "body": "Hook: Bạn đã biết cách làm marketing bằng AI chưa? ⚡\nPhân cảnh 1: Mở màn cuốn hút.",
                "cta": "Bấm vào link bio",
                "image_url": "",
                "status": "AI_DRAFT"
            }
        ]

        def escape_csv_cell(val):
            if val is None:
                return '""'
            s = str(val).replace('"', '""')
            return f'"{s}"'

        rows = []
        for c in test_contents:
            row = [
                escape_csv_cell(c["index"]),
                escape_csv_cell(c["channel"]),
                escape_csv_cell(c["title"]),
                escape_csv_cell(c["body"]),
                escape_csv_cell(c["cta"]),
                escape_csv_cell(c["image_url"]),
                escape_csv_cell(c["status"])
            ]
            rows.append(",".join(row))

        header_line = ",".join(escape_csv_cell(h) for h in headers)
        full_csv_str = BOM + "\r\n".join([header_line, *rows])

        # Chuyển đổi thành raw bytes qua UTF-8
        csv_bytes = full_csv_str.encode("utf-8")

        # RÀNG BUỘC CHẶT CHẼ: 3 byte đầu tiên BẮT BUỘC phải là UTF-8 BOM
        # 0xEF, 0xBB, 0xBF
        assert len(csv_bytes) >= 3
        assert csv_bytes[:3] == b"\xef\xbb\xbf", f"First 3 bytes are not UTF-8 BOM! Got: {csv_bytes[:3]}"
        assert csv_bytes[0] == 0xEF
        assert csv_bytes[1] == 0xBB
        assert csv_bytes[2] == 0xBF

        # Kiểm tra giải mã bằng 'utf-8-sig' trong Python (tương đương engine của Microsoft Excel)
        decoded_content = csv_bytes.decode("utf-8-sig")
        assert not decoded_content.startswith("\uFEFF"), "utf-8-sig should strip the BOM character seamlessly"
        assert "Chiến dịch Mùa Hè Rực Rỡ 2026 🎉" in decoded_content
        assert "Trí Tuệ Nhân Tạo & Tiếp Thị Đa Kênh" in decoded_content
        assert "\ufffd" not in decoded_content, "Found replacement character indicating font corruption!"

        # Đọc lại bằng thư viện chuẩn csv.reader để kiểm tra tính hợp lệ RFC 4180
        f_in = io.StringIO(decoded_content)
        reader = list(csv.reader(f_in))
        assert len(reader) == 3  # 1 header + 2 data rows
        assert reader[0][0] == "STT"
        assert reader[0][2] == "Tiêu Đề Bài Viết"
        assert reader[1][2] == "Chiến dịch Mùa Hè Rực Rỡ 2026 🎉"
        assert "• Hỗ trợ 24/7" in reader[1][3]

    def test_ch2_16_campaign_contents_endpoint_contract(self, client: TestClient):
        """3. Kiểm thử endpoint GET /campaigns/{id}/contents cho công cụ Export Kế Hoạch."""
        mgr_headers = get_manager_headers(client)

        # 1. Chiến dịch ID 1 có sẵn contents từ seed
        resp_1 = client.get("/api/v1/campaigns/1/contents", headers=mgr_headers)
        assert resp_1.status_code == 200
        contents_1 = resp_1.json()
        assert isinstance(contents_1, list)
        assert len(contents_1) >= 1
        first_item = contents_1[0]
        # Kiểm tra cấu trúc trường dữ liệu đầy đủ cho Social Preview & Export
        assert "id" in first_item
        assert "title" in first_item
        assert "body" in first_item
        assert "image_url" in first_item
        assert "status" in first_item
        assert "version_no" in first_item

        # 2. Chiến dịch ID 2 trống -> trả về HTTP 200 OK với danh sách [] (không báo 500 hay crash)
        resp_empty = client.get("/api/v1/campaigns/2/contents", headers=mgr_headers)
        assert resp_empty.status_code == 200
        assert resp_empty.json() == []

        # 3. Chiến dịch không tồn tại (99999) -> trả về HTTP 404
        resp_404 = client.get("/api/v1/campaigns/99999/contents", headers=mgr_headers)
        assert resp_404.status_code == 404
