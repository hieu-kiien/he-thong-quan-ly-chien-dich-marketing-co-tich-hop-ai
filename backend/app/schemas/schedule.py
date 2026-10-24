from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, Field

from app.models.enums import ContentStatus, ContentType, ScheduleStatus
from app.schemas.common import CampaignRef, ChannelRef, InputModel, ORMModel, UserRef
from app.schemas.content import _check_url


class ScheduleCreate(InputModel):
    content_id: int
    scheduled_at: datetime
    assignee_id: int | None = None
    note: str | None = Field(default=None, max_length=1000)


class ScheduleUpdate(InputModel):
    scheduled_at: datetime | None = None
    assignee_id: int | None = None
    note: str | None = Field(default=None, max_length=1000)


class ScheduleDoneIn(InputModel):
    published_url: Annotated[str | None, AfterValidator(_check_url)] = Field(default=None, max_length=500)


class ScheduleFilters(InputModel):
    date_from: date | None = None
    date_to: date | None = None
    channel_id: int | None = None
    campaign_id: int | None = None
    assignee_id: int | None = None
    status: ScheduleStatus | None = None


class ScheduleContentRef(ORMModel):
    id: int
    title: str
    status: ContentStatus
    content_type: ContentType
    created_by: UserRef


class ScheduleOut(ORMModel):
    id: int
    content_id: int
    scheduled_at: datetime
    assignee: UserRef | None
    status: ScheduleStatus
    note: str | None
    done_at: datetime | None
    content: ScheduleContentRef
    campaign: CampaignRef
    channel: ChannelRef
    created_at: datetime
    updated_at: datetime
