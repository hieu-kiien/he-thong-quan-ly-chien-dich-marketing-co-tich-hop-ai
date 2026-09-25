"""Unit and Integration Tests for Milestone 5:
Attribution Analytics & Actionable AI Doctor (R5 - FEAT-BE-19, FEAT-BE-20, FEAT-BE-21).
"""

import pytest
from typing import Dict
from fastapi.testclient import TestClient
from app.models.entities import Campaign, CampaignMetric, MarketingChannel, User


@pytest.fixture
def manager_headers(client: TestClient) -> Dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": "manager@ictu.edu.vn", "password": "Manager@123"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def marketer_headers(client: TestClient) -> Dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": "marketer@ictu.edu.vn", "password": "Marketer@123"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def create_test_campaign(db_session, name: str = "Test Campaign", owner_id: int = 1, budget: float = 50000000.0) -> Campaign:
    camp = Campaign(
        name=name,
        workspace_id=1,
        owner_id=owner_id,
        product_id=1,
        objective="Tối ưu hóa chuyển đổi và mở rộng nhận diện thương hiệu",
        audience="Khách hàng đô thị hiện đại 20-40 tuổi",
        start_date="2026-10-01",
        end_date="2026-10-31",
        budget=budget,
        status="ACTIVE"
    )
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)
    return camp


# ==============================================================================
# 1. Economic KPI Computations & Zero-Division Safeguards (FEAT-BE-19)
# ==============================================================================

def test_01_kpi_summary_contains_roas_and_channel_metrics(client: TestClient, manager_headers):
    """Xác thực endpoint KPI trả về đầy đủ trường roas và channel_metrics."""
    resp = client.get("/api/v1/campaigns/1/kpi", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "roas" in data
    assert "channel_metrics" in data
    assert isinstance(data["roas"], (int, float))
    assert isinstance(data["channel_metrics"], list)


def test_02_kpi_roas_calculation_accuracy(client: TestClient, manager_headers, db_session):
    """Xác thực tính toán ROAS chính xác: roas = total_revenue / total_cost."""
    camp = create_test_campaign(db_session, name="Test ROAS Accuracy Campaign", budget=100000000.0)

    # Ingest metric: cost = 10,000,000, revenue = 35,000,000 -> ROAS = 3.5, ROI = 250.0%
    metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-10-10",
        views=20000,
        clicks=1000,
        conversions=50,
        cost=10000000.0,
        revenue=35000000.0
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cost"] == 10000000.0
    assert data["total_revenue"] == 35000000.0
    assert data["roas"] == 3.5
    assert data["roi_percent"] == 250.0


def test_03_kpi_zero_cost_safeguard_no_zerodivision(client: TestClient, manager_headers, db_session):
    """Rào chắn an toàn khi cost = 0: roas = 0.0, roi = 0.0, cpc = 0.0, không crash."""
    camp = create_test_campaign(db_session, name="Zero Cost Campaign")

    metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=2,
        metric_date="2026-10-11",
        views=15000,
        clicks=800,
        conversions=40,
        cost=0.0,
        revenue=12000000.0
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["roas"] == 0.0
    assert data["roi_percent"] == 0.0
    assert data["cpc_avg"] == 0.0


def test_04_kpi_zero_views_safeguard(client: TestClient, manager_headers, db_session):
    """Rào chắn an toàn khi views = 0: ctr_percent = 0.0."""
    camp = create_test_campaign(db_session, name="Zero Views Campaign")

    metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-10-12",
        views=0,
        clicks=0,
        conversions=0,
        cost=100000.0,
        revenue=0.0
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=manager_headers)
    assert resp.status_code == 200
    assert resp.json()["ctr_percent"] == 0.0


def test_05_kpi_zero_clicks_safeguard(client: TestClient, manager_headers, db_session):
    """Rào chắn an toàn khi clicks = 0: cpc_avg = 0.0, cvr_percent = 0.0."""
    camp = create_test_campaign(db_session, name="Zero Clicks Campaign")

    metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-10-13",
        views=5000,
        clicks=0,
        conversions=0,
        cost=500000.0,
        revenue=0.0
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["cpc_avg"] == 0.0
    assert data["cvr_percent"] == 0.0


def test_06_kpi_empty_campaign_clean_zeros(client: TestClient, manager_headers, db_session):
    """Chiến dịch rỗng (0 metrics) trả về các số 0/0.0 sạch sẽ, không crash."""
    camp = create_test_campaign(db_session, name="Empty Campaign For KPI")

    resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_views"] == 0
    assert data["total_clicks"] == 0
    assert data["total_conversions"] == 0
    assert data["total_cost"] == 0.0
    assert data["total_revenue"] == 0.0
    assert data["roas"] == 0.0
    assert data["roi_percent"] == 0.0


def test_07_kpi_negative_cost_rejected_422(client: TestClient, manager_headers):
    """Từ chối số liệu chi phí hoặc doanh thu âm (HTTP 422)."""
    resp = client.post("/api/v1/campaigns/1/metrics", json={
        "campaign_id": 1,
        "channel_id": 1,
        "metric_date": "2026-11-28",
        "views": 100,
        "clicks": 10,
        "conversions": 1,
        "cost": -100000.0,
        "revenue": 500000.0
    }, headers=manager_headers)
    assert resp.status_code == 422


def test_08_kpi_clicks_exceed_views_rejected_422(client: TestClient, manager_headers):
    """Từ chối dữ liệu vô lý khi clicks > views (HTTP 422)."""
    resp = client.post("/api/v1/campaigns/1/metrics", json={
        "campaign_id": 1,
        "channel_id": 1,
        "metric_date": "2026-11-28",
        "views": 50,
        "clicks": 100,
        "conversions": 5,
        "cost": 100000.0,
        "revenue": 500000.0
    }, headers=manager_headers)
    assert resp.status_code == 422


def test_09_kpi_large_financial_scale_accuracy(client: TestClient, manager_headers, db_session):
    """Xử lý chính xác số liệu tài chính quy mô lớn (5 tỷ chi phí, 25 tỷ doanh thu)."""
    camp = create_test_campaign(db_session, name="Mega Scale Campaign", budget=10000000000.0)

    metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-11-29",
        views=10000000,
        clicks=500000,
        conversions=25000,
        cost=5000000000.0,
        revenue=25000000000.0
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cost"] == 5000000000.0
    assert data["total_revenue"] == 25000000000.0
    assert data["roas"] == 5.0
    assert data["roi_percent"] == 400.0


# ==============================================================================
# 2. Channel Attribution Analytics (FEAT-BE-20)
# ==============================================================================

def test_10_channel_attribution_endpoint_format(client: TestClient, manager_headers):
    """Xác thực endpoint GET /campaigns/{id}/attribution trả về danh sách phân bổ kênh chuẩn."""
    resp = client.get("/api/v1/campaigns/1/attribution", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        ch = data[0]
        assert "channel_id" in ch
        assert "channel_name" in ch
        assert "cost" in ch
        assert "revenue" in ch
        assert "roas" in ch
        assert "share_of_cost" in ch
        assert "share_of_revenue" in ch


def test_11_channel_attribution_empty_campaign(client: TestClient, manager_headers, db_session):
    """Chiến dịch rỗng trả về danh sách phân bổ rỗng []."""
    camp = create_test_campaign(db_session, name="Empty Campaign For Attribution")

    resp = client.get(f"/api/v1/campaigns/{camp.id}/attribution", headers=manager_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_12_channel_attribution_multi_channel_breakdown(client: TestClient, manager_headers, db_session):
    """Xác thực phân bổ 2 kênh khác nhau với share of cost và share of revenue."""
    camp = create_test_campaign(db_session, name="Multi Channel Attribution Campaign")

    # Kênh 1 (Facebook): Chi phí 6,000,000, Doanh thu 18,000,000 -> ROAS 3.0
    m1 = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-10-15",
        views=10000,
        clicks=500,
        conversions=25,
        cost=6000000.0,
        revenue=18000000.0
    )
    # Kênh 2 (TikTok): Chi phí 4,000,000, Doanh thu 16,000,000 -> ROAS 4.0
    m2 = CampaignMetric(
        campaign_id=camp.id,
        channel_id=2,
        metric_date="2026-10-15",
        views=15000,
        clicks=800,
        conversions=40,
        cost=4000000.0,
        revenue=16000000.0
    )
    db_session.add_all([m1, m2])
    db_session.commit()

    resp = client.get(f"/api/v1/campaigns/{camp.id}/attribution", headers=manager_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2

    # Tổng chi phí 10M, FB chiếm 60%, TikTok chiếm 40%
    fb_ch = next(c for c in items if c["channel_id"] == 1)
    tt_ch = next(c for c in items if c["channel_id"] == 2)
    assert fb_ch["share_of_cost"] == 60.0
    assert tt_ch["share_of_cost"] == 40.0
    assert fb_ch["roas"] == 3.0
    assert tt_ch["roas"] == 4.0


# ==============================================================================
# 3. Actionable AI Doctor Service (FEAT-BE-21)
# ==============================================================================

def test_13_ai_doctor_post_success(client: TestClient, manager_headers):
    """POST /campaigns/{id}/ai-doctor trả về HTTP 200 với các trường cốt lõi."""
    resp = client.post("/api/v1/campaigns/1/ai-doctor", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["health_status"] in ("HEALTHY", "NEEDS_ATTENTION", "CRITICAL")
    assert 0 <= data["health_score"] <= 100
    assert "diagnosis_summary" in data
    assert isinstance(data["recommendations"], list)
    assert "bottlenecks" in data


def test_14_ai_doctor_get_success(client: TestClient, manager_headers):
    """GET /campaigns/{id}/ai-doctor chuyển tiếp và trả về HTTP 200 tương tự POST."""
    resp = client.get("/api/v1/campaigns/1/ai-doctor", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "health_status" in data
    assert "health_score" in data


def test_15_ai_doctor_sparse_metrics_handling(client: TestClient, manager_headers, db_session):
    """Chiến dịch mới không có metrics trả về 200 OK sạch sẽ với is_sparse_data=True."""
    camp = create_test_campaign(db_session, name="Empty Campaign For Doctor")

    resp = client.post(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_sparse_data"] is True
    assert data["health_status"] in ("HEALTHY", "NEEDS_ATTENTION")
    assert data["health_score"] == 50
    assert len(data["recommendations"]) > 0


def test_16_ai_doctor_detects_low_roas_bottleneck(client: TestClient, manager_headers, db_session):
    """AI Doctor nhận diện điểm nghẽn khi ROAS < 1.0 (chiến dịch lỗ vốn)."""
    camp = create_test_campaign(db_session, name="Losing Money Campaign")

    # Cost = 15,000,000, Revenue = 3,000,000 -> ROAS = 0.20
    metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-10-18",
        views=20000,
        clicks=500,
        conversions=5,
        cost=15000000.0,
        revenue=3000000.0
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.post(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["health_status"] == "CRITICAL"
    bottlenecks_text = " ".join(data["bottlenecks"])
    assert "ROAS" in bottlenecks_text or "lỗ" in bottlenecks_text or "thâm hụt" in bottlenecks_text


def test_17_ai_doctor_detects_low_ctr_bottleneck(client: TestClient, manager_headers, db_session):
    """AI Doctor phát hiện điểm nghẽn CTR < 1.5% khi có nhiều views."""
    camp = create_test_campaign(db_session, name="Low CTR Campaign")

    # Views = 10,000, Clicks = 50 -> CTR = 0.5% (< 1.5%)
    metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-10-19",
        views=10000,
        clicks=50,
        conversions=5,
        cost=1000000.0,
        revenue=2000000.0
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.post(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    bottlenecks_text = " ".join(data["bottlenecks"])
    assert "CTR" in bottlenecks_text or "nhấp" in bottlenecks_text


def test_18_ai_doctor_detects_low_cvr_bottleneck(client: TestClient, manager_headers, db_session):
    """AI Doctor phát hiện điểm nghẽn CVR < 2.0% khi có nhiều clicks."""
    camp = create_test_campaign(db_session, name="Low CVR Campaign")

    # Clicks = 1000, Conversions = 5 -> CVR = 0.5% (< 2.0%)
    metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-10-20",
        views=20000,
        clicks=1000,
        conversions=5,
        cost=2000000.0,
        revenue=3000000.0
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.post(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    bottlenecks_text = " ".join(data["bottlenecks"])
    assert "CVR" in bottlenecks_text or "chuyển đổi" in bottlenecks_text


def test_19_ai_doctor_recommendations_scale_high_performer(client: TestClient, manager_headers, db_session):
    """AI Doctor đề xuất hành động SCALE cho kênh có ROAS >= 3.0."""
    camp = create_test_campaign(db_session, name="Scale Recommendation Campaign")

    metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=2,  # TikTok
        metric_date="2026-10-21",
        views=50000,
        clicks=2500,
        conversions=150,
        cost=8000000.0,
        revenue=32000000.0  # ROAS = 4.0
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.post(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=manager_headers)
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    actions = [r["action"] for r in recs]
    assert "SCALE" in actions


def test_20_ai_doctor_recommendations_reduce_loss_channel(client: TestClient, manager_headers, db_session):
    """AI Doctor đề xuất hành động REDUCE hoặc PAUSE cho kênh thua lỗ (ROAS < 1.0)."""
    camp = create_test_campaign(db_session, name="Reduce Recommendation Campaign")

    metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-10-22",
        views=15000,
        clicks=300,
        conversions=2,
        cost=10000000.0,
        revenue=2000000.0  # ROAS = 0.20
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.post(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=manager_headers)
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    actions = [r["action"] for r in recs]
    assert "REDUCE" in actions or "PAUSE" in actions


def test_21_ai_doctor_recommendations_optimize_channel(client: TestClient, manager_headers, db_session):
    """AI Doctor đề xuất OPTIMIZE khi kênh có CTR thấp hoặc CVR thấp."""
    camp = create_test_campaign(db_session, name="Optimize Recommendation Campaign")

    # Views = 5000, Clicks = 20 -> CTR = 0.4% (< 1.5%)
    metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-10-23",
        views=5000,
        clicks=20,
        conversions=1,
        cost=500000.0,
        revenue=1000000.0
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.post(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=manager_headers)
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    actions = [r["action"] for r in recs]
    assert "OPTIMIZE" in actions


# ==============================================================================
# 4. RBAC, Error Handling & Dashboard Integration
# ==============================================================================

def test_22_ai_doctor_nonexistent_campaign_404(client: TestClient, manager_headers):
    """Chiến dịch không tồn tại trả về HTTP 404."""
    resp = client.post("/api/v1/campaigns/99999/ai-doctor", headers=manager_headers)
    assert resp.status_code == 404


def test_23_ai_doctor_authorization_forbidden(client: TestClient, marketer_headers, db_session):
    """Marketer không được quyền truy cập chẩn đoán của chiến dịch mình không sở hữu."""
    # Tạo chiến dịch thuộc sở hữu của Manager (owner_id = 1), không gán Marketer làm member
    other_camp = create_test_campaign(db_session, name="Private Campaign", owner_id=1)

    resp = client.post(f"/api/v1/campaigns/{other_camp.id}/ai-doctor", headers=marketer_headers)
    assert resp.status_code == 403


def test_24_global_dashboard_includes_roas(client: TestClient, manager_headers):
    """GET /analytics/dashboard trả về KPI chứa trường roas."""
    resp = client.get("/api/v1/analytics/dashboard", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "kpi" in data
    assert "roas" in data["kpi"]
    assert isinstance(data["kpi"]["roas"], (int, float))
