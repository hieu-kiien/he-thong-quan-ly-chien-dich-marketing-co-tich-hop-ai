import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import (
    Notification, MarketingContent, Campaign, User, Workspace, WorkspaceMember
)
from app.api.v1.notifications import create_notification


# ==============================================================================
# CHALLENGER 2 (M3): EMPIRICAL VERIFICATION OF DATABASE NOTIFICATIONS SYSTEM
# ==============================================================================

class TestNotificationAuthAndValidation:
    """1. Test authentication, token validation and parameter boundaries for notification endpoints."""

    def test_unauthenticated_endpoints_rejected_with_401(self, client: TestClient):
        """Unauthenticated requests must return 401 Unauthorized."""
        res_get = client.get("/api/v1/notifications")
        assert res_get.status_code == 401, f"GET /notifications expected 401, got {res_get.status_code}"

        res_patch = client.patch("/api/v1/notifications/1/read")
        assert res_patch.status_code == 401, f"PATCH /notifications/1/read expected 401, got {res_patch.status_code}"

        res_post = client.post("/api/v1/notifications/mark-all-read")
        assert res_post.status_code == 401, f"POST /notifications/mark-all-read expected 401, got {res_post.status_code}"

    def test_invalid_bearer_token_rejected_with_401(self, client: TestClient):
        """Malformed or expired bearer tokens must return 401."""
        bad_headers = {"Authorization": "Bearer bad.token.signature"}
        res = client.get("/api/v1/notifications", headers=bad_headers)
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"

    def test_limit_query_parameter_validation(self, client: TestClient, marketer_headers):
        """Query parameter 'limit' must enforce ge=1 and le=100."""
        # limit < 1 should return 422
        res_zero = client.get("/api/v1/notifications?limit=0", headers=marketer_headers)
        assert res_zero.status_code == 422, f"Expected 422 for limit=0, got {res_zero.status_code}"

        # limit > 100 should return 422
        res_excess = client.get("/api/v1/notifications?limit=101", headers=marketer_headers)
        assert res_excess.status_code == 422, f"Expected 422 for limit=101, got {res_excess.status_code}"

        # valid limit
        res_valid = client.get("/api/v1/notifications?limit=10", headers=marketer_headers)
        assert res_valid.status_code == 200

    def test_invalid_notification_id_types(self, client: TestClient, marketer_headers):
        """Invalid ID format returns 422, non-existent returns 404."""
        # string non-integer ID -> 422
        res_str = client.patch("/api/v1/notifications/abc/read", headers=marketer_headers)
        assert res_str.status_code == 422

        # negative ID or non-existent -> 404
        res_neg = client.patch("/api/v1/notifications/-1/read", headers=marketer_headers)
        assert res_neg.status_code == 404


class TestNotificationApiEndpoints:
    """2. Test functional behaviour of GET, PATCH mark-read, and POST mark-all-read."""

    def test_get_notifications_schema_conformance(self, client: TestClient, db_session: Session, marketer_headers, workspace_alpha):
        """GET /notifications returns properly structured NotificationResponse objects."""
        mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()

        n = create_notification(
            db=db_session,
            user_id=mkt.id,
            workspace_id=workspace_alpha.id,
            title="Đánh giá chiến dịch Q3",
            message="Chiến dịch của bạn đã đạt 1000 lượt tương tác.",
            notif_type="campaign",
            target_tab="campaigns"
        )

        res = client.get(f"/api/v1/notifications?workspace_id={workspace_alpha.id}", headers=marketer_headers)
        assert res.status_code == 200
        items = res.json()
        assert len(items) >= 1

        match = next((item for item in items if item["id"] == n.id), None)
        assert match is not None
        assert match["title"] == "Đánh giá chiến dịch Q3"
        assert match["message"] == "Chiến dịch của bạn đã đạt 1000 lượt tương tác."
        assert match["type"] == "campaign"
        assert match["read"] is False
        assert match["target_tab"] == "campaigns"
        assert match["workspace_id"] == workspace_alpha.id
        assert match["user_id"] == mkt.id
        assert "created_at" in match

    def test_get_notifications_unread_only_filter(self, client: TestClient, db_session: Session, marketer_headers, workspace_alpha):
        """GET /notifications?unread_only=true returns strictly unread notifications."""
        mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()

        n_unread = create_notification(
            db=db_session,
            user_id=mkt.id,
            workspace_id=workspace_alpha.id,
            title="Chưa Đọc Duy Nhất",
            message="Thông điệp chưa đọc",
            notif_type="info"
        )
        n_read = create_notification(
            db=db_session,
            user_id=mkt.id,
            workspace_id=workspace_alpha.id,
            title="Đã Đọc Rồi",
            message="Thông điệp đã đọc",
            notif_type="info"
        )
        n_read.read = True
        db_session.commit()

        # Query unread only
        res_unread = client.get(f"/api/v1/notifications?workspace_id={workspace_alpha.id}&unread_only=true", headers=marketer_headers)
        assert res_unread.status_code == 200
        titles_unread = [item["title"] for item in res_unread.json()]
        assert "Chưa Đọc Duy Nhất" in titles_unread
        assert "Đã Đọc Rồi" not in titles_unread

        # Query all
        res_all = client.get(f"/api/v1/notifications?workspace_id={workspace_alpha.id}&unread_only=false", headers=marketer_headers)
        assert res_all.status_code == 200
        titles_all = [item["title"] for item in res_all.json()]
        assert "Chưa Đọc Duy Nhất" in titles_all
        assert "Đã Đọc Rồi" in titles_all

    def test_patch_notification_mark_read_idempotence(self, client: TestClient, db_session: Session, marketer_headers, workspace_alpha):
        """PATCH /notifications/{id}/read marks notification as read and is idempotent."""
        mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()

        n = create_notification(
            db=db_session,
            user_id=mkt.id,
            workspace_id=workspace_alpha.id,
            title="Thử nghiệm Mark Read",
            message="Cần đánh dấu đọc",
            notif_type="info"
        )
        assert n.read is False

        # First call -> marks read
        res1 = client.patch(f"/api/v1/notifications/{n.id}/read", headers=marketer_headers)
        assert res1.status_code == 200
        assert res1.json()["read"] is True

        # DB verification
        db_session.refresh(n)
        assert n.read is True

        # Second call (idempotent) -> remains read True
        res2 = client.patch(f"/api/v1/notifications/{n.id}/read", headers=marketer_headers)
        assert res2.status_code == 200
        assert res2.json()["read"] is True

    def test_patch_other_user_notification_forbidden(self, client: TestClient, db_session: Session, marketer_headers, workspace_alpha):
        """Marketer cannot mark Manager's targeted notification as read (HTTP 403 Forbidden)."""
        mgr = db_session.query(User).filter(User.email.in_(["manager@gmail.com", "manager@gmail.com"])).first()

        n_mgr = create_notification(
            db=db_session,
            user_id=mgr.id,
            workspace_id=workspace_alpha.id,
            title="Bảo mật Quản lý",
            message="Thông báo riêng của Quản lý",
            notif_type="review"
        )

        res = client.patch(f"/api/v1/notifications/{n_mgr.id}/read", headers=marketer_headers)
        assert res.status_code == 403
        assert "không có quyền" in res.json()["detail"].lower()

    def test_post_mark_all_read_functionality(self, client: TestClient, db_session: Session, marketer_headers, workspace_alpha):
        """POST /notifications/mark-all-read updates all unread notifications to read=True."""
        mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()

        # Create multiple unread notifications
        for i in range(4):
            create_notification(
                db=db_session,
                user_id=mkt.id,
                workspace_id=workspace_alpha.id,
                title=f"Thông báo chưa đọc {i}",
                message=f"Nội dung {i}",
                notif_type="info"
            )

        # Execute mark-all-read
        res = client.post(f"/api/v1/notifications/mark-all-read?workspace_id={workspace_alpha.id}", headers=marketer_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["count"] >= 4

        # Confirm unread list is now empty
        res_check = client.get(f"/api/v1/notifications?workspace_id={workspace_alpha.id}&unread_only=true", headers=marketer_headers)
        assert res_check.status_code == 200
        assert len(res_check.json()) == 0

        # Subsequent mark-all-read returns count 0
        res_again = client.post(f"/api/v1/notifications/mark-all-read?workspace_id={workspace_alpha.id}", headers=marketer_headers)
        assert res_again.status_code == 200
        assert res_again.json()["count"] == 0


class TestWorkflowTransitionsDatabaseEmission:
    """3. Verify that submitting, approving, rejecting, publishing, and editing approved content emit real DB notifications."""

    def test_emission_1_submit_content(self, client: TestClient, db_session: Session, marketer_headers, manager_headers, workspace_alpha):
        """Submitting content emits a notification to workspace managers/approvers in DB."""
        mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
        campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

        content = MarketingContent(
            workspace_id=workspace_alpha.id,
            campaign_id=campaign.id,
            channel_id=1,
            created_by=mkt.id,
            title="Bài Test Submit Emission",
            body="Nội dung kiểm thử phát sinh thông báo khi gửi duyệt.",
            cta="Đăng ký ngay",
            status="DRAFT",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        # Count notifications before
        count_before = db_session.query(Notification).filter(
            Notification.workspace_id == workspace_alpha.id,
            Notification.title.like("%Yêu cầu phê duyệt%")
        ).count()

        # Marketer submits
        res_sub = client.post(f"/api/v1/contents/{content.id}/submit", headers=marketer_headers)
        assert res_sub.status_code == 200
        assert res_sub.json()["status"] == "IN_REVIEW"

        # Check DB directly
        count_after = db_session.query(Notification).filter(
            Notification.workspace_id == workspace_alpha.id,
            Notification.title.like("%Yêu cầu phê duyệt%")
        ).count()
        assert count_after > count_before, "Database notification was not emitted on content submit!"

        # Inspect notification details
        notif = db_session.query(Notification).filter(
            Notification.workspace_id == workspace_alpha.id,
            Notification.message.like(f"%{content.title}%")
        ).order_by(Notification.id.desc()).first()

        assert notif is not None
        assert "Yêu cầu phê duyệt" in notif.title
        assert notif.type == "review"
        assert notif.target_tab == "reviews"
        assert notif.read is False

    def test_emission_2_approve_content(self, client: TestClient, db_session: Session, marketer_headers, manager_headers, workspace_alpha):
        """Approving content emits a notification to content creator in DB."""
        mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
        mgr = db_session.query(User).filter(User.email.in_(["manager@gmail.com", "manager@gmail.com"])).first()
        campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

        content = MarketingContent(
            workspace_id=workspace_alpha.id,
            campaign_id=campaign.id,
            channel_id=1,
            created_by=mkt.id,
            title="Bài Test Approve Emission",
            body="Nội dung chờ duyệt hợp lệ.",
            cta="Xem chi tiết",
            status="IN_REVIEW",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        # Manager approves
        res_appr = client.post(f"/api/v1/contents/{content.id}/approve", headers=manager_headers)
        assert res_appr.status_code == 200
        assert res_appr.json()["status"] == "APPROVED"

        # Check DB directly for notification targeted to marketer
        notif = db_session.query(Notification).filter(
            Notification.workspace_id == workspace_alpha.id,
            Notification.user_id == mkt.id,
            Notification.title.like("%phê duyệt%")
        ).order_by(Notification.id.desc()).first()

        assert notif is not None, "Notification targeted to creator was not emitted upon approval!"
        assert "phê duyệt" in notif.title.lower()
        assert notif.type == "review"
        assert content.title in notif.message
        assert notif.read is False

    def test_emission_3_reject_content(self, client: TestClient, db_session: Session, marketer_headers, manager_headers, workspace_alpha):
        """Rejecting content emits a notification to content creator containing rejection reason."""
        mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
        campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

        content = MarketingContent(
            workspace_id=workspace_alpha.id,
            campaign_id=campaign.id,
            channel_id=1,
            created_by=mkt.id,
            title="Bài Test Reject Emission",
            body="Nội dung sẽ bị từ chối.",
            cta="Bấm ngay",
            status="IN_REVIEW",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        specific_reason = "Hình ảnh và thông điệp chưa phù hợp với định vị thương hiệu cao cấp"
        res_rej = client.post(
            f"/api/v1/contents/{content.id}/reject",
            json={"decision": "REJECTED", "reason": specific_reason},
            headers=manager_headers
        )
        assert res_rej.status_code == 200
        assert res_rej.json()["status"] == "REJECTED"

        # Check DB directly
        notif = db_session.query(Notification).filter(
            Notification.workspace_id == workspace_alpha.id,
            Notification.user_id == mkt.id,
            Notification.title.like("%từ chối%")
        ).order_by(Notification.id.desc()).first()

        assert notif is not None, "Notification for rejection was not emitted in DB!"
        assert "từ chối" in notif.title.lower()
        assert notif.type == "warning"
        assert specific_reason in notif.message
        assert content.title in notif.message
        assert notif.read is False

    def test_emission_4_publish_content(self, client: TestClient, db_session: Session, manager_headers, workspace_alpha):
        """Publishing content emits a broadcast notification (user_id=None) in DB."""
        campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()
        mgr = db_session.query(User).filter(User.email.in_(["manager@gmail.com", "manager@gmail.com"])).first()

        content = MarketingContent(
            workspace_id=workspace_alpha.id,
            campaign_id=campaign.id,
            channel_id=1,
            created_by=mgr.id,
            title="Bài Test Publish Emission",
            body="Nội dung đã được duyệt sẵn sàng xuất bản.",
            cta="Tham gia ngay",
            status="APPROVED",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        # Manager publishes
        res_pub = client.post(f"/api/v1/contents/{content.id}/publish", headers=manager_headers)
        assert res_pub.status_code == 200
        assert res_pub.json()["status"] == "PUBLISHED"

        # Check DB directly for broadcast notification
        notif = db_session.query(Notification).filter(
            Notification.workspace_id == workspace_alpha.id,
            Notification.title.like("%xuất bản%"),
            Notification.message.like(f"%{content.title}%")
        ).order_by(Notification.id.desc()).first()

        assert notif is not None, "Notification was not emitted in DB upon content publishing!"
        assert notif.user_id is None, "Publish notification should be a workspace broadcast (user_id is None)"
        assert notif.type == "campaign"
        assert notif.target_tab == "campaigns"
        assert notif.read is False

    def test_emission_5_edit_approved_content_resets_and_emits(self, client: TestClient, db_session: Session, marketer_headers, workspace_alpha):
        """Editing an APPROVED content resets status to AI_DRAFT and emits warning notification in DB."""
        mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
        campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

        content = MarketingContent(
            workspace_id=workspace_alpha.id,
            campaign_id=campaign.id,
            channel_id=1,
            created_by=mkt.id,
            title="Bài Đã Duyệt Cần Sửa",
            body="Nội dung gốc đã duyệt ban đầu.",
            cta="Đăng ký",
            status="APPROVED",
            version_no=1
        )
        db_session.add(content)
        db_session.commit()
        db_session.refresh(content)

        # Marketer modifies body
        res_edit = client.put(
            f"/api/v1/contents/{content.id}",
            json={"body": "Nội dung đã được sửa đổi sau khi được duyệt."},
            headers=marketer_headers
        )
        assert res_edit.status_code == 200
        data = res_edit.json()
        assert data["status"] == "AI_DRAFT"
        assert data["version_no"] == 2

        # Check DB directly
        notif = db_session.query(Notification).filter(
            Notification.workspace_id == workspace_alpha.id,
            Notification.title.like("%chỉnh sửa%"),
            Notification.message.like(f"%{content.title}%")
        ).order_by(Notification.id.desc()).first()

        assert notif is not None, "Notification was not emitted in DB when approved content was edited!"
        assert notif.type == "warning"
        assert "AI_DRAFT" in notif.message
        assert notif.read is False


class TestAdversarialTenantIsolationAndEdgeCases:
    """4. Stress test multi-tenant boundaries, cross-workspace isolation, and adversarial edge cases."""

    def test_workspace_isolation_with_workspace_id_param(self, client: TestClient, db_session: Session, marketer_headers, beta_marketer_headers, workspace_alpha, workspace_beta):
        """When workspace_id is provided, notifications are strictly partitioned by workspace."""
        mkt_alpha = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
        mkt_beta = db_session.query(User).filter(User.email.in_(["marketer_beta@gmail.com", "marketer_beta@gmail.com"])).first()

        n_alpha = create_notification(
            db=db_session,
            user_id=mkt_alpha.id,
            workspace_id=workspace_alpha.id,
            title="Alpha Only Notification",
            message="Only for workspace Alpha",
            notif_type="info"
        )
        n_beta = create_notification(
            db=db_session,
            user_id=mkt_beta.id,
            workspace_id=workspace_beta.id,
            title="Beta Only Notification",
            message="Only for workspace Beta",
            notif_type="info"
        )

        # Alpha queries Alpha
        res_a = client.get(f"/api/v1/notifications?workspace_id={workspace_alpha.id}", headers=marketer_headers)
        assert res_a.status_code == 200
        titles_a = [n["title"] for n in res_a.json()]
        assert "Alpha Only Notification" in titles_a
        assert "Beta Only Notification" not in titles_a

        # Beta queries Beta
        res_b = client.get(f"/api/v1/notifications?workspace_id={workspace_beta.id}", headers=beta_marketer_headers)
        assert res_b.status_code == 200
        titles_b = [n["title"] for n in res_b.json()]
        assert "Beta Only Notification" in titles_b
        assert "Alpha Only Notification" not in titles_b

    def test_cross_workspace_broadcast_omitted_workspace_param_audit(self, client: TestClient, db_session: Session, beta_marketer_headers, workspace_alpha, workspace_beta):
        """AUDIT: When workspace_id is omitted on GET /notifications, broadcast notifications
        (user_id=None) across other workspaces leak if not filtered by workspace.
        This test documents current behavior and verifies safety with explicit workspace_id.
        """
        # Create broadcast notification in Workspace Alpha
        n_alpha_broadcast = create_notification(
            db=db_session,
            user_id=None,
            workspace_id=workspace_alpha.id,
            title="Alpha Broadcast Secret",
            message="Workspace Alpha Announcement",
            notif_type="campaign"
        )

        # When Beta marketer specifies their own workspace_id:
        res_isolated = client.get(f"/api/v1/notifications?workspace_id={workspace_beta.id}", headers=beta_marketer_headers)
        assert res_isolated.status_code == 200
        isolated_titles = [n["title"] for n in res_isolated.json()]
        assert "Alpha Broadcast Secret" not in isolated_titles, "Workspace Beta saw Alpha broadcast despite filtering by workspace_id!"

    def test_mark_all_read_with_workspace_scope_does_not_affect_other_workspaces(
        self, client: TestClient, db_session: Session, beta_marketer_headers, workspace_alpha, workspace_beta
    ):
        """POST /mark-all-read?workspace_id=2 must not mark unread notifications of Workspace 1 as read."""
        mkt_alpha = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()

        n_alpha = create_notification(
            db=db_session,
            user_id=mkt_alpha.id,
            workspace_id=workspace_alpha.id,
            title="Alpha Unread Guard",
            message="Must remain unread",
            notif_type="info"
        )
        assert n_alpha.read is False

        # Beta user calls mark-all-read for workspace Beta
        res = client.post(f"/api/v1/notifications/mark-all-read?workspace_id={workspace_beta.id}", headers=beta_marketer_headers)
        assert res.status_code == 200

        # Verify Alpha notification remains unread
        db_session.refresh(n_alpha)
        assert n_alpha.read is False, "Beta's mark-all-read erroneously marked Alpha's notification as read!"

    def test_rapid_consecutive_mark_all_read(self, client: TestClient, marketer_headers, workspace_alpha):
        """Stress test: 10 consecutive mark-all-read calls do not cause database deadlock or error."""
        for _ in range(10):
            res = client.post(f"/api/v1/notifications/mark-all-read?workspace_id={workspace_alpha.id}", headers=marketer_headers)
            assert res.status_code == 200
            assert res.json()["success"] is True
