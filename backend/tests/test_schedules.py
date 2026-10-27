"""Test router /schedules (CONTRACT §4, §10)."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.timeutil import now_utc
from app.models import Content


def test_create_schedule_success(
    client: TestClient, marketer1_headers: dict[str, str], sample_content: Content
):
    future_time = (now_utc() + timedelta(days=2)).isoformat()
    resp = client.post(
        "/api/v1/schedules",
        headers=marketer1_headers,
        json={
            "content_id": sample_content.id,
            "scheduled_at": future_time,
            "note": "Lịch đăng bài Facebook sáng thứ Ba",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content_id"] == sample_content.id
    assert data["status"] == "PLANNED"
    assert data["content"]["title"] == sample_content.title
    assert data["channel"]["code"] == "FACEBOOK"


def test_create_schedule_in_past(client: TestClient, marketer1_headers: dict[str, str], sample_content: Content):
    past_time = (now_utc() - timedelta(hours=2)).isoformat()
    resp = client.post(
        "/api/v1/schedules",
        headers=marketer1_headers,
        json={"content_id": sample_content.id, "scheduled_at": past_time},
    )
    assert resp.status_code == 422
    assert "scheduled_at" in resp.json()["detail"]["fields"]


def test_create_schedule_outside_campaign_dates(
    client: TestClient, marketer1_headers: dict[str, str], sample_content: Content
):
    # sample_campaign ends in today + 20 days. Pick today + 50 days:
    way_future_time = (now_utc() + timedelta(days=50)).isoformat()
    resp = client.post(
        "/api/v1/schedules",
        headers=marketer1_headers,
        json={"content_id": sample_content.id, "scheduled_at": way_future_time},
    )
    assert resp.status_code == 422
    assert "scheduled_at" in resp.json()["detail"]["fields"]


def test_complete_schedule_workflow(
    client: TestClient, marketer1_headers: dict[str, str], sample_content: Content, db: Session
):
    future_time = (now_utc() + timedelta(days=2)).isoformat()
    sched_resp = client.post(
        "/api/v1/schedules",
        headers=marketer1_headers,
        json={"content_id": sample_content.id, "scheduled_at": future_time},
    )
    assert sched_resp.status_code == 201
    sched_id = sched_resp.json()["id"]

    # Trying to complete when content is DRAFT -> 409 INVALID_TRANSITION
    done_resp = client.post(f"/api/v1/schedules/{sched_id}/done", headers=marketer1_headers)
    assert done_resp.status_code == 409
    assert done_resp.json()["detail"]["code"] == "INVALID_TRANSITION"

    # Now approve content
    sample_content.status = "APPROVED"
    db.commit()

    # Now complete schedule -> succeeds, sets content PUBLISHED and schedule DONE
    done_resp2 = client.post(
        f"/api/v1/schedules/{sched_id}/done",
        headers=marketer1_headers,
        json={"published_url": "https://facebook.com/annamexample/posts/999"},
    )
    assert done_resp2.status_code == 200
    assert done_resp2.json()["status"] == "DONE"

    # Verify content is now PUBLISHED
    content_resp = client.get(f"/api/v1/contents/{sample_content.id}", headers=marketer1_headers)
    assert content_resp.status_code == 200
    assert content_resp.json()["status"] == "PUBLISHED"


def test_cancel_schedule(
    client: TestClient, marketer1_headers: dict[str, str], sample_content: Content
):
    future_time = (now_utc() + timedelta(days=2)).isoformat()
    sched_resp = client.post(
        "/api/v1/schedules",
        headers=marketer1_headers,
        json={"content_id": sample_content.id, "scheduled_at": future_time},
    )
    sched_id = sched_resp.json()["id"]

    cancel_resp = client.post(f"/api/v1/schedules/{sched_id}/cancel", headers=marketer1_headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"


def test_marketer_cannot_schedule_someone_elses_content(
    client: TestClient, marketer2_headers: dict[str, str], sample_content: Content
):
    """Người lập lịch được phép đánh dấu 'đã đăng' nên chỉ tác giả/chủ chiến dịch/Quản lý được lập lịch."""
    resp = client.post(
        "/api/v1/schedules",
        headers=marketer2_headers,
        json={"content_id": sample_content.id, "scheduled_at": (now_utc() + timedelta(days=2)).isoformat()},
    )
    assert resp.status_code == 403


def test_manager_can_schedule_any_content(
    client: TestClient, manager_headers: dict[str, str], sample_content: Content
):
    resp = client.post(
        "/api/v1/schedules",
        headers=manager_headers,
        json={"content_id": sample_content.id, "scheduled_at": (now_utc() + timedelta(days=2)).isoformat()},
    )
    assert resp.status_code == 201
