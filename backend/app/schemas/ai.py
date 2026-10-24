"""Hình dạng response của Trợ lý AI (CONTRACT §10.11) — dùng chung cho `app/assistant/`."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import AiActionStatus, AiMessageRole, AiMessageStatus
from app.schemas.common import CampaignRef, ORMModel


class AiThreadCreate(BaseModel):
    title: str | None = None
    campaign_id: int | None = None


class AiThreadUpdate(BaseModel):
    title: str | None = None
    campaign_id: int | None = None
    pinned: bool | None = None


class MessageSendIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)


class ActionConfirmIn(BaseModel):
    args: dict[str, Any] | None = None


class AssistantStatusOut(BaseModel):
    available: bool
    runner: dict[str, Any]
    last_error: str | None = None
    queue_length: int = 0


class AiThreadOut(ORMModel):
    id: int
    user_id: int
    campaign_id: int | None
    campaign: CampaignRef | None
    title: str
    pinned: bool
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime


class AiMessageOut(ORMModel):
    id: int
    thread_id: int
    role: AiMessageRole
    content: str
    parts_json: list[dict[str, Any]]
    status: AiMessageStatus
    error_code: str | None
    model: str | None
    latency_ms: int | None
    created_at: datetime


class AiActionOut(ORMModel):
    id: int
    thread_id: int
    message_id: int
    user_id: int
    tool: str
    args_json: dict[str, Any]
    summary: str
    status: AiActionStatus
    result_json: dict[str, Any] | None
    error: str | None
    executed_at: datetime | None
    created_at: datetime
