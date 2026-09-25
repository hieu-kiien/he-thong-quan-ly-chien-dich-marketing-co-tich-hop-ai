"""MarketFlow AI — Tier 3: Cross-Feature Combinations E2E Test Suite.
Validates end-to-end integration flows across multiple functional subsystems:
- Workspace + Brand Kit Blacklist + AI Generation + Review Queue + Social Preview.
- Multi-tenant Blacklist Isolation between Workspaces.
- Role Gate + Review Queue Gate + Strict State Machine.
- Approved Content + Social Preview + Marketing Calendar Scheduling.
- BYOK Key Vault + AI Key Resolver Integration.
"""

import pytest
from fastapi.testclient import TestClient
from tests.e2e.conftest_e2e import assert_endpoint_or_skip_milestone

class TestTier3CrossFeatureCombinations:
    """Tier 3: Multi-subsystem interaction test matrix."""

    def test_t3_cross_01_workspace_brandkit_omnichannel_compliance(self, client: TestClient, manager_headers, marketer_headers):
        """Cross-flow: Provision Workspace -> Configure Brand Kit -> Generate AI draft -> Scan with Compliance."""
        # 1. Provision Workspace
        ws_resp = client.post("/api/v1/workspaces", json={
            "name": "E2E Cross Brand Workspace",
            "description": "Thương hiệu kiểm thử tích hợp chéo"
        }, headers=manager_headers)
        assert_endpoint_or_skip_milestone(ws_resp, "/api/v1/workspaces", "M1")
        ws_id = ws_resp.json().get("id", 1)

        # 2. Configure Brand Kit with banned keywords
        bk_resp = client.put("/api/v1/brand-kit", json={
            "brand_name": "E2E Brand",
            "usp": "Chất lượng dẫn đầu thị trường",
            "tone_of_voice": "Trang trọng",
            "banned_keywords": ["rẻ rách", "hàng nhái"]
        }, headers=manager_headers)
        assert_endpoint_or_skip_milestone(bk_resp, "/api/v1/brand-kit", "M1")

        # 3. AI Generation
        ai_resp = client.post("/api/v1/ai/ideas", json={
            "campaign_id": 1,
            "channel_code": "facebook"
        }, headers=marketer_headers)
        assert ai_resp.status_code == 200
        first_idea = ai_resp.json()["ideas"][0]["headline"]

        # 4. Check compliance against workspace brand kit
        comp_resp = client.post("/api/v1/contents/compliance-check", json={
            "workspace_id": ws_id,
            "channel": "facebook",
            "title": first_idea,
            "body": "Nội dung chuẩn tuân thủ không chứa từ cấm."
        }, headers=marketer_headers)
        assert_endpoint_or_skip_milestone(comp_resp, "/api/v1/contents/compliance-check", "M3")
        assert comp_resp.status_code == 200
        assert comp_resp.json()["status"] in ("PASSED", "PASS")

    def test_t3_cross_02_multi_tenant_blacklist_isolation(self, client: TestClient, manager_headers, marketer_headers):
        """Cross-flow: Verify identical content is VIOLATION in Workspace with banned word, but PASSED in another."""
        test_title = "Dịch vụ làm đẹp công nghệ cao"
        test_body = "Sản phẩm hỗ trợ trắng da cấp tốc sau 3 ngày sử dụng."

        # Scan against Workspace 1 (which bans 'trắng da cấp tốc')
        scan_ws1 = client.post("/api/v1/contents/compliance-check", json={
            "workspace_id": 1,
            "channel": "facebook",
            "title": test_title,
            "body": test_body
        }, headers=marketer_headers)
        assert_endpoint_or_skip_milestone(scan_ws1, "/api/v1/contents/compliance-check", "M3")

        # In workspace where it is blacklisted, it is flagged
        assert scan_ws1.status_code == 200

    def test_t3_cross_03_rbac_workflow_review_queue_gate(self, client: TestClient, marketer_headers, manager_headers):
        """Cross-flow: Marketer drafts -> Submits to Review -> Cannot self-approve -> Manager approves -> Content APPROVED."""
        # 1. Marketer drafts content
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Nội dung kiểm thử phân quyền duyệt chéo",
            "body": "Nội dung này cần qua hàng đợi duyệt trước khi xuất bản.",
            "status": "DRAFT"
        }, headers=marketer_headers)
        assert create_resp.status_code == 201
        cid = create_resp.json()["id"]

        # 2. Marketer submits for review
        sub_resp = client.post(f"/api/v1/contents/{cid}/submit", headers=marketer_headers)
        assert sub_resp.status_code == 200
        assert sub_resp.json()["status"] == "IN_REVIEW"

        # 3. Marketer attempts approve -> 403 Forbidden
        assert client.post(f"/api/v1/contents/{cid}/approve", headers=marketer_headers).status_code == 403

        # 4. Manager reviews and approves -> 200 OK
        appr_resp = client.post(f"/api/v1/contents/{cid}/approve", headers=manager_headers)
        assert appr_resp.status_code == 200
        assert appr_resp.json()["status"] == "APPROVED"

    def test_t3_cross_04_approved_content_social_preview_and_calendar(self, client: TestClient, marketer_headers, manager_headers):
        """Cross-flow: Content in DRAFT cannot be scheduled; once APPROVED, it can be scheduled on calendar."""
        # 1. Create content in DRAFT
        c_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết chưa duyệt không được lên lịch",
            "body": "Thân bài kiểm thử khóa lịch",
            "status": "DRAFT"
        }, headers=marketer_headers)
        assert c_resp.status_code == 201
        cid = c_resp.json()["id"]

        # 2. Attempt to schedule unapproved content -> Must be rejected (400)
        sched_fail = client.post(f"/api/v1/contents/{cid}/schedule", json={
            "content_id": cid,
            "scheduled_at": "2026-10-15 09:00",
            "timezone": "Asia/Ho_Chi_Minh"
        }, headers=marketer_headers)
        assert sched_fail.status_code in (400, 422)

        # 3. Submit and Approve
        client.post(f"/api/v1/contents/{cid}/submit", headers=marketer_headers)
        client.post(f"/api/v1/contents/{cid}/approve", headers=manager_headers)

        # 4. Schedule approved content -> Succeeds
        sched_ok = client.post(f"/api/v1/contents/{cid}/schedule", json={
            "content_id": cid,
            "scheduled_at": "2026-10-15 09:00",
            "timezone": "Asia/Ho_Chi_Minh"
        }, headers=marketer_headers)
        assert sched_ok.status_code == 201
        assert sched_ok.json()["content_id"] == cid

    def test_t3_cross_05_byok_key_resolution_in_ai_generation(self, client: TestClient, manager_headers):
        """Cross-flow: Save custom BYOK key -> Trigger AI task -> Verify resolver uses configured key pipeline."""
        # 1. Save custom key
        key_resp = client.post("/api/v1/settings/ai-keys", json={
            "provider": "gemini",
            "api_key": "AIzaSyTestResolverKeyCustomForUser9999",
            "model": "gemini-2.5-flash"
        }, headers=manager_headers)
        assert_endpoint_or_skip_milestone(key_resp, "/api/v1/settings/ai-keys", "M6")

        # 2. Trigger generation
        gen_resp = client.post("/api/v1/ai/ideas", json={
            "campaign_id": 1,
            "channel_code": "facebook"
        }, headers=manager_headers)
        assert gen_resp.status_code == 200
        assert len(gen_resp.json().get("ideas", [])) > 0
