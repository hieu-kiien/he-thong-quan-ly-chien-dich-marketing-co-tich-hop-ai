"""Comprehensive Multi-Tenant Hardening Test Suite (Worker M4).

Validates zero tenant data bleed, zero default=1 fallbacks in entities and schemas,
zero workspace_id > 1 bypasses, strict RBAC isolation, and scoped notifications.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import Campaign, MarketingContent, Notification, Workspace, WorkspaceMember, User
from app.schemas.schemas import ComplianceCheckRequest
from app.core.security import hash_password, create_access_token


def test_entities_no_default_workspace_id():
    """Verify Campaign and MarketingContent do not have default=1 on workspace_id."""
    camp = Campaign(
        name="Test Campaign Without Workspace",
        product_id=1,
        owner_id=1,
        objective="Testing default",
        audience="Audience",
        start_date="2026-09-01",
        end_date="2026-09-30",
        budget=1000.0,
    )
    assert camp.workspace_id is None, "Campaign.workspace_id must not have a default value of 1"

    content = MarketingContent(
        campaign_id=1,
        created_by=1,
        channel_id=1,
        title="Test Content Without Workspace",
        body="Content body",
    )
    assert content.workspace_id is None, "MarketingContent.workspace_id must not have a default value of 1"


def test_compliance_check_request_schema_default_workspace_id_is_none():
    """Verify ComplianceCheckRequest schema defaults workspace_id to None, not 1."""
    req = ComplianceCheckRequest(content="Nội dung kiểm tra tuân thủ")
    assert req.workspace_id is None, "ComplianceCheckRequest.workspace_id must default to None"


def test_create_campaign_workspace_resolution_via_header(client: TestClient, rbac_headers):
    """Test create_campaign resolves workspace correctly from X-Workspace-Id header."""
    headers = {**rbac_headers["marketer"], "X-Workspace-Id": "1"}
    payload = {
        "name": "Chiến Dịch Hợp Lệ Workspace 1",
        "product_id": 1,
        "objective": "Tăng trưởng doanh thu Q4",
        "audience": "Khách hàng B2B",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31",
        "budget": 5000000.0,
    }
    res = client.post("/api/v1/campaigns/", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["workspace_id"] == 1


def test_create_campaign_cross_tenant_forbidden(client: TestClient, rbac_headers):
    """Test user cannot create campaign in a workspace they are not a member of (403)."""
    # Marketer belongs to Workspace 1, attempts to create in Workspace 2
    headers = {**rbac_headers["marketer"], "X-Workspace-Id": "2"}
    payload = {
        "name": "Chiến Dịch Xâm Phạm Workspace 2",
        "product_id": 1,
        "objective": "Thử nghiệm xâm phạm bảo mật",
        "audience": "Audience",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31",
        "budget": 2000000.0,
    }
    res = client.post("/api/v1/campaigns/", json=payload, headers=headers)
    assert res.status_code == 403
    detail_lower = res.json()["detail"].lower()
    assert "workspace" in detail_lower or "authorized" in detail_lower


def test_create_campaign_without_header_resolves_user_workspace(client: TestClient, rbac_headers):
    """Beta marketer (only member of Workspace 2) creating campaign without X-Workspace-Id resolves to WS 2, never 1."""
    headers = rbac_headers["beta_marketer"]
    payload = {
        "name": "Chiến Dịch Tự Động Gán Workspace Beta",
        "product_id": 1,
        "objective": "Tự động gán",
        "audience": "Audience Beta",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31",
        "budget": 3000000.0,
    }
    res = client.post("/api/v1/campaigns/", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["workspace_id"] == 2, "Beta marketer campaign must resolve to Workspace 2, never fallback to 1"


def test_create_content_cross_tenant_forbidden(client: TestClient, rbac_headers, db_session: Session, workspace_beta: Workspace):
    """Marketer in Workspace 1 cannot create content under Campaign belonging to Workspace 2."""
    beta_camp = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_beta.id).first()
    assert beta_camp is not None

    headers = rbac_headers["marketer"]  # Member of Workspace 1 only
    payload = {
        "campaign_id": beta_camp.id,
        "channel_id": 1,
        "title": "Nội Dung Trái Phép Vào Campaign Beta",
        "body": "Nội dung quảng cáo vi phạm phân vùng dữ liệu",
    }
    res = client.post("/api/v1/contents/", json=payload, headers=headers)
    assert res.status_code == 403
    detail_lower = res.json()["detail"].lower()
    assert "not authorized" in detail_lower or "workspace" in detail_lower


def test_create_content_strictly_inherits_campaign_workspace(client: TestClient, rbac_headers, db_session: Session, workspace_beta: Workspace):
    """Beta marketer creates content under Beta campaign, strictly inheriting workspace_id 2."""
    beta_camp = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_beta.id).first()
    assert beta_camp is not None

    headers = rbac_headers["beta_marketer"]
    payload = {
        "campaign_id": beta_camp.id,
        "channel_id": 1,
        "title": "Video TikTok Hợp Pháp Workspace Beta",
        "body": "Kịch bản video TikTok 15s cho Workspace Beta",
    }
    res = client.post("/api/v1/contents/", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["workspace_id"] == workspace_beta.id


def test_metrics_no_workspace_1_bypass(client: TestClient, rbac_headers, db_session: Session):
    """Verify that workspace_id == 1 does NOT bypass permission checks for users in other workspaces."""
    camp_ws1 = db_session.query(Campaign).filter(Campaign.workspace_id == 1).first()
    assert camp_ws1 is not None

    # Beta marketer (Workspace 2) attempts to view metrics for Campaign 1 (Workspace 1)
    headers = rbac_headers["beta_marketer"]
    res = client.get(f"/api/v1/metrics/campaign/{camp_ws1.id}", headers=headers)
    assert res.status_code == 403
    detail_lower = res.json()["detail"].lower()
    assert "not authorized" in detail_lower or "workspace" in detail_lower


def test_schedules_no_workspace_1_bypass(client: TestClient, rbac_headers):
    """Verify that schedules endpoint scopes query by user accessible workspaces, not leaking WS 1 schedules to WS 2."""
    # Beta marketer lists schedules
    headers = rbac_headers["beta_marketer"]
    res = client.get("/api/v1/schedules/", headers=headers)
    assert res.status_code == 200
    schedules = res.json()
    for s in schedules:
        if s.get("campaign_id"):
            # Should never see Workspace 1 campaigns
            assert s.get("workspace_id", 2) == 2


def test_notifications_scoped_broadcast_isolation(client: TestClient, db_session: Session, rbac_headers):
    """Verify system broadcast notifications (user_id=None) are strictly isolated by workspace_id."""
    # Create broadcast notification in Workspace 1
    notif_ws1 = Notification(
        user_id=None,
        workspace_id=1,
        title="Thông báo toàn hệ thống WS 1",
        message="Bảo trì hệ thống nội bộ Workspace 1",
        type="SYSTEM",
        read=False,
    )
    # Create broadcast notification in Workspace 2
    notif_ws2 = Notification(
        user_id=None,
        workspace_id=2,
        title="Thông báo toàn hệ thống WS 2",
        message="Bảo trì hệ thống nội bộ Workspace 2",
        type="SYSTEM",
        read=False,
    )
    db_session.add_all([notif_ws1, notif_ws2])
    db_session.commit()

    # Beta marketer fetches notifications
    headers_beta = rbac_headers["beta_marketer"]
    res_beta = client.get("/api/v1/notifications/", headers=headers_beta)
    assert res_beta.status_code == 200
    beta_titles = [n["title"] for n in res_beta.json()]
    assert "Thông báo toàn hệ thống WS 2" in beta_titles
    assert "Thông báo toàn hệ thống WS 1" not in beta_titles, "Workspace 1 broadcast must not leak to Workspace 2 user!"

    # Alpha marketer fetches notifications
    headers_alpha = rbac_headers["marketer"]
    res_alpha = client.get("/api/v1/notifications/", headers=headers_alpha)
    assert res_alpha.status_code == 200
    alpha_titles = [n["title"] for n in res_alpha.json()]
    assert "Thông báo toàn hệ thống WS 1" in alpha_titles
    assert "Thông báo toàn hệ thống WS 2" not in alpha_titles, "Workspace 2 broadcast must not leak to Workspace 1 user!"


def test_notifications_unauthorized_workspace_param_forbidden(client: TestClient, rbac_headers):
    """Accessing notifications with workspace_id query param outside user's accessible workspaces returns 403."""
    headers_alpha = rbac_headers["marketer"]  # Member of Workspace 1 only
    res = client.get("/api/v1/notifications/?workspace_id=2", headers=headers_alpha)
    assert res.status_code == 403
    assert "workspace" in res.json()["detail"].lower()


def test_mark_notification_as_read_cross_tenant_forbidden(client: TestClient, db_session: Session, rbac_headers):
    """User in Workspace 2 cannot mark notification of Workspace 1 as read."""
    notif_ws1 = Notification(
        user_id=None,
        workspace_id=1,
        title="Thông báo riêng biệt WS 1",
        message="Nội dung bảo mật",
        type="SYSTEM",
        read=False,
    )
    db_session.add(notif_ws1)
    db_session.commit()
    db_session.refresh(notif_ws1)

    headers_beta = rbac_headers["beta_marketer"]
    res = client.patch(f"/api/v1/notifications/{notif_ws1.id}/read", headers=headers_beta)
    assert res.status_code in (403, 404)
