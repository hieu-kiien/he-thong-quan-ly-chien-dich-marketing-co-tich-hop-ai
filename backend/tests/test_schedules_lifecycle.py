"""Unit and Integration Tests for Complete Scheduling Lifecycle & Background Worker (FR08).
Tests schedule creation, cancellation, rescheduling, worker auto-execution, and content transition to PUBLISHED.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import Campaign, MarketingContent, MarketingSchedule
from app.services.scheduler.worker import (
    parse_scheduled_datetime,
    process_due_schedules,
    get_tz_from_name
)


@pytest.fixture
def manager_headers(client: TestClient) -> Dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": "manager@gmail.com", "password": "Manager@123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def approved_content(client: TestClient, manager_headers: Dict[str, str], db_session: Session) -> MarketingContent:
    """Helper fixture tạo nội dung ở trạng thái APPROVED sẵn sàng lập lịch."""
    content = MarketingContent(
        campaign_id=1,
        channel_id=1,
        title="Chiến dịch Khuyến mãi Lập lịch Mùa thu",
        body="Nội dung bài viết thử nghiệm tính năng lập lịch tự động",
        cta="Tìm hiểu ngay",
        status="APPROVED",
        created_by=1,
        workspace_id=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)
    return content


# ==============================================================================
# 1. Datetime Parsing Unit Tests (Worker)
# ==============================================================================

def test_01_parse_scheduled_datetime_formats():
    """Kiểm tra parse_scheduled_datetime xử lý chuẩn xác các định dạng thời gian và múi giờ."""
    # 1. ISO UTC với đuôi Z
    dt_z = parse_scheduled_datetime("2026-10-01T10:00:00Z")
    assert dt_z.tzinfo is not None
    assert dt_z.astimezone(timezone.utc).hour == 10

    # 2. ISO có offset tường minh (+07:00)
    dt_vn = parse_scheduled_datetime("2026-09-25T09:00:00+07:00")
    assert dt_vn.tzinfo is not None
    assert dt_vn.astimezone(timezone.utc).hour == 2

    # 3. YYYY-MM-DD HH:MM chuẩn
    dt_std = parse_scheduled_datetime("2026-10-05 10:00", tz_name="Asia/Ho_Chi_Minh")
    assert dt_std.year == 2026 and dt_std.month == 10 and dt_std.day == 5
    assert dt_std.hour == 10 and dt_std.minute == 0

    # 4. YYYY-MM-DD chỉ có ngày
    dt_date = parse_scheduled_datetime("2026-10-15")
    assert dt_date.year == 2026 and dt_date.month == 10 and dt_date.day == 15

    # 5. Format ngày Việt Nam DD/MM/YYYY HH:MM
    dt_vn_fmt = parse_scheduled_datetime("25/10/2026 14:30")
    assert dt_vn_fmt.day == 25 and dt_vn_fmt.month == 10 and dt_vn_fmt.hour == 14 and dt_vn_fmt.minute == 30

    # 6. Chuỗi rỗng hoặc sai định dạng văng ValueError
    with pytest.raises(ValueError):
        parse_scheduled_datetime("")

    with pytest.raises(ValueError):
        parse_scheduled_datetime("dinh-dang-sai-khong-the-doc")


# ==============================================================================
# 2. Scheduling Lifecycle API Endpoints (Create, Cancel, Reschedule)
# ==============================================================================

def test_02_schedule_creation_success(client: TestClient, manager_headers: Dict[str, str], approved_content: MarketingContent):
    """Lập lịch thành công cho nội dung đã APPROVED -> Trạng thái PLANNED."""
    payload = {
        "scheduled_at": "2026-12-01 10:00",
        "timezone": "Asia/Ho_Chi_Minh"
    }
    resp = client.post(f"/api/v1/contents/{approved_content.id}/schedule", json=payload, headers=manager_headers)
    assert resp.status_code == 201
    data = resp.json()

    assert data["content_id"] == approved_content.id
    assert data["status"] == "PLANNED"
    assert data["scheduled_at"] == "2026-12-01 10:00"


def test_03_schedule_creation_fails_if_not_approved(client: TestClient, manager_headers: Dict[str, str], db_session: Session):
    """Chặn lập lịch cho bài viết chưa APPROVED (AI_DRAFT hoặc IN_REVIEW) -> HTTP 400."""
    draft_content = MarketingContent(
        campaign_id=1,
        channel_id=1,
        title="Bản nháp chưa duyệt",
        body="Nội dung nháp",
        cta="Bấm ngay",
        status="AI_DRAFT",
        created_by=1,
        workspace_id=1
    )
    db_session.add(draft_content)
    db_session.commit()
    db_session.refresh(draft_content)

    resp = client.post(
        f"/api/v1/contents/{draft_content.id}/schedule",
        json={"scheduled_at": "2026-12-01 10:00", "timezone": "Asia/Ho_Chi_Minh"},
        headers=manager_headers
    )
    assert resp.status_code == 400
    assert "APPROVED" in resp.json()["detail"]


def test_04_cancel_schedule_success(client: TestClient, manager_headers: Dict[str, str], approved_content: MarketingContent, db_session: Session):
    """Hủy lịch đăng thành công qua POST /schedules/{id}/cancel và DELETE /schedules/{id}."""
    schedule = MarketingSchedule(
        content_id=approved_content.id,
        scheduled_at="2026-12-05 09:00",
        timezone="Asia/Ho_Chi_Minh",
        status="PLANNED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    # 1. Hủy qua POST /schedules/{id}/cancel
    resp = client.post(f"/api/v1/schedules/{schedule.id}/cancel", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "CANCELLED"

    # Kiểm tra nội dung liên kết vẫn giữ nguyên trạng thái APPROVED
    db_session.refresh(approved_content)
    assert approved_content.status == "APPROVED"

    # 2. Đưa lại về PLANNED và hủy qua DELETE /schedules/{id}
    schedule.status = "PLANNED"
    db_session.commit()

    resp_del = client.delete(f"/api/v1/schedules/{schedule.id}", headers=manager_headers)
    assert resp_del.status_code == 200
    assert resp_del.json()["status"] == "CANCELLED"


def test_05_cancel_already_executed_schedule_fails(client: TestClient, manager_headers: Dict[str, str], approved_content: MarketingContent, db_session: Session):
    """Không thể hủy lịch đăng đã thực thi (EXECUTED) -> HTTP 400."""
    executed_schedule = MarketingSchedule(
        content_id=approved_content.id,
        scheduled_at="2026-09-01 08:00",
        timezone="Asia/Ho_Chi_Minh",
        status="EXECUTED",
        created_by=1
    )
    db_session.add(executed_schedule)
    db_session.commit()
    db_session.refresh(executed_schedule)

    resp = client.post(f"/api/v1/schedules/{executed_schedule.id}/cancel", headers=manager_headers)
    assert resp.status_code == 400
    assert "EXECUTED" in resp.json()["detail"]


def test_06_reschedule_updates_time_and_resets_cancelled(client: TestClient, manager_headers: Dict[str, str], approved_content: MarketingContent, db_session: Session):
    """Dời lịch cập nhật thời gian và tự động đưa CANCELLED trở lại PLANNED."""
    schedule = MarketingSchedule(
        content_id=approved_content.id,
        scheduled_at="2026-12-10 10:00",
        timezone="Asia/Ho_Chi_Minh",
        status="CANCELLED",
        created_by=1
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    # Cập nhật thời gian mới qua PUT
    resp = client.put(
        f"/api/v1/schedules/{schedule.id}",
        json={"scheduled_at": "2026-12-25 15:00", "timezone": "Asia/Ho_Chi_Minh"},
        headers=manager_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["scheduled_at"] == "2026-12-25 15:00"
    assert data["status"] == "PLANNED"  # Tự động hồi phục từ CANCELLED -> PLANNED


def test_07_reschedule_executed_fails(client: TestClient, manager_headers: Dict[str, str], approved_content: MarketingContent, db_session: Session):
    """Không thể cập nhật hoặc dời lịch đã EXECUTED -> HTTP 400."""
    executed_schedule = MarketingSchedule(
        content_id=approved_content.id,
        scheduled_at="2026-09-01 08:00",
        timezone="Asia/Ho_Chi_Minh",
        status="EXECUTED",
        created_by=1
    )
    db_session.add(executed_schedule)
    db_session.commit()
    db_session.refresh(executed_schedule)

    resp = client.put(
        f"/api/v1/schedules/{executed_schedule.id}",
        json={"scheduled_at": "2026-12-30 10:00"},
        headers=manager_headers
    )
    assert resp.status_code == 400
    assert "EXECUTED" in resp.json()["detail"]


# ==============================================================================
# 3. Background Worker Auto-Execution Tests
# ==============================================================================

def test_08_worker_executes_due_schedules_and_publishes_content(db_session: Session):
    """Worker quét lịch đến hạn (scheduled_at <= now), chuyển schedule thành EXECUTED và bài viết thành PUBLISHED."""
    # 1. Tạo bài viết APPROVED
    content = MarketingContent(
        campaign_id=1,
        channel_id=1,
        title="Bài viết đến giờ xuất bản tự động",
        body="Nội dung sẽ được worker tự động chuyển sang PUBLISHED",
        cta="Đăng ký ngay",
        status="APPROVED",
        created_by=1,
        workspace_id=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    # 2. Tạo lịch với thời gian trong quá khứ (đã đến hạn)
    due_schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at="2026-01-01 00:00",
        timezone="Asia/Ho_Chi_Minh",
        status="PLANNED",
        created_by=1
    )
    db_session.add(due_schedule)
    db_session.commit()
    db_session.refresh(due_schedule)

    # 3. Kích hoạt worker xử lý
    processed = process_due_schedules(db_session)
    assert due_schedule.id in processed

    # 4. Kiểm chứng trạng thái sau khi worker chạy
    db_session.refresh(due_schedule)
    db_session.refresh(content)

    assert due_schedule.status == "EXECUTED"
    assert content.status == "PUBLISHED"


def test_09_worker_ignores_future_schedules(db_session: Session):
    """Worker không thực thi các lịch trong tương lai (scheduled_at > now)."""
    content = MarketingContent(
        campaign_id=1,
        channel_id=1,
        title="Bài viết chưa đến giờ",
        body="Chưa đến giờ đăng",
        cta="Chờ đợi",
        status="APPROVED",
        created_by=1,
        workspace_id=1
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)

    future_schedule = MarketingSchedule(
        content_id=content.id,
        scheduled_at="2099-01-01 12:00",
        timezone="Asia/Ho_Chi_Minh",
        status="PLANNED",
        created_by=1
    )
    db_session.add(future_schedule)
    db_session.commit()
    db_session.refresh(future_schedule)

    processed = process_due_schedules(db_session)
    assert future_schedule.id not in processed

    db_session.refresh(future_schedule)
    db_session.refresh(content)

    assert future_schedule.status == "PLANNED"
    assert content.status == "APPROVED"


def test_10_trigger_worker_endpoint(client: TestClient, manager_headers: Dict[str, str], approved_content: MarketingContent, db_session: Session):
    """Xác thực endpoint quản trị POST /schedules/trigger-worker hoạt động chuẩn xác."""
    # Tạo lịch đến hạn
    due_schedule = MarketingSchedule(
        content_id=approved_content.id,
        scheduled_at="2026-01-01 09:00",
        timezone="Asia/Ho_Chi_Minh",
        status="PLANNED",
        created_by=1
    )
    db_session.add(due_schedule)
    db_session.commit()
    db_session.refresh(due_schedule)

    resp = client.post("/api/v1/schedules/trigger-worker", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "processed_schedule_ids" in data
    assert due_schedule.id in data["processed_schedule_ids"]
    assert data["count"] >= 1


def test_11_nonexistent_schedule_returns_404(client: TestClient, manager_headers: Dict[str, str]):
    """Thao tác trên lịch không tồn tại trả về HTTP 404."""
    resp_cancel = client.post("/api/v1/schedules/999999/cancel", headers=manager_headers)
    assert resp_cancel.status_code == 404

    resp_update = client.put(
        "/api/v1/schedules/999999",
        json={"scheduled_at": "2026-12-01 10:00"},
        headers=manager_headers
    )
    assert resp_update.status_code == 404
