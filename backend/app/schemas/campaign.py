from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.models.enums import CampaignGoal, CampaignStatus
from app.schemas.common import InputModel, MoneyIn, MoneyOut, ORMModel, UserRef


class CampaignChannelIn(InputModel):
    """Một kênh của chiến dịch. Truyền `channel_id` hoặc `channel_code` (tiện cho công cụ AI)."""

    channel_id: int | None = None
    channel_code: str | None = Field(default=None, max_length=30)
    planned_budget: MoneyIn | None = None


class CampaignCreate(InputModel):
    name: str = Field(min_length=1, max_length=200)
    goal: CampaignGoal
    objective: str = Field(min_length=1, max_length=5000)
    target_audience: str = Field(min_length=1, max_length=5000)
    product: str = Field(min_length=1, max_length=2000)
    key_message: str | None = Field(default=None, max_length=2000)
    start_date: date
    end_date: date
    budget: MoneyIn
    status: Literal["PLANNED", "ACTIVE"] = "PLANNED"
    channels: list[CampaignChannelIn] = Field(min_length=1, max_length=20)


class CampaignUpdate(InputModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    goal: CampaignGoal | None = None
    objective: str | None = Field(default=None, min_length=1, max_length=5000)
    target_audience: str | None = Field(default=None, min_length=1, max_length=5000)
    product: str | None = Field(default=None, min_length=1, max_length=2000)
    key_message: str | None = Field(default=None, max_length=2000)
    start_date: date | None = None
    end_date: date | None = None
    budget: MoneyIn | None = None
    status: CampaignStatus | None = None
    owner_id: int | None = None
    channels: list[CampaignChannelIn] | None = Field(default=None, min_length=1, max_length=20)


class CampaignFilters(InputModel):
    q: str | None = None
    status: CampaignStatus | None = None
    goal: CampaignGoal | None = None
    channel_id: int | None = None
    channel_code: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    owner_id: int | None = None


class CampaignChannelOut(ORMModel):
    id: int
    code: str
    name: str
    planned_budget: MoneyOut | None = None


class CampaignStats(ORMModel):
    views: int
    clicks: int
    conversions: int
    cost: MoneyOut
    ctr: float | None
    cvr: float | None
    cpc: float | None
    cpa: float | None
    cpm: float | None
    budget_used_pct: float | None


class CampaignListItem(ORMModel):
    id: int
    name: str
    goal: CampaignGoal
    status: CampaignStatus
    start_date: date
    end_date: date
    budget: MoneyOut
    owner: UserRef
    channels: list[CampaignChannelOut]
    spent: MoneyOut
    content_counts: dict[str, int]
    created_at: datetime
    updated_at: datetime


class CampaignDetail(CampaignListItem):
    owner_id: int
    objective: str
    target_audience: str
    product: str
    key_message: str | None
    stats: CampaignStats
