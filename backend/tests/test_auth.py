"""Test xác thực /auth/* (CONTRACT §4, §10)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import login_rate_limiter
from app.models import User


def test_login_success(client: TestClient, manager_user: User):
    resp = client.post("/api/v1/auth/login", json={"email": manager_user.email, "password": "Manager@123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == manager_user.email
    assert data["user"]["role"] == "MANAGER"


def test_login_wrong_password(client: TestClient, manager_user: User):
    resp = client.post("/api/v1/auth/login", json={"email": manager_user.email, "password": "WrongPassword@123"})
    assert resp.status_code == 401
    err = resp.json()["detail"]
    assert err["code"] == "INVALID_CREDENTIALS"


def test_login_rate_limit(client: TestClient, manager_user: User):
    login_rate_limiter.reset()
    # 5 failed attempts
    for _ in range(5):
        resp = client.post("/api/v1/auth/login", json={"email": manager_user.email, "password": "BadPassword1"})
        assert resp.status_code == 401

    # 6th attempt should be rate limited (429)
    resp = client.post("/api/v1/auth/login", json={"email": manager_user.email, "password": "BadPassword1"})
    assert resp.status_code == 429
    err = resp.json()["detail"]
    assert err["code"] == "LOGIN_RATE_LIMITED"
    assert "Retry-After" in resp.headers

    login_rate_limiter.reset()


def test_login_disabled_account(client: TestClient, db: Session, manager_user: User):
    manager_user.is_active = False
    db.commit()

    resp = client.post("/api/v1/auth/login", json={"email": manager_user.email, "password": "Manager@123"})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ACCOUNT_DISABLED"


def test_me_endpoint(client: TestClient, manager_headers: dict[str, str], manager_user: User):
    resp = client.get("/api/v1/auth/me", headers=manager_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == manager_user.id
    assert resp.json()["email"] == manager_user.email


def test_logout_revokes_token(client: TestClient, manager_headers: dict[str, str]):
    # Check me works
    resp = client.get("/api/v1/auth/me", headers=manager_headers)
    assert resp.status_code == 200

    # Logout
    resp = client.post("/api/v1/auth/logout", headers=manager_headers)
    assert resp.status_code == 200

    # Check old token is now revoked
    resp = client.get("/api/v1/auth/me", headers=manager_headers)
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "TOKEN_REVOKED"


def test_change_password(client: TestClient, marketer1_headers: dict[str, str], marketer1_user: User):
    resp = client.post(
        "/api/v1/auth/change-password",
        headers=marketer1_headers,
        json={"current_password": "Marketer@123", "new_password": "NewSecretPass456"},
    )
    assert resp.status_code == 200
    new_token = resp.json()["access_token"]

    # Old token is revoked
    old_resp = client.get("/api/v1/auth/me", headers=marketer1_headers)
    assert old_resp.status_code == 401

    # New token works
    new_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert new_resp.status_code == 200


def test_register_success_and_validation(client: TestClient, manager_user: User):
    # Weak password rejected
    weak = client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@marketflow.vn", "full_name": "Nguyễn Văn Mới", "password": "short"},
    )
    assert weak.status_code == 422
    assert weak.json()["detail"]["code"] == "VALIDATION_ERROR"

    # Successful registration defaults to MANAGER and issues JWT
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "NewUser@MarketFlow.vn", "full_name": "Nguyễn Văn Mới", "password": "NewUser@123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "newuser@marketflow.vn"
    assert data["user"]["full_name"] == "Nguyễn Văn Mới"
    assert data["user"]["role"] == "MANAGER"

    # Duplicate email rejected (409)
    dup = client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@marketflow.vn", "full_name": "Người Khác", "password": "NewUser@123"},
    )
    assert dup.status_code == 409
    assert dup.json()["detail"]["code"] == "EMAIL_EXISTS"


def test_login_rate_limit_not_bypassed_by_spoofed_forwarded_header(client: TestClient, manager_user: User):
    """X-Forwarded-For do client gửi không được dùng để né giới hạn (peer không phải proxy nội bộ)."""
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": manager_user.email, "password": "BadPassword1"},
            headers={"X-Forwarded-For": f"10.0.0.{i}", "CF-Connecting-IP": f"9.9.9.{i}"},
        )
        assert resp.status_code == 401
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": manager_user.email, "password": "BadPassword1"},
        headers={"X-Forwarded-For": "10.0.0.99", "CF-Connecting-IP": "9.9.9.99"},
    )
    assert resp.status_code == 429


def test_register_rate_limited_per_ip(client: TestClient):
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": f"nguoi{i}@example.com", "full_name": f"Người dùng {i}", "password": "MatKhau123"},
        )
        assert resp.status_code == 201, resp.text
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "nguoi6@example.com", "full_name": "Người dùng 6", "password": "MatKhau123"},
    )
    assert resp.status_code == 429
    assert resp.json()["detail"]["code"] == "REGISTER_RATE_LIMITED"


def test_register_can_be_disabled(client: TestClient, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ALLOW_SELF_REGISTER", False)
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "khach@example.com", "full_name": "Khách", "password": "MatKhau123"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "REGISTER_DISABLED"


def test_login_limiter_memory_is_bounded():
    from app.core.security import LoginRateLimiter

    limiter = LoginRateLimiter(5, 300)
    for i in range(LoginRateLimiter.MAX_KEYS + 500):
        limiter.record_failure(f"user{i}@example.com|1.2.3.4")
    assert len(limiter._failures) <= LoginRateLimiter.MAX_KEYS
