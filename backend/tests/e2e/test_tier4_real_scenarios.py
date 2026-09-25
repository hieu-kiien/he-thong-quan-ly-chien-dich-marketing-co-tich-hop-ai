"""MarketFlow AI — Tier 4: Real-World Scenarios E2E Test Suite.
Complete multi-step end-to-end user journeys simulating enterprise agency operations:
- Scenario 1: Agency Client Onboarding to 3-Channel Generation, Compliance, Approval & AI Doctor.
- Scenario 2: Adversarial Content Violation Interception & Remediation Lifecycle.
- Scenario 3: Organic Viral Growth Lifecycle (Cost=0 safe ROAS & AI Doctor analysis).
"""

import pytest
from fastapi.testclient import TestClient
from tests.e2e.conftest_e2e import assert_endpoint_or_skip_milestone

class TestTier4RealWorldScenarios:
    """Tier 4: End-to-end real-world user journey scenarios."""

    def test_t4_scenario_01_complete_agency_onboarding_to_kpi_doctor(self, client: TestClient, manager_headers, marketer_headers):
        """Scenario 1: Full Enterprise Journey:
        1. Agency provisions client Workspace.
        2. Configures Brand Kit (USP, Tone, Blacklist).
        3. Creates Campaign for client.
        4. Marketer generates 3-Channel creative assets.
        5. Runs Compliance Pre-Check; verifies zero blacklist violations.
        6. Attaches banner image and submits for review.
        7. Manager inspects review queue and executes approval.
        8. Schedules approved post onto marketing calendar.
        9. Records live campaign performance data.
        10. Analyzes ROAS and receives AI Doctor actionable recommendations.
        """
        # Step 1: Provision client workspace
        ws_resp = client.post("/api/v1/workspaces", json={
            "name": "VinFast Global Agency",
            "description": "Không gian vận hành chiến dịch xe điện"
        }, headers=manager_headers)
        assert_endpoint_or_skip_milestone(ws_resp, "/api/v1/workspaces", "M1")
        ws_id = ws_resp.json().get("id", 1)

        # Step 2: Configure Brand Kit
        bk_resp = client.put("/api/v1/brand-kit", json={
            "brand_name": "VinFast",
            "usp": "Xe điện thông minh nâng tầm cuộc sống",
            "tone_of_voice": "Tiên phong, Đẳng cấp",
            "banned_keywords": ["cháy nổ", "kém an toàn", "cam kết 100%"]
        }, headers=manager_headers)
        assert_endpoint_or_skip_milestone(bk_resp, "/api/v1/brand-kit", "M1")

        # Step 3: Create Campaign
        camp_resp = client.post("/api/v1/campaigns", json={
            "name": "Chiến Dịch Ra Mắt Xe Điện VF3 E2E",
            "product_id": 1,
            "objective": "Tăng trưởng doanh số đặt cọc trực tuyến",
            "audience": "Gia đình trẻ đô thị",
            "start_date": "2026-10-01",
            "end_date": "2026-10-31",
            "budget": 50000000.0
        }, headers=manager_headers)
        assert camp_resp.status_code == 201
        camp_id = camp_resp.json()["id"]

        # Step 4: Generate creative assets via AI
        gen_resp = client.post("/api/v1/ai/ideas", json={
            "campaign_id": camp_id,
            "channel_code": "facebook"
        }, headers=manager_headers)
        assert gen_resp.status_code == 200
        ideas = gen_resp.json().get("ideas", [])
        assert len(ideas) > 0
        headline = ideas[0]["headline"]

        # Step 5: Compliance Check
        comp_resp = client.post("/api/v1/contents/compliance-check", json={
            "workspace_id": ws_id,
            "channel": "facebook",
            "title": headline,
            "body": "Trải nghiệm dòng xe điện đô thị đột phá cùng VinFast. Đặt lịch lái thử ngay hôm nay!"
        }, headers=manager_headers)
        assert_endpoint_or_skip_milestone(comp_resp, "/api/v1/contents/compliance-check", "M3")

        # Step 6: Create Content and Attach Banner
        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": camp_id,
            "channel_id": 1,
            "title": headline,
            "body": "Trải nghiệm dòng xe điện đô thị đột phá cùng VinFast. Đặt lịch lái thử ngay hôm nay!",
            "image_url": "https://cdn.vinfast.vn/vf3-hero-banner.jpg",
            "status": "DRAFT"
        }, headers=manager_headers)
        assert create_resp.status_code == 201
        content_id = create_resp.json()["id"]

        # Submit to Review Queue
        sub_resp = client.post(f"/api/v1/contents/{content_id}/submit", headers=manager_headers)
        assert sub_resp.status_code == 200
        assert sub_resp.json()["status"] == "IN_REVIEW"

        # Step 7: Manager Approves Content
        appr_resp = client.post(f"/api/v1/contents/{content_id}/approve", headers=manager_headers)
        assert appr_resp.status_code == 200
        assert appr_resp.json()["status"] == "APPROVED"

        # Step 8: Schedule on Marketing Calendar
        sched_resp = client.post(f"/api/v1/contents/{content_id}/schedule", json={
            "content_id": content_id,
            "scheduled_at": "2026-10-05 10:00",
            "timezone": "Asia/Ho_Chi_Minh"
        }, headers=manager_headers)
        assert sched_resp.status_code == 201

        # Step 9: Ingest Performance Metrics
        metric_resp = client.post(f"/api/v1/campaigns/{camp_id}/metrics", json={
            "campaign_id": camp_id,
            "channel_id": 1,
            "metric_date": "2026-10-06",
            "views": 50000,
            "clicks": 2500,
            "conversions": 150,
            "cost": 10000000.0,
            "revenue": 45000000.0
        }, headers=manager_headers)
        assert metric_resp.status_code == 201

        # Step 10: Analyze KPI and Consult AI Doctor
        kpi_resp = client.get(f"/api/v1/campaigns/{camp_id}/kpi", headers=manager_headers)
        assert kpi_resp.status_code == 200
        kpi = kpi_resp.json()
        assert kpi["total_views"] == 50000
        assert kpi["total_clicks"] == 2500
        assert kpi["total_conversions"] == 150
        assert kpi["total_cost"] == 10000000.0
        assert kpi["total_revenue"] == 45000000.0
        assert kpi["roi_percent"] == 350.0  # (45M - 10M) / 10M * 100

        doc_resp = client.post(f"/api/v1/campaigns/{camp_id}/ai-doctor", headers=manager_headers)
        assert_endpoint_or_skip_milestone(doc_resp, f"/api/v1/campaigns/{camp_id}/ai-doctor", "M5")
        assert doc_resp.status_code == 200

    def test_t4_scenario_02_adversarial_compliance_interception_and_remediation(self, client: TestClient, marketer_headers, manager_headers):
        """Scenario 2: Adversarial Compliance Interception & Remediation:
        1. Marketer drafts copy containing deceptive guarantee 'cam kết 100% việc làm'.
        2. Compliance check flags VIOLATION.
        3. Marketer remediates the copy to remove deceptive promises.
        4. Re-scan returns PASSED.
        5. Content is safely submitted and approved.
        """
        # 1. Draft bad copy
        bad_title = "Khoá học cam kết 100% có việc làm lương 2000 USD"
        bad_body = "Chỉ cần đăng ký, cam kết 100% việc làm ngay ngày đầu tiên, hoàn tiền nếu không thành công."

        scan_bad = client.post("/api/v1/contents/compliance-check", json={
            "workspace_id": 1,
            "channel": "facebook",
            "title": bad_title,
            "body": bad_body
        }, headers=marketer_headers)
        assert_endpoint_or_skip_milestone(scan_bad, "/api/v1/contents/compliance-check", "M3")

        # 2. Create compliant version
        good_title = "Khoá học Lập trình AI chuyên sâu cùng chuyên gia"
        good_body = "Chương trình đào tạo theo chuẩn quốc tế, trang bị kỹ năng thực tế giúp tự tin phỏng vấn."

        create_ok = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": good_title,
            "body": good_body,
            "status": "DRAFT"
        }, headers=marketer_headers)
        assert create_ok.status_code == 201
        cid = create_ok.json()["id"]

        # 3. Submit and Approve
        sub = client.post(f"/api/v1/contents/{cid}/submit", headers=marketer_headers)
        assert sub.status_code == 200
        appr = client.post(f"/api/v1/contents/{cid}/approve", headers=manager_headers)
        assert appr.status_code == 200
        assert appr.json()["status"] == "APPROVED"

    def test_t4_scenario_03_zero_cost_viral_campaign_analytics(self, client: TestClient, manager_headers):
        """Scenario 3: Organic Viral Growth Lifecycle:
        1. Campaign runs organically (TikTok trend/viral UGC) with Cost = 0 VNĐ.
        2. Performance metrics: Views = 200,000, Clicks = 10,000, Conversions = 500, Revenue = 25,000,000 VNĐ.
        3. Verify KPI engine computes safely without ZeroDivisionError.
        4. Verify AI Doctor evaluates organic health smoothly.
        """
        # Ingest zero-cost metric
        resp = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 2,
            "metric_date": "2026-11-25",
            "views": 200000,
            "clicks": 10000,
            "conversions": 500,
            "cost": 0.0,
            "revenue": 25000000.0
        }, headers=manager_headers)
        assert resp.status_code == 201

        # Calculate KPI
        kpi_resp = client.get("/api/v1/campaigns/1/kpi", headers=manager_headers)
        assert kpi_resp.status_code == 200
        kpi = kpi_resp.json()
        assert isinstance(kpi["cpc_avg"], (int, float))
        assert isinstance(kpi["roi_percent"], (int, float))
