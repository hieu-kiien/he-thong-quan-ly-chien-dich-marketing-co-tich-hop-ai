from __future__ import annotations

from datetime import date
from typing import Literal

from app.models.enums import CampaignStatus
from app.schemas.common import CampaignRef, ChannelRef, InputModel, MoneyOut, ORMModel

Granularity = Literal["day", "week", "month"]


class StatsFilters(InputModel):
    date_from: date | None = None
    date_to: date | None = None
    campaign_id: int | None = None
    channel_id: int | None = None
    channel_code: str | None = None
    status: CampaignStatus | None = None


class Totals(ORMModel):
    views: int
    clicks: int
    conversions: int
    cost: MoneyOut


class Rates(ORMModel):
    ctr: float | None
    cvr: float | None
    cpc: float | None
    cpa: float | None
    cpm: float | None


class BudgetSummary(ORMModel):
    total_budget: MoneyOut | None
    spent: MoneyOut
    used_pct: float | None


class StatusCounts(ORMModel):
    by_status: dict[str, int]


class StatsOverview(ORMModel):
    totals: Totals
    rates: Rates
    budget: BudgetSummary
    campaigns: StatusCounts
    contents: StatusCounts
    pending_reviews: int
    schedules_today: int
    has_seed_data: bool


class TimeseriesPoint(ORMModel):
    period: str
    views: int
    clicks: int
    conversions: int
    cost: MoneyOut


class ChannelStats(ORMModel):
    channel: ChannelRef
    views: int
    clicks: int
    conversions: int
    cost: MoneyOut
    ctr: float | None
    cvr: float | None
    cpc: float | None
    cpa: float | None


class CampaignStatsRef(CampaignRef):
    status: CampaignStatus


class CampaignStatsRow(ORMModel):
    campaign: CampaignStatsRef
    budget: MoneyOut
    cost: MoneyOut
    used_pct: float | None
    views: int
    clicks: int
    conversions: int
    ctr: float | None
    cpa: float | None
