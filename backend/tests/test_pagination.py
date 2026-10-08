"""Phân trang: hợp đồng, thứ tự lọc/cắt trang, trần tham số, và cách ly tenant.

BA ĐIỀU DỄ SAI NHẤT KHI THÊM PHÂN TRANG VÀO MỘT ENDPOINT ĐÃ CÓ SẴN — và là
đúng ba nhóm kiểm thử dưới đây:

1. **Phân trang rồi mới lọc** (`total` sai, trang cuối rỗng bất thường).
   Nhóm `test_*_filters_compose_with_paging_*` kiểm tra rằng mọi bộ lọc được
   áp TRƯỚC khi offset/limit, nên `total` là tổng của tập đã lọc và các trang
   ghép lại đúng không trùng/mất dòng.

2. **Thiếu khoá sắp xếp** (một dòng xuất hiện ở cả trang 1 và trang 2).
   Nhóm `test_*_pages_have_no_duplicate_or_missing_rows` dựng tập dữ liệu lớn
   hơn `page_size` rồi kiểm tra tập `id` của mọi trang ghép lại bằng đúng tập id
   gốc.

3. **`page_size` không trần** (đường DoS trên instance 512 MB).
   Nhóm `test_page_size_is_capped` kiểm tra 422 khi vượt trần.

Ngoài ra có nhóm `test_pagination_preserves_tenant_isolation`: trang 2 phải
không mở ra dữ liệu của tenant khác — đây là chỗ off-by-one trong mệnh đề lọc
sẽ lộ ra ngay.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import Campaign, MarketingContent, User


# Endpoint đã áp hợp đồng `Page`. Tham số truyền kèm để test gọi đúng cách.
PAGINATED_ENDPOINTS = [
    ("/api/v1/campaigns", {}),
    ("/api/v1/contents", {}),
    ("/api/v1/campaigns/1/contents", {}),
    ("/api/v1/schedules", {}),
    ("/api/v1/notifications", {}),
    ("/api/v1/workspaces", {}),
    ("/api/v1/ai/jobs", {}),
    ("/api/v1/ai/logs", {}),
    ("/api/v1/settings/ai-keys/list", {}),
    ("/api/v1/tasks/my-tasks", {}),
]

PAGE_KEYS = {"items", "total", "page", "page_size", "total_pages", "has_next", "has_prev"}


# ==============================================================================
# 1. HỢP ĐỒNG ENVELOPE
# ==============================================================================
@pytest.mark.parametrize("endpoint,params", PAGINATED_ENDPOINTS)
def test_every_list_endpoint_returns_page_envelope(
    client: TestClient, manager_headers, endpoint, params
):
    """Mọi endpoint danh sách trả về envelope `Page` đầy đủ trường."""
    resp = client.get(endpoint, headers=manager_headers, params=params)
    assert resp.status_code == 200, f"{endpoint}: {resp.text}"
    body = resp.json()
    assert isinstance(body, dict), f"{endpoint} phải trả object, không phải mảng phẳng"
    assert PAGE_KEYS <= set(body.keys()), f"{endpoint} thiếu trường: {PAGE_KEYS - set(body)}"
    assert isinstance(body["items"], list)
    assert body["total"] >= 0
    # `total` là TỔNG sau lọc, không phải số dòng của trang: len(items) <= total.
    assert len(body["items"]) <= body["total"]
    # total_pages = ceil(total / page_size)
    if body["total"] == 0:
        assert body["total_pages"] == 0
    else:
        assert body["total_pages"] == -(-body["total"] // body["page_size"])
    # has_prev phải khớp page
    assert body["has_prev"] is (body["page"] > 1)


@pytest.mark.parametrize("endpoint,params", PAGINATED_ENDPOINTS)
def test_omitting_pagination_params_returns_usable_default_page(
    client: TestClient, manager_headers, endpoint, params
):
    """Client cũ bỏ qua tham số phân trang vẫn nhận trang đầu hợp lệ (tương thích ngược)."""
    resp = client.get(endpoint, headers=manager_headers)
    assert resp.status_code == 200, f"{endpoint}: {resp.text}"
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert len(body["items"]) <= 20


# ==============================================================================
# 2. TRẦN THAM SỐ (đường DoS)
# ==============================================================================
@pytest.mark.parametrize("endpoint,_", PAGINATED_ENDPOINTS)
def test_page_size_is_capped(client: TestClient, manager_headers, endpoint, _):
    """`page_size` vượt trần 100 phải bị từ chối bằng 422, không phải cắt âm thầm."""
    too_big = client.get(endpoint, headers=manager_headers, params={"page_size": 5000})
    assert too_big.status_code == 422, f"{endpoint} chấp nhận page_size=5000 — mất trần chống DoS"

    at_cap = client.get(endpoint, headers=manager_headers, params={"page_size": 100})
    assert at_cap.status_code == 200, f"{endpoint} phải chấp nhận page_size=100 (đúng trần)"


@pytest.mark.parametrize("endpoint,_", PAGINATED_ENDPOINTS)
def test_page_must_be_at_least_one(client: TestClient, manager_headers, endpoint, _):
    for bad in (0, -1):
        resp = client.get(endpoint, headers=manager_headers, params={"page": bad})
        assert resp.status_code == 422, f"{endpoint} chấp nhận page={bad}"


# ==============================================================================
# 3. LỌC + PHÂN TRANG ĐI VỚI NHAU (đúng thứ tự)
# ==============================================================================
def _seed_campaigns(db: Session, workspace_id: int, owner: User, count: int, tag: str):
    """Tạo `count` chiến dịch cùng workspace với tên có `tag` để đếm được."""
    created = []
    for i in range(count):
        c = Campaign(
            workspace_id=workspace_id,
            product_id=1,
            owner_id=owner.id,
            name=f"{tag}-{i:03d}",
            objective="Muc tieu kiem thu phan trang",
            audience="Doi tuong kiem thu",
            start_date="2026-01-01",
            end_date="2026-12-31",
            budget=1000 + i,
            status="DRAFT",
        )
        db.add(c)
        created.append(c)
    db.commit()
    for c in created:
        db.refresh(c)
    return created


def test_filters_compose_with_paging_total_reflects_filter_not_page(
    client: TestClient, db_session: Session, manager_headers, workspace_alpha
):
    """`total` phải là tổng SAU KHI LỌC, không phải tổng toàn bảng.

    Đây là phép kiểm tra trực tiếp cho lỗi "phân trang rồi mới lọc": nếu lọc
    chạy sau `limit`, `total` sẽ bằng số dòng của trang (tối đa `page_size`) và
    mọi trang sau sẽ rỗng.
    """
    owner = db_session.query(User).filter(User.email == "manager@gmail.com").first()
    _seed_campaigns(db_session, workspace_alpha.id, owner, count=12, tag="PAGECHECK")

    everything = client.get("/api/v1/campaigns", headers=manager_headers, params={"page_size": 100})
    assert everything.status_code == 200, everything.text
    total_all = everything.json()["total"]

    filtered = client.get(
        "/api/v1/campaigns", headers=manager_headers,
        params={"search": "PAGECHECK", "page_size": 5},
    )
    assert filtered.status_code == 200, filtered.text
    body = filtered.json()

    assert len(body["items"]) == 5
    assert body["total"] == 12, f"total phải bằng 12 (đúng số dòng khớp lọc), nhận {body['total']}"
    assert body["total"] > total_all - 12  # tổng toàn bảng lớn hơn tổng đã lọc
    assert body["total_pages"] == 3
    assert body["has_next"] is True
    assert body["has_prev"] is False

    # Trang 3 là lát cuối: đúng 2 dòng, has_next False.
    last = client.get(
        "/api/v1/campaigns", headers=manager_headers,
        params={"search": "PAGECHECK", "page_size": 5, "page": 3},
    )
    assert last.status_code == 200
    assert len(last.json()["items"]) == 2
    assert last.json()["has_next"] is False
    assert last.json()["has_prev"] is True


def test_pagination_cuts_a_page_not_the_whole_set(client: TestClient, db_session: Session, manager_headers, workspace_alpha):
    """Không có lọc: `total` = toàn bộ tập, mỗi trang = `page_size` dòng."""
    owner = db_session.query(User).filter(User.email == "manager@gmail.com").first()
    _seed_campaigns(db_session, workspace_alpha.id, owner, count=12, tag="WHOLE")

    everything = client.get("/api/v1/campaigns", headers=manager_headers, params={"page_size": 100})
    total = everything.json()["total"]
    assert total > 5, "Cần seed đủ dữ liệu để phép thử có ý nghĩa"

    page1 = client.get("/api/v1/campaigns", headers=manager_headers, params={"page_size": 5, "page": 1})
    assert len(page1.json()["items"]) == 5
    assert page1.json()["total"] == total
    assert page1.json()["total_pages"] == -(-total // 5)


def test_pages_have_no_duplicate_or_missing_rows(
    client: TestClient, db_session: Session, manager_headers, workspace_alpha
):
    """Sắp xếp ổn định: ghép mọi trang phải ra đúng tập id, không trùng không mất.

    Đây là phép kiểm tra cho lỗi thiếu khoá phá thế: nếu `ORDER BY` không có
    cột phá thế, CSDL tự chọn thứ tự khác nhau giữa hai lần truy vấn và một dòng
    có thể xuất hiện ở cả trang 1 lẫn trang 2 (hoặc mất hẳn).
    """
    owner = db_session.query(User).filter(User.email == "manager@gmail.com").first()
    seeded = _seed_campaigns(db_session, workspace_alpha.id, owner, count=11, tag="STABLE")

    baseline = client.get("/api/v1/campaigns", headers=manager_headers, params={"page_size": 100})
    expected_ids = {c["id"] for c in baseline.json()["items"]}
    total = baseline.json()["total"]
    assert seeded[0].id in expected_ids

    page_size = 4
    # Số trang phải tính TỪ `page_size` đang dùng, không dùng `total_pages` của
    # lần gọi `page_size=100` — nếu không sẽ duyệt thiếu trang và tưởng mất dòng.
    page_count = -(-total // page_size)

    collected = []
    for page in range(1, page_count + 1):
        resp = client.get(
            "/api/v1/campaigns", headers=manager_headers,
            params={"page_size": page_size, "page": page, "sort": "newest"},
        )
        assert resp.status_code == 200
        collected.extend(c["id"] for c in resp.json()["items"])

    assert len(collected) == len(set(collected)), "Có id lặp giữa các trang — thiếu khoá sắp xếp ổn định"
    assert set(collected) == expected_ids, "Ghép các trang không ra đúng tập id gốc"
    assert len(collected) == total


def test_page_beyond_last_returns_empty_items_not_error(
    client: TestClient, manager_headers
):
    """Trang vượt quá số trang: 200 + `items` rỗng (không phải lỗi, không phải 500)."""
    resp = client.get("/api/v1/campaigns", headers=manager_headers, params={"page": 9999, "page_size": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["has_next"] is False
    assert body["has_prev"] is True


def test_invalid_sort_is_rejected_with_422(client: TestClient, manager_headers):
    """`sort` là dữ liệu client: sai thì 422, không phải SQL lỗi 500."""
    resp = client.get("/api/v1/campaigns", headers=manager_headers, params={"sort": "id; DROP TABLE campaigns"})
    assert resp.status_code == 422, f"Sai phải là 422, nhận {resp.status_code}"

    contents = client.get("/api/v1/contents", headers=manager_headers, params={"sort": "DROP TABLE"})
    assert contents.status_code == 422


def test_sort_allowlist_actually_orders(client: TestClient, db_session: Session, manager_headers, workspace_alpha):
    """Các khoá sắp xếp trong allowlist trả về đúng thứ tự mong đợi."""
    by_name = client.get(
        "/api/v1/campaigns", headers=manager_headers,
        params={"sort": "name_asc", "page_size": 100},
    )
    names = [c["name"] for c in by_name.json()["items"]]
    assert names == sorted(names), "sort=name_asc phải trả tên tăng dần"

    by_budget = client.get(
        "/api/v1/campaigns", headers=manager_headers,
        params={"sort": "budget_desc", "page_size": 100},
    )
    budgets = [float(c["budget"]) for c in by_budget.json()["items"]]
    assert budgets == sorted(budgets, reverse=True), "sort=budget_desc phải trả ngân sách giảm dần"


# ==============================================================================
# 4. CÁCH LY TENANT QUA PHÂN TRANG (off-by-one trong mệnh đề lọc)
# ==============================================================================
def test_pagination_preserves_tenant_isolation(client: TestClient, rbac_headers, workspace_alpha, workspace_beta):
    """Mọi trang của user Beta đều không được chứa chiến dịch của Alpha.

    Chạy hết các trang chứ không chỉ trang 1: lỗi off-by-one trong mệnh đề lọc
    (ví dụ `offset` đặt trước điều kiện tenant) chỉ lộ ra ở trang thứ hai trở đi.
    """
    headers = rbac_headers["beta_marketer"]

    first = client.get("/api/v1/campaigns", headers=headers, params={"page_size": 2})
    assert first.status_code == 200, first.text
    total = first.json()["total"]
    total_pages = first.json()["total_pages"]

    seen_ids = set()
    for page in range(1, max(total_pages, 1) + 1):
        resp = client.get("/api/v1/campaigns", headers=headers, params={"page_size": 2, "page": page})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == total, "total phải ổn định giữa các trang"
        for row in body["items"]:
            assert row["workspace_id"] != workspace_alpha.id, (
                "TENANT LEAK: chiến dịch Workspace Alpha lọt vào danh sách phân trang của Beta"
            )
            assert row["id"] not in seen_ids, "Trùng id giữa các trang"
            seen_ids.add(row["id"])

    assert len(seen_ids) == total, f"Phải thấy đúng `total` dòng, thấy {len(seen_ids)}"


def test_pagination_with_workspace_filter_stays_in_workspace(
    client: TestClient, rbac_headers, workspace_alpha, workspace_beta
):
    """Lọc `workspace_id` + phân trang: mọi trang đều thuộc workspace được chỉ định.

    Dùng Agency Manager của Beta vì người dùng này thực sự là thành viên
    Workspace Beta — Manager của Alpha không có quyền xem workspace đó.
    """
    headers = rbac_headers["beta_agency_manager"]
    resp = client.get(
        "/api/v1/campaigns", headers=headers,
        params={"workspace_id": workspace_beta.id, "page_size": 2},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for row in body["items"]:
        assert row["workspace_id"] == workspace_beta.id


def test_paginated_list_still_requires_auth(client: TestClient):
    for endpoint, _ in PAGINATED_ENDPOINTS:
        resp = client.get(endpoint)
        assert resp.status_code == 401, f"{endpoint} không được bỏ qua xác thực"


def test_task_lists_paginate(client: TestClient, manager_headers, marketer_headers):
    """Hai endpoint tác vụ cũng dùng chung envelope."""
    for endpoint, headers in (
        ("/api/v1/campaigns/1/tasks", manager_headers),
        ("/api/v1/tasks/my-tasks", marketer_headers),
    ):
        resp = client.get(endpoint, headers=headers, params={"page_size": 3})
        assert resp.status_code == 200, f"{endpoint}: {resp.text}"
        body = resp.json()
        assert PAGE_KEYS <= set(body.keys())
        assert len(body["items"]) <= 3


def test_schedule_and_content_search_filters_compose(
    client: TestClient, db_session: Session, manager_headers
):
    """`search` mới trên nội dung + lọc trạng thái vẫn tính `total` đúng."""
    contents = client.get(
        "/api/v1/contents", headers=manager_headers,
        params={"search": "zzzz-khong-ton-tai", "page_size": 5},
    )
    assert contents.status_code == 200, contents.text
    assert contents.json()["total"] == 0
    assert contents.json()["items"] == []
    assert contents.json()["total_pages"] == 0

    everything = client.get("/api/v1/contents", headers=manager_headers, params={"page_size": 1})
    assert everything.status_code == 200
    body = everything.json()
    assert len(body["items"]) == 1
    assert body["total"] >= 1
    assert body["total_pages"] >= 1


def test_contents_scoped_by_campaign_keeps_total_consistent(
    client: TestClient, manager_headers
):
    """Lọc theo `campaign_id` rồi mới phân trang: `total` là số nội dung của riêng chiến dịch đó."""
    scoped = client.get(
        "/api/v1/campaigns/1/contents", headers=manager_headers, params={"page_size": 2}
    )
    assert scoped.status_code == 200, scoped.text
    body = scoped.json()
    for row in body["items"]:
        assert row["campaign_id"] == 1