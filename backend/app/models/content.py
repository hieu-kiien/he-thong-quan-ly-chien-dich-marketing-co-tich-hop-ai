from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UTCDateTime
from app.models.base import enum_column
from app.models.campaign import Campaign
from app.models.channel import Channel
from app.models.enums import ContentOrigin, ContentStatus, ContentType, ReviewDecision
from app.models.user import User


class Content(TimestampMixin, Base):
    __tablename__ = "contents"

    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False, index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), nullable=False, index=True)
    content_type: Mapped[ContentType] = mapped_column(enum_column(ContentType, "content_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    cta: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ContentStatus] = mapped_column(
        enum_column(ContentStatus, "content_status"), nullable=False, default=ContentStatus.DRAFT, index=True
    )
    origin: Mapped[ContentOrigin] = mapped_column(
        enum_column(ContentOrigin, "content_origin"), nullable=False, default=ContentOrigin.MANUAL
    )
    ai_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_messages.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    published_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    published_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    campaign: Mapped[Campaign] = relationship(lazy="joined")
    channel: Mapped[Channel] = relationship(lazy="joined")
    creator: Mapped[User] = relationship(foreign_keys=[created_by], lazy="joined")
    publisher: Mapped[User | None] = relationship(foreign_keys=[published_by], lazy="joined")


class ContentReview(TimestampMixin, Base):
    __tablename__ = "content_reviews"

    content_id: Mapped[int] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    decision: Mapped[ReviewDecision] = mapped_column(
        enum_column(ReviewDecision, "review_decision"), nullable=False
    )
    comment: Mapped[str] = mapped_column(Text, default="", nullable=False)

    reviewer: Mapped[User] = relationship(lazy="joined")
