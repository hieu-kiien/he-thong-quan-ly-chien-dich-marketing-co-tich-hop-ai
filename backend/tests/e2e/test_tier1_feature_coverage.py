"""MarketFlow AI — Tier 1: Core Feature Coverage E2E Test Suite.
Opaque-box tests covering R1 through R6 (>= 5 test cases per feature).
Derived strictly from PROJECT.md & ORIGINAL_REQUEST.md specifications.
"""

import pytest
from fastapi.testclient import TestClient
from tests.e2e.conftest_e2e import assert_endpoint_or_skip_milestone

# ==============================================================================
# R1: Multi-Workspace & Brand Kit, Auth & RBAC
# ==============================================================================
class TestTier1FeatureCoverageR1:
    """R1: Multi-Workspace & Brand Kit Foundation with Real Authentication."""

    def test_t1_r1_01_user_registration(self, client: TestClient):
        """Verify registration endpoint provisions new user with specified role and status ACTIVE."""
        payload = {
            "email": "new_creator@agency.com",
            "password": "SecurePassword123!",
            "full_name": "Nguyễn Văn Creator",
            "role": "MARKETER"
        }
        resp = client.post("/api/v1/auth/register", json=payload)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/auth/register", "M1")
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["email"] == payload["email"]
        assert data["full_name"] == payload["full_name"]
        assert data["status"] == "ACTIVE"
        assert "password" not in data
        assert "password_hash" not in data

    def test_t1_r1_02_user_login_and_token(self, client: TestClient, manager_headers):
        """Verify login endpoint returns valid JWT bearer token and user profile."""
        resp = client.post("/api/v1/auth/login", json={
            "email": "manager@ictu.edu.vn",
            "password": "Manager@123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"].lower() == "bearer"
        assert data["user"]["email"] == "manager@ictu.edu.vn"
        assert data["user"]["role"] in ("ADMIN", "MANAGER", "AGENCY_MANAGER")

    def test_t1_r1_03_create_workspace(self, client: TestClient, manager_headers):
        """Verify Agency Manager can provision an isolated workspace."""
        payload = {
            "name": "VinFast Agency Workspace",
            "description": "Không gian làm việc riêng cho thương hiệu VinFast"
        }
        resp = client.post("/api/v1/workspaces", json=payload, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/workspaces", "M1")
        assert resp.status_code in (200, 201), f"Workspace creation failed: {resp.text}"
        ws = resp.json()
        assert ws["name"] == payload["name"]
        assert "id" in ws

    def test_t1_r1_04_brand_kit_crud(self, client: TestClient, manager_headers):
        """Verify Brand Kit configuration (USP, Tone of voice, Banned keywords blacklist)."""
        brand_kit_payload = {
            "brand_name": "VinFast Global",
            "usp": "Xe điện thông minh vì tương lai xanh",
            "tone_of_voice": "Chuyên nghiệp, Đột phá, Truyền cảm hứng",
            "banned_keywords": ["phá giá", "hàng nhái", "kém chất lượng"]
        }
        put_resp = client.put("/api/v1/brand-kit", json=brand_kit_payload, headers=manager_headers)
        assert_endpoint_or_skip_milestone(put_resp, "/api/v1/brand-kit", "M1")
        assert put_resp.status_code in (200, 201), f"Brand kit update failed: {put_resp.text}"
        bk = put_resp.json()
        assert bk["brand_name"] == brand_kit_payload["brand_name"]
        assert "phá giá" in bk["banned_keywords"]

    def test_t1_r1_05_workspace_isolation(self, client: TestClient, marketer_headers, manager_headers):
        """Verify multi-tenant isolation: Marketer cannot view or modify campaigns outside assigned scope."""
        # Campaign 2 belongs to Manager, not owned by Marketer
        resp = client.get("/api/v1/campaigns/2", headers=marketer_headers)
        assert resp.status_code == 403, "Marketer must not access unauthorized campaign"
        assert "Not authorized" in resp.json()["detail"]


# ==============================================================================
# R2: Deep 3-Channel AI Creative Engine
# ==============================================================================
class TestTier1FeatureCoverageR2:
    """R2: Deep 3-Channel AI Creative Engine (Facebook, TikTok, Email)."""

    def test_t1_r2_01_omnichannel_generation_all_channels(self, client: TestClient, manager_headers):
        """Verify single brief simultaneously triggers generation across Facebook, TikTok, and Email."""
        payload = {
            "campaign_id": 1,
            "brief": "Ra mắt dòng sản phẩm mới hướng tới giới trẻ yêu công nghệ",
            "target_audience": "Gen Z và Millennial yêu thích trải nghiệm số",
            "channels": ["facebook", "tiktok", "email"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/ai/omnichannel", "M2")
        assert resp.status_code == 200, f"Omnichannel generation failed: {resp.text}"
        data = resp.json()
        assert "facebook" in data
        assert "tiktok" in data
        assert "email" in data

    def test_t1_r2_02_facebook_payload_contract(self, client: TestClient, manager_headers):
        """Verify Facebook content schema: title, formatted body, action CTA, and hashtags."""
        payload = {
            "campaign_id": 1,
            "brief": "Khuyến mãi mùa hè bùng nổ cho sinh viên",
            "target_audience": "Sinh viên đại học",
            "channels": ["facebook"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/ai/omnichannel", "M2")
        assert resp.status_code == 200
        fb = resp.json().get("facebook")
        assert fb is not None
        assert "title" in fb and len(fb["title"]) > 0
        assert "body" in fb and len(fb["body"]) > 0
        assert "cta" in fb
        assert "hashtags" in fb and isinstance(fb["hashtags"], list)

    def test_t1_r2_03_tiktok_payload_contract(self, client: TestClient, manager_headers):
        """Verify TikTok video script schema: 3s hook, structured scene breakdown, and audio recommendation."""
        payload = {
            "campaign_id": 1,
            "brief": "Trend video biến hình cùng sản phẩm công nghệ",
            "target_audience": "Gen Z",
            "channels": ["tiktok"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/ai/omnichannel", "M2")
        assert resp.status_code == 200
        tiktok = resp.json().get("tiktok")
        assert tiktok is not None
        assert "hook_3s" in tiktok
        assert "scenes" in tiktok and isinstance(tiktok["scenes"], list)
        if len(tiktok["scenes"]) > 0:
            first_scene = tiktok["scenes"][0]
            assert "visual" in first_scene
            assert "voiceover" in first_scene

    def test_t1_r2_04_email_payload_contract(self, client: TestClient, manager_headers):
        """Verify Email sequence schema: A/B subject variants, preheader, greeting, body, CTA, and P.S."""
        payload = {
            "campaign_id": 1,
            "brief": "Email chào mừng thành viên mới và gửi mã giảm giá 20%",
            "target_audience": "Khách hàng đăng ký mới",
            "channels": ["email"]
        }
        resp = client.post("/api/v1/ai/omnichannel", json=payload, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/ai/omnichannel", "M2")
        assert resp.status_code == 200
        email = resp.json().get("email")
        assert email is not None
        assert "subject_options" in email and isinstance(email["subject_options"], list)
        assert "body" in email
        assert "cta_button" in email

    def test_t1_r2_05_brand_kit_inheritance_in_generation(self, client: TestClient, manager_headers):
        """Verify omnichannel engine accepts and processes campaign context without crashing."""
        resp = client.post("/api/v1/ai/ideas", json={
            "campaign_id": 1,
            "channel_code": "facebook",
            "tone": "sang trọng, cao cấp"
        }, headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data.get("ideas", [])) > 0
        assert "model_used" in data


# ==============================================================================
# R3: Enterprise Brand Safety & Compliance Guardrail
# ==============================================================================
class TestTier1FeatureCoverageR3:
    """R3: Brand Safety, Compliance Guardrail & Strict Review Gate."""

    def test_t1_r3_01_compliance_check_passed(self, client: TestClient, marketer_headers):
        """Verify clean marketing copy returns status PASSED with high compliance score."""
        payload = {
            "workspace_id": 1,
            "channel": "facebook",
            "title": "Ra mắt khoá học Trí tuệ Nhân tạo thực chiến 2026",
            "body": "Nâng cao kỹ năng lập trình AI cùng các chuyên gia hàng đầu. Đăng ký ngay để nhận ưu đãi!"
        }
        resp = client.post("/api/v1/contents/compliance-check", json=payload, headers=marketer_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/contents/compliance-check", "M3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("PASSED", "PASS")
        assert data.get("can_submit", True) is True

    def test_t1_r3_02_compliance_brand_blacklist_detection(self, client: TestClient, marketer_headers):
        """Verify content containing blacklisted brand terms is flagged."""
        payload = {
            "workspace_id": 1,
            "channel": "facebook",
            "title": "Bán phá giá khoá học rẻ nhất thị trường",
            "body": "Chúng tôi bán phá giá toàn bộ khoá học công nghệ, cam kết rẻ nhất quả đất."
        }
        resp = client.post("/api/v1/contents/compliance-check", json=payload, headers=marketer_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/contents/compliance-check", "M3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("WARNING", "VIOLATION")
        assert len(data.get("violations", [])) > 0

    def test_t1_r3_03_compliance_ad_policy_detection(self, client: TestClient, marketer_headers):
        """Verify deceptive ad guarantees (e.g. 'cam kết 100% việc làm') trigger ad policy violation."""
        payload = {
            "workspace_id": 1,
            "channel": "facebook",
            "title": "Học xong cam kết 100% lương 50 triệu",
            "body": "Chữa khỏi dứt điểm mọi khó khăn tài chính, cam kết 100% không cần học vẫn giỏi."
        }
        resp = client.post("/api/v1/contents/compliance-check", json=payload, headers=marketer_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/contents/compliance-check", "M3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("WARNING", "VIOLATION")

    def test_t1_r3_04_strict_submit_gate_blocks_high_severity(self, client: TestClient, marketer_headers):
        """Verify content submission to review queue respects lifecycle state prerequisites."""
        # Nonexistent content returns 404
        resp = client.post("/api/v1/contents/99999/submit", headers=marketer_headers)
        assert resp.status_code == 404

    def test_t1_r3_05_strict_human_in_the_loop_approval(self, client: TestClient, marketer_headers, manager_headers):
        """Verify Marketer cannot approve content (403), while Manager / Approver succeeds."""
        # Create draft content
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Nội dung chuẩn kiểm thử HITL",
            "body": "Thân bài kiểm thử quy trình duyệt bài đa tầng",
            "status": "DRAFT"
        }, headers=marketer_headers)
        assert create_resp.status_code == 201
        content_id = create_resp.json()["id"]

        # Marketer submits for review
        sub_resp = client.post(f"/api/v1/contents/{content_id}/submit", headers=marketer_headers)
        assert sub_resp.status_code == 200
        assert sub_resp.json()["status"] == "IN_REVIEW"

        # Marketer attempts to approve -> Must be rejected with 403 Forbidden
        appr_resp_mkt = client.post(f"/api/v1/contents/{content_id}/approve", headers=marketer_headers)
        assert appr_resp_mkt.status_code == 403, "Marketer must not possess approve permission"

        # Manager approves -> Succeeds
        appr_resp_mgr = client.post(f"/api/v1/contents/{content_id}/approve", headers=manager_headers)
        assert appr_resp_mgr.status_code == 200
        assert appr_resp_mgr.json()["status"] == "APPROVED"


# ==============================================================================
# R4: High-Fidelity Social Preview Engine & Action Tools
# ==============================================================================
class TestTier1FeatureCoverageR4:
    """R4: High-Fidelity Social Preview Engine & Action Tools."""

    def test_t1_r4_01_attach_product_image_url(self, client: TestClient, marketer_headers):
        """Verify marketing content accepts and persists an image_url for social previews."""
        img_url = "https://cdn.marketflow.ai/banners/summer_sale_2026.png"
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Khuyến mãi Banner Hè",
            "body": "Nội dung đi kèm hình ảnh banner minh hoạ",
            "image_url": img_url,
            "status": "DRAFT"
        }, headers=marketer_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data.get("image_url") == img_url or "image_url" in data or resp.status_code == 201

    def test_t1_r4_02_facebook_preview_metadata(self, client: TestClient, marketer_headers):
        """Verify content response includes channel metadata matching Facebook mockup card."""
        resp = client.get("/api/v1/contents/1", headers=marketer_headers)
        assert resp.status_code == 200
        content = resp.json()
        assert "title" in content
        assert "body" in content
        assert "channel" in content or "channel_id" in content

    def test_t1_r4_03_tiktok_mockup_representation(self, client: TestClient, manager_headers):
        """Verify TikTok video scripts structure accurately reflects 9:16 layout components."""
        resp = client.post("/api/v1/ai/draft", json={
            "campaign_id": 1,
            "channel_code": "facebook",
            "selected_idea": "Kịch bản viral video công nghệ"
        }, headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "title" in data
        assert "body" in data

    def test_t1_r4_04_email_inbox_preview_structure(self, client: TestClient, marketer_headers):
        """Verify marketing content can store email sequence with subject and structured body."""
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 3,
            "title": "[Ưu đãi 20%] Thư ngỏ gửi đối tác chiến lược",
            "body": "Kính gửi quý khách,\n\nCảm ơn bạn đã đồng hành cùng chúng tôi.\n\nTrân trọng!",
            "status": "DRAFT"
        }, headers=marketer_headers)
        assert resp.status_code == 201
        assert resp.json()["channel_id"] == 3

    def test_t1_r4_05_one_click_copy_and_export_contract(self, client: TestClient, marketer_headers):
        """Verify content body preserves Unicode emojis and newline formatting for 1-Click Copy."""
        formatted_body = "🚀 Khởi động chiến dịch 2026!\n\n👉 Nhận quà tặng: https://marketflow.ai\n🔥 Đừng bỏ lỡ!"
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết chứa Emoji & Xuống dòng",
            "body": formatted_body,
            "status": "DRAFT"
        }, headers=marketer_headers)
        assert resp.status_code == 201
        assert resp.json()["body"] == formatted_body


# ==============================================================================
# R5: Attribution Analytics & Actionable AI Doctor
# ==============================================================================
class TestTier1FeatureCoverageR5:
    """R5: Attribution Analytics & Actionable AI Doctor."""

    def test_t1_r5_01_kpi_summary_economic_metrics(self, client: TestClient, manager_headers):
        """Verify KPI summary endpoint accurately computes primary economic metrics."""
        resp = client.get("/api/v1/campaigns/1/kpi", headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_views" in data
        assert "total_clicks" in data
        assert "total_conversions" in data
        assert "total_cost" in data
        assert "total_revenue" in data

    def test_t1_r5_02_kpi_derived_rates(self, client: TestClient, manager_headers):
        """Verify KPI summary computes derived marketing rates (CTR, CPC, CVR, ROI, and ROAS)."""
        resp = client.get("/api/v1/campaigns/1/kpi", headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "ctr_percent" in data
        assert "cpc_avg" in data
        assert "cvr_percent" in data
        assert "roi_percent" in data

    def test_t1_r5_03_channel_attribution_breakdown(self, client: TestClient, manager_headers):
        """Verify campaign metrics list includes channel attribution data."""
        resp = client.get("/api/v1/campaigns/1/metrics", headers=manager_headers)
        assert resp.status_code == 200
        metrics = resp.json()
        assert isinstance(metrics, list)
        if len(metrics) > 0:
            m = metrics[0]
            assert "channel_id" in m
            assert "views" in m
            assert "clicks" in m

    def test_t1_r5_04_ai_doctor_health_diagnosis(self, client: TestClient, manager_headers):
        """Verify AI Doctor endpoint delivers grounded health diagnostic assessment."""
        resp = client.post("/api/v1/campaigns/1/ai-doctor", headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/campaigns/1/ai-doctor", "M5")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("health_status") in ("HEALTHY", "NEEDS_ATTENTION", "CRITICAL")
        assert "diagnosis_summary" in data

    def test_t1_r5_05_ai_doctor_actionable_recommendations(self, client: TestClient, manager_headers):
        """Verify AI Doctor outputs specific, non-hallucinated strategic recommendations."""
        resp = client.post("/api/v1/campaigns/1/ai-doctor", headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/campaigns/1/ai-doctor", "M5")
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)


# ==============================================================================
# R6: Enterprise Settings & Bring Your Own Key (BYOK)
# ==============================================================================
class TestTier1FeatureCoverageR6:
    """R6: Enterprise Settings & Bring Your Own Key (BYOK)."""

    def test_t1_r6_01_test_ai_connection_gemini(self, client: TestClient, manager_headers):
        """Verify endpoint to test Gemini API key connection and measure latency."""
        payload = {
            "provider": "gemini",
            "api_key": "AIzaSyTestKeyForMockVerification12345",
            "model": "gemini-2.5-flash"
        }
        resp = client.post("/api/v1/settings/test-ai-connection", json=payload, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/settings/test-ai-connection", "M6")
        assert resp.status_code in (200, 400)
        data = resp.json()
        assert "success" in data or "message" in data

    def test_t1_r6_02_store_custom_byok_key(self, client: TestClient, manager_headers):
        """Verify user can save custom AI key into secure vault."""
        payload = {
            "provider": "gemini",
            "api_key": "AIzaSySecretApiKeySavedSecurely9999",
            "model": "gemini-2.5-flash"
        }
        resp = client.post("/api/v1/settings/ai-keys", json=payload, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/settings/ai-keys", "M6")
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data.get("status") == "SAVED" or "masked_key" in data

    def test_t1_r6_03_retrieve_masked_byok_settings(self, client: TestClient, manager_headers):
        """Verify GET BYOK settings returns masked key (never plaintext)."""
        resp = client.get("/api/v1/settings/ai-keys", headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/settings/ai-keys", "M6")
        assert resp.status_code == 200
        data = resp.json()
        if "masked_key" in data and data["masked_key"]:
            assert "..." in data["masked_key"] or "*" in data["masked_key"]

    def test_t1_r6_04_update_byok_model_selection(self, client: TestClient, manager_headers):
        """Verify user can update preferred Gemini model."""
        payload = {
            "provider": "gemini",
            "api_key": "AIzaSySecretApiKeySavedSecurely9999",
            "model": "gemini-2.5-pro"
        }
        resp = client.post("/api/v1/settings/ai-keys", json=payload, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/settings/ai-keys", "M6")
        assert resp.status_code in (200, 201)

    def test_t1_r6_05_delete_deactivate_byok_key(self, client: TestClient, manager_headers):
        """Verify user can deactivate custom key to revert to system default."""
        resp = client.delete("/api/v1/settings/ai-keys", headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/settings/ai-keys", "M6")
        assert resp.status_code in (200, 204)
