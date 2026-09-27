"""Unit and Integration Tests for CPA (Cost Per Acquisition) Metric (FR09 & V9 Research Model Sync).
Validates math calculation, zero-division protection, and schema compliance.
"""

import pytest
from typing import Dict
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import Campaign, CampaignMetric, User
from app.schemas.schemas import KPISummaryResponse


@pytest.fixture
def auth_headers(client: TestClient) -> Dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": "manager@gmail.com", "password": "Manager@123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_01_kpi_schema_includes_cpa_field():
    """Xác thực schema KPISummaryResponse có trường cpa_avg với giá trị mặc định là 0.0."""
    kpi = KPISummaryResponse(
        total_views=1000,
        total_clicks=100,
        total_conversions=10,
        total_cost=500000.0,
        total_revenue=1500000.0,
        ctr_percent=10.0,
        cpc_avg=5000.0,
        cvr_percent=10.0,
        roi_percent=200.0,
    )
    assert hasattr(kpi, "cpa_avg")
    assert kpi.cpa_avg == 0.0

    # Khởi tạo có cpa_avg tường minh
    kpi_with_cpa = KPISummaryResponse(
        total_views=1000,
        total_clicks=100,
        total_conversions=10,
        total_cost=500000.0,
        total_revenue=1500000.0,
        ctr_percent=10.0,
        cpc_avg=5000.0,
        cvr_percent=10.0,
        cpa_avg=50000.0,
        roi_percent=200.0,
    )
    assert kpi_with_cpa.cpa_avg == 50000.0


def test_02_cpa_normal_calculation(client: TestClient, auth_headers: Dict[str, str], db_session: Session):
    """Xác thực công thức tính toán CPA: total_cost / total_conversions."""
    # Tạo chiến dịch mới
    camp = Campaign(
        name="CPA Normal Test Campaign",
        workspace_id=1,
        owner_id=1,
        product_id=1,
        objective="Kiểm thử chỉ số CPA chuẩn",
        audience="Khách hàng tiềm năng",
        start_date="2026-10-01",
        end_date="2026-10-31",
        budget=20000000.0,
        status="ACTIVE"
    )
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)

    # Thêm metric: cost = 5,000,000; conversions = 100 -> CPA = 50,000
    metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-10-05",
        views=10000,
        clicks=500,
        conversions=100,
        cost=5000000.0,
        revenue=15000000.0
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "cpa_avg" in data
    assert data["cpa_avg"] == 50000.0
    assert data["total_cost"] == 5000000.0
    assert data["total_conversions"] == 100


def test_03_cpa_zero_conversions_protection(client: TestClient, auth_headers: Dict[str, str], db_session: Session):
    """Bảo vệ chống chia cho 0: khi total_conversions == 0, cpa_avg phải trả về 0.0 không văng 500."""
    camp = Campaign(
        name="CPA Zero Conversions Campaign",
        workspace_id=1,
        owner_id=1,
        product_id=1,
        objective="Kiểm thử chia cho 0",
        audience="Đại chúng",
        start_date="2026-10-01",
        end_date="2026-10-31",
        budget=10000000.0,
        status="ACTIVE"
    )
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)

    # Thêm metric có chi phí nhưng 0 chuyển đổi
    metric = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-10-06",
        views=5000,
        clicks=200,
        conversions=0,
        cost=3000000.0,
        revenue=0.0
    )
    db_session.add(metric)
    db_session.commit()

    resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "cpa_avg" in data
    assert data["cpa_avg"] == 0.0
    assert data["total_conversions"] == 0


def test_04_cpa_zero_metrics_campaign(client: TestClient, auth_headers: Dict[str, str], db_session: Session):
    """Chiến dịch hoàn toàn chưa có số liệu (0 views, 0 cost, 0 conversions) -> cpa_avg == 0.0."""
    camp = Campaign(
        name="CPA Empty Campaign",
        workspace_id=1,
        owner_id=1,
        product_id=1,
        objective="Chiến dịch rỗng",
        audience="Đại chúng",
        start_date="2026-10-01",
        end_date="2026-10-31",
        budget=5000000.0,
        status="ACTIVE"
    )
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)

    resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["cpa_avg"] == 0.0
    assert data["total_cost"] == 0.0
    assert data["total_conversions"] == 0


def test_05_cpa_multi_channel_aggregation_and_rounding(client: TestClient, auth_headers: Dict[str, str], db_session: Session):
    """Tính toán CPA tổng hợp đa kênh và làm tròn 2 chữ số thập phân."""
    camp = Campaign(
        name="CPA Multi-Channel Campaign",
        workspace_id=1,
        owner_id=1,
        product_id=1,
        objective="Kiểm thử đa kênh",
        audience="Đại chúng",
        start_date="2026-10-01",
        end_date="2026-10-31",
        budget=50000000.0,
        status="ACTIVE"
    )
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)

    # Kênh 1: cost = 100, conversions = 3 -> 100 / 3 = 33.3333...
    m1 = CampaignMetric(
        campaign_id=camp.id,
        channel_id=1,
        metric_date="2026-10-07",
        views=1000,
        clicks=50,
        conversions=3,
        cost=100.0,
        revenue=300.0
    )
    db_session.add(m1)
    db_session.commit()

    resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["cpa_avg"] == 33.33


def test_06_dashboard_overview_includes_cpa(client: TestClient, auth_headers: Dict[str, str]):
    """Xác thực các endpoint dashboard tổng quan đều trả về cpa_avg trong KPI."""
    for path in ["/api/v1/analytics/dashboard", "/api/v1/metrics/dashboard", "/api/v1/metrics/overview"]:
        resp = client.get(path, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "kpi" in data
        assert "cpa_avg" in data["kpi"]
        assert isinstance(data["kpi"]["cpa_avg"], (int, float))
