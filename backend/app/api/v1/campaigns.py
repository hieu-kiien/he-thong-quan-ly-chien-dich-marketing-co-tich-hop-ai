"""Router chiến dịch marketing."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query, status

from app.core.pagination import Page
from app.core.security import CurrentUser, DbSession
from app.models.enums import CampaignGoal, CampaignStatus
from app.schemas.campaign import (
    CampaignCreate,
    CampaignDetail,
    CampaignFilters,
    CampaignListItem,
    CampaignUpdate,
)
from app.schemas.common import Message
from app.services import campaign_service

router = APIRouter(prefix="/campaigns", tags=["Chiến dịch"])


@router.get("", response_model=Page[CampaignListItem])
def list_campaigns(
    user: CurrentUser,
    db: DbSession,
    q: str | None = None,
    status: CampaignStatus | None = None,
    goal: CampaignGoal | None = None,
    channel_id: int | None = None,
    channel_code: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    owner_id: int | None = None,
    sort: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[CampaignListItem]:
    filters = CampaignFilters(
        q=q,
        status=status,
        goal=goal,
        channel_id=channel_id,
        channel_code=channel_code,
        date_from=date_from,
        date_to=date_to,
        owner_id=owner_id,
    )
    return campaign_service.list_campaigns(db, user, filters, page=page, page_size=page_size, sort=sort)


@router.post("", response_model=CampaignDetail, status_code=status.HTTP_201_CREATED)
def create_campaign(data: CampaignCreate, user: CurrentUser, db: DbSession) -> CampaignDetail:
    return campaign_service.create_campaign(db, user, data)


@router.get("/{campaign_id}", response_model=CampaignDetail)
def get_campaign(campaign_id: int, user: CurrentUser, db: DbSession) -> CampaignDetail:
    return campaign_service.get_campaign(db, user, campaign_id)


@router.patch("/{campaign_id}", response_model=CampaignDetail)
def update_campaign(campaign_id: int, data: CampaignUpdate, user: CurrentUser, db: DbSession) -> CampaignDetail:
    return campaign_service.update_campaign(db, user, campaign_id, data)


@router.delete("/{campaign_id}", response_model=Message)
def delete_campaign(campaign_id: int, user: CurrentUser, db: DbSession) -> Message:
    campaign_service.delete_campaign(db, user, campaign_id)
    return Message(message="Đã xoá chiến dịch thành công")
