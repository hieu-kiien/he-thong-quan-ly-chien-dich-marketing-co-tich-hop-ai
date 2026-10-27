"""Test router /metrics & import CSV (CONTRACT §2, §4, §10)."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from app.core.timeutil import today_vn
from app.models import Campaign, Channel


def test_upsert_metric_success(
    client: TestClient, marketer1_headers: dict[str, str], sample_campaign: Campaign, test_channels: dict[str, Channel]
):
    today = today_vn()
    payload = {
        "campaign_id": sample_campaign.id,
        "channel_code": "FACEBOOK",
        "metric_date": str(today),
        "views": 1000,
        "clicks": 50,
        "conversions": 5,
        "cost": 250_000,
    }
    resp = client.post("/api/v1/metrics", headers=marketer1_headers, json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["views"] == 1000
    assert data["clicks"] == 50
    assert data["cost"] == 250_000
    assert data["source"] == "MANUAL"

    # Upsert with new views: should update existing
    payload["views"] = 1200
    resp2 = client.post("/api/v1/metrics", headers=marketer1_headers, json=payload)
    assert resp2.status_code == 201
    assert resp2.json()["views"] == 1200
    assert resp2.json()["id"] == data["id"]


def test_metric_validation_clicks_greater_than_views(
    client: TestClient, marketer1_headers: dict[str, str], sample_campaign: Campaign, test_channels: dict[str, Channel]
):
    today = today_vn()
    payload = {
        "campaign_id": sample_campaign.id,
        "channel_code": "FACEBOOK",
        "metric_date": str(today),
        "views": 100,
        "clicks": 150,  # clicks > views
        "conversions": 10,
        "cost": 100_000,
    }
    resp = client.post("/api/v1/metrics", headers=marketer1_headers, json=payload)
    assert resp.status_code == 422
    assert "clicks" in resp.json()["detail"]["fields"]


def test_metric_validation_conversions_greater_than_clicks(
    client: TestClient, marketer1_headers: dict[str, str], sample_campaign: Campaign, test_channels: dict[str, Channel]
):
    today = today_vn()
    payload = {
        "campaign_id": sample_campaign.id,
        "channel_code": "FACEBOOK",
        "metric_date": str(today),
        "views": 500,
        "clicks": 20,
        "conversions": 30,  # conversions > clicks
        "cost": 100_000,
    }
    resp = client.post("/api/v1/metrics", headers=marketer1_headers, json=payload)
    assert resp.status_code == 422
    assert "conversions" in resp.json()["detail"]["fields"]


def test_marketer_cannot_edit_other_marketer_metric(
    client: TestClient,
    marketer1_headers: dict[str, str],
    marketer2_headers: dict[str, str],
    sample_campaign: Campaign,
    test_channels: dict[str, Channel],
):
    today = today_vn()
    # Marketer 1 inserts metric
    resp = client.post(
        "/api/v1/metrics",
        headers=marketer1_headers,
        json={
            "campaign_id": sample_campaign.id,
            "channel_code": "FACEBOOK",
            "metric_date": str(today),
            "views": 200,
            "clicks": 10,
            "conversions": 1,
            "cost": 50_000,
        },
    )
    metric_id = resp.json()["id"]

    # Marketer 2 tries to update or delete -> 403
    patch_resp = client.patch(
        f"/api/v1/metrics/{metric_id}",
        headers=marketer2_headers,
        json={"views": 300},
    )
    assert patch_resp.status_code == 403
    assert patch_resp.json()["detail"]["code"] == "FORBIDDEN"

    del_resp = client.delete(f"/api/v1/metrics/{metric_id}", headers=marketer2_headers)
    assert del_resp.status_code == 403


def test_csv_template(client: TestClient, marketer1_headers: dict[str, str]):
    resp = client.get("/api/v1/metrics/import/template", headers=marketer1_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "date,campaign_id" in resp.text


def test_csv_preview_and_commit(
    client: TestClient,
    marketer1_headers: dict[str, str],
    sample_campaign: Campaign,
    test_channels: dict[str, Channel],
):
    today = today_vn()
    csv_content = f"""date,campaign_id,channel_code,views,clicks,conversions,cost
{today},{sample_campaign.id},FACEBOOK,1000,50,5,200000
{today - timedelta(days=1)},{sample_campaign.id},INSTAGRAM,500,20,2,100000
{today - timedelta(days=2)},{sample_campaign.id},FACEBOOK,100,200,10,50000
"""  # Row 4 has clicks (200) > views (100) -> invalid

    files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
    resp = client.post("/api/v1/metrics/import/preview", headers=marketer1_headers, files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total"] == 3
    assert data["summary"]["valid"] == 2
    assert data["summary"]["invalid"] == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["row"] == 4

    # Now commit the valid rows
    commit_rows = [
        {
            "metric_date": r["metric_date"],
            "campaign_id": r["campaign_id"],
            "channel_id": r["channel_id"],
            "channel_code": r["channel_code"],
            "views": r["views"],
            "clicks": r["clicks"],
            "conversions": r["conversions"],
            "cost": r["cost"],
        }
        for r in data["rows"]
    ]

    commit_resp = client.post(
        "/api/v1/metrics/import/commit",
        headers=marketer1_headers,
        json={"rows": commit_rows},
    )
    assert commit_resp.status_code == 200
    commit_data = commit_resp.json()
    assert commit_data["inserted"] == 2
    assert commit_data["import_batch"].startswith("csv_")


def test_csv_template_requires_login(client: TestClient):
    assert client.get("/api/v1/metrics/import/template").status_code == 401


def test_csv_preview_rejects_non_finite_numbers_without_500(
    client: TestClient,
    marketer1_headers: dict[str, str],
    sample_campaign: Campaign,
    test_channels: dict[str, Channel],
):
    today = today_vn()
    csv_content = (
        "date,campaign_id,channel_code,views,clicks,conversions,cost\n"
        f"{today},{sample_campaign.id},FACEBOOK,1000,50,5,inf\n"
        f"{today - timedelta(days=1)},{sample_campaign.id},FACEBOOK,1000,50,5,nan\n"
        f"{today - timedelta(days=2)},{sample_campaign.id},FACEBOOK,1000,50,5,-inf\n"
    )
    files = {"file": ("bad.csv", csv_content.encode("utf-8"), "text/csv")}
    resp = client.post("/api/v1/metrics/import/preview", headers=marketer1_headers, files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["valid"] == 0
    assert data["summary"]["invalid"] == 3


def test_csv_preview_flags_rows_that_would_overwrite_other_users_metrics(
    client: TestClient,
    marketer1_headers: dict[str, str],
    marketer2_headers: dict[str, str],
    manager_headers: dict[str, str],
    sample_campaign: Campaign,
    test_channels: dict[str, Channel],
):
    today = today_vn()
    created = client.post(
        "/api/v1/metrics",
        headers=marketer1_headers,
        json={
            "campaign_id": sample_campaign.id,
            "channel_code": "FACEBOOK",
            "metric_date": str(today),
            "views": 200,
            "clicks": 10,
            "conversions": 1,
            "cost": 50_000,
        },
    )
    assert created.status_code in (200, 201)
    csv_content = (
        "date,campaign_id,channel_code,views,clicks,conversions,cost\n"
        f"{today},{sample_campaign.id},FACEBOOK,300,20,2,70000\n"
    )
    files = lambda: {"file": ("x.csv", csv_content.encode("utf-8"), "text/csv")}

    # Marketer khác: báo lỗi ngay ở bước xem trước (thay vì để lệnh commit bị 403 giữa chừng)
    other = client.post("/api/v1/metrics/import/preview", headers=marketer2_headers, files=files()).json()
    assert other["summary"]["valid"] == 0 and other["summary"]["invalid"] == 1
    assert "người khác" in other["errors"][0]["message"]

    # Chính chủ và Quản lý được cập nhật
    own = client.post("/api/v1/metrics/import/preview", headers=marketer1_headers, files=files()).json()
    assert own["summary"]["updates"] == 1
    mgr = client.post("/api/v1/metrics/import/preview", headers=manager_headers, files=files()).json()
    assert mgr["summary"]["updates"] == 1
