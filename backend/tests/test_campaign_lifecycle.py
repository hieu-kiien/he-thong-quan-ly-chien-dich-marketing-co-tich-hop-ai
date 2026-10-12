"""Campaign lifecycle / state machine tests (Phase 2)."""

import pytest
from fastapi.testclient import TestClient

from app.services.campaign_lifecycle import (
    ALLOWED_TRANSITIONS,
    CREATE_ALLOWED_STATUSES,
    assert_create_status,
    assert_transition,
    compute_progress_pct,
)


def test_create_with_status_active_is_preserved(client: TestClient, marketer_headers, db_session):
    """Wizard gửi ACTIVE → campaign tạo ra phải ACTIVE (không bị ép về DRAFT)."""
    payload = {
        "name": "Campaign ACTIVE ngay từ wizard",
        "product_id": 1,
        "objective": "Tăng trưởng",
        "audience": "Gen Z",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31",
        "budget": 5_000_000.0,
        "status": "ACTIVE",
    }
    res = client.post("/api/v1/campaigns", json=payload, headers=marketer_headers)
    assert res.status_code == 201, res.text
    assert res.json()["status"] == "ACTIVE"


def test_create_rejects_invalid_status(client: TestClient, marketer_headers):
    payload = {
        "name": "Status không hợp lệ",
        "product_id": 1,
        "objective": "x",
        "audience": "y",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31",
        "budget": 1000.0,
        "status": "COMPLETED",
    }
    res = client.post("/api/v1/campaigns", json=payload, headers=marketer_headers)
    assert res.status_code == 422


def test_transition_valid_and_invalid(client: TestClient, marketer_headers, db_session):
    create = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Transition campaign",
            "product_id": 1,
            "objective": "x",
            "audience": "y",
            "start_date": "2026-10-01",
            "end_date": "2026-10-31",
            "budget": 1000.0,
            "status": "DRAFT",
        },
        headers=marketer_headers,
    )
    assert create.status_code == 201
    cid = create.json()["id"]

    # DRAFT → ACTIVE hợp lệ
    ok = client.put(f"/api/v1/campaigns/{cid}", json={"status": "ACTIVE"}, headers=marketer_headers)
    assert ok.status_code == 200
    assert ok.json()["status"] == "ACTIVE"

    # ACTIVE → DRAFT không hợp lệ (không có nhánh đó)
    bad = client.put(f"/api/v1/campaigns/{cid}", json={"status": "DRAFT"}, headers=marketer_headers)
    assert bad.status_code == 422

    # ACTIVE → PAUSED hợp lệ
    pause = client.put(f"/api/v1/campaigns/{cid}", json={"status": "PAUSED"}, headers=marketer_headers)
    assert pause.status_code == 200

    # PAUSED → COMPLETED hợp lệ
    done = client.put(f"/api/v1/campaigns/{cid}", json={"status": "COMPLETED"}, headers=marketer_headers)
    assert done.status_code == 200


def test_toggle_active_paused_roundtrip(client: TestClient, marketer_headers):
    """UI 1-click toggle ACTIVE↔PAUSED phải luôn hợp lệ với state machine."""
    create = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Toggle campaign",
            "product_id": 1,
            "objective": "x",
            "audience": "y",
            "start_date": "2026-10-01",
            "end_date": "2026-10-31",
            "budget": 1000.0,
            "status": "ACTIVE",
        },
        headers=marketer_headers,
    )
    assert create.status_code == 201
    cid = create.json()["id"]

    pause = client.put(f"/api/v1/campaigns/{cid}", json={"status": "PAUSED"}, headers=marketer_headers)
    assert pause.status_code == 200
    active = client.put(f"/api/v1/campaigns/{cid}", json={"status": "ACTIVE"}, headers=marketer_headers)
    assert active.status_code == 200
    assert active.json()["status"] == "ACTIVE"


def test_soft_delete_archives(client: TestClient, manager_headers, marketer_headers):
    create = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Soft delete campaign",
            "product_id": 1,
            "objective": "x",
            "audience": "y",
            "start_date": "2026-10-01",
            "end_date": "2026-10-31",
            "budget": 1000.0,
            "status": "ACTIVE",
        },
        headers=marketer_headers,
    )
    assert create.status_code == 201
    cid = create.json()["id"]

    res = client.delete(f"/api/v1/campaigns/{cid}", headers=manager_headers)
    assert res.status_code == 204

    # Vẫn GET được theo id (audit)
    get = client.get(f"/api/v1/campaigns/{cid}", headers=manager_headers)
    assert get.status_code == 200
    assert get.json()["status"] == "ARCHIVED"

    # List mặc định ẩn
    listed = client.get("/api/v1/campaigns", headers=marketer_headers)
    assert listed.status_code == 200
    assert cid not in [c["id"] for c in listed.json()["items"]]


def test_progress_pct_from_tasks(client: TestClient, marketer_headers):
    create = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Progress campaign",
            "product_id": 1,
            "objective": "x",
            "audience": "y",
            "start_date": "2026-10-01",
            "end_date": "2026-10-31",
            "budget": 1000.0,
            "status": "ACTIVE",
        },
        headers=marketer_headers,
    )
    assert create.status_code == 201
    assert create.json().get("progress_pct") is None  # chưa có task

    cid = create.json()["id"]
    for i, st in enumerate(("DONE", "TODO")):
        t = client.post(
            f"/api/v1/campaigns/{cid}/tasks",
            json={
                "title": f"Task {i}",
                "status": st,
                "task_type": "OTHER",
                "priority": "MEDIUM",
            },
            headers=marketer_headers,
        )
        assert t.status_code in (200, 201), t.text

    got = client.get(f"/api/v1/campaigns/{cid}", headers=marketer_headers)
    assert got.status_code == 200
    # 1/2 = 50%
    assert got.json().get("progress_pct") == 50


def test_unit_state_machine_helpers():
    assert assert_create_status("active") == "ACTIVE"
    assert assert_transition("DRAFT", "ACTIVE") == "ACTIVE"
    assert assert_transition("ACTIVE", None) == "ACTIVE"
    assert compute_progress_pct(0, 0) is None
    assert compute_progress_pct(1, 2) == 50
    assert compute_progress_pct(3, 2) == 100  # clamp
    # Ma trận chuyển tiếp không rỗng
    for st in CREATE_ALLOWED_STATUSES:
        assert st in ALLOWED_TRANSITIONS
