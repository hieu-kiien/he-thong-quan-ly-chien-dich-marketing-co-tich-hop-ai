from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UTCDateTime, utcnow
from app.models.base import MONEY, enum_column
from app.models.channel import Channel
from app.models.enums import CampaignGoal, CampaignStatus
from app.models.user import User


class Campaign(TimestampMixin, Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="date_range"),
        CheckConstraint("budget >= 0", name="budget_non_negative"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[CampaignGoal] = mapped_column(enum_column(CampaignGoal, "campaign_goal"), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[str] = mapped_column(Text, nullable=False)
    product: Mapped[str] = mapped_column(Text, nullable=False)
    key_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    budget: Mapped[Decimal] = mapped_column(MONEY, nullable=False, default=0)
    status: Mapped[CampaignStatus] = mapped_column(
        enum_column(CampaignStatus, "campaign_status"), nullable=False, default=CampaignStatus.PLANNED
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    owner: Mapped[User] = relationship(lazy="joined")
    channel_links: Mapped[list[CampaignChannel]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CampaignChannel.channel_id",
    )


class CampaignChannel(Base):
    __tablename__ = "campaign_channels"
    __table_args__ = (
        CheckConstraint("planned_budget IS NULL OR planned_budget >= 0", name="planned_budget_non_negative"),
    )

    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), primary_key=True, index=True)
    planned_budget: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow, nullable=False
    )

    campaign: Mapped[Campaign] = relationship(back_populates="channel_links")
    channel: Mapped[Channel] = relationship(lazy="joined")
