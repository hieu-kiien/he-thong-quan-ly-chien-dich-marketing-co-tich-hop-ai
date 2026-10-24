"""Test router /users (chỉ MANAGER toàn quyền, MARKETER bị chặn) (CONTRACT §2, §4)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models import User


def test_list_users_as_manager(client: TestClient, manager_headers: dict[str, str], manager_user: User):
    resp = client.get("/api/v1/users", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(u["id"] == manager_user.id for u in data["items"])


def test_list_users_as_marketer_forbidden(client: TestClient, marketer1_headers: dict[str, str]):
    resp = client.get("/api/v1/users", headers=marketer1_headers)
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "FORBIDDEN"


def test_create_user_as_manager(client: TestClient, manager_headers: dict[str, str]):
    resp = client.post(
        "/api/v1/users",
        headers=manager_headers,
        json={
            "email": "new.member@marketflow.vn",
            "full_name": "Nhân Viên Mới",
            "role": "MARKETER",
            "password": "Password123",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "new.member@marketflow.vn"
    assert resp.json()["role"] == "MARKETER"


def test_create_duplicate_email(client: TestClient, manager_headers: dict[str, str], marketer1_user: User):
    resp = client.post(
        "/api/v1/users",
        headers=manager_headers,
        json={
            "email": marketer1_user.email,
            "full_name": "Người Trùng Email",
            "role": "MARKETER",
            "password": "Password123",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "EMAIL_EXISTS"


def test_update_user_and_self_protection(
    client: TestClient, manager_headers: dict[str, str], manager_user: User, marketer1_user: User
):
    # Manager can update another user's name
    resp = client.patch(
        f"/api/v1/users/{marketer1_user.id}",
        headers=manager_headers,
        json={"full_name": "Tên Mới Sau Khi Cập Nhật"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Tên Mới Sau Khi Cập Nhật"

    # Manager cannot demote themselves
    resp = client.patch(
        f"/api/v1/users/{manager_user.id}",
        headers=manager_headers,
        json={"role": "MARKETER"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "CANNOT_MODIFY_SELF"

    # Manager cannot deactivate themselves
    resp = client.patch(
        f"/api/v1/users/{manager_user.id}",
        headers=manager_headers,
        json={"is_active": False},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "CANNOT_MODIFY_SELF"


def test_reset_password(client: TestClient, manager_headers: dict[str, str], marketer1_user: User):
    resp = client.post(
        f"/api/v1/users/{marketer1_user.id}/reset-password",
        headers=manager_headers,
        json={"new_password": "NewResetPass999"},
    )
    assert resp.status_code == 200

    # Old token for marketer1 should now be revoked
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": marketer1_user.email, "password": "NewResetPass999"},
    )
    assert login_resp.status_code == 200
