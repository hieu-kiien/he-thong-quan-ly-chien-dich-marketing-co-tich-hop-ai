"""Bảng lưu trữ cho Trợ lý AI (CONTRACT §3). Runtime trợ lý do agent khác triển khai trong `app/assistant/`."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UTCDateTime, utcnow
from app.models.base import enum_column
from app.models.campaign import Campaign
from app.models.enums import AiActionStatus, AiMessageRole, AiMessageStatus


class AiThread(TimestampMixin, Base):
    __tablename__ = "ai_threads"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="Phiên mới")
    opencode_session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)

    campaign: Mapped[Campaign | None] = relationship(lazy="joined")
    messages: Mapped[list[AiMessage]] = relationship(
        back_populates="thread", cascade="all, delete-orphan", passive_deletes=True, order_by="AiMessage.id"
    )


class AiMessage(TimestampMixin, Base):
    __tablename__ = "ai_messages"

    thread_id: Mapped[int] = mapped_column(
        ForeignKey("ai_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[AiMessageRole] = mapped_column(enum_column(AiMessageRole, "ai_message_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    parts_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[AiMessageStatus] = mapped_column(
        enum_column(AiMessageStatus, "ai_message_status"), nullable=False, default=AiMessageStatus.COMPLETE
    )
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    thread: Mapped[AiThread] = relationship(back_populates="messages")


class AiAction(TimestampMixin, Base):
    __tablename__ = "ai_actions"

    thread_id: Mapped[int] = mapped_column(
        ForeignKey("ai_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[int] = mapped_column(
        ForeignKey("ai_messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tool: Mapped[str] = mapped_column(String(64), nullable=False)
    args_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[AiActionStatus] = mapped_column(
        enum_column(AiActionStatus, "ai_action_status"), nullable=False, default=AiActionStatus.PROPOSED
    )
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
