"""Thống kê tổng quan, chuỗi thời gian và phân tích theo kênh / chiến dịch (CONTRACT §4, §10)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailed
from app.core.timeutil import today_vn, vn_day_end_utc, vn_day_start_utc
from app.models import (
    Campaign,
    CampaignChannel,
    Channel,
    Content,
    Metric,
    Schedule,
    User,
)
from app.models.enums import CampaignStatus, ContentStatus, MetricSource, ScheduleStatus
from app.schemas.common import ChannelRef
from app.schemas.stats import (
    BudgetSummary,
    CampaignStatsRef,
    CampaignStatsRow,
    ChannelStats,
    Granularity,
    Rates,
    StatsFilters,
    StatsOverview,
    StatusCounts,
    TimeseriesPoint,
    Totals,
)
from app.services import channel_service
from app.services.common import compute_rates, money_ratio, percent, ratio


def _apply_stats_filters(stmt, filters: StatsFilters, db: Session | None = None):
    if filters.date_from and filters.date_to and filters.date_from > filters.date_to:
        raise ValidationFailed(fields={"date_to": "Ngày kết thúc phải sau hoặc bằng ngày bắt đầu"})

    if filters.campaign_id:
        stmt = stmt.where(Metric.campaign_id == filters.campaign_id)
    channel_id = filters.channel_id
    if channel_id is None and filters.channel_code and db is not None:
        ch = channel_service.find_by_code(db, filters.channel_code)
        channel_id = ch.id if ch else -1
    if channel_id is not None:
        stmt = stmt.where(Metric.channel_id == channel_id)
    if filters.date_from:
        stmt = stmt.where(Metric.metric_date >= filters.date_from)
    if filters.date_to:
        stmt = stmt.where(Metric.metric_date <= filters.date_to)
    if filters.status:
        stmt = stmt.join(Campaign, Metric.campaign_id == Campaign.id).where(Campaign.status == filters.status)
    return stmt


def _resolve_channel_id(db: Session, filters: StatsFilters) -> int | None:
    """id kênh đang lọc (-1 nếu mã kênh không tồn tại); None nếu không lọc theo kênh."""
    if filters.channel_id is not None:
        return filters.channel_id
    if filters.channel_code:
        ch = channel_service.find_by_code(db, filters.channel_code)
        return ch.id if ch else -1
    return None


def _planned_budgets(db: Session, campaign_ids: list[int], channel_id: int) -> dict[int, Decimal]:
    """Ngân sách dự kiến của riêng một kênh theo từng chiến dịch (chỉ các chiến dịch có đặt ngân sách kênh)."""
    rows = db.execute(
        select(CampaignChannel.campaign_id, CampaignChannel.planned_budget).where(
            CampaignChannel.channel_id == channel_id,
            CampaignChannel.campaign_id.in_(campaign_ids),
            CampaignChannel.planned_budget.is_not(None),
        )
    ).all()
    return {cid: Decimal(str(pb)) for cid, pb in rows}


def get_overview(db: Session, user: User, filters: StatsFilters | None = None) -> StatsOverview:
    filters = filters or StatsFilters()

    # 1. Metric totals
    metric_stmt = select(
        func.coalesce(func.sum(Metric.views), 0),
        func.coalesce(func.sum(Metric.clicks), 0),
        func.coalesce(func.sum(Metric.conversions), 0),
        func.coalesce(func.sum(Metric.cost), 0),
    )
    metric_stmt = _apply_stats_filters(metric_stmt, filters, db)
    views, clicks, conversions, cost = db.execute(metric_stmt).one()
    views = int(views)
    clicks = int(clicks)
    conversions = int(conversions)
    cost_dec = Decimal(str(cost or 0))

    totals = Totals(views=views, clicks=clicks, conversions=conversions, cost=cost_dec)
    rates_dict = compute_rates(views, clicks, conversions, cost_dec)
    rates = Rates(**rates_dict)

    # 2. Budget summary
    camp_stmt = select(Campaign)
    if filters.campaign_id:
        camp_stmt = camp_stmt.where(Campaign.id == filters.campaign_id)
    if filters.status:
        camp_stmt = camp_stmt.where(Campaign.status == filters.status)
    channel_filter = _resolve_channel_id(db, filters)
    if channel_filter is not None:
        camp_stmt = camp_stmt.where(
            exists().where(CampaignChannel.campaign_id == Campaign.id, CampaignChannel.channel_id == channel_filter)
        )
    campaigns = list(db.execute(camp_stmt).scalars())

    if channel_filter is not None:
        # Đang lọc theo kênh: so chi phí của kênh đó với NGÂN SÁCH DỰ KIẾN CỦA KÊNH (không phải cả chiến dịch)
        planned = _planned_budgets(db, [c.id for c in campaigns], channel_filter)
        total_budget_dec = sum(planned.values(), Decimal(0)) if planned else None
    else:
        total_budget_dec = sum((c.budget for c in campaigns), Decimal(0)) if campaigns else None
    used_pct = percent(cost_dec, total_budget_dec) if total_budget_dec is not None and total_budget_dec > 0 else None

    budget = BudgetSummary(
        total_budget=total_budget_dec,
        spent=cost_dec,
        used_pct=used_pct,
    )

    # 3. Campaign counts by status
    camp_counts = {s.value: 0 for s in CampaignStatus}
    for c in db.execute(select(Campaign.status, func.count(Campaign.id)).group_by(Campaign.status)):
        camp_counts[CampaignStatus(c[0]).value] = int(c[1])

    # 4. Content counts by status
    content_stmt = select(Content.status, func.count(Content.id)).group_by(Content.status)
    if filters.campaign_id:
        content_stmt = content_stmt.where(Content.campaign_id == filters.campaign_id)
    content_counts = {s.value: 0 for s in ContentStatus}
    for c in db.execute(content_stmt):
        content_counts[ContentStatus(c[0]).value] = int(c[1])

    # 5. Pending reviews
    pending_stmt = select(func.count(Content.id)).where(Content.status == ContentStatus.PENDING_REVIEW)
    if filters.campaign_id:
        pending_stmt = pending_stmt.where(Content.campaign_id == filters.campaign_id)
    pending_reviews = int(db.execute(pending_stmt).scalar_one())

    # 6. Schedules today
    today = today_vn()
    sched_stmt = select(func.count(Schedule.id)).where(
        Schedule.status == ScheduleStatus.PLANNED,
        Schedule.scheduled_at >= vn_day_start_utc(today),
        Schedule.scheduled_at < vn_day_end_utc(today),
    )
    if filters.campaign_id:
        sched_stmt = sched_stmt.join(Content, Schedule.content_id == Content.id).where(Content.campaign_id == filters.campaign_id)
    schedules_today = int(db.execute(sched_stmt).scalar_one())

    # 7. Has seed data
    # Chỉ báo "Dữ liệu mẫu" khi CHÍNH tập số liệu đang xem có dòng SEED (áp dụng cùng bộ lọc)
    seed_stmt = _apply_stats_filters(select(Metric.id).where(Metric.source == MetricSource.SEED), filters, db)
    has_seed = db.execute(seed_stmt.limit(1)).first() is not None

    return StatsOverview(
        totals=totals,
        rates=rates,
        budget=budget,
        campaigns=StatusCounts(by_status=camp_counts),
        contents=StatusCounts(by_status=content_counts),
        pending_reviews=pending_reviews,
        schedules_today=schedules_today,
        has_seed_data=has_seed,
    )


def get_timeseries(
    db: Session,
    user: User,
    filters: StatsFilters | None = None,
    granularity: Granularity = "day",
) -> list[TimeseriesPoint]:
    filters = filters or StatsFilters()
    stmt = select(Metric.metric_date, Metric.views, Metric.clicks, Metric.conversions, Metric.cost)
    stmt = _apply_stats_filters(stmt, filters, db)
    rows = db.execute(stmt).all()

    def get_period(d: date) -> str:
        if granularity == "day":
            return d.strftime("%Y-%m-%d")
        if granularity == "week":
            iso_year, iso_week, _ = d.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        if granularity == "month":
            return d.strftime("%Y-%m")
        return d.strftime("%Y-%m-%d")

    agg: dict[str, dict[str, Any]] = defaultdict(lambda: {"views": 0, "clicks": 0, "conversions": 0, "cost": Decimal(0)})
    for m_date, views, clicks, convs, cost in rows:
        period = get_period(m_date)
        agg[period]["views"] += views or 0
        agg[period]["clicks"] += clicks or 0
        agg[period]["conversions"] += convs or 0
        agg[period]["cost"] += Decimal(str(cost or 0))

    sorted_periods = sorted(agg.keys())
    return [
        TimeseriesPoint(
            period=p,
            views=agg[p]["views"],
            clicks=agg[p]["clicks"],
            conversions=agg[p]["conversions"],
            cost=agg[p]["cost"],
        )
        for p in sorted_periods
    ]


def get_by_channel(db: Session, user: User, filters: StatsFilters | None = None) -> list[ChannelStats]:
    filters = filters or StatsFilters()
    stmt = select(
        Metric.channel_id,
        func.sum(Metric.views),
        func.sum(Metric.clicks),
        func.sum(Metric.conversions),
        func.sum(Metric.cost),
    ).group_by(Metric.channel_id)
    stmt = _apply_stats_filters(stmt, filters, db)

    rows = db.execute(stmt).all()
    if not rows:
        return []

    channel_ids = [r[0] for r in rows]
    channels = {c.id: c for c in db.execute(select(Channel).where(Channel.id.in_(channel_ids))).scalars()}

    result: list[ChannelStats] = []
    for ch_id, views, clicks, convs, cost in rows:
        ch = channels.get(ch_id)
        if ch is None:
            continue
        v = int(views or 0)
        c = int(clicks or 0)
        cv = int(convs or 0)
        cost_dec = Decimal(str(cost or 0))
        rates = compute_rates(v, c, cv, cost_dec)
        result.append(
            ChannelStats(
                channel=ChannelRef(id=ch.id, code=ch.code, name=ch.name),
                views=v,
                clicks=c,
                conversions=cv,
                cost=cost_dec,
                ctr=rates["ctr"],
                cvr=rates["cvr"],
                cpc=rates["cpc"],
                cpa=rates["cpa"],
            )
        )

    result.sort(key=lambda x: (x.cost, x.views), reverse=True)
    return result


def get_by_campaign(db: Session, user: User, filters: StatsFilters | None = None) -> list[CampaignStatsRow]:
    filters = filters or StatsFilters()

    # Base campaigns matching campaign filters
    camp_stmt = select(Campaign)
    if filters.campaign_id:
        camp_stmt = camp_stmt.where(Campaign.id == filters.campaign_id)
    if filters.status:
        camp_stmt = camp_stmt.where(Campaign.status == filters.status)
    channel_filter = _resolve_channel_id(db, filters)
    if channel_filter is not None:
        camp_stmt = camp_stmt.where(
            exists().where(CampaignChannel.campaign_id == Campaign.id, CampaignChannel.channel_id == channel_filter)
        )
    campaigns = list(db.execute(camp_stmt).scalars())

    if not campaigns:
        return []

    planned_by_campaign = (
        _planned_budgets(db, [c.id for c in campaigns], channel_filter) if channel_filter is not None else {}
    )

    camp_ids = [c.id for c in campaigns]

    # Metrics aggregated by campaign
    metric_stmt = (
        select(
            Metric.campaign_id,
            func.sum(Metric.views),
            func.sum(Metric.clicks),
            func.sum(Metric.conversions),
            func.sum(Metric.cost),
        )
        .where(Metric.campaign_id.in_(camp_ids))
        .group_by(Metric.campaign_id)
    )
    metric_stmt = _apply_stats_filters(metric_stmt, filters, db)
    metrics_map = {
        r[0]: (int(r[1] or 0), int(r[2] or 0), int(r[3] or 0), Decimal(str(r[4] or 0)))
        for r in db.execute(metric_stmt).all()
    }

    result: list[CampaignStatsRow] = []
    for camp in campaigns:
        m_views, m_clicks, m_convs, m_cost = metrics_map.get(camp.id, (0, 0, 0, Decimal(0)))
        # Lọc theo kênh: dùng ngân sách dự kiến của kênh đó; không có thì không tính tỉ lệ (null)
        budget_basis = planned_by_campaign.get(camp.id) if channel_filter is not None else camp.budget
        used_pct = percent(m_cost, budget_basis) if budget_basis is not None and budget_basis > 0 else None
        ctr_val = ratio(m_clicks, m_views)
        cpa_val = money_ratio(m_cost, m_convs)

        result.append(
            CampaignStatsRow(
                campaign=CampaignStatsRef(id=camp.id, name=camp.name, status=camp.status),
                budget=budget_basis if budget_basis is not None else Decimal(0),
                cost=m_cost,
                used_pct=used_pct,
                views=m_views,
                clicks=m_clicks,
                conversions=m_convs,
                ctr=ctr_val,
                cpa=cpa_val,
            )
        )

    result.sort(key=lambda x: (x.cost, x.budget), reverse=True)
    return result
