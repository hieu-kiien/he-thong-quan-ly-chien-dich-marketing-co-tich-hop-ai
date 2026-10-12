"""Workstream E — Auth: logout revocation + change password.

Bất biến kiểm:
- Logout tăng token_version → token cũ (được cấp trước logout) bị 401 fail-closed.
- Token cấp SAU logout (phiên mới) vẫn hoạt động.
- Đổi mật khẩu: sai mật khẩu hiện tại → 400; đúng → hash mới + token mới hoạt
  động, token cũ (trước khi đổi) bị thu hồi.
- Đổi mật khẩu không cho mật khẩu mới trùng mật khẩu cũ.
"""
from app.models.entities import User


def _login(client, email: str, password: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()


def test_logout_revokes_existing_token(client, db_session):
    data = _login(client, "manager@gmail.com", "Manager@123")
    old_token = data["access_token"]
    old_headers = {"Authorization": f"Bearer {old_token}"}

    # Token hợp lệ trước logout
    assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 200

    # Logout → thu hồi
    res = client.post("/api/v1/auth/logout", headers=old_headers)
    assert res.status_code == 204, res.text

    # Token cũ phải bị 401 fail-closed
    res = client.get("/api/v1/auth/me", headers=old_headers)
    assert res.status_code == 401, (
        f"Token đã bị thu hồi phải trả 401, nhận {res.status_code}: {res.text}"
    )


def test_login_after_logout_issues_working_token(client):
    first = _login(client, "manager@gmail.com", "Manager@123")
    client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {first['access_token']}"},
    )

    second = _login(client, "manager@gmail.com", "Manager@123")
    new_headers = {"Authorization": f"Bearer {second['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=new_headers).status_code == 200


def test_change_password_requires_correct_current(client, db_session):
    me = client.post(
        "/api/v1/auth/login",
        json={"email": "manager@gmail.com", "password": "Manager@123"},
    ).json()

    res = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "SaiMatKhau123", "new_password": "MoiKhac@123"},
        headers={"Authorization": f"Bearer {me['access_token']}"},
    )
    assert res.status_code == 400, res.text
    assert "hiện tại" in res.json()["detail"]

    # Mật khẩu cũ vẫn đăng nhập được (chưa bị đổi)
    assert _login(client, "manager@gmail.com", "Manager@123")["access_token"]


def test_change_password_rejects_identical_password(client):
    me = _login(client, "manager@gmail.com", "Manager@123")
    res = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Manager@123", "new_password": "Manager@123"},
        headers={"Authorization": f"Bearer {me['access_token']}"},
    )
    assert res.status_code == 400, res.text
    assert "khác" in res.json()["detail"]


def test_change_password_updates_hash_and_revokes_old_tokens(client, db_session):
    old = _login(client, "marketer@gmail.com", "Marketer@123")
    old_headers = {"Authorization": f"Bearer {old['access_token']}"}

    res = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Marketer@123", "new_password": "MoiMatKhau@2026"},
        headers=old_headers,
    )
    assert res.status_code == 200, res.text
    new_token = res.json()["access_token"]

    # Hash trong DB đã đổi
    u = db_session.query(User).filter(User.email == "marketer@gmail.com").first()
    db_session.refresh(u)
    from app.core.security import verify_password
    assert verify_password("MoiMatKhau@2026", u.password_hash)
    assert not verify_password("Manager@123", u.password_hash)

    # Token cũ (trước khi đổi) bị thu hồi
    assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 401

    # Token mới cấp trong response hoạt động
    new_headers = {"Authorization": f"Bearer {new_token}"}
    assert client.get("/api/v1/auth/me", headers=new_headers).status_code == 200

    # Đăng nhập bằng mật khẩu mới OK, mật khẩu cũ fail
    _login(client, "marketer@gmail.com", "MoiMatKhau@2026")
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "marketer@gmail.com", "password": "Marketer@123"},
    )
    assert res.status_code == 401


def test_logout_requires_authentication(client):
    assert client.post("/api/v1/auth/logout").status_code == 401


def test_change_password_requires_authentication(client):
    res = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "x", "new_password": "yyyyyy"},
    )
    assert res.status_code == 401
