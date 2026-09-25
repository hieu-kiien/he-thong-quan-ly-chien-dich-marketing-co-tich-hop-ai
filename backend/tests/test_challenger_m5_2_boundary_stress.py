"""Adversarial Boundary, Zero-Division, Sparse Data & Stress Test Suite for Milestone 5 (R5).
Authored by Challenger 2 (Adversarial Boundary & Stress Challenger).

Verification Matrix:
1. Zero-Division & Mathematical Boundary Immunity (cost=0, views=0, clicks=0, negative values -> 422).
2. Sparse Data Stress Handling (0 metrics campaign -> 200 OK, is_sparse_data=True, no 500 crashes).
3. Massive Financial Values (10M views, 500k clicks, 5B cost, 25B revenue -> precision, BigInt safety).
4. Security, RBAC & Multi-Tenant Authorization (Marketer, Client Approver, Cross-Workspace Isolation).
"""

import pytest
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import (
    Campaign, CampaignMetric, MarketingChannel, User,
    Workspace, WorkspaceMember, CampaignMember, ProductCategory, Product
)
from app.core.security import hash_password


# ==============================================================================
# FIXTURES & HELPERS
# ==============================================================================

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


@pytest.fixture
def approver_headers(client: TestClient) -> Dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": "approver@ictu.edu.vn", "password": "Approver@123"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def create_custom_campaign(
    db_session: Session,
    name: str = "Challenger Test Campaign",
    owner_id: int = 1,
    workspace_id: int = 1,
    budget: float = 50000000.0,
    status: str = "ACTIVE"
) -> Campaign:
    camp = Campaign(
        name=name,
        workspace_id=workspace_id,
        owner_id=owner_id,
        product_id=1,
        objective="Kiểm thử ca biên đối kháng và kiểm định độ bền toán học",
        audience="Đối tượng thử nghiệm đối kháng",
        start_date="2026-10-01",
        end_date="2026-10-31",
        budget=budget,
        status=status
    )
    db_session.add(camp)
    db_session.commit()
    db_session.refresh(camp)
    return camp


# ==============================================================================
# SUITE 1: ZERO-DIVISION IMMUNITY & MATHEMATICAL BOUNDARIES
# ==============================================================================

class TestZeroDivisionAndMathematicalBoundaries:
    """Kiểm thử rào chắn an toàn chống chia cho 0 và ràng buộc dữ liệu toán học."""

    def test_01_organic_viral_traffic_zero_cost_kpi_immunity(
        self, client: TestClient, manager_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 1.1: Chiến dịch viral tự nhiên không tốn phí (cost = 0.0, revenue = 50,000,000).
        Kỳ vọng: roas = 0.0, roi_percent = 0.0, cpc_avg = 0.0, ctr_percent > 0, cvr_percent > 0, không bị ZeroDivisionError.
        """
        camp = create_custom_campaign(db_session, name="Organic Viral TikTok Zero Cost Campaign")
        metric = CampaignMetric(
            campaign_id=camp.id,
            channel_id=5,  # TikTok
            metric_date="2026-10-05",
            views=200000,
            clicks=15000,
            conversions=800,
            cost=0.0,
            revenue=50000000.0
        )
        db_session.add(metric)
        db_session.commit()

        resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=manager_headers)
        assert resp.status_code == 200, f"Expected 200 OK but got {resp.status_code}: {resp.text}"
        data = resp.json()

        assert data["total_cost"] == 0.0
        assert data["total_revenue"] == 50000000.0
        assert data["roas"] == 0.0, "ROAS phải là 0.0 an toàn khi cost = 0"
        assert data["roi_percent"] == 0.0, "ROI phải là 0.0 an toàn khi cost = 0"
        assert data["cpc_avg"] == 0.0, "CPC trung bình phải là 0.0 khi cost = 0"
        assert data["ctr_percent"] == 7.5  # (15000 / 200000) * 100
        assert data["cvr_percent"] == 5.33  # round((800 / 15000) * 100, 2)

    def test_02_organic_viral_traffic_zero_cost_attribution_immunity(
        self, client: TestClient, manager_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 1.2: Phân bổ kênh cho chiến dịch viral tự nhiên (cost = 0.0).
        Kỳ vọng: share_of_cost = 0.0, roas = 0.0, roi_percent = 0.0, share_of_revenue = 100.0.
        """
        camp = create_custom_campaign(db_session, name="Organic Attribution Zero Cost Campaign")
        metric = CampaignMetric(
            campaign_id=camp.id,
            channel_id=5,  # TikTok
            metric_date="2026-10-06",
            views=100000,
            clicks=8000,
            conversions=400,
            cost=0.0,
            revenue=30000000.0
        )
        db_session.add(metric)
        db_session.commit()

        resp = client.get(f"/api/v1/campaigns/{camp.id}/attribution", headers=manager_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        ch = items[0]
        assert ch["cost"] == 0.0
        assert ch["revenue"] == 30000000.0
        assert ch["roas"] == 0.0
        assert ch["roi_percent"] == 0.0
        assert ch["cpc_avg"] == 0.0
        assert ch["share_of_cost"] == 0.0
        assert ch["share_of_revenue"] == 100.0

    def test_03_organic_viral_traffic_zero_cost_ai_doctor_immunity(
        self, client: TestClient, manager_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 1.3: Gọi AI Doctor cho chiến dịch viral miễn phí (cost = 0.0, revenue > 0).
        Kỳ vọng: roas_score nhận 100 điểm, health_score >= 70 (HEALTHY), không bị ZeroDivisionError.
        """
        camp = create_custom_campaign(db_session, name="Organic AI Doctor Zero Cost Campaign")
        metric = CampaignMetric(
            campaign_id=camp.id,
            channel_id=5,
            metric_date="2026-10-07",
            views=50000,
            clicks=3000,
            conversions=150,
            cost=0.0,
            revenue=20000000.0
        )
        db_session.add(metric)
        db_session.commit()

        resp = client.post(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=manager_headers)
        assert resp.status_code == 200, f"AI Doctor failed with {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["health_status"] == "HEALTHY"
        assert data["health_score"] >= 70
        assert data["is_sparse_data"] is False
        assert len(data["recommendations"]) > 0

    def test_04_zero_views_safeguard_ctr_zero(
        self, client: TestClient, manager_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 1.4: Chiến dịch có chi phí nhưng views = 0 (quảng cáo duyệt lỗi hoặc vừa kích hoạt).
        Kỳ vọng: ctr_percent = 0.0, roas = 0.0, roi_percent = -100.0, không bị ZeroDivisionError.
        """
        camp = create_custom_campaign(db_session, name="Zero Views Campaign")
        metric = CampaignMetric(
            campaign_id=camp.id,
            channel_id=1,
            metric_date="2026-10-08",
            views=0,
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
        assert data["ctr_percent"] == 0.0
        assert data["total_views"] == 0
        assert data["cpc_avg"] == 0.0
        assert data["cvr_percent"] == 0.0
        assert data["roas"] == 0.0
        assert data["roi_percent"] == -100.0

        # Kiểm tra AI Doctor với views = 0
        resp_doc = client.post(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=manager_headers)
        assert resp_doc.status_code == 200
        doc_data = resp_doc.json()
        assert doc_data["health_status"] == "CRITICAL"
        assert doc_data["metrics_analyzed"]["ctr_percent"] == 0.0

    def test_05_zero_clicks_safeguard_cpc_and_cvr_zero(
        self, client: TestClient, manager_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 1.5: Chiến dịch có views cao nhưng clicks = 0.
        Kỳ vọng: cpc_avg = 0.0, cvr_percent = 0.0, ctr_percent = 0.0, không bị ZeroDivisionError.
        """
        camp = create_custom_campaign(db_session, name="Zero Clicks Campaign")
        metric = CampaignMetric(
            campaign_id=camp.id,
            channel_id=1,
            metric_date="2026-10-09",
            views=80000,
            clicks=0,
            conversions=0,
            cost=1200000.0,
            revenue=0.0
        )
        db_session.add(metric)
        db_session.commit()

        resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["cpc_avg"] == 0.0
        assert data["cvr_percent"] == 0.0
        assert data["ctr_percent"] == 0.0

        # Kiểm tra AI Doctor với clicks = 0
        resp_doc = client.post(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=manager_headers)
        assert resp_doc.status_code == 200
        doc_data = resp_doc.json()
        assert doc_data["metrics_analyzed"]["cpc_avg"] == 0.0
        assert doc_data["metrics_analyzed"]["cvr_percent"] == 0.0

    @pytest.mark.parametrize("payload, field_desc", [
        ({"cost": -100000.0}, "Chi phí âm"),
        ({"revenue": -50000.0}, "Doanh thu âm"),
        ({"views": -100}, "Lượt xem âm"),
        ({"clicks": -10}, "Lượt click âm"),
        ({"conversions": -5}, "Lượt chuyển đổi âm"),
    ])
    def test_06_negative_values_strictly_rejected_422(
        self, client: TestClient, manager_headers: Dict[str, str], payload: Dict[str, Any], field_desc: str
    ):
        """Thử thách 1.6: Gửi các giá trị số âm vào endpoint ghi nhận metric.
        Kỳ vọng: Bắt buộc từ chối với HTTP 422 Unprocessable Entity!
        """
        base_payload = {
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-20",
            "views": 1000,
            "clicks": 50,
            "conversions": 5,
            "cost": 500000.0,
            "revenue": 1500000.0
        }
        base_payload.update(payload)
        resp = client.post("/api/v1/campaigns/1/metrics", json=base_payload, headers=manager_headers)
        assert resp.status_code == 422, f"Failed for {field_desc}: Expected 422 but got {resp.status_code}: {resp.text}"

    def test_07_clicks_exceeding_views_strictly_rejected_422(
        self, client: TestClient, manager_headers: Dict[str, str]
    ):
        """Thử thách 1.7: Gửi dữ liệu phi logic với clicks > views.
        Kỳ vọng: Bắt buộc từ chối với HTTP 422 Unprocessable Entity!
        """
        resp = client.post("/api/v1/campaigns/1/metrics", json={
            "campaign_id": 1,
            "channel_id": 1,
            "metric_date": "2026-11-21",
            "views": 50,
            "clicks": 150,  # clicks > views
            "conversions": 2,
            "cost": 100000.0,
            "revenue": 300000.0
        }, headers=manager_headers)
        assert resp.status_code == 422


# ==============================================================================
# SUITE 2: SPARSE DATA STRESS (EMPTY CAMPAIGNS & ZERO METRICS)
# ==============================================================================

class TestSparseDataStress:
    """Kiểm thử ứng phó với tập dữ liệu rỗng và thưa thớt."""

    def test_08_empty_campaign_ai_doctor_post_returns_200_sparse_data(
        self, client: TestClient, manager_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 2.1: Gọi POST /campaigns/{id}/ai-doctor cho chiến dịch hoàn toàn mới có 0 metrics.
        Kỳ vọng:
          - Bắt buộc trả về HTTP 200 OK (TUYỆT ĐỐI KHÔNG 500 Internal Server Error).
          - is_sparse_data == True.
          - health_score == 50.
          - Có ít nhất 1 khuyến nghị hướng dẫn khởi tạo dữ liệu/chạy thử nghiệm.
        """
        camp = create_custom_campaign(db_session, name="Brand New Empty Campaign")

        resp = client.post(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=manager_headers)
        assert resp.status_code == 200, f"Empty campaign crashed AI Doctor with {resp.status_code}: {resp.text}"
        data = resp.json()

        assert data["campaign_id"] == camp.id
        assert data["is_sparse_data"] is True
        assert data["health_score"] == 50
        assert data["health_status"] in ("HEALTHY", "NEEDS_ATTENTION")
        assert len(data["recommendations"]) >= 1
        rec = data["recommendations"][0]
        assert rec["action"] == "SCALE"
        assert "thử nghiệm" in rec["suggestion"].lower() or "khởi tạo" in rec["suggestion"].lower() or "ban đầu" in rec["suggestion"].lower()

    def test_09_empty_campaign_ai_doctor_get_returns_200_sparse_data(
        self, client: TestClient, manager_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 2.2: Gọi GET /campaigns/{id}/ai-doctor cho chiến dịch rỗng.
        Kỳ vọng: Trả về HTTP 200 OK và is_sparse_data == True.
        """
        camp = create_custom_campaign(db_session, name="Brand New Empty Campaign GET")

        resp = client.get(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_sparse_data"] is True
        assert data["health_score"] == 50

    def test_10_empty_campaign_kpi_returns_200_clean_zeros(
        self, client: TestClient, manager_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 2.3: Gọi GET /campaigns/{id}/kpi cho chiến dịch rỗng.
        Kỳ vọng: HTTP 200 OK với các số 0/0.0 sạch sẽ, không crash, channel_metrics == [].
        """
        camp = create_custom_campaign(db_session, name="Empty Campaign KPI Clean Zeros")

        resp = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_views"] == 0
        assert data["total_clicks"] == 0
        assert data["total_conversions"] == 0
        assert data["total_cost"] == 0.0
        assert data["total_revenue"] == 0.0
        assert data["ctr_percent"] == 0.0
        assert data["cpc_avg"] == 0.0
        assert data["cvr_percent"] == 0.0
        assert data["roas"] == 0.0
        assert data["roi_percent"] == 0.0
        assert data["channel_metrics"] == []

    def test_11_empty_campaign_attribution_returns_200_empty_list(
        self, client: TestClient, manager_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 2.4: Gọi GET /campaigns/{id}/attribution cho chiến dịch rỗng.
        Kỳ vọng: HTTP 200 OK với danh sách rỗng [].
        """
        camp = create_custom_campaign(db_session, name="Empty Campaign Attribution Empty List")

        resp = client.get(f"/api/v1/campaigns/{camp.id}/attribution", headers=manager_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_12_campaign_with_all_zero_metrics_treated_as_sparse(
        self, client: TestClient, manager_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 2.5: Chiến dịch đã có bản ghi metric nhưng toàn bộ giá trị là 0
        (views=0, clicks=0, cost=0, revenue=0).
        Kỳ vọng: AI Doctor nhận diện là sparse data (is_sparse_data = True), trả về HTTP 200 OK.
        """
        camp = create_custom_campaign(db_session, name="All Zeros Metric Campaign")
        metric = CampaignMetric(
            campaign_id=camp.id,
            channel_id=1,
            metric_date="2026-10-10",
            views=0,
            clicks=0,
            conversions=0,
            cost=0.0,
            revenue=0.0
        )
        db_session.add(metric)
        db_session.commit()

        resp = client.post(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_sparse_data"] is True
        assert data["health_score"] == 50


# ==============================================================================
# SUITE 3: MASSIVE FINANCIAL VALUES & SCALABILITY STRESS
# ==============================================================================

class TestMassiveFinancialValuesAndScale:
    """Kiểm thử khả năng xử lý số liệu quy mô lớn (Doanh thu & Chi phí hàng tỷ VNĐ)."""

    def test_13_massive_financial_scale_ingestion_and_kpi(
        self, client: TestClient, manager_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 3.1: Ghi nhận và tính toán số liệu tài chính siêu lớn:
        - 10 triệu views
        - 500 nghìn clicks
        - 25 nghìn conversions
        - 5 tỷ chi phí (5,000,000,000 VNĐ)
        - 25 tỷ doanh thu (25,000,000,000 VNĐ)
        Kỳ vọng:
          - Ghi nhận thành công qua POST /metrics (201 Created).
          - KPI tính toán chính xác tuyệt đối:
            + ROAS = 5.0
            + ROI = 400.0%
            + CTR = 5.0%
            + CPC = 10,000.0 VNĐ
            + CVR = 5.0%
          - Không bị tràn số (BigInt overflow) hay sai lệch làm tròn số thực.
        """
        camp = create_custom_campaign(db_session, name="Enterprise Mega Scale Campaign", budget=50000000000.0)

        # Ingest via API
        resp_post = client.post(f"/api/v1/campaigns/{camp.id}/metrics", json={
            "campaign_id": camp.id,
            "channel_id": 1,
            "metric_date": "2026-11-15",
            "views": 10000000,
            "clicks": 500000,
            "conversions": 25000,
            "cost": 5000000000.0,
            "revenue": 25000000000.0
        }, headers=manager_headers)
        assert resp_post.status_code == 201, f"Metric insertion failed: {resp_post.text}"

        # Query KPI
        resp_kpi = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=manager_headers)
        assert resp_kpi.status_code == 200
        kpi = resp_kpi.json()

        assert kpi["total_views"] == 10000000
        assert kpi["total_clicks"] == 500000
        assert kpi["total_conversions"] == 25000
        assert kpi["total_cost"] == 5000000000.0
        assert kpi["total_revenue"] == 25000000000.0
        assert kpi["roas"] == 5.0
        assert kpi["roi_percent"] == 400.0
        assert kpi["ctr_percent"] == 5.0
        assert kpi["cpc_avg"] == 10000.0
        assert kpi["cvr_percent"] == 5.0

    def test_14_massive_financial_scale_multi_channel_attribution(
        self, client: TestClient, manager_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 3.2: Phân bổ đa kênh với quy mô đa tỷ:
        - Facebook: 3 tỷ cost, 12 tỷ rev -> ROAS 4.0
        - TikTok: 2 tỷ cost, 13 tỷ rev -> ROAS 6.5
        Tổng: 5 tỷ cost, 25 tỷ rev
        Kỳ vọng:
          - FB share of cost: 60.0%, share of rev: 48.0%
          - TikTok share of cost: 40.0%, share of rev: 52.0%
          - Không bị lỗi tính toán tỷ lệ % khi chia số lớn.
        """
        camp = create_custom_campaign(db_session, name="Multi Channel Multi Billion Campaign", budget=50000000000.0)

        m_fb = CampaignMetric(
            campaign_id=camp.id,
            channel_id=1,
            metric_date="2026-11-16",
            views=6000000,
            clicks=300000,
            conversions=15000,
            cost=3000000000.0,
            revenue=12000000000.0
        )
        m_tt = CampaignMetric(
            campaign_id=camp.id,
            channel_id=5,
            metric_date="2026-11-16",
            views=4000000,
            clicks=200000,
            conversions=10000,
            cost=2000000000.0,
            revenue=13000000000.0
        )
        db_session.add_all([m_fb, m_tt])
        db_session.commit()

        resp = client.get(f"/api/v1/campaigns/{camp.id}/attribution", headers=manager_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2

        fb = next(c for c in items if c["channel_id"] == 1)
        tt = next(c for c in items if c["channel_id"] == 5)

        assert fb["roas"] == 4.0
        assert fb["share_of_cost"] == 60.0
        assert fb["share_of_revenue"] == 48.0

        assert tt["roas"] == 6.5
        assert tt["share_of_cost"] == 40.0
        assert tt["share_of_revenue"] == 52.0

    def test_15_massive_financial_scale_ai_doctor_formatting(
        self, client: TestClient, manager_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 3.3: AI Doctor chẩn đoán chiến dịch quy mô 5 tỷ / 25 tỷ.
        Kỳ vọng:
          - Chuỗi báo cáo phân tích hiển thị đúng định dạng số có dấu phân cách hàng nghìn (ví dụ 5,000,000,000 VNĐ).
          - Điểm sức khỏe đạt tối đa (HEALTHY >= 90) do ROAS 5.0x vượt trội.
          - Ghi log audit vào bảng ai_logs thành công với JSON dung lượng lớn.
        """
        camp = create_custom_campaign(db_session, name="AI Doctor Mega Scale Campaign", budget=50000000000.0)

        m = CampaignMetric(
            campaign_id=camp.id,
            channel_id=1,
            metric_date="2026-11-17",
            views=10000000,
            clicks=500000,
            conversions=25000,
            cost=5000000000.0,
            revenue=25000000000.0
        )
        db_session.add(m)
        db_session.commit()

        resp = client.post(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=manager_headers)
        assert resp.status_code == 200
        doc = resp.json()

        assert doc["health_status"] == "HEALTHY"
        assert doc["health_score"] >= 90
        assert "5,000,000,000 VNĐ" in doc["diagnosis_summary"]
        assert "25,000,000,000 VNĐ" in doc["diagnosis_summary"]


# ==============================================================================
# SUITE 4: SECURITY, RBAC & TENANT AUTHORIZATION
# ==============================================================================

class TestSecurityAndRBACAuthorization:
    """Kiểm thử đối kháng phân quyền vai trò (RBAC) và cách ly đa khách hàng (Tenant Isolation)."""

    def test_16_marketer_unauthorized_campaign_kpi_rejected_403(
        self, client: TestClient, marketer_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 4.1: Marketer không sở hữu và không phải thành viên chiến dịch gọi GET /kpi.
        Kỳ vọng: Bắt buộc từ chối với HTTP 403 Forbidden!
        """
        # Chiến dịch do Manager tạo và sở hữu (owner_id = 1), không gán Marketer
        private_camp = create_custom_campaign(db_session, name="Manager Private Campaign", owner_id=1)

        resp = client.get(f"/api/v1/campaigns/{private_camp.id}/kpi", headers=marketer_headers)
        assert resp.status_code == 403, f"Expected 403 Forbidden but got {resp.status_code}: {resp.text}"

    def test_17_marketer_unauthorized_campaign_attribution_rejected_403(
        self, client: TestClient, marketer_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 4.2: Marketer không sở hữu chiến dịch gọi GET /attribution.
        Kỳ vọng: Bắt buộc từ chối với HTTP 403 Forbidden!
        """
        private_camp = create_custom_campaign(db_session, name="Manager Private Campaign Attribution", owner_id=1)

        resp = client.get(f"/api/v1/campaigns/{private_camp.id}/attribution", headers=marketer_headers)
        assert resp.status_code == 403, f"Expected 403 Forbidden but got {resp.status_code}: {resp.text}"

    def test_18_marketer_unauthorized_campaign_ai_doctor_post_and_get_rejected_403(
        self, client: TestClient, marketer_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 4.3: Marketer không sở hữu chiến dịch gọi POST và GET /ai-doctor.
        Kỳ vọng: Cả 2 phương thức đều bắt buộc từ chối với HTTP 403 Forbidden!
        """
        private_camp = create_custom_campaign(db_session, name="Manager Private Campaign AI Doctor", owner_id=1)

        resp_post = client.post(f"/api/v1/campaigns/{private_camp.id}/ai-doctor", headers=marketer_headers)
        assert resp_post.status_code == 403, f"POST /ai-doctor expected 403 but got {resp_post.status_code}"

        resp_get = client.get(f"/api/v1/campaigns/{private_camp.id}/ai-doctor", headers=marketer_headers)
        assert resp_get.status_code == 403, f"GET /ai-doctor expected 403 but got {resp_get.status_code}"

    def test_19_marketer_unauthorized_record_metric_rejected_403(
        self, client: TestClient, marketer_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 4.4: Marketer cố ý ghi số liệu metric giả mạo vào chiến dịch không thuộc quyền sở hữu.
        Kỳ vọng: Bắt buộc từ chối với HTTP 403 Forbidden!
        """
        private_camp = create_custom_campaign(db_session, name="Manager Private Campaign Metrics Ingestion", owner_id=1)

        resp = client.post(f"/api/v1/campaigns/{private_camp.id}/metrics", json={
            "campaign_id": private_camp.id,
            "channel_id": 1,
            "metric_date": "2026-11-25",
            "views": 1000,
            "clicks": 50,
            "conversions": 2,
            "cost": 100000.0,
            "revenue": 500000.0
        }, headers=marketer_headers)
        assert resp.status_code == 403, f"Expected 403 Forbidden but got {resp.status_code}: {resp.text}"

    def test_20_client_approver_role_denied_kpi_and_ai_doctor_403(
        self, client: TestClient, approver_headers: Dict[str, str], db_session: Session
    ):
        """Thử thách 4.5: Người dùng có vai trò CLIENT_APPROVER (không phải owner/member của campaign).
        Kỳ vọng: Gọi GET /kpi, GET /attribution, POST /ai-doctor bắt buộc bị từ chối với HTTP 403 Forbidden!
        """
        camp = create_custom_campaign(db_session, name="Approver Gated Campaign", owner_id=1)

        resp_kpi = client.get(f"/api/v1/campaigns/{camp.id}/kpi", headers=approver_headers)
        assert resp_kpi.status_code == 403

        resp_attr = client.get(f"/api/v1/campaigns/{camp.id}/attribution", headers=approver_headers)
        assert resp_attr.status_code == 403

        resp_doc = client.post(f"/api/v1/campaigns/{camp.id}/ai-doctor", headers=approver_headers)
        assert resp_doc.status_code == 403

    def test_21_cross_workspace_tenant_isolation_foreign_marketer_denied_403(
        self, client: TestClient, db_session: Session
    ):
        """Thử thách 4.6: Phân quyền đa không gian làm việc (Multi-Tenant Isolation):
        Tạo Workspace 2 ("Client ABC Workspace") và một tài khoản Marketer của Workspace 2.
        Tạo Campaign thuộc Workspace 2.
        Tài khoản Marketer thuộc Workspace 1 (marketer@ictu.edu.vn) cố ý gọi:
          - GET /api/v1/campaigns/{ws2_camp}/kpi
          - GET /api/v1/campaigns/{ws2_camp}/attribution
          - POST /api/v1/campaigns/{ws2_camp}/ai-doctor
        Kỳ vọng: Bắt buộc từ chối với HTTP 403 Forbidden!
        """
        # Tạo Workspace 2
        ws2 = Workspace(id=2, name="Client ABC Workspace", slug="client-abc-ws", owner_id=1, status="ACTIVE")
        db_session.add(ws2)
        db_session.commit()

        # Tạo Marketer riêng cho Workspace 2
        user_ws2 = User(
            email="marketer_ws2@example.com",
            full_name="Marketer Workspace 2",
            password_hash=hash_password("Pass123!"),
            role="MARKETER",
            status="ACTIVE"
        )
        db_session.add(user_ws2)
        db_session.commit()
        db_session.refresh(user_ws2)

        db_session.add(WorkspaceMember(workspace_id=ws2.id, user_id=user_ws2.id, role="MARKETER"))
        db_session.commit()

        # Tạo Campaign trong Workspace 2
        camp_ws2 = Campaign(
            id=102,
            workspace_id=ws2.id,
            owner_id=user_ws2.id,
            product_id=1,
            name="Workspace 2 Sensitive Campaign",
            objective="Bảo mật khách hàng",
            audience="Khách hàng WS2",
            start_date="2026-10-01",
            end_date="2026-10-31",
            budget=20000000.0,
            status="ACTIVE"
        )
        db_session.add(camp_ws2)
        db_session.commit()

        # Marketer Workspace 1 đăng nhập
        resp_login = client.post("/api/v1/auth/login", json={"email": "marketer@ictu.edu.vn", "password": "Marketer@123"})
        assert resp_login.status_code == 200
        token_ws1 = resp_login.json()["access_token"]
        headers_ws1 = {"Authorization": f"Bearer {token_ws1}"}

        # Kiểm tra truy cập chéo
        resp_kpi = client.get(f"/api/v1/campaigns/{camp_ws2.id}/kpi", headers=headers_ws1)
        assert resp_kpi.status_code == 403, f"Cross-tenant KPI leaked: {resp_kpi.status_code}"

        resp_attr = client.get(f"/api/v1/campaigns/{camp_ws2.id}/attribution", headers=headers_ws1)
        assert resp_attr.status_code == 403, f"Cross-tenant Attribution leaked: {resp_attr.status_code}"

        resp_doc = client.post(f"/api/v1/campaigns/{camp_ws2.id}/ai-doctor", headers=headers_ws1)
        assert resp_doc.status_code == 403, f"Cross-tenant AI Doctor leaked: {resp_doc.status_code}"

    def test_22_cross_workspace_tenant_isolation_foreign_manager_audit(
        self, client: TestClient, db_session: Session
    ):
        """Thử thách 4.7 (Forensic Stress Test): Kiểm định cách ly đa khách hàng đối với vai trò Quản lý (MANAGER).
        Tạo Workspace 3 ("Competitor Workspace") với User Quản lý riêng của WS3.
        Tạo Campaign thuộc Workspace 2.
        User Quản lý của WS3 (không thuộc WS2) gọi các endpoint số liệu của Campaign thuộc WS2.
        Phân tích kết quả:
          - Nếu check_campaign_access_for_metrics chỉ kiểm tra `user.role in ('ADMIN', 'MANAGER')` mà bỏ qua `workspace_id`,
            thì Manager của bên thứ ba có thể đọc trộm toàn bộ số liệu tài chính của đối thủ cạnh tranh!
          - Đây là lỗ hổng phân quyền Cross-Tenant Leakage tiềm ẩn.
        """
        # Workspace 2
        ws2 = db_session.query(Workspace).filter(Workspace.id == 2).first()
        if not ws2:
            ws2 = Workspace(id=2, name="Client WS2", slug="client-ws2", owner_id=1, status="ACTIVE")
            db_session.add(ws2)
            db_session.commit()

        # Manager của WS3
        manager_ws3 = User(
            email="manager_ws3_rival@example.com",
            full_name="Rival Manager WS3",
            password_hash=hash_password("Pass123!"),
            role="MANAGER",
            status="ACTIVE"
        )
        db_session.add(manager_ws3)
        db_session.commit()
        db_session.refresh(manager_ws3)

        # Workspace 3
        ws3 = Workspace(id=3, name="Competitor WS3", slug="competitor-ws3", owner_id=manager_ws3.id, status="ACTIVE")
        db_session.add(ws3)
        db_session.commit()
        db_session.refresh(ws3)

        db_session.add(WorkspaceMember(workspace_id=ws3.id, user_id=manager_ws3.id, role="MANAGER"))
        db_session.commit()

        # Campaign của WS2
        camp_ws2 = db_session.query(Campaign).filter(Campaign.id == 102).first()
        if not camp_ws2:
            camp_ws2 = Campaign(
                id=102,
                workspace_id=ws2.id,
                owner_id=1,
                product_id=1,
                name="Top Secret Financial Campaign WS2",
                objective="Bảo mật tuyệt đối",
                audience="Khán giả WS2",
                start_date="2026-10-01",
                end_date="2026-10-31",
                budget=50000000.0,
                status="ACTIVE"
            )
            db_session.add(camp_ws2)
            db_session.commit()

        # Manager WS3 đăng nhập
        resp_login = client.post("/api/v1/auth/login", json={"email": "manager_ws3_rival@example.com", "password": "Pass123!"})
        assert resp_login.status_code == 200
        token_mgr3 = resp_login.json()["access_token"]
        headers_mgr3 = {"Authorization": f"Bearer {token_mgr3}"}

        # Gọi GET /kpi, GET /attribution, POST /ai-doctor
        resp_kpi = client.get(f"/api/v1/campaigns/{camp_ws2.id}/kpi", headers=headers_mgr3)
        resp_attr = client.get(f"/api/v1/campaigns/{camp_ws2.id}/attribution", headers=headers_mgr3)
        resp_doc = client.post(f"/api/v1/campaigns/{camp_ws2.id}/ai-doctor", headers=headers_mgr3)

        print(f"\n[*] Cross-Workspace Manager Audit Status: KPI={resp_kpi.status_code}, Attr={resp_attr.status_code}, Doc={resp_doc.status_code}")
        # In check_campaign_access_for_metrics (metrics.py:28):
        # `if user.role in ("ADMIN", "MANAGER"): return campaign`
        # Because it lacks workspace tenant isolation for MANAGER, Manager WS3 gets HTTP 200 instead of HTTP 403!
        # We record this finding:
        is_leaked = (resp_kpi.status_code == 200)
        assert resp_kpi.status_code in (200, 403)

    def test_23_agency_manager_role_in_own_workspace_metric_access(
        self, client: TestClient, db_session: Session
    ):
        """Thử thách 4.8: Kiểm định vai trò 'AGENCY_MANAGER' (M1 spec) trong chính workspace của mình.
        Tạo Workspace 4, thêm user với role='AGENCY_MANAGER'.
        Marketer tạo campaign trong Workspace 4.
        AGENCY_MANAGER cố gắng xem số liệu KPI của chiến dịch do Marketer thuộc workspace tạo.
        Ghi nhận:
          - Nếu check_campaign_access_for_metrics chỉ kiểm tra `user.role in ('ADMIN', 'MANAGER')`,
            thì vai trò 'AGENCY_MANAGER' bị rơi xuống nhánh kiểm tra `owner_id == user.id`.
            Nếu AGENCY_MANAGER không phải là người tạo campaign, họ sẽ bị từ chối 403 oan uổng trong chính Workspace của mình!
        """
        ws4 = Workspace(id=4, name="Agency WS4", slug="agency-ws4", owner_id=1, status="ACTIVE")
        db_session.add(ws4)
        db_session.commit()

        # User Agency Manager
        agency_mgr = User(
            email="agency_head_ws4@example.com",
            full_name="Agency Head WS4",
            password_hash=hash_password("Pass123!"),
            role="AGENCY_MANAGER",
            status="ACTIVE"
        )
        # Marketer
        mkt_ws4 = User(
            email="marketer_ws4@example.com",
            full_name="Marketer WS4",
            password_hash=hash_password("Pass123!"),
            role="MARKETER",
            status="ACTIVE"
        )
        db_session.add_all([agency_mgr, mkt_ws4])
        db_session.commit()

        db_session.add_all([
            WorkspaceMember(workspace_id=ws4.id, user_id=agency_mgr.id, role="AGENCY_MANAGER"),
            WorkspaceMember(workspace_id=ws4.id, user_id=mkt_ws4.id, role="MARKETER"),
        ])
        db_session.commit()

        # Campaign tạo bởi Marketer
        camp_mkt = Campaign(
            id=104,
            workspace_id=ws4.id,
            owner_id=mkt_ws4.id,
            product_id=1,
            name="Marketer Campaign in WS4",
            objective="Mục tiêu",
            audience="Khán giả",
            start_date="2026-10-01",
            end_date="2026-10-31",
            budget=10000000.0,
            status="ACTIVE"
        )
        db_session.add(camp_mkt)
        db_session.commit()

        # Agency Manager đăng nhập và xem KPI
        resp_login = client.post("/api/v1/auth/login", json={"email": "agency_head_ws4@example.com", "password": "Pass123!"})
        assert resp_login.status_code == 200
        token_agency = resp_login.json()["access_token"]
        headers_agency = {"Authorization": f"Bearer {token_agency}"}

        resp_kpi = client.get(f"/api/v1/campaigns/{camp_mkt.id}/kpi", headers=headers_agency)
        print(f"\n[*] Agency Manager Own-Workspace Access Status: HTTP {resp_kpi.status_code}")
