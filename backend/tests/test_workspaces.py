"""
Test Suite: Workspace Management Tests (Milestone 1)
Covers:
- GET /api/v1/workspaces (listing)
- POST /api/v1/workspaces (creation, slug generation, brand kit init)
- GET /api/v1/workspaces/{id} (scoping & access check)
- PUT /api/v1/workspaces/{id} (permission check)
- POST /api/v1/workspaces/{id}/members (member addition)
"""

import pytest
from app.models.entities import Workspace, WorkspaceMember, BrandKit, User

def get_auth_headers(client, email="manager@ictu.edu.vn", password="Manager@123"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_list_workspaces_authenticated(client):
    """Người dùng đã đăng nhập lấy được danh sách workspace của mình."""
    headers = get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")
    resp = client.get("/api/v1/workspaces", headers=headers)
    assert resp.status_code == 200
    workspaces = resp.json()
    assert len(workspaces) >= 1
    assert any(w["id"] == 1 for w in workspaces)

def test_list_workspaces_unauthenticated_fails(client):
    """Truy cập danh sách workspace khi chưa xác thực trả về HTTP 401."""
    resp = client.get("/api/v1/workspaces")
    assert resp.status_code == 401

def test_create_workspace_success(client, db_session):
    """Tạo workspace mới thành công trả về HTTP 201."""
    headers = get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")
    payload = {
        "name": "VinFast Auto Brand",
        "slug": "vinfast-auto",
        "description": "Không gian chiến dịch xe điện thông minh"
    }
    resp = client.post("/api/v1/workspaces", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "VinFast Auto Brand"
    assert data["slug"] == "vinfast-auto"
    assert data["id"] is not None

    # Xác minh người tạo là AGENCY_MANAGER trong workspace_members
    membership = db_session.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == data["id"]
    ).first()
    assert membership is not None
    assert membership.role == "AGENCY_MANAGER"

def test_create_workspace_auto_generates_slug(client):
    """Tạo workspace không truyền slug sẽ tự động sinh slug hợp lệ."""
    headers = get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")
    payload = {
        "name": "Tiki E-Commerce Workspace",
        "description": "Sàn thương mại điện tử"
    }
    resp = client.post("/api/v1/workspaces", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] is not None
    assert "tiki" in data["slug"]

def test_create_workspace_auto_initializes_brand_kit(client, db_session):
    """Tạo workspace mới tự động khởi tạo Brand Kit trong CSDL."""
    headers = get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")
    payload = {
        "name": "Shopee Mall Campaign",
        "slug": "shopee-mall"
    }
    resp = client.post("/api/v1/workspaces", json=payload, headers=headers)
    assert resp.status_code == 201
    ws_id = resp.json()["id"]

    bk = db_session.query(BrandKit).filter(BrandKit.workspace_id == ws_id).first()
    assert bk is not None
    assert bk.brand_name == "Shopee Mall Campaign"

def test_get_workspace_by_id_owner(client):
    """Chủ sở hữu có quyền xem chi tiết workspace."""
    headers = get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")
    resp = client.get("/api/v1/workspaces/1", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == 1

def test_get_workspace_by_id_non_member_forbidden(client):
    """Người dùng không phải thành viên bị từ chối truy cập workspace với HTTP 403."""
    # Đăng ký một user độc lập không thuộc workspace 1
    reg_payload = {
        "email": "outsider@example.com",
        "password": "Password@123",
        "full_name": "Người Ngoài Cuộc"
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201

    outsider_headers = get_auth_headers(client, "outsider@example.com", "Password@123")
    # Cố gắng truy cập workspace 1 (thuộc manager/marketer)
    # Lưu ý: outsider chỉ là member của workspace cá nhân mình, không phải workspace 1
    resp = client.get("/api/v1/workspaces/1", headers=outsider_headers)
    assert resp.status_code == 403
    assert "không có quyền" in resp.json()["detail"]

def test_update_workspace_by_manager(client):
    """Quản lý có quyền cập nhật thông tin Workspace."""
    headers = get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")
    payload = {
        "name": "Không gian Tiếp thị Cập Nhật",
        "description": "Mô tả mới đã cập nhật"
    }
    resp = client.put("/api/v1/workspaces/1", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Không gian Tiếp thị Cập Nhật"

def test_update_workspace_by_marketer_forbidden(client):
    """Marketer không có quyền quản trị bị chặn khi cập nhật Workspace (HTTP 403)."""
    headers = get_auth_headers(client, "marketer@ictu.edu.vn", "Marketer@123")
    payload = {
        "name": "Marketer Cố Tình Đổi Tên",
        "description": "Thao tác trái quyền"
    }
    resp = client.put("/api/v1/workspaces/1", json=payload, headers=headers)
    assert resp.status_code == 403

def test_add_workspace_member_success(client, db_session):
    """Quản lý thêm thành viên mới vào workspace thành công, thêm trùng lặp bị từ chối."""
    headers = get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")

    # Đăng ký tài khoản mới để thêm vào workspace
    reg_payload = {
        "email": "collaborator@example.com",
        "password": "Password@123",
        "full_name": "Cộng Tác Viên"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # Thêm vào workspace 1
    add_payload = {
        "email": "collaborator@example.com",
        "role": "MARKETER"
    }
    resp = client.post("/api/v1/workspaces/1/members", json=add_payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["role"] == "MARKETER"

    # Thêm lại lần 2 bị chặn trùng lặp với HTTP 400
    resp_dup = client.post("/api/v1/workspaces/1/members", json=add_payload, headers=headers)
    assert resp_dup.status_code == 400
    assert "đã là thành viên" in resp_dup.json()["detail"]
