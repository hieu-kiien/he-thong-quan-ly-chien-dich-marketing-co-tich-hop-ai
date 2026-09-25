"""
Test Suite: Authentication Registration Tests (Milestone 1)
Covers:
- POST /api/v1/auth/register for various roles
- Automatic personal workspace creation
- Automatic brand kit initialization
- Validation rules (duplicate email, invalid format, short password)
"""

import pytest
from app.models.entities import User, Workspace, WorkspaceMember, BrandKit

def test_register_marketer_success(client, db_session):
    """Đăng ký tài khoản Marketer mới thành công trả về HTTP 201."""
    payload = {
        "email": "new_marketer@example.com",
        "password": "Password@123",
        "full_name": "Nguyễn Văn Marketer Mới",
        "role": "MARKETER"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new_marketer@example.com"
    assert data["full_name"] == "Nguyễn Văn Marketer Mới"
    assert data["role"] == "MARKETER"
    assert data["status"] == "ACTIVE"
    assert "password" not in data
    assert "password_hash" not in data

def test_register_creates_personal_workspace(client, db_session):
    """Đăng ký tài khoản tự động tạo Personal Workspace trong CSDL."""
    payload = {
        "email": "workspace_test@example.com",
        "password": "Password@123",
        "full_name": "Lê Workspace Test"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    ws = db_session.query(Workspace).filter(Workspace.owner_id == user_id).first()
    assert ws is not None
    assert "Lê Workspace Test" in ws.name
    assert ws.status == "ACTIVE"
    assert ws.slug is not None

def test_register_creates_workspace_membership(client, db_session):
    """Đăng ký tài khoản tự động gán người dùng làm thành viên Workspace."""
    payload = {
        "email": "membership_test@example.com",
        "password": "Password@123",
        "full_name": "Phạm Membership Test",
        "role": "MARKETER"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    ws = db_session.query(Workspace).filter(Workspace.owner_id == user_id).first()
    assert ws is not None

    membership = db_session.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws.id,
        WorkspaceMember.user_id == user_id
    ).first()
    assert membership is not None
    assert membership.role == "MARKETER"

def test_register_creates_brand_kit(client, db_session):
    """Đăng ký tài khoản tự động khởi tạo Brand Kit mặc định cho Workspace."""
    payload = {
        "email": "brandkit_test@example.com",
        "password": "Password@123",
        "full_name": "Vũ BrandKit Test"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    ws = db_session.query(Workspace).filter(Workspace.owner_id == user_id).first()
    assert ws is not None

    bk = db_session.query(BrandKit).filter(BrandKit.workspace_id == ws.id).first()
    assert bk is not None
    assert bk.brand_name == "Vũ BrandKit Test"
    assert bk.tone_of_voice is not None

def test_register_duplicate_email_fails(client):
    """Đăng ký với email đã tồn tại bị từ chối với HTTP 400."""
    payload = {
        "email": "manager@ictu.edu.vn", # Email đã có từ seed data
        "password": "Password@123",
        "full_name": "Trùng Email"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400
    assert "đã được sử dụng" in resp.json()["detail"]

def test_register_invalid_email_format(client):
    """Đăng ký với định dạng email sai bị từ chối bởi Pydantic validation (HTTP 422)."""
    payload = {
        "email": "invalid-email-format",
        "password": "Password@123",
        "full_name": "Sai Email"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422

def test_register_short_password_fails(client):
    """Đăng ký với mật khẩu dưới 6 ký tự bị từ chối với HTTP 422."""
    payload = {
        "email": "short_pw@example.com",
        "password": "123", # < 6 ký tự
        "full_name": "Mật Khẩu Ngắn"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422

def test_register_agency_manager_role(client, db_session):
    """Đăng ký tài khoản với vai trò AGENCY_MANAGER thành công."""
    payload = {
        "email": "agency_mgr@example.com",
        "password": "Password@123",
        "full_name": "Agency Manager VIP",
        "role": "AGENCY_MANAGER"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    assert resp.json()["role"] == "AGENCY_MANAGER"

    user_id = resp.json()["id"]
    ws = db_session.query(Workspace).filter(Workspace.owner_id == user_id).first()
    membership = db_session.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws.id,
        WorkspaceMember.user_id == user_id
    ).first()
    assert membership.role == "AGENCY_MANAGER"

def test_register_client_approver_role(client):
    """Đăng ký tài khoản với vai trò CLIENT_APPROVER thành công."""
    payload = {
        "email": "client_appr@example.com",
        "password": "Password@123",
        "full_name": "Client Approver Partner",
        "role": "CLIENT_APPROVER"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    assert resp.json()["role"] == "CLIENT_APPROVER"

def test_register_admin_role_rejected(client):
    """Đăng ký tài khoản với vai trò ADMIN bị từ chối để chống leo thang đặc quyền."""
    payload = {
        "email": "hacker_admin@example.com",
        "password": "Password@123",
        "full_name": "Hacker Wanna Be Admin",
        "role": "ADMIN"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    # Bị chặn bởi Pydantic validation (422) hoặc Endpoint Security (403)
    assert resp.status_code in (403, 422)

def test_register_manager_role_rejected(client):
    """Đăng ký tài khoản với vai trò MANAGER bị từ chối để chống leo thang đặc quyền."""
    payload = {
        "email": "hacker_mgr@example.com",
        "password": "Password@123",
        "full_name": "Hacker Wanna Be Manager",
        "role": "MANAGER"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code in (403, 422)
