from __future__ import annotations

from datetime import datetime

from app.core.pagination import Page
from app.schemas.common import ORMModel


class NotificationOut(ORMModel):
    id: int
    type: str
    message: str
    link: str | None
    is_read: bool
    created_at: datetime


class NotificationPage(Page[NotificationOut]):
    unread_count: int


class ReadAllOut(ORMModel):
    updated: int
