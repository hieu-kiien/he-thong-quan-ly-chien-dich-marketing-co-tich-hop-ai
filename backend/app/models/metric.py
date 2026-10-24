from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.base import MONEY, enum_column
from app.models.campaign import Campaign
from app.models.channel import Channel
from app.models.enums import MetricSource
from app.models.user import User


class Metric(TimestampMixin, Base):
    __tablename__ = "metrics"
    __table_args__ = (
        UniqueConstraint("campaign_id", "channel_id", "metric_date", name="uq_metrics_campaign_channel_date"),
        CheckConstraint("views >= 0 AND clicks >= 0 AND conversions >= 0", name="counts_non_negative"),
        CheckConstraint("cost >= 0", name="cost_non_negative"),
        CheckConstraint("views = 0 OR clicks <= views", name="clicks_le_views"),
        CheckConstraint("clicks = 0 OR conversions <= clicks", name="conversions_le_clicks"),
    )

    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False, index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), nullable=False, index=True)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[Decimal] = mapped_column(MONEY, nullable=False, default=0)
    source: Mapped[MetricSource] = mapped_column(enum_column(MetricSource, "metric_source"), nullable=False)
    entered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    import_batch: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    campaign: Mapped[Campaign] = relationship(lazy="joined")
    channel: Mapped[Channel] = relationship(lazy="joined")
    enterer: Mapped[User | None] = relationship(lazy="joined")
