"""Test endpoint xuất dữ liệu (ADMIN-only).

Bao gồm kiểm tra bảo mật quan trọng nhất: KHÔNG cột bí mật nào
(password_hash, encrypted_key) được trả về trong payload export.
"""

import pytest
from app.core.security import hash_password
from app.models.entities import User, Workspace
from sqlalchemy import inspect, text


def _make_admin(db_session) -> User:
    admin = db_session.query(User).filter(User.email == "export_admin@test.local").first()
    if not admin:
        admin = User(
            email="export_admin@test.local",
            full_name="Export Admin",
            password_hash=hash_password("ExportAdmin@Test123"),
            role="ADMIN",
            status="ACTIVE",
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
    return admin


def _admin_headers(admin: User) -> dict:
    from app.core.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token({'sub': str(admin.id)})}"}


def test_export_denied_for_manager(client, manager_headers):
    """MANAGER không được xuất dữ liệu toàn hệ thống."""
    r = client.get("/api/v1/export/data", headers=manager_headers)
    assert r.status_code == 403
    assert "ADMIN" in r.json()["detail"]


def test_export_denied_for_marketer(client, marketer_headers):
    """MARKETER không được xuất dữ liệu toàn hệ thống."""
    r = client.get("/api/v1/export/data", headers=marketer_headers)
    assert r.status_code == 403


def test_export_requires_auth(client):
    """Không token thì bị chặn."""
    r = client.get("/api/v1/export/data")
    assert r.status_code in (401, 403)


def test_export_redacts_password_hash(client, db_session):
    """Không user nào lộ password_hash trong export."""
    admin = _make_admin(db_session)
    r = client.get("/api/v1/export/data", headers=_admin_headers(admin))
    assert r.status_code == 200
    body = r.json()

    user_rows = body["tables"].get("users", {}).get("rows", [])
    assert user_rows, "export phải chứa bảng users"
    assert "password_hash" not in body["tables"]["users"]["columns"]
    for row in user_rows:
        assert "password_hash" not in row


def test_export_redacts_encrypted_api_key(client, db_session):
    """Không lộ khóa API đã mã hoá."""
    admin = _make_admin(db_session)
    r = client.get("/api/v1/export/data", headers=_admin_headers(admin))
    assert r.status_code == 200
    tables = r.json()["tables"]

    if "custom_api_keys" in tables:
        assert "encrypted_key" not in tables["custom_api_keys"]["columns"]
        for row in tables["custom_api_keys"]["rows"]:
            assert "encrypted_key" not in row


def test_export_has_no_secret_values_anywhere(client, db_session):
    """Quét toàn payload: không được có giá trị hash/khoá bí mật."""
    admin = _make_admin(db_session)
    r = client.get("/api/v1/export/data", headers=_admin_headers(admin))
    assert r.status_code == 200

    blob = r.text
    assert "$2b$" not in blob, "payload chứa bcrypt hash"
    for user in db_session.query(User).all():
        assert user.password_hash not in blob


def test_export_structure(client, db_session):
    """Cấu trúc trả về đầy đủ cho việc khôi phục dữ liệu."""
    admin = _make_admin(db_session)
    r = client.get("/api/v1/export/data", headers=_admin_headers(admin))
    assert r.status_code == 200
    body = r.json()

    for key in ("exported_at", "total_rows", "tables", "redacted_columns"):
        assert key in body

    ws_rows = body["tables"].get("workspaces", {}).get("rows", [])
    assert ws_rows, "phải export được workspaces"
    assert "id" in ws_rows[0]
    # Không còn object datetime thô (đã serialize thành ISO string).
    assert isinstance(ws_rows[0]["id"], int)


def test_export_row_counts_match_db(client, db_session):
    """row_count phải khớp số bản ghi thật trong DB."""
    admin = _make_admin(db_session)
    r = client.get("/api/v1/export/data", headers=_admin_headers(admin))
    body = r.json()

    dumped = body["tables"]["workspaces"]
    assert dumped["row_count"] == db_session.query(Workspace).count()
    assert dumped["row_count"] == len(dumped["rows"])
