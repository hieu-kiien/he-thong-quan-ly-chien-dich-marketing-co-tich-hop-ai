from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UTCDateTime
from app.models.base import enum_column
from app.models.content import Content
from app.models.enums import ScheduleStatus
from app.models.user import User


class Schedule(TimestampMixin, Base):
    __tablename__ = "schedules"

    content_id: Mapped[int] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[ScheduleStatus] = mapped_column(
        enum_column(ScheduleStatus, "schedule_status"), nullable=False, default=ScheduleStatus.PLANNED
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    content: Mapped[Content] = relationship(lazy="joined")
    assignee: Mapped[User | None] = relationship(lazy="joined")
