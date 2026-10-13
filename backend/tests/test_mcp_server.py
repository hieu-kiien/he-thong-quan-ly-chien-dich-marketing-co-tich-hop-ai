"""
Test Suite: MarketFlow MCP Server & Agentic AI Copilot
Covers:
- GET /api/v1/mcp/manifest (MCP 2025-03-26 specification)
- POST /api/v1/mcp/rpc (JSON-RPC 2.0 initialize, tools/list, resources/read, tools/call)
- POST /api/v1/mcp/agent/run (Multi-step Agentic workflow orchestration with trace)
- POST /api/v1/mcp/compliance/auto-fix (1-click semantic compliance auto-remediation)
- Multi-tenant workspace isolation across MCP tools
"""

from app.models.entities import Campaign


def test_mcp_manifest_returns_tools_resources_prompts(client, marketer_headers):
    """GET /api/v1/mcp/manifest trả về đầy đủ 8 Tools, 3 Resources và 3 Prompts chuẩn MCP."""
    resp = client.get("/api/v1/mcp/manifest", headers=marketer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["server"]["protocolVersion"] == "2025-03-26"
    assert data["server"]["name"] == "marketflow-mcp-server"
    assert len(data["tools"]) == 8
    assert len(data["resources"]) == 3
    assert len(data["prompts"]) == 3

    tool_names = {t["name"] for t in data["tools"]}
    assert {
        "list_workspace_campaigns",
        "get_campaign_metrics",
        "diagnose_campaign_health",
        "scan_content_compliance",
        "auto_fix_compliance_violations",
        "create_marketing_draft",
        "rebalance_campaign_budget",
        "dispatch_external_webhook",
    }.issubset(tool_names)


def test_mcp_jsonrpc_initialize_and_resources_read(client, marketer_headers):
    """POST /api/v1/mcp/rpc xử lý chuẩn JSON-RPC 2.0 cho initialize và resources/read."""
    init_resp = client.post(
        "/api/v1/mcp/rpc",
        headers=marketer_headers,
        json={"jsonrpc": "2.0", "id": 101, "method": "initialize", "params": {}},
    )
    assert init_resp.status_code == 200
    init_body = init_resp.json()
    assert init_body["jsonrpc"] == "2.0"
    assert init_body["id"] == 101
    assert init_body["result"]["protocolVersion"] == "2025-03-26"

    res_resp = client.post(
        "/api/v1/mcp/rpc",
        headers=marketer_headers,
        json={
            "jsonrpc": "2.0",
            "id": 102,
            "method": "resources/read",
            "params": {"uri": "marketflow://workspace/brand-kit"},
        },
    )
    assert res_resp.status_code == 200
    contents = res_resp.json()["result"]["contents"]
    assert len(contents) == 1
    assert contents[0]["uri"] == "marketflow://workspace/brand-kit"


def test_mcp_jsonrpc_tools_call_and_tenant_isolation(
    client, db_session, marketer_headers, beta_marketer_headers
):
    """POST /api/v1/mcp/rpc gọi tool get_campaign_metrics và chặn truy cập chéo Workspace."""
    alpha_campaign = db_session.query(Campaign).filter(Campaign.workspace_id == 1).first()
    assert alpha_campaign is not None

    # Marketer thuộc Workspace Alpha đọc được KPI chiến dịch Alpha
    ok_resp = client.post(
        "/api/v1/mcp/rpc",
        headers=marketer_headers,
        json={
            "jsonrpc": "2.0",
            "id": 201,
            "method": "tools/call",
            "params": {
                "name": "get_campaign_metrics",
                "arguments": {"campaign_id": alpha_campaign.id},
            },
        },
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["result"]["isError"] is False
    assert ok_resp.json()["result"]["structuredContent"]["campaign_id"] == alpha_campaign.id

    # Marketer thuộc Workspace Beta bị chặn khi truy cập chiến dịch của Workspace Alpha
    denied_resp = client.post(
        "/api/v1/mcp/rpc",
        headers=beta_marketer_headers,
        json={
            "jsonrpc": "2.0",
            "id": 202,
            "method": "tools/call",
            "params": {
                "name": "get_campaign_metrics",
                "arguments": {"campaign_id": alpha_campaign.id},
            },
        },
    )
    assert denied_resp.status_code == 200
    body = denied_resp.json()
    assert "error" in body and body["error"]["code"] == -32003


def test_mcp_compliance_auto_fix_remediates_violations(client, marketer_headers):
    """POST /api/v1/mcp/compliance/auto-fix tự động làm sạch từ khóa cấm và nâng điểm lên 100/100."""
    resp = client.post(
        "/api/v1/mcp/compliance/auto-fix",
        headers=marketer_headers,
        json={
            "channel": "facebook",
            "title": "Cam kết 100% thành công ngay lập tức - Khóa học số 1 Việt Nam",
            "body": "Đăng ký ngay khóa học với cam kết 100% đầu ra và trị dứt điểm nỗi lo thất nghiệp.",
            "cta": "Cam kết 100% miễn phí",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["before_score"] < 100
    assert len(data["applied_fixes"]) >= 2
    assert data["after_compliance"]["score"] == 100
    assert data["after_compliance"]["status"] == "PASSED"
    assert data["after_compliance"]["can_submit"] is True
    assert "cam kết 100%" not in data["rewritten"]["title"].lower()


def test_mcp_agent_run_multi_step_workflow(client, db_session, marketer_headers):
    """POST /api/v1/mcp/agent/run điều phối chuỗi công cụ MCP đa bước và trả về trace chi tiết."""
    alpha_campaign = db_session.query(Campaign).filter(Campaign.workspace_id == 1).first()
    assert alpha_campaign is not None

    resp = client.post(
        "/api/v1/mcp/agent/run",
        headers=marketer_headers,
        json={
            "goal": "Kiểm toán toàn diện chiến dịch, phân tích ngân sách ROAS, tự động làm sạch vi phạm chính sách và lưu bản nháp",
            "campaign_id": alpha_campaign.id,
            "channel": "facebook",
            "draft_input": {
                "title": "Cam kết 100% hiệu quả tức thì",
                "body": "Chương trình đào tạo AI thực chiến với cam kết 100% chất lượng.",
                "cta": "Tìm hiểu ngay",
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["protocol"] == "MCP/2025-03-26"
    assert data["steps_executed"] >= 5
    step_names = [s["name"] for s in data["trace"]]
    assert "marketflow://workspace/brand-kit" in step_names
    assert "get_campaign_metrics" in step_names
    assert "scan_content_compliance" in step_names
    assert "auto_fix_compliance_violations" in step_names
    assert "rebalance_campaign_budget" in step_names
    assert "create_marketing_draft" in step_names


def test_mcp_external_integrations_and_hmac_webhook(client, marketer_headers):
    """Kiểm thử cổng kết nối bên ngoài: Blueprint cấu hình Claude/Cursor & Outbound Webhook ký số HMAC-SHA256."""
    bp_resp = client.get("/api/v1/mcp/integrations/blueprint", headers=marketer_headers)
    assert bp_resp.status_code == 200
    bp = bp_resp.json()
    assert "claude_desktop" in bp["mcp_client_configs"]
    assert "cursor_ide" in bp["mcp_client_configs"]
    assert len(bp["outbound_connectors"]) == 6

    wh_resp = client.post(
        "/api/v1/mcp/integrations/webhook-test",
        headers=marketer_headers,
        json={
            "connector_type": "n8n_zapier",
            "event_type": "content.published",
            "campaign_id": 1,
        },
    )
    assert wh_resp.status_code == 200
    wh = wh_resp.json()
    assert wh["status"] == "SIGNED_AND_DISPATCHED"
    assert wh["signature_algorithm"] == "HMAC-SHA256"
    assert wh["signature_header"].startswith("sha256=")
    assert wh["headers"]["X-MarketFlow-Event"] == "content.published"


def test_rbac_demo_role_switcher(client, marketer_headers):
    """Kiểm thử chuyển nhanh giữa 3 vai trò Demo RBAC (Manager / Marketer / Approver) không lộ mật khẩu."""
    for role_key, expected_role in [
        ("manager", "MANAGER"),
        ("approver", "CLIENT_APPROVER"),
        ("marketer", "MARKETER"),
    ]:
        res = client.post(
            "/api/v1/auth/switch-demo-role",
            headers=marketer_headers,
            json={"role_key": role_key},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["access_token"]
        assert body["user"]["role"] == expected_role

