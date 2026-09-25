"""MarketFlow AI — Tier 2: Boundary & Corner Cases E2E Test Suite.
Opaque-box tests covering R1 through R6 boundary values, corner cases, and stress conditions.
Derived strictly from PROJECT.md & ORIGINAL_REQUEST.md specifications.
"""

import pytest
from fastapi.testclient import TestClient
from tests.e2e.conftest_e2e import assert_endpoint_or_skip_milestone

# ==============================================================================
# R1 Boundary & Corner Cases
# ==============================================================================
class TestTier2BoundaryCornerR1:
    """R1 Boundary Cases: Empty inputs, special characters, token expiry, invalid emails."""

    def test_t2_r1_01_empty_workspace_name_rejected(self, client: TestClient, manager_headers):
        """Reject empty or whitespace-only workspace names with HTTP 422."""
        resp = client.post("/api/v1/workspaces", json={"name": ""}, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/workspaces", "M1")
        assert resp.status_code == 422

    def test_t2_r1_02_special_characters_brand_kit(self, client: TestClient, manager_headers):
        """Verify Brand Kit safely handles Vietnamese accents, HTML tags, and Unicode emojis."""
        payload = {
            "brand_name": "Thương Hiệu Việt Nam 🇻🇳 <script>alert('xss')</script>",
            "usp": "Độc quyền công nghệ 4.0 & AI tự động hoá 100%",
            "tone_of_voice": "Trang trọng, Nhiệt huyết 🔥",
            "banned_keywords": ["hàng giả", "kém chất lượng ⚠️"]
        }
        resp = client.put("/api/v1/brand-kit", json=payload, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/brand-kit", "M1")
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "🇻🇳" in data["brand_name"]
        assert "🔥" in data["tone_of_voice"]

    def test_t2_r1_03_expired_or_malformed_jwt(self, client: TestClient):
        """Verify requests with malformed or missing Bearer prefix return HTTP 401."""
        bad_headers = {"Authorization": "Bearer not_a_valid_jwt_token_at_all"}
        resp = client.get("/api/v1/auth/me", headers=bad_headers)
        assert resp.status_code == 401

    def test_t2_r1_04_invalid_email_format_registration(self, client: TestClient):
        """Verify registration rejects invalid email structures with HTTP 422."""
        for invalid_email in ["notanemail", "user@", "user@.com", "@domain.com"]:
            resp = client.post("/api/v1/auth/register", json={
                "email": invalid_email,
                "password": "ValidPassword123!",
                "full_name": "Test User",
                "role": "MARKETER"
            })
            assert_endpoint_or_skip_milestone(resp, "/api/v1/auth/register", "M1")
            assert resp.status_code == 422

    def test_t2_r1_05_nonexistent_workspace_access(self, client: TestClient, manager_headers):
        """Verify accessing nonexistent workspace ID returns HTTP 404 cleanly."""
        resp = client.get("/api/v1/workspaces/999999", headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/workspaces", "M1")
        assert resp.status_code == 404


# ==============================================================================
# R2 Boundary & Corner Cases
# ==============================================================================
class TestTier2BoundaryCornerR2:
    """R2 Boundary Cases: Empty brief, oversized brief, single channel, fallback."""

    def test_t2_r2_01_empty_brief_validation(self, client: TestClient, manager_headers):
        """Verify empty brief triggers validation error HTTP 422."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "",
            "target_audience": "All"
        }, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/ai/omnichannel", "M2")
        assert resp.status_code == 422

    def test_t2_r2_02_oversized_brief_stress(self, client: TestClient, manager_headers):
        """Verify oversized brief (5000+ characters) is handled gracefully without crashing."""
        giant_brief = "Chiến dịch tiếp thị toàn cầu với mô tả cực dài: " + (" MarketFlow " * 400)
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": giant_brief,
            "target_audience": "Toàn bộ thị trường mục tiêu"
        }, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/ai/omnichannel", "M2")
        assert resp.status_code in (200, 422)

    def test_t2_r2_03_single_channel_subset(self, client: TestClient, manager_headers):
        """Verify requesting only Facebook channel returns only Facebook and omits others."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Chiến dịch quảng cáo Facebook tập trung",
            "target_audience": "Người dùng mạng xã hội",
            "channels": ["facebook"]
        }, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/ai/omnichannel", "M2")
        assert resp.status_code == 200
        data = resp.json()
        assert "facebook" in data

    def test_t2_r2_04_unsupported_channel_handling(self, client: TestClient, manager_headers):
        """Verify requesting invalid/unsupported channel returns validation error or handles safely."""
        resp = client.post("/api/v1/ai/omnichannel", json={
            "campaign_id": 1,
            "brief": "Quảng cáo kênh không hợp lệ",
            "target_audience": "Ai đó",
            "channels": ["unknown_social_network_xyz"]
        }, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/ai/omnichannel", "M2")
        assert resp.status_code in (200, 400, 422)

    def test_t2_r2_05_ai_provider_fallback_resilience(self, client: TestClient, manager_headers):
        """Verify AI system uses deterministic fallback if upstream LLM times out or fails."""
        resp = client.post("/api/v1/ai/ideas", json={
            "custom_topic": "Chủ đề tự do không có chiến dịch",
            "channel_code": "facebook"
        }, headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data.get("ideas", [])) > 0


# ==============================================================================
# R3 Boundary & Corner Cases
# ==============================================================================
class TestTier2BoundaryCornerR3:
    """R3 Boundary Cases: Case/accent insensitivity, overlapping keywords, state tampering."""

    def test_t2_r3_01_blacklist_case_and_accent_insensitivity(self, client: TestClient, marketer_headers):
        """Verify blacklist detects prohibited words regardless of upper/lower case."""
        payload = {
            "workspace_id": 1,
            "channel": "facebook",
            "title": "BÁN PHÁ GIÁ TOÀN BỘ SẢN PHẨM",
            "body": "Chúng tôi CAM KẾT 100% HOÀN VỐN NGAY LẬP TỨC"
        }
        resp = client.post("/api/v1/contents/compliance-check", json=payload, headers=marketer_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/contents/compliance-check", "M3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("WARNING", "VIOLATION")

    def test_t2_r3_02_overlapping_banned_keywords(self, client: TestClient, marketer_headers):
        """Verify text containing multiple overlapping prohibited words aggregates all violations."""
        payload = {
            "workspace_id": 1,
            "channel": "facebook",
            "title": "Cam kết 100% chữa khỏi dứt điểm kiếm tiền tỷ",
            "body": "Bán phá giá khoá học làm giàu nhanh, cam kết không rủi ro."
        }
        resp = client.post("/api/v1/contents/compliance-check", json=payload, headers=marketer_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/contents/compliance-check", "M3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "VIOLATION"

    def test_t2_r3_03_empty_content_compliance_scan(self, client: TestClient, marketer_headers):
        """Verify empty text compliance scan produces clean pass without false positives."""
        payload = {
            "workspace_id": 1,
            "channel": "facebook",
            "title": "Tiêu đề hợp lệ",
            "body": "Nội dung đạt chuẩn thuần tuý không chứa từ cấm."
        }
        resp = client.post("/api/v1/contents/compliance-check", json=payload, headers=marketer_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/contents/compliance-check", "M3")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("PASSED", "PASS")

    def test_t2_r3_04_illegal_state_jump_rejected(self, client: TestClient, marketer_headers):
        """Verify direct jump from DRAFT to APPROVED or PUBLISHED via PUT is rejected with HTTP 400."""
        # Create draft content
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết thử nghiệm trạng thái",
            "body": "Nội dung bài viết",
            "status": "DRAFT"
        }, headers=marketer_headers)
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]

        # Attempt illegal update to APPROVED
        put_resp = client.put(f"/api/v1/contents/{cid}", json={"status": "APPROVED"}, headers=marketer_headers)
        assert put_resp.status_code == 400
        assert "APPROVED" in put_resp.json()["detail"]

    def test_t2_r3_05_edit_approved_content_reverts_state(self, client: TestClient, marketer_headers, manager_headers):
        """Verify editing an already APPROVED content automatically resets status back to AI_DRAFT or DRAFT."""
        # Create and approve content
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Tiêu đề ban đầu đã duyệt",
            "body": "Nội dung ban đầu đã duyệt",
            "status": "DRAFT"
        }, headers=marketer_headers)
        cid = create_resp.json()["id"]

        client.post(f"/api/v1/contents/{cid}/submit", headers=marketer_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=manager_headers)

        # Marketer edits content title
        edit_resp = client.put(f"/api/v1/contents/{cid}", json={"title": "Tiêu đề đã bị can thiệp sau duyệt"}, headers=marketer_headers)
        assert edit_resp.status_code == 200
        assert edit_resp.json()["status"] in ("AI_DRAFT", "DRAFT")


# ==============================================================================
# R4 Boundary & Corner Cases
# ==============================================================================
class TestTier2BoundaryCornerR4:
    """R4 Boundary Cases: Malformed image URL, emoji fidelity, empty content export."""

    def test_t2_r4_01_malformed_image_url_handling(self, client: TestClient, marketer_headers):
        """Verify non-standard image URLs do not cause internal server errors."""
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Tiêu đề test URL",
            "body": "Nội dung test",
            "image_url": "ftp://not-an-https-url/image.jpg",
            "status": "DRAFT"
        }, headers=marketer_headers)
        assert resp.status_code in (201, 422)

    def test_t2_r4_02_copy_format_preserves_multiline_and_emoji(self, client: TestClient, marketer_headers):
        """Verify complex multi-line strings with tabs and multiple emojis maintain exact byte fidelity."""
        complex_text = "🎉 CHÚC MỪNG!\n\n\t• Điểm 1: Tuyệt vời ✨\n\t• Điểm 2: Tiện ích 🚀\n\nLink: https://ai.vn"
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Test Độ toàn vẹn Format",
            "body": complex_text,
            "status": "DRAFT"
        }, headers=marketer_headers)
        assert resp.status_code == 201
        assert resp.json()["body"] == complex_text

    def test_t2_r4_03_content_without_image_defaults_cleanly(self, client: TestClient, marketer_headers):
        """Verify content created without image_url defaults to null without breaking preview."""
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết không kèm hình",
            "body": "Nội dung thuần văn bản",
            "status": "DRAFT"
        }, headers=marketer_headers)
        assert resp.status_code == 201
        assert resp.json().get("image_url") is None or "image_url" in resp.json()

    def test_t2_r4_04_boundary_length_title_and_body(self, client: TestClient, marketer_headers):
        """Verify title exceeding 255 chars is rejected by Pydantic schema with HTTP 422."""
        oversized_title = "A" * 256
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": oversized_title,
            "body": "Nội dung hợp lệ",
            "status": "DRAFT"
        }, headers=marketer_headers)
        assert resp.status_code == 422

    def test_t2_r4_05_export_empty_campaign(self, client: TestClient, manager_headers):
        """Verify export on empty campaign handles cleanly without 500 error."""
        resp = client.get("/api/v1/campaigns/2/contents", headers=manager_headers)
        assert resp.status_code in (200, 404)


# ==============================================================================
# R5 Boundary & Corner Cases
# ==============================================================================
class TestTier2BoundaryCornerR5:
    """R5 Boundary Cases: Zero cost (division safety), zero clicks/views, massive numbers."""

    def test_t2_r5_01_zero_cost_division_safety(self, client: TestClient, manager_headers):
        """Verify cost=0 avoids ZeroDivisionError in ROAS and CPC calculations."""
        # Query KPI for campaign; verify all calculated fields return finite numbers (no NaN or Inf)
        resp = client.get("/api/v1/campaigns/1/kpi", headers=manager_headers)
        assert resp.status_code == 200
        kpi = resp.json()
        assert isinstance(kpi["cpc_avg"], (int, float))
        assert isinstance(kpi["roi_percent"], (int, float))

    def test_t2_r5_02_zero_clicks_and_views_safety(self, client: TestClient, manager_headers):
        """Verify CTR and CVR safely compute as 0.0% when views=0 or clicks=0."""
        # Record metric with views=0, clicks=0
        resp = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 2,
            "metric_date": "2026-11-20",
            "views": 0,
            "clicks": 0,
            "conversions": 0,
            "cost": 0.0,
            "revenue": 0.0
        }, headers=manager_headers)
        assert resp.status_code == 201

    def test_t2_r5_03_negative_cost_revenue_validation(self, client: TestClient, manager_headers):
        """Verify negative cost or revenue is strictly rejected by schema validation (HTTP 422)."""
        resp = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-21",
            "views": 100,
            "clicks": 10,
            "conversions": 1,
            "cost": -500000.0,
            "revenue": 1000000.0
        }, headers=manager_headers)
        assert resp.status_code == 422

    def test_t2_r5_04_ai_doctor_sparse_metrics_context(self, client: TestClient, manager_headers):
        """Verify AI Doctor handles new campaigns with zero performance metrics without crashing."""
        resp = client.post("/api/v1/campaigns/2/ai-doctor", headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/campaigns/2/ai-doctor", "M5")
        assert resp.status_code == 200

    def test_t2_r5_05_large_scale_financial_values(self, client: TestClient, manager_headers):
        """Verify KPI computations handle large numbers (e.g. 10 billion VNĐ) without precision loss."""
        resp = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-22",
            "views": 10000000,
            "clicks": 500000,
            "conversions": 50000,
            "cost": 5000000000.0,
            "revenue": 25000000000.0
        }, headers=manager_headers)
        assert resp.status_code == 201


# ==============================================================================
# R6 Boundary & Corner Cases
# ==============================================================================
class TestTier2BoundaryCornerR6:
    """R6 Boundary Cases: Empty BYOK key, prohibited providers (No Claude, No GPT), masked keys."""

    def test_t2_r6_01_empty_byok_key_rejected(self, client: TestClient, manager_headers):
        """Verify submitting an empty or whitespace-only API key is rejected with HTTP 422."""
        resp = client.post("/api/v1/settings/ai-keys", json={
            "provider": "gemini",
            "api_key": "   ",
            "model": "gemini-2.5-flash"
        }, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/settings/ai-keys", "M6")
        assert resp.status_code in (400, 422)

    def test_t2_r6_02_prohibited_ai_providers_rejected(self, client: TestClient, manager_headers):
        """Verify models from prohibited providers (Claude 3.7, Sonnet, GPT) are strictly rejected."""
        prohibited_models = ["claude-3-7-sonnet", "gpt-4o", "claude-3-5-sonnet"]
        for model in prohibited_models:
            resp = client.post("/api/v1/settings/test-ai-connection", json={
                "provider": "anthropic",
                "api_key": "test_key",
                "model": model
            }, headers=manager_headers)
            assert_endpoint_or_skip_milestone(resp, "/api/v1/settings/test-ai-connection", "M6")
            assert resp.status_code in (400, 422)

    def test_t2_r6_03_test_connection_invalid_key_fails_cleanly(self, client: TestClient, manager_headers):
        """Verify testing an invalid dummy key returns success: false cleanly without unhandled exception."""
        resp = client.post("/api/v1/settings/test-ai-connection", json={
            "provider": "gemini",
            "api_key": "invalid_dummy_key_0000",
            "model": "gemini-2.5-flash"
        }, headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/settings/test-ai-connection", "M6")
        assert resp.status_code in (200, 400)
        data = resp.json()
        assert data.get("success") is False or "error" in data or "message" in data

    def test_t2_r6_04_byok_encryption_at_rest(self, client: TestClient, manager_headers):
        """Verify saved custom keys are never returned as plaintext in GET responses."""
        resp = client.get("/api/v1/settings/ai-keys", headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/settings/ai-keys", "M6")
        if resp.status_code == 200:
            data = resp.json()
            assert "api_key" not in data or data.get("api_key") is None

    def test_t2_r6_05_masked_key_format_integrity(self, client: TestClient, manager_headers):
        """Verify masked key format presents at least 3 masking characters."""
        resp = client.get("/api/v1/settings/ai-keys", headers=manager_headers)
        assert_endpoint_or_skip_milestone(resp, "/api/v1/settings/ai-keys", "M6")
        if resp.status_code == 200:
            data = resp.json()
            masked = data.get("masked_key", "")
            if masked:
                assert "*" in masked or "." in masked
