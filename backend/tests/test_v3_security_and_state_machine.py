import pytest
from app.models.entities import Campaign, MarketingContent, User, CampaignMember, ContentReview
from app.core.security import create_access_token, RoleChecker
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import HTTPException
from app.services.ai.ai_service import ai_service

def get_auth_headers(client, email: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}

def get_marketer_headers(client) -> dict:
    return get_auth_headers(client, "marketer@ictu.edu.vn", "Marketer@123")

def get_manager_headers(client) -> dict:
    return get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")


# ==============================================================================
# 1. RECORD-LEVEL AUTHORIZATION (NFR01) TESTS
# ==============================================================================

class TestRecordLevelAuthorizationNFR01:
    """Kiểm thử toàn diện phân quyền mức bản ghi (Record-Level Authorization).
    - Marketer chỉ được thao tác trên tài nguyên mình sở hữu hoặc tham gia.
    - Admin/Manager có toàn quyền.
    """

    def test_marketer_cannot_access_foreign_campaign(self, client):
        """Marketer bị chặn 403 khi cố xem hoặc sửa chiến dịch không thuộc quyền sở hữu/thành viên (Campaign 2)."""
        mkt_headers = get_marketer_headers(client)

        # GET /campaigns/2
        r_get = client.get("/api/v1/campaigns/2", headers=mkt_headers)
        assert r_get.status_code == 403
        assert "Not authorized" in r_get.json()["detail"]

        # PUT /campaigns/2
        r_put = client.put("/api/v1/campaigns/2", json={"name": "Hacked Campaign Name"}, headers=mkt_headers)
        assert r_put.status_code == 403
        assert "Not authorized" in r_put.json()["detail"]

    def test_manager_can_access_all_campaigns(self, client):
        """Manager/Admin được phép truy cập tất cả các chiến dịch trong hệ thống."""
        mgr_headers = get_manager_headers(client)
        assert client.get("/api/v1/campaigns/1", headers=mgr_headers).status_code == 200
        assert client.get("/api/v1/campaigns/2", headers=mgr_headers).status_code == 200

    def test_marketer_campaign_list_scoped(self, client):
        """GET /campaigns của Marketer chỉ trả về các chiến dịch thuộc phạm vi sở hữu/thành viên."""
        mkt_headers = get_marketer_headers(client)
        resp = client.get("/api/v1/campaigns", headers=mkt_headers)
        assert resp.status_code == 200
        campaign_ids = [c["id"] for c in resp.json()]
        assert 1 in campaign_ids
        assert 2 not in campaign_ids

    def test_manager_campaign_list_unrestricted(self, client):
        """GET /campaigns của Manager trả về tất cả các chiến dịch."""
        mgr_headers = get_manager_headers(client)
        resp = client.get("/api/v1/campaigns", headers=mgr_headers)
        assert resp.status_code == 200
        campaign_ids = [c["id"] for c in resp.json()]
        assert 1 in campaign_ids
        assert 2 in campaign_ids

    def test_marketer_cannot_create_content_for_foreign_campaign(self, client):
        """Marketer không thể tạo bài viết cho chiến dịch mà mình không có quyền sở hữu hoặc thành viên."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 2,
            "channel_id": 1,
            "title": "Bài viết trái phép",
            "body": "Nội dung bài viết",
            "cta": "Click"
        }, headers=mkt_headers)
        assert resp.status_code == 403
        assert "Not authorized" in resp.json()["detail"]

    def test_marketer_cannot_access_metrics_of_foreign_campaign(self, client):
        """Marketer bị chặn 403 khi truy cập metrics hoặc KPI của chiến dịch người khác."""
        mkt_headers = get_marketer_headers(client)

        # GET /campaigns/2/metrics
        r_get_m = client.get("/api/v1/campaigns/2/metrics", headers=mkt_headers)
        assert r_get_m.status_code == 403
        assert "Not authorized" in r_get_m.json()["detail"]

        # POST /campaigns/2/metrics
        r_post_m = client.post("/api/v1/campaigns/2/metrics", json={
            "campaign_id": 2,
            "channel_id": 1,
            "metric_date": "2026-10-15",
            "views": 100,
            "clicks": 10,
            "conversions": 1,
            "cost": 100000,
            "revenue": 300000
        }, headers=mkt_headers)
        assert r_post_m.status_code == 403
        assert "Not authorized" in r_post_m.json()["detail"]

        # GET /campaigns/2/kpi
        r_kpi = client.get("/api/v1/campaigns/2/kpi", headers=mkt_headers)
        assert r_kpi.status_code == 403
        assert "Not authorized" in r_kpi.json()["detail"]

    def test_marketer_cannot_invoke_ai_for_foreign_campaign(self, client):
        """Marketer không được gọi AI Ideas, Draft, Summary với chiến dịch không thuộc quyền hạn."""
        mkt_headers = get_marketer_headers(client)

        r_ideas = client.post("/api/v1/ai/ideas", json={
            "campaign_id": 2,
            "channel_code": "facebook"
        }, headers=mkt_headers)
        assert r_ideas.status_code == 403
        assert "Not authorized" in r_ideas.json()["detail"]

        r_draft = client.post("/api/v1/ai/draft", json={
            "campaign_id": 2,
            "channel_code": "facebook",
            "selected_idea": "Ý tưởng trái phép"
        }, headers=mkt_headers)
        assert r_draft.status_code == 403
        assert "Not authorized" in r_draft.json()["detail"]

        r_sum = client.post("/api/v1/ai/summary", json={
            "campaign_id": 2
        }, headers=mkt_headers)
        assert r_sum.status_code == 403
        assert "Not authorized" in r_sum.json()["detail"]

    def test_marketer_dashboard_scoped(self, client):
        """Dashboard /analytics/dashboard và /metrics/dashboard của Marketer chỉ tính toán dựa trên chiến dịch của họ."""
        mkt_headers = get_marketer_headers(client)
        resp = client.get("/api/v1/analytics/dashboard", headers=mkt_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["campaigns_summary"]["total"] == 1

        resp_alias = client.get("/api/v1/metrics/dashboard", headers=mkt_headers)
        assert resp_alias.status_code == 200
        assert resp_alias.json()["campaigns_summary"]["total"] == 1


# ==============================================================================
# 2. STATE MACHINE HARDENING & WORKFLOW INTEGRITY
# ==============================================================================

class TestStateMachineHardening:
    """Kiểm thử khóa chặt quy trình State Machine Human-in-the-loop."""

    def test_disallow_create_content_directly_approved(self, client):
        """Cấm tạo bài viết trực tiếp ở trạng thái APPROVED qua POST /contents."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Hack Approve on Create",
            "body": "Nội dung bypass",
            "status": "APPROVED"
        }, headers=mkt_headers)
        assert resp.status_code == 400
        assert "Cannot create content directly in APPROVED or PUBLISHED status" in resp.json()["detail"]

    def test_disallow_create_content_directly_published(self, client):
        """Cấm tạo bài viết trực tiếp ở trạng thái PUBLISHED qua POST /contents."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Hack Publish on Create",
            "body": "Nội dung bypass",
            "status": "PUBLISHED"
        }, headers=mkt_headers)
        assert resp.status_code == 400
        assert "Cannot create content directly in APPROVED or PUBLISHED status" in resp.json()["detail"]

    def test_disallow_direct_transition_to_approved_or_published_via_put(self, client):
        """Cấm PUT trực tiếp sang APPROVED hoặc PUBLISHED."""
        mkt_headers = get_marketer_headers(client)
        r_app = client.put("/api/v1/contents/1", json={"status": "APPROVED"}, headers=mkt_headers)
        assert r_app.status_code == 400
        assert "Direct transition to APPROVED or PUBLISHED via update is forbidden" in r_app.json()["detail"]

        r_pub = client.put("/api/v1/contents/1", json={"status": "PUBLISHED"}, headers=mkt_headers)
        assert r_pub.status_code == 400
        assert "Direct transition to APPROVED or PUBLISHED via update is forbidden" in r_pub.json()["detail"]

    def test_marketer_cannot_publish_content(self, client):
        """Marketer không được phép gọi POST /contents/{id}/publish (403 Forbidden)."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents/1/publish", headers=mkt_headers)
        assert resp.status_code == 403
        assert "trái quyền" in resp.json()["detail"].lower()

    def test_cannot_publish_unapproved_content(self, client, db_session):
        """Không thể publish nội dung chưa qua phê duyệt (chưa ở APPROVED)."""
        mgr_headers = get_manager_headers(client)
        # Đưa content 1 về IN_REVIEW
        c1 = db_session.query(MarketingContent).filter(MarketingContent.id == 1).first()
        c1.status = "IN_REVIEW"
        db_session.commit()

        resp = client.post("/api/v1/contents/1/publish", headers=mgr_headers)
        assert resp.status_code == 400
        assert "APPROVED" in resp.json()["detail"]

    def test_manager_can_publish_approved_content(self, client, db_session):
        """Manager có quyền xuất bản nội dung khi nội dung đã ở trạng thái APPROVED."""
        mgr_headers = get_manager_headers(client)
        c1 = db_session.query(MarketingContent).filter(MarketingContent.id == 1).first()
        c1.status = "APPROVED"
        db_session.commit()

        resp = client.post("/api/v1/contents/1/publish", headers=mgr_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "PUBLISHED"


# ==============================================================================
# 3. ROLECHECKER AND INACTIVE USER STATUS TESTS
# ==============================================================================

class TestRoleCheckerActiveStatus:
    """Kiểm tra RoleChecker đồng bộ với user.status == 'ACTIVE' trong CSDL."""

    def test_inactive_user_rejected_by_role_checker(self, client, db_session):
        """Tài khoản bị vô hiệu hóa hoặc bị khóa (status != ACTIVE) bị RoleChecker chặn 403."""
        user = db_session.query(User).filter(User.email == "manager@ictu.edu.vn").first()
        user.status = "DISABLED"
        db_session.commit()

        token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post("/api/v1/contents/1/approve", headers=headers)
        assert resp.status_code == 403
        assert "inactive or suspended" in resp.json()["detail"].lower() or "vô hiệu hóa" in resp.json()["detail"].lower()

        # Phục hồi trạng thái ACTIVE
        user.status = "ACTIVE"
        db_session.commit()


# ==============================================================================
# 4. AI FALLBACK ZERO HALLUCINATION & METADATA TESTS
# ==============================================================================

class TestAIFallbackZeroHallucination:
    """Kiểm tra AI fallback không có ảo giác và tách bạch cờ is_fallback / model_provider."""

    def test_ai_fallback_metadata_and_flags(self, client):
        """Fallback trả về đầy đủ is_fallback=True và model_provider='template-fallback-engine'."""
        mkt_headers = get_marketer_headers(client)
        from unittest.mock import patch
        with patch.object(ai_service, "api_key", ""):
            resp = client.post("/api/v1/ai/summary", json={"campaign_id": 1}, headers=mkt_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_fallback"] is True
            assert data["model_provider"] == "template-fallback-engine"

    def test_ai_fallback_summary_contains_no_hallucinations(self, client):
        """Fallback Summary không được nhắc tới 'khung giờ vàng', 'cuối tuần' hay giờ giấc ảo giác."""
        mkt_headers = get_marketer_headers(client)
        from unittest.mock import patch
        with patch.object(ai_service, "api_key", ""):
            resp = client.post("/api/v1/ai/summary", json={"campaign_id": 1}, headers=mkt_headers)
            assert resp.status_code == 200
            data = resp.json()
            combined_text = " ".join(data["weaknesses"] + data["recommendations"]).lower()

            assert "khung giờ vàng" not in combined_text
            assert "cuối tuần" not in combined_text
            assert "19:00" not in combined_text
            assert "21:00" not in combined_text
            assert "11h30" not in combined_text
            assert "20h00" not in combined_text

    def test_ai_ideas_and_draft_fallback_flags(self, client):
        """Ideas và Draft fallback trả về đúng cờ is_fallback=True và model_provider."""
        mkt_headers = get_marketer_headers(client)
        from unittest.mock import patch
        with patch.object(ai_service, "api_key", ""):
            r_ideas = client.post("/api/v1/ai/ideas", json={
                "campaign_id": 1,
                "channel_code": "facebook"
            }, headers=mkt_headers)
            assert r_ideas.status_code == 200
            assert r_ideas.json()["is_fallback"] is True
            assert r_ideas.json()["model_provider"] == "template-fallback-engine"

            r_draft = client.post("/api/v1/ai/draft", json={
                "campaign_id": 1,
                "channel_code": "facebook",
                "selected_idea": "Ý tưởng thử nghiệm"
            }, headers=mkt_headers)
            assert r_draft.status_code == 200
            assert r_draft.json()["is_fallback"] is True
            assert r_draft.json()["model_provider"] == "template-fallback-engine"

    def test_live_llm_flag_distinction(self, client):
        """Khi Live LLM trả lời thành công, is_fallback=False và model_provider phản ánh provider thật."""
        mkt_headers = get_marketer_headers(client)
        import json
        from unittest.mock import patch
        mock_summary = json.dumps({
            "executive_summary": "Tóm tắt từ Gemini Live",
            "strengths": ["Điểm mạnh từ LLM"],
            "weaknesses": ["Điểm yếu từ LLM"],
            "recommendations": ["Khuyến nghị từ LLM"],
            "warnings": []
        })
        with patch.object(ai_service, "_call_provider_with_retry", return_value=mock_summary):
            ai_service.api_key = "gemini_mock_key"
            resp = client.post("/api/v1/ai/summary", json={"campaign_id": 1}, headers=mkt_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_fallback"] is False
            assert "gemini" in data["model_provider"].lower() or "open" in data["model_provider"].lower()
