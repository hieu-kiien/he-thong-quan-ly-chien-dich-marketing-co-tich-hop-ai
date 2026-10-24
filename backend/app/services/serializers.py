"""Chuyển ORM → schema response theo CONTRACT §10 (Ref object nhúng)."""

from __future__ import annotations

from app.models import Content, ContentReview, Metric, Schedule, User
from app.schemas.common import UserRef
from app.schemas.content import ContentOut, ContentReviewOut
from app.schemas.metric import MetricOut
from app.schemas.schedule import ScheduleOut


def user_ref(user: User | None) -> UserRef | None:
    return UserRef(id=user.id, full_name=user.full_name) if user is not None else None


def content_out(c: Content) -> ContentOut:
    return ContentOut(
        id=c.id,
        campaign_id=c.campaign_id,
        campaign={"id": c.campaign.id, "name": c.campaign.name},
        channel_id=c.channel_id,
        channel={"id": c.channel.id, "code": c.channel.code, "name": c.channel.name},
        content_type=c.content_type,
        title=c.title,
        body=c.body,
        cta=c.cta,
        status=c.status,
        origin=c.origin,
        ai_message_id=c.ai_message_id,
        created_by=user_ref(c.creator),
        published_url=c.published_url,
        published_at=c.published_at,
        published_by=user_ref(c.publisher),
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def review_out(r: ContentReview) -> ContentReviewOut:
    return ContentReviewOut(
        id=r.id,
        content_id=r.content_id,
        reviewer=user_ref(r.reviewer),
        decision=r.decision,
        comment=r.comment or "",
        created_at=r.created_at,
    )


def metric_out(m: Metric) -> MetricOut:
    return MetricOut(
        id=m.id,
        campaign_id=m.campaign_id,
        campaign={"id": m.campaign.id, "name": m.campaign.name},
        channel_id=m.channel_id,
        channel={"id": m.channel.id, "code": m.channel.code, "name": m.channel.name},
        metric_date=m.metric_date,
        views=m.views,
        clicks=m.clicks,
        conversions=m.conversions,
        cost=m.cost,
        source=m.source,
        entered_by=user_ref(m.enterer),
        import_batch=m.import_batch,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def schedule_out(s: Schedule) -> ScheduleOut:
    c = s.content
    return ScheduleOut(
        id=s.id,
        content_id=s.content_id,
        scheduled_at=s.scheduled_at,
        assignee=user_ref(s.assignee),
        status=s.status,
        note=s.note,
        done_at=s.done_at,
        content={
            "id": c.id,
            "title": c.title,
            "status": c.status,
            "content_type": c.content_type,
            "created_by": user_ref(c.creator),
        },
        campaign={"id": c.campaign.id, "name": c.campaign.name},
        channel={"id": c.channel.id, "code": c.channel.code, "name": c.channel.name},
        created_at=s.created_at,
        updated_at=s.updated_at,
    )
