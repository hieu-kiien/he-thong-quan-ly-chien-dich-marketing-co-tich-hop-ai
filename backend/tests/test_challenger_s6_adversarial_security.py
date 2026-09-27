"""
Test Suite: Sprint S6 Adversarial Security Challenger
Module: test_challenger_s6_adversarial_security.py
Purpose: Empirical Adversarial Attack Verification on Security, Crypto, and Database Safeguards.

Actively attempts to break the hardened safeguards across 5 attack scenarios:
1. Public Registration Privilege Escalation (POST /api/v1/auth/register)
2. Token Claims Spoofing & Inactive User Bypass (RoleChecker & sub validation)
3. Cross-Tenant Workspace Tampering (/submit, /approve, /reject, /publish, /update)
4. Production Database Reset Exploit (reset_db() in production environment)
5. Insecure Secrets Detection & Startup Hardening (validate_security_configuration())
"""

import os
import jwt
import pytest
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock

from app.core.config import Settings, settings, validate_security_configuration
from app.core.database import Base
from app.core.security import (
    create_access_token,
    hash_password,
    RoleChecker,
    UserStatus
)
from app.models.entities import (
    User,
    Workspace,
    WorkspaceMember,
    Campaign,
    MarketingContent,
    Product
)
from seed.seed_data import reset_db, init_db as seed_init_db, is_production_env


# Helper for creating auth headers
def make_user_token(user: User, custom_claims: dict = None) -> str:
    data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name
    }
    if custom_claims:
        data.update(custom_claims)
    return create_access_token(data=data)


def make_auth_headers(user: User, custom_claims: dict = None) -> dict:
    token = make_user_token(user, custom_claims)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# ATTACK SCENARIO 1: Public Registration Privilege Escalation
# ==============================================================================
class TestAttackScenario1_PublicRegistrationPrivilegeEscalation:
    """Kiểm thử đối kháng: Tấn công leo thang đặc quyền qua endpoint đăng ký công khai.
    Kẻ tấn công gửi yêu cầu POST /api/v1/auth/register kèm các vai trò đặc quyền:
    (AGENCY_MANAGER, CLIENT_APPROVER, ADMIN, MANAGER).
    Hệ thống bắt buộc chặn với HTTP 403 Forbidden và thông báo chuẩn.
    Các giá trị không thuộc schema hợp lệ bị chặn ở tầng Pydantic với HTTP 422.
    """

    @pytest.mark.parametrize("priv_role", [
        "AGENCY_MANAGER",
        "CLIENT_APPROVER",
        "ADMIN",
        "MANAGER",
    ])
    def test_attack_privileged_registration_blocked_with_403(self, client, priv_role):
        """Kẻ tấn công gửi vai trò đặc quyền khi đăng ký -> Bắt buộc nhận 403 Forbidden."""
        payload = {
            "email": f"attacker_{priv_role.lower()}_{os.urandom(4).hex()}@evilcorp.com",
            "password": "EvilPassword@123",
            "full_name": f"Malicious Actor {priv_role}",
            "role": priv_role
        }

        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 403, (
            f"Vulnerability found! Privileged role '{priv_role}' was not rejected with 403. "
            f"Received: {resp.status_code} - {resp.text}"
        )
        data = resp.json()
        expected_msg = "Self-registration with privileged roles is not allowed. Contact your workspace administrator."
        assert data.get("detail") == expected_msg, (
            f"Unexpected error message for role '{priv_role}': {data.get('detail')}"
        )

    @pytest.mark.parametrize("malformed_role", [
        "agency_manager",
        "client_approver",
        "admin",
        "manager",
        "superadmin",
        "root",
        "hacker",
    ])
    def test_attack_malformed_role_registration_blocked_with_422(self, client, malformed_role):
        """Các biến thể role không đúng chuẩn schema bị chặn tại tầng Pydantic (HTTP 422)."""
        payload = {
            "email": f"attacker_mal_{os.urandom(4).hex()}@evilcorp.com",
            "password": "EvilPassword@123",
            "full_name": "Malicious Role Format",
            "role": malformed_role
        }
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 422, f"Malformed role '{malformed_role}' bypassed schema validation"

    def test_legitimate_marketer_registration_succeeds(self, client, db_session):
        """Người dùng thông thường đăng ký vai trò MARKETER được chấp thuận với HTTP 201."""
        email = f"legit_marketer_{os.urandom(4).hex()}@goodcorp.com"
        payload = {
            "email": email,
            "password": "ValidPassword@123",
            "full_name": "Nguyen Van Marketer",
            "role": "MARKETER"
        }
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201
        res_data = resp.json()
        assert res_data["role"] == "MARKETER"

        # Kiểm tra trạng thái trong DB
        db_user = db_session.query(User).filter(User.email == email).first()
        assert db_user is not None
        assert db_user.role == "MARKETER"
        assert db_user.status == "ACTIVE"


# ==============================================================================
# ATTACK SCENARIO 2: Token Claims Spoofing & Inactive User Bypass
# ==============================================================================
class TestAttackScenario2_TokenClaimsSpoofingAndInactiveUserBypass:
    """Kiểm thử đối kháng: Giả mạo payload claim trong JWT token và bypass tài khoản bị vô hiệu hóa.
    1. Giả mạo claim role='AGENCY_MANAGER'/'MANAGER' khi DB user là 'MARKETER' -> 403 Forbidden.
    2. Sử dụng token của tài khoản có status != 'ACTIVE' -> 403 Forbidden.
    3. Token thiếu / rỗng / sai trường 'sub' -> 401 Unauthorized.
    4. Token có chữ ký giả mạo -> 401 Unauthorized.
    """

    def test_attack_forged_payload_role_claim_rejected_by_db_role(self, client, db_session):
        """Kẻ tấn công sở hữu tài khoản MARKETER, tự tạo token với claim role='AGENCY_MANAGER'
        và cố gắng phê duyệt hoặc xuất bản nội dung.
        Hệ thống phải truy vấn DB để xác thực vai trò thực tế và chặn với 403 Forbidden.
        """
        marketer = db_session.query(User).filter(User.email == "marketer@gmail.com").first()
        assert marketer is not None
        assert marketer.role == "MARKETER"

        # Tạo token giả mạo role đặc quyền nhưng sub là ID của Marketer
        forged_claims = {
            "sub": str(marketer.id),
            "email": marketer.email,
            "role": "AGENCY_MANAGER",
            "full_name": marketer.full_name
        }
        forged_token = create_access_token(data=forged_claims)
        headers = {"Authorization": f"Bearer {forged_token}"}

        # Thử gọi endpoint Approve (chỉ dành cho MANAGER/AGENCY_MANAGER/CLIENT_APPROVER)
        resp_approve = client.post("/api/v1/contents/1/approve", headers=headers)
        assert resp_approve.status_code == 403, (
            f"Vulnerability found! Role claim spoofing succeeded on /approve. Status: {resp_approve.status_code}"
        )
        assert "Thao tác trái quyền" in resp_approve.json().get("detail", "")

        # Thử gọi endpoint Publish (chỉ dành cho MANAGER/AGENCY_MANAGER)
        resp_publish = client.post("/api/v1/contents/1/publish", headers=headers)
        assert resp_publish.status_code == 403, (
            f"Vulnerability found! Role claim spoofing succeeded on /publish. Status: {resp_publish.status_code}"
        )
        assert "Thao tác trái quyền" in resp_publish.json().get("detail", "")

    def test_attack_inactive_disabled_user_token_blocked(self, client, db_session):
        """Tài khoản quản lý bị vô hiệu hóa (status='DISABLED') nhưng kẻ tấn công có token hợp lệ.
        Hệ thống phải kiểm tra user.status == 'ACTIVE' trong DB và chặn với 403 Forbidden.
        """
        manager = db_session.query(User).filter(User.email == "manager@gmail.com").first()
        assert manager is not None
        orig_status = manager.status
        try:
            manager.status = UserStatus.DISABLED
            db_session.commit()

            # Tạo token hợp lệ cho manager này
            token = create_access_token(data={
                "sub": str(manager.id),
                "email": manager.email,
                "role": manager.role,
                "full_name": manager.full_name
            })
            headers = {"Authorization": f"Bearer {token}"}

            # 1. Thử qua RoleChecker (endpoint /approve)
            resp = client.post("/api/v1/contents/1/approve", headers=headers)
            assert resp.status_code == 403, (
                f"Vulnerability! Inactive user bypassed RoleChecker: {resp.status_code}"
            )
            assert "user account is not active" in resp.json().get("detail", "").lower()

            # 2. Thử qua get_current_user (endpoint GET /contents)
            resp_list = client.get("/api/v1/contents", headers=headers)
            assert resp_list.status_code == 403, (
                f"Vulnerability! Inactive user bypassed get_current_user: {resp_list.status_code}"
            )
            assert "user account is not active" in resp_list.json().get("detail", "").lower()

        finally:
            manager.status = orig_status
            db_session.commit()

    @pytest.mark.parametrize("mock_status", ["SUSPENDED", "INACTIVE", "BANNED", "PENDING_VERIFICATION"])
    def test_attack_role_checker_blocks_any_non_active_user_status(self, mock_status):
        """RoleChecker trực tiếp chặn mọi trạng thái người dùng khác ACTIVE (kể cả SUSPENDED/INACTIVE)."""
        checker = RoleChecker(allowed_roles=["MANAGER", "AGENCY_MANAGER"])

        # Giả lập payload và DB user có status không phải ACTIVE
        mock_user = MagicMock()
        mock_user.id = 123
        mock_user.role = "MANAGER"
        mock_user.status = mock_status

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        # Token chứa sub=123 và role=MANAGER
        valid_token = create_access_token(data={"sub": "123", "role": "MANAGER"})
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=valid_token)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            checker(credentials=creds, db=mock_db)

        assert exc_info.value.status_code == 403
        assert "user account is not active" in str(exc_info.value.detail).lower()

    def test_attack_missing_or_blank_sub_claim_rejected(self, client):
        """Token thiếu claim 'sub' hoặc chỉ chứa khoảng trắng -> HTTP 401 Unauthorized."""
        # 1. Không có claim sub
        token_no_sub = create_access_token(data={"role": "MANAGER", "email": "admin@example.com"})
        r1 = client.post("/api/v1/contents/1/approve", headers={"Authorization": f"Bearer {token_no_sub}"})
        assert r1.status_code == 401
        assert "sub" in r1.json().get("detail", "").lower()

        # 2. Claim sub là khoảng trắng
        token_blank_sub = create_access_token(data={"sub": "   ", "role": "MANAGER"})
        r2 = client.post("/api/v1/contents/1/approve", headers={"Authorization": f"Bearer {token_blank_sub}"})
        assert r2.status_code == 401

    def test_attack_nonexistent_sub_user_rejected(self, client):
        """Token chứa sub trỏ tới ID người dùng không hề tồn tại trong CSDL -> HTTP 401."""
        token_fake = create_access_token(data={"sub": "88888888", "role": "MANAGER"})
        resp = client.post("/api/v1/contents/1/approve", headers={"Authorization": f"Bearer {token_fake}"})
        assert resp.status_code == 401
        assert "không tồn tại" in resp.json().get("detail", "").lower()

    def test_attack_forged_jwt_signature_rejected(self, client):
        """Token được ký bởi khóa bí mật giả mạo (forged secret key) -> HTTP 401 Unauthorized."""
        bogus_key = "completely-unauthorized-bogus-secret-key-12345"
        forged_jwt = jwt.encode(
            {"sub": "1", "role": "MANAGER", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            bogus_key,
            algorithm="HS256"
        )
        resp = client.post("/api/v1/contents/1/approve", headers={"Authorization": f"Bearer {forged_jwt}"})
        assert resp.status_code == 401


# ==============================================================================
# ATTACK SCENARIO 3: Cross-Tenant Workspace Tampering
# ==============================================================================
class TestAttackScenario3_CrossTenantWorkspaceTampering:
    """Kiểm thử đối kháng: Tấn công xuyên tenant (Cross-Tenant Tampering).
    Kẻ tấn công ở Workspace A (Tenant A) cố tình thao tác trên nội dung thuộc Workspace B (Tenant B):
    - /submit
    - /approve
    - /reject
    - /publish
    - PUT /contents/{id}
    Hệ thống bắt buộc chặn với HTTP 403 Forbidden ("User does not have access to this workspace content").
    Nội dung Tenant B không được phép bị biến đổi trạng thái hay nội dung.
    """

    @pytest.fixture
    def setup_two_tenants(self, db_session):
        """Thiết lập 2 Workspace hoàn toàn cách ly với người dùng và nội dung tương ứng."""
        # 1. Tenant A
        user_a_mgr = User(
            email=f"manager_a_{os.urandom(3).hex()}@tenant-a.com",
            full_name="Manager Tenant A",
            password_hash=hash_password("PassA@123"),
            role="AGENCY_MANAGER",
            status="ACTIVE"
        )
        user_a_mkt = User(
            email=f"marketer_a_{os.urandom(3).hex()}@tenant-a.com",
            full_name="Marketer Tenant A",
            password_hash=hash_password("PassA@123"),
            role="MARKETER",
            status="ACTIVE"
        )
        db_session.add_all([user_a_mgr, user_a_mkt])
        db_session.commit()

        ws_a = Workspace(
            name="Workspace Tenant A",
            slug=f"ws-a-{os.urandom(3).hex()}",
            description="Tenant A",
            owner_id=user_a_mgr.id,
            status="ACTIVE"
        )
        db_session.add(ws_a)
        db_session.commit()

        db_session.add_all([
            WorkspaceMember(workspace_id=ws_a.id, user_id=user_a_mgr.id, role="AGENCY_MANAGER"),
            WorkspaceMember(workspace_id=ws_a.id, user_id=user_a_mkt.id, role="MARKETER"),
        ])
        db_session.commit()

        # 2. Tenant B
        user_b_mgr = User(
            email=f"manager_b_{os.urandom(3).hex()}@tenant-b.com",
            full_name="Manager Tenant B",
            password_hash=hash_password("PassB@123"),
            role="AGENCY_MANAGER",
            status="ACTIVE"
        )
        user_b_mkt = User(
            email=f"marketer_b_{os.urandom(3).hex()}@tenant-b.com",
            full_name="Marketer Tenant B",
            password_hash=hash_password("PassB@123"),
            role="MARKETER",
            status="ACTIVE"
        )
        db_session.add_all([user_b_mgr, user_b_mkt])
        db_session.commit()

        ws_b = Workspace(
            name="Workspace Tenant B",
            slug=f"ws-b-{os.urandom(3).hex()}",
            description="Tenant B",
            owner_id=user_b_mgr.id,
            status="ACTIVE"
        )
        db_session.add(ws_b)
        db_session.commit()

        db_session.add_all([
            WorkspaceMember(workspace_id=ws_b.id, user_id=user_b_mgr.id, role="AGENCY_MANAGER"),
            WorkspaceMember(workspace_id=ws_b.id, user_id=user_b_mkt.id, role="MARKETER"),
        ])
        db_session.commit()

        product = db_session.query(Product).first()
        now = datetime.now(timezone.utc)
        camp_b = Campaign(
            workspace_id=ws_b.id,
            product_id=product.id if product else 1,
            owner_id=user_b_mgr.id,
            name="Campaign Tenant B",
            objective="Awareness",
            audience="B2B",
            start_date=now,
            end_date=now + timedelta(days=30)
        )
        db_session.add(camp_b)
        db_session.commit()

        content_b = MarketingContent(
            workspace_id=ws_b.id,
            campaign_id=camp_b.id,
            channel_id=1,
            created_by=user_b_mkt.id,
            title="Private Content Tenant B",
            body="Confidential Marketing Asset for Tenant B",
            cta="Buy Now",
            status="DRAFT"
        )
        db_session.add(content_b)
        db_session.commit()
        db_session.refresh(content_b)

        return {
            "ws_a": ws_a,
            "user_a_mgr": user_a_mgr,
            "user_a_mkt": user_a_mkt,
            "ws_b": ws_b,
            "user_b_mgr": user_b_mgr,
            "user_b_mkt": user_b_mkt,
            "camp_b": camp_b,
            "content_b": content_b,
        }

    def test_attack_cross_tenant_submit_rejected(self, client, setup_two_tenants):
        """User từ Workspace A không được phép submit nội dung thuộc Workspace B."""
        data = setup_two_tenants
        headers_a_mkt = make_auth_headers(data["user_a_mkt"])
        headers_a_mgr = make_auth_headers(data["user_a_mgr"])

        # Marketer A attempts submit Content B
        resp1 = client.post(f"/api/v1/contents/{data['content_b'].id}/submit", headers=headers_a_mkt)
        assert resp1.status_code == 403, f"Cross-tenant submit breached by Marketer A: {resp1.status_code}"
        assert "User does not have access to this workspace content" in resp1.json().get("detail", "")

        # Manager A attempts submit Content B
        resp2 = client.post(f"/api/v1/contents/{data['content_b'].id}/submit", headers=headers_a_mgr)
        assert resp2.status_code == 403, f"Cross-tenant submit breached by Manager A: {resp2.status_code}"
        assert "User does not have access to this workspace content" in resp2.json().get("detail", "")

    def test_attack_cross_tenant_approve_rejected(self, client, db_session, setup_two_tenants):
        """Manager từ Workspace A không được phép approve nội dung thuộc Workspace B."""
        data = setup_two_tenants
        content_b = data["content_b"]
        content_b.status = "IN_REVIEW"
        db_session.commit()

        headers_a_mgr = make_auth_headers(data["user_a_mgr"])
        resp = client.post(f"/api/v1/contents/{content_b.id}/approve", headers=headers_a_mgr)
        assert resp.status_code == 403, f"Cross-tenant approve breached: {resp.status_code}"
        assert "User does not have access to this workspace content" in resp.json().get("detail", "")

    def test_attack_cross_tenant_reject_rejected(self, client, db_session, setup_two_tenants):
        """Manager từ Workspace A không được phép reject nội dung thuộc Workspace B."""
        data = setup_two_tenants
        content_b = data["content_b"]
        content_b.status = "IN_REVIEW"
        db_session.commit()

        headers_a_mgr = make_auth_headers(data["user_a_mgr"])
        resp = client.post(
            f"/api/v1/contents/{content_b.id}/reject",
            json={"decision": "REJECTED", "reason": "Malicious reject from foreign tenant"},
            headers=headers_a_mgr
        )
        assert resp.status_code == 403, f"Cross-tenant reject breached: {resp.status_code}"
        assert "User does not have access to this workspace content" in resp.json().get("detail", "")

    def test_attack_cross_tenant_publish_rejected(self, client, db_session, setup_two_tenants):
        """Manager từ Workspace A không được phép publish nội dung thuộc Workspace B."""
        data = setup_two_tenants
        content_b = data["content_b"]
        content_b.status = "APPROVED"
        db_session.commit()

        headers_a_mgr = make_auth_headers(data["user_a_mgr"])
        resp = client.post(f"/api/v1/contents/{content_b.id}/publish", headers=headers_a_mgr)
        assert resp.status_code == 403, f"Cross-tenant publish breached: {resp.status_code}"
        assert "User does not have access to this workspace content" in resp.json().get("detail", "")

    def test_attack_cross_tenant_put_update_rejected(self, client, setup_two_tenants):
        """User từ Workspace A cố tình ghi đè nội dung Content B qua endpoint PUT."""
        data = setup_two_tenants
        headers_a_mkt = make_auth_headers(data["user_a_mkt"])
        resp = client.put(
            f"/api/v1/contents/{data['content_b'].id}",
            json={"title": "Hacked Title", "body": "Hacked Body"},
            headers=headers_a_mkt
        )
        assert resp.status_code == 403, f"Cross-tenant PUT update breached: {resp.status_code}"

    def test_content_b_immutability_verified_after_attacks(self, db_session, setup_two_tenants):
        """Xác thực tính toàn vẹn: Content B không bị thay đổi sau các cuộc tấn công."""
        data = setup_two_tenants
        refreshed = db_session.query(MarketingContent).filter(MarketingContent.id == data["content_b"].id).first()
        assert refreshed.title == "Private Content Tenant B"
        assert refreshed.body == "Confidential Marketing Asset for Tenant B"

    def test_legitimate_tenant_b_workflow_succeeds(self, client, db_session, setup_two_tenants):
        """Thành viên hợp lệ của Tenant B thực hiện toàn bộ vòng đời nội dung thành công."""
        data = setup_two_tenants
        content_b = data["content_b"]
        headers_b_mkt = make_auth_headers(data["user_b_mkt"])
        headers_b_mgr = make_auth_headers(data["user_b_mgr"])

        # 1. Submit by Tenant B Marketer
        r_sub = client.post(f"/api/v1/contents/{content_b.id}/submit", headers=headers_b_mkt)
        assert r_sub.status_code == 200
        assert r_sub.json()["status"] == "IN_REVIEW"

        # 2. Approve by Tenant B Manager
        r_app = client.post(f"/api/v1/contents/{content_b.id}/approve", headers=headers_b_mgr)
        assert r_app.status_code == 200
        assert r_app.json()["status"] == "APPROVED"

        # 3. Publish by Tenant B Manager
        r_pub = client.post(f"/api/v1/contents/{content_b.id}/publish", headers=headers_b_mgr)
        assert r_pub.status_code == 200
        assert r_pub.json()["status"] == "PUBLISHED"


# ==============================================================================
# ATTACK SCENARIO 4: Production Database Reset Exploit
# ==============================================================================
class TestAttackScenario4_ProductionDatabaseResetExploit:
    """Kiểm thử đối kháng: Khai thác gọi hàm reset_db() hoặc init_db(reset=True)
    trong môi trường production.
    Hệ thống bắt buộc từ chối và ném RuntimeError, tuyệt đối KHÔNG drop tables hay xóa dữ liệu.
    """

    @pytest.fixture
    def test_db_with_data(self):
        """Tạo isolated engine in-memory có sẵn schema và dữ liệu."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=engine)
        # Nạp dữ liệu mẫu
        CustomSession = sessionmaker(bind=engine)
        session = CustomSession()
        test_user = User(
            email="prod_customer@company.com",
            full_name="Production Customer",
            password_hash=hash_password("Pass@123"),
            role="MARKETER",
            status="ACTIVE"
        )
        session.add(test_user)
        session.commit()
        session.close()

        yield engine
        engine.dispose()

    def test_attack_reset_db_blocked_in_production_env_var(self, test_db_with_data, monkeypatch):
        """Gọi reset_db() khi biến môi trường ENVIRONMENT=production -> Bị chặn và ném RuntimeError."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        assert is_production_env() is True

        with pytest.raises(RuntimeError, match="Database reset is forbidden in production environment"):
            reset_db(db_engine=test_db_with_data)

        # Kiểm tra bảng và dữ liệu vẫn nguyên vẹn
        CustomSession = sessionmaker(bind=test_db_with_data)
        session = CustomSession()
        user = session.query(User).filter(User.email == "prod_customer@company.com").first()
        assert user is not None, "Vulnerability! Production user data was deleted by reset_db()!"
        session.close()

    def test_attack_reset_db_blocked_in_production_app_env(self, test_db_with_data, monkeypatch):
        """Gọi reset_db() khi APP_ENV=production -> Bị chặn và ném RuntimeError."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("APP_ENV", "production")
        assert is_production_env() is True

        with pytest.raises(RuntimeError, match="Database reset is forbidden in production environment"):
            reset_db(db_engine=test_db_with_data)

        CustomSession = sessionmaker(bind=test_db_with_data)
        session = CustomSession()
        assert session.query(User).count() == 1
        session.close()

    def test_attack_init_db_reset_true_blocked_in_production(self, test_db_with_data, monkeypatch):
        """Gọi init_db(reset=True) khi ở production -> Bị chặn ngay từ bước reset_db()."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        with pytest.raises(RuntimeError, match="Database reset is forbidden in production environment"):
            seed_init_db(reset=True, db_engine=test_db_with_data)

    def test_init_db_safe_default_preserves_production_data(self, test_db_with_data, monkeypatch):
        """Khởi tạo init_db(reset=False) mặc định không làm mất dữ liệu sản xuất."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        seed_init_db(reset=False, db_engine=test_db_with_data)

        CustomSession = sessionmaker(bind=test_db_with_data)
        session = CustomSession()
        user = session.query(User).filter(User.email == "prod_customer@company.com").first()
        assert user is not None, "Safe init_db() inadvertently deleted production customer data!"
        session.close()


# ==============================================================================
# ATTACK SCENARIO 5: Insecure Secrets Detection & Startup Hardening
# ==============================================================================
class TestAttackScenario5_InsecureSecretsDetection:
    """Kiểm thử đối kháng: Phát hiện cấu hình bí mật không an toàn khi khởi động.
    validate_security_configuration() bắt buộc chặn (raise RuntimeError) nếu:
    - Sử dụng SECRET_KEY placeholder mặc định
    - Độ dài khóa < 32 ký tự
    - Khóa rỗng hoặc None
    - BYOK_ENCRYPTION_KEY không an toàn trong production
    Chỉ cho phép khởi động khi khóa đạt chuẩn bảo mật (>= 32 ký tự, non-placeholder).
    """

    @pytest.mark.parametrize("bad_secret", [
        "aia331-secret-key-change-in-production-super-secure",
        "aia331-super-secret-production-key-change-it",
        "your-super-secret-jwt-key",
        "change-me",
        "changethisinproduction",
        "secret",
        "admin",
        "12345678",
        "custom-placeholder-change-in-production-long-enough-32-chars",
        "short",
        "1234567890123456789012345678901",  # 31 ký tự (< 32)
    ])
    def test_attack_insecure_secret_key_rejected_in_production(self, bad_secret):
        """Cấu hình SECRET_KEY không an toàn bị từ chối khởi động trên production."""
        s = Settings(
            APP_ENV="production",
            SECRET_KEY=bad_secret,
            JWT_SECRET_KEY=None,
            BYOK_ENCRYPTION_KEY=None,
        )
        with pytest.raises(RuntimeError):
            validate_security_configuration(s, enforce_production=True)

    def test_attack_empty_secrets_rejected_in_production(self):
        """Cấu hình khóa rỗng bị từ chối khởi động trên production."""
        s = Settings(
            APP_ENV="production",
            SECRET_KEY="",
            JWT_SECRET_KEY="",
            BYOK_ENCRYPTION_KEY="",
        )
        with pytest.raises(RuntimeError, match="không được để trống"):
            validate_security_configuration(s, enforce_production=True)

    def test_attack_insecure_byok_key_rejected_in_production(self):
        """Cấu hình JWT_SECRET_KEY hợp lệ nhưng BYOK_ENCRYPTION_KEY không an toàn."""
        valid_jwt = "a-very-secure-production-jwt-secret-key-that-is-over-32-characters!!"
        s = Settings(
            APP_ENV="production",
            SECRET_KEY="another-very-secure-master-secret-key-over-32-chars-long!",
            JWT_SECRET_KEY=valid_jwt,
            BYOK_ENCRYPTION_KEY="short-byok",
        )
        with pytest.raises(RuntimeError, match="độ dài nhỏ hơn 32 ký tự"):
            validate_security_configuration(s, enforce_production=True)

    def test_genuine_secure_configuration_accepted_in_production(self):
        """Cấu hình chứa các khóa bí mật thực sự an toàn (>= 32 ký tự, non-placeholder) được duyệt."""
        valid_jwt = "production-jwt-key-9f8e7d6c5b4a392817263544778899aabbccddeeff"
        valid_byok = Fernet.generate_key().decode("utf-8")
        master_secret = "master-production-key-9f8e7d6c5b4a392817263544778899aabbccddeeff"

        s = Settings(
            APP_ENV="production",
            SECRET_KEY=master_secret,
            JWT_SECRET_KEY=valid_jwt,
            BYOK_ENCRYPTION_KEY=valid_byok,
        )
        assert validate_security_configuration(s, enforce_production=True) is True

    def test_development_mode_tolerates_defaults_with_warning(self):
        """Chế độ development/test không ném lỗi fatal đối với khóa mặc định."""
        dev_s = Settings(
            APP_ENV="development",
            SECRET_KEY="aia331-secret-key-change-in-production-super-secure",
        )
        result = validate_security_configuration(dev_s, enforce_production=False)
        assert result in (True, False)
