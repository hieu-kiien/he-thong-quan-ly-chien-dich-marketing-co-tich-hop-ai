"""Lịch đăng nội dung (lịch nội bộ — MarketFlow không tự đăng lên mạng xã hội)."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import (
    Conflict,
    InvalidTransition,
    NotFound,
    PermissionDenied,
    ValidationFailed,
)
from app.core.timeutil import (
    VN_TZ,
    local_date,
    now_utc,
    to_utc,
    vn_day_end_utc,
    vn_day_start_utc,
)
from app.models import Content, Schedule, User
from app.models.enums import ContentStatus, ScheduleStatus
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleDoneIn,
    ScheduleFilters,
    ScheduleOut,
    ScheduleUpdate,
)
from app.services import (
    campaign_service,
    content_service,
    notification_service,
    user_service,
)
from app.services.serializers import schedule_out

MAX_SCHEDULE_ITEMS = 1000
PAST_TOLERANCE = timedelta(minutes=5)
NOT_SCHEDULABLE = {ContentStatus.REJECTED, ContentStatus.PUBLISHED}


def get_schedule_orm(db: Session, schedule_id: int) -> Schedule:
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise NotFound("Không tìm thấy lịch đăng")
    return schedule


def can_manage(user: User, schedule: Schedule) -> bool:
    return user.is_manager or schedule.assignee_id == user.id or schedule.content.created_by == user.id


def _ensure_can_manage(user: User, schedule: Schedule) -> None:
    if not can_manage(user, schedule):
        raise PermissionDenied("Chỉ quản lý, người phụ trách lịch hoặc người tạo nội dung được thao tác lịch này")


def _ensure_planned(schedule: Schedule, action: str) -> None:
    if schedule.status != ScheduleStatus.PLANNED:
        raise InvalidTransition(f"Chỉ có thể {action} lịch đang ở trạng thái 'Đã lên lịch'")


def _validate_time(content: Content, scheduled_at: datetime) -> datetime:
    value = to_utc(scheduled_at)
    if value < now_utc() - PAST_TOLERANCE:
        raise ValidationFailed(fields={"scheduled_at": "Thời điểm đăng phải ở tương lai"})
    campaign = content.campaign
    day = local_date(value)
    if day < campaign.start_date or day > campaign.end_date:
        raise ValidationFailed(
            fields={
                "scheduled_at": (
                    f"Thời điểm đăng phải nằm trong thời gian chiến dịch "
                    f"({campaign.start_date:%d/%m/%Y} – {campaign.end_date:%d/%m/%Y})"
                )
            }
        )
    return value


def _notify_assignee(db: Session, user: User, assignee_id: int | None, content: Content, when: datetime) -> None:
    if assignee_id and assignee_id != user.id:
        local = when.astimezone(VN_TZ)
        notification_service.notify(
            db,
            [assignee_id],
            "SCHEDULE_ASSIGNED",
            f'{user.full_name} giao bạn đăng "{content.title}" lúc {local:%H:%M %d/%m/%Y}',
            "/calendar",
        )


# --- Đọc ----------------------------------------------------------------------

def list_schedules(db: Session, user: User, filters: ScheduleFilters | None = None) -> list[ScheduleOut]:
    filters = filters or ScheduleFilters()
    if filters.date_from and filters.date_to and filters.date_from > filters.date_to:
        raise ValidationFailed(fields={"date_to": "Ngày kết thúc phải sau hoặc bằng ngày bắt đầu"})
    stmt = select(Schedule).join(Content, Schedule.content_id == Content.id)
    if filters.date_from:
        stmt = stmt.where(Schedule.scheduled_at >= vn_day_start_utc(filters.date_from))
    if filters.date_to:
        stmt = stmt.where(Schedule.scheduled_at < vn_day_end_utc(filters.date_to))
    if filters.channel_id:
        stmt = stmt.where(Content.channel_id == filters.channel_id)
    if filters.campaign_id:
        stmt = stmt.where(Content.campaign_id == filters.campaign_id)
    if filters.assignee_id:
        stmt = stmt.where(Schedule.assignee_id == filters.assignee_id)
    if filters.status:
        stmt = stmt.where(Schedule.status == filters.status)
    stmt = stmt.order_by(Schedule.scheduled_at.asc(), Schedule.id.asc()).limit(MAX_SCHEDULE_ITEMS)
    return [schedule_out(s) for s in db.execute(stmt).unique().scalars()]


def get_schedule(db: Session, user: User, schedule_id: int) -> ScheduleOut:
    return schedule_out(get_schedule_orm(db, schedule_id))


# --- Ghi ----------------------------------------------------------------------

def create_schedule(db: Session, user: User, data: ScheduleCreate) -> ScheduleOut:
    content = db.get(Content, data.content_id)
    if content is None:
        raise ValidationFailed(fields={"content_id": "Nội dung không tồn tại"})
    if content.status in NOT_SCHEDULABLE:
        raise Conflict(
            f"Không thể lập lịch cho nội dung '{content_service.STATUS_LABELS[ContentStatus(content.status)]}'",
            code="CONTENT_NOT_SCHEDULABLE",
        )
    if content.campaign.status in campaign_service.CLOSED_STATUSES:
        raise Conflict("Chiến dịch đã kết thúc hoặc bị huỷ, không thể lập lịch", code="CAMPAIGN_CLOSED")
    scheduled_at = _validate_time(content, data.scheduled_at)
    assignee_id = data.assignee_id or user.id
    user_service.get_active_user(db, assignee_id)
    schedule = Schedule(
        content_id=content.id,
        scheduled_at=scheduled_at,
        assignee_id=assignee_id,
        status=ScheduleStatus.PLANNED,
        note=data.note or None,
    )
    db.add(schedule)
    _notify_assignee(db, user, assignee_id, content, scheduled_at)
    db.commit()
    db.refresh(schedule)
    return schedule_out(schedule)


def update_schedule(db: Session, user: User, schedule_id: int, data: ScheduleUpdate) -> ScheduleOut:
    schedule = get_schedule_orm(db, schedule_id)
    _ensure_can_manage(user, schedule)
    _ensure_planned(schedule, "sửa")
    fields = data.model_dump(exclude_unset=True)
    if fields.get("scheduled_at") is not None:
        schedule.scheduled_at = _validate_time(schedule.content, fields["scheduled_at"])
    if fields.get("assignee_id") is not None and fields["assignee_id"] != schedule.assignee_id:
        user_service.get_active_user(db, fields["assignee_id"])
        schedule.assignee_id = fields["assignee_id"]
        _notify_assignee(db, user, schedule.assignee_id, schedule.content, schedule.scheduled_at)
    if "note" in fields:
        schedule.note = fields["note"] or None
    db.commit()
    db.refresh(schedule)
    return schedule_out(schedule)


def complete_schedule(db: Session, user: User, schedule_id: int, data: ScheduleDoneIn | None = None) -> ScheduleOut:
    """Đánh dấu lịch đã thực hiện: nội dung phải APPROVED → chuyển PUBLISHED."""
    schedule = get_schedule_orm(db, schedule_id)
    _ensure_can_manage(user, schedule)
    _ensure_planned(schedule, "đánh dấu hoàn thành")
    content = schedule.content
    if content.status != ContentStatus.APPROVED:
        raise InvalidTransition("Nội dung phải được duyệt trước khi đánh dấu đã đăng")
    content_service.publish(db, user, content, data.published_url if data else None, None)
    db.commit()
    db.refresh(schedule)
    return schedule_out(schedule)


def cancel_schedule(db: Session, user: User, schedule_id: int) -> ScheduleOut:
    schedule = get_schedule_orm(db, schedule_id)
    _ensure_can_manage(user, schedule)
    _ensure_planned(schedule, "huỷ")
    schedule.status = ScheduleStatus.CANCELLED
    db.commit()
    db.refresh(schedule)
    return schedule_out(schedule)
