"""Kiểm thử ToolRegistry & các công cụ AI (CONTRACT §5: Đọc thực thi ngay, Ghi chỉ đề xuất)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from app.assistant.context import ToolContext
from app.assistant.tools import (
    CheckBannedKeywordsArgs,
    EmptyArgs,
    GetCampaignArgs,
    GetContentArgs,
    GetStatsArgs,
    ListCampaignsArgs,
    ListContentsArgs,
    ListSchedulesArgs,
    ProposeCampaignArgs,
    ProposeCampaignChannelItem,
    ProposeCampaignUpdateArgs,
    ProposeContentDraftItem,
    ProposeContentDraftsArgs,
    ProposeMetricRowItem,
    ProposeMetricsArgs,
    ProposeScheduleArgs,
    registry,
)
from app.core.errors import ValidationFailed
from app.core.timeutil import now_utc, today_vn
from app.models import (
    AiAction,
    AiMessage,
    AiThread,
    BannedKeyword,
    Campaign,
    Channel,
    Content,
    Schedule,
    User,
)
from app.models.enums import (
    AiActionStatus,
    AiMessageRole,
    AiMessageStatus,
    CampaignGoal,
    ContentType,
    ScheduleStatus,
)


@pytest.fixture
def tool_context(db: Session, marketer1_user: User, sample_campaign: Campaign) -> ToolContext:
    thread = AiThread(
        user_id=marketer1_user.id,
        campaign_id=sample_campaign.id,
        title="Phiên kiểm thử Tools",
        last_message_at=now_utc(),
    )
    db.add(thread)
    db.flush()

    message = AiMessage(
        thread_id=thread.id,
        role=AiMessageRole.ASSISTANT,
        content="",
        status=AiMessageStatus.STREAMING,
    )
    db.add(message)
    db.commit()
    db.refresh(thread)
    db.refresh(message)
    return ToolContext(db=db, user=marketer1_user, thread=thread, message=message)


def test_read_tools_execution(
    tool_context: ToolContext,
    sample_campaign: Campaign,
    sample_content: Content,
    test_channels: dict[str, Channel],
    db: Session,
):
    ctx = tool_context

    # 1. list_campaigns
    tool = registry.get("list_campaigns")
    assert tool is not None
    res = tool.handler(ctx, ListCampaignsArgs())
    assert res["total"] >= 1
    assert any(c["id"] == sample_campaign.id for c in res["campaigns"])

    # 2. get_campaign
    tool = registry.get("get_campaign")
    res = tool.handler(ctx, GetCampaignArgs(campaign_id=sample_campaign.id))
    assert res["id"] == sample_campaign.id
    assert res["name"] == sample_campaign.name
    assert "stats" in res
    assert "stats_by_channel" in res
    assert len(res["channels"]) == 2

    # 3. get_stats
    tool = registry.get("get_stats")
    # overview
    res_ov = tool.handler(ctx, GetStatsArgs(campaign_id=sample_campaign.id, group_by="none"))
    assert res_ov["group_by"] == "none"
    assert "totals" in res_ov
    # by channel
    res_ch = tool.handler(ctx, GetStatsArgs(group_by="channel"))
    assert res_ch["group_by"] == "channel"
    # by campaign
    res_camp = tool.handler(ctx, GetStatsArgs(group_by="campaign"))
    assert res_camp["group_by"] == "campaign"
    # timeseries
    res_time = tool.handler(ctx, GetStatsArgs(group_by="day"))
    assert res_time["group_by"] == "day"

    # 4. list_contents
    tool = registry.get("list_contents")
    res = tool.handler(ctx, ListContentsArgs(campaign_id=sample_campaign.id))
    assert res["total"] >= 1
    assert any(c["id"] == sample_content.id for c in res["contents"])

    # 5. get_content
    tool = registry.get("get_content")
    res = tool.handler(ctx, GetContentArgs(content_id=sample_content.id))
    assert res["id"] == sample_content.id
    assert res["title"] == sample_content.title

    # 6. list_schedules
    sched = Schedule(
        content_id=sample_content.id,
        scheduled_at=now_utc() + timedelta(days=2),
        assignee_id=ctx.user.id,
        status=ScheduleStatus.PLANNED,
        note="Đăng bài test",
    )
    db.add(sched)
    db.commit()
    tool = registry.get("list_schedules")
    res = tool.handler(ctx, ListSchedulesArgs())
    assert any(s["id"] == sched.id for s in res["schedules"])

    # 7. list_channels
    tool = registry.get("list_channels")
    res = tool.handler(ctx, EmptyArgs())
    assert len(res["channels"]) >= 7

    # 8. get_brand_profile
    tool = registry.get("get_brand_profile")
    res = tool.handler(ctx, EmptyArgs())
    assert "brand_name" in res
    assert "banned_keywords" in res

    # 9. check_banned_keywords
    db.add(BannedKeyword(keyword="cam kết 100%"))
    db.commit()
    tool = registry.get("check_banned_keywords")
    res = tool.handler(ctx, CheckBannedKeywordsArgs(text="Sản phẩm cam kết 100% chính hãng"))
    assert res["has_banned_keywords"] is True
    assert res["matches"][0]["keyword"] == "cam kết 100%"


def test_write_tools_only_create_proposed_actions(
    tool_context: ToolContext,
    sample_campaign: Campaign,
    sample_content: Content,
    db: Session,
):
    ctx = tool_context
    today = today_vn()

    # 1. propose_content_drafts
    tool = registry.get("propose_content_drafts")
    initial_content_count = db.query(Content).count()
    res = tool.handler(
        ctx,
        ProposeContentDraftsArgs(
            items=[
                ProposeContentDraftItem(
                    campaign_id=sample_campaign.id,
                    channel_code="FACEBOOK",
                    content_type=ContentType.SOCIAL_POST,
                    title="Bản nháp AI #1",
                    body="Nội dung bài viết do AI gợi ý",
                    cta="Xem chi tiết",
                    status="PENDING_REVIEW",
                )
            ]
        ),
    )
    assert res["status"] == "PROPOSED"
    action_id = res["action_id"]
    action = db.get(AiAction, action_id)
    assert action is not None
    assert action.status == AiActionStatus.PROPOSED
    assert action.tool == "propose_content_drafts"
    # Ensure NO content was created directly in contents table
    assert db.query(Content).count() == initial_content_count

    # 2. propose_campaign
    tool = registry.get("propose_campaign")
    initial_camp_count = db.query(Campaign).count()
    res = tool.handler(
        ctx,
        ProposeCampaignArgs(
            name="Chiến dịch AI Mùa Hè",
            goal=CampaignGoal.AWARENESS,
            objective="Mở rộng tệp khách hàng",
            target_audience="Giới trẻ 18-25",
            product="Trà Trái Cây",
            start_date=today,
            end_date=today + timedelta(days=30),
            budget=15_000_000,
            channels=[ProposeCampaignChannelItem(channel_code="FACEBOOK", planned_budget=10_000_000)],
        ),
    )
    assert res["status"] == "PROPOSED"
    assert db.query(Campaign).count() == initial_camp_count

    # 3. propose_campaign_update
    tool = registry.get("propose_campaign_update")
    res = tool.handler(
        ctx,
        ProposeCampaignUpdateArgs(
            campaign_id=sample_campaign.id,
            name="Tên chiến dịch đã sửa",
        ),
    )
    assert res["status"] == "PROPOSED"

    # 4. propose_schedule
    tool = registry.get("propose_schedule")
    initial_sched_count = db.query(Schedule).count()
    res = tool.handler(
        ctx,
        ProposeScheduleArgs(
            content_id=sample_content.id,
            scheduled_at=now_utc() + timedelta(days=3),
            note="Lịch đăng đề xuất",
        ),
    )
    assert res["status"] == "PROPOSED"
    assert db.query(Schedule).count() == initial_sched_count

    # 5. propose_metrics
    tool = registry.get("propose_metrics")
    res = tool.handler(
        ctx,
        ProposeMetricsArgs(
            rows=[
                ProposeMetricRowItem(
                    campaign_id=sample_campaign.id,
                    channel_code="FACEBOOK",
                    metric_date=today,
                    views=1000,
                    clicks=50,
                    conversions=5,
                    cost=200_000,
                )
            ]
        ),
    )
    assert res["status"] == "PROPOSED"


def test_tool_validations(tool_context: ToolContext, sample_campaign: Campaign, db: Session):
    ctx = tool_context
    today = today_vn()

    # End date before start date
    tool_camp = registry.get("propose_campaign")
    with pytest.raises(ValidationFailed):
        tool_camp.handler(
            ctx,
            ProposeCampaignArgs(
                name="Chiến dịch lỗi ngày",
                goal=CampaignGoal.TRAFFIC,
                objective="Test",
                target_audience="Test",
                product="Test",
                start_date=today + timedelta(days=10),
                end_date=today,
                budget=5_000_000,
                channels=[ProposeCampaignChannelItem(channel_code="FACEBOOK")],
            ),
        )

    # Channel not in campaign
    tool_drafts = registry.get("propose_content_drafts")
    with pytest.raises(ValidationFailed):
        tool_drafts.handler(
            ctx,
            ProposeContentDraftsArgs(
                items=[
                    ProposeContentDraftItem(
                        campaign_id=sample_campaign.id,
                        channel_code="TIKTOK",  # TIKTOK not linked to sample_campaign
                        content_type=ContentType.SOCIAL_POST,
                        title="Bài TikTok",
                        body="Test",
                    )
                ]
            ),
        )

    # Metrics count validation: clicks > views
    tool_metrics = registry.get("propose_metrics")
    with pytest.raises(ValidationFailed):
        tool_metrics.handler(
            ctx,
            ProposeMetricsArgs(
                rows=[
                    ProposeMetricRowItem(
                        campaign_id=sample_campaign.id,
                        channel_code="FACEBOOK",
                        metric_date=today,
                        views=10,
                        clicks=50,  # clicks > views
                        conversions=0,
                        cost=1000,
                    )
                ]
            ),
        )
