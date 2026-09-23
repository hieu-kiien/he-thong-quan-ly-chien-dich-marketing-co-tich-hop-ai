import json
from datetime import timedelta
import pytest
from unittest.mock import patch
import jwt
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import create_access_token
from app.models.entities import (
    User, Campaign, MarketingChannel, MarketingContent,
    CampaignMetric, ContentReview, MarketingSchedule, Product
)
from app.services.ai.ai_service import ai_service


# ==============================================================================
# Authentication & Header Helpers
# ==============================================================================

def get_auth_headers_for(client, email: str = "marketer@ictu.edu.vn", password: str = "Marketer@123") -> dict:
    """Helper to authenticate and return Bearer headers for a specific user."""
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def get_marketer_headers(client) -> dict:
    return get_auth_headers_for(client, "marketer@ictu.edu.vn", "Marketer@123")


def get_manager_headers(client) -> dict:
    return get_auth_headers_for(client, "manager@ictu.edu.vn", "Manager@123")


# ==============================================================================
# 1. AUTHENTICATION & SECURITY EDGE CASES
# ==============================================================================

class TestAuthenticationAndSecurityEdgeCases:
    """Kiểm thử toàn diện các trường hợp biên của xác thực và bảo mật."""

    def test_unauthenticated_campaign_endpoints_return_401(self, client):
        """Tất cả các route liên quan đến Campaign đều từ chối 401 nếu thiếu Bearer Token."""
        assert client.get("/api/v1/campaigns").status_code == 401
        assert client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Campaign Without Auth",
            "objective": "Testing",
            "audience": "Everyone",
            "start_date": "2026-10-01",
            "end_date": "2026-10-30",
            "budget": 1000.0
        }).status_code == 401
        assert client.get("/api/v1/campaigns/1").status_code == 401
        assert client.put("/api/v1/campaigns/1", json={"name": "Tampered Name"}).status_code == 401
        assert client.delete("/api/v1/campaigns/1").status_code == 401

    def test_unauthenticated_content_endpoints_return_401(self, client):
        """Tất cả các route liên quan đến Marketing Content đều từ chối 401 nếu thiếu Bearer Token."""
        assert client.get("/api/v1/contents").status_code == 401
        assert client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Title Without Auth",
            "body": "Body content",
            "cta": "Click"
        }).status_code == 401
        assert client.get("/api/v1/contents/1").status_code == 401
        assert client.put("/api/v1/contents/1", json={"title": "Hacked Title"}).status_code == 401
        assert client.post("/api/v1/contents/1/submit").status_code == 401
        assert client.post("/api/v1/contents/1/approve").status_code == 401
        assert client.post("/api/v1/contents/1/reject", json={
            "decision": "REJECTED",
            "reason": "Unauthorized attempt"
        }).status_code == 401

    def test_unauthenticated_metric_endpoints_return_401(self, client):
        """Tất cả các route metrics, KPI và dashboard đều từ chối 401 nếu không có Bearer Token."""
        assert client.get("/api/v1/campaigns/1/metrics").status_code == 401
        assert client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-10-01",
            "views": 100,
            "clicks": 10,
            "conversions": 1,
            "cost": 100.0,
            "revenue": 500.0
        }).status_code == 401
        assert client.get("/api/v1/campaigns/1/kpi").status_code == 401
        assert client.get("/api/v1/analytics/dashboard").status_code == 401

    def test_unauthenticated_channel_product_schedule_endpoints_return_401(self, client):
        """Các endpoint channels, products, categories và schedules yêu cầu Bearer Token."""
        assert client.get("/api/v1/channels").status_code == 401
        assert client.get("/api/v1/products").status_code == 401
        assert client.get("/api/v1/product-categories").status_code == 401
        assert client.get("/api/v1/schedules").status_code == 401
        assert client.post("/api/v1/contents/1/schedule", json={
            "content_id": 1,
            "scheduled_at": "2026-10-15 10:00",
            "timezone": "Asia/Ho_Chi_Minh"
        }).status_code == 401

    def test_unauthenticated_ai_endpoints_return_401(self, client):
        """Các endpoint AI Engine từ chối truy cập 401 đối với request chưa xác thực."""
        assert client.post("/api/v1/ai/ideas", json={
            "campaign_id": 1,
            "channel_code": "facebook"
        }).status_code == 401

        assert client.post("/api/v1/ai/draft", json={
            "campaign_id": 1,
            "channel_code": "facebook",
            "selected_idea": "Chiến dịch tuyển sinh"
        }).status_code == 401

        assert client.post("/api/v1/ai/summary", json={
            "campaign_id": 1
        }).status_code == 401

        assert client.get("/api/v1/ai/logs").status_code == 401

    def test_expired_jwt_token_returns_401(self, client):
        """Token JWT đã hết hạn (expired) trả về HTTP 401 Unauthorized."""
        expired_token = create_access_token(
            data={"sub": "1", "email": "marketer@ictu.edu.vn", "role": "MARKETER"},
            expires_delta=timedelta(seconds=-10)
        )
        headers = {"Authorization": f"Bearer {expired_token}"}

        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 401
        assert "hết hạn" in resp.json()["detail"].lower() or "không hợp lệ" in resp.json()["detail"].lower()

        assert client.get("/api/v1/campaigns", headers=headers).status_code == 401
        assert client.get("/api/v1/contents", headers=headers).status_code == 401

    def test_corrupted_and_malformed_tokens_return_401(self, client):
        """Các dạng token bị biến dạng, sai định dạng hoặc giả mạo secret trả về HTTP 401."""
        # 1. Chuỗi ngẫu nhiên không phải JWT
        bad_headers_1 = {"Authorization": "Bearer not-a-valid-jwt-token"}
        r1 = client.get("/api/v1/auth/me", headers=bad_headers_1)
        assert r1.status_code == 401

        # 2. JWT bị cắt cụt (truncated)
        bad_headers_2 = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.truncated"}
        r2 = client.get("/api/v1/campaigns", headers=bad_headers_2)
        assert r2.status_code == 401

        # 3. JWT ký bằng secret key khác (giả mạo signature)
        forged_token = jwt.encode(
            {"sub": "1", "email": "marketer@ictu.edu.vn", "role": "MARKETER"},
            "FORGED_SECRET_KEY_LONGER_THAN_32_BYTES_FOR_HMAC_SHA256",
            algorithm="HS256"
        )
        bad_headers_3 = {"Authorization": f"Bearer {forged_token}"}
        r3 = client.get("/api/v1/contents", headers=bad_headers_3)
        assert r3.status_code == 401

        # 4. Bearer rỗng
        bad_headers_4 = {"Authorization": "Bearer "}
        r4 = client.get("/api/v1/channels", headers=bad_headers_4)
        assert r4.status_code == 401

    def test_jwt_invalid_subject_returns_401(self, client):
        """Token thiếu subject, subject không phải số, hoặc subject là user không tồn tại trả về 401."""
        # 1. sub là chuỗi không chuyển đổi sang int được
        token_str_sub = create_access_token(data={"sub": "user_id_string_not_numeric"})
        r1 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_str_sub}"})
        assert r1.status_code == 401
        assert "không hợp lệ" in r1.json()["detail"].lower()

        # 2. Token không chứa trường 'sub'
        token_no_sub = create_access_token(data={"email": "ghost@ictu.edu.vn", "role": "MARKETER"})
        r2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_no_sub}"})
        assert r2.status_code == 401
        assert "không chứa định danh" in r2.json()["detail"].lower()

        # 3. sub trỏ đến user ID không tồn tại trong hệ thống (e.g. 999999)
        token_ghost_sub = create_access_token(data={"sub": "999999", "role": "MARKETER"})
        r3 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_ghost_sub}"})
        assert r3.status_code == 401
        assert "không tồn tại" in r3.json()["detail"].lower()

    def test_deactivated_user_receives_403_forbidden(self, client, db_session):
        """Người dùng có trạng thái DISABLED / INACTIVE bị chặn với HTTP 403 Forbidden."""
        user = db_session.query(User).filter(User.email == "marketer@ictu.edu.vn").first()
        user.status = "DISABLED"
        db_session.commit()

        token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
        headers = {"Authorization": f"Bearer {token}"}

        # Truy cập các tài nguyên được bảo vệ
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 403
        assert client.get("/api/v1/campaigns", headers=headers).status_code == 403
        assert client.get("/api/v1/contents", headers=headers).status_code == 403
        assert client.get("/api/v1/ai/logs", headers=headers).status_code == 403

    def test_login_with_deactivated_user_returns_403_forbidden(self, client, db_session):
        """Đăng nhập bằng tài khoản đã bị vô hiệu hóa trả về HTTP 403 Forbidden."""
        user = db_session.query(User).filter(User.email == "marketer@ictu.edu.vn").first()
        user.status = "DISABLED"
        db_session.commit()

        resp = client.post("/api/v1/auth/login", json={
            "email": "marketer@ictu.edu.vn",
            "password": "Marketer@123"
        })
        assert resp.status_code == 403
        assert "vô hiệu hóa" in resp.json()["detail"].lower()


# ==============================================================================
# 2. BOUNDARY VALUE & INPUT VALIDATION (ZERO 500s)
# ==============================================================================

class TestBoundaryValueAndInputValidation:
    """Kiểm thử biên dữ liệu và bảo đảm hoàn toàn không xảy ra lỗi máy chủ HTTP 500."""

    @pytest.mark.parametrize("invalid_status", [
        "HACKED_STATUS",
        "",
        "draft",           # Chữ thường không khớp ENUM quy chuẩn
        "DELETED",
        "PENDING",
        "DROP_TABLE_USERS",
        "UNKNOWN"
    ])
    def test_content_create_with_invalid_status_returns_422(self, client, invalid_status):
        """ContentCreate với status không nằm trong whitelist trả về HTTP 422, KHÔNG BAO GIỜ là 500."""
        headers = get_marketer_headers(client)
        payload = {
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Tiêu đề hợp lệ",
            "body": "Nội dung hợp lệ",
            "cta": "Tìm hiểu ngay",
            "status": invalid_status
        }
        resp = client.post("/api/v1/contents", json=payload, headers=headers)
        assert resp.status_code == 422
        assert resp.status_code != 500

    @pytest.mark.parametrize("invalid_status", [
        "CORRUPT_STATUS",
        "",
        "SUPER_ADMIN",
        "NOT_A_STATUS"
    ])
    def test_content_update_with_invalid_status_returns_422(self, client, invalid_status):
        """ContentUpdate với status không hợp lệ trả về HTTP 422, KHÔNG BAO GIỜ là 500."""
        headers = get_marketer_headers(client)
        resp = client.put("/api/v1/contents/1", json={"status": invalid_status}, headers=headers)
        assert resp.status_code == 422
        assert resp.status_code != 500

    @pytest.mark.parametrize("bad_date", [
        "2026/13/45",     # Sai dấu phân cách và sai tháng/ngày
        "invalid-date",   # Không phải ngày
        "2026-02-30",     # Tháng 2 không có ngày 30
        "2026-13-01",     # Tháng 13 không tồn tại
        "2026-00-10",     # Tháng 0 không tồn tại
        "2026-04-31",     # Tháng 4 chỉ có 30 ngày
        "01-12-2026",     # Sai thứ tự (DD-MM-YYYY thay vì YYYY-MM-DD)
        "2026.12.01",     # Dùng dấu chấm thay vì gạch ngang
    ])
    def test_campaign_create_invalid_date_formats_return_422(self, client, bad_date):
        """start_date hoặc end_date sai định dạng hoặc không tồn tại theo lịch trả về HTTP 422."""
        headers = get_marketer_headers(client)
        payload = {
            "product_id": 1,
            "name": f"Test Date Validation {bad_date}",
            "objective": "Test",
            "audience": "Test Audience",
            "start_date": bad_date,
            "end_date": "2026-12-31",
            "budget": 500000.0
        }
        resp = client.post("/api/v1/campaigns", json=payload, headers=headers)
        assert resp.status_code == 422
        assert resp.status_code != 500

    def test_campaign_create_non_string_date_type_returns_422(self, client):
        """start_date truyền kiểu số integer trả về HTTP 422 thay vì HTTP 500."""
        headers = get_marketer_headers(client)
        payload = {
            "product_id": 1,
            "name": "Integer Date Campaign",
            "objective": "Test",
            "audience": "Test Audience",
            "start_date": 12345,
            "end_date": "2026-12-31",
            "budget": 500000.0
        }
        resp = client.post("/api/v1/campaigns", json=payload, headers=headers)
        assert resp.status_code == 422

    def test_campaign_update_invalid_date_format_returns_422(self, client):
        """Cập nhật chiến dịch với ngày sai định dạng trả về HTTP 422."""
        headers = get_marketer_headers(client)
        resp = client.put("/api/v1/campaigns/1", json={"start_date": "2026/09/01"}, headers=headers)
        assert resp.status_code == 422

    @pytest.mark.parametrize("bad_date", [
        "2026/13/45",
        "2026-02-30",
        "not-a-date",
        "2026-04-31"
    ])
    def test_metric_create_invalid_date_formats_return_422(self, client, bad_date):
        """metric_date sai quy chuẩn định dạng hoặc sai lịch trả về HTTP 422, KHÔNG BAO GIỜ là 500."""
        headers = get_marketer_headers(client)
        payload = {
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": bad_date,
            "views": 100,
            "clicks": 10,
            "conversions": 1,
            "cost": 1000.0,
            "revenue": 5000.0
        }
        resp = client.post("/api/v1/campaigns/1/metrics", json=payload, headers=headers)
        assert resp.status_code == 422
        assert resp.status_code != 500

    def test_campaign_logical_date_boundaries_start_after_end_returns_422(self, client):
        """Ràng buộc logic: start_date > end_date bị từ chối với HTTP 422 Unprocessable Entity."""
        headers = get_marketer_headers(client)

        # 1. Khi tạo chiến dịch mới
        payload = {
            "product_id": 1,
            "name": "Chiến dịch ngày nghịch lý",
            "objective": "Kiểm tra start_date > end_date",
            "audience": "Sinh viên",
            "start_date": "2026-12-31",
            "end_date": "2026-12-01",  # Ngày kết thúc trước ngày bắt đầu!
            "budget": 2000000.0
        }
        resp = client.post("/api/v1/campaigns", json=payload, headers=headers)
        assert resp.status_code == 422
        assert "không được nhỏ hơn ngày bắt đầu" in resp.text

        # 2. Khi cập nhật chiến dịch
        update_payload = {
            "start_date": "2026-12-15",
            "end_date": "2026-12-10"
        }
        resp_update = client.put("/api/v1/campaigns/1", json=update_payload, headers=headers)
        assert resp_update.status_code == 422

    def test_campaign_logical_date_boundary_same_day_succeeds(self, client):
        """Biên hợp lệ: Chiến dịch trong ngày (start_date == end_date) được chấp thuận với HTTP 201."""
        headers = get_marketer_headers(client)
        payload = {
            "product_id": 1,
            "name": "Chiến dịch Flash Sale 1 Ngày",
            "objective": "Ưu đãi duy nhất ngày 11-11",
            "audience": "Khách hàng thân thiết",
            "start_date": "2026-11-11",
            "end_date": "2026-11-11",  # start_date == end_date: hợp lệ
            "budget": 1000000.0
        }
        resp = client.post("/api/v1/campaigns", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["start_date"] == "2026-11-11"
        assert data["end_date"] == "2026-11-11"

    def test_duplicate_metric_insertion_returns_409_conflict_with_detail(self, client):
        """Ghi trùng lặp chỉ số (campaign_id, channel_id, metric_date) trả về HTTP 409 Conflict với mô tả chi tiết."""
        headers = get_marketer_headers(client)
        metric_payload = {
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-15",
            "views": 500,
            "clicks": 50,
            "conversions": 5,
            "cost": 25000.0,
            "revenue": 100000.0
        }

        # Ghi lần đầu thành công
        r1 = client.post("/api/v1/campaigns/1/metrics", json=metric_payload, headers=headers)
        assert r1.status_code == 201

        # Ghi lần thứ hai cùng bộ 3 khóa trả về 409
        r2 = client.post("/api/v1/campaigns/1/metrics", json=metric_payload, headers=headers)
        assert r2.status_code == 409
        detail = r2.json()["detail"]
        assert "đã tồn tại" in detail
        assert "2026-11-15" in detail or "chiến dịch" in detail


# ==============================================================================
# 3. REVIEW WORKFLOW STATE MACHINE & ANTI-TAMPERING
# ==============================================================================

class TestReviewWorkflowStateMachineAndAntiTampering:
    """Kiểm thử vòng đời phê duyệt Human-in-the-Loop và chống can thiệp trái phép."""

    def test_hitl_full_lifecycle_draft_to_approved(self, client, db_session):
        """Quy trình HITL hoàn chỉnh: DRAFT -> submit -> IN_REVIEW -> approve -> APPROVED."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        # 1. Tạo bài viết ở trạng thái DRAFT
        content_payload = {
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Hành trình khởi nghiệp 2026",
            "body": "Nội dung bài viết kêu gọi sinh viên tham gia tuyển sinh.",
            "cta": "Đăng ký ngay hôm nay",
            "status": "DRAFT"
        }
        create_resp = client.post("/api/v1/contents", json=content_payload, headers=mkt_headers)
        assert create_resp.status_code == 201
        content_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "DRAFT"

        # 2. Marketer gửi duyệt (submit)
        submit_resp = client.post(f"/api/v1/contents/{content_id}/submit", headers=mkt_headers)
        assert submit_resp.status_code == 200
        assert submit_resp.json()["status"] == "IN_REVIEW"

        # 3. Manager phê duyệt (approve)
        approve_resp = client.post(f"/api/v1/contents/{content_id}/approve", headers=mgr_headers)
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "APPROVED"

        # 4. Kiểm tra bản ghi ContentReview trong DB
        review_log = db_session.query(ContentReview).filter(ContentReview.content_id == content_id).first()
        assert review_log is not None
        assert review_log.decision == "APPROVED"

    def test_hitl_full_lifecycle_ai_draft_to_approved(self, client):
        """Bài viết do AI sinh (AI_DRAFT) chuyển tiếp mượt mà qua submit -> approve."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        create_resp = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "AI Generated Title",
            "body": "AI Generated Content Body",
            "cta": "Khám phá ngay",
            "status": "AI_DRAFT"
        }, headers=mkt_headers)
        assert create_resp.status_code == 201
        content_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "AI_DRAFT"

        # Submit
        sub_resp = client.post(f"/api/v1/contents/{content_id}/submit", headers=mkt_headers)
        assert sub_resp.status_code == 200
        assert sub_resp.json()["status"] == "IN_REVIEW"

        # Approve
        app_resp = client.post(f"/api/v1/contents/{content_id}/approve", headers=mgr_headers)
        assert app_resp.status_code == 200
        assert app_resp.json()["status"] == "APPROVED"

    def test_direct_put_approved_status_strictly_rejected_with_400(self, client):
        """Mọi nỗ lực set status='APPROVED' trực tiếp qua PUT /contents/{id} đều bị từ chối với HTTP 400."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        # Marketer cố ý bypass
        resp_mkt = client.put("/api/v1/contents/1", json={"status": "APPROVED"}, headers=mkt_headers)
        assert resp_mkt.status_code == 400
        assert "APPROVED" in resp_mkt.json()["detail"]

        # Kể cả Manager dùng PUT thay vì endpoint /approve cũng phải bị từ chối để bảo đảm lưu vết review log
        resp_mgr = client.put("/api/v1/contents/1", json={"status": "APPROVED"}, headers=mgr_headers)
        assert resp_mgr.status_code == 400
        assert "APPROVED" in resp_mgr.json()["detail"]

    def test_modifying_approved_content_title_resets_to_ai_draft(self, client, db_session):
        """Sửa title của bài viết APPROVED tự động hạ trạng thái về AI_DRAFT và tăng version_no."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        # Đảm bảo bài viết 1 được duyệt APPROVED
        client.post("/api/v1/contents/1/approve", headers=mgr_headers)
        content = db_session.query(MarketingContent).filter(MarketingContent.id == 1).first()
        assert content.status == "APPROVED"
        initial_ver = content.version_no

        # Sửa tiêu đề
        edit_resp = client.put("/api/v1/contents/1", json={"title": "Tiêu đề đã bị can thiệp trái phép!"}, headers=mkt_headers)
        assert edit_resp.status_code == 200
        data = edit_resp.json()
        assert data["status"] == "AI_DRAFT"
        assert data["version_no"] == initial_ver + 1
        assert data["title"] == "Tiêu đề đã bị can thiệp trái phép!"

    def test_modifying_approved_content_body_resets_to_ai_draft(self, client, db_session):
        """Sửa body của bài viết APPROVED tự động hạ trạng thái về AI_DRAFT."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        client.post("/api/v1/contents/1/approve", headers=mgr_headers)
        edit_resp = client.put("/api/v1/contents/1", json={"body": "Nội dung quảng cáo bị thay đổi nội dung!"}, headers=mkt_headers)
        assert edit_resp.status_code == 200
        data = edit_resp.json()
        assert data["status"] == "AI_DRAFT"
        assert data["body"] == "Nội dung quảng cáo bị thay đổi nội dung!"

    def test_modifying_approved_content_cta_resets_to_ai_draft(self, client, db_session):
        """Sửa CTA của bài viết APPROVED tự động hạ trạng thái về AI_DRAFT."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        client.post("/api/v1/contents/1/approve", headers=mgr_headers)
        edit_resp = client.put("/api/v1/contents/1", json={"cta": "Nhấp link lừa đảo ngay!"}, headers=mkt_headers)
        assert edit_resp.status_code == 200
        data = edit_resp.json()
        assert data["status"] == "AI_DRAFT"
        assert data["cta"] == "Nhấp link lừa đảo ngay!"

    def test_rejection_workflow_with_reason_and_resubmission(self, client, db_session):
        """Quy trình từ chối bài viết: Manager từ chối có lý do -> Marketer sửa và gửi duyệt lại."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        # Bài 1 đang ở IN_REVIEW (từ seed)
        reject_payload = {
            "decision": "REJECTED",
            "reason": "Ngôn ngữ bài viết chưa phù hợp với nhóm tuổi 18-24, cần trẻ trung hơn."
        }
        reject_resp = client.post("/api/v1/contents/1/reject", json=reject_payload, headers=mgr_headers)
        assert reject_resp.status_code == 200
        assert reject_resp.json()["status"] == "REJECTED"

        # Kiểm tra nhật ký đánh giá đã ghi lại lý do
        review_record = db_session.query(ContentReview).filter(
            ContentReview.content_id == 1,
            ContentReview.decision == "REJECTED"
        ).order_by(ContentReview.id.desc()).first()
        assert review_record is not None
        assert "chưa phù hợp" in review_record.reason

        # Marketer gửi duyệt lại bài viết REJECTED
        resubmit_resp = client.post("/api/v1/contents/1/submit", headers=mkt_headers)
        assert resubmit_resp.status_code == 200
        assert resubmit_resp.json()["status"] == "IN_REVIEW"

    def test_invalid_workflow_state_transitions_rejected(self, client):
        """Không thể submit bài viết đang IN_REVIEW hoặc duyệt bài viết chưa gửi duyệt."""
        mkt_headers = get_marketer_headers(client)
        mgr_headers = get_manager_headers(client)

        # Bài 1 đã ở IN_REVIEW, submit tiếp sẽ lỗi 400
        sub_dup = client.post("/api/v1/contents/1/submit", headers=mkt_headers)
        assert sub_dup.status_code == 400
        assert "IN_REVIEW" in sub_dup.json()["detail"]

        # Tạo bài viết mới ở DRAFT, chưa submit mà Manager cố approve -> từ chối 400
        new_content = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Chưa gửi duyệt",
            "body": "Nội dung",
            "cta": "Click",
            "status": "DRAFT"
        }, headers=mkt_headers).json()

        app_err = client.post(f"/api/v1/contents/{new_content['id']}/approve", headers=mgr_headers)
        assert app_err.status_code == 400
        assert "IN_REVIEW" in app_err.json()["detail"]

    def test_marketer_forbidden_from_approving_or_rejecting(self, client):
        """Marketer không có quyền phê duyệt hoặc từ chối bài viết (HTTP 403 Forbidden)."""
        mkt_headers = get_marketer_headers(client)

        resp_app = client.post("/api/v1/contents/1/approve", headers=mkt_headers)
        assert resp_app.status_code == 403

        resp_rej = client.post("/api/v1/contents/1/reject", json={
            "decision": "REJECTED",
            "reason": "Marketer tự từ chối"
        }, headers=mkt_headers)
        assert resp_rej.status_code == 403


# ==============================================================================
# 4. AI PROVIDER RESILIENCE & SMART FALLBACK
# ==============================================================================

class TestAIProviderResilienceAndSmartFallback:
    """Kiểm thử cơ chế bẫy lỗi Schema Mismatch, JSON hỏng và Fallback tự động của AI Service."""

    def test_ai_ideas_smart_fallback_on_schema_mismatch(self, client):
        """Khi AI Provider trả về JSON hợp lệ nhưng sai schema (thiếu 'ideas'), kích hoạt Smart Fallback HTTP 200."""
        headers = get_marketer_headers(client)

        # Provider trả về JSON không chứa mảng 'ideas'
        mock_broken_schema = json.dumps({"status": "success", "result": "no ideas field"})

        with patch.object(ai_service, "_call_provider_with_retry", return_value=mock_broken_schema):
            ai_service.api_key = "mock_api_key_valid"
            ai_service.fallback_enabled = True

            payload = {
                "campaign_id": 1,
                "channel_code": "facebook",
                "tone": "thuyết phục",
                "prompt_version": "v3"
            }
            resp = client.post("/api/v1/ai/ideas", json=payload, headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["task_type"] == "IDEA"
            assert isinstance(data["ideas"], list)
            assert len(data["ideas"]) >= 1
            assert any("fallback" in w.lower() or "schema" in w.lower() for w in data.get("warnings", []))

    def test_ai_ideas_smart_fallback_on_malformed_json(self, client):
        """Khi AI Provider trả về chuỗi JSON bị vỡ hoặc ngắt cụt, bẫy lỗi và kích hoạt Fallback an toàn."""
        headers = get_marketer_headers(client)

        # Provider trả về JSON hỏng cú pháp
        mock_malformed_json = '{"ideas": [ {"angle": "Học tập", "headline": "Bị cắt ngang...'

        with patch.object(ai_service, "_call_provider_with_retry", return_value=mock_malformed_json):
            ai_service.api_key = "mock_api_key_valid"
            ai_service.fallback_enabled = True

            payload = {
                "campaign_id": 1,
                "channel_code": "facebook",
                "tone": "thuyết phục",
                "prompt_version": "v3"
            }
            resp = client.post("/api/v1/ai/ideas", json=payload, headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["ideas"]) >= 1

    def test_ai_draft_smart_fallback_on_schema_mismatch(self, client):
        """Khi sinh bài viết (draft) gặp schema mismatch, Smart Fallback trả về cấu trúc draft chuẩn nghiệp vụ."""
        headers = get_marketer_headers(client)

        # JSON thiếu title, body, cta
        mock_invalid_draft = json.dumps({"draft_text": "Chỉ có một trường duy nhất"})

        with patch.object(ai_service, "_call_provider_with_retry", return_value=mock_invalid_draft):
            ai_service.api_key = "mock_api_key_valid"
            ai_service.fallback_enabled = True

            payload = {
                "campaign_id": 1,
                "channel_code": "facebook",
                "selected_idea": "Ý tưởng đột phá năm 2026",
                "prompt_version": "v3"
            }
            resp = client.post("/api/v1/ai/draft", json=payload, headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["task_type"] == "DRAFT"
            assert "title" in data and len(data["title"]) > 0
            assert "body" in data and len(data["body"]) > 0
            assert "cta" in data and len(data["cta"]) > 0
            assert any("fallback" in w.lower() or "schema" in w.lower() for w in data.get("warnings", []))

    def test_ai_draft_smart_fallback_on_malformed_json(self, client):
        """Khi sinh bài viết gặp JSON hỏng, Fallback bảo đảm không crash 500."""
        headers = get_marketer_headers(client)

        with patch.object(ai_service, "_call_provider_with_retry", return_value="{broken json body"):
            ai_service.api_key = "mock_api_key_valid"
            ai_service.fallback_enabled = True

            payload = {
                "campaign_id": 1,
                "channel_code": "facebook",
                "selected_idea": "Ý tưởng đột phá năm 2026",
                "prompt_version": "v3"
            }
            resp = client.post("/api/v1/ai/draft", json=payload, headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert "title" in data
            assert "body" in data

    def test_ai_summary_smart_fallback_on_schema_mismatch(self, client):
        """Khi tóm tắt chiến dịch gặp schema mismatch, Fallback trả về cấu trúc summary hợp lệ."""
        headers = get_marketer_headers(client)

        # JSON thiếu strengths, weaknesses, recommendations
        mock_incomplete_summary = json.dumps({"summary": "Tóm tắt nhưng thiếu các trường phân tích"})

        with patch.object(ai_service, "_call_provider_with_retry", return_value=mock_incomplete_summary):
            ai_service.api_key = "mock_api_key_valid"
            ai_service.fallback_enabled = True

            payload = {
                "campaign_id": 1,
                "prompt_version": "v3"
            }
            resp = client.post("/api/v1/ai/summary", json=payload, headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["task_type"] == "SUMMARY"
            assert "executive_summary" in data
            assert isinstance(data["strengths"], list)
            assert isinstance(data["weaknesses"], list)
            assert isinstance(data["recommendations"], list)

    def test_ai_provider_error_returns_clean_502_when_fallback_disabled(self, client):
        """Khi tắt chế độ Fallback và AI Provider bị lỗi hoặc trả về schema sai, trả về HTTP 502 Bad Gateway (không bao giờ 500)."""
        headers = get_marketer_headers(client)

        # 1. Provider ném exception mạng
        with patch.object(ai_service, "_call_provider_with_retry", side_effect=RuntimeError("AI Provider 503 Service Unavailable")):
            ai_service.api_key = "mock_key"
            ai_service.fallback_enabled = False

            payload = {
                "campaign_id": 1,
                "channel_code": "facebook",
                "selected_idea": "Ý tưởng test",
                "prompt_version": "v3"
            }
            resp = client.post("/api/v1/ai/draft", json=payload, headers=headers)
            assert resp.status_code == 502
            assert resp.status_code != 500
            assert "lỗi" in resp.json()["detail"].lower() or "ai" in resp.json()["detail"].lower()

            # Khôi phục trạng thái mặc định
            ai_service.fallback_enabled = True
            ai_service.api_key = ""


# ==============================================================================
# 5. SQLITE FOREIGN KEY INTEGRITY
# ==============================================================================

class TestSQLiteForeignKeyIntegrity:
    """Kiểm thử ràng buộc khóa ngoại (Foreign Key) trên tầng CSDL SQLite và tầng API."""

    def test_direct_db_insert_invalid_campaign_id_triggers_fk_violation(self, db_session):
        """Thêm MarketingContent với campaign_id không tồn tại kích hoạt lỗi IntegrityError do vi phạm Foreign Key."""
        content = MarketingContent(
            campaign_id=99999,  # Không tồn tại
            channel_id=1,
            created_by=1,
            title="Content With Ghost Campaign",
            body="Should fail on commit",
            cta="None",
            status="DRAFT"
        )
        db_session.add(content)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "foreign key" in str(exc_info.value).lower()
        db_session.rollback()

    def test_direct_db_insert_invalid_channel_id_triggers_fk_violation(self, db_session):
        """Thêm MarketingContent với channel_id không tồn tại kích hoạt vi phạm Foreign Key."""
        content = MarketingContent(
            campaign_id=1,
            channel_id=99999,  # Không tồn tại
            created_by=1,
            title="Content With Ghost Channel",
            body="Should fail on commit",
            cta="None",
            status="DRAFT"
        )
        db_session.add(content)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "foreign key" in str(exc_info.value).lower()
        db_session.rollback()

    def test_direct_db_insert_invalid_creator_id_triggers_fk_violation(self, db_session):
        """Thêm MarketingContent với created_by trỏ đến user không tồn tại kích hoạt vi phạm Foreign Key."""
        content = MarketingContent(
            campaign_id=1,
            channel_id=1,
            created_by=99999,  # Không tồn tại
            title="Content With Ghost Creator",
            body="Should fail on commit",
            cta="None",
            status="DRAFT"
        )
        db_session.add(content)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "foreign key" in str(exc_info.value).lower()
        db_session.rollback()

    def test_direct_db_insert_metric_invalid_campaign_triggers_fk_violation(self, db_session):
        """Thêm CampaignMetric với campaign_id không tồn tại kích hoạt vi phạm Foreign Key."""
        metric = CampaignMetric(
            campaign_id=99999,  # Không tồn tại
            channel_id=1,
            metric_date="2026-10-20",
            views=100,
            clicks=10,
            conversions=1,
            cost=100.0,
            revenue=500.0
        )
        db_session.add(metric)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "foreign key" in str(exc_info.value).lower()
        db_session.rollback()

    def test_api_content_create_nonexistent_foreign_keys_handled_cleanly(self, client):
        """API POST /contents với campaign_id hoặc channel_id không tồn tại trả về HTTP 404/422, KHÔNG BAO GIỜ là 500."""
        headers = get_marketer_headers(client)

        # 1. campaign_id không tồn tại
        r1 = client.post("/api/v1/contents", json={
            "campaign_id": 99999,
            "channel_id": 1,
            "title": "Test Ghost Campaign",
            "body": "Body",
            "cta": "Click"
        }, headers=headers)
        assert r1.status_code in [404, 422]
        assert r1.status_code != 500

        # 2. channel_id không tồn tại
        r2 = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 99999,
            "title": "Test Ghost Channel",
            "body": "Body",
            "cta": "Click"
        }, headers=headers)
        assert r2.status_code in [404, 422]
        assert r2.status_code != 500

    def test_api_metric_create_nonexistent_foreign_keys_handled_cleanly(self, client):
        """API POST metrics với campaign_id hoặc channel_id không tồn tại trả về HTTP 404, KHÔNG BAO GIỜ là 500."""
        headers = get_marketer_headers(client)

        # 1. campaign_id không tồn tại
        r1 = client.post("/api/v1/campaigns/99999/metrics", json={
            "campaign_id": 99999,
            "channel_id": 1,
            "metric_date": "2026-10-20",
            "views": 100,
            "clicks": 10,
            "conversions": 1,
            "cost": 100.0,
            "revenue": 500.0
        }, headers=headers)
        assert r1.status_code == 404
        assert r1.status_code != 500

        # 2. channel_id không tồn tại
        r2 = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 99999,
            "metric_date": "2026-10-20",
            "views": 100,
            "clicks": 10,
            "conversions": 1,
            "cost": 100.0,
            "revenue": 500.0
        }, headers=headers)
        assert r2.status_code == 404
        assert r2.status_code != 500

    def test_cascade_delete_campaign_removes_dependent_records_cleanly(self, client, db_session):
        """Xóa chiến dịch (Manager) kích hoạt xóa cascade toàn bộ contents, metrics, schedules và members liên quan mà không vi phạm ràng buộc."""
        mgr_headers = get_manager_headers(client)

        # Xác nhận chiến dịch 1 đang có contents và metrics
        assert db_session.query(MarketingContent).filter(MarketingContent.campaign_id == 1).count() > 0
        assert db_session.query(CampaignMetric).filter(CampaignMetric.campaign_id == 1).count() > 0

        # Manager thực hiện xóa
        del_resp = client.delete("/api/v1/campaigns/1", headers=mgr_headers)
        assert del_resp.status_code == 204

        # Kiểm tra sạch sẽ, không còn bản ghi mồ côi
        assert db_session.query(Campaign).filter(Campaign.id == 1).first() is None
        assert db_session.query(MarketingContent).filter(MarketingContent.campaign_id == 1).count() == 0
        assert db_session.query(CampaignMetric).filter(CampaignMetric.campaign_id == 1).count() == 0
