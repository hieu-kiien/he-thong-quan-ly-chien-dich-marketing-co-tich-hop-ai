"""Định nghĩa công cụ Trợ lý AI (ToolRegistry) cho MCP và thực thi nghiệp vụ (CONTRACT §5)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.assistant.context import ToolContext
from app.core.errors import ValidationFailed
from app.core.timeutil import now_utc, to_utc
from app.models.ai import AiAction
from app.models.enums import (
    AiActionStatus,
    CampaignGoal,
    CampaignStatus,
    ContentType,
)
from app.schemas.campaign import (
    CampaignFilters,
)
from app.schemas.content import ContentFilters
from app.schemas.schedule import ScheduleFilters
from app.schemas.stats import StatsFilters
from app.services import (
    brand_service,
    campaign_service,
    channel_service,
    content_service,
    metric_service,
    schedule_service,
    stats_service,
)

# --- Input Models cho Công cụ ------------------------------------------------

class ListCampaignsArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    q: str | None = Field(default=None, description="Từ khoá tìm theo tên chiến dịch")
    status: CampaignStatus | None = Field(default=None, description="Trạng thái chiến dịch: PLANNED, ACTIVE, PAUSED, COMPLETED, CANCELLED")
    channel_code: str | None = Field(default=None, description="Lọc theo mã kênh (ví dụ: FACEBOOK, TIKTOK, EMAIL...)")
    date_from: date | None = Field(default=None, description="Ngày bắt đầu khoảng lọc (YYYY-MM-DD)")
    date_to: date | None = Field(default=None, description="Ngày kết thúc khoảng lọc (YYYY-MM-DD)")
    limit: int = Field(default=20, ge=1, le=50, description="Số lượng tối đa cần lấy (mặc định 20, tối đa 50)")


class GetCampaignArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    campaign_id: int = Field(..., description="ID của chiến dịch cần lấy thông tin chi tiết")


class GetStatsArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    campaign_id: int | None = Field(default=None, description="ID chiến dịch cần lọc số liệu")
    channel_code: str | None = Field(default=None, description="Mã kênh cần lọc số liệu")
    date_from: date | None = Field(default=None, description="Từ ngày (YYYY-MM-DD)")
    date_to: date | None = Field(default=None, description="Đến ngày (YYYY-MM-DD)")
    group_by: str = Field(
        default="none",
        description="Hình thức nhóm số liệu: 'none' (tổng quan), 'channel' (theo kênh), 'campaign' (theo chiến dịch), 'day' (theo ngày), 'week' (theo tuần), 'month' (theo tháng)",
    )


class ListContentsArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    campaign_id: int | None = Field(default=None, description="ID chiến dịch cần lọc nội dung")
    channel_code: str | None = Field(default=None, description="Mã kênh (FACEBOOK, INSTAGRAM...)")
    status: str | None = Field(default=None, description="Trạng thái nội dung (DRAFT, PENDING_REVIEW, APPROVED, REJECTED, PUBLISHED)")
    q: str | None = Field(default=None, description="Từ khoá tìm trong tiêu đề hoặc nội dung")
    limit: int = Field(default=20, ge=1, le=50, description="Số lượng tối đa cần lấy (mặc định 20, tối đa 50)")


class GetContentArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    content_id: int = Field(..., description="ID của nội dung cần xem chi tiết")


class ListSchedulesArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    date_from: date | None = Field(default=None, description="Từ ngày (YYYY-MM-DD)")
    date_to: date | None = Field(default=None, description="Đến ngày (YYYY-MM-DD)")
    campaign_id: int | None = Field(default=None, description="ID chiến dịch")


class EmptyArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")


class CheckBannedKeywordsArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    text: str = Field(..., description="Đoạn văn bản cần kiểm tra từ cấm hoặc nhạy cảm")


# --- Input Models cho Write Tools (Propose) -----------------------------------

class ProposeContentDraftItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    campaign_id: int = Field(..., description="ID chiến dịch")
    channel_code: str = Field(..., description="Mã kênh (FACEBOOK, INSTAGRAM, TIKTOK, ZALO_OA, EMAIL, GOOGLE_ADS, WEBSITE)")
    content_type: ContentType = Field(default=ContentType.SOCIAL_POST, description="Loại nội dung: SOCIAL_POST, EMAIL, AD_COPY, VIDEO_SCRIPT, OTHER")
    title: str = Field(..., description="Tiêu đề bài đăng hoặc chủ đề email")
    body: str = Field(..., description="Nội dung chi tiết của bài viết/kịch bản")
    cta: str | None = Field(default=None, description="Lời kêu gọi hành động (Call to action)")
    status: str = Field(default="PENDING_REVIEW", description="Trạng thái: PENDING_REVIEW (mặc định) hoặc DRAFT")


class ProposeContentDraftsArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    items: list[ProposeContentDraftItem] = Field(..., min_length=1, max_length=20, description="Danh sách các bản nháp nội dung đề xuất")


class ProposeCampaignChannelItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    channel_code: str = Field(..., description="Mã kênh")
    planned_budget: int | None = Field(default=None, ge=0, description="Ngân sách dự kiến phân bổ cho kênh (VND)")


class ProposeCampaignArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(..., description="Tên chiến dịch")
    goal: CampaignGoal = Field(..., description="Mục tiêu: AWARENESS, TRAFFIC, LEADS, SALES")
    objective: str = Field(..., description="Mục tiêu cụ thể bằng văn bản")
    target_audience: str = Field(..., description="Chân dung đối tượng khách hàng mục tiêu")
    product: str = Field(..., description="Sản phẩm hoặc dịch vụ trọng tâm")
    start_date: date = Field(..., description="Ngày bắt đầu (YYYY-MM-DD)")
    end_date: date = Field(..., description="Ngày kết thúc (YYYY-MM-DD)")
    budget: int = Field(..., ge=0, description="Tổng ngân sách chiến dịch (VND)")
    channels: list[ProposeCampaignChannelItem] = Field(..., min_length=1, description="Danh sách các kênh triển khai")
    key_message: str | None = Field(default=None, description="Thông điệp cốt lõi")


class ProposeCampaignUpdateArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    campaign_id: int = Field(..., description="ID chiến dịch cần chỉnh sửa")
    name: str | None = Field(default=None, description="Tên chiến dịch mới")
    goal: CampaignGoal | None = Field(default=None, description="Mục tiêu mới")
    objective: str | None = Field(default=None, description="Mục tiêu cụ thể mới")
    target_audience: str | None = Field(default=None, description="Chân dung đối tượng mục tiêu mới")
    product: str | None = Field(default=None, description="Sản phẩm/dịch vụ mới")
    start_date: date | None = Field(default=None, description="Ngày bắt đầu mới")
    end_date: date | None = Field(default=None, description="Ngày kết thúc mới")
    budget: int | None = Field(default=None, ge=0, description="Tổng ngân sách mới")
    status: CampaignStatus | None = Field(default=None, description="Trạng thái chiến dịch mới")
    key_message: str | None = Field(default=None, description="Thông điệp cốt lõi mới")
    channels: list[ProposeCampaignChannelItem] | None = Field(default=None, description="Danh sách kênh thay thế (nếu có)")


class ProposeScheduleArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    content_id: int = Field(..., description="ID nội dung cần lập lịch")
    scheduled_at: datetime = Field(..., description="Thời điểm đăng dự kiến (ISO 8601 có timezone)")
    note: str | None = Field(default=None, description="Ghi chú lập lịch")


class ProposeMetricRowItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    campaign_id: int = Field(..., description="ID chiến dịch")
    channel_code: str = Field(..., description="Mã kênh")
    metric_date: date = Field(..., description="Ngày ghi nhận số liệu (YYYY-MM-DD)")
    views: int = Field(default=0, ge=0, description="Lượt xem / tiếp cận")
    clicks: int = Field(default=0, ge=0, description="Lượt nhấp")
    conversions: int = Field(default=0, ge=0, description="Lượt chuyển đổi")
    cost: int = Field(default=0, ge=0, description="Chi phí đã tiêu (VND)")


class ProposeMetricsArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rows: list[ProposeMetricRowItem] = Field(..., min_length=1, max_length=100, description="Danh sách các dòng số liệu cần nhập/cập nhật")


# --- Handler Implementations --------------------------------------------------

def handle_list_campaigns(ctx: ToolContext, args: ListCampaignsArgs) -> dict[str, Any]:
    filters = CampaignFilters(
        q=args.q,
        status=args.status,
        channel_code=args.channel_code,
        date_from=args.date_from,
        date_to=args.date_to,
    )
    page = campaign_service.list_campaigns(ctx.db, ctx.user, filters=filters, page=1, page_size=args.limit)
    items = []
    for c in page.items:
        items.append({
            "id": c.id,
            "name": c.name,
            "goal": c.goal.value,
            "status": c.status.value,
            "status_label": campaign_service.STATUS_LABELS.get(c.status, c.status.value),
            "start_date": str(c.start_date),
            "end_date": str(c.end_date),
            "budget": int(c.budget),
            "spent": int(c.spent),
            "owner": c.owner.full_name,
            "channels": [ch.code for ch in c.channels],
        })
    return {"total": page.total, "limit": args.limit, "campaigns": items}


def handle_get_campaign(ctx: ToolContext, args: GetCampaignArgs) -> dict[str, Any]:
    camp = campaign_service.get_campaign(ctx.db, ctx.user, args.campaign_id)
    return {
        "id": camp.id,
        "name": camp.name,
        "goal": camp.goal.value,
        "status": camp.status.value,
        "status_label": campaign_service.STATUS_LABELS.get(camp.status, camp.status.value),
        "objective": camp.objective,
        "target_audience": camp.target_audience,
        "product": camp.product,
        "key_message": camp.key_message,
        "start_date": str(camp.start_date),
        "end_date": str(camp.end_date),
        "budget": int(camp.budget),
        "owner": camp.owner.full_name,
        "channels": [
            {
                "id": ch.id,
                "code": ch.code,
                "name": ch.name,
                "planned_budget": int(ch.planned_budget) if ch.planned_budget is not None else None,
            }
            for ch in camp.channels
        ],
        "stats": {
            "views": camp.stats.views,
            "clicks": camp.stats.clicks,
            "conversions": camp.stats.conversions,
            "cost": int(camp.stats.cost),
            "ctr": float(camp.stats.ctr) if camp.stats.ctr is not None else None,
            "cvr": float(camp.stats.cvr) if camp.stats.cvr is not None else None,
            "cpc": float(camp.stats.cpc) if camp.stats.cpc is not None else None,
            "cpa": float(camp.stats.cpa) if camp.stats.cpa is not None else None,
            "budget_used_pct": float(camp.stats.budget_used_pct) if camp.stats.budget_used_pct is not None else None,
        },
    }


def handle_get_stats(ctx: ToolContext, args: GetStatsArgs) -> dict[str, Any]:
    filters = StatsFilters(
        campaign_id=args.campaign_id,
        channel_code=args.channel_code,
        date_from=args.date_from,
        date_to=args.date_to,
    )
    group = (args.group_by or "none").lower()
    if group == "channel":
        rows = stats_service.get_by_channel(ctx.db, ctx.user, filters)
        return {
            "group_by": "channel",
            "items": [
                {
                    "channel_code": r.channel.code,
                    "channel_name": r.channel.name,
                    "views": r.views,
                    "clicks": r.clicks,
                    "conversions": r.conversions,
                    "cost": int(r.cost),
                    "ctr": float(r.ctr) if r.ctr is not None else None,
                    "cvr": float(r.cvr) if r.cvr is not None else None,
                    "cpc": float(r.cpc) if r.cpc is not None else None,
                    "cpa": float(r.cpa) if r.cpa is not None else None,
                }
                for r in rows
            ],
        }
    if group == "campaign":
        c_rows = stats_service.get_by_campaign(ctx.db, ctx.user, filters)
        return {
            "group_by": "campaign",
            "items": [
                {
                    "campaign_id": r.campaign.id,
                    "campaign_name": r.campaign.name,
                    "status": r.campaign.status.value,
                    "budget": int(r.budget),
                    "cost": int(r.cost),
                    "used_pct": float(r.used_pct) if r.used_pct is not None else None,
                    "views": r.views,
                    "clicks": r.clicks,
                    "conversions": r.conversions,
                    "ctr": float(r.ctr) if r.ctr is not None else None,
                    "cpa": float(r.cpa) if r.cpa is not None else None,
                }
                for r in c_rows
            ],
        }
    if group in ("day", "week", "month"):
        t_rows = stats_service.get_timeseries(ctx.db, ctx.user, filters, granularity=group)  # type: ignore[arg-type]
        return {
            "group_by": group,
            "items": [
                {
                    "period": r.period,
                    "views": r.views,
                    "clicks": r.clicks,
                    "conversions": r.conversions,
                    "cost": int(r.cost),
                }
                for r in t_rows
            ],
        }

    # "none" -> overview
    ov = stats_service.get_overview(ctx.db, ctx.user, filters)
    return {
        "group_by": "none",
        "totals": {
            "views": ov.totals.views,
            "clicks": ov.totals.clicks,
            "conversions": ov.totals.conversions,
            "cost": int(ov.totals.cost),
        },
        "rates": {
            "ctr": float(ov.rates.ctr) if ov.rates.ctr is not None else None,
            "cvr": float(ov.rates.cvr) if ov.rates.cvr is not None else None,
            "cpc": float(ov.rates.cpc) if ov.rates.cpc is not None else None,
            "cpa": float(ov.rates.cpa) if ov.rates.cpa is not None else None,
            "cpm": float(ov.rates.cpm) if ov.rates.cpm is not None else None,
        },
        "budget": {
            "total_budget": int(ov.budget.total_budget) if ov.budget.total_budget is not None else None,
            "spent": int(ov.budget.spent),
            "used_pct": float(ov.budget.used_pct) if ov.budget.used_pct is not None else None,
        },
        "campaigns_count": ov.campaigns.by_status,
        "contents_count": ov.contents.by_status,
        "pending_reviews": ov.pending_reviews,
        "schedules_today": ov.schedules_today,
    }


def handle_list_contents(ctx: ToolContext, args: ListContentsArgs) -> dict[str, Any]:
    filters = ContentFilters(
        campaign_id=args.campaign_id,
        channel_code=args.channel_code,
        status=args.status,  # type: ignore[arg-type]
        q=args.q,
    )
    page = content_service.list_contents(ctx.db, ctx.user, filters=filters, page=1, page_size=args.limit)
    items = []
    for c in page.items:
        items.append({
            "id": c.id,
            "campaign_id": c.campaign_id,
            "campaign_name": c.campaign.name,
            "channel_code": c.channel.code,
            "content_type": c.content_type.value,
            "title": c.title,
            "status": c.status.value,
            "status_label": content_service.STATUS_LABELS.get(c.status, c.status.value),
            "origin": c.origin.value,
            "created_by": c.created_by.full_name,
        })
    return {"total": page.total, "limit": args.limit, "contents": items}


def handle_get_content(ctx: ToolContext, args: GetContentArgs) -> dict[str, Any]:
    c = content_service.get_content(ctx.db, ctx.user, args.content_id)
    reviews = content_service.list_reviews(ctx.db, ctx.user, args.content_id)
    return {
        "id": c.id,
        "campaign_id": c.campaign_id,
        "campaign_name": c.campaign.name,
        "channel_code": c.channel.code,
        "content_type": c.content_type.value,
        "title": c.title,
        "body": c.body,
        "cta": c.cta,
        "status": c.status.value,
        "status_label": content_service.STATUS_LABELS.get(c.status, c.status.value),
        "origin": c.origin.value,
        "created_by": c.created_by.full_name,
        "published_url": c.published_url,
        "reviews": [
            {
                "reviewer": r.reviewer.full_name,
                "decision": r.decision.value,
                "comment": r.comment,
                "created_at": r.created_at.isoformat(),
            }
            for r in reviews
        ],
    }


def handle_list_schedules(ctx: ToolContext, args: ListSchedulesArgs) -> dict[str, Any]:
    filters = ScheduleFilters(
        date_from=args.date_from,
        date_to=args.date_to,
        campaign_id=args.campaign_id,
    )
    schedules = schedule_service.list_schedules(ctx.db, ctx.user, filters)
    return {
        "schedules": [
            {
                "id": s.id,
                "content_id": s.content_id,
                "content_title": s.content.title,
                "campaign_name": s.campaign.name,
                "channel_code": s.channel.code,
                "scheduled_at": s.scheduled_at.isoformat(),
                "assignee": s.assignee.full_name if s.assignee else None,
                "status": s.status.value,
                "note": s.note,
            }
            for s in schedules
        ]
    }


def handle_list_channels(ctx: ToolContext, args: EmptyArgs) -> dict[str, Any]:
    channels = channel_service.list_channels(ctx.db, ctx.user, include_inactive=False)
    return {
        "channels": [
            {
                "id": ch.id,
                "code": ch.code,
                "name": ch.name,
                "format_rules": ch.format_rules,
            }
            for ch in channels
        ]
    }


def handle_get_brand_profile(ctx: ToolContext, args: EmptyArgs) -> dict[str, Any]:
    p = brand_service.get_brand_profile(ctx.db, ctx.user)
    return {
        "brand_name": p.brand_name,
        "description": p.description,
        "tone_of_voice": p.tone_of_voice,
        "target_audience": p.target_audience,
        "guidelines": p.guidelines,
        "banned_keywords": [k.keyword for k in p.banned_keywords],
    }


def handle_check_banned_keywords(ctx: ToolContext, args: CheckBannedKeywordsArgs) -> dict[str, Any]:
    matches = brand_service.check_banned(ctx.db, args.text)
    return {
        "has_banned_keywords": len(matches) > 0,
        "matches": [{"keyword": m.keyword, "count": m.count} for m in matches],
    }


# --- Write Handlers (AiAction PROPOSED Only) ----------------------------------

def handle_propose_content_drafts(ctx: ToolContext, args: ProposeContentDraftsArgs) -> dict[str, Any]:
    banned_notes: list[str] = []
    for idx, item in enumerate(args.items):
        camp = campaign_service.find_campaign_for_reference(ctx.db, item.campaign_id, field=f"items.{idx}.campaign_id")
        if camp.status in campaign_service.CLOSED_STATUSES:
            raise ValidationFailed(fields={f"items.{idx}.campaign_id": f"Chiến dịch '{camp.name}' đã đóng"})
        ch = channel_service.resolve_channel(ctx.db, None, item.channel_code, field=f"items.{idx}.channel_code")
        if ch.id not in campaign_service.campaign_channel_ids(camp):
            raise ValidationFailed(fields={f"items.{idx}.channel_code": f"Kênh {ch.name} không thuộc chiến dịch '{camp.name}'"})

        text_to_check = f"{item.title}\n{item.body}\n{item.cta or ''}"
        matches = brand_service.check_banned(ctx.db, text_to_check)
        if matches:
            kw_list = ", ".join(f"'{m.keyword}'" for m in matches)
            banned_notes.append(f"bài #{idx + 1} có từ nhạy cảm: {kw_list}")

    count = len(args.items)
    summary = f"Đề xuất tạo {count} bản nháp nội dung"
    if banned_notes:
        summary += f" (Lưu ý: {'; '.join(banned_notes)})"

    action = AiAction(
        thread_id=ctx.thread.id,
        message_id=ctx.message.id,
        user_id=ctx.user.id,
        tool="propose_content_drafts",
        args_json=args.model_dump(mode="json"),
        summary=summary,
        status=AiActionStatus.PROPOSED,
    )
    ctx.db.add(action)
    ctx.db.commit()
    ctx.db.refresh(action)

    return {
        "action_id": action.id,
        "status": "PROPOSED",
        "message": f"Đã tạo đề xuất #{action.id}, chờ người dùng xác nhận",
        "summary": summary,
    }


def handle_propose_campaign(ctx: ToolContext, args: ProposeCampaignArgs) -> dict[str, Any]:
    if args.end_date < args.start_date:
        raise ValidationFailed(fields={"end_date": "Ngày kết thúc phải sau hoặc bằng ngày bắt đầu"})

    # Validate channel codes
    for idx, ch in enumerate(args.channels):
        channel_service.resolve_channel(ctx.db, None, ch.channel_code, field=f"channels.{idx}.channel_code")

    planned_total = sum(ch.planned_budget for ch in args.channels if ch.planned_budget is not None)
    if planned_total > args.budget:
        raise ValidationFailed(fields={"budget": "Tổng ngân sách phân bổ theo kênh vượt quá ngân sách chiến dịch"})

    summary = f"Đề xuất tạo chiến dịch mới '{args.name}' (Ngân sách: {args.budget:,} VND, {len(args.channels)} kênh)"
    action = AiAction(
        thread_id=ctx.thread.id,
        message_id=ctx.message.id,
        user_id=ctx.user.id,
        tool="propose_campaign",
        args_json=args.model_dump(mode="json"),
        summary=summary,
        status=AiActionStatus.PROPOSED,
    )
    ctx.db.add(action)
    ctx.db.commit()
    ctx.db.refresh(action)

    return {
        "action_id": action.id,
        "status": "PROPOSED",
        "message": f"Đã tạo đề xuất #{action.id}, chờ người dùng xác nhận",
        "summary": summary,
    }


def handle_propose_campaign_update(ctx: ToolContext, args: ProposeCampaignUpdateArgs) -> dict[str, Any]:
    camp = campaign_service.get_campaign_orm(ctx.db, args.campaign_id)
    if args.start_date or args.end_date:
        s = args.start_date or camp.start_date
        e = args.end_date or camp.end_date
        if e < s:
            raise ValidationFailed(fields={"end_date": "Ngày kết thúc phải sau hoặc bằng ngày bắt đầu"})

    if args.channels is not None:
        for idx, ch in enumerate(args.channels):
            channel_service.resolve_channel(ctx.db, None, ch.channel_code, field=f"channels.{idx}.channel_code")

    summary = f"Đề xuất cập nhật chiến dịch #{camp.id} '{camp.name}'"
    action = AiAction(
        thread_id=ctx.thread.id,
        message_id=ctx.message.id,
        user_id=ctx.user.id,
        tool="propose_campaign_update",
        args_json=args.model_dump(mode="json"),
        summary=summary,
        status=AiActionStatus.PROPOSED,
    )
    ctx.db.add(action)
    ctx.db.commit()
    ctx.db.refresh(action)

    return {
        "action_id": action.id,
        "status": "PROPOSED",
        "message": f"Đã tạo đề xuất #{action.id}, chờ người dùng xác nhận",
        "summary": summary,
    }


def handle_propose_schedule(ctx: ToolContext, args: ProposeScheduleArgs) -> dict[str, Any]:
    content = content_service.get_content_orm(ctx.db, args.content_id)
    if content.status in schedule_service.NOT_SCHEDULABLE:
        raise ValidationFailed(
            fields={"content_id": f"Không thể lập lịch cho nội dung đang ở trạng thái '{content_service.STATUS_LABELS[content.status]}'"}
        )
    if content.campaign.status in campaign_service.CLOSED_STATUSES:
        raise ValidationFailed(fields={"content_id": "Chiến dịch đã kết thúc hoặc bị huỷ"})

    when_utc = to_utc(args.scheduled_at)
    if when_utc < now_utc() - schedule_service.PAST_TOLERANCE:
        raise ValidationFailed(fields={"scheduled_at": "Thời điểm đăng phải ở tương lai"})

    summary = f"Đề xuất lập lịch đăng cho bài '{content.title[:40]}' vào lúc {when_utc.strftime('%H:%M %d/%m/%Y UTC')}"
    action = AiAction(
        thread_id=ctx.thread.id,
        message_id=ctx.message.id,
        user_id=ctx.user.id,
        tool="propose_schedule",
        args_json=args.model_dump(mode="json"),
        summary=summary,
        status=AiActionStatus.PROPOSED,
    )
    ctx.db.add(action)
    ctx.db.commit()
    ctx.db.refresh(action)

    return {
        "action_id": action.id,
        "status": "PROPOSED",
        "message": f"Đã tạo đề xuất #{action.id}, chờ người dùng xác nhận",
        "summary": summary,
    }


def handle_propose_metrics(ctx: ToolContext, args: ProposeMetricsArgs) -> dict[str, Any]:
    for idx, row in enumerate(args.rows):
        camp = campaign_service.find_campaign_for_reference(ctx.db, row.campaign_id, field=f"rows.{idx}.campaign_id")
        ch = channel_service.resolve_channel(ctx.db, None, row.channel_code, field=f"rows.{idx}.channel_code")
        if ch.id not in campaign_service.campaign_channel_ids(camp):
            raise ValidationFailed(fields={f"rows.{idx}.channel_code": f"Kênh {ch.name} không thuộc chiến dịch '{camp.name}'"})
        metric_service.validate_metric_counts(row.views, row.clicks, row.conversions, row.cost, field_prefix=f"rows.{idx}.")

    summary = f"Đề xuất ghi nhận số liệu cho {len(args.rows)} bản ghi kênh/chiến dịch"
    action = AiAction(
        thread_id=ctx.thread.id,
        message_id=ctx.message.id,
        user_id=ctx.user.id,
        tool="propose_metrics",
        args_json=args.model_dump(mode="json"),
        summary=summary,
        status=AiActionStatus.PROPOSED,
    )
    ctx.db.add(action)
    ctx.db.commit()
    ctx.db.refresh(action)

    return {
        "action_id": action.id,
        "status": "PROPOSED",
        "message": f"Đã tạo đề xuất #{action.id}, chờ người dùng xác nhận",
        "summary": summary,
    }


# --- Tool Registry -----------------------------------------------------------

@dataclass
class ToolDefinition:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[[ToolContext, Any], dict[str, Any]]
    is_write: bool = False


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())


registry = ToolRegistry()

# Register READ tools
registry.register(
    ToolDefinition(
        name="list_campaigns",
        description="Tra cứu danh sách chiến dịch tiếp thị theo từ khoá, trạng thái, kênh hoặc thời gian",
        args_model=ListCampaignsArgs,
        handler=handle_list_campaigns,
    )
)
registry.register(
    ToolDefinition(
        name="get_campaign",
        description="Xem chi tiết chiến dịch gồm thông tin mục tiêu, ngân sách, các kênh và thống kê hiệu quả tổng thể",
        args_model=GetCampaignArgs,
        handler=handle_get_campaign,
    )
)
registry.register(
    ToolDefinition(
        name="get_stats",
        description="Xem số liệu thống kê hiệu quả tiếp thị (tổng quan, phân tích theo kênh, theo chiến dịch hoặc theo thời gian ngày/tuần/tháng)",
        args_model=GetStatsArgs,
        handler=handle_get_stats,
    )
)
registry.register(
    ToolDefinition(
        name="list_contents",
        description="Tra cứu danh sách bài viết/nội dung theo chiến dịch, kênh, trạng thái hoặc từ khoá",
        args_model=ListContentsArgs,
        handler=handle_list_contents,
    )
)
registry.register(
    ToolDefinition(
        name="get_content",
        description="Xem chi tiết một bài viết/nội dung marketing gồm tiêu đề, văn bản, kênh và lịch sử phản hồi duyệt",
        args_model=GetContentArgs,
        handler=handle_get_content,
    )
)
registry.register(
    ToolDefinition(
        name="list_schedules",
        description="Tra cứu lịch đăng nội dung theo khoảng thời gian hoặc theo chiến dịch",
        args_model=ListSchedulesArgs,
        handler=handle_list_schedules,
    )
)
registry.register(
    ToolDefinition(
        name="list_channels",
        description="Lấy danh sách các kênh truyền thông đang kích hoạt kèm quy chuẩn định dạng (format_rules)",
        args_model=EmptyArgs,
        handler=handle_list_channels,
    )
)
registry.register(
    ToolDefinition(
        name="get_brand_profile",
        description="Xem hồ sơ thương hiệu (tên thương hiệu, văn phong tone-of-voice, đối tượng mục tiêu, hướng dẫn và danh sách từ cấm)",
        args_model=EmptyArgs,
        handler=handle_get_brand_profile,
    )
)
registry.register(
    ToolDefinition(
        name="check_banned_keywords",
        description="Kiểm tra một đoạn văn bản xem có chứa từ cấm hoặc từ khoá nhạy cảm của thương hiệu hay không",
        args_model=CheckBannedKeywordsArgs,
        handler=handle_check_banned_keywords,
    )
)

# Register WRITE tools
registry.register(
    ToolDefinition(
        name="propose_content_drafts",
        description="Tạo đề xuất soạn thảo nhiều bản nháp nội dung (bài viết, email, kịch bản video, quảng cáo...). Chỉ tạo đề xuất chờ người dùng bấm Xác nhận.",
        args_model=ProposeContentDraftsArgs,
        handler=handle_propose_content_drafts,
        is_write=True,
    )
)
registry.register(
    ToolDefinition(
        name="propose_campaign",
        description="Tạo đề xuất một chiến dịch tiếp thị mới với mục tiêu, ngân sách và các kênh phân bổ. Chỉ tạo đề xuất chờ người dùng xác nhận.",
        args_model=ProposeCampaignArgs,
        handler=handle_propose_campaign,
        is_write=True,
    )
)
registry.register(
    ToolDefinition(
        name="propose_campaign_update",
        description="Tạo đề xuất chỉnh sửa thông tin hoặc phân bổ kênh của chiến dịch hiện có. Chỉ tạo đề xuất chờ người dùng xác nhận.",
        args_model=ProposeCampaignUpdateArgs,
        handler=handle_propose_campaign_update,
        is_write=True,
    )
)
registry.register(
    ToolDefinition(
        name="propose_schedule",
        description="Tạo đề xuất lên lịch đăng bài cho một nội dung marketing vào thời điểm cụ thể. Chỉ tạo đề xuất chờ người dùng xác nhận.",
        args_model=ProposeScheduleArgs,
        handler=handle_propose_schedule,
        is_write=True,
    )
)
registry.register(
    ToolDefinition(
        name="propose_metrics",
        description="Tạo đề xuất nhập hoặc cập nhật số liệu hiệu quả (views, clicks, conversions, cost) từ bảng dữ liệu người dùng cung cấp. Chỉ tạo đề xuất chờ người dùng xác nhận.",
        args_model=ProposeMetricsArgs,
        handler=handle_propose_metrics,
        is_write=True,
    )
)
