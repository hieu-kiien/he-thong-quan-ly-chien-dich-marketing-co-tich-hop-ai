"""Test router /channels (CONTRACT §2, §4)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models import Campaign, Channel


def test_list_channels(client: TestClient, marketer1_headers: dict[str, str], test_channels: dict[str, Channel]):
    resp = client.get("/api/v1/channels", headers=marketer1_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 7
    codes = [c["code"] for c in items]
    assert "FACEBOOK" in codes


def test_create_channel_manager(client: TestClient, manager_headers: dict[str, str]):
    resp = client.post(
        "/api/v1/channels",
        headers=manager_headers,
        json={"code": "THREADS", "name": "Threads", "format_rules": "Max 500 chars"},
    )
    assert resp.status_code == 201
    assert resp.json()["code"] == "THREADS"


def test_create_channel_marketer_forbidden(client: TestClient, marketer1_headers: dict[str, str]):
    resp = client.post(
        "/api/v1/channels",
        headers=marketer1_headers,
        json={"code": "THREADS2", "name": "Threads 2"},
    )
    assert resp.status_code == 403


def test_delete_channel_in_use_conflict(
    client: TestClient, manager_headers: dict[str, str], sample_campaign: Campaign, test_channels: dict[str, Channel]
):
    # FACEBOOK is used in sample_campaign
    fb_id = test_channels["FACEBOOK"].id
    resp = client.delete(f"/api/v1/channels/{fb_id}", headers=manager_headers)
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "CHANNEL_IN_USE"


def test_delete_channel_unused(client: TestClient, manager_headers: dict[str, str], test_channels: dict[str, Channel]):
    # GOOGLE_ADS is not used in sample_campaign
    ads_id = test_channels["GOOGLE_ADS"].id
    resp = client.delete(f"/api/v1/channels/{ads_id}", headers=manager_headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Đã xoá kênh thành công"
