import pytest
from app.models.entities import Notification, MarketingContent, Campaign, User, WorkspaceMember
from app.api.v1.notifications import create_notification


def test_create_notification_helper(db_session, workspace_alpha):
    """Test the create_notification helper persists correctly in DB."""
    mgr = db_session.query(User).filter(User.email.in_(["manager@gmail.com", "manager@gmail.com"])).first()
    notif = create_notification(
        db=db_session,
        user_id=mgr.id,
        workspace_id=workspace_alpha.id,
        title="Test Helper Title",
        message="Test Helper Message",
        notif_type="info",
        target_tab="dashboard"
    )
    assert notif.id is not None
    assert notif.title == "Test Helper Title"
    assert notif.message == "Test Helper Message"
    assert notif.type == "info"
    assert notif.read is False
    assert notif.target_tab == "dashboard"

    found = db_session.query(Notification).filter(Notification.id == notif.id).first()
    assert found is not None
    assert found.read is False


def test_get_notifications_for_current_user(client, db_session, manager_headers, marketer_headers, workspace_alpha):
    """Test GET /notifications returns notifications for the current user and workspace broadcasts."""
    mgr = db_session.query(User).filter(User.email.in_(["manager@gmail.com", "manager@gmail.com"])).first()
    mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()

    # 1. Notification for manager only
    n1 = create_notification(
        db=db_session,
        user_id=mgr.id,
        workspace_id=workspace_alpha.id,
        title="Manager Private",
        message="Only for manager",
        notif_type="review"
    )

    # 2. Notification for marketer only
    n2 = create_notification(
        db=db_session,
        user_id=mkt.id,
        workspace_id=workspace_alpha.id,
        title="Marketer Private",
        message="Only for marketer",
        notif_type="warning"
    )

    # 3. Broadcast notification (user_id=None)
    n3 = create_notification(
        db=db_session,
        user_id=None,
        workspace_id=workspace_alpha.id,
        title="Workspace Broadcast",
        message="For everyone in workspace",
        notif_type="campaign"
    )

    # Manager should see n1 and n3, but NOT n2
    res_mgr = client.get("/api/v1/notifications", headers=manager_headers)
    assert res_mgr.status_code == 200
    mgr_titles = [n["title"] for n in res_mgr.json()["items"]]
    assert "Manager Private" in mgr_titles
    assert "Workspace Broadcast" in mgr_titles
    assert "Marketer Private" not in mgr_titles

    # Marketer should see n2 and n3, but NOT n1
    res_mkt = client.get("/api/v1/notifications", headers=marketer_headers)
    assert res_mkt.status_code == 200
    mkt_titles = [n["title"] for n in res_mkt.json()["items"]]
    assert "Marketer Private" in mkt_titles
    assert "Workspace Broadcast" in mkt_titles
    assert "Manager Private" not in mkt_titles


def test_get_notifications_unread_filter(client, db_session, marketer_headers, workspace_alpha):
    """Test unread_only filter on GET /notifications."""
    mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()

    n_unread = create_notification(
        db=db_session,
        user_id=mkt.id,
        workspace_id=workspace_alpha.id,
        title="Unread Notice",
        message="Msg 1",
        notif_type="info"
    )

    n_read = create_notification(
        db=db_session,
        user_id=mkt.id,
        workspace_id=workspace_alpha.id,
        title="Read Notice",
        message="Msg 2",
        notif_type="info"
    )
    n_read.read = True
    db_session.commit()

    # Query with unread_only=True
    res = client.get("/api/v1/notifications?unread_only=true", headers=marketer_headers)
    assert res.status_code == 200
    items = res.json()["items"]
    titles = [i["title"] for i in items]
    assert "Unread Notice" in titles
    assert "Read Notice" not in titles


def test_patch_notification_mark_read(client, db_session, marketer_headers, workspace_alpha):
    """Test PATCH /notifications/{id}/read marks a notification as read."""
    mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()

    notif = create_notification(
        db=db_session,
        user_id=mkt.id,
        workspace_id=workspace_alpha.id,
        title="To be marked read",
        message="Please read",
        notif_type="info"
    )
    assert notif.read is False

    res = client.patch(f"/api/v1/notifications/{notif.id}/read", headers=marketer_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == notif.id
    assert data["read"] is True

    # Confirm in DB
    db_session.refresh(notif)
    assert notif.read is True


def test_patch_notification_not_found(client, marketer_headers):
    """Test PATCH /notifications/99999/read returns 404 for non-existent notification."""
    res = client.patch("/api/v1/notifications/99999/read", headers=marketer_headers)
    assert res.status_code == 404
    assert "không tồn tại" in res.json()["detail"].lower()


def test_patch_notification_forbidden_other_user(client, db_session, marketer_headers, workspace_alpha):
    """Test PATCH /notifications/{id}/read fails with 403 when marking another user's private notification."""
    mgr = db_session.query(User).filter(User.email.in_(["manager@gmail.com", "manager@gmail.com"])).first()

    # Create notification strictly for manager
    notif = create_notification(
        db=db_session,
        user_id=mgr.id,
        workspace_id=workspace_alpha.id,
        title="Manager Only Notice",
        message="Confidential",
        notif_type="info"
    )

    # Marketer attempts to mark manager's private notification as read
    res = client.patch(f"/api/v1/notifications/{notif.id}/read", headers=marketer_headers)
    assert res.status_code == 403


def test_post_mark_all_read(client, db_session, marketer_headers, workspace_alpha):
    """Test POST /notifications/mark-all-read marks all unread notifications for current user as read."""
    mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()

    create_notification(db=db_session, user_id=mkt.id, workspace_id=workspace_alpha.id, title="Notice 1", message="1")
    create_notification(db=db_session, user_id=mkt.id, workspace_id=workspace_alpha.id, title="Notice 2", message="2")
    create_notification(db=db_session, user_id=None, workspace_id=workspace_alpha.id, title="Broadcast Notice", message="All")

    res = client.post("/api/v1/notifications/mark-all-read", headers=marketer_headers)
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["count"] >= 3

    # Now verify unread count is 0
    res_unread = client.get("/api/v1/notifications?unread_only=true", headers=marketer_headers)
    assert res_unread.status_code == 200
    assert len(res_unread.json()["items"]) == 0


def test_lifecycle_notifications_trigger(client, db_session, manager_headers, marketer_headers, workspace_alpha):
    """Test notifications are automatically generated on content lifecycle events:
    submit -> approve -> publish and edit reset.
    """
    mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
    mgr = db_session.query(User).filter(User.email.in_(["manager@gmail.com", "manager@gmail.com"])).first()

    # Create campaign and content for marketer
    campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()
    content = MarketingContent(
        workspace_id=workspace_alpha.id,
        campaign_id=campaign.id,
        channel_id=1,
        created_by=mkt.id,
        title="Bài Viết Kiểm Thử Lifecycle",
        body="Nội dung kiểm thử hệ thống thông báo đa tầng khi bài viết di chuyển trong state machine.",
        cta="Tìm hiểu ngay",
        status="DRAFT",
        version_no=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    # 1. On /submit: Marketer submits article
    res_sub = client.post(f"/api/v1/contents/{content.id}/submit", headers=marketer_headers)
    assert res_sub.status_code == 200
    assert res_sub.json()["status"] == "IN_REVIEW"

    # Check that Manager received notification
    res_notif_mgr = client.get("/api/v1/notifications", headers=manager_headers)
    assert res_notif_mgr.status_code == 200
    mgr_notifs = res_notif_mgr.json()["items"]
    submit_notif = next((n for n in mgr_notifs if "Yêu cầu phê duyệt" in n["title"]), None)
    assert submit_notif is not None
    assert "Bài Viết Kiểm Thử Lifecycle" in submit_notif["message"]

    # 2. On /approve: Manager approves article
    res_appr = client.post(f"/api/v1/contents/{content.id}/approve", headers=manager_headers)
    assert res_appr.status_code == 200
    assert res_appr.json()["status"] == "APPROVED"

    # Check that Marketer received approval notification
    res_notif_mkt = client.get("/api/v1/notifications", headers=marketer_headers)
    assert res_notif_mkt.status_code == 200
    mkt_notifs = res_notif_mkt.json()["items"]
    appr_notif = next((n for n in mkt_notifs if "phê duyệt" in n["title"].lower()), None)
    assert appr_notif is not None
    assert "Bài Viết Kiểm Thử Lifecycle" in appr_notif["message"]

    # 3. On edit reset to AI_DRAFT: Marketer edits approved content
    res_edit = client.put(
        f"/api/v1/contents/{content.id}",
        json={"body": "Nội dung đã bị sửa đổi sau khi được duyệt!"},
        headers=marketer_headers
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["status"] == "AI_DRAFT"

    # Check notification for reset to draft
    res_notif_reset = client.get("/api/v1/notifications", headers=manager_headers)
    assert res_notif_reset.status_code == 200
    reset_notif = next((n for n in res_notif_reset.json()["items"] if "chỉnh sửa" in n["title"].lower()), None)
    assert reset_notif is not None
    assert "AI_DRAFT" in reset_notif["message"]


def test_reject_lifecycle_notification(client, db_session, manager_headers, marketer_headers, workspace_alpha):
    """Test notification is sent to content owner on /reject with specific reason."""
    mkt = db_session.query(User).filter(User.email.in_(["marketer@gmail.com", "marketer@gmail.com"])).first()
    campaign = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()

    content = MarketingContent(
        workspace_id=workspace_alpha.id,
        campaign_id=campaign.id,
        channel_id=1,
        created_by=mkt.id,
        title="Bài Viết Bị Từ Chối",
        body="Nội dung cần bị từ chối với lý do rõ ràng.",
        cta="Bấm ngay",
        status="IN_REVIEW",
        version_no=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    res_rej = client.post(
        f"/api/v1/contents/{content.id}/reject",
        json={"decision": "REJECTED", "reason": "Giọng văn chưa chuẩn phong cách thương hiệu"},
        headers=manager_headers
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "REJECTED"

    # Verify Marketer received notification with rejection reason
    res_notifs = client.get("/api/v1/notifications", headers=marketer_headers)
    assert res_notifs.status_code == 200
    rej_notif = next((n for n in res_notifs.json()["items"] if "từ chối" in n["title"].lower()), None)
    assert rej_notif is not None
    assert "Giọng văn chưa chuẩn phong cách thương hiệu" in rej_notif["message"]
