"""Router thông báo nội bộ."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.security import CurrentUser, DbSession
from app.schemas.notification import NotificationOut, NotificationPage, ReadAllOut
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Thông báo"])


@router.get("", response_model=NotificationPage)
def list_notifications(
    user: CurrentUser,
    db: DbSession,
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> NotificationPage:
    return notification_service.list_notifications(db, user, unread_only=unread_only, page=page, page_size=page_size)


@router.post("/read-all", response_model=ReadAllOut)
def mark_all_read(user: CurrentUser, db: DbSession) -> ReadAllOut:
    return notification_service.mark_all_read(db, user)


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user: CurrentUser, db: DbSession) -> NotificationOut:
    return notification_service.mark_read(db, user, notification_id)
