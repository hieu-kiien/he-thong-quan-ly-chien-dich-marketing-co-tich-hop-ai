"""Workstream C — KPI: duplicate validation + kpi-progress (target vs actual)."""

from datetime import datetime, timedelta

from app.models.entities import CampaignMetric, CampaignKPITarget


def test_kpi_duplicate_metric_name_rejected(client, manager_headers):
    """metric_name trùng (không phân biệt hoa thường) → 400 thay vì IntegrityError 500."""
    res = client.put(
        "/api/v1/campaigns/1/kpi-targets",
        json=[
            {"metric_name": "CTR", "target_value": 3.0, "unit": "%"},
            {"metric_name": "ctr", "target_value": 4.0, "unit": "%"},
        ],
        headers=manager_headers,
    )
    assert res.status_code == 400
    assert "trùng lặp" in res.json()["detail"]


def test_kpi_targets_unique_ok(client, manager_headers):
    res = client.put(
        "/api/v1/campaigns/1/kpi-targets",
        json=[
            {"metric_name": "CTR", "target_value": 3.5, "unit": "%"},
            {"metric_name": "Conversions", "target_value": 150.0, "unit": "count"},
            {"metric_name": "ROAS", "target_value": 4.0, "unit": "ratio"},
        ],
        headers=manager_headers,
    )
    assert res.status_code == 200, res.text
    assert len(res.json()) == 3


def test_kpi_progress_computes_achieved_pct(client, manager_headers, db_session):
    """Target CTR với actual từ tổng metrics → achieved_pct đúng tỉ lệ; metric lạ = không đo được.

    Seed đã có metrics cho campaign 1 nên test theo baseline (trừ metrics sẵn có)
    thay vì cộng dồn absolute.
    """
    from sqlalchemy import func as sa_func

    base_views, base_clicks, base_conv = db_session.query(
        sa_func.coalesce(sa_func.sum(CampaignMetric.views), 0),
        sa_func.coalesce(sa_func.sum(CampaignMetric.clicks), 0),
        sa_func.coalesce(sa_func.sum(CampaignMetric.conversions), 0),
    ).filter(CampaignMetric.campaign_id == 1).one()

    # Thêm metrics làm CTR=10% TRÊN baseline: chọn views/clicks để tổng đạt tỉ lệ gọn.
    # Đơn giản: thêm 1000 views + 100 clicks → CTR mới = (base_clicks+100)/(base_views+1000).
    d1 = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")
    db_session.add(CampaignMetric(
        campaign_id=1, channel_id=1, metric_date=d1,
        views=1000, clicks=100, conversions=50, cost=1_000_000.0, revenue=4_000_000.0,
    ))
    db_session.commit()

    exp_views = int(base_views) + 1000
    exp_clicks = int(base_clicks) + 100
    exp_conv = int(base_conv) + 50
    exp_ctr = round(100.0 * exp_clicks / exp_views, 2)

    put = client.put(
        "/api/v1/campaigns/1/kpi-targets",
        json=[
            {"metric_name": "CTR", "target_value": 2.0, "unit": "%"},
            {"metric_name": "Conversions", "target_value": 100.0, "unit": "count"},
            {"metric_name": "MysteryMetric", "target_value": 10.0, "unit": "x"},
        ],
        headers=manager_headers,
    )
    assert put.status_code == 200, put.text

    res = client.get("/api/v1/campaigns/1/kpi-progress", headers=manager_headers)
    assert res.status_code == 200, res.text
    data = res.json()

    by_name = {t["metric_name"]: t for t in data["targets"]}
    assert by_name["CTR"]["actual_value"] == exp_ctr
    assert by_name["CTR"]["achieved_pct"] == round(100.0 * exp_ctr / 2.0, 2)
    assert by_name["CTR"]["measurable"] is True

    assert by_name["Conversions"]["actual_value"] == float(exp_conv)
    assert by_name["Conversions"]["achieved_pct"] == round(100.0 * exp_conv / 100.0, 2)

    # Metric lạ → không đo được, không bịa
    assert by_name["MysteryMetric"]["actual_value"] is None
    assert by_name["MysteryMetric"]["achieved_pct"] is None
    assert by_name["MysteryMetric"]["measurable"] is False

    assert data["measurable_count"] == 2
    assert data["total_count"] == 3
    expected_overall = round(
        (round(100.0 * exp_ctr / 2.0, 2) + round(100.0 * exp_conv / 100.0, 2)) / 2, 2
    )
    assert data["overall_achieved_pct"] == expected_overall


def test_kpi_progress_no_metrics_no_division_by_zero(client, manager_headers):
    """Chưa có metrics → actual None/0 an toàn, không 500."""
    res = client.get("/api/v1/campaigns/2/kpi-progress", headers=manager_headers)
    assert res.status_code == 200, res.text
    assert res.json()["overall_achieved_pct"] is None or res.json()["targets"] == []


def test_kpi_progress_cross_tenant(client, beta_marketer_headers):
    res = client.get("/api/v1/campaigns/1/kpi-progress", headers=beta_marketer_headers)
    assert res.status_code in (403, 404)


def test_kpi_progress_unauthenticated(client):
    assert client.get("/api/v1/campaigns/1/kpi-progress").status_code == 401


def test_kpi_progress_roas_and_revenue_mapping(client, manager_headers, db_session):
    """ROAS = revenue/cost, revenue = tổng doanh thu — map đúng đơn vị."""
    d1 = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    db_session.add(CampaignMetric(
        campaign_id=2, channel_id=1, metric_date=d1,
        views=500, clicks=50, conversions=10, cost=2_000_000.0, revenue=8_000_000.0,
    ))
    db_session.commit()

    put = client.put(
        "/api/v1/campaigns/2/kpi-targets",
        json=[
            {"metric_name": "ROAS", "target_value": 3.0, "unit": "ratio"},
            {"metric_name": "Revenue", "target_value": 6_000_000.0, "unit": "vnd"},
        ],
        headers=manager_headers,
    )
    assert put.status_code == 200, put.text

    res = client.get("/api/v1/campaigns/2/kpi-progress", headers=manager_headers)
    assert res.status_code == 200
    by_name = {t["metric_name"]: t for t in res.json()["targets"]}
    assert by_name["ROAS"]["actual_value"] == 4.0
    assert by_name["ROAS"]["achieved_pct"] == round(100.0 * 4.0 / 3.0, 2)
    assert by_name["Revenue"]["actual_value"] == 8_000_000.0
    assert by_name["Revenue"]["achieved_pct"] == round(100.0 * 8_000_000.0 / 6_000_000.0, 2)
