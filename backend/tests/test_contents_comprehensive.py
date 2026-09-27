import pytest
from app.models.entities import User, Workspace, WorkspaceMember, Campaign, MarketingContent, Product
from app.core.security import create_access_token, hash_password

def get_auth_token(user: User) -> str:
    return create_access_token(data={
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name
    })

def get_headers_for_user(user: User) -> dict:
    token = get_auth_token(user)
    return {"Authorization": f"Bearer {token}"}

class TestWorkspaceBoundaryEnforcement:
    """Kiểm thử tính cô lập ranh giới Workspace đối với quy trình nội dung (Workflow Isolation).
    Người dùng không thuộc workspace của nội dung bị từ chối 403 trên /submit, /approve, /reject, /publish.
    """

    @pytest.fixture
    def setup_isolated_workspaces(self, db_session):
        # 1. Tạo User và Workspace thứ 2 (Tenant B)
        user_ws2_manager = User(
            email="manager_tenant_b@example.com",
            full_name="Manager Tenant B",
            password_hash=hash_password("Password@123"),
            role="AGENCY_MANAGER",
            status="ACTIVE"
        )
        user_ws2_approver = User(
            email="approver_tenant_b@example.com",
            full_name="Approver Tenant B",
            password_hash=hash_password("Password@123"),
            role="CLIENT_APPROVER",
            status="ACTIVE"
        )
        db_session.add_all([user_ws2_manager, user_ws2_approver])
        db_session.commit()
        db_session.refresh(user_ws2_manager)
        db_session.refresh(user_ws2_approver)

        ws2 = Workspace(
            name="Workspace Tenant B",
            slug="ws-tenant-b",
            description="Không gian làm việc riêng của Tenant B",
            owner_id=user_ws2_manager.id,
            status="ACTIVE"
        )
        db_session.add(ws2)
        db_session.commit()
        db_session.refresh(ws2)

        mem_mgr2 = WorkspaceMember(workspace_id=ws2.id, user_id=user_ws2_manager.id, role="AGENCY_MANAGER")
        mem_app2 = WorkspaceMember(workspace_id=ws2.id, user_id=user_ws2_approver.id, role="CLIENT_APPROVER")
        db_session.add_all([mem_mgr2, mem_app2])

        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        product = db_session.query(Product).first()
        camp2 = Campaign(
            workspace_id=ws2.id,
            product_id=product.id,
            owner_id=user_ws2_manager.id,
            name="Chiến dịch Tenant B",
            objective="Tăng trưởng",
            audience="B2B",
            start_date=now,
            end_date=now + timedelta(days=30)
        )
        db_session.add(camp2)
        db_session.commit()
        db_session.refresh(camp2)

        content_ws2 = MarketingContent(
            workspace_id=ws2.id,
            campaign_id=camp2.id,
            channel_id=1,
            created_by=user_ws2_manager.id,
            title="Nội dung thuộc Tenant B",
            body="Đây là nội dung bảo mật của Tenant B",
            cta="Tìm hiểu ngay",
            status="IN_REVIEW"
        )
        db_session.add(content_ws2)
        db_session.commit()
        db_session.refresh(content_ws2)

        return {
            "ws2": ws2,
            "user_ws2_manager": user_ws2_manager,
            "user_ws2_approver": user_ws2_approver,
            "content_ws2": content_ws2
        }

    def test_foreign_user_cannot_approve_workspace_content(self, client, db_session, setup_isolated_workspaces):
        """Manager / Approver thuộc Workspace 1 không được duyệt bài viết thuộc Workspace 2 (403 Forbidden)."""
        content_ws2 = setup_isolated_workspaces["content_ws2"]
        user_ws1_manager = db_session.query(User).filter(User.email == "manager@gmail.com").first()
        headers = get_headers_for_user(user_ws1_manager)

        resp = client.post(f"/api/v1/contents/{content_ws2.id}/approve", headers=headers)
        assert resp.status_code == 403
        assert resp.json()["detail"] == "User does not have access to this workspace content"

    def test_foreign_user_cannot_reject_workspace_content(self, client, db_session, setup_isolated_workspaces):
        """Manager / Approver thuộc Workspace 1 không được từ chối bài viết thuộc Workspace 2 (403 Forbidden)."""
        content_ws2 = setup_isolated_workspaces["content_ws2"]
        user_ws1_approver = db_session.query(User).filter(User.email == "approver@gmail.com").first()
        headers = get_headers_for_user(user_ws1_approver)

        resp = client.post(
            f"/api/v1/contents/{content_ws2.id}/reject",
            json={"decision": "REJECTED", "reason": "Lý do từ chối từ người ngoài workspace"},
            headers=headers
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "User does not have access to this workspace content"

    def test_foreign_user_cannot_publish_workspace_content(self, client, db_session, setup_isolated_workspaces):
        """Manager thuộc Workspace 1 không được xuất bản bài viết thuộc Workspace 2 (403 Forbidden)."""
        content_ws2 = setup_isolated_workspaces["content_ws2"]
        content_ws2.status = "APPROVED"
        db_session.commit()

        user_ws1_manager = db_session.query(User).filter(User.email == "manager@gmail.com").first()
        headers = get_headers_for_user(user_ws1_manager)

        resp = client.post(f"/api/v1/contents/{content_ws2.id}/publish", headers=headers)
        assert resp.status_code == 403
        assert resp.json()["detail"] == "User does not have access to this workspace content"

    def test_foreign_user_cannot_submit_workspace_content(self, client, db_session, setup_isolated_workspaces):
        """Người dùng thuộc Workspace 1 không được gửi duyệt bài viết thuộc Workspace 2 (403 Forbidden)."""
        content_ws2 = setup_isolated_workspaces["content_ws2"]
        content_ws2.status = "DRAFT"
        db_session.commit()

        user_ws1_marketer = db_session.query(User).filter(User.email == "marketer@gmail.com").first()
        headers = get_headers_for_user(user_ws1_marketer)

        resp = client.post(f"/api/v1/contents/{content_ws2.id}/submit", headers=headers)
        assert resp.status_code == 403
        assert resp.json()["detail"] == "User does not have access to this workspace content"

    def test_separated_approver_can_approve_content_of_another_author(self, client, db_session, setup_isolated_workspaces):
        """Happy path đúng nghiệp vụ: người DUYỆT khác người TẠO.

        Nội dung do AGENCY_MANAGER (user A) tạo, CLIENT_APPROVER (user B - khác A, cùng
        Workspace 2) phê duyệt. Đây là mô hình Human-in-the-loop / Separation of Duties:
        người viết không được tự phê duyệt bài của chính mình.
        """
        content_ws2 = setup_isolated_workspaces["content_ws2"]
        mgr2 = setup_isolated_workspaces["user_ws2_manager"]
        approver2 = setup_isolated_workspaces["user_ws2_approver"]

        # Người tạo và người duyệt phải là hai tài khoản KHÁC NHAU
        assert content_ws2.created_by == mgr2.id
        assert approver2.id != mgr2.id
        assert approver2.role == "CLIENT_APPROVER"

        headers_approver2 = get_headers_for_user(approver2)
        headers_mgr2 = get_headers_for_user(mgr2)

        # 1. Approve bởi người duyệt độc lập -> thành công
        r_app = client.post(f"/api/v1/contents/{content_ws2.id}/approve", headers=headers_approver2)
        assert r_app.status_code == 200
        assert r_app.json()["status"] == "APPROVED"

        # 2. Publish (chỉ MANAGER/AGENCY_MANAGER được publish)
        r_pub = client.post(f"/api/v1/contents/{content_ws2.id}/publish", headers=headers_mgr2)
        assert r_pub.status_code == 200
        assert r_pub.json()["status"] == "PUBLISHED"

    def test_author_cannot_approve_own_content(self, client, db_session, setup_isolated_workspaces):
        """P0 regression: người TẠO bị cấm tự phê duyệt bài của chính mình (403 Forbidden)."""
        content_ws2 = setup_isolated_workspaces["content_ws2"]
        mgr2 = setup_isolated_workspaces["user_ws2_manager"]
        assert content_ws2.created_by == mgr2.id

        headers_mgr2 = get_headers_for_user(mgr2)
        resp = client.post(f"/api/v1/contents/{content_ws2.id}/approve", headers=headers_mgr2)
        assert resp.status_code == 403
        assert "tự phê duyệt" in resp.json()["detail"].lower()

        # Trạng thái trong DB phải được giữ nguyên ở IN_REVIEW
        db_session.expire_all()
        assert db_session.query(MarketingContent).filter(
            MarketingContent.id == content_ws2.id
        ).one().status == "IN_REVIEW"


class TestHardenedRoleCheckerAndSubValidation:
    """Kiểm thử tầng xác thực RoleChecker và JWT sub được siết chặt."""

    def test_missing_sub_in_token_rejected_401(self, client):
        """Token không chứa trường 'sub' bị từ chối với HTTP 401."""
        token = create_access_token(data={"role": "MANAGER"})
        resp = client.post("/api/v1/contents/1/approve", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_empty_sub_in_token_rejected_401(self, client):
        """Token chứa trường 'sub' rỗng ('') bị từ chối với HTTP 401."""
        token = create_access_token(data={"sub": "  ", "role": "MANAGER"})
        resp = client.post("/api/v1/contents/1/approve", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_nonexistent_user_sub_rejected_401(self, client):
        """Token chứa sub trỏ tới người dùng không tồn tại bị từ chối với HTTP 401."""
        token = create_access_token(data={"sub": "999999", "role": "MANAGER"})
        resp = client.post("/api/v1/contents/1/approve", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_forged_payload_role_rejected_by_db_role_check(self, client, db_session):
        """Kẻ tấn công giả mạo payload role='MANAGER' nhưng tài khoản trong DB là MARKETER -> bị chặn 403."""
        marketer = db_session.query(User).filter(User.email == "marketer@gmail.com").first()
        assert marketer.role == "MARKETER"

        # Token giả mạo role MANAGER nhưng sub là marketer.id
        forged_token = create_access_token(data={
            "sub": str(marketer.id),
            "email": marketer.email,
            "role": "MANAGER"
        })
        resp = client.post("/api/v1/contents/1/approve", headers={"Authorization": f"Bearer {forged_token}"})
        assert resp.status_code == 403
        assert "Thao tác trái quyền" in resp.json()["detail"]

    def test_inactive_user_rejected_by_role_checker_with_exact_status(self, client, db_session):
        """Tài khoản có status != 'ACTIVE' bị RoleChecker từ chối 403 với thông báo chuẩn."""
        manager = db_session.query(User).filter(User.email == "manager@gmail.com").first()
        manager.status = "DISABLED"
        db_session.commit()

        token = create_access_token(data={
            "sub": str(manager.id),
            "email": manager.email,
            "role": manager.role
        })
        resp = client.post("/api/v1/contents/1/approve", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert "user account is not active" in resp.json()["detail"].lower()
