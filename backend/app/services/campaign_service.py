"""Chiến dịch marketing: CRUD, lọc, thống kê tổng, phân quyền (CONTRACT §2, §4)."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import (
    Conflict,
    InvalidTransition,
    NotFound,
    PermissionDenied,
    ValidationFailed,
)
from app.core.pagination import Page, apply_sort, paginate
from app.models import Campaign, CampaignChannel, Channel, Content, Metric, User
from app.models.enums import CampaignStatus, ContentStatus
from app.schemas.campaign import (
    CampaignChannelIn,
    CampaignChannelOut,
    CampaignCreate,
    CampaignDetail,
    CampaignFilters,
    CampaignListItem,
    CampaignStats,
    CampaignUpdate,
)
from app.services import channel_service, user_service
from app.services.common import compute_rates, like_pattern, percent

ALLOWED_TRANSITIONS: dict[CampaignStatus, set[CampaignStatus]] = {
    CampaignStatus.PLANNED: {CampaignStatus.ACTIVE, CampaignStatus.CANCELLED},
    CampaignStatus.ACTIVE: {CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.CANCELLED},
    CampaignStatus.PAUSED: {CampaignStatus.ACTIVE, CampaignStatus.COMPLETED, CampaignStatus.CANCELLED},
    CampaignStatus.COMPLETED: set(),
    CampaignStatus.CANCELLED: set(),
}

STATUS_LABELS = {
    CampaignStatus.PLANNED: "Lên kế hoạch",
    CampaignStatus.ACTIVE: "Đang chạy",
    CampaignStatus.PAUSED: "Tạm dừng",
    CampaignStatus.COMPLETED: "Hoàn thành",
    CampaignStatus.CANCELLED: "Đã huỷ",
}

CLOSED_STATUSES = {CampaignStatus.COMPLETED, CampaignStatus.CANCELLED}


# --- Truy vấn nội bộ dùng chung -----------------------------------------------

def get_campaign_orm(db: Session, campaign_id: int) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise NotFound("Không tìm thấy chiến dịch")
    return campaign


def find_campaign_for_reference(db: Session, campaign_id: int, field: str = "campaign_id") -> Campaign:
    """Dùng khi chiến dịch là khoá ngoại trong input: không tồn tại → 422 thay vì 404."""
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise ValidationFailed(fields={field: "Chiến dịch không tồn tại"})
    return campaign


def can_edit(user: User, campaign: Campaign) -> bool:
    return user.is_manager or campaign.owner_id == user.id


def ensure_can_edit(user: User, campaign: Campaign) -> None:
    if not can_edit(user, campaign):
        raise PermissionDenied("Bạn chỉ được sửa/xoá chiến dịch do mình phụ trách")


def campaign_channel_ids(campaign: Campaign) -> set[int]:
    return {link.channel_id for link in campaign.channel_links}


def _spent_by_campaign(db: Session, ids: list[int]) -> dict[int, Decimal]:
    if not ids:
        return {}
    rows = db.execute(
        select(Metric.campaign_id, func.coalesce(func.sum(Metric.cost), 0))
        .where(Metric.campaign_id.in_(ids))
        .group_by(Metric.campaign_id)
    ).all()
    return {cid: Decimal(str(total or 0)) for cid, total in rows}


def _content_counts(db: Session, ids: list[int]) -> dict[int, dict[str, int]]:
    result: dict[int, dict[str, int]] = defaultdict(lambda: {s.value: 0 for s in ContentStatus})
    if not ids:
        return result
    rows = db.execute(
        select(Content.campaign_id, Content.status, func.count(Content.id))
        .where(Content.campaign_id.in_(ids))
        .group_by(Content.campaign_id, Content.status)
    ).all()
    for cid, status, count in rows:
        result[cid][ContentStatus(status).value] = int(count)
    return result


def _channels_out(campaign: Campaign) -> list[CampaignChannelOut]:
    return [
        CampaignChannelOut(
            id=link.channel.id, code=link.channel.code, name=link.channel.name, planned_budget=link.planned_budget
        )
        for link in campaign.channel_links
    ]


def _list_item(campaign: Campaign, spent: Decimal, counts: dict[str, int]) -> dict:
    return {
        "id": campaign.id,
        "name": campaign.name,
        "goal": campaign.goal,
        "status": campaign.status,
        "start_date": campaign.start_date,
        "end_date": campaign.end_date,
        "budget": campaign.budget,
        "owner": {"id": campaign.owner.id, "full_name": campaign.owner.full_name},
        "channels": _channels_out(campaign),
        "spent": spent,
        "content_counts": counts,
        "created_at": campaign.created_at,
        "updated_at": campaign.updated_at,
    }


def campaign_stats(db: Session, campaign: Campaign) -> CampaignStats:
    views, clicks, conversions, cost = db.execute(
        select(
            func.coalesce(func.sum(Metric.views), 0),
            func.coalesce(func.sum(Metric.clicks), 0),
            func.coalesce(func.sum(Metric.conversions), 0),
            func.coalesce(func.sum(Metric.cost), 0),
        ).where(Metric.campaign_id == campaign.id)
    ).one()
    rates = compute_rates(views, clicks, conversions, cost)
    return CampaignStats(
        views=int(views),
        clicks=int(clicks),
        conversions=int(conversions),
        cost=Decimal(str(cost)),
        **rates,
        budget_used_pct=percent(cost, campaign.budget),
    )


def _detail(db: Session, campaign: Campaign) -> CampaignDetail:
    spent = _spent_by_campaign(db, [campaign.id]).get(campaign.id, Decimal(0))
    counts = _content_counts(db, [campaign.id])[campaign.id]
    data = _list_item(campaign, spent, counts)
    data.update(
        owner_id=campaign.owner_id,
        objective=campaign.objective,
        target_audience=campaign.target_audience,
        product=campaign.product,
        key_message=campaign.key_message,
        stats=campaign_stats(db, campaign),
    )
    return CampaignDetail.model_validate(data)


# --- Đọc ----------------------------------------------------------------------

def _apply_filters(db: Session, stmt, filters: CampaignFilters):
    if filters.date_from and filters.date_to and filters.date_from > filters.date_to:
        raise ValidationFailed(fields={"date_to": "Ngày kết thúc phải sau hoặc bằng ngày bắt đầu"})
    if filters.q:
        pattern = like_pattern(filters.q)
        stmt = stmt.where(
            or_(Campaign.name.ilike(pattern, escape="\\"), Campaign.product.ilike(pattern, escape="\\"))
        )
    if filters.status:
        stmt = stmt.where(Campaign.status == filters.status)
    if filters.goal:
        stmt = stmt.where(Campaign.goal == filters.goal)
    if filters.owner_id:
        stmt = stmt.where(Campaign.owner_id == filters.owner_id)
    channel_id = filters.channel_id
    if channel_id is None and filters.channel_code:
        channel = channel_service.find_by_code(db, filters.channel_code)
        channel_id = channel.id if channel else -1
    if channel_id is not None:
        stmt = stmt.where(
            exists().where(CampaignChannel.campaign_id == Campaign.id, CampaignChannel.channel_id == channel_id)
        )
    # Lọc theo giao nhau khoảng [start_date, end_date] với [date_from, date_to].
    if filters.date_to:
        stmt = stmt.where(Campaign.start_date <= filters.date_to)
    if filters.date_from:
        stmt = stmt.where(Campaign.end_date >= filters.date_from)
    return stmt


def filtered_campaign_ids_stmt(db: Session, filters: CampaignFilters):
    """Subquery id chiến dịch theo bộ lọc (dùng cho thống kê)."""
    return _apply_filters(db, select(Campaign.id), filters)


SORT_FIELDS = {
    "name": Campaign.name,
    "start_date": Campaign.start_date,
    "end_date": Campaign.end_date,
    "budget": Campaign.budget,
    "status": Campaign.status,
    "created_at": Campaign.created_at,
    "updated_at": Campaign.updated_at,
}


def list_campaigns(
    db: Session,
    user: User,
    filters: CampaignFilters | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: str | None = None,
) -> Page[CampaignListItem]:
    filters = filters or CampaignFilters()
    stmt = _apply_filters(db, select(Campaign), filters)
    stmt = apply_sort(stmt, sort, SORT_FIELDS, "-start_date", Campaign.id)
    items, total = paginate(db, stmt, page, page_size)
    ids = [c.id for c in items]
    spent = _spent_by_campaign(db, ids)
    counts = _content_counts(db, ids)
    return Page[CampaignListItem](
        items=[CampaignListItem.model_validate(_list_item(c, spent.get(c.id, Decimal(0)), counts[c.id])) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_campaign(db: Session, user: User, campaign_id: int) -> CampaignDetail:
    return _detail(db, get_campaign_orm(db, campaign_id))


# --- Ghi ----------------------------------------------------------------------

def _resolve_channel_links(
    db: Session, items: list[CampaignChannelIn], budget: Decimal | int, existing_ids: set[int] | None = None
) -> list[tuple[Channel, int | None]]:
    existing_ids = existing_ids or set()
    resolved: list[tuple[Channel, int | None]] = []
    seen: set[int] = set()
    for idx, item in enumerate(items):
        field = f"channels.{idx}"
        channel = channel_service.resolve_channel(db, item.channel_id, item.channel_code, field=field, require_active=False)
        if not channel.is_active and channel.id not in existing_ids:
            raise ValidationFailed(fields={field: f"Kênh {channel.name} đang tắt"})
        if channel.id in seen:
            raise ValidationFailed(fields={field: f"Kênh {channel.name} bị lặp"})
        seen.add(channel.id)
        resolved.append((channel, item.planned_budget))
    planned_total = sum(p for _, p in resolved if p is not None)
    if planned_total > Decimal(budget):
        raise ValidationFailed(
            fields={"channels": "Tổng ngân sách dự kiến theo kênh vượt ngân sách chiến dịch"}
        )
    return resolved


def _validate_dates(start, end) -> None:
    if end < start:
        raise ValidationFailed(fields={"end_date": "Ngày kết thúc phải sau hoặc bằng ngày bắt đầu"})


def create_campaign(db: Session, user: User, data: CampaignCreate) -> CampaignDetail:
    _validate_dates(data.start_date, data.end_date)
    links = _resolve_channel_links(db, data.channels, data.budget)
    campaign = Campaign(
        name=data.name,
        goal=data.goal,
        objective=data.objective,
        target_audience=data.target_audience,
        product=data.product,
        key_message=data.key_message or None,
        start_date=data.start_date,
        end_date=data.end_date,
        budget=Decimal(data.budget),
        status=CampaignStatus(data.status),
        owner_id=user.id,
    )
    campaign.channel_links = [
        CampaignChannel(channel_id=ch.id, planned_budget=None if pb is None else Decimal(pb)) for ch, pb in links
    ]
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return _detail(db, campaign)


def check_transition(current: CampaignStatus, target: CampaignStatus) -> None:
    if current == target:
        return
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransition(
            f"Không thể chuyển chiến dịch từ '{STATUS_LABELS[current]}' sang '{STATUS_LABELS[target]}'"
        )


def update_campaign(db: Session, user: User, campaign_id: int, data: CampaignUpdate) -> CampaignDetail:
    campaign = get_campaign_orm(db, campaign_id)
    ensure_can_edit(user, campaign)
    fields = data.model_dump(exclude_unset=True)

    if "owner_id" in fields and fields["owner_id"] is not None and fields["owner_id"] != campaign.owner_id:
        if not user.is_manager:
            raise PermissionDenied("Chỉ Quản lý marketing được đổi người phụ trách chiến dịch")
        user_service.get_active_user(db, fields["owner_id"], field="owner_id")
        campaign.owner_id = fields["owner_id"]

    start = fields.get("start_date") or campaign.start_date
    end = fields.get("end_date") or campaign.end_date
    _validate_dates(start, end)
    budget = fields["budget"] if fields.get("budget") is not None else campaign.budget

    if fields.get("status") is not None:
        check_transition(CampaignStatus(campaign.status), CampaignStatus(fields["status"]))

    if data.channels is not None:
        current_ids = campaign_channel_ids(campaign)
        links = _resolve_channel_links(db, data.channels, budget, existing_ids=current_ids)
        new_ids = {ch.id for ch, _ in links}
        removed = current_ids - new_ids
        if removed:
            used = db.execute(
                select(Channel.name).where(
                    Channel.id.in_(removed),
                    exists().where(Content.campaign_id == campaign.id, Content.channel_id == Channel.id)
                    | exists().where(Metric.campaign_id == campaign.id, Metric.channel_id == Channel.id),
                )
            ).scalars().all()
            if used:
                raise Conflict(
                    f"Không thể bỏ kênh {', '.join(used)} vì chiến dịch đã có nội dung hoặc số liệu trên kênh đó",
                    code="CHANNEL_HAS_DATA",
                )
        by_id = {link.channel_id: link for link in campaign.channel_links}
        new_links = []
        for ch, pb in links:
            link = by_id.get(ch.id) or CampaignChannel(channel_id=ch.id)
            link.planned_budget = None if pb is None else Decimal(pb)
            new_links.append(link)
        campaign.channel_links = new_links
    else:
        planned_total = sum(
            (link.planned_budget for link in campaign.channel_links if link.planned_budget is not None), Decimal(0)
        )
        if planned_total > Decimal(budget):
            raise ValidationFailed(fields={"budget": "Ngân sách nhỏ hơn tổng ngân sách dự kiến theo kênh"})

    for key in ("name", "goal", "objective", "target_audience", "product", "start_date", "end_date", "status"):
        if fields.get(key) is not None:
            setattr(campaign, key, fields[key])
    if "key_message" in fields:
        campaign.key_message = fields["key_message"] or None
    if fields.get("budget") is not None:
        campaign.budget = Decimal(fields["budget"])

    db.commit()
    db.refresh(campaign)
    return _detail(db, campaign)


def delete_campaign(db: Session, user: User, campaign_id: int) -> None:
    campaign = get_campaign_orm(db, campaign_id)
    ensure_can_edit(user, campaign)
    has_data = db.execute(
        select(
            exists().where(Content.campaign_id == campaign_id) | exists().where(Metric.campaign_id == campaign_id)
        )
    ).scalar()
    if has_data:
        raise Conflict(
            "Chiến dịch đã có nội dung hoặc số liệu nên không thể xoá. Hãy chuyển trạng thái sang 'Đã huỷ'.",
            code="CAMPAIGN_HAS_DATA",
        )
    db.delete(campaign)
    db.commit()
