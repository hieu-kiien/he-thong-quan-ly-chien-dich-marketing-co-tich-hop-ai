"""Router nội dung marketing & quy trình duyệt."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.pagination import Page
from app.core.security import CurrentUser, DbSession
from app.models.enums import ContentOrigin, ContentStatus
from app.schemas.common import Message
from app.schemas.content import (
    ApproveIn,
    CheckBannedIn,
    CheckBannedOut,
    ContentCreate,
    ContentFilters,
    ContentOut,
    ContentReviewOut,
    ContentUpdate,
    MarkPublishedIn,
    RejectIn,
    SubmitOut,
)
from app.services import content_service

router = APIRouter(prefix="/contents", tags=["Nội dung"])


@router.get("", response_model=Page[ContentOut])
def list_contents(
    user: CurrentUser,
    db: DbSession,
    campaign_id: int | None = None,
    channel_id: int | None = None,
    channel_code: str | None = None,
    status: ContentStatus | None = None,
    origin: ContentOrigin | None = None,
    created_by: int | None = None,
    q: str | None = None,
    sort: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[ContentOut]:
    filters = ContentFilters(
        campaign_id=campaign_id,
        channel_id=channel_id,
        channel_code=channel_code,
        status=status,
        origin=origin,
        created_by=created_by,
        q=q,
    )
    return content_service.list_contents(db, user, filters, page=page, page_size=page_size, sort=sort)


@router.post("", response_model=ContentOut, status_code=status.HTTP_201_CREATED)
def create_content(data: ContentCreate, user: CurrentUser, db: DbSession) -> ContentOut:
    return content_service.create_content(db, user, data)


@router.post("/check-banned", response_model=CheckBannedOut)
def check_banned(data: CheckBannedIn, user: CurrentUser, db: DbSession) -> CheckBannedOut:
    matches = content_service.check_banned(db, data.text)
    return CheckBannedOut(matches=matches)


@router.get("/{content_id}", response_model=ContentOut)
def get_content(content_id: int, user: CurrentUser, db: DbSession) -> ContentOut:
    return content_service.get_content(db, user, content_id)


@router.patch("/{content_id}", response_model=ContentOut)
def update_content(content_id: int, data: ContentUpdate, user: CurrentUser, db: DbSession) -> ContentOut:
    return content_service.update_content(db, user, content_id, data)


@router.delete("/{content_id}", response_model=Message)
def delete_content(content_id: int, user: CurrentUser, db: DbSession) -> Message:
    content_service.delete_content(db, user, content_id)
    return Message(message="Đã xoá nội dung thành công")


@router.post("/{content_id}/submit", response_model=SubmitOut)
def submit_content(content_id: int, user: CurrentUser, db: DbSession) -> SubmitOut:
    return content_service.submit_content(db, user, content_id)


@router.post("/{content_id}/approve", response_model=ContentOut)
def approve_content(
    content_id: int, user: CurrentUser, db: DbSession, data: ApproveIn | None = None
) -> ContentOut:
    return content_service.approve_content(db, user, content_id, data)


@router.post("/{content_id}/reject", response_model=ContentOut)
def reject_content(content_id: int, data: RejectIn, user: CurrentUser, db: DbSession) -> ContentOut:
    return content_service.reject_content(db, user, content_id, data)


@router.post("/{content_id}/mark-published", response_model=ContentOut)
def mark_published(
    content_id: int, user: CurrentUser, db: DbSession, data: MarkPublishedIn | None = None
) -> ContentOut:
    return content_service.mark_published(db, user, content_id, data)


@router.get("/{content_id}/reviews", response_model=list[ContentReviewOut])
def list_reviews(content_id: int, user: CurrentUser, db: DbSession) -> list[ContentReviewOut]:
    return content_service.list_reviews(db, user, content_id)
