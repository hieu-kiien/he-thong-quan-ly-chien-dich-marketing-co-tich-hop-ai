import pytest
from datetime import datetime, timedelta
from app.models.entities import Task, Campaign, User, CampaignBudgetAllocation, CampaignKPITarget, MarketingChannel

def test_create_and_list_campaign_tasks(client, manager_headers, db_session):
    # Campaign 1 is seeded in workspace 1
    campaign = db_session.query(Campaign).filter(Campaign.id == 1).first()
    assert campaign is not None

    marketer = db_session.query(User).filter(User.email == "marketer@gmail.com").first()
    assert marketer is not None

    task_payload = {
        "title": "Soạn nội dung bài đăng Facebook",
        "description": "Viết copy và brief hình ảnh cho chiến dịch",
        "task_type": "CONTENT",
        "assignee_id": marketer.id,
        "status": "TODO",
        "priority": "HIGH",
        "due_date": (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
    }


    # 1. Create task
    res = client.post("/api/v1/campaigns/1/tasks", json=task_payload, headers=manager_headers)
    assert res.status_code == 201
    created_task = res.json()
    assert created_task["title"] == task_payload["title"]
    assert created_task["assignee_id"] == marketer.id
    assert created_task["campaign_id"] == 1
    task_id = created_task["id"]

    # 2. List tasks for campaign
    res_list = client.get("/api/v1/campaigns/1/tasks", headers=manager_headers)
    assert res_list.status_code == 200
    tasks = res_list.json()["items"]
    assert any(t["id"] == task_id for t in tasks)

    # 3. Filter by priority
    res_filter = client.get("/api/v1/campaigns/1/tasks?priority=HIGH", headers=manager_headers)
    assert res_filter.status_code == 200
    assert all(t["priority"] == "HIGH" for t in res_filter.json()["items"])


def test_my_tasks_endpoint(client, marketer_headers, manager_headers, db_session):
    marketer = db_session.query(User).filter(User.email == "marketer@gmail.com").first()
    assert marketer is not None

    # Create task assigned to marketer
    task_payload = {
        "title": "Thiết kế banner 1200x628",
        "task_type": "DESIGN",
        "assignee_id": marketer.id,
        "status": "TODO",
        "priority": "URGENT",
        "due_date": datetime.utcnow().strftime("%Y-%m-%d")
    }
    res_create = client.post("/api/v1/campaigns/1/tasks", json=task_payload, headers=manager_headers)
    assert res_create.status_code == 201
    created_id = res_create.json()["id"]

    # Fetch marketer's own tasks
    res_my = client.get("/api/v1/tasks/my-tasks", headers=marketer_headers)
    assert res_my.status_code == 200
    my_tasks = res_my.json()["items"]
    assert any(t["id"] == created_id for t in my_tasks)


def test_update_task_rbac_and_field_restrictions(client, marketer_headers, manager_headers, db_session):
    marketer = db_session.query(User).filter(User.email == "marketer@gmail.com").first()

    # Campaign 2 is owned by manager@gmail.com, marketer is only assignee (not owner/creator)
    task_payload = {
        "title": "Duyệt ngân sách giai đoạn 1",
        "task_type": "OTHER",
        "assignee_id": marketer.id,
        "status": "TODO",
        "priority": "MEDIUM",
        "due_date": (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%d")
    }
    res_create = client.post("/api/v1/campaigns/2/tasks", json=task_payload, headers=manager_headers)
    assert res_create.status_code == 201
    task_id = res_create.json()["id"]

    # Marketer (assignee only, not campaign owner) updating status -> ALLOWED
    res_update_status = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "IN_PROGRESS"},
        headers=marketer_headers
    )
    assert res_update_status.status_code == 200
    assert res_update_status.json()["status"] == "IN_PROGRESS"

    # Marketer (assignee only) attempting to change title -> FORBIDDEN 403
    res_restricted = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Đổi tiêu đề trái phép"},
        headers=marketer_headers
    )
    assert res_restricted.status_code == 403

    # Manager updating title and priority -> ALLOWED
    res_mgr_update = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Duyệt ngân sách giai đoạn 1 (Đã sửa)", "priority": "HIGH"},
        headers=manager_headers
    )
    assert res_mgr_update.status_code == 200
    assert res_mgr_update.json()["title"] == "Duyệt ngân sách giai đoạn 1 (Đã sửa)"
    assert res_mgr_update.json()["priority"] == "HIGH"


def test_delete_task_rbac(client, marketer_headers, manager_headers, db_session):
    marketer = db_session.query(User).filter(User.email == "marketer@gmail.com").first()
    task_payload = {
        "title": "Tác vụ thử nghiệm xóa",
        "task_type": "OTHER",
        "assignee_id": marketer.id,
        "status": "TODO",
        "priority": "LOW"
    }
    # Create task in Campaign 2 (owned by manager)
    res_create = client.post("/api/v1/campaigns/2/tasks", json=task_payload, headers=manager_headers)
    assert res_create.status_code == 201
    task_id = res_create.json()["id"]

    # Marketer (who did not create the task and does not own campaign 2) attempting to delete -> 403
    res_del_unauth = client.delete(f"/api/v1/tasks/{task_id}", headers=marketer_headers)
    assert res_del_unauth.status_code == 403

    # Manager deleting -> 204
    res_del = client.delete(f"/api/v1/tasks/{task_id}", headers=manager_headers)
    assert res_del.status_code == 204

    # Verify task deleted
    res_check = client.get(f"/api/v1/tasks/{task_id}", headers=manager_headers)
    assert res_check.status_code == 404



def test_budget_allocations_crud(client, manager_headers, db_session):
    channel1 = db_session.query(MarketingChannel).filter(MarketingChannel.id == 1).first()
    channel2 = db_session.query(MarketingChannel).filter(MarketingChannel.id == 2).first()
    assert channel1 is not None and channel2 is not None

    payload = [
        {"channel_id": channel1.id, "planned_amount": 5000000.0},
        {"channel_id": channel2.id, "planned_amount": 3000000.0}
    ]

    # PUT allocations
    res_put = client.put("/api/v1/campaigns/1/budget-allocations", json=payload, headers=manager_headers)
    assert res_put.status_code == 200
    allocations = res_put.json()
    assert len(allocations) == 2
    assert sum(a["planned_amount"] for a in allocations) == 8000000.0

    # GET allocations
    res_get = client.get("/api/v1/campaigns/1/budget-allocations", headers=manager_headers)
    assert res_get.status_code == 200
    assert len(res_get.json()) == 2


def test_kpi_targets_crud(client, manager_headers):
    payload = [
        {"metric_name": "CTR", "target_value": 3.5, "unit": "%"},
        {"metric_name": "Conversions", "target_value": 150.0, "unit": "actions"},
        {"metric_name": "ROAS", "target_value": 4.0, "unit": "x"}
    ]

    # PUT targets
    res_put = client.put("/api/v1/campaigns/1/kpi-targets", json=payload, headers=manager_headers)
    assert res_put.status_code == 200
    targets = res_put.json()
    assert len(targets) == 3

    # GET targets
    res_get = client.get("/api/v1/campaigns/1/kpi-targets", headers=manager_headers)
    assert res_get.status_code == 200
    assert len(res_get.json()) == 3
    metric_names = [t["metric_name"] for t in res_get.json()]
    assert "CTR" in metric_names
    assert "ROAS" in metric_names


def test_command_center_aggregator(client, manager_headers, marketer_headers, db_session):
    marketer = db_session.query(User).filter(User.email == "marketer@gmail.com").first()

    # Create an overdue task to verify attention item generation
    yesterday_str = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
    overdue_task = Task(
        campaign_id=1,
        workspace_id=1,
        title="Báo cáo chiến dịch quá hạn",
        task_type="RESEARCH",
        assignee_id=marketer.id,
        creator_id=marketer.id,
        status="TODO",
        priority="URGENT",
        due_date=yesterday_str,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(overdue_task)
    db_session.commit()


    # Call command center endpoint
    res = client.get("/api/v1/analytics/command-center", headers=manager_headers)
    assert res.status_code == 200
    data = res.json()

    assert "attention_items" in data
    assert "my_work_today" in data
    assert "campaigns_health" in data
    assert "summary_counts" in data

    # Verify overdue task appears in attention items
    attention_types = [item["type"] for item in data["attention_items"]]
    assert "OVERDUE_TASK" in attention_types
    overdue_item = next(item for item in data["attention_items"] if item["type"] == "OVERDUE_TASK")
    assert overdue_item["severity"] == "CRITICAL" # URGENT priority maps to CRITICAL

    # Verify summary counts
    assert data["summary_counts"]["total_overdue_tasks"] >= 1
    assert data["summary_counts"]["critical_issues"] >= 1

    # Verify marketer's work today
    res_mkt = client.get("/api/v1/analytics/command-center", headers=marketer_headers)
    assert res_mkt.status_code == 200
    mkt_data = res_mkt.json()
    assert any(w["id"] == overdue_task.id for w in mkt_data["my_work_today"])
    my_overdue_work = next(w for w in mkt_data["my_work_today"] if w["id"] == overdue_task.id)
    assert my_overdue_work["is_overdue"] is True


def test_command_center_multi_tenant_isolation(client, beta_marketer_headers, manager_headers, db_session):
    # Call command center as Beta Marketer
    res_beta = client.get("/api/v1/analytics/command-center", headers=beta_marketer_headers)
    assert res_beta.status_code == 200
    beta_data = res_beta.json()

    # Beta marketer must NOT see Alpha campaign (id=1) in campaigns_health
    alpha_campaign_ids = [ch["campaign_id"] for ch in beta_data["campaigns_health"] if ch["campaign_id"] == 1]
    assert len(alpha_campaign_ids) == 0, "Beta marketer leaked Alpha campaign health data!"


def test_campaign_brief_update_persistence(client, manager_headers):
    """Test Item 2: Campaign Brief update API must allow key_message, primary_cta,
    target_kpi_name, target_kpi_value and persist on reload."""
    brief_data = {
        "key_message": "Chuyển đổi số tiếp thị doanh nghiệp toàn diện",
        "primary_cta": "Trải nghiệm miễn phí",
        "target_kpi_name": "conversions",
        "target_kpi_value": 750.0
    }
    # 1. Update campaign brief
    res_put = client.put("/api/v1/campaigns/1", json=brief_data, headers=manager_headers)
    assert res_put.status_code == 200, f"Update failed: {res_put.text}"
    put_data = res_put.json()
    assert put_data["key_message"] == brief_data["key_message"]
    assert put_data["primary_cta"] == brief_data["primary_cta"]
    assert put_data["target_kpi_name"] == brief_data["target_kpi_name"]
    assert float(put_data["target_kpi_value"]) == 750.0

    # 2. Reload campaign and verify persistence
    res_get = client.get("/api/v1/campaigns/1", headers=manager_headers)
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert get_data["key_message"] == brief_data["key_message"]
    assert get_data["primary_cta"] == brief_data["primary_cta"]
    assert get_data["target_kpi_name"] == brief_data["target_kpi_name"]
    assert float(get_data["target_kpi_value"]) == 750.0


def test_task_security_cross_tenant_and_fail_closed(client, manager_headers, beta_marketer_headers, db_session):
    """Test Item 3: Task Security Hardening
    - Absolute removal of campaign.workspace_id or 1
    - Fail-closed on NULL workspace
    - DELETE task must verify workspace access
    - Assignee must belong to valid workspace/campaign
    - Cross-tenant adversarial tests for GET/PATCH/DELETE
    """
    # 1. Manager creates a task in Workspace 1 (Campaign 1)
    marketer = db_session.query(User).filter(User.email == "marketer@gmail.com").first()
    res_create = client.post(
        "/api/v1/campaigns/1/tasks",
        json={
            "title": "Alpha Workspace Task",
            "task_type": "CONTENT",
            "assignee_id": marketer.id,
            "status": "TODO",
            "priority": "HIGH"
        },
        headers=manager_headers
    )
    assert res_create.status_code == 201
    task_id = res_create.json()["id"]

    # 2. Beta Marketer (Tenant 2) tries to GET Alpha task -> 403 Forbidden
    res_get_cross = client.get(f"/api/v1/tasks/{task_id}", headers=beta_marketer_headers)
    assert res_get_cross.status_code == 403

    # 3. Beta Marketer tries to PATCH Alpha task -> 403 Forbidden
    res_patch_cross = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "DONE"},
        headers=beta_marketer_headers
    )
    assert res_patch_cross.status_code == 403

    # 4. Beta Marketer tries to DELETE Alpha task -> 403 Forbidden
    res_del_cross = client.delete(f"/api/v1/tasks/{task_id}", headers=beta_marketer_headers)
    assert res_del_cross.status_code == 403

    # 5. Manager tries to assign task to beta user not in workspace 1 -> 400 Bad Request
    beta_user = db_session.query(User).filter(User.email.like("%beta%")).first()
    if beta_user:
        res_cross_assign = client.post(
            "/api/v1/campaigns/1/tasks",
            json={
                "title": "Adversarial Cross Assignment",
                "task_type": "CONTENT",
                "assignee_id": beta_user.id
            },
            headers=manager_headers
        )
        assert res_cross_assign.status_code == 400

    # 6. Campaign with NULL workspace must fail-closed (403)
    orphan_campaign = Campaign(
        name="Orphan Campaign No Workspace",
        objective="Test fail closed",
        audience="Adversarial",
        start_date="2026-01-01",
        end_date="2026-12-31",
        owner_id=marketer.id,
        product_id=1,
        workspace_id=None
    )
    db_session.add(orphan_campaign)
    db_session.commit()

    res_orphan_task = client.post(
        f"/api/v1/campaigns/{orphan_campaign.id}/tasks",
        json={"title": "Should fail closed on null ws", "task_type": "OTHER"},
        headers=manager_headers
    )
    assert res_orphan_task.status_code == 403


def test_password_hash_robustness_malformed():
    """Test Item 12: verify_password safely handles malformed/corrupted bcrypt hashes
    without raising unhandled exceptions, returning False cleanly."""
    from app.core.security import verify_password

    # Invalid salt / format
    assert verify_password("Secret123", "corrupted_garbage_hash_not_bcrypt") is False
    assert verify_password("Secret123", "$2b$invalid_format_string") is False
    assert verify_password("Secret123", "$2$old_format_rejected") is False
    assert verify_password("Secret123", "") is False
    assert verify_password("", "$2b$12$somevalidlengthbutfakehashstringhere1234567890") is False
    assert verify_password(None, "some_hash") is False
    assert verify_password("Secret123", None) is False

