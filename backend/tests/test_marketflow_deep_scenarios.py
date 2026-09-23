import base64
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.security import create_access_token, RoleChecker
from app.models.entities import Campaign, MarketingContent
from app.services.ai.ai_service import ai_service


# ==============================================================================
# Helper Functions for Deep Scenarios Authentication
# ==============================================================================

def get_auth_headers_for(client, email: str, password: str) -> dict:
    """Helper xác thực người dùng và nhận Bearer token."""
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Đăng nhập thất bại cho {email}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def get_marketer_headers(client) -> dict:
    """Helper lấy token xác thực quyền MARKETER."""
    return get_auth_headers_for(client, "marketer@ictu.edu.vn", "Marketer@123")


def get_manager_headers(client) -> dict:
    """Helper lấy token xác thực quyền MANAGER."""
    return get_auth_headers_for(client, "manager@ictu.edu.vn", "Manager@123")


def get_custom_role_headers(role: str, user_id: str = "1") -> dict:
    """Helper tạo Bearer header với role tùy ý nhằm kiểm thử RBAC ma trận."""
    token = create_access_token(data={"sub": user_id, "email": f"{role.lower()}@ictu.edu.vn", "role": role})
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# I. TestDeepRBACMatrix (15 Test Cases)
# ==============================================================================

class TestDeepRBACMatrix:
    """Ma trận kiểm thử phân quyền Role-Based Access Control đa tầng."""

    def test_rbac_manager_can_approve_reject_and_delete(self, client):
        """1. Manager có đầy đủ đặc quyền phê duyệt (/approve), từ chối (/reject) và xóa chiến dịch (/delete)."""
        mgr_headers = get_manager_headers(client)
        mkt_headers = get_marketer_headers(client)

        # 1.1 Phê duyệt content_1 đang ở trạng thái IN_REVIEW
        resp_approve = client.post("/api/v1/contents/1/approve", headers=mgr_headers)
        assert resp_approve.status_code == 200
        assert resp_approve.json()["status"] == "APPROVED"

        # 1.2 Tạo bài viết mới để test từ chối (reject)
        resp_create = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Nội dung kiểm thử từ chối",
            "body": "Nội dung bài viết chưa hoàn thiện",
            "cta": "Click"
        }, headers=mkt_headers)
        assert resp_create.status_code == 201
        new_content_id = resp_create.json()["id"]

        resp_submit = client.post(f"/api/v1/contents/{new_content_id}/submit", headers=mkt_headers)
        assert resp_submit.status_code == 200

        resp_reject = client.post(f"/api/v1/contents/{new_content_id}/reject", json={
            "decision": "REJECTED",
            "reason": "Chất lượng chưa đạt chuẩn nhận diện thương hiệu"
        }, headers=mgr_headers)
        assert resp_reject.status_code == 200
        assert resp_reject.json()["status"] == "REJECTED"

        # 1.3 Manager xóa chiến dịch mẫu số 2
        resp_del = client.delete("/api/v1/campaigns/2", headers=mgr_headers)
        assert resp_del.status_code == 204

    def test_rbac_marketer_forbidden_from_approving(self, client):
        """2. Marketer không có quyền phê duyệt nội dung và bị chặn với HTTP 403."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents/1/approve", headers=mkt_headers)
        assert resp.status_code == 403
        assert "trái quyền" in resp.json()["detail"].lower()

    def test_rbac_marketer_forbidden_from_rejecting(self, client):
        """3. Marketer không có quyền từ chối nội dung trong hàng đợi và bị chặn với HTTP 403."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents/1/reject", json={
            "decision": "REJECTED",
            "reason": "Marketer tự từ chối trái phép"
        }, headers=mkt_headers)
        assert resp.status_code == 403
        assert "trái quyền" in resp.json()["detail"].lower()

    def test_rbac_marketer_forbidden_from_deleting_campaign(self, client):
        """4. Marketer không có quyền xóa chiến dịch và bị chặn với HTTP 403."""
        mkt_headers = get_marketer_headers(client)
        resp = client.delete("/api/v1/campaigns/1", headers=mkt_headers)
        assert resp.status_code == 403
        assert "trái quyền" in resp.json()["detail"].lower()

    def test_rbac_viewer_role_blocked_from_mutations(self, client):
        """5. Role VIEWER bị chặn toàn diện với HTTP 403 khi thực hiện các tác vụ thay đổi dữ liệu có bảo vệ RoleChecker."""
        viewer_headers = get_custom_role_headers("VIEWER", user_id="1")

        # Xóa chiến dịch
        assert client.delete("/api/v1/campaigns/1", headers=viewer_headers).status_code == 403
        # Phê duyệt nội dung
        assert client.post("/api/v1/contents/1/approve", headers=viewer_headers).status_code == 403
        # Từ chối nội dung
        assert client.post("/api/v1/contents/1/reject", json={
            "decision": "REJECTED",
            "reason": "Viewer unauthorized rejection"
        }, headers=viewer_headers).status_code == 403

        # Kiểm tra RoleChecker trực tiếp
        manager_checker = RoleChecker(allowed_roles=["MANAGER"])
        token_str = viewer_headers["Authorization"].split(" ")[1]
        with pytest.raises(HTTPException) as exc_info:
            manager_checker(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_str))
        assert exc_info.value.status_code == 403

    def test_rbac_viewer_role_allowed_read_only(self, client):
        """6. Role VIEWER được phép truy cập xem danh sách dữ liệu (Read-Only) hợp lệ với HTTP 200."""
        viewer_headers = get_custom_role_headers("VIEWER", user_id="1")
        assert client.get("/api/v1/campaigns", headers=viewer_headers).status_code == 200
        assert client.get("/api/v1/contents", headers=viewer_headers).status_code == 200
        assert client.get("/api/v1/channels", headers=viewer_headers).status_code == 200
        assert client.get("/api/v1/products", headers=viewer_headers).status_code == 200

    def test_rbac_admin_role_cannot_bypass_manager_check(self, client):
        """7. Role ADMIN giả định không thể vượt qua RoleChecker quản lý theo nguyên tắc đặc quyền tối thiểu (Least Privilege)."""
        admin_headers = get_custom_role_headers("ADMIN", user_id="1")
        resp_approve = client.post("/api/v1/contents/1/approve", headers=admin_headers)
        assert resp_approve.status_code == 403
        assert "trái quyền" in resp_approve.json()["detail"].lower()

        resp_reject = client.post("/api/v1/contents/1/reject", json={
            "decision": "REJECTED",
            "reason": "Admin rejection bypass attempt"
        }, headers=admin_headers)
        assert resp_reject.status_code == 403

        resp_delete = client.delete("/api/v1/campaigns/1", headers=admin_headers)
        assert resp_delete.status_code == 403

    def test_rbac_marketer_can_create_and_submit_content(self, client):
        """8. Marketer được quyền tạo nội dung mới (DRAFT) và gửi vào hàng đợi duyệt (/submit -> IN_REVIEW)."""
        mkt_headers = get_marketer_headers(client)
        resp_create = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bài viết tuyển sinh tháng 10",
            "body": "Nội dung giới thiệu chi tiết",
            "cta": "Đăng ký ngay"
        }, headers=mkt_headers)
        assert resp_create.status_code == 201
        content_id = resp_create.json()["id"]
        assert resp_create.json()["status"] == "DRAFT"

        resp_submit = client.post(f"/api/v1/contents/{content_id}/submit", headers=mkt_headers)
        assert resp_submit.status_code == 200
        assert resp_submit.json()["status"] == "IN_REVIEW"

    def test_rbac_marketer_can_record_metrics(self, client):
        """9. Marketer được quyền ghi nhận chỉ số hiệu quả chiến dịch (Campaign Metrics)."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-05",
            "views": 500,
            "clicks": 50,
            "conversions": 5,
            "cost": 200000.0,
            "revenue": 1000000.0
        }, headers=mkt_headers)
        assert resp.status_code == 201
        assert resp.json()["views"] == 500
        assert resp.json()["clicks"] == 50

    def test_rbac_marketer_can_invoke_ai_draft(self, client):
        """10. Marketer được quyền gọi AI Service để sinh bản nháp nội dung (/ai/draft)."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/ai/draft", json={
            "campaign_id": 1,
            "channel_code": "facebook",
            "selected_idea": "Chiến dịch tuyển sinh lập trình AI chuyên sâu"
        }, headers=mkt_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_type"] == "DRAFT"
        assert len(data["title"]) > 0
        assert len(data["body"]) > 0

    def test_rbac_forged_unknown_role_returns_403(self, client):
        """11. Token mang role tùy tiện không xác định (ví dụ 'HACKER') bị chặn với HTTP 403 Forbidden."""
        hacker_headers = get_custom_role_headers("HACKER", user_id="1")
        assert client.post("/api/v1/contents/1/approve", headers=hacker_headers).status_code == 403
        assert client.delete("/api/v1/campaigns/1", headers=hacker_headers).status_code == 403

    def test_rbac_empty_role_claim_returns_403(self, client):
        """12. Token có trường role rỗng hoặc không chứa trường role bị RoleChecker từ chối 403."""
        token_empty_role = create_access_token(data={"sub": "1", "role": ""})
        headers_empty = {"Authorization": f"Bearer {token_empty_role}"}
        assert client.post("/api/v1/contents/1/approve", headers=headers_empty).status_code == 403

        token_no_role = create_access_token(data={"sub": "1"})
        headers_none = {"Authorization": f"Bearer {token_no_role}"}
        assert client.post("/api/v1/contents/1/approve", headers=headers_none).status_code == 403

    def test_rbac_unauthenticated_ai_endpoints_return_401(self, client):
        """13. Toàn bộ các API dịch vụ AI từ chối truy cập 401 khi thiếu Bearer Token."""
        assert client.post("/api/v1/ai/ideas", json={"campaign_id": 1, "channel_code": "facebook"}).status_code == 401
        assert client.post("/api/v1/ai/draft", json={
            "campaign_id": 1,
            "channel_code": "facebook",
            "selected_idea": "idea"
        }).status_code == 401
        assert client.post("/api/v1/ai/summary", json={"campaign_id": 1}).status_code == 401
        assert client.get("/api/v1/ai/logs").status_code == 401

    def test_rbac_unauthenticated_schedule_endpoints_return_401(self, client):
        """14. Toàn bộ các API quản lý lịch đăng từ chối truy cập 401 khi không đăng nhập."""
        assert client.get("/api/v1/schedules").status_code == 401
        assert client.post("/api/v1/contents/1/schedule", json={
            "content_id": 1,
            "scheduled_at": "2026-11-01 10:00"
        }).status_code == 401

    def test_rbac_unauthenticated_catalog_endpoints_return_401(self, client):
        """15. Toàn bộ các API danh mục sản phẩm và danh mục yêu cầu Bearer Token 401."""
        assert client.get("/api/v1/products").status_code == 401
        assert client.get("/api/v1/product-categories").status_code == 401


# ==============================================================================
# II. TestDeepContentStateMachine (15 Test Cases)
# ==============================================================================

class TestDeepContentStateMachine:
    """Kiểm thử máy trạng thái nội dung (Content State Machine) & Anti-tampering."""

    def test_transition_draft_to_approved_directly_via_put_rejected(self, client):
        """16. Không cho phép chuyển trực tiếp DRAFT sang APPROVED qua PUT /contents/{id} (HTTP 400)."""
        mkt_headers = get_marketer_headers(client)
        resp_c = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bản nháp 1",
            "body": "Nội dung",
            "cta": "CTA"
        }, headers=mkt_headers)
        content_id = resp_c.json()["id"]

        resp_put = client.put(f"/api/v1/contents/{content_id}", json={"status": "APPROVED"}, headers=mkt_headers)
        assert resp_put.status_code == 400
        assert "không thể chuyển trạng thái trực tiếp sang approved" in resp_put.json()["detail"].lower()

    def test_transition_ai_draft_to_approved_directly_via_put_rejected(self, client):
        """17. Không cho phép chuyển trực tiếp AI_DRAFT sang APPROVED qua PUT (HTTP 400)."""
        mkt_headers = get_marketer_headers(client)
        resp_c = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "AI Draft",
            "body": "Nội dung AI",
            "cta": "CTA",
            "status": "AI_DRAFT"
        }, headers=mkt_headers)
        content_id = resp_c.json()["id"]

        resp_put = client.put(f"/api/v1/contents/{content_id}", json={"status": "APPROVED"}, headers=mkt_headers)
        assert resp_put.status_code == 400

    def test_transition_rejected_to_approved_directly_via_put_rejected(self, client):
        """18. Không cho phép chuyển trực tiếp REJECTED sang APPROVED qua PUT (HTTP 400)."""
        mgr_headers = get_manager_headers(client)
        mkt_headers = get_marketer_headers(client)

        # Manager reject content 1
        client.post("/api/v1/contents/1/reject", json={"decision": "REJECTED", "reason": "Lỗi"}, headers=mgr_headers)

        resp_put = client.put("/api/v1/contents/1", json={"status": "APPROVED"}, headers=mkt_headers)
        assert resp_put.status_code == 400

    def test_transition_in_review_to_approved_via_put_rejected(self, client):
        """19. Không cho phép chuyển IN_REVIEW sang APPROVED qua PUT, bắt buộc qua /approve (HTTP 400)."""
        mkt_headers = get_marketer_headers(client)
        resp_put = client.put("/api/v1/contents/1", json={"status": "APPROVED"}, headers=mkt_headers)
        assert resp_put.status_code == 400

    def test_transition_approve_endpoint_on_draft_rejected(self, client):
        """20. Gọi POST /approve trên nội dung đang là DRAFT bị từ chối với HTTP 400."""
        mgr_headers = get_manager_headers(client)
        mkt_headers = get_marketer_headers(client)

        c = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Draft test approve",
            "body": "Body",
            "cta": "CTA"
        }, headers=mkt_headers).json()

        resp = client.post(f"/api/v1/contents/{c['id']}/approve", headers=mgr_headers)
        assert resp.status_code == 400
        assert "chỉ có thể phê duyệt nội dung đang ở trạng thái chờ duyệt" in resp.json()["detail"].lower()

    def test_transition_approve_endpoint_on_ai_draft_rejected(self, client):
        """21. Gọi POST /approve trên nội dung đang là AI_DRAFT bị từ chối với HTTP 400."""
        mgr_headers = get_manager_headers(client)
        mkt_headers = get_marketer_headers(client)

        c = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "AI Draft approve",
            "body": "Body",
            "cta": "CTA",
            "status": "AI_DRAFT"
        }, headers=mkt_headers).json()

        resp = client.post(f"/api/v1/contents/{c['id']}/approve", headers=mgr_headers)
        assert resp.status_code == 400

    def test_transition_approve_endpoint_on_rejected_content_rejected(self, client):
        """22. Gọi POST /approve trên nội dung đang bị REJECTED bị từ chối với HTTP 400."""
        mgr_headers = get_manager_headers(client)

        client.post("/api/v1/contents/1/reject", json={"decision": "REJECTED", "reason": "Lỗi"}, headers=mgr_headers)
        resp = client.post("/api/v1/contents/1/approve", headers=mgr_headers)
        assert resp.status_code == 400

    def test_transition_resubmit_rejected_content_to_in_review(self, client):
        """23. Cho phép gửi duyệt lại (/submit) nội dung đã bị REJECTED, chuyển trạng thái về IN_REVIEW."""
        mgr_headers = get_manager_headers(client)
        mkt_headers = get_marketer_headers(client)

        # Từ chối nội dung
        client.post("/api/v1/contents/1/reject", json={"decision": "REJECTED", "reason": "Lỗi"}, headers=mgr_headers)

        # Marketer gửi duyệt lại
        resp_submit = client.post("/api/v1/contents/1/submit", headers=mkt_headers)
        assert resp_submit.status_code == 200
        assert resp_submit.json()["status"] == "IN_REVIEW"

    def test_transition_submit_already_in_review_content_rejected(self, client):
        """24. Không cho phép gửi duyệt (/submit) nội dung đang ở trạng thái IN_REVIEW (HTTP 400)."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/contents/1/submit", headers=mkt_headers)
        assert resp.status_code == 400
        assert "không thể gửi duyệt" in resp.json()["detail"].lower()

    def test_transition_submit_already_approved_content_rejected(self, client):
        """25. Không cho phép gửi duyệt (/submit) nội dung đã được APPROVED (HTTP 400)."""
        mgr_headers = get_manager_headers(client)
        mkt_headers = get_marketer_headers(client)

        client.post("/api/v1/contents/1/approve", headers=mgr_headers)
        resp = client.post("/api/v1/contents/1/submit", headers=mkt_headers)
        assert resp.status_code == 400
        assert "không thể gửi duyệt" in resp.json()["detail"].lower()

    def test_anti_tamper_edit_title_reverts_approved_to_ai_draft(self, client):
        """26. Chỉnh sửa tiêu đề của nội dung đã APPROVED tự động hạ cấp về AI_DRAFT và tăng version_no."""
        mgr_headers = get_manager_headers(client)
        mkt_headers = get_marketer_headers(client)

        client.post("/api/v1/contents/1/approve", headers=mgr_headers)
        resp_edit = client.put("/api/v1/contents/1", json={"title": "Tiêu đề mới bị chỉnh sửa"}, headers=mkt_headers)
        assert resp_edit.status_code == 200
        data = resp_edit.json()
        assert data["status"] == "AI_DRAFT"
        assert data["version_no"] == 2
        assert data["title"] == "Tiêu đề mới bị chỉnh sửa"

    def test_anti_tamper_edit_body_reverts_approved_to_ai_draft(self, client):
        """27. Chỉnh sửa nội dung (body) của bài viết đã APPROVED tự động hạ về AI_DRAFT và tăng version_no."""
        mgr_headers = get_manager_headers(client)
        mkt_headers = get_marketer_headers(client)

        client.post("/api/v1/contents/1/approve", headers=mgr_headers)
        resp_edit = client.put("/api/v1/contents/1", json={"body": "Nội dung bài viết mới"}, headers=mkt_headers)
        assert resp_edit.status_code == 200
        data = resp_edit.json()
        assert data["status"] == "AI_DRAFT"
        assert data["version_no"] == 2

    def test_anti_tamper_edit_cta_reverts_approved_to_ai_draft(self, client):
        """28. Chỉnh sửa CTA của bài viết đã APPROVED tự động hạ về AI_DRAFT và tăng version_no."""
        mgr_headers = get_manager_headers(client)
        mkt_headers = get_marketer_headers(client)

        client.post("/api/v1/contents/1/approve", headers=mgr_headers)
        resp_edit = client.put("/api/v1/contents/1", json={"cta": "CTA hoàn toàn mới"}, headers=mkt_headers)
        assert resp_edit.status_code == 200
        data = resp_edit.json()
        assert data["status"] == "AI_DRAFT"
        assert data["version_no"] == 2

    def test_anti_tamper_idempotent_put_preserves_approved_status(self, client):
        """29. Gửi PUT với nội dung không thay đổi (idempotent) bảo toàn trạng thái APPROVED."""
        mgr_headers = get_manager_headers(client)
        mkt_headers = get_marketer_headers(client)

        client.post("/api/v1/contents/1/approve", headers=mgr_headers)
        current = client.get("/api/v1/contents/1", headers=mkt_headers).json()

        resp_put = client.put("/api/v1/contents/1", json={
            "title": current["title"],
            "body": current["body"],
            "cta": current["cta"]
        }, headers=mkt_headers)
        assert resp_put.status_code == 200
        assert resp_put.json()["status"] == "APPROVED"

    def test_scheduling_non_approved_content_rejected_across_states(self, client):
        """30. Lập lịch đăng cho bài viết chưa APPROVED (ở trạng thái IN_REVIEW, DRAFT, REJECTED) bị từ chối 400."""
        mgr_headers = get_manager_headers(client)
        mkt_headers = get_marketer_headers(client)

        # IN_REVIEW
        r1 = client.post("/api/v1/contents/1/schedule", json={
            "content_id": 1,
            "scheduled_at": "2026-11-20 10:00",
            "timezone": "Asia/Ho_Chi_Minh"
        }, headers=mkt_headers)
        assert r1.status_code == 400
        assert "chỉ có thể lập lịch" in r1.json()["detail"].lower()

        # DRAFT
        draft_c = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Bản nháp",
            "body": "Nội dung",
            "cta": "CTA"
        }, headers=mkt_headers).json()
        r2 = client.post(f"/api/v1/contents/{draft_c['id']}/schedule", json={
            "content_id": draft_c["id"],
            "scheduled_at": "2026-11-20 10:00"
        }, headers=mkt_headers)
        assert r2.status_code == 400

        # REJECTED
        client.post("/api/v1/contents/1/reject", json={"decision": "REJECTED", "reason": "Từ chối"}, headers=mgr_headers)
        r3 = client.post("/api/v1/contents/1/schedule", json={
            "content_id": 1,
            "scheduled_at": "2026-11-20 10:00"
        }, headers=mkt_headers)
        assert r3.status_code == 400


# ==============================================================================
# III. TestDeepDateRangeBoundaries (12 Test Cases)
# ==============================================================================

class TestDeepDateRangeBoundaries:
    """Kiểm thử giá trị biên ngày tháng, chiến dịch flash sale và năm nhuận."""

    def test_date_boundary_same_day_flash_campaign_succeeds(self, client):
        """31. Chiến dịch Flash Sale chạy trong cùng một ngày (start_date == end_date) tạo thành công (HTTP 201)."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Chiến dịch Flash Sale 11.11",
            "objective": "Bùng nổ doanh số trong ngày",
            "audience": "Mọi đối tượng",
            "start_date": "2026-11-11",
            "end_date": "2026-11-11",
            "budget": 5000000.0
        }, headers=mkt_headers)
        assert resp.status_code == 201
        assert resp.json()["start_date"] == "2026-11-11"
        assert resp.json()["end_date"] == "2026-11-11"

    def test_date_boundary_start_greater_than_end_by_one_day_rejected(self, client):
        """32. Ngày bắt đầu lớn hơn ngày kết thúc đúng 1 ngày bị từ chối với HTTP 422."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Chiến dịch lỗi ngày 1",
            "objective": "Test",
            "audience": "All",
            "start_date": "2026-06-02",
            "end_date": "2026-06-01",
            "budget": 1000.0
        }, headers=mkt_headers)
        assert resp.status_code == 422
        assert resp.status_code != 500

    def test_date_boundary_start_greater_than_end_by_one_year_rejected(self, client):
        """33. Ngày bắt đầu lớn hơn ngày kết thúc 1 năm bị từ chối với HTTP 422."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Chiến dịch lỗi ngày 2",
            "objective": "Test",
            "audience": "All",
            "start_date": "2027-01-01",
            "end_date": "2026-01-01",
            "budget": 1000.0
        }, headers=mkt_headers)
        assert resp.status_code == 422

    def test_date_leap_year_2024_feb_29_valid(self, client):
        """34. Năm nhuận 2024 có ngày 29/02 hợp lệ và được chấp nhận thành công (HTTP 201)."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Chiến dịch Năm Nhuận 2024",
            "objective": "Tuyển sinh sớm",
            "audience": "All",
            "start_date": "2024-02-29",
            "end_date": "2024-03-01",
            "budget": 2000000.0
        }, headers=mkt_headers)
        assert resp.status_code == 201

    def test_date_leap_year_2028_feb_29_valid(self, client):
        """35. Năm nhuận tương lai 2028 có ngày 29/02 hợp lệ và được chấp nhận (HTTP 201)."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Chiến dịch Năm Nhuận 2028",
            "objective": "Dự án dài hạn",
            "audience": "All",
            "start_date": "2028-02-29",
            "end_date": "2028-03-05",
            "budget": 3000000.0
        }, headers=mkt_headers)
        assert resp.status_code == 201

    def test_date_century_leap_year_2000_feb_29_valid(self, client):
        """36. Năm thế kỷ nhuận 2000 (chia hết cho 400) có ngày 29/02 hợp lệ (HTTP 201)."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Chiến dịch Năm Thế Kỷ 2000",
            "objective": "Lịch sử dữ liệu",
            "audience": "All",
            "start_date": "2000-02-29",
            "end_date": "2000-03-01",
            "budget": 1000000.0
        }, headers=mkt_headers)
        assert resp.status_code == 201

    def test_date_non_leap_year_2025_feb_29_rejected(self, client):
        """37. Năm không nhuận 2025 không có ngày 29/02 và bị Pydantic bắt lỗi 422."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Lỗi năm không nhuận 2025",
            "objective": "Test",
            "audience": "All",
            "start_date": "2025-02-29",
            "end_date": "2025-03-01",
            "budget": 1000.0
        }, headers=mkt_headers)
        assert resp.status_code == 422
        assert resp.status_code != 500

    def test_date_non_leap_year_2026_feb_29_rejected(self, client):
        """38. Năm hiện tại 2026 không phải năm nhuận, ngày 2026-02-29 bị từ chối 422."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Lỗi năm không nhuận 2026",
            "objective": "Test",
            "audience": "All",
            "start_date": "2026-02-29",
            "end_date": "2026-03-01",
            "budget": 1000.0
        }, headers=mkt_headers)
        assert resp.status_code == 422

    def test_date_century_non_leap_year_2100_feb_29_rejected(self, client):
        """39. Năm thế kỷ 2100 chia hết cho 100 nhưng không chia hết cho 400, 2100-02-29 không tồn tại (HTTP 422)."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Lỗi thế kỷ không nhuận 2100",
            "objective": "Test",
            "audience": "All",
            "start_date": "2100-02-29",
            "end_date": "2100-03-01",
            "budget": 1000.0
        }, headers=mkt_headers)
        assert resp.status_code == 422

    def test_date_month_boundary_april_31_rejected(self, client):
        """40. Tháng 4 chỉ có 30 ngày, ngày 2026-04-31 bị từ chối với HTTP 422."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Lỗi tháng 4 ngày 31",
            "objective": "Test",
            "audience": "All",
            "start_date": "2026-04-31",
            "end_date": "2026-05-01",
            "budget": 1000.0
        }, headers=mkt_headers)
        assert resp.status_code == 422

    def test_date_month_boundary_june_31_and_nov_31_rejected(self, client):
        """41. Tháng 6 và tháng 11 chỉ có 30 ngày, các ngày 31 tương ứng bị từ chối với HTTP 422."""
        mkt_headers = get_marketer_headers(client)

        r_june = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Lỗi tháng 6 ngày 31",
            "objective": "Test",
            "audience": "All",
            "start_date": "2026-06-31",
            "end_date": "2026-07-01",
            "budget": 1000.0
        }, headers=mkt_headers)
        assert r_june.status_code == 422

        r_nov = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Lỗi tháng 11 ngày 31",
            "objective": "Test",
            "audience": "All",
            "start_date": "2026-11-31",
            "end_date": "2026-12-01",
            "budget": 1000.0
        }, headers=mkt_headers)
        assert r_nov.status_code == 422

    def test_schedule_timezone_offsets_supported(self, client):
        """42. Hỗ trợ các múi giờ tiêu chuẩn (UTC, Asia/Tokyo, America/New_York) khi lập lịch đăng bài viết."""
        mgr_headers = get_manager_headers(client)
        mkt_headers = get_marketer_headers(client)

        # Duyệt content 1 trước khi lập lịch
        client.post("/api/v1/contents/1/approve", headers=mgr_headers)

        timezones_to_test = ["UTC", "Asia/Tokyo", "America/New_York"]
        for tz in timezones_to_test:
            resp = client.post("/api/v1/contents/1/schedule", json={
                "content_id": 1,
                "scheduled_at": "2026-12-01 10:00",
                "timezone": tz
            }, headers=mkt_headers)
            assert resp.status_code == 201
            assert resp.json()["timezone"] == tz


# ==============================================================================
# IV. TestDeepMetricsAndFinancialMath (10 Test Cases)
# ==============================================================================

class TestDeepMetricsAndFinancialMath:
    """Kiểm thử tính toàn vẹn chỉ số chiến dịch, khóa phức hợp và toán tài chính."""

    def test_metric_duplicate_compound_key_returns_409_conflict(self, client):
        """43. Trùng lặp khóa phức hợp (campaign_id, channel_id, metric_date) trả về HTTP 409 Conflict."""
        mkt_headers = get_marketer_headers(client)
        payload = {
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-20",
            "views": 100,
            "clicks": 10,
            "conversions": 1,
            "cost": 100000.0,
            "revenue": 500000.0
        }
        r1 = client.post("/api/v1/campaigns/1/metrics", json=payload, headers=mkt_headers)
        assert r1.status_code == 201

        r2 = client.post("/api/v1/campaigns/1/metrics", json=payload, headers=mkt_headers)
        assert r2.status_code == 409
        assert "đã tồn tại" in r2.json()["detail"].lower()

    def test_metric_same_date_different_channel_succeeds(self, client):
        """44. Cùng một ngày nhưng ghi nhận chỉ số cho 2 kênh khác nhau tạo thành công (HTTP 201)."""
        mkt_headers = get_marketer_headers(client)
        r1 = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-22",
            "views": 100,
            "clicks": 10,
            "conversions": 1,
            "cost": 50000.0,
            "revenue": 200000.0
        }, headers=mkt_headers)
        assert r1.status_code == 201

        r2 = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 2,
            "metric_date": "2026-11-22",
            "views": 200,
            "clicks": 20,
            "conversions": 2,
            "cost": 80000.0,
            "revenue": 400000.0
        }, headers=mkt_headers)
        assert r2.status_code == 201

    def test_metric_same_channel_different_date_succeeds(self, client):
        """45. Cùng một kênh nhưng trên 2 ngày khác nhau tạo thành công (HTTP 201)."""
        mkt_headers = get_marketer_headers(client)
        r1 = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-23",
            "views": 300,
            "clicks": 30,
            "conversions": 3,
            "cost": 100000.0,
            "revenue": 300000.0
        }, headers=mkt_headers)
        assert r1.status_code == 201

        r2 = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-24",
            "views": 400,
            "clicks": 40,
            "conversions": 4,
            "cost": 120000.0,
            "revenue": 500000.0
        }, headers=mkt_headers)
        assert r2.status_code == 201

    def test_metric_negative_views_rejected(self, client):
        """46. Lượt xem views âm (views = -1) bị Pydantic bắt lỗi 422."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-25",
            "views": -1,
            "clicks": 0,
            "conversions": 0,
            "cost": 0.0,
            "revenue": 0.0
        }, headers=mkt_headers)
        assert resp.status_code == 422

    def test_metric_negative_clicks_rejected(self, client):
        """47. Lượt clicks âm bị từ chối với HTTP 422."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-25",
            "views": 10,
            "clicks": -1,
            "conversions": 0,
            "cost": 0.0,
            "revenue": 0.0
        }, headers=mkt_headers)
        assert resp.status_code == 422

    def test_metric_negative_conversions_rejected(self, client):
        """48. Lượt chuyển đổi conversions âm bị từ chối với HTTP 422."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-25",
            "views": 10,
            "clicks": 1,
            "conversions": -1,
            "cost": 0.0,
            "revenue": 0.0
        }, headers=mkt_headers)
        assert resp.status_code == 422

    def test_metric_negative_cost_and_revenue_rejected(self, client):
        """49. Chi phí cost hoặc doanh thu revenue âm bị từ chối với HTTP 422."""
        mkt_headers = get_marketer_headers(client)
        r_cost = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-25",
            "views": 10,
            "clicks": 1,
            "conversions": 1,
            "cost": -50.0,
            "revenue": 100.0
        }, headers=mkt_headers)
        assert r_cost.status_code == 422

        r_rev = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-25",
            "views": 10,
            "clicks": 1,
            "conversions": 1,
            "cost": 50.0,
            "revenue": -10.0
        }, headers=mkt_headers)
        assert r_rev.status_code == 422

    def test_metric_clicks_greater_than_views_rejected(self, client):
        """50. Lượt click lớn hơn lượt xem (clicks > views) vi phạm logic nghiệp vụ và bị từ chối 422."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-25",
            "views": 100,
            "clicks": 101,
            "conversions": 1,
            "cost": 1000.0,
            "revenue": 5000.0
        }, headers=mkt_headers)
        assert resp.status_code == 422
        assert "không được lớn hơn lượt view" in resp.text.lower()

    def test_metric_clicks_equal_to_views_succeeds(self, client):
        """51. Lượt click bằng đúng lượt xem (100% CTR) là ngưỡng biên hợp lệ (HTTP 201)."""
        mkt_headers = get_marketer_headers(client)
        resp = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-26",
            "views": 50,
            "clicks": 50,
            "conversions": 5,
            "cost": 50000.0,
            "revenue": 200000.0
        }, headers=mkt_headers)
        assert resp.status_code == 201

    def test_kpi_zero_division_immunity_and_exact_math(self, client, db_session):
        """52. Bảo đảm miễn nhiễm lỗi chia cho 0 khi chưa có số liệu và tính toán công thức KPI chuẩn xác tuyệt đối."""
        mkt_headers = get_marketer_headers(client)

        # 52.1 Kiểm tra chiến dịch 2 ban đầu chưa có metric nào
        kpi_zero = client.get("/api/v1/campaigns/2/kpi", headers=mkt_headers).json()
        assert kpi_zero["total_views"] == 0
        assert kpi_zero["total_clicks"] == 0
        assert kpi_zero["ctr_percent"] == 0.0
        assert kpi_zero["cpc_avg"] == 0.0
        assert kpi_zero["cvr_percent"] == 0.0
        assert kpi_zero["roi_percent"] == 0.0

        # 52.2 Nạp metric chính xác vào chiến dịch 2
        # views = 1000, clicks = 100, conversions = 10, cost = 500.0, revenue = 1500.0
        client.post("/api/v1/campaigns/2/metrics", json={
            "campaign_id": 2,
            "channel_id": 1,
            "metric_date": "2026-10-15",
            "views": 1000,
            "clicks": 100,
            "conversions": 10,
            "cost": 500.0,
            "revenue": 1500.0
        }, headers=mkt_headers)

        kpi_calc = client.get("/api/v1/campaigns/2/kpi", headers=mkt_headers).json()
        assert kpi_calc["total_views"] == 1000
        assert kpi_calc["total_clicks"] == 100
        assert kpi_calc["total_conversions"] == 10
        assert kpi_calc["total_cost"] == 500.0
        assert kpi_calc["total_revenue"] == 1500.0
        # CTR = (100 / 1000) * 100 = 10.0%
        assert kpi_calc["ctr_percent"] == 10.0
        # CPC = 500.0 / 100 = 5.0
        assert kpi_calc["cpc_avg"] == 5.0
        # CVR = (10 / 100) * 100 = 10.0%
        assert kpi_calc["cvr_percent"] == 10.0
        # ROI = ((1500 - 500) / 500) * 100 = 200.0%
        assert kpi_calc["roi_percent"] == 200.0


# ==============================================================================
# V. TestDeepAISmartFallbackResilience (10 Test Cases)
# ==============================================================================

class TestDeepAISmartFallbackResilience:
    """Kiểm thử khả năng chịu lỗi và tự phục hồi Smart Fallback của AI Service."""

    def test_ai_ideas_provider_timeout_recovers_via_fallback(self, client):
        """53. Khi nhà cung cấp AI bị timeout trên /ideas, hệ thống tự kích hoạt Fallback sinh ý tưởng an toàn (HTTP 200)."""
        mkt_headers = get_marketer_headers(client)
        with patch.object(ai_service, "_call_provider_with_retry", side_effect=TimeoutError("AI Gateway Timeout")):
            ai_service.api_key = "mock_valid_key"
            ai_service.fallback_enabled = True
            try:
                resp = client.post("/api/v1/ai/ideas", json={
                    "campaign_id": 1,
                    "channel_code": "facebook"
                }, headers=mkt_headers)
                assert resp.status_code == 200
                data = resp.json()
                assert data["task_type"] == "IDEA"
                assert len(data["ideas"]) >= 1
                assert any("phòng" in w.lower() or "fallback" in w.lower() or "sự cố" in w.lower() for w in data.get("warnings", []))
            finally:
                ai_service.api_key = ""

    def test_ai_draft_provider_timeout_recovers_via_fallback(self, client):
        """54. Khi AI timeout trên /draft, Smart Fallback tự động trả về bài viết chuẩn doanh nghiệp (HTTP 200)."""
        mkt_headers = get_marketer_headers(client)
        with patch.object(ai_service, "_call_provider_with_retry", side_effect=TimeoutError("AI Gateway Timeout")):
            ai_service.api_key = "mock_valid_key"
            ai_service.fallback_enabled = True
            try:
                resp = client.post("/api/v1/ai/draft", json={
                    "campaign_id": 1,
                    "channel_code": "facebook",
                    "selected_idea": "Tuyển sinh ngành AI"
                }, headers=mkt_headers)
                assert resp.status_code == 200
                data = resp.json()
                assert data["task_type"] == "DRAFT"
                assert "title" in data and len(data["title"]) > 0
                assert "body" in data and len(data["body"]) > 0
                assert "cta" in data and len(data["cta"]) > 0
            finally:
                ai_service.api_key = ""

    def test_ai_summary_provider_timeout_recovers_via_fallback(self, client):
        """55. Khi AI timeout trên /summary, hệ thống fallback thành công báo cáo đánh giá chiến dịch (HTTP 200)."""
        mkt_headers = get_marketer_headers(client)
        with patch.object(ai_service, "_call_provider_with_retry", side_effect=TimeoutError("AI Gateway Timeout")):
            ai_service.api_key = "mock_valid_key"
            ai_service.fallback_enabled = True
            try:
                resp = client.post("/api/v1/ai/summary", json={"campaign_id": 1}, headers=mkt_headers)
                assert resp.status_code == 200
                data = resp.json()
                assert data["task_type"] == "SUMMARY"
                assert "executive_summary" in data
                assert isinstance(data["strengths"], list)
            finally:
                ai_service.api_key = ""

    def test_ai_ideas_provider_500_server_error_recovers_via_fallback(self, client):
        """56. Khi nhà cung cấp AI trả về lỗi HTTP 500, hệ thống tự động bẫy lỗi và kích hoạt Fallback sinh ý tưởng."""
        mkt_headers = get_marketer_headers(client)
        with patch.object(ai_service, "_call_provider_with_retry", side_effect=RuntimeError("500 Internal Server Error from OpenAI API")):
            ai_service.api_key = "mock_valid_key"
            ai_service.fallback_enabled = True
            try:
                resp = client.post("/api/v1/ai/ideas", json={
                    "campaign_id": 1,
                    "channel_code": "facebook"
                }, headers=mkt_headers)
                assert resp.status_code == 200
                assert len(resp.json()["ideas"]) >= 1
            finally:
                ai_service.api_key = ""

    def test_ai_draft_provider_html_error_page_recovers_via_fallback(self, client):
        """57. Khi nhà cung cấp trả về trang lỗi HTML (Cloudflare 502 Bad Gateway), Smart Fallback sinh dữ liệu an toàn."""
        mkt_headers = get_marketer_headers(client)
        mock_html = "<html><head><title>502 Bad Gateway</title></head><body>Cloudflare Error</body></html>"
        with patch.object(ai_service, "_call_provider_with_retry", return_value=mock_html):
            ai_service.api_key = "mock_valid_key"
            ai_service.fallback_enabled = True
            try:
                resp = client.post("/api/v1/ai/draft", json={
                    "campaign_id": 1,
                    "channel_code": "facebook",
                    "selected_idea": "Sáng tạo nội dung với AI"
                }, headers=mkt_headers)
                assert resp.status_code == 200
                assert "title" in resp.json()
                assert "body" in resp.json()
            finally:
                ai_service.api_key = ""

    def test_ai_summary_provider_empty_string_recovers_via_fallback(self, client):
        """58. Khi phản hồi AI là chuỗi rỗng (''), Smart Fallback tự phục hồi dữ liệu báo cáo (HTTP 200)."""
        mkt_headers = get_marketer_headers(client)
        with patch.object(ai_service, "_call_provider_with_retry", return_value=""):
            ai_service.api_key = "mock_valid_key"
            ai_service.fallback_enabled = True
            try:
                resp = client.post("/api/v1/ai/summary", json={"campaign_id": 1}, headers=mkt_headers)
                assert resp.status_code == 200
                assert "executive_summary" in resp.json()
            finally:
                ai_service.api_key = ""

    def test_ai_ideas_missing_ideas_key_recovers_via_fallback(self, client):
        """59. Khi kết quả AI thiếu trường khóa 'ideas', bẫy Schema Error và kích hoạt Fallback an toàn."""
        mkt_headers = get_marketer_headers(client)
        broken_json = json.dumps({"status": "ok", "message": "everything ok but ideas key is missing"})
        with patch.object(ai_service, "_call_provider_with_retry", return_value=broken_json):
            ai_service.api_key = "mock_valid_key"
            ai_service.fallback_enabled = True
            try:
                resp = client.post("/api/v1/ai/ideas", json={
                    "campaign_id": 1,
                    "channel_code": "facebook"
                }, headers=mkt_headers)
                assert resp.status_code == 200
                assert len(resp.json()["ideas"]) >= 1
            finally:
                ai_service.api_key = ""

    def test_ai_draft_missing_body_cta_recovers_via_fallback(self, client):
        """60. Khi kết quả bài viết thiếu body và cta, Fallback tự phục hồi bài viết hoàn chỉnh."""
        mkt_headers = get_marketer_headers(client)
        incomplete_draft = json.dumps({"title": "Chỉ có tiêu đề"})
        with patch.object(ai_service, "_call_provider_with_retry", return_value=incomplete_draft):
            ai_service.api_key = "mock_valid_key"
            ai_service.fallback_enabled = True
            try:
                resp = client.post("/api/v1/ai/draft", json={
                    "campaign_id": 1,
                    "channel_code": "facebook",
                    "selected_idea": "Ý tưởng mới"
                }, headers=mkt_headers)
                assert resp.status_code == 200
                assert "body" in resp.json() and "cta" in resp.json()
            finally:
                ai_service.api_key = ""

    def test_ai_summary_missing_executive_summary_recovers(self, client):
        """61. Khi kết quả tóm tắt thiếu executive_summary, Smart Fallback trả về cấu trúc summary đầy đủ."""
        mkt_headers = get_marketer_headers(client)
        incomplete_summary = json.dumps({"strengths": ["Điểm mạnh đơn lẻ"]})
        with patch.object(ai_service, "_call_provider_with_retry", return_value=incomplete_summary):
            ai_service.api_key = "mock_valid_key"
            ai_service.fallback_enabled = True
            try:
                resp = client.post("/api/v1/ai/summary", json={"campaign_id": 1}, headers=mkt_headers)
                assert resp.status_code == 200
                assert "executive_summary" in resp.json()
            finally:
                ai_service.api_key = ""

    def test_ai_service_clean_502_when_fallback_disabled_on_error(self, client):
        """62. Khi tắt Fallback (fallback_enabled=False), lỗi mạng trả về HTTP 502 Bad Gateway (không crash 500)."""
        mkt_headers = get_marketer_headers(client)
        with patch.object(ai_service, "_call_provider_with_retry", side_effect=RuntimeError("AI Provider unreachable")):
            ai_service.api_key = "mock_valid_key"
            ai_service.fallback_enabled = False
            try:
                r1 = client.post("/api/v1/ai/ideas", json={"campaign_id": 1, "channel_code": "facebook"}, headers=mkt_headers)
                assert r1.status_code == 502
                assert r1.status_code != 500

                r2 = client.post("/api/v1/ai/draft", json={
                    "campaign_id": 1,
                    "channel_code": "facebook",
                    "selected_idea": "idea"
                }, headers=mkt_headers)
                assert r2.status_code == 502
                assert r2.status_code != 500

                r3 = client.post("/api/v1/ai/summary", json={"campaign_id": 1}, headers=mkt_headers)
                assert r3.status_code == 502
                assert r3.status_code != 500
            finally:
                ai_service.fallback_enabled = True
                ai_service.api_key = ""


# ==============================================================================
# VI. TestDeepJWTSecurityAndTampering (10 Test Cases)
# ==============================================================================

class TestDeepJWTSecurityAndTampering:
    """Kiểm thử độ an toàn, tính chống giả mạo và giải mã JWT token."""

    def test_jwt_expired_token_returns_401(self, client):
        """63. Token JWT đã hết hạn trả về HTTP 401 Unauthorized."""
        expired_token = create_access_token(
            data={"sub": "1", "role": "MANAGER"},
            expires_delta=timedelta(seconds=-3600)
        )
        resp = client.get("/api/v1/campaigns", headers={"Authorization": f"Bearer {expired_token}"})
        assert resp.status_code == 401
        assert "hết hạn" in resp.json()["detail"].lower() or "không hợp lệ" in resp.json()["detail"].lower()

    def test_jwt_invalid_signature_wrong_key_returns_401(self, client):
        """64. Token được ký bởi Secret Key khác trả về HTTP 401 do chữ ký không hợp lệ."""
        forged_token = jwt.encode(
            {"sub": "1", "role": "MANAGER", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "ANOTHER_FORGED_SECRET_KEY_NOT_MATCHING_SERVER_CONFIG",
            algorithm="HS256"
        )
        resp = client.get("/api/v1/campaigns", headers={"Authorization": f"Bearer {forged_token}"})
        assert resp.status_code == 401

    def test_jwt_algorithm_none_attack_returns_401(self, client):
        """65. Tấn công algorithm none (alg='none') bị thư viện PyJWT chặn đứng với HTTP 401."""
        payload_bytes = json.dumps({"sub": "1", "role": "MANAGER", "exp": 253402300799}).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
        none_token = f"eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.{payload_b64}."
        resp = client.get("/api/v1/campaigns", headers={"Authorization": f"Bearer {none_token}"})
        assert resp.status_code == 401

    def test_jwt_tampered_payload_returns_401(self, client):
        """66. Token có payload bị sửa đổi sau khi ký bị phát hiện và từ chối 401."""
        valid_token = create_access_token({"sub": "2", "role": "MARKETER"})
        header, _, signature = valid_token.split(".")
        tampered_payload = base64.urlsafe_b64encode(json.dumps({"sub": "1", "role": "MANAGER"}).encode("utf-8")).decode("utf-8").rstrip("=")
        tampered_token = f"{header}.{tampered_payload}.{signature}"

        resp = client.get("/api/v1/campaigns", headers={"Authorization": f"Bearer {tampered_token}"})
        assert resp.status_code == 401

    def test_jwt_missing_bearer_prefix_returns_401(self, client):
        """67. Header Authorization thiếu tiền tố 'Bearer ' trả về HTTP 401 Unauthorized."""
        token = create_access_token({"sub": "1", "role": "MANAGER"})
        resp = client.get("/api/v1/campaigns", headers={"Authorization": token})
        assert resp.status_code == 401

    def test_jwt_empty_bearer_token_string_returns_401(self, client):
        """68. Header Authorization chỉ có chuỗi 'Bearer ' rỗng trả về HTTP 401."""
        resp = client.get("/api/v1/campaigns", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401

    def test_jwt_empty_authorization_header_returns_401(self, client):
        """69. Header Authorization rỗng ('') trả về HTTP 401 Unauthorized."""
        resp = client.get("/api/v1/campaigns", headers={"Authorization": ""})
        assert resp.status_code == 401

    def test_jwt_non_existent_user_id_returns_401(self, client):
        """70. Token mang định danh sub trỏ đến user không tồn tại trả về HTTP 401."""
        token = create_access_token({"sub": "999999", "role": "MANAGER"})
        resp = client.get("/api/v1/campaigns", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "không tồn tại" in resp.json()["detail"].lower()

    def test_jwt_negative_user_id_returns_401(self, client):
        """71. Token mang định danh sub là số âm (sub='-5') trả về HTTP 401."""
        token = create_access_token({"sub": "-5", "role": "MANAGER"})
        resp = client.get("/api/v1/campaigns", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "không tồn tại" in resp.json()["detail"].lower()

    def test_jwt_alphanumeric_sub_returns_401(self, client):
        """72. Token mang sub là chuỗi chữ không ép kiểu int được trả về HTTP 401."""
        token = create_access_token({"sub": "administrator_admin", "role": "MANAGER"})
        resp = client.get("/api/v1/campaigns", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "không hợp lệ" in resp.json()["detail"].lower()


# ==============================================================================
# VII. TestDeepInputFuzzingAndInjectionResistance (10 Test Cases)
# ==============================================================================

class TestDeepInputFuzzingAndInjectionResistance:
    """Kiểm thử khả năng chống SQL Injection, XSS và Fuzzing đầu vào."""

    def test_sqli_campaign_search_tautology_neutralized(self, client):
        """73. Tấn công SQLi tautology (?search=' OR '1'='1) được vô hiệu hóa, tìm kiếm theo chuỗi ký tự thuần túy."""
        mkt_headers = get_marketer_headers(client)
        resp = client.get("/api/v1/campaigns?search=%27%20OR%20%271%27=%271", headers=mkt_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_sqli_campaign_search_drop_table_neutralized(self, client, db_session):
        """74. Tấn công SQLi phá hủy bảng (?search='; DROP TABLE campaigns; --) không làm ảnh hưởng CSDL."""
        mkt_headers = get_marketer_headers(client)
        resp = client.get("/api/v1/campaigns?search=%27;%20DROP%20TABLE%20campaigns;%20--", headers=mkt_headers)
        assert resp.status_code == 200
        assert db_session.query(Campaign).count() >= 2

    def test_sqli_campaign_status_union_select_neutralized(self, client):
        """75. Tấn công UNION SELECT qua query parameter status không gây rò rỉ dữ liệu tài khoản."""
        mkt_headers = get_marketer_headers(client)
        resp = client.get("/api/v1/campaigns?status=%27%20UNION%20SELECT%20*%20FROM%20users%20--", headers=mkt_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_sqli_content_status_quote_injection_neutralized(self, client):
        """76. Tấn công nháy đơn trên status của /contents được xử lý an toàn dưới dạng chuỗi thuần túy."""
        mkt_headers = get_marketer_headers(client)
        resp = client.get("/api/v1/contents?status=%27%20OR%20%271%27=%271", headers=mkt_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_xss_campaign_name_stored_and_rendered_safely(self, client):
        """77. Payload XSS trong tên chiến dịch được lưu trữ và phản hồi an toàn dưới dạng JSON (không thực thi HTML)."""
        mkt_headers = get_marketer_headers(client)
        xss_payload = "<script>alert('XSS Attack!')</script>"
        resp_post = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": xss_payload,
            "objective": "Kiểm tra XSS",
            "audience": "Mọi đối tượng",
            "start_date": "2026-11-01",
            "end_date": "2026-11-30",
            "budget": 1000.0
        }, headers=mkt_headers)
        assert resp_post.status_code == 201
        camp_id = resp_post.json()["id"]

        resp_get = client.get(f"/api/v1/campaigns/{camp_id}", headers=mkt_headers)
        assert resp_get.status_code == 200
        assert resp_get.json()["name"] == xss_payload

    def test_xss_content_title_and_body_rendered_safely(self, client):
        """78. Payload XSS trong tiêu đề, nội dung và CTA được lưu trữ nguyên vẹn dưới dạng văn bản thuần túy."""
        mkt_headers = get_marketer_headers(client)
        xss_title = "<svg onload=alert('XSS')>"
        xss_body = "<img src=x onerror=alert(document.cookie)>"
        xss_cta = "<iframe src='javascript:alert(1)'></iframe>"

        resp_post = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": xss_title,
            "body": xss_body,
            "cta": xss_cta
        }, headers=mkt_headers)
        assert resp_post.status_code == 201
        content_id = resp_post.json()["id"]

        resp_get = client.get(f"/api/v1/contents/{content_id}", headers=mkt_headers)
        assert resp_get.status_code == 200
        data = resp_get.json()
        assert data["title"] == xss_title
        assert data["body"] == xss_body
        assert data["cta"] == xss_cta

    def test_unicode_and_emojis_in_campaign_and_content(self, client):
        """79. Hỗ trợ đầy đủ UTF-8 gồm tiếng Việt có dấu, Emoji, tiếng Nhật, tiếng Hàn, tiếng Trung và ký tự toán học."""
        mkt_headers = get_marketer_headers(client)
        vn_name = "Chiến dịch Mùa Thu 2026 🍁 - Chúc mừng năm mới & Phát tài phát lộc 🇻🇳"
        emoji_title = "🌟🚀 Siêu Khóa Học AI - Làm Chủ Tương Lai! 💡🎯🔥"
        multilingual_body = "日本語: 人工知能の学習 / 한국어: AI 프로그래밍 과정 / 中文: 人工智能实战 / Math: ∑ ∫ π ≠ ≤ ≥ ≈"

        resp_camp = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": vn_name,
            "objective": "Đa ngôn ngữ & Emoji",
            "audience": "Toàn cầu",
            "start_date": "2026-11-01",
            "end_date": "2026-11-30",
            "budget": 2000000.0
        }, headers=mkt_headers)
        assert resp_camp.status_code == 201
        camp_id = resp_camp.json()["id"]

        resp_cnt = client.post("/api/v1/contents", json={
            "campaign_id": camp_id,
            "channel_id": 1,
            "title": emoji_title,
            "body": multilingual_body,
            "cta": "Khám phá ngay 🚀"
        }, headers=mkt_headers)
        assert resp_cnt.status_code == 201
        cnt_id = resp_cnt.json()["id"]

        camp_data = client.get(f"/api/v1/campaigns/{camp_id}", headers=mkt_headers).json()
        assert camp_data["name"] == vn_name

        cnt_data = client.get(f"/api/v1/contents/{cnt_id}", headers=mkt_headers).json()
        assert cnt_data["title"] == emoji_title
        assert cnt_data["body"] == multilingual_body

    def test_campaign_name_exceeding_max_length_rejected(self, client):
        """80. Tên chiến dịch vượt quá giới hạn tối đa (max_length=255) bị Pydantic từ chối với HTTP 422."""
        mkt_headers = get_marketer_headers(client)
        oversized_name = "A" * 256
        resp = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": oversized_name,
            "objective": "Quá độ dài",
            "audience": "All",
            "start_date": "2026-11-01",
            "end_date": "2026-11-30",
            "budget": 1000.0
        }, headers=mkt_headers)
        assert resp.status_code == 422
        assert resp.status_code != 500

    def test_empty_strings_rejected_on_required_fields(self, client):
        """81. Chuỗi rỗng trên các trường bắt buộc (name, title, body) bị từ chối với HTTP 422."""
        mkt_headers = get_marketer_headers(client)

        r1 = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "",
            "objective": "Obj",
            "audience": "All",
            "start_date": "2026-11-01",
            "end_date": "2026-11-30",
            "budget": 1000.0
        }, headers=mkt_headers)
        assert r1.status_code == 422

        r2 = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "",
            "body": "Nội dung hợp lệ",
            "cta": "CTA"
        }, headers=mkt_headers)
        assert r2.status_code == 422

        r3 = client.post("/api/v1/contents", json={
            "campaign_id": 1,
            "channel_id": 1,
            "title": "Tiêu đề hợp lệ",
            "body": "",
            "cta": "CTA"
        }, headers=mkt_headers)
        assert r3.status_code == 422

    def test_type_mismatch_payloads_rejected_cleanly(self, client):
        """82. Dữ liệu sai kiểu (chuỗi truyền vào budget float, views int, content_id int) trả về HTTP 422 (không 500)."""
        mkt_headers = get_marketer_headers(client)

        # Budget không phải số
        r1 = client.post("/api/v1/campaigns", json={
            "product_id": 1,
            "name": "Sai kiểu dữ liệu",
            "objective": "Obj",
            "audience": "All",
            "start_date": "2026-11-01",
            "end_date": "2026-11-30",
            "budget": "khong_phai_so_thuc"
        }, headers=mkt_headers)
        assert r1.status_code == 422

        # Views không phải số nguyên
        r2 = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-20",
            "views": "mot_tram_views",
            "clicks": 10,
            "conversions": 1,
            "cost": 100.0,
            "revenue": 200.0
        }, headers=mkt_headers)
        assert r2.status_code == 422

        # content_id không phải số nguyên
        r3 = client.post("/api/v1/contents/1/schedule", json={
            "content_id": "chuoi_chu_content_id",
            "scheduled_at": "2026-12-01 10:00"
        }, headers=mkt_headers)
        assert r3.status_code == 422

        # Xác nhận tuyệt đối không trả về HTTP 500
        assert r1.status_code != 500
        assert r2.status_code != 500
        assert r3.status_code != 500
