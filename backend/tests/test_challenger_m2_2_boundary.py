"""
Empirical Boundary & Stress Adversarial Test Suite for Milestone 2: Deep 3-Channel AI Creative Engine (R2)
Author: Challenger 2 (Boundary & Stress Challenger)
Covers:
  - Brief boundary testing (empty, whitespace, 5000+ chars, 10000 max_length, 100k stress, unicode/emojis)
  - Channels array boundary testing (empty, invalid, mixed, case insensitivity, injections, non-list types)
  - Authentication boundary testing (missing, malformed, expired, forged secret, disabled user)
  - Multi-tenant workspace authorization (non-member marketer, cross-workspace manager, agency_manager role)
  - SQLite ai_logs persistence verification (task_type='OMNICHANNEL', model, user_id, campaign_id)
"""

import json
from datetime import datetime, timedelta, timezone
import pytest
import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.entities import (
    User, Workspace, WorkspaceMember, BrandKit, Campaign, CampaignMember, AILog, Product, ProductCategory
)


@pytest.fixture
def manager_headers(client: TestClient):
    resp = client.post("/api/v1/auth/login", json={"email": "manager@ictu.edu.vn", "password": "Manager@123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def marketer_headers(client: TestClient):
    resp = client.post("/api/v1/auth/login", json={"email": "marketer@ictu.edu.vn", "password": "Marketer@123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def setup_ai_service():
    from app.services.ai.ai_service import ai_service
    ai_service.api_key = ""
    ai_service.fallback_enabled = True
    yield
    del ai_service.api_key
    del ai_service.fallback_enabled


class TestBriefBoundaryAndStress:
    """Nhiệm vụ 1: Thử thách các ca biên dị thường của tham số 'brief'."""

    def test_01_brief_empty_string_fails_422(self, client: TestClient, manager_headers):
        """Brief rỗng '' phải trả về HTTP 422 Unprocessable Entity."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "",
            "target_audience": "Đại chúng"
        }, headers=manager_headers)
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_02_brief_whitespace_spaces_only_fails_422(self, client: TestClient, manager_headers):
        """Brief chỉ chứa khoảng trắng '   ' phải trả về HTTP 422."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "      ",
            "target_audience": "Đại chúng"
        }, headers=manager_headers)
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_03_brief_whitespace_tabs_newlines_fails_422(self, client: TestClient, manager_headers):
        """Brief chứa tab, xuống dòng '\\t\\n\\r  \\n' phải trả về HTTP 422."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "\t\n  \r\n \t",
            "target_audience": "Đại chúng"
        }, headers=manager_headers)
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_04_brief_missing_or_none_fails_422(self, client: TestClient, manager_headers):
        """Brief bị bỏ qua hoàn toàn hoặc bằng None phải trả về HTTP 422."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "target_audience": "Đại chúng"
        }, headers=manager_headers)
        assert resp.status_code == 422

        resp2 = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": None,
            "target_audience": "Đại chúng"
        }, headers=manager_headers)
        assert resp2.status_code == 422

    def test_05_brief_boundary_5000_chars_handled_safely(self, client: TestClient, manager_headers):
        """Brief cực dài (5000+ ký tự) xử lý an toàn (HTTP 200 hoặc 422), tuyệt đối không gây 500 crash."""
        large_brief = "Chiến dịch tuyển sinh công nghệ cao: " + (" MarketFlow " * 420)
        assert len(large_brief) >= 5000
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": large_brief,
            "target_audience": "Kỹ sư và sinh viên"
        }, headers=manager_headers)
        assert resp.status_code in (200, 422), f"Unexpected status {resp.status_code}: {resp.text}"
        assert resp.status_code != 500, "Server must NOT crash with HTTP 500 on 5000+ char brief!"

    def test_06_brief_boundary_10000_chars_handled_safely(self, client: TestClient, manager_headers):
        """Brief đúng giới hạn 10000 ký tự (Pydantic max_length) xử lý an toàn (không crash 500)."""
        ten_k_brief = "A" * 10000
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": ten_k_brief,
            "target_audience": "Test Audience"
        }, headers=manager_headers)
        assert resp.status_code in (200, 422)
        assert resp.status_code != 500

    def test_07_brief_over_10000_chars_rejected_cleanly_422(self, client: TestClient, manager_headers):
        """Brief vượt quá 10000 ký tự (10001+ chars) phải bị từ chối sạch sẽ với HTTP 422 mà không 500."""
        oversized_brief = "A" * 10005
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": oversized_brief,
            "target_audience": "Test Audience"
        }, headers=manager_headers)
        assert resp.status_code == 422, f"Expected 422 for >10000 chars, got {resp.status_code}"

    def test_08_brief_extreme_stress_100k_chars_no_crash(self, client: TestClient, manager_headers):
        """Stress test: Brief 100,000 ký tự (DDoS payload) bị từ chối HTTP 422, server hoàn toàn an toàn."""
        massive_payload = "B" * 100000
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": massive_payload
        }, headers=manager_headers)
        assert resp.status_code == 422
        assert resp.status_code != 500

    def test_09_brief_unicode_and_vietnamese_accents(self, client: TestClient, manager_headers):
        """Brief chứa tiếng Việt đầy đủ dấu, emoji, ký tự đặc biệt được xử lý chuẩn xác."""
        special_brief = "🌟 Chiến dịch ra mắt sản phẩm Đột Phá AI 2026! 🚀 Giá trị cốt lõi: 'Học thật - Làm thật & Chuyển đổi số'."
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": special_brief,
            "channels": ["facebook"]
        }, headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "facebook" in data and data["facebook"] is not None


class TestChannelsBoundaryAndValidation:
    """Nhiệm vụ 1: Thử thách các ca biên dị thường của tham số 'channels'."""

    def test_10_channels_empty_array_fails_422(self, client: TestClient, manager_headers):
        """Mảng channels rỗng [] phải trả về HTTP 422."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Chiến dịch quảng cáo",
            "channels": []
        }, headers=manager_headers)
        assert resp.status_code == 422, f"Expected 422 for empty channels [], got {resp.status_code}"

    def test_11_channels_unknown_channel_fails_422(self, client: TestClient, manager_headers):
        """Mảng channels chứa kênh không hợp lệ ['unknown_channel_xyz'] phải trả về HTTP 422."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Chiến dịch quảng cáo",
            "channels": ["unknown_channel_xyz"]
        }, headers=manager_headers)
        assert resp.status_code == 422, f"Expected 422 for invalid channel, got {resp.status_code}"

    def test_12_channels_mixed_valid_and_invalid_fails_422(self, client: TestClient, manager_headers):
        """Mảng channels chứa cả kênh hợp lệ và không hợp lệ ['facebook', 'telegram_bot'] phải trả về HTTP 422."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Chiến dịch quảng cáo",
            "channels": ["facebook", "telegram_bot"]
        }, headers=manager_headers)
        assert resp.status_code == 422, f"Expected 422 for mixed channels, got {resp.status_code}"

    def test_13_channels_case_insensitivity_and_whitespace(self, client: TestClient, manager_headers):
        """Kênh truyền dạng chữ hoa hoặc có khoảng trắng [' FACEBOOK ', 'TikTok', 'EMAIL'] được chuẩn hóa."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Chiến dịch kiểm tra chuẩn hóa kênh hoa thường",
            "channels": [" FACEBOOK ", "TikTok", "EMAIL"]
        }, headers=manager_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("facebook") is not None
        assert data.get("tiktok") is not None
        assert data.get("email") is not None

    def test_14_channels_with_malicious_injections_fails_422(self, client: TestClient, manager_headers):
        """Mảng channels chứa injection chuỗi như script/path traversal phải trả về HTTP 422."""
        for malicious_channel in ["<script>alert(1)</script>", "../../../etc/passwd", "' OR '1'='1"]:
            resp = client.post("/api/v1/ai/omnichannel", json={
                "campaign_id": 1,
                "brief": "Chiến dịch kiểm tra injection",
                "channels": [malicious_channel]
            }, headers=manager_headers)
            assert resp.status_code == 422, f"Payload {malicious_channel} must be rejected with 422!"

    def test_15_channels_non_list_type_fails_422(self, client: TestClient, manager_headers):
        """channels gửi kiểu dữ liệu sai (string, integer, dict) phải trả về HTTP 422."""
        for invalid_val in ["facebook", 123, {"channel": "facebook"}]:
            resp = client.post("/api/v1/ai/omnichannel", json={
                "campaign_id": 1,
                "brief": "Chiến dịch kiểm tra sai kiểu dữ liệu channels",
                "channels": invalid_val
            }, headers=manager_headers)
            assert resp.status_code == 422


class TestAuthenticationSecurityBoundary:
    """Nhiệm vụ 1: Thử thách các ca biên bảo mật Token và Authentication."""

    def test_16_missing_token_blocked_401(self, client: TestClient):
        """Không có token xác thực -> Phải chặn HTTP 401 Unauthorized."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Bản brief hợp lệ nhưng không gửi token"
        })
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_17_malformed_token_blocked_401(self, client: TestClient):
        """Token rác hoặc malformed -> Phải chặn HTTP 401."""
        bad_headers = {"Authorization": "Bearer not.a.valid.jwt.payload"}
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Bản brief với token giả mạo"
        }, headers=bad_headers)
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_18_missing_bearer_prefix_blocked_401(self, client: TestClient, manager_headers):
        """Token thiếu tiền tố Bearer -> Phải chặn HTTP 401."""
        token = manager_headers["Authorization"].replace("Bearer ", "")
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Bản brief không có tiền tố Bearer"
        }, headers={"Authorization": token})
        assert resp.status_code == 401

    def test_19_expired_token_blocked_401(self, client: TestClient):
        """Token đã hết hạn (expired) -> Phải chặn HTTP 401."""
        expire = datetime.now(timezone.utc) - timedelta(hours=2)
        payload = {"sub": "1", "exp": expire}
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Bản brief với token hết hạn"
        }, headers={"Authorization": f"Bearer {expired_token}"})
        assert resp.status_code == 401

    def test_20_forged_secret_token_blocked_401(self, client: TestClient):
        """Token ký bằng Secret Key khác -> Phải chặn HTTP 401."""
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        payload = {"sub": "1", "exp": expire}
        forged_token = jwt.encode(payload, "ATTACKER_SECRET_KEY_NEVER_MATCH", algorithm=settings.ALGORITHM)
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Bản brief với token ký bằng secret giả"
        }, headers={"Authorization": f"Bearer {forged_token}"})
        assert resp.status_code == 401

    def test_21_disabled_user_token_blocked_403(self, client: TestClient, db_session: Session):
        """User có trạng thái DISABLED trong CSDL dù có token hợp lệ cũng phải bị chặn HTTP 403."""
        disabled_user = User(
            email="disabled_user@ictu.edu.vn",
            full_name="Bị Khóa Tài Khoản",
            password_hash=hash_password("Pass@123"),
            role="MARKETER",
            status="DISABLED"
        )
        db_session.add(disabled_user)
        db_session.commit()
        db_session.refresh(disabled_user)

        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        token = jwt.encode({"sub": str(disabled_user.id), "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Thử nghiệm tài khoản bị vô hiệu hóa"
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403, f"Disabled user must be blocked with 403, got {resp.status_code}"


class TestMultiTenantWorkspaceAuthorization:
    """Nhiệm vụ 1: Thử thách cách ly đa không gian làm việc (Multi-tenant Workspace Isolation)."""

    def test_22_marketer_not_in_campaign_workspace_blocked_403(self, client: TestClient, db_session: Session):
        """User MARKETER thuộc Workspace 2 cố ý gọi AI omnichannel trên Campaign thuộc Workspace 1 -> Phải chặn HTTP 403!"""
        ws2 = Workspace(id=2, name="Client B Workspace", slug="client-b", owner_id=1, status="ACTIVE")
        db_session.add(ws2)
        db_session.commit()

        mkt2 = User(
            email="marketer_ws2@example.com",
            full_name="Marketer WS2",
            password_hash=hash_password("Pass123!"),
            role="MARKETER",
            status="ACTIVE"
        )
        db_session.add(mkt2)
        db_session.commit()
        db_session.refresh(mkt2)

        db_session.add(WorkspaceMember(workspace_id=ws2.id, user_id=mkt2.id, role="MARKETER"))
        db_session.commit()

        resp = client.post("/api/v1/auth/login", json={"email": "marketer_ws2@example.com", "password": "Pass123!"})
        assert resp.status_code == 200
        token_ws2 = resp.json()["access_token"]

        resp_attack = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Cố gắng truy cập tài nguyên của Workspace khác"
        }, headers={"Authorization": f"Bearer {token_ws2}"})

        assert resp_attack.status_code == 403, (
            f"VULNERABILITY: User không thuộc workspace của campaign phải bị chặn HTTP 403! Got {resp_attack.status_code}"
        )

    def test_23_cross_workspace_manager_leak_challenge(self, client: TestClient, db_session: Session):
        """Thử thách: Manager của Workspace 3 gọi AI Omnichannel trên Campaign thuộc Workspace 2.
        PROJECT.md quy định:
          - Workspace Isolation: campaigns & contents link to workspace_id. All queries strictly filter by active workspace_id.
          - Yêu cầu kiểm thử từ Orchestrator: 'User không thuộc workspace của campaign -> Phải chặn HTTP 403!'
        Hành vi thực tế phát hiện:
          check_campaign_access_for_ai (ai.py:26) kiểm tra:
             if user.role in ('ADMIN', 'MANAGER'): return campaign
          Hệ thống KHÔNG kiểm tra xem Manager có thuộc workspace_id của Campaign (> 1) hay không!
          Do đó, Manager của Workspace 3 có thể tự do tạo AI cho Campaign của Workspace 2!
        """
        # Tạo Workspace 2 và Campaign 3 (thuộc Workspace 2)
        ws2 = Workspace(id=2, name="Workspace Client 2", slug="ws-client-2", owner_id=1, status="ACTIVE")
        db_session.add(ws2)
        db_session.commit()

        cat = db_session.query(ProductCategory).first()
        prod2 = Product(category_id=cat.id, name="Sản phẩm WS2", status="ACTIVE")
        db_session.add(prod2)
        db_session.commit()

        camp3 = Campaign(
            id=3,
            workspace_id=ws2.id,
            product_id=prod2.id,
            owner_id=1,
            name="Chiến dịch Bí mật của Client 2",
            objective="Mục tiêu nội bộ",
            audience="Khách hàng WS2",
            start_date="2026-10-01",
            end_date="2026-10-31",
            budget=5000000.0,
            status="ACTIVE"
        )
        db_session.add(camp3)
        db_session.commit()

        # Tạo Workspace 3 và Manager 3 (chỉ có quyền tại Workspace 3)
        ws3 = Workspace(id=3, name="Workspace Client 3", slug="ws-client-3", owner_id=1, status="ACTIVE")
        db_session.add(ws3)
        db_session.commit()

        mgr3 = User(
            email="manager_ws3@example.com",
            full_name="Manager WS3 Only",
            password_hash=hash_password("Pass123!"),
            role="MANAGER",
            status="ACTIVE"
        )
        db_session.add(mgr3)
        db_session.commit()
        db_session.refresh(mgr3)

        db_session.add(WorkspaceMember(workspace_id=ws3.id, user_id=mgr3.id, role="AGENCY_MANAGER"))
        db_session.commit()

        resp_login = client.post("/api/v1/auth/login", json={"email": "manager_ws3@example.com", "password": "Pass123!"})
        assert resp_login.status_code == 200
        token_mgr3 = resp_login.json()["access_token"]

        resp_cross = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 3,
            "brief": "Xâm nhập tạo AI cho campaign của Workspace 2"
        }, headers={"Authorization": f"Bearer {token_mgr3}"})

        # Đo lường thực chứng kết quả:
        is_isolated = (resp_cross.status_code == 403)
        is_leaked = (resp_cross.status_code == 200)

        # Ghi nhận lỗ hổng thực chứng
        assert is_isolated, (
            f"[SECURITY FLAW REPRODUCED] User Manager WS3 không thuộc workspace của campaign 3 (WS2), "
            f"nhưng endpoint /api/v1/ai/omnichannel trả về HTTP {resp_cross.status_code} thay vì HTTP 403 Forbidden! "
            f"Cơ chế check_campaign_access_for_ai tại backend/app/api/v1/ai.py line 26 bỏ qua kiểm tra workspace_id."
        )

    def test_24_agency_manager_role_denied_in_own_workspace(self, client: TestClient, db_session: Session):
        """Thử thách: Tài khoản có role 'AGENCY_MANAGER' (M1 spec) tại Workspace 2
        gọi AI Omnichannel cho Campaign trong chính workspace của mình (do Marketer tạo).
        Hành vi phát hiện:
          check_campaign_access_for_ai chỉ cho qua nếu user.role in ('ADMIN', 'MANAGER').
          Role 'AGENCY_MANAGER' không nằm trong danh sách này, dẫn đến Quản lý Agency bị từ chối 403!
        """
        ws2 = Workspace(id=2, name="Workspace Client 2", slug="ws-client-2", owner_id=1, status="ACTIVE")
        db_session.add(ws2)
        db_session.commit()

        # Marketer tạo campaign
        cat = db_session.query(ProductCategory).first()
        prod2 = Product(category_id=cat.id, name="Sản phẩm WS2", status="ACTIVE")
        db_session.add(prod2)
        db_session.commit()

        camp4 = Campaign(
            id=4,
            workspace_id=ws2.id,
            product_id=prod2.id,
            owner_id=2,  # Marketer
            name="Chiến dịch của Marketer",
            objective="Mục tiêu",
            audience="Khán giả",
            start_date="2026-10-01",
            end_date="2026-10-31",
            budget=5000000.0,
            status="ACTIVE"
        )
        db_session.add(camp4)
        db_session.commit()

        # Agency Manager của Workspace 2
        agency_mgr = User(
            email="agency_mgr_ws2@example.com",
            full_name="Agency Manager WS2",
            password_hash=hash_password("Pass123!"),
            role="AGENCY_MANAGER",
            status="ACTIVE"
        )
        db_session.add(agency_mgr)
        db_session.commit()
        db_session.refresh(agency_mgr)

        db_session.add(WorkspaceMember(workspace_id=ws2.id, user_id=agency_mgr.id, role="AGENCY_MANAGER"))
        db_session.commit()

        resp_login = client.post("/api/v1/auth/login", json={"email": "agency_mgr_ws2@example.com", "password": "Pass123!"})
        assert resp_login.status_code == 200
        token_agency_mgr = resp_login.json()["access_token"]

        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 4,
            "brief": "Agency Manager tạo nội dung cho campaign của workspace mình"
        }, headers={"Authorization": f"Bearer {token_agency_mgr}"})

        # Agency manager đáng lẽ PHẢI được phép (HTTP 200), nhưng lại bị chặn 403
        assert resp.status_code == 200, (
            f"[ROLE FLAW REPRODUCED] User role AGENCY_MANAGER của Workspace 2 bị chặn HTTP {resp.status_code} "
            f"khi truy cập campaign trong chính workspace của mình do check_campaign_access_for_ai không nhận diện AGENCY_MANAGER!"
        )


class TestDatabaseLoggingAndPersistence:
    """Nhiệm vụ 2: Thử nghiệm lưu trữ và ghi nhật ký trong SQLite DB (ai_logs)."""

    def test_25_ai_logs_record_created_with_omnichannel_task_type(self, client: TestClient, manager_headers, db_session: Session):
        """Gọi endpoint omnichannel thành công -> Bản ghi ai_logs được tạo với task_type='OMNICHANNEL'."""
        count_before = db_session.query(AILog).filter(AILog.task_type == "OMNICHANNEL").count()

        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Chiến dịch kiểm tra ghi nhật ký audit log trong CSDL SQLite",
            "channels": ["facebook", "tiktok"]
        }, headers=manager_headers)
        assert resp.status_code == 200

        logs = db_session.query(AILog).filter(AILog.task_type == "OMNICHANNEL").order_by(AILog.id.desc()).all()
        assert len(logs) == count_before + 1, "Phải có đúng 1 bản ghi mới trong ai_logs!"

        latest_log = logs[0]
        assert latest_log.task_type == "OMNICHANNEL"
        assert latest_log.campaign_id == 1
        assert latest_log.result_status == "SUCCESS"
        assert "gemini" in latest_log.model.lower() or "flash" in latest_log.model.lower() or "fallback" in latest_log.model.lower()
        assert latest_log.created_at is not None
        assert latest_log.prompt_version == "v3"

    def test_26_ai_logs_persisted_for_freeform_omnichannel(self, client: TestClient, manager_headers, db_session: Session):
        """Gọi AI Omnichannel không kèm campaign_id (tự do) -> Bản ghi ai_logs vẫn được tạo với campaign_id=None."""
        count_before = db_session.query(AILog).filter(AILog.task_type == "OMNICHANNEL").count()

        resp = client.post("/api/v1/ai/omnichannel", json={
            "brief": "Chiến dịch độc lập tự do không gắn campaign",
            "channels": ["facebook"]
        }, headers=manager_headers)
        assert resp.status_code == 200

        latest_log = db_session.query(AILog).filter(AILog.task_type == "OMNICHANNEL").order_by(AILog.id.desc()).first()
        assert latest_log is not None
        assert latest_log.task_type == "OMNICHANNEL"
        assert latest_log.campaign_id is None
        assert latest_log.result_status == "SUCCESS"

    def test_27_ai_logs_api_endpoint_queryable(self, client: TestClient, manager_headers):
        """Kiểm tra endpoint GET /api/v1/ai/logs trả về các bản ghi OMNICHANNEL đã ghi."""
        resp_gen = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Tạo nội dung để kiểm tra endpoint logs",
            "channels": ["facebook"]
        }, headers=manager_headers)
        assert resp_gen.status_code == 200

        resp = client.get("/api/v1/ai/logs", headers=manager_headers)
        assert resp.status_code == 200
        logs = resp.json()
        assert isinstance(logs, list)
        omni_logs = [l for l in logs if l.get("task_type") == "OMNICHANNEL"]
        assert len(omni_logs) > 0, "Endpoint GET /api/v1/ai/logs phải trả về các log có task_type='OMNICHANNEL'"
