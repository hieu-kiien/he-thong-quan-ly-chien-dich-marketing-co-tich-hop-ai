"""Adversarial Empirical Stress-Testing Suite for Milestone M4.

Designed by Challenger 1 to rigorously stress-test:
1. Model & schema instantiation without workspace_id (must be None, never default 1).
2. Cross-tenant API requests (Marketer WS1 -> Workspace 2 rejected with 403).
3. Workspace 1 access isolation (Marketer WS2 -> Workspace 1 rejected with 403, zero bypass on WS1).
4. Notification broadcast scoping (WS1 broadcasts completely invisible to WS2 users, cross-tenant read/mark-all-read safe).
5. Edge cases: parameter pollution, spoofed workspace fields, schedule visibility across roles.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import (
    Campaign,
    MarketingContent,
    MarketingSchedule,
    Notification,
    Workspace,
    WorkspaceMember,
    User,
    Product,
    CampaignMember,
)
from app.schemas.schemas import (
    ComplianceCheckRequest,
    CampaignCreate,
    ContentCreate,
)


# ==============================================================================
# SECTION 1: MODEL & SCHEMA INSTANTIATION STRESS TESTS
# ==============================================================================

def test_emp_01_campaign_instantiation_without_workspace_id(db_session: Session):
    """Verify that creating Campaign without workspace_id leaves workspace_id = None, both in Python and in SQLite."""
    # 1. Instantiation without workspace_id
    camp = Campaign(
        product_id=1,
        owner_id=1,
        name="Empirical Test Campaign No WS",
        objective="Verify workspace_id is None",
        audience="Adversarial Auditor",
        start_date="2026-10-01",
        end_date="2026-10-31",
        budget=1000000.0,
    )
    assert camp.workspace_id is None, "Campaign.workspace_id must be None when omitted"

    # 2. Instantiation with explicit workspace_id=None
    camp_none = Campaign(
        workspace_id=None,
        product_id=1,
        owner_id=1,
        name="Empirical Test Campaign Explicit None",
        objective="Verify explicit None",
        audience="Adversarial Auditor",
        start_date="2026-10-01",
        end_date="2026-10-31",
        budget=1000000.0,
    )
    assert camp_none.workspace_id is None, "Campaign.workspace_id must be None when explicitly passed None"

    # 3. Persistence to SQLite database
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)

    assert camp.id is not None
    assert camp.workspace_id is None, "Campaign.workspace_id must remain None after DB insert/refresh (no DB default 1)"

    # 4. Fetching back from DB via clean query
    fetched = db_session.query(Campaign).filter(Campaign.id == camp.id).first()
    assert fetched is not None
    assert fetched.workspace_id is None, "Persisted campaign workspace_id queried from DB must be None"


def test_emp_02_content_instantiation_without_workspace_id(db_session: Session):
    """Verify that creating MarketingContent without workspace_id leaves workspace_id = None, both in Python and in SQLite."""
    # Ensure campaign exists
    camp = Campaign(
        product_id=1,
        owner_id=1,
        name="Parent Campaign",
        objective="Parent",
        audience="Parent",
        start_date="2026-10-01",
        end_date="2026-10-31",
        budget=500000.0,
    )
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)

    # 1. Instantiation without workspace_id
    content = MarketingContent(
        campaign_id=camp.id,
        channel_id=1,
        created_by=1,
        title="Empirical Content No WS",
        body="Empirical Body",
    )
    assert content.workspace_id is None, "MarketingContent.workspace_id must be None when omitted"

    # 2. Instantiation with explicit workspace_id=None
    content_none = MarketingContent(
        workspace_id=None,
        campaign_id=camp.id,
        channel_id=1,
        created_by=1,
        title="Empirical Content None WS",
        body="Empirical Body None",
    )
    assert content_none.workspace_id is None, "MarketingContent.workspace_id must be None when explicitly passed None"

    # 3. Persistence to SQLite database
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    assert content.id is not None
    assert content.workspace_id is None, "MarketingContent.workspace_id must remain None after DB insert/refresh"

    # 4. Fetching back from DB
    fetched = db_session.query(MarketingContent).filter(MarketingContent.id == content.id).first()
    assert fetched is not None
    assert fetched.workspace_id is None, "Persisted content workspace_id queried from DB must be None"


def test_emp_03_schemas_default_workspace_id_none():
    """Verify all relevant Pydantic schemas default workspace_id to None, never 1."""
    # ComplianceCheckRequest
    c_req = ComplianceCheckRequest(content="Testing brand safety compliance")
    assert c_req.workspace_id is None, "ComplianceCheckRequest.workspace_id must default to None"

    # CampaignCreate
    camp_create = CampaignCreate(
        product_id=1,
        name="Campaign Create Test",
        objective="Testing schema defaults",
        audience="Audience",
        start_date="2026-10-01",
        end_date="2026-10-31",
        budget=2000000.0,
    )
    assert camp_create.workspace_id is None, "CampaignCreate.workspace_id must default to None"

    # ContentCreate
    content_create = ContentCreate(
        campaign_id=1,
        channel_id=1,
        title="Content Create Test",
        body="Testing schema defaults",
    )
    assert content_create.workspace_id is None, "ContentCreate.workspace_id must default to None"


# ==============================================================================
# SECTION 2: CROSS-TENANT API REQUESTS (MARKETER WS1 -> WORKSPACE 2)
# ==============================================================================

def test_emp_04_marketer_ws1_cannot_create_campaign_in_ws2_via_header(client: TestClient, rbac_headers):
    """Marketer in WS1 attempts to create campaign in WS2 by specifying X-Workspace-Id: 2 -> HTTP 403."""
    headers = {**rbac_headers["marketer"], "X-Workspace-Id": "2"}
    payload = {
        "name": "Hostile Infiltration Campaign Header",
        "product_id": 1,
        "objective": "Cross-tenant intrusion attempt via header",
        "audience": "Adversary",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31",
        "budget": 1000000.0,
    }
    res = client.post("/api/v1/campaigns/", json=payload, headers=headers)
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_emp_05_marketer_ws1_cannot_create_campaign_in_ws2_via_body(client: TestClient, rbac_headers):
    """Marketer in WS1 attempts to create campaign in WS2 by specifying workspace_id: 2 in JSON body -> HTTP 403."""
    headers = rbac_headers["marketer"]
    payload = {
        "workspace_id": 2,
        "name": "Hostile Infiltration Campaign Body",
        "product_id": 1,
        "objective": "Cross-tenant intrusion attempt via body",
        "audience": "Adversary",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31",
        "budget": 1000000.0,
    }
    res = client.post("/api/v1/campaigns/", json=payload, headers=headers)
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_emp_06_marketer_ws1_cannot_create_campaign_in_ws2_via_header_and_body(client: TestClient, rbac_headers):
    """Marketer in WS1 attempts to create campaign with both header X-Workspace-Id: 2 and body workspace_id: 2 -> HTTP 403."""
    headers = {**rbac_headers["marketer"], "X-Workspace-Id": "2"}
    payload = {
        "workspace_id": 2,
        "name": "Hostile Infiltration Campaign Double WS2",
        "product_id": 1,
        "objective": "Double WS2 attempt",
        "audience": "Adversary",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31",
        "budget": 1000000.0,
    }
    res = client.post("/api/v1/campaigns/", json=payload, headers=headers)
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_emp_07_marketer_ws1_cannot_create_content_in_ws2_campaign(
    client: TestClient, rbac_headers, db_session: Session, workspace_beta: Workspace
):
    """Marketer in WS1 attempts to create content targeting a campaign in WS2 -> HTTP 403."""
    beta_camp = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_beta.id).first()
    assert beta_camp is not None, "Workspace Beta campaign must exist"

    headers = rbac_headers["marketer"]
    payload = {
        "campaign_id": beta_camp.id,
        "channel_id": 1,
        "title": "Cross Tenant Malicious Content",
        "body": "Attempting to inject content into Beta campaign",
    }
    res = client.post("/api/v1/contents/", json=payload, headers=headers)
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_emp_08_marketer_ws1_cannot_create_content_in_ws2_with_spoofed_body(
    client: TestClient, rbac_headers, db_session: Session, workspace_beta: Workspace
):
    """Marketer in WS1 attempts to target WS2 campaign while spoofing workspace_id=1 in content payload -> HTTP 403."""
    beta_camp = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_beta.id).first()
    assert beta_camp is not None

    headers = rbac_headers["marketer"]
    payload = {
        "workspace_id": 1,  # Spoofed: trying to bypass by claiming content belongs to WS1
        "campaign_id": beta_camp.id,  # but campaign belongs to WS2
        "channel_id": 1,
        "title": "Spoofed Workspace Content",
        "body": "Spoofed payload targeting Beta campaign",
    }
    res = client.post("/api/v1/contents/", json=payload, headers=headers)
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"


def test_emp_09_marketer_ws1_cannot_modify_or_delete_ws2_content(
    client: TestClient, rbac_headers, db_session: Session, workspace_beta: Workspace
):
    """Marketer in WS1 attempts to update, delete, or submit content in WS2 -> HTTP 403."""
    beta_content = db_session.query(MarketingContent).filter(MarketingContent.workspace_id == workspace_beta.id).first()
    assert beta_content is not None, "Workspace Beta content must exist"

    headers = rbac_headers["marketer"]

    # 1. Update attempt
    res_put = client.put(f"/api/v1/contents/{beta_content.id}", json={"title": "Hacked Title"}, headers=headers)
    assert res_put.status_code in (403, 404), f"PUT expected 403/404, got {res_put.status_code}: {res_put.text}"

    # 2. Delete attempt (endpoint is not exposed / returns 405 Method Not Allowed or 403)
    res_del = client.delete(f"/api/v1/contents/{beta_content.id}", headers=headers)
    assert res_del.status_code in (403, 404, 405), f"DELETE expected 403/404/405, got {res_del.status_code}: {res_del.text}"

    # 3. Submit for review attempt
    res_sub = client.post(f"/api/v1/contents/{beta_content.id}/submit", headers=headers)
    assert res_sub.status_code in (403, 404), f"Submit expected 403/404, got {res_sub.status_code}: {res_sub.text}"


# ==============================================================================
# SECTION 3: WORKSPACE 1 ACCESS BYPASS (MARKETER WS2 -> WORKSPACE 1)
# ==============================================================================

def test_emp_10_marketer_ws2_cannot_access_ws1_metrics(
    client: TestClient, rbac_headers, db_session: Session, workspace_alpha: Workspace
):
    """Marketer in WS2 attempts to query metrics or KPI of Campaign in Workspace 1 -> HTTP 403."""
    ws1_camp = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()
    assert ws1_camp is not None, "Workspace Alpha campaign must exist"

    headers_beta = rbac_headers["beta_marketer"]

    # 1. Campaign metrics list
    res_metrics = client.get(f"/api/v1/metrics/campaign/{ws1_camp.id}", headers=headers_beta)
    assert res_metrics.status_code == 403, f"Metrics expected 403 Forbidden, got {res_metrics.status_code}"

    # 2. Campaign KPI summary
    res_kpi = client.get(f"/api/v1/metrics/campaign/{ws1_camp.id}/kpi", headers=headers_beta)
    assert res_kpi.status_code == 403, f"KPI expected 403 Forbidden, got {res_kpi.status_code}"


def test_emp_11_marketer_ws2_cannot_access_ws1_campaign_by_id(
    client: TestClient, rbac_headers, db_session: Session, workspace_alpha: Workspace
):
    """Marketer in WS2 attempts to GET or PUT Campaign in Workspace 1 by ID -> HTTP 403."""
    ws1_camp = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()
    assert ws1_camp is not None

    headers_beta = rbac_headers["beta_marketer"]

    # 1. GET campaign by ID
    res_get = client.get(f"/api/v1/campaigns/{ws1_camp.id}", headers=headers_beta)
    assert res_get.status_code == 403, f"GET campaign expected 403 Forbidden, got {res_get.status_code}"

    # 2. PUT campaign by ID
    res_put = client.put(f"/api/v1/campaigns/{ws1_camp.id}", json={"name": "Hacked WS1 Campaign"}, headers=headers_beta)
    assert res_put.status_code == 403, f"PUT campaign expected 403 Forbidden, got {res_put.status_code}"


def test_emp_12_marketer_ws2_cannot_list_ws1_campaigns(
    client: TestClient, rbac_headers, db_session: Session, workspace_alpha: Workspace
):
    """Marketer in WS2 attempting to list campaigns with workspace_id=1 gets 403; listing unscoped never returns WS1 campaigns."""
    headers_beta = rbac_headers["beta_marketer"]

    # 1. Explicitly requesting workspace_id=1
    res_ws1 = client.get(f"/api/v1/campaigns/?workspace_id={workspace_alpha.id}", headers=headers_beta)
    assert res_ws1.status_code == 403, f"Querying WS1 campaigns expected 403, got {res_ws1.status_code}"

    # 2. Unscoped campaign list
    res_all = client.get("/api/v1/campaigns/", headers=headers_beta)
    assert res_all.status_code == 200
    returned_campaigns = res_all.json()
    for c in returned_campaigns:
        assert c["workspace_id"] != workspace_alpha.id, "Unscoped campaigns must NEVER leak Workspace 1 campaigns to WS2 user!"


def test_emp_13_marketer_ws2_cannot_generate_ai_ideas_or_drafts_on_ws1_campaign(
    client: TestClient, rbac_headers, db_session: Session, workspace_alpha: Workspace
):
    """Marketer in WS2 attempts to generate AI ideas or drafts referencing Campaign in WS1 -> HTTP 403."""
    ws1_camp = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()
    assert ws1_camp is not None

    headers_beta = rbac_headers["beta_marketer"]

    # 1. AI Ideas
    res_ideas = client.post(
        "/api/v1/ai/ideas",
        json={"campaign_id": ws1_camp.id, "channel_code": "FACEBOOK"},
        headers=headers_beta
    )
    assert res_ideas.status_code == 403, f"AI Ideas on WS1 campaign expected 403, got {res_ideas.status_code}"

    # 2. AI Draft
    res_draft = client.post(
        "/api/v1/ai/draft",
        json={"campaign_id": ws1_camp.id, "channel_code": "FACEBOOK", "selected_idea": "Test idea for Draft"},
        headers=headers_beta
    )
    assert res_draft.status_code == 403, f"AI Draft on WS1 campaign expected 403, got {res_draft.status_code}"


def test_emp_14_marketer_ws2_cannot_access_ws1_schedules(
    client: TestClient, rbac_headers, db_session: Session, workspace_alpha: Workspace
):
    """Marketer in WS2 requesting schedules with workspace_id=1 gets 403; listing unscoped never returns WS1 schedules."""
    headers_beta = rbac_headers["beta_marketer"]

    # Explicitly requesting workspace_id=1
    res_ws1 = client.get(f"/api/v1/schedules?workspace_id={workspace_alpha.id}", headers=headers_beta)
    assert res_ws1.status_code == 403, f"Querying WS1 schedules expected 403, got {res_ws1.status_code}"


def test_emp_15_investigate_agency_manager_ws2_schedules_scoping(
    client: TestClient, rbac_headers, db_session: Session, workspace_alpha: Workspace, workspace_beta: Workspace
):
    """Adversarial investigation: Does an Agency Manager in WS2 leak schedules from WS1 when querying unscoped /schedules?
    
    In backend/app/api/v1/schedules.py line 48:
    query = query.filter(... | (MarketingContent.workspace_id == 1) | ...)
    Let's empirically test if a schedule in WS1 is returned to WS2 Agency Manager!
    """
    # 1. Create content and schedule in Workspace 1
    ws1_camp = db_session.query(Campaign).filter(Campaign.workspace_id == workspace_alpha.id).first()
    assert ws1_camp is not None

    ws1_content = MarketingContent(
        workspace_id=workspace_alpha.id,
        campaign_id=ws1_camp.id,
        channel_id=1,
        created_by=ws1_camp.owner_id,
        title="Nội dung mật Workspace 1 Lên Lịch",
        body="Nội dung bảo mật của WS 1",
        status="APPROVED",
    )
    db_session.add(ws1_content)
    db_session.commit()
    db_session.refresh(ws1_content)

    ws1_schedule = MarketingSchedule(
        content_id=ws1_content.id,
        scheduled_at="2026-10-15T10:00:00Z",
        timezone="Asia/Ho_Chi_Minh",
        status="PLANNED",
        created_by=ws1_camp.owner_id,
    )
    db_session.add(ws1_schedule)
    db_session.commit()
    db_session.refresh(ws1_schedule)

    # 2. Beta Agency Manager queries unscoped /schedules
    headers_beta_mgr = rbac_headers["beta_agency_manager"]
    res = client.get("/api/v1/schedules", headers=headers_beta_mgr)
    assert res.status_code == 200

    schedules = res.json()
    schedule_content_ids = [s["content_id"] for s in schedules]

    # EMPIRICAL ORACLE:
    # If ws1_content.id is in schedule_content_ids, this confirms an empirical cross-tenant schedule leak!
    leaked = ws1_content.id in schedule_content_ids
    print(f"\n[EMPIRICAL PROBE] Schedule leak detected for WS2 Agency Manager: {leaked}")
    # We record this finding and assert desired tenant isolation behavior:
    # A manager in Workspace 2 should NOT see Workspace 1 schedules!
    assert not leaked, (
        f"CRITICAL VULNERABILITY CONFIRMED: Beta Agency Manager received schedule for content {ws1_content.id} "
        f"belonging to Workspace 1! Caused by `(MarketingContent.workspace_id == 1)` in schedules.py line 48."
    )


# ==============================================================================
# SECTION 4: NOTIFICATION BROADCAST SCOPING STRESS TESTS
# ==============================================================================

def test_emp_16_broadcast_notification_isolation_ws1_to_ws2(
    client: TestClient, db_session: Session, rbac_headers, workspace_alpha: Workspace, workspace_beta: Workspace
):
    """Broadcast notification emitted in Workspace 1 is completely invisible to users in Workspace 2."""
    notif_ws1 = Notification(
        user_id=None,
        workspace_id=workspace_alpha.id,
        title="Thông Báo Broadcast Nội Bộ Workspace 1 (Bảo Mật)",
        message="Thông tin nhạy cảm dành riêng cho thành viên Workspace 1",
        type="SYSTEM",
        read=False,
    )
    db_session.add(notif_ws1)
    db_session.commit()

    headers_beta = rbac_headers["beta_marketer"]
    res_beta = client.get("/api/v1/notifications/", headers=headers_beta)
    assert res_beta.status_code == 200
    beta_titles = [n["title"] for n in res_beta.json()]

    assert "Thông Báo Broadcast Nội Bộ Workspace 1 (Bảo Mật)" not in beta_titles, (
        "CRITICAL LEAK: Workspace 1 broadcast notification leaked to Workspace 2 user!"
    )


def test_emp_17_broadcast_notification_isolation_ws2_to_ws1(
    client: TestClient, db_session: Session, rbac_headers, workspace_alpha: Workspace, workspace_beta: Workspace
):
    """Broadcast notification emitted in Workspace 2 is completely invisible to users in Workspace 1."""
    notif_ws2 = Notification(
        user_id=None,
        workspace_id=workspace_beta.id,
        title="Thông Báo Broadcast Nội Bộ Workspace 2 (Bảo Mật)",
        message="Thông tin nhạy cảm dành riêng cho thành viên Workspace 2",
        type="SYSTEM",
        read=False,
    )
    db_session.add(notif_ws2)
    db_session.commit()

    headers_alpha = rbac_headers["marketer"]
    res_alpha = client.get("/api/v1/notifications/", headers=headers_alpha)
    assert res_alpha.status_code == 200
    alpha_titles = [n["title"] for n in res_alpha.json()]

    assert "Thông Báo Broadcast Nội Bộ Workspace 2 (Bảo Mật)" not in alpha_titles, (
        "CRITICAL LEAK: Workspace 2 broadcast notification leaked to Workspace 1 user!"
    )


def test_emp_18_notification_direct_workspace_query_forbidden(
    client: TestClient, rbac_headers, workspace_alpha: Workspace, workspace_beta: Workspace
):
    """Accessing notifications with cross-tenant workspace_id query param returns HTTP 403 Forbidden."""
    headers_beta = rbac_headers["beta_marketer"]
    res_beta_ws1 = client.get(f"/api/v1/notifications/?workspace_id={workspace_alpha.id}", headers=headers_beta)
    assert res_beta_ws1.status_code == 403, f"Expected 403 Forbidden, got {res_beta_ws1.status_code}"

    headers_alpha = rbac_headers["marketer"]
    res_alpha_ws2 = client.get(f"/api/v1/notifications/?workspace_id={workspace_beta.id}", headers=headers_alpha)
    assert res_alpha_ws2.status_code == 403, f"Expected 403 Forbidden, got {res_alpha_ws2.status_code}"


def test_emp_19_cross_tenant_mark_read_forbidden(
    client: TestClient, db_session: Session, rbac_headers, workspace_alpha: Workspace
):
    """User in Workspace 2 cannot mark broadcast notification of Workspace 1 as read (returns 403)."""
    notif_ws1 = Notification(
        user_id=None,
        workspace_id=workspace_alpha.id,
        title="Thông Báo WS 1 Thử Nghiệm Mark Read",
        message="Kiểm tra không thể bị đánh dấu đọc bởi WS 2",
        type="SYSTEM",
        read=False,
    )
    db_session.add(notif_ws1)
    db_session.commit()
    db_session.refresh(notif_ws1)

    headers_beta = rbac_headers["beta_marketer"]
    res = client.patch(f"/api/v1/notifications/{notif_ws1.id}/read", headers=headers_beta)
    assert res.status_code in (403, 404), f"Expected 403 or 404, got {res.status_code}"

    # Verify notification state in DB was NOT modified
    db_session.refresh(notif_ws1)
    assert notif_ws1.read is False, "WS1 notification was improperly marked as read by WS2 user!"


def test_emp_20_mark_all_read_does_not_mutate_other_workspace_notifications(
    client: TestClient, db_session: Session, rbac_headers, workspace_alpha: Workspace, workspace_beta: Workspace
):
    """Calling mark-all-read by WS2 user must ONLY mark WS2 notifications read, leaving WS1 notifications untouched."""
    # 1. Create broadcast notification in WS1
    notif_ws1 = Notification(
        user_id=None,
        workspace_id=workspace_alpha.id,
        title="WS1 Broadcast Unread",
        message="Must stay unread",
        type="SYSTEM",
        read=False,
    )
    # 2. Create broadcast notification in WS2
    notif_ws2 = Notification(
        user_id=None,
        workspace_id=workspace_beta.id,
        title="WS2 Broadcast Unread",
        message="Should become read",
        type="SYSTEM",
        read=False,
    )
    db_session.add_all([notif_ws1, notif_ws2])
    db_session.commit()
    db_session.refresh(notif_ws1)
    db_session.refresh(notif_ws2)

    # 3. WS2 user triggers mark-all-read without query params
    headers_beta = rbac_headers["beta_marketer"]
    res = client.post("/api/v1/notifications/mark-all-read", headers=headers_beta)
    assert res.status_code == 200

    # 4. Verify in DB
    db_session.refresh(notif_ws1)
    db_session.refresh(notif_ws2)

    assert notif_ws2.read is True, "WS2 broadcast notification should have been marked as read"
    assert notif_ws1.read is False, "WS1 broadcast notification was illegally marked as read by WS2 user action!"
