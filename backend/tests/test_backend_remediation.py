import pytest
from unittest.mock import patch
from app.models.entities import User, MarketingContent, CampaignMetric
from app.core.config import settings
from app.core.security import create_access_token
from app.services.ai.ai_service import ai_service

# ==============================================================================
# Helpers
# ==============================================================================
def get_marketer_headers(client):
    resp = client.post("/api/v1/auth/login", json={
        "email": "marketer@ictu.edu.vn",
        "password": "Marketer@123"
    })
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}

def get_manager_headers(client):
    resp = client.post("/api/v1/auth/login", json={
        "email": "manager@ictu.edu.vn",
        "password": "Manager@123"
    })
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}

# ==============================================================================
# BUG-BE-01 & BUG-BE-02: Content Status Validation & 500 Prevention
# ==============================================================================
def test_bug_be_01_content_create_invalid_status_rejected(client):
    """BUG-BE-01: ContentCreate với status không hợp lệ trả về HTTP 422 thay vì HTTP 500."""
    headers = get_marketer_headers(client)
    payload = {
        "campaign_id": 1,
        "channel_id": 1,
        "title": "Tiêu đề thử nghiệm",
        "body": "Nội dung tiếp thị thử nghiệm",
        "cta": "Click ngay",
        "status": "INVALID_CORRUPT_STATUS"
    }
    resp = client.post("/api/v1/contents", json=payload, headers=headers)
    assert resp.status_code == 422

def test_bug_be_02_content_update_invalid_status_rejected(client):
    """BUG-BE-02: ContentUpdate với status không hợp lệ trả về HTTP 422 thay vì HTTP 500."""
    headers = get_marketer_headers(client)
    payload = {
        "status": "NON_EXISTENT_STATUS"
    }
    resp = client.put("/api/v1/contents/1", json=payload, headers=headers)
    assert resp.status_code == 422

# ==============================================================================
# BUG-BE-03: Duplicate Metric Returns 409 Conflict Instead of HTTP 500
# ==============================================================================
def test_bug_be_03_duplicate_metric_returns_409_conflict(client):
    """BUG-BE-03: Ghi trùng metric_date và channel_id trả về HTTP 409 Conflict thay vì HTTP 500."""
    headers = get_marketer_headers(client)
    metric_payload = {
        "campaign_id": 1,
        "channel_id": 1,
        "metric_date": "2026-10-15",
        "views": 100,
        "clicks": 10,
        "conversions": 1,
        "cost": 10000.0,
        "revenue": 50000.0
    }
    # Lần 1: Tạo mới thành công 201 Created
    r1 = client.post("/api/v1/campaigns/1/metrics", json=metric_payload, headers=headers)
    assert r1.status_code == 201

    # Lần 2: Ghi trùng lặp metric_date và channel_id bị từ chối với 409 Conflict thay vì crash 500
    r2 = client.post("/api/v1/campaigns/1/metrics", json=metric_payload, headers=headers)
    assert r2.status_code == 409
    assert "đã tồn tại" in r2.json()["detail"]

# ==============================================================================
# BUG-BE-04: CORS Security Misconfiguration
# ==============================================================================
def test_bug_be_04_cors_origins_configured_properly():
    """BUG-BE-04: Cấu hình CORS không chứa wildcard '*' khi allow_credentials=True."""
    assert "*" not in settings.ALLOWED_ORIGINS
    assert any("5173" in origin for origin in settings.ALLOWED_ORIGINS)

# ==============================================================================
# BUG-BE-05: Enforce Authentication on Protected Endpoints
# ==============================================================================
def test_bug_be_05_unauthenticated_requests_return_401(client):
    """BUG-BE-05: Các endpoint cần bảo vệ trả về HTTP 401 khi không truyền Token."""
    # Campaigns
    assert client.get("/api/v1/campaigns").status_code == 401
    assert client.get("/api/v1/campaigns/1").status_code == 401
    assert client.put("/api/v1/campaigns/1", json={"name": "Hacked"}).status_code == 401

    # Contents
    assert client.get("/api/v1/contents").status_code == 401
    assert client.get("/api/v1/contents/1").status_code == 401
    assert client.put("/api/v1/contents/1", json={"title": "Hacked"}).status_code == 401
    assert client.post("/api/v1/contents/1/submit").status_code == 401

    # Metrics
    assert client.get("/api/v1/campaigns/1/metrics").status_code == 401
    assert client.post("/api/v1/campaigns/1/metrics", json={}).status_code == 401
    assert client.get("/api/v1/campaigns/1/kpi").status_code == 401
    assert client.get("/api/v1/analytics/dashboard").status_code == 401

    # Schedules & Channels
    assert client.get("/api/v1/schedules").status_code == 401
    assert client.get("/api/v1/channels").status_code == 401

def test_bug_be_05_auth_me_with_invalid_sub_and_disabled_user(client, db_session):
    """BUG-BE-05 & BUG-BE-11: Token có sub không hợp lệ hoặc user bị khóa trả về mã lỗi thích hợp."""
    # 1. Token có sub không phải số
    bad_token = create_access_token(data={"sub": "not_an_integer", "email": "test@test.com", "role": "MARKETER"})
    resp_bad = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert resp_bad.status_code == 401
    assert "không hợp lệ" in resp_bad.json()["detail"]

    # 2. Token của user bị vô hiệu hóa (status='DISABLED')
    user = db_session.query(User).filter(User.email == "marketer@ictu.edu.vn").first()
    user.status = "DISABLED"
    db_session.commit()

    token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
    resp_disabled = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp_disabled.status_code == 403
    assert "vô hiệu hóa" in resp_disabled.json()["detail"]

# ==============================================================================
# BUG-BE-06: Date Format Validation on Campaigns and Metrics
# ==============================================================================
def test_bug_be_06_campaign_invalid_date_format_rejected(client):
    """BUG-BE-06: start_date hoặc end_date sai format YYYY-MM-DD bị từ chối với HTTP 422."""
    headers = get_marketer_headers(client)
    payload = {
        "product_id": 1,
        "name": "Chiến dịch ngày rác",
        "objective": "Kiểm tra validate ngày",
        "audience": "Mọi người",
        "start_date": "invalid-date-format",
        "end_date": "2026-12-31",
        "budget": 1000000.0
    }
    resp = client.post("/api/v1/campaigns", json=payload, headers=headers)
    assert resp.status_code == 422

def test_bug_be_06_metric_invalid_date_format_rejected(client):
    """BUG-BE-06: metric_date sai format YYYY-MM-DD bị từ chối với HTTP 422."""
    headers = get_marketer_headers(client)
    metric_payload = {
        "campaign_id": 1,
        "channel_id": 1,
        "metric_date": "2026/09/01", # Sai định dạng (dùng gạch chéo thay vì gạch ngang)
        "views": 100,
        "clicks": 10,
        "conversions": 1,
        "cost": 1000.0,
        "revenue": 5000.0
    }
    resp = client.post("/api/v1/campaigns/1/metrics", json=metric_payload, headers=headers)
    assert resp.status_code == 422

# ==============================================================================
# BUG-BE-07: Review Workflow Integrity & Anti-Tampering
# ==============================================================================
def test_bug_be_07_disallow_direct_approved_status_via_put(client):
    """BUG-BE-07: Không cho phép set status='APPROVED' trực tiếp qua PUT /contents/{id}."""
    headers = get_marketer_headers(client)
    resp = client.put("/api/v1/contents/1", json={"status": "APPROVED"}, headers=headers)
    assert resp.status_code == 400
    assert "quy trình duyệt" in resp.json()["detail"] or "APPROVED" in resp.json()["detail"]

def test_bug_be_07_modifying_approved_content_reverts_to_ai_draft(client, db_session):
    """BUG-BE-07: Chỉnh sửa bài viết đã APPROVED (title, body, cta) tự động chuyển về AI_DRAFT."""
    headers = get_marketer_headers(client)
    mgr_headers = get_manager_headers(client)

    # 1. Duyệt bài viết số 1 thành APPROVED
    client.post("/api/v1/contents/1/approve", headers=mgr_headers)
    content = db_session.query(MarketingContent).filter(MarketingContent.id == 1).first()
    assert content.status == "APPROVED"

    # 2. Marketer chỉnh sửa nội dung bài viết
    edit_resp = client.put("/api/v1/contents/1", json={"title": "Tiêu đề đã bị can thiệp sau duyệt!"}, headers=headers)
    assert edit_resp.status_code == 200
    assert edit_resp.json()["status"] == "AI_DRAFT"

# ==============================================================================
# BUG-BE-08: AI Fallback Schema Mismatch Resilience
# ==============================================================================
def test_bug_be_08_ai_ideas_fallback_on_invalid_schema(client):
    """BUG-BE-08: AI Provider trả về JSON hợp lệ nhưng sai schema, hệ thống kích hoạt Smart Fallback trả về HTTP 200."""
    headers = get_marketer_headers(client)

    # Giả lập external AI provider trả về JSON nhưng thiếu trường 'ideas'
    with patch.object(ai_service, "_call_provider_with_retry", return_value='{"status": "ok", "unexpected_field": [1, 2, 3]}'):
        # Bật fallback
        ai_service.api_key = "mock_key"
        ai_service.fallback_enabled = True

        req_payload = {
            "campaign_id": 1,
            "channel_code": "facebook",
            "tone": "chuyên nghiệp",
            "prompt_version": "v3"
        }
        resp = client.post("/api/v1/ai/ideas", json=req_payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_type"] == "IDEA"
        assert len(data["ideas"]) >= 1
        assert any("fallback" in w.lower() or "smart fallback" in w.lower() or "schema" in w.lower() for w in data.get("warnings", []))

def test_bug_be_08_ai_error_handled_cleanly_when_fallback_disabled(client):
    """BUG-BE-08: Khi tắt fallback và AI provider bị lỗi, endpoint trả về HTTP 502 thay vì HTTP 500."""
    headers = get_marketer_headers(client)

    with patch.object(ai_service, "_call_provider_with_retry", side_effect=RuntimeError("AI API Connection Timeout")):
        ai_service.api_key = "mock_key"
        ai_service.fallback_enabled = False

        req_payload = {
            "campaign_id": 1,
            "channel_code": "facebook",
            "tone": "chuyên nghiệp",
            "prompt_version": "v3"
        }
        resp = client.post("/api/v1/ai/ideas", json=req_payload, headers=headers)
        assert resp.status_code == 502
        assert "Lỗi" in resp.json()["detail"] or "AI" in resp.json()["detail"]

        # Khôi phục trạng thái fallback mặc định
        ai_service.fallback_enabled = True
        ai_service.api_key = ""

# ==============================================================================
# BUG-BE-10: Foreign Key Enforcement in Test SQLite Engine
# ==============================================================================
def test_bug_be_10_foreign_key_pragma_enabled(client, db_session):
    """BUG-BE-10: Kiểm tra PRAGMA foreign_keys được bật trên SQLite test database."""
    from sqlalchemy import text
    result = db_session.execute(text("PRAGMA foreign_keys")).scalar()
    assert result == 1, "SQLite PRAGMA foreign_keys phải bằng 1 (ON) trong test suite!"
