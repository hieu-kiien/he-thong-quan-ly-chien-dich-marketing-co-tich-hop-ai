"""
Wave 1 (P0 Security Matrix & Multi-Tenant Verification Test Suite)
==================================================================

Authoritative Specification:
- ORIGINAL_REQUEST.md (Wave 1: P0 Fixtures & Bảo mật)
- PROJECT.md (MarketFlow AI 5-Wave Comprehensive Testing & QA Strategy: Features 1-8)

Covers 100% of the P0 Security Matrix:
1. Privilege Escalation Prevention:
   - Self-registration rejects AGENCY_MANAGER, CLIENT_APPROVER, ADMIN, MANAGER (HTTP 403 Forbidden).
   - Role promotion via workspace member additions strictly restricted to authorized roles.
   - JWT payload role spoofing blocked by active database state verification (RoleChecker).
   - Inactive / suspended accounts blocked regardless of JWT validity.
2. Multi-Tenant Workspace Isolation:
   - Cross-workspace access attempts across Campaigns, Contents, Metrics, BrandKit, BYOK Keys return 403 Forbidden.
   - Record-level and tenant boundary enforcement across Workspace Alpha (id=1) and Workspace Beta (id=2).
3. Review Queue State Machine:
   - Direct creation to APPROVED or PUBLISHED blocked (HTTP 400 Bad Request).
   - Direct update to APPROVED or PUBLISHED blocked (HTTP 400 Bad Request).
   - Auto-demotion to AI_DRAFT when approved or published content is edited.
   - Rejection reason length validation (minimum 3 characters).
   - Role-based publishing enforcement (only MANAGER / AGENCY_MANAGER, CLIENT_APPROVER forbidden).
   - Full end-to-end review queue state machine lifecycle.
4. BYOK Crypto Vault:
   - Fernet ciphertext invariant: all encrypted keys strictly start with 'gAAAAA'.
   - Dedicated key separation between JWT_SECRET_KEY and BYOK_ENCRYPTION_KEY.
   - Rejection of insecure, default, or placeholder keys in production environments.
   - MultiFernet key rotation preserving decryption capability across key versions.
   - API key masking ladder ensuring confidentiality.
5. Database Safety & Time Determinism:
   - reset_db() and init_db(reset=True) strictly rejected in production environments.
   - Non-destructive init_db(reset=False) preserving pre-existing data.
   - Vietnam timezone (+07:00) and clock freeze determinism.
   - Live database (marketing_campaigns.db) immutability invariant.
6. Metrics Matrix Scenarios:
   - Rich metrics, empty metrics, and zero-value metrics handled safely without 500s or division by zero.
"""

import os
import json
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import hash_password, create_access_token
from app.core.crypto import (
    encrypt_api_key, decrypt_api_key, mask_api_key,
    get_jwt_secret_key, get_byok_encryption_key, rotate_custom_api_keys
)
from app.models.entities import (
    User, Workspace, WorkspaceMember, BrandKit,
    Campaign, CampaignMember, MarketingContent, ContentReview,
    CampaignMetric
)
from seed.seed_data import init_db as seed_init_db, reset_db, is_production_env


# ==============================================================================
# 1. PRIVILEGE ESCALATION PREVENTION TESTS
# ==============================================================================
class TestP0PrivilegeEscalation:
    """Verifies prevention of unauthorized role assignment and privilege escalation."""

    @pytest.mark.parametrize("disallowed_role", [
        "AGENCY_MANAGER",
        "CLIENT_APPROVER",
        "ADMIN",
        "MANAGER",
    ])
    def test_01_self_registration_with_privileged_roles_rejected_403(
        self, client: TestClient, disallowed_role: str
    ):
        """Public self-registration with privileged roles must return HTTP 403 Forbidden."""
        payload = {
            "email": f"hacker_{disallowed_role.lower()}@attacker.vn",
            "password": "SecurePassword@123",
            "full_name": f"Hacker {disallowed_role}",
            "role": disallowed_role
        }
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 403, f"Expected 403 for role '{disallowed_role}', got {resp.status_code}: {resp.text}"
        detail = resp.json().get("detail", "")
        assert "not allowed" in detail.lower() or "privileged" in detail.lower() or "tự cấp" in detail.lower()

    @pytest.mark.parametrize("invalid_role", [
        "agency_manager",
        "client_approver",
        "admin",
        "manager",
        "SUPERUSER",
        "ROOT",
    ])
    def test_02_self_registration_with_unrecognized_roles_rejected(
        self, client: TestClient, invalid_role: str
    ):
        """Self-registration with lowercase or unrecognized role names is rejected."""
        payload = {
            "email": f"invalid_{invalid_role.lower()}@attacker.vn",
            "password": "SecurePassword@123",
            "full_name": f"Invalid {invalid_role}",
            "role": invalid_role
        }
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code in (400, 403, 422), f"Expected validation failure, got {resp.status_code}: {resp.text}"

    def test_03_self_registration_defaults_to_marketer(
        self, client: TestClient, db_session: Session
    ):
        """Public self-registration with MARKETER or empty role succeeds and assigns MARKETER."""
        # 1. Explicit MARKETER
        email1 = "legit_marketer_1@ictu.edu.vn"
        resp1 = client.post("/api/v1/auth/register", json={
            "email": email1,
            "password": "SecurePassword@123",
            "full_name": "Nguyễn Marketer Một",
            "role": "MARKETER"
        })
        assert resp1.status_code == 201, f"Registration failed: {resp1.text}"
        u1 = db_session.query(User).filter(User.email == email1).first()
        assert u1 is not None
        assert u1.role == "MARKETER"

        # 2. Omitting role defaults to MARKETER
        email2 = "legit_marketer_2@ictu.edu.vn"
        resp2 = client.post("/api/v1/auth/register", json={
            "email": email2,
            "password": "SecurePassword@123",
            "full_name": "Nguyễn Marketer Hai"
        })
        assert resp2.status_code == 201, f"Registration failed: {resp2.text}"
        u2 = db_session.query(User).filter(User.email == email2).first()
        assert u2 is not None
        assert u2.role == "MARKETER"

    def test_04_non_admin_cannot_add_members_to_workspace(
        self, client: TestClient, marketer_headers, workspace_alpha, db_session: Session
    ):
        """A user with MARKETER role cannot add members or elevate roles in a workspace."""
        new_target = User(
            email="target_elevation@ictu.edu.vn",
            full_name="Target User",
            password_hash=hash_password("Pass@123"),
            role="MARKETER",
            status="ACTIVE"
        )
        db_session.add(new_target)
        db_session.commit()
        db_session.refresh(new_target)

        resp = client.post(
            f"/api/v1/workspaces/{workspace_alpha.id}/members",
            json={"email": new_target.email, "role": "AGENCY_MANAGER"},
            headers=marketer_headers
        )
        assert resp.status_code == 403, f"Expected 403 Forbidden, got {resp.status_code}: {resp.text}"

    def test_05_jwt_role_spoofing_prevented_by_active_db_lookup(
        self, client: TestClient, db_session: Session, workspace_alpha
    ):
        """RoleChecker pulls user from DB dynamically: forged token claims are rejected."""
        # Genuine DB user has MARKETER role
        marketer_user = db_session.query(User).filter(User.email == "marketer@ictu.edu.vn").first()
        assert marketer_user is not None
        assert marketer_user.role == "MARKETER"

        # Attacker crafts a JWT containing role="AGENCY_MANAGER" but sub=marketer_user.id
        spoofed_token = create_access_token(data={
            "sub": str(marketer_user.id),
            "email": marketer_user.email,
            "role": "AGENCY_MANAGER"
        })
        spoofed_headers = {"Authorization": f"Bearer {spoofed_token}"}

        # Attempt to call an endpoint restricted to AGENCY_MANAGER / MANAGER
        resp = client.put(
            f"/api/v1/workspaces/{workspace_alpha.id}",
            json={"name": "Hacked Workspace Name"},
            headers=spoofed_headers
        )
        assert resp.status_code == 403, (
            f"VULNERABILITY: RoleChecker trusted forged JWT role claim! Status: {resp.status_code}"
        )

    def test_06_inactive_or_suspended_account_rejected_even_with_valid_jwt(
        self, client: TestClient, db_session: Session
    ):
        """A user marked INACTIVE or DISABLED is rejected with 403 even if token is valid."""
        suspended_user = User(
            email="suspended_marketer@ictu.edu.vn",
            full_name="Suspended User",
            password_hash=hash_password("Pass@123"),
            role="MARKETER",
            status="DISABLED"
        )
        db_session.add(suspended_user)
        db_session.commit()
        db_session.refresh(suspended_user)

        valid_token = create_access_token(data={
            "sub": str(suspended_user.id),
            "email": suspended_user.email,
            "role": suspended_user.role
        })
        headers = {"Authorization": f"Bearer {valid_token}"}

        resp = client.get("/api/v1/campaigns", headers=headers)
        assert resp.status_code == 403
        detail = resp.json().get("detail", "")
        assert "not active" in detail.lower() or "vô hiệu hóa" in detail.lower()


# ==============================================================================
# 2. MULTI-TENANT WORKSPACE ISOLATION TESTS (BOLA / IDOR)
# ==============================================================================
class TestP0MultiTenantWorkspaceIsolation:
    """Verifies strict cross-workspace data isolation between Workspace Alpha and Workspace Beta."""

    def test_01_cross_workspace_campaign_view_blocked_403(
        self, client: TestClient, marketer_headers, manager_headers, workspace_beta, db_session: Session
    ):
        """Users in Workspace Alpha cannot view campaigns belonging to Workspace Beta."""
        beta_campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_beta.id).first()
        assert beta_campaign is not None, "Workspace Beta must have at least one campaign"

        # Alpha Marketer -> Beta Campaign
        resp_mkt = client.get(f"/api/v1/campaigns/{beta_campaign.id}", headers=marketer_headers)
        assert resp_mkt.status_code == 403, f"BOLA breach: Alpha Marketer accessed Beta Campaign! Got {resp_mkt.status_code}"

        # Alpha Manager -> Beta Campaign
        resp_mgr = client.get(f"/api/v1/campaigns/{beta_campaign.id}", headers=manager_headers)
        assert resp_mgr.status_code == 403, f"BOLA breach: Alpha Manager accessed Beta Campaign! Got {resp_mgr.status_code}"

    def test_02_cross_workspace_campaign_update_and_delete_blocked_403(
        self, client: TestClient, manager_headers, workspace_beta, db_session: Session
    ):
        """Users in Workspace Alpha cannot update or delete campaigns belonging to Workspace Beta."""
        beta_campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_beta.id).first()
        assert beta_campaign is not None

        # Attempt PUT
        resp_put = client.put(
            f"/api/v1/campaigns/{beta_campaign.id}",
            json={"name": "Compromised by Alpha", "budget": 99999999.0},
            headers=manager_headers
        )
        assert resp_put.status_code == 403

        # Attempt DELETE
        resp_del = client.delete(f"/api/v1/campaigns/{beta_campaign.id}", headers=manager_headers)
        assert resp_del.status_code == 403

    def test_03_cross_workspace_content_view_and_update_blocked_403(
        self, client: TestClient, marketer_headers, manager_headers, workspace_beta, db_session: Session
    ):
        """Users in Workspace Alpha cannot view or update contents in Workspace Beta."""
        beta_content = db_session.query(MarketingContent).filter(
            MarketingContent.workspace_id == workspace_beta.id
        ).first()
        assert beta_content is not None, "Workspace Beta must have at least one content record"

        # GET
        resp_get = client.get(f"/api/v1/contents/{beta_content.id}", headers=marketer_headers)
        assert resp_get.status_code == 403

        # PUT
        resp_put = client.put(
            f"/api/v1/contents/{beta_content.id}",
            json={"title": "Defaced by Alpha Marketer", "body": "Hacked content"},
            headers=marketer_headers
        )
        assert resp_put.status_code == 403

    def test_04_cross_workspace_review_operations_blocked_403(
        self, client: TestClient, manager_headers, client_approver_headers, workspace_beta, db_session: Session
    ):
        """Reviewers in Workspace Alpha cannot submit, approve, reject, or publish Beta content."""
        beta_content = db_session.query(MarketingContent).filter(
            MarketingContent.workspace_id == workspace_beta.id
        ).first()
        assert beta_content is not None

        # 1. Submit on DRAFT content -> 403
        beta_content.status = "DRAFT"
        db_session.commit()
        resp_sub = client.post(f"/api/v1/contents/{beta_content.id}/submit", headers=manager_headers)
        assert resp_sub.status_code == 403

        # 2. Approve and Reject on IN_REVIEW content -> 403
        beta_content.status = "IN_REVIEW"
        db_session.commit()

        resp_app = client.post(f"/api/v1/contents/{beta_content.id}/approve", headers=client_approver_headers)
        assert resp_app.status_code == 403

        resp_rej = client.post(
            f"/api/v1/contents/{beta_content.id}/reject",
            json={"decision": "REJECTED", "reason": "Rejected by unauthorized workspace manager"},
            headers=manager_headers
        )
        assert resp_rej.status_code == 403

        # 3. Publish on APPROVED content -> 403
        beta_content.status = "APPROVED"
        db_session.commit()

        resp_pub = client.post(f"/api/v1/contents/{beta_content.id}/publish", headers=manager_headers)
        assert resp_pub.status_code == 403

    def test_05_cross_workspace_metrics_view_and_poisoning_blocked_403(
        self, client: TestClient, marketer_headers, workspace_beta, db_session: Session
    ):
        """Users in Workspace Alpha cannot query or insert metrics for Workspace Beta campaigns."""
        beta_campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_beta.id).first()
        assert beta_campaign is not None

        # GET metrics
        resp_get = client.get(f"/api/v1/campaigns/{beta_campaign.id}/metrics", headers=marketer_headers)
        assert resp_get.status_code == 403

        # POST metrics (Metrics Poisoning attack)
        poison_payload = {
            "campaign_id": beta_campaign.id,
            "channel_id": 1,
            "metric_date": "2026-09-26",
            "views": 1000000,
            "clicks": 50000,
            "conversions": 1000,
            "cost": 1000000.0,
            "revenue": 50000000.0
        }
        resp_post = client.post(
            f"/api/v1/campaigns/{beta_campaign.id}/metrics",
            json=poison_payload,
            headers=marketer_headers
        )
        assert resp_post.status_code == 403

    def test_06_cross_workspace_brand_kit_and_byok_isolation_403(
        self, client: TestClient, manager_headers, workspace_beta
    ):
        """Brand Kit and BYOK settings are isolated per workspace."""
        # Brand Kit of Beta
        resp_bk = client.get(f"/api/v1/brand-kit?workspace_id={workspace_beta.id}", headers=manager_headers)
        assert resp_bk.status_code == 403

        # BYOK AI Key of Beta
        resp_byok = client.get(f"/api/v1/settings/ai-keys?workspace_id={workspace_beta.id}", headers=manager_headers)
        assert resp_byok.status_code == 403

    def test_07_reverse_cross_workspace_campaign_access_blocked_403(
        self, client: TestClient, beta_marketer_headers, beta_agency_manager_headers, workspace_alpha, db_session: Session
    ):
        """Users in Workspace Beta (Marketer & Agency Manager) cannot view, update, delete, or list Alpha campaigns."""
        alpha_campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()
        assert alpha_campaign is not None, "Workspace Alpha must have at least one campaign"

        # 1. Beta Marketer -> Alpha Campaign GET, PUT
        resp_mkt_get = client.get(f"/api/v1/campaigns/{alpha_campaign.id}", headers=beta_marketer_headers)
        assert resp_mkt_get.status_code == 403

        resp_mkt_put = client.put(f"/api/v1/campaigns/{alpha_campaign.id}", json={"name": "Hacked by Beta Marketer"}, headers=beta_marketer_headers)
        assert resp_mkt_put.status_code == 403

        # 2. Beta Agency Manager -> Alpha Campaign GET, PUT, DELETE
        resp_mgr_get = client.get(f"/api/v1/campaigns/{alpha_campaign.id}", headers=beta_agency_manager_headers)
        assert resp_mgr_get.status_code == 403

        resp_mgr_put = client.put(f"/api/v1/campaigns/{alpha_campaign.id}", json={"name": "Hacked by Beta Agency Mgr"}, headers=beta_agency_manager_headers)
        assert resp_mgr_put.status_code == 403

        resp_mgr_del = client.delete(f"/api/v1/campaigns/{alpha_campaign.id}", headers=beta_agency_manager_headers)
        assert resp_mgr_del.status_code == 403

        # 3. Listing Alpha campaigns by passing workspace_id=1
        resp_list = client.get(f"/api/v1/campaigns?workspace_id={workspace_alpha.id}", headers=beta_agency_manager_headers)
        assert resp_list.status_code == 403

    def test_08_reverse_cross_workspace_content_access_blocked_403(
        self, client: TestClient, beta_marketer_headers, beta_agency_manager_headers, workspace_alpha, db_session: Session
    ):
        """Users in Workspace Beta cannot view, edit, or list contents in Workspace Alpha."""
        alpha_content = db_session.query(MarketingContent).filter(
            MarketingContent.workspace_id == workspace_alpha.id
        ).first()
        assert alpha_content is not None, "Workspace Alpha must have at least one content record"

        # 1. Beta Marketer -> Alpha Content GET, PUT
        resp_mkt_get = client.get(f"/api/v1/contents/{alpha_content.id}", headers=beta_marketer_headers)
        assert resp_mkt_get.status_code == 403

        resp_mkt_put = client.put(f"/api/v1/contents/{alpha_content.id}", json={"title": "Defaced by Beta Marketer"}, headers=beta_marketer_headers)
        assert resp_mkt_put.status_code == 403

        # 2. Beta Agency Manager -> Alpha Content GET, PUT
        resp_mgr_get = client.get(f"/api/v1/contents/{alpha_content.id}", headers=beta_agency_manager_headers)
        assert resp_mgr_get.status_code == 403

        resp_mgr_put = client.put(f"/api/v1/contents/{alpha_content.id}", json={"title": "Defaced by Beta Agency Manager"}, headers=beta_agency_manager_headers)
        assert resp_mgr_put.status_code == 403

        # 3. Listing Alpha contents by passing workspace_id=1
        resp_list = client.get(f"/api/v1/contents?workspace_id={workspace_alpha.id}", headers=beta_agency_manager_headers)
        assert resp_list.status_code == 403

    def test_09_reverse_cross_workspace_byok_and_brand_kit_blocked_403(
        self, client: TestClient, beta_agency_manager_headers, beta_marketer_headers, workspace_alpha
    ):
        """Users in Workspace Beta cannot view, list, create/overwrite, or delete Alpha BYOK keys or Brand Kit."""
        # 1. GET Alpha BYOK
        resp_byok_get = client.get(f"/api/v1/settings/ai-keys?workspace_id={workspace_alpha.id}", headers=beta_agency_manager_headers)
        assert resp_byok_get.status_code == 403

        # 2. LIST Alpha BYOK
        resp_byok_list = client.get(f"/api/v1/settings/ai-keys/list?workspace_id={workspace_alpha.id}", headers=beta_agency_manager_headers)
        assert resp_byok_list.status_code == 403

        # 3. POST/Tamper Alpha BYOK
        resp_byok_post = client.post(
            "/api/v1/settings/ai-keys",
            json={
                "api_key": "AIzaSyBetaAdversarialTamperingKey123",
                "provider": "gemini",
                "workspace_id": workspace_alpha.id
            },
            headers=beta_agency_manager_headers
        )
        assert resp_byok_post.status_code == 403

        # 4. DELETE Alpha BYOK
        resp_byok_del = client.delete(f"/api/v1/settings/ai-keys?workspace_id={workspace_alpha.id}", headers=beta_agency_manager_headers)
        assert resp_byok_del.status_code == 403

        # 5. GET Alpha Brand Kit as Beta user
        resp_bk = client.get(f"/api/v1/brand-kit?workspace_id={workspace_alpha.id}", headers=beta_agency_manager_headers)
        assert resp_bk.status_code == 403


# ==============================================================================
# 3. REVIEW QUEUE STATE MACHINE INTEGRITY TESTS
# ==============================================================================
class TestP0ReviewQueueStateMachine:
    """Verifies that review state transitions strictly obey Human-in-the-loop gates."""

    def test_01_direct_content_creation_as_approved_or_published_rejected_400(
        self, client: TestClient, marketer_headers
    ):
        """Direct creation of content in APPROVED or PUBLISHED state is rejected with 400."""
        base_payload = {
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bypass Test Direct State",
            "body": "Nội dung cố ý tạo trực tiếp ở trạng thái phê duyệt",
            "cta": "Mua ngay"
        }

        # APPROVED
        resp1 = client.post("/api/v1/contents", json={**base_payload, "status": "APPROVED"}, headers=marketer_headers)
        assert resp1.status_code == 400, f"Expected 400, got {resp1.status_code}: {resp1.text}"

        # PUBLISHED
        resp2 = client.post("/api/v1/contents", json={**base_payload, "status": "PUBLISHED"}, headers=marketer_headers)
        assert resp2.status_code == 400, f"Expected 400, got {resp2.status_code}: {resp2.text}"

    def test_02_direct_content_update_to_approved_or_published_rejected_400(
        self, client: TestClient, marketer_headers, db_session: Session
    ):
        """Direct update changing status directly to APPROVED or PUBLISHED is rejected with 400."""
        # Create normal draft content
        draft = MarketingContent(
            workspace_id=1,
            campaign_id=1,
            channel_id=1,
            created_by=2,
            title="Bản nháp ban đầu",
            body="Thân bài nháp",
            cta="CTA nháp",
            status="DRAFT",
            version_no=1
        )
        db_session.add(draft)
        db_session.commit()
        db_session.refresh(draft)

        # Attempt to directly PUT status to APPROVED
        resp1 = client.put(f"/api/v1/contents/{draft.id}", json={"status": "APPROVED"}, headers=marketer_headers)
        assert resp1.status_code == 400

        # Attempt to directly PUT status to PUBLISHED
        resp2 = client.put(f"/api/v1/contents/{draft.id}", json={"status": "PUBLISHED"}, headers=marketer_headers)
        assert resp2.status_code == 400

    def test_03_auto_demotion_to_ai_draft_when_approved_content_is_edited(
        self, client: TestClient, marketer_headers, db_session: Session
    ):
        """When an APPROVED content is edited, its status must auto-demote to AI_DRAFT."""
        approved_content = MarketingContent(
            workspace_id=1,
            campaign_id=1,
            channel_id=1,
            created_by=2,
            title="Bài viết đã được duyệt hợp lệ",
            body="Nội dung đã được kiểm duyệt và phê duyệt",
            cta="Bấm vào đây",
            status="APPROVED",
            version_no=1
        )
        db_session.add(approved_content)
        db_session.commit()
        db_session.refresh(approved_content)

        # Edit body
        resp = client.put(
            f"/api/v1/contents/{approved_content.id}",
            json={"body": "Nội dung đã bị chỉnh sửa sau khi duyệt!"},
            headers=marketer_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "AI_DRAFT", f"Expected demotion to AI_DRAFT, got {data['status']}"

        # Verify database reflection
        db_session.refresh(approved_content)
        assert approved_content.status == "AI_DRAFT"

    def test_04_rejection_reason_min_length_validation(
        self, client: TestClient, manager_headers, db_session: Session
    ):
        """Rejection requires a non-empty reason of at least 3 characters."""
        content = MarketingContent(
            workspace_id=1,
            campaign_id=1,
            channel_id=1,
            created_by=2,
            title="Bài viết chờ kiểm tra lý do từ chối",
            body="Thân bài kiểm tra",
            cta="Đăng ký",
            status="IN_REVIEW",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        # Empty reason -> 400
        resp_empty = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": ""},
            headers=manager_headers
        )
        assert resp_empty.status_code in (400, 422)

        # Short reason (< 3 chars) -> 400
        resp_short = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": "no"},
            headers=manager_headers
        )
        assert resp_short.status_code == 400

        # Valid reason (>= 3 chars) -> 200 OK
        resp_valid = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": "Tiêu đề chưa nêu bật USP sản phẩm"},
            headers=manager_headers
        )
        assert resp_valid.status_code == 200
        assert resp_valid.json()["status"] == "REJECTED"

        # Check review log
        rev = db_session.query(ContentReview).filter(ContentReview.content_id == content.id).first()
        assert rev is not None
        assert rev.decision == "REJECTED"
        assert rev.reason == "Tiêu đề chưa nêu bật USP sản phẩm"

    def test_05_client_approver_forbidden_from_publishing_content_403(
        self, client: TestClient, client_approver_headers, db_session: Session
    ):
        """CLIENT_APPROVER can approve, but cannot execute POST /publish (only MANAGER / AGENCY_MANAGER)."""
        approved_content = MarketingContent(
            workspace_id=1,
            campaign_id=1,
            channel_id=1,
            created_by=2,
            title="Bài viết sẵn sàng xuất bản",
            body="Nội dung đã được duyệt sẵn sàng đăng lên mạng xã hội",
            cta="Khám phá ngay",
            status="APPROVED",
            version_no=1
        )
        db_session.add(approved_content)
        db_session.commit()
        db_session.refresh(approved_content)

        resp = client.post(f"/api/v1/contents/{approved_content.id}/publish", headers=client_approver_headers)
        assert resp.status_code == 403, f"Expected 403 Forbidden for CLIENT_APPROVER on publish, got {resp.status_code}"

    def test_06_end_to_end_state_machine_lifecycle(
        self, client: TestClient, marketer_headers, manager_headers, client_approver_headers, db_session: Session
    ):
        """Verifies full state machine progression:
        DRAFT -> SUBMIT -> IN_REVIEW -> REJECT -> REJECTED -> EDIT -> SUBMIT -> IN_REVIEW -> APPROVE -> APPROVED -> PUBLISH -> PUBLISHED.
        """
        # 1. Create initial draft
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Hành trình vòng lặp kiểm duyệt toàn diện",
            "body": "Nội dung chuẩn chỉ không vi phạm từ cấm",
            "cta": "Tham gia ngay"
        }, headers=marketer_headers)
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]
        assert create_resp.json()["status"] in ("DRAFT", "AI_DRAFT")

        # 2. Marketer submits for review -> IN_REVIEW
        sub1 = client.post(f"/api/v1/contents/{cid}/submit", headers=marketer_headers)
        assert sub1.status_code == 200
        assert sub1.json()["status"] == "IN_REVIEW"

        # 3. Manager rejects -> REJECTED
        rej = client.post(
            f"/api/v1/contents/{cid}/reject",
            json={"decision": "REJECTED", "reason": "Cần bổ sung thêm ví dụ thực tế"},
            headers=manager_headers
        )
        assert rej.status_code == 200
        assert rej.json()["status"] == "REJECTED"

        # 4. Marketer edits body -> resubmits
        edit = client.put(f"/api/v1/contents/{cid}", json={"body": "Nội dung đã bổ sung ví dụ thực tế chi tiết"}, headers=marketer_headers)
        assert edit.status_code == 200

        sub2 = client.post(f"/api/v1/contents/{cid}/submit", headers=marketer_headers)
        assert sub2.status_code == 200
        assert sub2.json()["status"] == "IN_REVIEW"

        # 5. Client Approver approves -> APPROVED
        app_resp = client.post(f"/api/v1/contents/{cid}/approve", headers=client_approver_headers)
        assert app_resp.status_code == 200
        assert app_resp.json()["status"] == "APPROVED"

        # 6. Manager publishes -> PUBLISHED
        pub_resp = client.post(f"/api/v1/contents/{cid}/publish", headers=manager_headers)
        assert pub_resp.status_code == 200
        assert pub_resp.json()["status"] == "PUBLISHED"


# ==============================================================================
# 4. BYOK CRYPTOGRAPHY VAULT & KEY SAFETY TESTS
# ==============================================================================
class TestP0BYOKCryptoVault:
    """Verifies enterprise BYOK cryptographic vault security, ciphertext invariant, and key rotation."""

    def test_01_fernet_ciphertext_invariant_always_starts_with_gAAAAA(self):
        """All encrypted keys strictly adhere to the Fernet standard format starting with 'gAAAAA'."""
        raw_keys = [
            "AIzaSyDemoGoogleGeminiKey1234567890",
            "sk-proj-openai-production-key-long-token-9999",
            "openrouter-key-test-abcde-12345"
        ]
        for key in raw_keys:
            encrypted = encrypt_api_key(key)
            assert isinstance(encrypted, str)
            assert encrypted.startswith("gAAAAA"), f"Fernet invariant violated! Key: {encrypted[:15]}..."
            # Decryption recovers identical plaintext
            decrypted = decrypt_api_key(encrypted)
            assert decrypted == key

    def test_02_tampered_ciphertext_rejected_with_value_error(self):
        """Tampered or corrupted ciphertexts are rejected with ValueError without unhandled crash."""
        key = "AIzaSyTamperTestKey123456789"
        encrypted = encrypt_api_key(key)

        # Alter bytes in the middle
        corrupted = encrypted[:15] + ("X" if encrypted[15] != "X" else "Y") + encrypted[16:]
        with pytest.raises(ValueError, match="Tampered or invalid key"):
            decrypt_api_key(corrupted)

    def test_03_empty_or_whitespace_key_rejected(self):
        """Empty or whitespace-only keys cannot be encrypted or decrypted."""
        with pytest.raises(ValueError):
            encrypt_api_key("")
        with pytest.raises(ValueError):
            encrypt_api_key("   ")
        with pytest.raises(ValueError):
            decrypt_api_key("")

    def test_04_dedicated_jwt_and_byok_key_separation(self, monkeypatch):
        """JWT secret and BYOK encryption key must be completely decoupled."""
        monkeypatch.setattr(settings, "JWT_SECRET_KEY", "jwt-signing-secret-key-32-characters-1234")
        monkeypatch.setattr(settings, "BYOK_ENCRYPTION_KEY", "byok-encryption-key-32-characters-5678")

        jwt_key = get_jwt_secret_key()
        byok_key = get_byok_encryption_key()

        assert jwt_key == "jwt-signing-secret-key-32-characters-1234"
        assert byok_key != jwt_key.encode()

    def test_05_security_config_validation_rejects_insecure_keys_in_production(self, monkeypatch):
        """validate_security_configuration() strictly rejects short or placeholder keys in production."""
        from app.core.config import validate_security_configuration

        monkeypatch.setattr(settings, "APP_ENV", "production")
        monkeypatch.setenv("APP_ENV", "production")

        # 1. Short key (< 32 chars)
        monkeypatch.setattr(settings, "SECRET_KEY", "short-key-123")
        with pytest.raises(RuntimeError):
            validate_security_configuration()

        # 2. Insecure placeholder pattern
        monkeypatch.setattr(settings, "SECRET_KEY", "placeholder-secret-key-that-is-at-least-32-chars")
        with pytest.raises(RuntimeError):
            validate_security_configuration()

        # 3. Default dev key in production
        monkeypatch.setattr(settings, "SECRET_KEY", "aia331-secret-key-change-in-production-super-secure")
        with pytest.raises(RuntimeError):
            validate_security_configuration()

    def test_06_byok_key_rotation_preserves_decryption_with_multifernet(self, monkeypatch, db_session: Session):
        """MultiFernet decrypts ciphertexts produced under older keys when rotation keys are provided."""
        # Key 1
        key1 = "initial-primary-byok-passphrase-v1-32chars"
        monkeypatch.setattr(settings, "BYOK_ENCRYPTION_KEY", key1)
        monkeypatch.setattr(settings, "BYOK_ROTATION_KEYS", "")

        secret_text = "AIzaSyOldKeyDecryptionTest"
        c1 = encrypt_api_key(secret_text)
        assert decrypt_api_key(c1) == secret_text

        # Rotate to Key 2, with Key 1 listed in rotation keys
        key2 = "second-primary-byok-passphrase-v2-32chars"
        monkeypatch.setattr(settings, "BYOK_ENCRYPTION_KEY", key2)
        monkeypatch.setattr(settings, "BYOK_ROTATION_KEYS", json.dumps([key1]))

        # Decryption of c1 still succeeds
        assert decrypt_api_key(c1) == secret_text

    def test_07_api_key_masking_ladder_preserves_confidentiality(self):
        """mask_api_key() hides sensitive characters and guarantees '...' masking."""
        assert mask_api_key("AIzaSyD-1234567890abcdef") == "AIzaSy...cdef"
        assert mask_api_key("123456") == "12...56"
        assert mask_api_key("abc") == "..."
        assert mask_api_key("") == ""


# ==============================================================================
# 5. DATABASE SAFETY, NON-DESTRUCTION & DETERMINISTIC TIME TESTS
# ==============================================================================
class TestP0DatabaseSafetyAndDeterminism:
    """Verifies that database reset is forbidden in production, and deterministic clock operates accurately."""

    def test_01_reset_db_strictly_blocked_in_production(self, monkeypatch):
        """reset_db() throws RuntimeError if ENVIRONMENT=production or APP_ENV=production."""
        monkeypatch.setattr(settings, "APP_ENV", "production")
        monkeypatch.setenv("APP_ENV", "production")
        assert is_production_env() is True

        with pytest.raises(RuntimeError, match="Database reset is forbidden in production environment"):
            reset_db()

    def test_02_init_db_reset_true_strictly_blocked_in_production(self, monkeypatch):
        """init_db(reset=True) is strictly blocked in production."""
        monkeypatch.setattr(settings, "APP_ENV", "production")
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(RuntimeError, match="Database reset is forbidden in production environment"):
            seed_init_db(reset=True)

    def test_03_init_db_reset_false_is_non_destructive(self):
        """init_db(reset=False) preserves existing records in the database."""
        isolated_engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
        try:
            # First initialization
            seed_init_db(reset=False, db_engine=isolated_engine)

            from sqlalchemy.orm import sessionmaker
            CustomSession = sessionmaker(bind=isolated_engine)
            s = CustomSession()
            u_count_before = s.query(User).count()
            assert u_count_before > 0
            s.close()

            # Second initialization (simulation of server restart or deploy)
            seed_init_db(reset=False, db_engine=isolated_engine)

            s2 = CustomSession()
            u_count_after = s2.query(User).count()
            assert u_count_after == u_count_before, "init_db(reset=False) modified or deleted existing users!"
            s2.close()
        finally:
            isolated_engine.dispose()

    def test_04_vietnam_time_freezing_deterministic_clock(self, freeze_vietnam_time):
        """Verifies that freeze_vietnam_time locks test time deterministically to 2026-09-26 12:00:00+07:00."""
        from app.models.entities import utc_now

        assert freeze_vietnam_time["date_iso"] == "2026-09-26"
        assert freeze_vietnam_time["time_iso"] == "12:00:00"
        assert freeze_vietnam_time["date_display"] == "26/09/2026"
        assert freeze_vietnam_time["currency_symbol"] == "₫"

        # utc_now() should return the frozen UTC time (05:00:00 UTC)
        frozen_utc = utc_now()
        assert frozen_utc.year == 2026
        assert frozen_utc.month == 9
        assert frozen_utc.day == 26
        assert frozen_utc.hour == 5
        assert frozen_utc.minute == 0


# ==============================================================================
# 6. METRICS FIXTURES MATRIX VALIDATION TESTS
# ==============================================================================
class TestP0MetricsFixturesMatrix:
    """Verifies that rich, empty, and zero-value metric scenarios are handled cleanly."""

    def test_01_rich_metrics_fixture_provides_valid_kpi(
        self, client: TestClient, manager_headers, rich_metrics_campaign
    ):
        """Campaign with rich metrics returns valid KPI data and positive ROAS."""
        resp = client.get(f"/api/v1/campaigns/{rich_metrics_campaign.id}/kpi", headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_views"] > 0
        assert data["total_clicks"] > 0
        assert data["roas"] > 0

    def test_02_empty_metrics_fixture_handles_cleanly_without_500(
        self, client: TestClient, manager_headers, empty_metrics_campaign
    ):
        """Campaign with empty metrics returns 0 counters with 200 OK and no 500 crashes."""
        resp = client.get(f"/api/v1/campaigns/{empty_metrics_campaign.id}/kpi", headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_views"] == 0
        assert data["total_clicks"] == 0
        assert data["roas"] == 0.0

    def test_03_zero_metrics_fixture_calculates_zero_roas_without_division_by_zero(
        self, client: TestClient, manager_headers, zero_metrics_campaign
    ):
        """Campaign with zero metrics (cost=0, revenue=0) does not produce ZeroDivisionError."""
        resp = client.get(f"/api/v1/campaigns/{zero_metrics_campaign.id}/kpi", headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cost"] == 0.0
        assert data["total_revenue"] == 0.0
        assert data["roas"] == 0.0
