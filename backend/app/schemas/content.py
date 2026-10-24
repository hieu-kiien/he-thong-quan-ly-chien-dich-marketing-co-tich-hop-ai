from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, Field

from app.models.enums import ContentOrigin, ContentStatus, ContentType, ReviewDecision
from app.schemas.common import CampaignRef, ChannelRef, InputModel, ORMModel, UserRef


def _check_url(v: str | None) -> str | None:
    if v is None or v == "":
        return None
    if not v.startswith(("http://", "https://")) or " " in v:
        raise ValueError("Đường dẫn phải bắt đầu bằng http:// hoặc https://")
    return v


class ContentCreate(InputModel):
    campaign_id: int
    channel_id: int | None = None
    channel_code: str | None = Field(default=None, max_length=30)
    content_type: ContentType
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=20000)
    cta: str | None = Field(default=None, max_length=255)


class ContentUpdate(InputModel):
    campaign_id: int | None = None
    channel_id: int | None = None
    content_type: ContentType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1, max_length=20000)
    cta: str | None = Field(default=None, max_length=255)


class ContentFilters(InputModel):
    campaign_id: int | None = None
    channel_id: int | None = None
    channel_code: str | None = None
    status: ContentStatus | None = None
    origin: ContentOrigin | None = None
    created_by: int | None = None
    q: str | None = None


class ContentOut(ORMModel):
    id: int
    campaign_id: int
    campaign: CampaignRef
    channel_id: int
    channel: ChannelRef
    content_type: ContentType
    title: str
    body: str
    cta: str | None
    status: ContentStatus
    origin: ContentOrigin
    ai_message_id: int | None
    created_by: UserRef
    published_url: str | None
    published_at: datetime | None
    published_by: UserRef | None
    created_at: datetime
    updated_at: datetime


class BannedMatch(ORMModel):
    keyword: str
    count: int


class SubmitOut(ContentOut):
    banned_matches: list[BannedMatch]


class ApproveIn(InputModel):
    comment: str | None = Field(default=None, max_length=2000)


class RejectIn(InputModel):
    comment: str = Field(min_length=1, max_length=2000)


class MarkPublishedIn(InputModel):
    published_url: Annotated[str | None, AfterValidator(_check_url)] = Field(default=None, max_length=500)
    published_at: datetime | None = None


class ContentReviewOut(ORMModel):
    id: int
    content_id: int
    reviewer: UserRef
    decision: ReviewDecision
    comment: str
    created_at: datetime


class CheckBannedIn(InputModel):
    text: str = Field(max_length=50000)


class CheckBannedOut(ORMModel):
    matches: list[BannedMatch]
