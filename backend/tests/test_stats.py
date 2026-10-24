"""Test router /stats (CONTRACT §4, §10)."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.timeutil import today_vn
from app.models import Campaign, Channel, Metric
from app.models.enums import MetricSource


def test_stats_overview_zero_denominators(
    client: TestClient, marketer1_headers: dict[str, str], sample_campaign: Campaign
):
    # No metrics yet: totals are 0, rates are all null
    resp = client.get("/api/v1/stats/overview", headers=marketer1_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["totals"]["views"] == 0
    assert data["totals"]["clicks"] == 0
    assert data["totals"]["cost"] == 0
    assert data["rates"]["ctr"] is None
    assert data["rates"]["cvr"] is None
    assert data["rates"]["cpc"] is None
    assert data["rates"]["cpa"] is None
    assert data["rates"]["cpm"] is None
    assert data["budget"]["spent"] == 0
    assert data["has_seed_data"] is False


def test_stats_overview_with_metrics(
    client: TestClient,
    marketer1_headers: dict[str, str],
    sample_campaign: Campaign,
    test_channels: dict[str, Channel],
    db: Session,
):
    today = today_vn()
    # Add metric: views=1000, clicks=100, conv=10, cost=500,000
    # ctr = 100/1000 = 0.1
    # cvr = 10/100 = 0.1
    # cpc = 500000/100 = 5000.0
    # cpa = 500000/10 = 50000.0
    # cpm = 500000/1000 * 1000 = 500000.0
    # budget = 20,000,000 -> used_pct = 500000 / 20000000 * 100 = 2.5%
    db.add(
        Metric(
            campaign_id=sample_campaign.id,
            channel_id=test_channels["FACEBOOK"].id,
            metric_date=today,
            views=1000,
            clicks=100,
            conversions=10,
            cost=Decimal(500_000),
            source=MetricSource.SEED,
        )
    )
    db.commit()

    resp = client.get("/api/v1/stats/overview", headers=marketer1_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["totals"]["views"] == 1000
    assert data["totals"]["clicks"] == 100
    assert data["totals"]["conversions"] == 10
    assert data["totals"]["cost"] == 500_000

    assert data["rates"]["ctr"] == 0.1
    assert data["rates"]["cvr"] == 0.1
    assert data["rates"]["cpc"] == 5000.0
    assert data["rates"]["cpa"] == 50000.0
    assert data["rates"]["cpm"] == 500000.0

    assert data["budget"]["total_budget"] == 20_000_000
    assert data["budget"]["spent"] == 500_000
    assert data["budget"]["used_pct"] == 2.5
    assert data["has_seed_data"] is True


def test_stats_timeseries(
    client: TestClient,
    marketer1_headers: dict[str, str],
    sample_campaign: Campaign,
    test_channels: dict[str, Channel],
    db: Session,
):
    today = today_vn()
    for i in range(3):
        db.add(
            Metric(
                campaign_id=sample_campaign.id,
                channel_id=test_channels["FACEBOOK"].id,
                metric_date=today - timedelta(days=i),
                views=100 * (i + 1),
                clicks=10 * (i + 1),
                conversions=1 * (i + 1),
                cost=Decimal(50_000 * (i + 1)),
                source=MetricSource.MANUAL,
            )
        )
    db.commit()

    # Day granularity
    resp_day = client.get("/api/v1/stats/timeseries?granularity=day", headers=marketer1_headers)
    assert resp_day.status_code == 200
    assert len(resp_day.json()) == 3

    # Month granularity
    resp_month = client.get("/api/v1/stats/timeseries?granularity=month", headers=marketer1_headers)
    assert resp_month.status_code == 200
    assert len(resp_month.json()) >= 1


def test_stats_by_channel_and_by_campaign(
    client: TestClient,
    marketer1_headers: dict[str, str],
    sample_campaign: Campaign,
    test_channels: dict[str, Channel],
    db: Session,
):
    today = today_vn()
    db.add(
        Metric(
            campaign_id=sample_campaign.id,
            channel_id=test_channels["FACEBOOK"].id,
            metric_date=today,
            views=1000,
            clicks=50,
            conversions=5,
            cost=Decimal(200_000),
            source=MetricSource.MANUAL,
        )
    )
    db.commit()

    # By channel
    resp_ch = client.get("/api/v1/stats/by-channel", headers=marketer1_headers)
    assert resp_ch.status_code == 200
    data_ch = resp_ch.json()
    assert len(data_ch) >= 1
    assert data_ch[0]["channel"]["code"] == "FACEBOOK"
    assert data_ch[0]["views"] == 1000

    # By campaign
    resp_camp = client.get("/api/v1/stats/by-campaign", headers=marketer1_headers)
    assert resp_camp.status_code == 200
    data_camp = resp_camp.json()
    assert len(data_camp) >= 1
    assert data_camp[0]["campaign"]["name"] == sample_campaign.name
    assert data_camp[0]["views"] == 1000
