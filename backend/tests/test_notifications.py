"""Test router /notifications (CONTRACT §4, §10)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Notification, User


def test_notification_flow(
    client: TestClient, marketer1_headers: dict[str, str], marketer2_headers: dict[str, str], marketer1_user: User, db: Session
):
    # Add 2 notifications for marketer1
    n1 = Notification(user_id=marketer1_user.id, type="TEST_1", message="Thông báo 1", is_read=False)
    n2 = Notification(user_id=marketer1_user.id, type="TEST_2", message="Thông báo 2", is_read=False)
    db.add_all([n1, n2])
    db.commit()
    db.refresh(n1)
    db.refresh(n2)

    # List notifications
    resp = client.get("/api/v1/notifications", headers=marketer1_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["unread_count"] == 2

    # Mark 1 as read
    resp_read = client.post(f"/api/v1/notifications/{n1.id}/read", headers=marketer1_headers)
    assert resp_read.status_code == 200
    assert resp_read.json()["is_read"] is True

    # Marketer 2 cannot mark marketer 1's notification as read (404)
    resp_other = client.post(f"/api/v1/notifications/{n2.id}/read", headers=marketer2_headers)
    assert resp_other.status_code == 404

    # Mark all read
    resp_all = client.post("/api/v1/notifications/read-all", headers=marketer1_headers)
    assert resp_all.status_code == 200
    assert resp_all.json()["updated"] >= 1

    # Check unread count is now 0
    resp_after = client.get("/api/v1/notifications", headers=marketer1_headers)
    assert resp_after.json()["unread_count"] == 0
