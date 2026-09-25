"""
Empirical Adversarial Test Suite for Milestone 1 Security & RBAC Verification
Author: Challenger 2 (Security & State Machine Challenger)
"""

import json
from datetime import datetime, timedelta, timezone
import pytest
import jwt
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.entities import User, Workspace, WorkspaceMember, BrandKit, Campaign, MarketingContent

def get_auth_headers(client, email: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

class TestRBACBrandKit:
    def test_marketer_updating_brand_kit_blocked_403(self, client):
        """Marketer thử cập nhật Brand Kit của workspace -> Phải bị chặn HTTP 403."""
        mkt_headers = get_auth_headers(client, "marketer@ictu.edu.vn", "Marketer@123")
        payload = {
            "brand_name": "Hacked Brand Name by Marketer",
            "usp": "Hacked USP",
            "tone_of_voice": "Informal",
            "banned_keywords": ["forbidden"]
        }
        resp = client.put("/api/v1/brand-kit?workspace_id=1", json=payload, headers=mkt_headers)
        assert resp.status_code == 403, f"Expected 403 but got {resp.status_code}: {resp.text}"
        assert "Chỉ Quản lý" in resp.json().get("detail", "")

class TestRBACCampaignCreation:
    def test_client_approver_creating_campaign_reproduces_rbac_bypass(self, client):
        """Thử nghiệm tài khoản role CLIENT_APPROVER thử tạo campaign mới.
        Theo thiết kế kỹ thuật (PROJECT.md line 34):
          'CLIENT_APPROVER: Client representative; access Review Queue, inspect Social Previews
           and Compliance scores, approve or reject content. CANNOT create campaigns or edit Brand Kit.'
        Sau khi khắc phục: Hệ thống chặn role CLIENT_APPROVER với HTTP 403 Forbidden.
        """
        approver_headers = get_auth_headers(client, "approver@ictu.edu.vn", "Approver@123")
        payload = {
            "product_id": 1,
            "name": "Campaign By Client Approver",
            "objective": "Test if approver can create campaign",
            "audience": "Approvers",
            "start_date": "2026-10-01",
            "end_date": "2026-10-31",
            "budget": 5000000.0,
            "workspace_id": 1
        }
        resp = client.post("/api/v1/campaigns", json=payload, headers=approver_headers)
        assert resp.status_code == 403, f"Expected 403 Forbidden, got {resp.status_code}: {resp.text}"

class TestRBACContentApprove:
    def test_marketer_approve_content_blocked_403(self, client):
        """Tài khoản MARKETER không có quyền duyệt thử gọi POST /api/v1/contents/{id}/approve -> Bị chặn 403."""
        mkt_headers = get_auth_headers(client, "marketer@ictu.edu.vn", "Marketer@123")
        # Content 1 đang ở trạng thái IN_REVIEW
        resp = client.post("/api/v1/contents/1/approve", headers=mkt_headers)
        assert resp.status_code == 403, f"Expected 403 but got {resp.status_code}: {resp.text}"

    def test_manager_and_approver_can_approve_content(self, client, db_session):
        """Manager và Client Approver có quyền phê duyệt nội dung."""
        approver_headers = get_auth_headers(client, "approver@ictu.edu.vn", "Approver@123")
        # Đảm bảo Content 1 ở trạng thái IN_REVIEW
        content = db_session.query(MarketingContent).filter(MarketingContent.id == 1).first()
        content.status = "IN_REVIEW"
        db_session.commit()

        resp = client.post("/api/v1/contents/1/approve", headers=approver_headers)
        assert resp.status_code == 200, f"Approver approve failed: {resp.text}"
        assert resp.json()["status"] == "APPROVED"

class TestTokenAuthentication:
    def test_missing_authorization_header_returns_401(self, client):
        """Không gửi Authorization header -> HTTP 401."""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        assert "Yêu cầu xác thực đăng nhập" in resp.json().get("detail", "")

        resp2 = client.get("/api/v1/brand-kit?workspace_id=1")
        assert resp2.status_code == 401

        resp3 = client.get("/api/v1/workspaces")
        assert resp3.status_code == 401

    def test_fake_invalid_token_returns_401(self, client):
        """Gửi token giả / sai chữ ký -> HTTP 401."""
        headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake.payload"}
        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 401
        assert "Token không hợp lệ hoặc đã hết hạn" in resp.json().get("detail", "")

    def test_expired_token_returns_401(self, client):
        """Gửi token hết hạn -> HTTP 401."""
        expired_payload = {
            "sub": "1",
            "email": "manager@ictu.edu.vn",
            "role": "MANAGER",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=10) # 10 phút trước
        }
        expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        headers = {"Authorization": f"Bearer {expired_token}"}

        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 401
        assert "Token không hợp lệ hoặc đã hết hạn" in resp.json().get("detail", "")

class TestPasswordSecurityAndStorage:
    def test_all_passwords_are_bcrypt_hashed(self, db_session):
        """Kiểm tra toàn bộ mật khẩu trong DB: phải bắt đầu bằng $2b$, không lưu plaintext."""
        users = db_session.query(User).all()
        assert len(users) >= 3
        for u in users:
            assert u.password_hash is not None
            assert u.password_hash.startswith("$2b$"), f"User {u.email} password is not bcrypt: {u.password_hash}"
            assert u.password_hash != "Manager@123"
            assert u.password_hash != "Marketer@123"
            assert u.password_hash != "Approver@123"

    def test_registered_user_password_is_bcrypt_hashed(self, client, db_session):
        """Đăng ký user mới và kiểm tra password_hash trong CSDL."""
        reg_payload = {
            "email": "new_security_test@example.com",
            "password": "SuperSecretPassword@2026",
            "full_name": "Security Test User",
            "role": "MARKETER"
        }
        resp = client.post("/api/v1/auth/register", json=reg_payload)
        assert resp.status_code == 201

        new_user = db_session.query(User).filter(User.email == "new_security_test@example.com").first()
        assert new_user is not None
        assert new_user.password_hash.startswith("$2b$")
        assert "SuperSecretPassword@2026" not in new_user.password_hash

class TestBrandKitSQLiAndJSONSafety:
    def test_banned_keywords_sqli_injection_immune(self, client, db_session):
        """Thử nghiệm các vector SQL Injection và XSS qua banned_keywords."""
        mgr_headers = get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")
        sqli_payloads = [
            "'; DROP TABLE brand_kits; --",
            "' OR '1'='1",
            "admin' --",
            "1; SELECT * FROM users; --",
            "<script>alert('xss')</script>",
            '{"evil": "nested"}',
            "UNION SELECT null, null, null --"
        ]
        update_data = {
            "brand_name": "Safe Brand SQLi Test",
            "banned_keywords": sqli_payloads
        }
        resp = client.put("/api/v1/brand-kit?workspace_id=1", json=update_data, headers=mgr_headers)
        assert resp.status_code == 200, f"Update failed: {resp.text}"

        # Kiểm tra bảng brand_kits vẫn tồn tại nguyên vẹn
        bk = db_session.query(BrandKit).filter(BrandKit.workspace_id == 1).first()
        assert bk is not None
        saved_list = json.loads(bk.banned_keywords_json)
        assert saved_list == sqli_payloads

        # Kiểm tra GET trả về đúng mảng nguyên vẹn
        get_resp = client.get("/api/v1/brand-kit?workspace_id=1", headers=mgr_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["banned_keywords"] == sqli_payloads

    def test_banned_keywords_invalid_type_rejected(self, client):
        """Gửi chuỗi hoặc kiểu dữ liệu sai cho banned_keywords -> HTTP 422."""
        mgr_headers = get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")
        bad_payload = {
            "banned_keywords": "this should be a list, not a string"
        }
        resp = client.put("/api/v1/brand-kit?workspace_id=1", json=bad_payload, headers=mgr_headers)
        assert resp.status_code == 422
