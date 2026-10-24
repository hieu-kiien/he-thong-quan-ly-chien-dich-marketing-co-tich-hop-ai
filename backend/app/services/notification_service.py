"""Thông báo trong ứng dụng (không gửi email/Zalo — chỉ hiển thị trong MarketFlow)."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.core.pagination import normalize_page, paginate
from app.models import Notification, User
from app.schemas.notification import NotificationOut, NotificationPage, ReadAllOut


def notify(db: Session, user_ids: Iterable[int], type_: str, message: str, link: str | None = None) -> None:
    """Thêm thông báo vào session (không commit — đi cùng giao dịch của thao tác gốc)."""
    for uid in set(user_ids):
        db.add(Notification(user_id=uid, type=type_, message=message, link=link, is_read=False))


def list_notifications(
    db: Session, user: User, unread_only: bool = False, page: int = 1, page_size: int = 20
) -> NotificationPage:
    page, page_size = normalize_page(page, page_size)
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc())
    items, total = paginate(db, stmt, page, page_size)
    unread = db.execute(
        select(func.count(Notification.id)).where(Notification.user_id == user.id, Notification.is_read.is_(False))
    ).scalar_one()
    return NotificationPage(
        items=[NotificationOut.model_validate(n) for n in items],
        total=total,
        page=page,
        page_size=page_size,
        unread_count=int(unread),
    )


def mark_read(db: Session, user: User, notification_id: int) -> NotificationOut:
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise NotFound("Không tìm thấy thông báo")
    if not n.is_read:
        n.is_read = True
        db.commit()
        db.refresh(n)
    return NotificationOut.model_validate(n)


def mark_all_read(db: Session, user: User) -> ReadAllOut:
    result = db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.commit()
    return ReadAllOut(updated=result.rowcount or 0)
