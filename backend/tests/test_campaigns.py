"""Test router /campaigns (CONTRACT §2, §4, §10)."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.timeutil import today_vn
from app.models import Campaign, Channel, Content


def test_create_campaign(client: TestClient, marketer1_headers: dict[str, str], test_channels: dict[str, Channel]):
    today = today_vn()
    payload = {
        "name": "Chiến dịch Tết 2027",
        "goal": "SALES",
        "objective": "Tăng trưởng doanh số giỏ quà Tết",
        "target_audience": "Gia đình và doanh nghiệp",
        "product": "Hộp quà Tết An Nam",
        "key_message": "Tết sum vầy",
        "start_date": str(today),
        "end_date": str(today + timedelta(days=30)),
        "budget": 50_000_000,
        "status": "PLANNED",
        "channels": [
            {"channel_code": "FACEBOOK", "planned_budget": 30_000_000},
            {"channel_code": "INSTAGRAM", "planned_budget": 20_000_000},
        ],
    }
    resp = client.post("/api/v1/campaigns", headers=marketer1_headers, json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Chiến dịch Tết 2027"
    assert data["budget"] == 50_000_000
    assert len(data["channels"]) == 2
    assert data["owner"]["full_name"] == "Trần Thị Lan Anh Test"


def test_campaign_validation_end_before_start(client: TestClient, marketer1_headers: dict[str, str], test_channels: dict[str, Channel]):
    today = today_vn()
    payload = {
        "name": "Chiến dịch lỗi ngày",
        "goal": "AWARENESS",
        "objective": "Mục tiêu",
        "target_audience": "Khách hàng",
        "product": "Sản phẩm",
        "start_date": str(today),
        "end_date": str(today - timedelta(days=5)),
        "budget": 10_000_000,
        "channels": [{"channel_code": "FACEBOOK"}],
    }
    resp = client.post("/api/v1/campaigns", headers=marketer1_headers, json=payload)
    assert resp.status_code == 422
    assert "end_date" in resp.json()["detail"]["fields"]


def test_campaign_planned_budget_exceeds_total(client: TestClient, marketer1_headers: dict[str, str], test_channels: dict[str, Channel]):
    today = today_vn()
    payload = {
        "name": "Chiến dịch lạm chi",
        "goal": "AWARENESS",
        "objective": "Mục tiêu",
        "target_audience": "Khách hàng",
        "product": "Sản phẩm",
        "start_date": str(today),
        "end_date": str(today + timedelta(days=10)),
        "budget": 10_000_000,
        "channels": [
            {"channel_code": "FACEBOOK", "planned_budget": 8_000_000},
            {"channel_code": "INSTAGRAM", "planned_budget": 5_000_000},  # 8 + 5 = 13M > 10M
        ],
    }
    resp = client.post("/api/v1/campaigns", headers=marketer1_headers, json=payload)
    assert resp.status_code == 422
    assert "channels" in resp.json()["detail"]["fields"]


def test_campaign_date_overlap_filter(
    client: TestClient, marketer1_headers: dict[str, str], sample_campaign: Campaign
):
    # sample_campaign is from today - 10 to today + 20
    today = today_vn()

    # Query with overlapping range [today - 5, today + 5]
    resp = client.get(
        f"/api/v1/campaigns?date_from={today - timedelta(days=5)}&date_to={today + timedelta(days=5)}",
        headers=marketer1_headers,
    )
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()["items"]]
    assert sample_campaign.id in ids

    # Query with completely non-overlapping range [today + 50, today + 60]
    resp2 = client.get(
        f"/api/v1/campaigns?date_from={today + timedelta(days=50)}&date_to={today + timedelta(days=60)}",
        headers=marketer1_headers,
    )
    assert resp2.status_code == 200
    ids2 = [c["id"] for c in resp2.json()["items"]]
    assert sample_campaign.id not in ids2


def test_marketer_cannot_edit_others_campaign(
    client: TestClient, marketer2_headers: dict[str, str], sample_campaign: Campaign
):
    # sample_campaign belongs to marketer1. marketer2 tries to edit:
    resp = client.patch(
        f"/api/v1/campaigns/{sample_campaign.id}",
        headers=marketer2_headers,
        json={"name": "Marketer 2 Hack Tên"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "FORBIDDEN"


def test_campaign_invalid_transition(
    client: TestClient, manager_headers: dict[str, str], sample_campaign: Campaign, db: Session
):
    sample_campaign.status = "COMPLETED"
    db.commit()

    # Try transitioning COMPLETED -> ACTIVE -> should be 409 INVALID_TRANSITION
    resp = client.patch(
        f"/api/v1/campaigns/{sample_campaign.id}",
        headers=manager_headers,
        json={"status": "ACTIVE"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INVALID_TRANSITION"


def test_delete_campaign_with_content_conflict(
    client: TestClient, manager_headers: dict[str, str], sample_campaign: Campaign, sample_content: Content
):
    resp = client.delete(f"/api/v1/campaigns/{sample_campaign.id}", headers=manager_headers)
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "CAMPAIGN_HAS_DATA"
