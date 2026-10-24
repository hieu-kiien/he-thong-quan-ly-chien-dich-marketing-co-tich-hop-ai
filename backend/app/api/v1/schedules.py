"""Router lịch đăng nội dung."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, status

from app.core.security import CurrentUser, DbSession
from app.models.enums import ScheduleStatus
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleDoneIn,
    ScheduleFilters,
    ScheduleOut,
    ScheduleUpdate,
)
from app.services import schedule_service

router = APIRouter(prefix="/schedules", tags=["Lịch đăng"])


@router.get("", response_model=list[ScheduleOut])
def list_schedules(
    user: CurrentUser,
    db: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    channel_id: int | None = None,
    campaign_id: int | None = None,
    assignee_id: int | None = None,
    status: ScheduleStatus | None = None,
) -> list[ScheduleOut]:
    filters = ScheduleFilters(
        date_from=date_from,
        date_to=date_to,
        channel_id=channel_id,
        campaign_id=campaign_id,
        assignee_id=assignee_id,
        status=status,
    )
    return schedule_service.list_schedules(db, user, filters)


@router.post("", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule(data: ScheduleCreate, user: CurrentUser, db: DbSession) -> ScheduleOut:
    return schedule_service.create_schedule(db, user, data)


@router.get("/{schedule_id}", response_model=ScheduleOut)
def get_schedule(schedule_id: int, user: CurrentUser, db: DbSession) -> ScheduleOut:
    return schedule_service.get_schedule(db, user, schedule_id)


@router.patch("/{schedule_id}", response_model=ScheduleOut)
def update_schedule(schedule_id: int, data: ScheduleUpdate, user: CurrentUser, db: DbSession) -> ScheduleOut:
    return schedule_service.update_schedule(db, user, schedule_id, data)


@router.post("/{schedule_id}/done", response_model=ScheduleOut)
def complete_schedule(
    schedule_id: int, user: CurrentUser, db: DbSession, data: ScheduleDoneIn | None = None
) -> ScheduleOut:
    return schedule_service.complete_schedule(db, user, schedule_id, data)


@router.post("/{schedule_id}/cancel", response_model=ScheduleOut)
def cancel_schedule(schedule_id: int, user: CurrentUser, db: DbSession) -> ScheduleOut:
    return schedule_service.cancel_schedule(db, user, schedule_id)
