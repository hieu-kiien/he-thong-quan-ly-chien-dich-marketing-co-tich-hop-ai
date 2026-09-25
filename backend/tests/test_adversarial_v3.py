"""
Test Suite: Adversarial Security & Robustness Verification V3 (MarketFlow AI)
Team: Scrum 2 (AI Evaluation & Verification Engineering)
Integrity Mode: Strict Empirical / Zero Facade

Coverage:
1. NFR01 Record-Level Access Control Hardening:
   - Marketer attempting cross-tenant / unauthorized access to Campaigns, Contents, Metrics, AI Context
   - Blocked with HTTP 403 Forbidden
2. Content State Machine Tamper-Resistance:
   - Forbids direct creation of APPROVED or PUBLISHED content via POST /api/v1/contents (HTTP 400)
   - Forbids direct state elevation to APPROVED or PUBLISHED via PUT /api/v1/contents/{id} (HTTP 400)
   - Anti-tampering auto-downgrade to AI_DRAFT upon unauthorized content modification
3. Inactive / Suspended Account Invalidation:
   - Valid JWT tokens for users with status != 'ACTIVE' (INACTIVE, SUSPENDED) rejected with HTTP 403 Forbidden
4. AI Fallback De-Hallucination & Grounding:
   - Fallback summaries grounded strictly in aggregate input metrics
   - Absolute zero hallucination on golden hours ("khung giờ vàng"), hourly distribution, or weekends ("cuối tuần")
"""

import pytest
import re
from unittest.mock import patch
from app.models.entities import User, Campaign, CampaignMember, MarketingContent, CampaignMetric
from app.core.security import create_access_token, hash_password
from app.schemas.schemas import AISummaryResponse, AIIdeaResponse, AIDraftResponse
from app.services.ai.ai_service import ai_service


# ==============================================================================
# Helpers
# ==============================================================================

def get_auth_token(client, email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Authentication failed for {email}: {resp.text}"
    return resp.json()["access_token"]


def get_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. Adversarial Record-Level Authorization (NFR01)
# ==============================================================================

class TestAdversarialRecordLevelAuthorization:
    """Kiểm thử đối kháng ngăn chặn vượt quyền truy cập phạm vi bản ghi (NFR01).
    Marketer chỉ được thao tác trên tài nguyên do mình sở hữu hoặc tham gia.
    Mọi hành vi truy cập trái phép vào tài nguyên người khác đều bị chặn HTTP 403 Forbidden.
    """

    def test_adv_marketer_access_foreign_campaign_forbidden(self, client, db_session):
        """Kẻ tấn công (Marketer sở hữu Camp 1) cố tình GET, PUT, DELETE chiến dịch của Manager (Camp 2)."""
        token = get_auth_token(client, "marketer@ictu.edu.vn", "Marketer@123")
        headers = get_headers(token)

        # GET foreign campaign -> 403 Forbidden
        resp_get = client.get("/api/v1/campaigns/2", headers=headers)
        assert resp_get.status_code == 403
        assert "Not authorized" in resp_get.json()["detail"]

        # PUT foreign campaign -> 403 Forbidden
        resp_put = client.put("/api/v1/campaigns/2", json={"name": "Attacker Hijacked Campaign"}, headers=headers)
        assert resp_put.status_code == 403
        assert "Not authorized" in resp_put.json()["detail"]

        # DELETE foreign campaign -> 403 Forbidden (chỉ MANAGER mới có quyền xóa)
        resp_del = client.delete("/api/v1/campaigns/2", headers=headers)
        assert resp_del.status_code == 403

    def test_adv_intruder_marketer_access_all_foreign_resources_forbidden(self, client, db_session):
        """Tạo một Marketer thứ hai (Intruder) không sở hữu Camp 1 và Camp 2, cố tình truy cập tài nguyên Camp 1."""
        intruder = User(
            email="intruder@ictu.edu.vn",
            full_name="Attacker Marketer",
            password_hash=hash_password("Intruder@123"),
            role="MARKETER",
            status="ACTIVE"
        )
        db_session.add(intruder)
        db_session.commit()
        db_session.refresh(intruder)

        token = get_auth_token(client, "intruder@ictu.edu.vn", "Intruder@123")
        headers = get_headers(token)

        # Thử truy cập Campaign 1
        assert client.get("/api/v1/campaigns/1", headers=headers).status_code == 403
        assert client.put("/api/v1/campaigns/1", json={"budget": 999999999}, headers=headers).status_code == 403

        # Thử tạo Content cho Campaign 1
        resp_post_content = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Nội dung độc hại",
            "body": "Spam payload",
            "cta": "Click"
        }, headers=headers)
        assert resp_post_content.status_code == 403
        assert "Not authorized" in resp_post_content.json()["detail"]

        # Thử đọc và sửa Content 1 (thuộc Camp 1, tạo bởi Marketer 1)
        assert client.get("/api/v1/contents/1", headers=headers).status_code == 403
        assert client.put("/api/v1/contents/1", json={"title": "Hacked Title"}, headers=headers).status_code == 403
        assert client.post("/api/v1/contents/1/submit", headers=headers).status_code == 403
        assert client.delete("/api/v1/campaigns/1", headers=headers).status_code == 403

    def test_adv_marketer_metrics_and_kpi_tamper_forbidden(self, client, db_session):
        """Marketer cố tình xem hoặc ghi trộm số liệu KPI của chiến dịch người khác."""
        token = get_auth_token(client, "marketer@ictu.edu.vn", "Marketer@123")
        headers = get_headers(token)

        # Xem metrics của Campaign 2
        assert client.get("/api/v1/campaigns/2/metrics", headers=headers).status_code == 403
        assert client.get("/api/v1/metrics/campaign/2", headers=headers).status_code == 403

        # Xem KPI của Campaign 2
        assert client.get("/api/v1/campaigns/2/kpi", headers=headers).status_code == 403
        assert client.get("/api/v1/metrics/campaign/2/kpi", headers=headers).status_code == 403

        # Ghi trộm metric vào Campaign 2
        resp_post_metric = client.post("/api/v1/campaigns/2/metrics", json={
            "campaign_id": 2,
            "channel_id": 1,
            "metric_date": "2026-10-20",
            "views": 500,
            "clicks": 50,
            "conversions": 2,
            "cost": 100000.0,
            "revenue": 500000.0
        }, headers=headers)
        assert resp_post_metric.status_code == 403
        assert "Not authorized" in resp_post_metric.json()["detail"]

    def test_adv_marketer_ai_context_theft_forbidden(self, client, db_session):
        """Marketer cố tình sinh nội dung AI, tóm tắt hiệu suất hoặc đọc AI log của chiến dịch người khác."""
        token = get_auth_token(client, "marketer@ictu.edu.vn", "Marketer@123")
        headers = get_headers(token)

        # Gọi AI Ideas cho Campaign 2 -> 403 Forbidden
        resp_ideas = client.post("/api/v1/ai/ideas", json={
            "campaign_id": 2,
            "channel_code": "facebook"
        }, headers=headers)
        assert resp_ideas.status_code == 403
        assert "Not authorized" in resp_ideas.json()["detail"]

        # Gọi AI Draft cho Campaign 2 -> 403 Forbidden
        resp_draft = client.post("/api/v1/ai/draft", json={
            "campaign_id": 2,
            "channel_code": "facebook",
            "selected_idea": "Chiếm quyền ngữ cảnh"
        }, headers=headers)
        assert resp_draft.status_code == 403
        assert "Not authorized" in resp_draft.json()["detail"]

        # Gọi AI Summary cho Campaign 2 -> 403 Forbidden
        resp_summary = client.post("/api/v1/ai/summary", json={
            "campaign_id": 2
        }, headers=headers)
        assert resp_summary.status_code == 403
        assert "Not authorized" in resp_summary.json()["detail"]

        # Xem AI Logs của Campaign 2 -> 403 Forbidden
        resp_logs = client.get("/api/v1/ai/logs?campaign_id=2", headers=headers)
        assert resp_logs.status_code == 403
        assert "Not authorized" in resp_logs.json()["detail"]


# ==============================================================================
# 2. Adversarial State Machine Bypass & Anti-Tampering
# ==============================================================================

class TestAdversarialStateMachineBypass:
    """Kiểm thử đối kháng ngăn chặn bypass luồng duyệt nội dung (State Machine Anti-Bypass).
    Không một tác nhân nào có thể tự ý gán trạng thái APPROVED hoặc PUBLISHED qua POST / PUT thông thường.
    """

    def test_adv_direct_post_approved_rejected_with_400(self, client):
        """Cố tình tạo bài viết trực tiếp ở trạng thái APPROVED qua POST /contents -> HTTP 400 Bad Request."""
        headers = get_headers(get_auth_token(client, "marketer@ictu.edu.vn", "Marketer@123"))
        payload = {
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bypass Test - Direct Approved Post",
            "body": "Nội dung cố tình gắn trạng thái đã duyệt",
            "cta": "Click ngay",
            "status": "APPROVED"
        }
        resp = client.post("/api/v1/contents", json=payload, headers=headers)
        assert resp.status_code == 400
        assert "không thể tạo bài viết trực tiếp ở trạng thái approved" in resp.json()["detail"].lower() or \
               "cannot create content directly in approved" in resp.json()["detail"].lower()

    def test_adv_direct_post_published_rejected_with_400(self, client):
        """Cố tình tạo bài viết trực tiếp ở trạng thái PUBLISHED qua POST /contents -> HTTP 400 Bad Request."""
        headers = get_headers(get_auth_token(client, "marketer@ictu.edu.vn", "Marketer@123"))
        payload = {
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bypass Test - Direct Published Post",
            "body": "Nội dung cố tình gắn trạng thái đã xuất bản",
            "cta": "Click ngay",
            "status": "PUBLISHED"
        }
        resp = client.post("/api/v1/contents", json=payload, headers=headers)
        assert resp.status_code == 400
        assert "không thể tạo bài viết trực tiếp ở trạng thái approved hoặc published" in resp.json()["detail"].lower() or \
               "cannot create content directly in approved or published" in resp.json()["detail"].lower()

    def test_adv_direct_put_approved_from_draft_rejected(self, client):
        """Cố tình cập nhật status='APPROVED' từ DRAFT qua PUT /contents/{id} -> HTTP 400 Bad Request."""
        headers = get_headers(get_auth_token(client, "marketer@ictu.edu.vn", "Marketer@123"))
        # Tạo bài viết DRAFT hợp lệ
        res_create = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "DRAFT Valid Content",
            "body": "Original Body",
            "cta": "CTA"
        }, headers=headers)
        assert res_create.status_code == 201
        cid = res_create.json()["id"]

        # Cố tình đổi sang APPROVED bằng PUT
        res_put = client.put(f"/api/v1/contents/{cid}", json={"status": "APPROVED"}, headers=headers)
        assert res_put.status_code == 400
        assert "không thể chuyển trạng thái trực tiếp sang approved" in res_put.json()["detail"].lower()

    def test_adv_direct_put_published_from_draft_rejected(self, client):
        """Cố tình cập nhật status='PUBLISHED' từ DRAFT qua PUT /contents/{id} -> HTTP 400 Bad Request."""
        headers = get_headers(get_auth_token(client, "marketer@ictu.edu.vn", "Marketer@123"))
        res_create = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "DRAFT Valid Content 2",
            "body": "Original Body",
            "cta": "CTA"
        }, headers=headers)
        assert res_create.status_code == 201
        cid = res_create.json()["id"]

        # Cố tình đổi sang PUBLISHED bằng PUT
        res_put = client.put(f"/api/v1/contents/{cid}", json={"status": "PUBLISHED"}, headers=headers)
        assert res_put.status_code == 400
        assert "không thể chuyển trạng thái trực tiếp sang approved hoặc published" in res_put.json()["detail"].lower() or \
               "direct transition to approved or published via update is forbidden" in res_put.json()["detail"].lower()

    def test_adv_anti_tampering_approved_content_reverts_to_ai_draft(self, client):
        """Kiểm tra cơ chế Anti-tampering: Khi Manager đã duyệt APPROVED, nếu bài viết bị sửa đổi, nó phải tự động quay về AI_DRAFT."""
        mkt_headers = get_headers(get_auth_token(client, "marketer@ictu.edu.vn", "Marketer@123"))
        mgr_headers = get_headers(get_auth_token(client, "manager@ictu.edu.vn", "Manager@123"))

        # 1. Marketer tạo DRAFT
        r_c = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bản nháp chuẩn bị duyệt",
            "body": "Nội dung chuẩn chỉ",
            "cta": "Đăng ký"
        }, headers=mkt_headers)
        cid = r_c.json()["id"]

        # 2. Marketer submit -> IN_REVIEW
        r_sub = client.post(f"/api/v1/contents/{cid}/submit", headers=mkt_headers)
        assert r_sub.status_code == 200
        assert r_sub.json()["status"] == "IN_REVIEW"

        # 3. Manager duyệt -> APPROVED
        r_app = client.post(f"/api/v1/contents/{cid}/approve", json={"decision": "APPROVED", "reason": "Đạt chuẩn"}, headers=mgr_headers)
        assert r_app.status_code == 200
        assert r_app.json()["status"] == "APPROVED"

        # 4. Kẻ gian cố tình sửa tiêu đề nhằm chèn thông tin sai lệch sau khi đã duyệt
        r_tamper = client.put(f"/api/v1/contents/{cid}", json={"title": "Nội dung bị sửa trộm trái phép"}, headers=mkt_headers)
        assert r_tamper.status_code == 200
        # Bắt buộc trạng thái phải bị giáng cấp về AI_DRAFT, không được giữ nguyên APPROVED
        assert r_tamper.json()["status"] == "AI_DRAFT"


# ==============================================================================
# 3. Adversarial Inactive & Suspended Account Enforcement
# ==============================================================================

class TestAdversarialInactiveAndSuspendedAccounts:
    """Kiểm thử đối kháng ngăn chặn tài khoản bị khóa / đình chỉ hoạt động sử dụng hệ thống.
    Token của user có status != 'ACTIVE' (INACTIVE, SUSPENDED) phải bị từ chối HTTP 403 Forbidden.
    """

    def test_adv_inactive_user_token_rejected_with_403(self, client, db_session):
        """User có trạng thái DISABLED (không ACTIVE) trong CSDL cầm JWT token hợp lệ bị từ chối 403 Forbidden."""
        user = User(
            email="adv_disabled_user@ictu.edu.vn",
            full_name="Disabled User",
            password_hash=hash_password("Pass@123"),
            role="MARKETER",
            status="DISABLED"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token = create_access_token(data={"sub": str(user.id), "role": user.role})
        headers = get_headers(token)

        # GET /campaigns -> 403
        r_camp = client.get("/api/v1/campaigns", headers=headers)
        assert r_camp.status_code == 403
        assert "inactive or suspended" in r_camp.json()["detail"].lower()

        # GET /auth/me -> 403
        r_me = client.get("/api/v1/auth/me", headers=headers)
        assert r_me.status_code == 403

    def test_adv_suspended_manager_cannot_approve_content(self, client, db_session):
        """Manager có trạng thái DISABLED cầm Token hợp lệ không thể duyệt nội dung qua RoleChecker (HTTP 403)."""
        mgr = User(
            email="adv_disabled_mgr@ictu.edu.vn",
            full_name="Disabled Manager",
            password_hash=hash_password("Pass@123"),
            role="MANAGER",
            status="DISABLED"
        )
        db_session.add(mgr)
        db_session.commit()
        db_session.refresh(mgr)

        token = create_access_token(data={"sub": str(mgr.id), "role": mgr.role})
        headers = get_headers(token)

        # Thử duyệt Content 1
        resp_approve = client.post("/api/v1/contents/1/approve", json={
            "decision": "APPROVED",
            "reason": "Suspended approval attempt"
        }, headers=headers)
        assert resp_approve.status_code == 403
        assert "inactive or suspended" in resp_approve.json()["detail"].lower()

    def test_adv_suspended_marketer_cannot_mutate_data(self, client, db_session):
        """Marketer có trạng thái DISABLED không thể tạo mới nội dung hay chiến dịch."""
        user = User(
            email="adv_disabled_mkt2@ictu.edu.vn",
            full_name="Disabled Marketer",
            password_hash=hash_password("Pass@123"),
            role="MARKETER",
            status="DISABLED"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token = create_access_token(data={"sub": str(user.id), "role": user.role})
        headers = get_headers(token)

        resp_create = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Chiến dịch trái phép",
            "objective": "Spam",
            "audience": "All",
            "start_date": "2026-11-01",
            "end_date": "2026-11-30",
            "budget": 5000000.0
        }, headers=headers)
        assert resp_create.status_code == 403
        assert "inactive or suspended" in resp_create.json()["detail"].lower()

    def test_adv_role_checker_rejects_any_non_active_status(self, client, db_session):
        """Kiểm tra trực tiếp RoleChecker và get_current_user từ chối bất kỳ status nào != 'ACTIVE' (INACTIVE, SUSPENDED, PENDING)."""
        from app.core.security import RoleChecker, get_current_user
        from fastapi.security import HTTPAuthorizationCredentials
        from fastapi import HTTPException
        from unittest.mock import MagicMock

        checker = RoleChecker(allowed_roles=["MANAGER", "MARKETER"])
        
        for non_active_status in ["INACTIVE", "SUSPENDED", "PENDING", "DISABLED", "BANNED"]:
            fake_user = MagicMock()
            fake_user.id = 999
            fake_user.role = "MARKETER"
            fake_user.status = non_active_status

            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = fake_user

            token = create_access_token(data={"sub": "999", "role": "MARKETER"})
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            # RoleChecker phải raise HTTP 403
            with pytest.raises(HTTPException) as exc_info:
                checker(credentials=creds, db=mock_db)
            assert exc_info.value.status_code == 403
            assert "inactive or suspended" in exc_info.value.detail.lower()

            # get_current_user phải raise HTTP 403
            with pytest.raises(HTTPException) as exc_user:
                get_current_user(credentials=creds, db=mock_db)
            assert exc_user.value.status_code == 403
            assert "inactive or suspended" in exc_user.value.detail.lower()


# ==============================================================================
# 4. Adversarial AI Fallback De-Hallucination & Empirical Grounding
# ==============================================================================

class TestAdversarialAIFallbackDeHallucination:
    """Kiểm thử đối kháng thuật toán AI Fallback ngăn chặn hoàn toàn ảo giác (Zero Hallucination).
    Khi context đầu vào chỉ chứa dữ liệu tổng (views, clicks, conversions, ctr, roi), fallback tuyệt đối
    không được bịa đặt dữ liệu về thời gian (khung giờ vàng, cuối tuần, giờ cao điểm).
    """

    def test_adv_fallback_summary_absolute_zero_time_hallucination(self):
        """Kiểm tra phản hồi tóm tắt AI Fallback: Tuyệt đối không chứa nhận định bịa đặt về khung giờ vàng hay cuối tuần."""
        context = {
            "campaign_name": "Chiến dịch Thực nghiệm Đối kháng",
            "total_views": 15000,
            "total_clicks": 900,
            "total_conversions": 45,
            "ctr": 6.0,
            "cvr": 5.0,
            "cpc": "2,200",
            "total_cost": "1,980,000",
            "total_revenue": "9,000,000",
            "roi": 354.55
        }

        output = ai_service._generate_fallback("performance_summary", context)

        # 1. Tuân thủ Pydantic Schema AISummaryResponse
        validated = AISummaryResponse.model_validate({
            **output,
            "model_used": "muse-spark-1.3 (Fallback Mock)",
            "prompt_version": "v3",
            "task_type": "SUMMARY"
        })
        assert validated.task_type == "SUMMARY"
        assert len(validated.executive_summary) > 0
        assert len(validated.strengths) > 0
        assert len(validated.weaknesses) > 0
        assert len(validated.recommendations) > 0

        # 2. Duyệt toàn bộ văn bản đầu ra để phát hiện ảo giác
        full_text = " ".join([
            validated.executive_summary,
            " ".join(validated.strengths),
            " ".join(validated.weaknesses),
            " ".join(validated.recommendations),
            " ".join(validated.warnings)
        ]).lower()

        # Danh sách các từ khóa ảo giác thời gian bị cấm (Banned Hallucination Tokens)
        forbidden_hallucinations = [
            "khung giờ vàng",
            "khung giờ",
            "11h30",
            "13h00",
            "20h00",
            "22h00",
            "cuối tuần",
            "thứ bảy",
            "chủ nhật",
            "giờ cao điểm",
            "ban đêm",
            "buổi sáng"
        ]

        for forbidden in forbidden_hallucinations:
            assert forbidden not in full_text, (
                f"Phát hiện ảo giác bị cấm trong AI Fallback: '{forbidden}' xuất hiện trong nội dung: {full_text}"
            )

        # 3. Grounding: Tất cả các nhận định phải khớp với các con số trong context
        assert "15000" in full_text
        assert "900" in full_text
        assert "6.0" in full_text

        # 4. Tách biệt rõ ràng log/flag giữa AI LLM thật và Fallback Mock
        assert output.get("is_fallback") is True
        assert output.get("model_provider") == "template-fallback-engine"

    def test_adv_fallback_summary_sparse_and_zero_metric_context(self):
        """Kiểm tra AI Fallback trong kịch bản dữ liệu cực biên (0 clicks, 0 conversions, 0 revenue)."""
        sparse_context = {
            "campaign_name": "Chiến dịch Mới Khởi động",
            "total_views": 100,
            "total_clicks": 0,
            "total_conversions": 0,
            "ctr": 0.0,
            "cvr": 0.0,
            "cpc": "0",
            "total_cost": "50,000",
            "total_revenue": "0",
            "roi": -100.0
        }

        output = ai_service._generate_fallback("performance_summary", sparse_context)
        validated = AISummaryResponse.model_validate({
            **output,
            "model_used": "muse-spark-1.3 (Fallback Mock)",
            "prompt_version": "v3",
            "task_type": "SUMMARY"
        })

        full_text = " ".join([
            validated.executive_summary,
            " ".join(validated.strengths),
            " ".join(validated.weaknesses),
            " ".join(validated.recommendations)
        ]).lower()

        # Không phát sinh lỗi chia cho 0 hoặc bịa đặt thành công rực rỡ
        assert "khung giờ vàng" not in full_text
        assert "cuối tuần" not in full_text
        assert output.get("is_fallback") is True

    def test_adv_fallback_idea_and_draft_grounding(self):
        """Kiểm nghiệm tính grounding của Idea và Draft Fallback bám sát USP và Tên sản phẩm đầu vào."""
        context = {
            "product_name": "Phần mềm HRM Nhân sự AI",
            "product_usp": "Tự động hóa tính lương và KPI chuẩn xác 100%",
            "channel_name": "LinkedIn B2B",
            "selected_idea": "Giải phóng 80% thời gian cho phòng nhân sự"
        }

        # Kiểm tra Idea Fallback
        idea_out = ai_service._generate_fallback("idea_generation", context)
        validated_idea = AIIdeaResponse.model_validate({
            **idea_out,
            "model_used": "muse-spark-1.3 (Fallback Mock)",
            "prompt_version": "v3",
            "task_type": "IDEA"
        })
        assert len(validated_idea.ideas) == 5
        assert idea_out.get("is_fallback") is True
        assert any("HRM" in item.headline or "HRM" in item.concept for item in validated_idea.ideas)

        # Kiểm tra Draft Fallback
        draft_out = ai_service._generate_fallback("content_draft", context)
        validated_draft = AIDraftResponse.model_validate({
            **draft_out,
            "model_used": "muse-spark-1.3 (Fallback Mock)",
            "prompt_version": "v3",
            "task_type": "DRAFT"
        })
        assert "HRM" in validated_draft.title or "HRM" in validated_draft.body
        assert "Giải phóng 80% thời gian" in validated_draft.body
        assert draft_out.get("is_fallback") is True
