"""
Test Suite: Brand Kit Management Tests (Milestone 1)
Covers:
- GET /api/v1/brand-kit
- PUT /api/v1/brand-kit (RBAC: Only manager/owner)
- Banned keywords JSON serialization/deserialization
- Auto-initialization
"""

import json
import pytest
from app.models.entities import BrandKit, Workspace, WorkspaceMember

def get_auth_headers(client, email="manager@ictu.edu.vn", password="Manager@123"):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_get_brand_kit_default_workspace(client):
    """Lấy Brand Kit của Workspace mặc định thành công, trả về mảng banned_keywords."""
    headers = get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")
    resp = client.get("/api/v1/brand-kit?workspace_id=1", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["brand_name"] == "MarketFlow AI"
    assert isinstance(data["banned_keywords"], list)
    assert len(data["banned_keywords"]) > 0
    assert "cam kết 100%" in data["banned_keywords"]

def test_get_brand_kit_unauthenticated_fails(client):
    """Truy cập Brand Kit khi chưa đăng nhập trả về HTTP 401."""
    resp = client.get("/api/v1/brand-kit?workspace_id=1")
    assert resp.status_code == 401

def test_get_brand_kit_non_member_forbidden(client):
    """Người dùng ngoài workspace bị từ chối xem Brand Kit (HTTP 403)."""
    # Đăng ký tài khoản ngoài
    client.post("/api/v1/auth/register", json={
        "email": "external_user@example.com",
        "password": "Password@123",
        "full_name": "Người Ngoài"
    })
    ext_headers = get_auth_headers(client, "external_user@example.com", "Password@123")

    resp = client.get("/api/v1/brand-kit?workspace_id=1", headers=ext_headers)
    assert resp.status_code == 403

def test_update_brand_kit_by_manager_success(client, db_session):
    """Quản lý cập nhật thành công Brand Kit (USP, Tone, Blacklist)."""
    headers = get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")
    payload = {
        "brand_name": "MarketFlow AI Enterprise",
        "usp": "Hệ sinh thái MarTech số 1 Đông Nam Á",
        "tone_of_voice": "Mạnh mẽ, đột phá, chuẩn doanh nghiệp",
        "banned_keywords": ["rẻ nhất", "chữa bệnh", "cam kết 100%"]
    }
    resp = client.put("/api/v1/brand-kit?workspace_id=1", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["brand_name"] == "MarketFlow AI Enterprise"
    assert data["usp"] == "Hệ sinh thái MarTech số 1 Đông Nam Á"
    assert "rẻ nhất" in data["banned_keywords"]

    # Kiểm tra CSDL lưu dưới dạng chuỗi JSON
    bk = db_session.query(BrandKit).filter(BrandKit.workspace_id == 1).first()
    assert bk is not None
    assert json.loads(bk.banned_keywords_json) == ["rẻ nhất", "chữa bệnh", "cam kết 100%"]

def test_update_brand_kit_by_marketer_forbidden(client):
    """Marketer không có quyền quản trị bị chặn khi cập nhật Brand Kit (HTTP 403)."""
    headers = get_auth_headers(client, "marketer@ictu.edu.vn", "Marketer@123")
    payload = {
        "brand_name": "Marketer Hack Brand Kit",
        "tone_of_voice": "Thao tác trái quyền"
    }
    resp = client.put("/api/v1/brand-kit?workspace_id=1", json=payload, headers=headers)
    assert resp.status_code == 403

def test_brand_kit_banned_keywords_json_serialization(client, db_session):
    """Đảm bảo việc tuần tự hóa và giải mã JSON của danh sách từ khóa cấm hoạt động trơn tru."""
    headers = get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")
    custom_keywords = ["từ khóa 1", "từ khóa 2 đặc biệt: #@!"]
    payload = {
        "banned_keywords": custom_keywords
    }
    resp = client.put("/api/v1/brand-kit?workspace_id=1", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["banned_keywords"] == custom_keywords

    # Truy vấn lại bằng GET
    get_resp = client.get("/api/v1/brand-kit?workspace_id=1", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["banned_keywords"] == custom_keywords

def test_brand_kit_auto_create_if_missing(client, db_session):
    """Nếu workspace chưa có Brand Kit, GET tự động khởi tạo bản ghi mặc định."""
    # Tạo workspace mới qua DB mà chưa có Brand Kit
    headers = get_auth_headers(client, "manager@ictu.edu.vn", "Manager@123")
    raw_ws = Workspace(
        name="Workspace Thủ Công Chưa Có Kit",
        slug="manual-no-kit",
        owner_id=1,
        status="ACTIVE"
    )
    db_session.add(raw_ws)
    db_session.commit()
    db_session.refresh(raw_ws)

    # Thêm manager làm member
    mem = WorkspaceMember(workspace_id=raw_ws.id, user_id=1, role="AGENCY_MANAGER")
    db_session.add(mem)
    db_session.commit()

    # GET /brand-kit
    resp = client.get(f"/api/v1/brand-kit?workspace_id={raw_ws.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["brand_name"] == "Workspace Thủ Công Chưa Có Kit"
    assert resp.json()["workspace_id"] == raw_ws.id
