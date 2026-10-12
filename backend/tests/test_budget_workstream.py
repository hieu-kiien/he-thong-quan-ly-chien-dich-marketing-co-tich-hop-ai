"""Workstream B — Budget: validation phân bổ + budget summary (spent tracking)."""

from datetime import datetime, timedelta

from app.models.entities import CampaignMetric, MarketingChannel


def _channels(db_session):
    rows = db_session.query(MarketingChannel).order_by(MarketingChannel.id).limit(2).all()
    assert len(rows) == 2, "seed phải có ít nhất 2 kênh"
    return rows[0], rows[1]


def test_allocations_cannot_exceed_campaign_budget(client, manager_headers):
    """Tổng phân bổ > budget → 400 với thông báo rõ ràng (không silently ghi)."""
    res = client.put(
        "/api/v1/campaigns/1/budget-allocations",
        json=[
            {"channel_id": 1, "planned_amount": 10_000_000.0},
            {"channel_id": 2, "planned_amount": 10_000_000.0},
        ],
        headers=manager_headers,
    )
    # Campaign 1 seed budget = 15M → 20M phải bị chặn
    assert res.status_code == 400, res.text
    assert "vượt ngân sách" in res.json()["detail"]


def test_allocations_duplicate_channel_rejected(client, manager_headers):
    res = client.put(
        "/api/v1/campaigns/1/budget-allocations",
        json=[
            {"channel_id": 1, "planned_amount": 1_000_000.0},
            {"channel_id": 1, "planned_amount": 2_000_000.0},
        ],
        headers=manager_headers,
    )
    assert res.status_code == 400
    assert "trùng lặp" in res.json()["detail"]


def test_allocations_within_budget_ok(client, manager_headers, db_session):
    ch1, ch2 = _channels(db_session)
    res = client.put(
        "/api/v1/campaigns/1/budget-allocations",
        json=[
            {"channel_id": ch1.id, "planned_amount": 9_000_000.0},
            {"channel_id": ch2.id, "planned_amount": 6_000_000.0},
        ],
        headers=manager_headers,
    )
    assert res.status_code == 200, res.text
    total = sum(a["planned_amount"] for a in res.json())
    assert total == 15_000_000.0  # đúng bằng budget = hợp lệ


def test_budget_summary_spent_tracking(client, manager_headers, db_session):
    """budget-summary trả allocated (kế hoạch) và spent (SUM cost từ metrics) thật."""
    ch1, ch2 = _channels(db_session)

    # Phân bổ 9M + 6M (= budget 15M)
    put = client.put(
        "/api/v1/campaigns/1/budget-allocations",
        json=[
            {"channel_id": ch1.id, "planned_amount": 9_000_000.0},
            {"channel_id": ch2.id, "planned_amount": 6_000_000.0},
        ],
        headers=manager_headers,
    )
    assert put.status_code == 200

    # Ghi thêm 3 dòng metrics: channel1 +1.5M/0.5M, channel2 +2M → spent tăng 4M
    # (seed đã có metrics sẵn cho campaign 1 nên test theo delta, không cộng dồn absolute).
    baseline = sum(
        float(c or 0)
        for (c,) in db_session.query(CampaignMetric.cost)
        .filter(CampaignMetric.campaign_id == 1)
        .all()
    )
    d1 = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
    d2 = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    db_session.add_all([
        CampaignMetric(campaign_id=1, channel_id=ch1.id, metric_date=d1,
                       views=1000, clicks=100, conversions=10, cost=1_500_000.0, revenue=5_000_000.0),
        CampaignMetric(campaign_id=1, channel_id=ch1.id, metric_date=d2,
                       views=500, clicks=50, conversions=5, cost=500_000.0, revenue=2_000_000.0),
        CampaignMetric(campaign_id=1, channel_id=ch2.id, metric_date=d1,
                       views=800, clicks=40, conversions=4, cost=2_000_000.0, revenue=3_000_000.0),
    ])
    db_session.commit()

    res = client.get("/api/v1/campaigns/1/budget-summary", headers=manager_headers)
    assert res.status_code == 200, res.text
    data = res.json()

    expected_spent = baseline + 4_000_000.0
    assert data["campaign_id"] == 1
    assert data["total_budget"] == 15_000_000.0
    assert data["total_allocated"] == 15_000_000.0
    assert data["total_spent"] == expected_spent
    assert data["unallocated_amount"] == 0.0
    assert round(data["remaining_amount"], 2) == round(15_000_000.0 - expected_spent, 2)
    assert data["allocated_pct"] == 100.0
    assert data["spent_pct"] == round(100.0 * expected_spent / 15_000_000.0, 2)

    # Spend theo kênh: delta của 2 kênh test = 2M + 2M (seed metrics kênh khác
    # không rơi vào 2 kênh này hoặc được gộp — chỉ assert delta không giảm).
    by_ch = {c["channel_id"]: c for c in data["channels"]}
    assert by_ch[ch1.id]["planned_amount"] == 9_000_000.0
    assert by_ch[ch2.id]["planned_amount"] == 6_000_000.0
    assert by_ch[ch1.id]["spent_amount"] >= 2_000_000.0
    assert by_ch[ch2.id]["spent_amount"] >= 2_000_000.0


def test_budget_summary_zero_budget_no_division_error(client, manager_headers, db_session):
    """budget=0 không được chia cho 0 (0% thay vì 500)."""
    from app.models.entities import Campaign
    camp = db_session.query(Campaign).filter(Campaign.id == 2).first()
    assert camp is not None
    original = float(camp.budget)
    camp.budget = 0
    db_session.commit()
    try:
        res = client.get("/api/v1/campaigns/2/budget-summary", headers=manager_headers)
        assert res.status_code == 200, res.text
        assert res.json()["allocated_pct"] == 0.0
        assert res.json()["spent_pct"] == 0.0
    finally:
        camp.budget = original
        db_session.commit()


def test_budget_summary_cross_tenant_forbidden(client, beta_marketer_headers):
    """Workspace Beta không đọc được budget-summary của chiến dịch Alpha (id=1)."""
    res = client.get("/api/v1/campaigns/1/budget-summary", headers=beta_marketer_headers)
    assert res.status_code in (403, 404)


def test_budget_summary_unauthenticated(client):
    res = client.get("/api/v1/campaigns/1/budget-summary")
    assert res.status_code == 401
