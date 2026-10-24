"""Router báo cáo & thống kê marketing."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.security import CurrentUser, DbSession
from app.models.enums import CampaignStatus
from app.schemas.stats import (
    CampaignStatsRow,
    ChannelStats,
    Granularity,
    StatsFilters,
    StatsOverview,
    TimeseriesPoint,
)
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["Thống kê & Báo cáo"])


@router.get("/overview", response_model=StatsOverview)
def get_overview(
    user: CurrentUser,
    db: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    campaign_id: int | None = None,
    channel_id: int | None = None,
    channel_code: str | None = None,
    status: CampaignStatus | None = None,
) -> StatsOverview:
    filters = StatsFilters(
        date_from=date_from,
        date_to=date_to,
        campaign_id=campaign_id,
        channel_id=channel_id,
        channel_code=channel_code,
        status=status,
    )
    return stats_service.get_overview(db, user, filters)


@router.get("/timeseries", response_model=list[TimeseriesPoint])
def get_timeseries(
    user: CurrentUser,
    db: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    campaign_id: int | None = None,
    channel_id: int | None = None,
    channel_code: str | None = None,
    status: CampaignStatus | None = None,
    granularity: Annotated[Granularity, Query()] = "day",
) -> list[TimeseriesPoint]:
    filters = StatsFilters(
        date_from=date_from,
        date_to=date_to,
        campaign_id=campaign_id,
        channel_id=channel_id,
        channel_code=channel_code,
        status=status,
    )
    return stats_service.get_timeseries(db, user, filters, granularity=granularity)


@router.get("/by-channel", response_model=list[ChannelStats])
def get_by_channel(
    user: CurrentUser,
    db: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    campaign_id: int | None = None,
    channel_id: int | None = None,
    channel_code: str | None = None,
    status: CampaignStatus | None = None,
) -> list[ChannelStats]:
    filters = StatsFilters(
        date_from=date_from,
        date_to=date_to,
        campaign_id=campaign_id,
        channel_id=channel_id,
        channel_code=channel_code,
        status=status,
    )
    return stats_service.get_by_channel(db, user, filters)


@router.get("/by-campaign", response_model=list[CampaignStatsRow])
def get_by_campaign(
    user: CurrentUser,
    db: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    campaign_id: int | None = None,
    channel_id: int | None = None,
    channel_code: str | None = None,
    status: CampaignStatus | None = None,
) -> list[CampaignStatsRow]:
    filters = StatsFilters(
        date_from=date_from,
        date_to=date_to,
        campaign_id=campaign_id,
        channel_id=channel_id,
        channel_code=channel_code,
        status=status,
    )
    return stats_service.get_by_campaign(db, user, filters)
