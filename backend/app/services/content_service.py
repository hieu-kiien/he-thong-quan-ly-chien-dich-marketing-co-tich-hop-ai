"""Nội dung marketing & quy trình duyệt (DRAFT → PENDING_REVIEW → APPROVED/REJECTED → PUBLISHED)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import (
    Conflict,
    InvalidTransition,
    NotFound,
    PermissionDenied,
    ValidationFailed,
)
from app.core.pagination import Page, apply_sort, paginate
from app.core.timeutil import now_utc, to_utc
from app.models import Campaign, Channel, Content, ContentReview, Schedule, User
from app.models.enums import (
    ContentOrigin,
    ContentStatus,
    ReviewDecision,
    ScheduleStatus,
)
from app.schemas.content import (
    ApproveIn,
    BannedMatch,
    ContentCreate,
    ContentFilters,
    ContentOut,
    ContentReviewOut,
    ContentUpdate,
    MarkPublishedIn,
    RejectIn,
    SubmitOut,
)
from app.services import (
    brand_service,
    campaign_service,
    channel_service,
    notification_service,
    user_service,
)
from app.services.common import like_pattern
from app.services.serializers import content_out, review_out

STATUS_LABELS = {
    ContentStatus.DRAFT: "Nháp",
    ContentStatus.PENDING_REVIEW: "Chờ duyệt",
    ContentStatus.APPROVED: "Đã duyệt",
    ContentStatus.REJECTED: "Bị từ chối",
    ContentStatus.PUBLISHED: "Đã đăng",
}

MANAGER_EDITABLE = {ContentStatus.DRAFT, ContentStatus.PENDING_REVIEW, ContentStatus.REJECTED}
CREATOR_EDITABLE = {ContentStatus.DRAFT, ContentStatus.REJECTED}
DELETABLE = {ContentStatus.DRAFT, ContentStatus.REJECTED}
SUBMITTABLE = {ContentStatus.DRAFT, ContentStatus.REJECTED}


def _transition_error(content: Content, action: str) -> InvalidTransition:
    return InvalidTransition(
        f"Không thể {action} nội dung đang ở trạng thái '{STATUS_LABELS[ContentStatus(content.status)]}'"
    )


# --- Truy vấn nội bộ ----------------------------------------------------------

def get_content_orm(db: Session, content_id: int) -> Content:
    content = db.get(Content, content_id)
    if content is None:
        raise NotFound("Không tìm thấy nội dung")
    return content


def _validate_target(
    db: Session, campaign_id: int, channel_id: int | None, channel_code: str | None, prefix: str = ""
) -> tuple[Campaign, Channel]:
    campaign = campaign_service.find_campaign_for_reference(db, campaign_id, field=f"{prefix}campaign_id")
    if campaign.status in campaign_service.CLOSED_STATUSES:
        raise Conflict(
            f"Chiến dịch '{campaign.name}' đã kết thúc hoặc bị huỷ, không thể thêm/sửa nội dung",
            code="CAMPAIGN_CLOSED",
        )
    field = f"{prefix}channel_id" if channel_id is not None or not channel_code else f"{prefix}channel_code"
    channel = channel_service.resolve_channel(db, channel_id, channel_code, field=field)
    if channel.id not in campaign_service.campaign_channel_ids(campaign):
        raise ValidationFailed(fields={field: f"Kênh {channel.name} không thuộc chiến dịch '{campaign.name}'"})
    return campaign, channel


def is_planned_assignee(db: Session, user: User, content_id: int) -> bool:
    return (
        db.execute(
            select(Schedule.id).where(
                Schedule.content_id == content_id,
                Schedule.assignee_id == user.id,
                Schedule.status == ScheduleStatus.PLANNED,
            )
        ).first()
        is not None
    )


def can_edit(user: User, content: Content) -> bool:
    if user.is_manager:
        return content.status in MANAGER_EDITABLE
    return content.created_by == user.id and content.status in CREATOR_EDITABLE


def _ensure_can_edit(user: User, content: Content) -> None:
    if not user.is_manager and content.created_by != user.id:
        raise PermissionDenied("Bạn chỉ được sửa nội dung do mình tạo")
    allowed = MANAGER_EDITABLE if user.is_manager else CREATOR_EDITABLE
    if content.status not in allowed:
        raise Conflict(
            f"Nội dung đang ở trạng thái '{STATUS_LABELS[ContentStatus(content.status)]}' nên không thể sửa",
            code="CONTENT_LOCKED",
        )


def publish(db: Session, user: User, content: Content, published_url: str | None, published_at: datetime | None) -> None:
    """APPROVED → PUBLISHED và đánh dấu các lịch PLANNED của nội dung là DONE (không commit)."""
    if content.status != ContentStatus.APPROVED:
        raise _transition_error(content, "đánh dấu đã đăng")
    now = now_utc()
    if published_at is not None:
        published_at = to_utc(published_at)
        if published_at > now + timedelta(minutes=5):
            raise ValidationFailed(fields={"published_at": "Thời điểm đăng không được ở tương lai"})
    content.status = ContentStatus.PUBLISHED
    content.published_url = published_url or None
    content.published_at = published_at or now
    content.published_by = user.id
    for schedule in db.execute(
        select(Schedule).where(Schedule.content_id == content.id, Schedule.status == ScheduleStatus.PLANNED)
    ).scalars():
        schedule.status = ScheduleStatus.DONE
        schedule.done_at = now


def _notify_managers_pending(db: Session, user: User, content: Content) -> None:
    managers = [mid for mid in user_service.active_manager_ids(db) if mid != user.id]
    notification_service.notify(
        db,
        managers,
        "CONTENT_SUBMITTED",
        f'{user.full_name} gửi duyệt nội dung "{content.title}"',
        f"/contents/{content.id}",
    )


# --- Đọc ----------------------------------------------------------------------

SORT_FIELDS = {
    "created_at": Content.created_at,
    "updated_at": Content.updated_at,
    "title": Content.title,
    "status": Content.status,
}


def list_contents(
    db: Session,
    user: User,
    filters: ContentFilters | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: str | None = None,
) -> Page[ContentOut]:
    filters = filters or ContentFilters()
    stmt = select(Content)
    if filters.campaign_id:
        stmt = stmt.where(Content.campaign_id == filters.campaign_id)
    channel_id = filters.channel_id
    if channel_id is None and filters.channel_code:
        channel = channel_service.find_by_code(db, filters.channel_code)
        channel_id = channel.id if channel else -1
    if channel_id is not None:
        stmt = stmt.where(Content.channel_id == channel_id)
    if filters.status:
        stmt = stmt.where(Content.status == filters.status)
    if filters.origin:
        stmt = stmt.where(Content.origin == filters.origin)
    if filters.created_by:
        stmt = stmt.where(Content.created_by == filters.created_by)
    if filters.q:
        pattern = like_pattern(filters.q)
        stmt = stmt.where(or_(Content.title.ilike(pattern, escape="\\"), Content.body.ilike(pattern, escape="\\")))
    stmt = apply_sort(stmt, sort, SORT_FIELDS, "-updated_at", Content.id)
    items, total = paginate(db, stmt, page, page_size)
    return Page[ContentOut](items=[content_out(c) for c in items], total=total, page=page, page_size=page_size)


def get_content(db: Session, user: User, content_id: int) -> ContentOut:
    return content_out(get_content_orm(db, content_id))


def list_reviews(db: Session, user: User, content_id: int) -> list[ContentReviewOut]:
    get_content_orm(db, content_id)
    rows = db.execute(
        select(ContentReview)
        .where(ContentReview.content_id == content_id)
        .order_by(ContentReview.created_at.desc(), ContentReview.id.desc())
    ).scalars()
    return [review_out(r) for r in rows]


def check_banned(db: Session, text: str) -> list[BannedMatch]:
    return brand_service.check_banned(db, text)


def _content_text(content: Content) -> str:
    return "\n".join(part for part in (content.title, content.body, content.cta or "") if part)


# --- Ghi ----------------------------------------------------------------------

def _build_content(
    db: Session,
    user: User,
    data: ContentCreate,
    origin: ContentOrigin,
    ai_message_id: int | None,
    submit: bool,
    prefix: str = "",
) -> Content:
    campaign, channel = _validate_target(db, data.campaign_id, data.channel_id, data.channel_code, prefix)
    content = Content(
        campaign_id=campaign.id,
        channel_id=channel.id,
        content_type=data.content_type,
        title=data.title,
        body=data.body,
        cta=data.cta or None,
        status=ContentStatus.PENDING_REVIEW if submit else ContentStatus.DRAFT,
        origin=origin,
        ai_message_id=ai_message_id,
        created_by=user.id,
    )
    db.add(content)
    return content


def create_content(
    db: Session,
    user: User,
    data: ContentCreate,
    *,
    origin: ContentOrigin = ContentOrigin.MANUAL,
    ai_message_id: int | None = None,
    submit: bool = False,
) -> ContentOut:
    """Tạo nội dung. `submit=True` → tạo thẳng ở trạng thái PENDING_REVIEW (dùng khi xác nhận đề xuất AI)."""
    return create_contents(db, user, [data], origin=origin, ai_message_id=ai_message_id, submit=submit)[0]


def create_contents(
    db: Session,
    user: User,
    items: Sequence[ContentCreate],
    *,
    origin: ContentOrigin = ContentOrigin.MANUAL,
    ai_message_id: int | None = None,
    submit: bool = False,
) -> list[ContentOut]:
    """Tạo nhiều nội dung trong một giao dịch (lỗi một mục → không tạo mục nào)."""
    try:
        created = [
            _build_content(db, user, item, origin, ai_message_id, submit, prefix=f"items.{i}." if len(items) > 1 else "")
            for i, item in enumerate(items)
        ]
        db.flush()
        if submit:
            for content in created:
                _notify_managers_pending(db, user, content)
        db.commit()
    except Exception:
        db.rollback()
        raise
    for content in created:
        db.refresh(content)
    return [content_out(c) for c in created]


def update_content(db: Session, user: User, content_id: int, data: ContentUpdate) -> ContentOut:
    content = get_content_orm(db, content_id)
    _ensure_can_edit(user, content)
    fields = data.model_dump(exclude_unset=True)
    if fields.get("campaign_id") is not None or fields.get("channel_id") is not None:
        campaign_id = fields.get("campaign_id") or content.campaign_id
        channel_id = fields.get("channel_id") or content.channel_id
        _validate_target(db, campaign_id, channel_id, None)
        content.campaign_id = campaign_id
        content.channel_id = channel_id
    for key in ("content_type", "title", "body"):
        if fields.get(key) is not None:
            setattr(content, key, fields[key])
    if "cta" in fields:
        content.cta = fields["cta"] or None
    db.commit()
    db.refresh(content)
    return content_out(content)


def delete_content(db: Session, user: User, content_id: int) -> None:
    content = get_content_orm(db, content_id)
    if not user.is_manager and content.created_by != user.id:
        raise PermissionDenied("Bạn chỉ được xoá nội dung do mình tạo")
    if content.status not in DELETABLE:
        raise Conflict("Chỉ xoá được nội dung ở trạng thái Nháp hoặc Bị từ chối", code="CONTENT_LOCKED")
    db.delete(content)
    db.commit()


def submit_content(db: Session, user: User, content_id: int) -> SubmitOut:
    content = get_content_orm(db, content_id)
    if content.created_by != user.id:
        raise PermissionDenied("Chỉ người tạo nội dung mới được gửi duyệt")
    if content.status not in SUBMITTABLE:
        raise _transition_error(content, "gửi duyệt")
    matches = brand_service.check_banned(db, _content_text(content))
    content.status = ContentStatus.PENDING_REVIEW
    _notify_managers_pending(db, user, content)
    db.commit()
    db.refresh(content)
    return SubmitOut(**content_out(content).model_dump(), banned_matches=matches)


def _ensure_reviewer(user: User, content: Content) -> None:
    if not user.is_manager:
        raise PermissionDenied("Chỉ Quản lý marketing được duyệt hoặc từ chối nội dung")
    if content.created_by == user.id:
        raise PermissionDenied("Bạn không thể tự duyệt nội dung do chính mình tạo", code="CANNOT_REVIEW_OWN")


def approve_content(db: Session, user: User, content_id: int, data: ApproveIn | None = None) -> ContentOut:
    content = get_content_orm(db, content_id)
    _ensure_reviewer(user, content)
    if content.status != ContentStatus.PENDING_REVIEW:
        raise _transition_error(content, "duyệt")
    comment = (data.comment if data else None) or ""
    content.status = ContentStatus.APPROVED
    db.add(ContentReview(content_id=content.id, reviewer_id=user.id, decision=ReviewDecision.APPROVED, comment=comment))
    notification_service.notify(
        db, [content.created_by], "CONTENT_APPROVED",
        f'Nội dung "{content.title}" đã được {user.full_name} duyệt', f"/contents/{content.id}",
    )
    db.commit()
    db.refresh(content)
    return content_out(content)


def reject_content(db: Session, user: User, content_id: int, data: RejectIn) -> ContentOut:
    content = get_content_orm(db, content_id)
    _ensure_reviewer(user, content)
    comment = (data.comment or "").strip()
    if not comment:
        raise ValidationFailed(fields={"comment": "Vui lòng nhập lý do từ chối"})
    if content.status != ContentStatus.PENDING_REVIEW:
        raise _transition_error(content, "từ chối")
    content.status = ContentStatus.REJECTED
    db.add(ContentReview(content_id=content.id, reviewer_id=user.id, decision=ReviewDecision.REJECTED, comment=comment))
    notification_service.notify(
        db, [content.created_by], "CONTENT_REJECTED",
        f'Nội dung "{content.title}" bị từ chối: {comment[:200]}', f"/contents/{content.id}",
    )
    db.commit()
    db.refresh(content)
    return content_out(content)


def mark_published(db: Session, user: User, content_id: int, data: MarkPublishedIn | None = None) -> ContentOut:
    content = get_content_orm(db, content_id)
    allowed = user.is_manager or content.created_by == user.id or is_planned_assignee(db, user, content.id)
    if not allowed:
        raise PermissionDenied("Chỉ quản lý, người tạo hoặc người phụ trách lịch đăng được đánh dấu đã đăng")
    data = data or MarkPublishedIn()
    publish(db, user, content, data.published_url, data.published_at)
    db.commit()
    db.refresh(content)
    return content_out(content)
