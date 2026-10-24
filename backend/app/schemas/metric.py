from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from app.models.enums import MetricSource
from app.schemas.common import (
    CampaignRef,
    ChannelRef,
    Count,
    InputModel,
    MoneyIn,
    MoneyOut,
    ORMModel,
    UserRef,
)


class MetricIn(InputModel):
    """Một dòng số liệu. Truyền `channel_id` hoặc `channel_code`."""

    campaign_id: int
    channel_id: int | None = None
    channel_code: str | None = Field(default=None, max_length=30)
    metric_date: date
    views: Count = 0
    clicks: Count = 0
    conversions: Count = 0
    cost: MoneyIn = 0


class MetricUpdate(InputModel):
    views: Count | None = None
    clicks: Count | None = None
    conversions: Count | None = None
    cost: MoneyIn | None = None


class MetricFilters(InputModel):
    campaign_id: int | None = None
    channel_id: int | None = None
    channel_code: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    source: MetricSource | None = None


class MetricOut(ORMModel):
    id: int
    campaign_id: int
    campaign: CampaignRef
    channel_id: int
    channel: ChannelRef
    metric_date: date
    views: int
    clicks: int
    conversions: int
    cost: MoneyOut
    source: MetricSource
    entered_by: UserRef | None
    import_batch: str | None
    created_at: datetime
    updated_at: datetime


class ImportRow(ORMModel):
    row: int
    metric_date: date
    campaign_id: int
    campaign_name: str
    channel_id: int
    channel_code: str
    views: int
    clicks: int
    conversions: int
    cost: int
    exists: bool


class ImportRowError(ORMModel):
    row: int
    message: str


class ImportSummary(ORMModel):
    total: int
    valid: int
    invalid: int
    inserts: int
    updates: int


class ImportPreviewOut(ORMModel):
    rows: list[ImportRow]
    errors: list[ImportRowError]
    summary: ImportSummary


class ImportCommitRow(InputModel):
    row: int | None = None
    metric_date: date
    campaign_id: int
    channel_id: int | None = None
    channel_code: str | None = Field(default=None, max_length=30)
    views: Count = 0
    clicks: Count = 0
    conversions: Count = 0
    cost: MoneyIn = 0


class ImportCommitIn(InputModel):
    rows: list[ImportCommitRow] = Field(min_length=1, max_length=5000)


class ImportCommitOut(ORMModel):
    inserted: int
    updated: int
    import_batch: str | None
