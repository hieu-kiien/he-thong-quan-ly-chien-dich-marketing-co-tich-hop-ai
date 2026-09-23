import pytest

# ==============================================================================
# NHÓM 1: TRƯỜNG HỢP ĐÚNG (POSITIVE / NORMAL CASES - TC_POS_01 -> TC_POS_05)
# ==============================================================================

def test_tc_pos_01_login_valid(client):
    """TC_POS_01: Đăng nhập hợp lệ cho Manager và Marketer, trả về JWT Token."""
    # 1. Đăng nhập Manager
    resp_mgr = client.post("/api/v1/auth/login", json={
        "email": "manager@ictu.edu.vn",
        "password": "Manager@123"
    })
    assert resp_mgr.status_code == 200
    data_mgr = resp_mgr.json()
    assert "access_token" in data_mgr
    assert data_mgr["user"]["role"] == "MANAGER"

    # 2. Đăng nhập Marketer
    resp_mkt = client.post("/api/v1/auth/login", json={
        "email": "marketer@ictu.edu.vn",
        "password": "Marketer@123"
    })
    assert resp_mkt.status_code == 200
    data_mkt = resp_mkt.json()
    assert "access_token" in data_mkt
    assert data_mkt["user"]["role"] == "MARKETER"


def test_tc_pos_02_create_campaign_valid(client):
    """TC_POS_02: Tạo chiến dịch hợp lệ (start_date < end_date, budget >= 0)."""
    # Lấy token marketer
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "marketer@ictu.edu.vn",
        "password": "Marketer@123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "product_id": 1,
        "name": "Chiến dịch Thu Đông Khởi Nghiệp",
        "objective": "Tiếp cận 10.000 sinh viên tại Thái Nguyên",
        "audience": "Sinh viên đại học",
        "start_date": "2026-11-01",
        "end_date": "2026-11-30",
        "budget": 5000000.0
    }
    resp = client.post("/api/v1/campaigns", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == payload["name"]
    assert data["budget"] == 5000000.0
    assert data["status"] in ["PLANNING", "DRAFT"]


def test_tc_pos_03_ai_ideas_valid_schema(client):
    """TC_POS_03: AI sinh 5 ý tưởng theo schema JSON hợp lệ."""
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "marketer@ictu.edu.vn",
        "password": "Marketer@123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    req_payload = {
        "campaign_id": 1,
        "channel_code": "facebook",
        "tone": "trẻ trung, cuốn hút",
        "prompt_version": "v3"
    }
    resp = client.post("/api/v1/ai/ideas", json=req_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_type"] == "IDEA"
    assert "ideas" in data
    assert len(data["ideas"]) == 5
    first_idea = data["ideas"][0]
    assert "angle" in first_idea
    assert "headline" in first_idea
    assert "concept" in first_idea


def test_tc_pos_04_manager_approve_content(client):
    """TC_POS_04: Manager phê duyệt nội dung đang ở trạng thái IN_REVIEW."""
    # Đăng nhập bằng Manager
    mgr_login = client.post("/api/v1/auth/login", json={
        "email": "manager@ictu.edu.vn",
        "password": "Manager@123"
    })
    token = mgr_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Content id 1 đã ở IN_REVIEW từ seed data
    resp = client.post("/api/v1/contents/1/approve", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "APPROVED"


def test_tc_pos_05_calculate_kpi_correct(client):
    """TC_POS_05: Tính toán CTR, CPC, ROI chuẩn xác từ các metrics."""
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "marketer@ictu.edu.vn",
        "password": "Marketer@123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/campaigns/1/kpi", headers=headers)
    assert resp.status_code == 200
    kpi = resp.json()
    assert kpi["total_views"] == 15700 # 12500 + 3200
    assert kpi["total_clicks"] == 1260 # 850 + 410
    assert kpi["ctr_percent"] > 0
    assert kpi["cpc_avg"] > 0
    assert kpi["roi_percent"] > 0


# ==============================================================================
# NHÓM 2: TRƯỜNG HỢP SAI (NEGATIVE CASES - TC_NEG_01 -> TC_NEG_03)
# ==============================================================================

def test_tc_neg_01_login_invalid_password(client):
    """TC_NEG_01: Đăng nhập sai mật khẩu trả về HTTP 401 Unauthorized."""
    resp = client.post("/api/v1/auth/login", json={
        "email": "manager@ictu.edu.vn",
        "password": "WrongPassword@999"
    })
    assert resp.status_code == 401
    assert "không chính xác" in resp.json()["detail"]


def test_tc_neg_02_create_campaign_invalid_dates(client):
    """TC_NEG_02: Tạo chiến dịch có end_date < start_date trả về HTTP 422."""
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "marketer@ictu.edu.vn",
        "password": "Marketer@123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "product_id": 1,
        "name": "Chiến dịch ngày sai",
        "objective": "Thử nghiệm lỗi ngày",
        "audience": "Mọi người",
        "start_date": "2026-10-30",
        "end_date": "2026-10-01", # Sai: ngày kết thúc trước ngày bắt đầu!
        "budget": 1000000.0
    }
    resp = client.post("/api/v1/campaigns", json=payload, headers=headers)
    assert resp.status_code == 422


def test_tc_neg_03_marketer_delete_campaign_forbidden(client):
    """TC_NEG_03: Marketer xóa chiến dịch bị từ chối với HTTP 403 Forbidden."""
    # Đăng nhập với Marketer (không có quyền xóa)
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "marketer@ictu.edu.vn",
        "password": "Marketer@123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.delete("/api/v1/campaigns/1", headers=headers)
    assert resp.status_code == 403
    assert "Thao tác trái quyền" in resp.json()["detail"]


# ==============================================================================
# NHÓM 3: TRƯỜNG HỢP BIÊN (BOUNDARY CASES - TC_BND_01 -> TC_BND_03)
# ==============================================================================

def test_tc_bnd_01_zero_division_protection(client):
    """TC_BND_01: Chiến dịch 0 views và 0 clicks không crash ZeroDivisionError."""
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "marketer@ictu.edu.vn",
        "password": "Marketer@123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Campaign 2 chưa có metrics nào (0 views, 0 clicks, 0 cost)
    resp = client.get("/api/v1/campaigns/2/kpi", headers=headers)
    assert resp.status_code == 200
    kpi = resp.json()
    assert kpi["total_views"] == 0
    assert kpi["total_clicks"] == 0
    assert kpi["ctr_percent"] == 0.0
    assert kpi["cpc_avg"] == 0.0
    assert kpi["roi_percent"] == 0.0


def test_tc_bnd_02_zero_budget_campaign(client):
    """TC_BND_02: Chiến dịch với ngân sách 0đ là trường hợp biên hợp lệ."""
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "marketer@ictu.edu.vn",
        "password": "Marketer@123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "product_id": 1,
        "name": "Chiến dịch 0 đồng Organic Viral",
        "objective": "Tận dụng kênh tự nhiên",
        "audience": "Cộng đồng mạng",
        "start_date": "2026-12-01",
        "end_date": "2026-12-31",
        "budget": 0.0
    }
    resp = client.post("/api/v1/campaigns", json=payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["budget"] == 0.0


def test_tc_bnd_03_metric_clicks_cannot_exceed_views(client):
    """TC_BND_03: Ràng buộc logic clicks không thể lớn hơn views."""
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "marketer@ictu.edu.vn",
        "password": "Marketer@123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    invalid_metric = {
        "campaign_id": 1,
        "channel_id": 1,
        "metric_date": "2026-09-20",
        "views": 100,
        "clicks": 200, # Vô lý: 200 clicks trên 100 views!
        "conversions": 10,
        "cost": 50000.0,
        "revenue": 100000.0
    }
    resp = client.post("/api/v1/campaigns/1/metrics", json=invalid_metric, headers=headers)
    assert resp.status_code == 422


# ==============================================================================
# BỔ SUNG: QUẢN LÝ LỊCH ĐĂNG (FR04), LỌC KÊNH/THỜI GIAN (FR07), KÊNH & SẢN PHẨM (FR03)
# ==============================================================================

def test_tc_pos_06_schedule_approved_content(client):
    """TC_POS_06: Lập lịch đăng hợp lệ cho nội dung đã được APPROVED."""
    # 1. Manager duyệt bài content 1
    mgr_login = client.post("/api/v1/auth/login", json={
        "email": "manager@ictu.edu.vn",
        "password": "Manager@123"
    })
    token = mgr_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/v1/contents/1/approve", headers=headers)

    # 2. Lập lịch đăng
    schedule_payload = {
        "content_id": 1,
        "scheduled_at": "2026-09-25 10:00:00",
        "timezone": "Asia/Ho_Chi_Minh"
    }
    resp = client.post("/api/v1/contents/1/schedule", json=schedule_payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "PLANNED"


def test_tc_neg_04_schedule_unapproved_content_rejected(client):
    """TC_NEG_04: Lập lịch đăng cho nội dung chưa được duyệt (IN_REVIEW/DRAFT) bị từ chối với HTTP 400."""
    mkt_login = client.post("/api/v1/auth/login", json={
        "email": "marketer@ictu.edu.vn",
        "password": "Marketer@123"
    })
    token = mkt_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Content 1 đang ở IN_REVIEW (chưa approved)
    schedule_payload = {
        "content_id": 1,
        "scheduled_at": "2026-09-25 10:00:00",
        "timezone": "Asia/Ho_Chi_Minh"
    }
    resp = client.post("/api/v1/contents/1/schedule", json=schedule_payload, headers=headers)
    assert resp.status_code == 400
    assert "Chỉ có thể lập lịch cho nội dung đã được Quản lý phê duyệt" in resp.json()["detail"]


def test_tc_pos_07_filter_campaigns_by_channel_and_date(client):
    """TC_POS_07: Tra cứu chiến dịch theo kênh, khoảng thời gian và trạng thái (Mục 3.1.7)."""
    mkt_login = client.post("/api/v1/auth/login", json={
        "email": "marketer@ictu.edu.vn",
        "password": "Marketer@123"
    })
    token = mkt_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Lọc theo trạng thái ACTIVE và khoảng ngày
    resp = client.get("/api/v1/campaigns?status=ACTIVE&start_date=2026-09-01&end_date=2026-09-30", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["status"] == "ACTIVE"


def test_tc_pos_08_get_channels_and_products(client):
    """TC_POS_08: Lấy danh sách kênh truyền thông và sản phẩm hợp lệ (Mục 3.1.3)."""
    mkt_login = client.post("/api/v1/auth/login", json={
        "email": "marketer@ictu.edu.vn",
        "password": "Marketer@123"
    })
    token = mkt_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp_ch = client.get("/api/v1/channels", headers=headers)
    assert resp_ch.status_code == 200
    assert len(resp_ch.json()) >= 4

    resp_prod = client.get("/api/v1/products", headers=headers)
    assert resp_prod.status_code == 200
    assert len(resp_prod.json()) >= 2

