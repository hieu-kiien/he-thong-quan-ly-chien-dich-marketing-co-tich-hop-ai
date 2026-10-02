"""
Test Suite: X-Workspace-Id header chọn workspace hiện hành cho endpoint list.

Bối cảnh: frontend gửi `X-Workspace-Id` tự động từ workspace người dùng đang
chọn trên `WorkspaceSwitcher` (xem interceptor trong
`frontend/src/services/api.ts`). Trước khi `get_workspace_filter` được thêm, chỉ
`POST /campaigns` đọc header này; các endpoint LIST bỏ qua, nên đổi workspace trên
giao diện không làm thay đổi dữ liệu hiển thị — bộ chuyển workspace trông như
hoạt động nhưng không có tác dụng.

Các test dưới đây khoá lại hành vi đó, đồng thời kiểm tra fail-closed: không có
header thì trả về phạm vi rộng, nhưng header trỏ tới workspace người dùng không
thuộc về thì phải bị 403 chứ không được âm thầm bỏ qua.
"""

import pytest
from app.models.entities import Campaign, User


def _login(client, email: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def dual_workspace_user(client, db_session, workspace_alpha, workspace_beta):
    """Người dùng là thành viên của CẢ alpha và beta, mỗi workspace có 1 chiến dịch riêng.

    Điều kiện "thuộc cả hai" là mấu chốt: nếu chỉ thuộc một workspace thì việc lọc
    theo workspace thứ hai sẽ bị chặn bởi kiểm tra quyền và test không chứng minh
    được rằng header thật sự thay đổi tập kết quả.
    """
    from app.models.entities import WorkspaceMember, Product

    email = "multi_ws_user@gmail.com"
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            full_name="User Hai Workspace",
            password_hash=__import__("app.core.security", fromlist=["hash_password"]).hash_password("MultiWs@123"),
            role="MANAGER",
            status="ACTIVE",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    for ws in (workspace_alpha, workspace_beta):
        already = db_session.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == ws.id,
            WorkspaceMember.user_id == user.id,
        ).first()
        if not already:
            db_session.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="MANAGER"))
    db_session.commit()

    product = db_session.query(Product).first()
    assert product is not None, "Seed data phải có ít nhất một sản phẩm"

    created = []
    for ws, marker in ((workspace_alpha, "ALPHA"), (workspace_beta, "BETA")):
        name = f"Campaign only in {marker}"
        existing = db_session.query(Campaign).filter(Campaign.name == name).first()
        if not existing:
            camp = Campaign(
                workspace_id=ws.id,
                product_id=product.id,
                owner_id=user.id,
                name=name,
                objective=f"Objective {marker}",
                audience=f"Audience {marker}",
                start_date="2026-09-01",
                end_date="2026-09-30",
                budget=1_000_000,
                status="ACTIVE",
            )
            db_session.add(camp)
            db_session.commit()
            created.append(camp)

    return {"user": user, "alpha": workspace_alpha, "beta": workspace_beta, "created": created}


def _header(headers: dict, workspace_id: int) -> dict:
    return {**headers, "X-Workspace-Id": str(workspace_id)}


def test_campaigns_list_follows_workspace_header(client, dual_workspace_user):
    """GET /campaigns phải trả dữ liệu ĐÚNG workspace trỏ bởi X-Workspace-Id."""
    headers = _login(client, "multi_ws_user@gmail.com", "MultiWs@123")
    alpha, beta = dual_workspace_user["alpha"], dual_workspace_user["beta"]

    alpha_resp = client.get("/api/v1/campaigns", headers=_header(headers, alpha.id))
    beta_resp = client.get("/api/v1/campaigns", headers=_header(headers, beta.id))

    assert alpha_resp.status_code == 200, alpha_resp.text
    assert beta_resp.status_code == 200, beta_resp.text

    alpha_names = {c["name"] for c in alpha_resp.json()}
    beta_names = {c["name"] for c in beta_resp.json()}

    assert "Campaign only in ALPHA" in alpha_names
    assert "Campaign only in ALPHA" not in beta_names, (
        "Workspace BETA không được nhận campaign thuộc ALPHA khi header trỏ sang BETA"
    )
    assert "Campaign only in BETA" in beta_names
    assert "Campaign only in BETA" not in alpha_names

    # Hai workspace phải trả về hai tập khác nhau, tức header có tác dụng thật.
    assert alpha_names != beta_names


def test_contents_list_follows_workspace_header(client, dual_workspace_user):
    """GET /contents cũng phải tôn trọng X-Workspace-Id."""
    headers = _login(client, "multi_ws_user@gmail.com", "MultiWs@123")
    alpha, beta = dual_workspace_user["alpha"], dual_workspace_user["beta"]

    for ws in (alpha, beta):
        resp = client.get("/api/v1/contents", headers=_header(headers, ws.id))
        assert resp.status_code == 200, resp.text
        for item in resp.json():
            assert item.get("workspace_id") in (None, ws.id), (
                f"GET /contents?ws={ws.id} trả về nội dung của workspace "
                f"{item.get('workspace_id')}"
            )


def test_query_param_takes_precedence_over_header(client, dual_workspace_user):
    """Query param `workspace_id` thắng header (gọi API trực tiếp phải có quyền ưu tiên)."""
    headers = _login(client, "multi_ws_user@gmail.com", "MultiWs@123")
    alpha, beta = dual_workspace_user["alpha"], dual_workspace_user["beta"]

    # Header trỏ BETA nhưng query param trỏ ALPHA -> phải theo ALPHA.
    resp = client.get(
        f"/api/v1/campaigns?workspace_id={alpha.id}",
        headers=_header(headers, beta.id),
    )
    assert resp.status_code == 200, resp.text
    names = {c["name"] for c in resp.json()}
    assert "Campaign only in ALPHA" in names
    assert "Campaign only in BETA" not in names


def test_malformed_header_is_rejected_not_ignored(client, dual_workspace_user):
    """Header không phải số phải trả 400 chứ không âm thầm bị bỏ qua."""
    headers = _login(client, "multi_ws_user@gmail.com", "MultiWs@123")
    resp = client.get("/api/v1/campaigns", headers=_header(headers, "abc"))
    assert resp.status_code == 400, f"Mong đợi 400, nhận {resp.status_code}: {resp.text}"


def test_header_for_foreign_workspace_is_forbidden(client, dual_workspace_user, db_session):
    """Header trỏ workspace người dùng KHÔNG thuộc về phải bị 403 (fail-closed).

    Đây là kiểm tra bảo mật quan trọng nhất của nhóm test: nếu backend chỉ "nhận"
    header mà không kiểm tra quyền, client có thể tự dùng nó để đọc dữ liệu của
    tenant khác. Test tự tạo workspace thứ ba thay vì skip, vì skip ở đây đồng
    nghĩa với việc im lặng bỏ trống một lỗ hổng.
    """
    from app.models.entities import Workspace

    headers = _login(client, "multi_ws_user@gmail.com", "MultiWs@123")

    # Tạo workspace thứ ba mà user này KHÔNG phải owner lẫn thành viên.
    foreign = db_session.query(Workspace).filter(
        Workspace.id.notin_([dual_workspace_user["alpha"].id, dual_workspace_user["beta"].id])
    ).first()
    created = False
    if foreign is None:
        # Cần một user THẬT làm chủ sở hữu: owner_id là khoá ngoại nên không thể
        # dùng id giả (SQLite sẽ ném IntegrityError trước khi test kịp kiểm tra).
        from app.core.security import hash_password

        other_email = "other_tenant_owner@gmail.com"
        other = db_session.query(User).filter(User.email == other_email).first()
        if not other:
            other = User(
                email=other_email,
                full_name="Chu S\u1ed1 H\u1eefu Tenant Kh\u00e1c",
                password_hash=hash_password("OtherTenant@123"),
                role="MANAGER",
                status="ACTIVE",
            )
            db_session.add(other)
            db_session.commit()
            db_session.refresh(other)

        foreign = Workspace(
            name="Workspace C\u1ee7a Tenant Kh\u00e1c",
            slug="tenant-khac-abc",
            description="Kh\u00f4ng li\u00ean quan t\u1edbi user d\u01b0\u1edbi test",
            owner_id=other.id,
            status="ACTIVE",
        )
        db_session.add(foreign)
        db_session.commit()
        db_session.refresh(foreign)
        created = True

    try:
        resp = client.get("/api/v1/campaigns", headers=_header(headers, foreign.id))
        assert resp.status_code == 403, (
            f"Header trỏ workspace ngoài phạm vi phải bị 403, nhận {resp.status_code}: {resp.text}"
        )
    finally:
        if created:
            db_session.delete(foreign)
            db_session.commit()


def test_absent_header_still_returns_own_workspaces_only(client, dual_workspace_user):
    """Không có header thì vẫn phải giữ tenant scope (không rơi về toàn bộ tenant)."""
    headers = _login(client, "multi_ws_user@gmail.com", "MultiWs@123")
    resp = client.get("/api/v1/campaigns", headers=headers)
    assert resp.status_code == 200, resp.text
    names = {c["name"] for c in resp.json()}
    assert "Campaign only in ALPHA" in names
    assert "Campaign only in BETA" in names
