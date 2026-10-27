"""Số liệu hiệu quả chiến dịch (metrics), nhập tay, import CSV (CONTRACT §2, §4, §10)."""

from __future__ import annotations

import csv
import io
import math
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import (
    NotFound,
    PayloadTooLarge,
    PermissionDenied,
    ValidationFailed,
)
from app.core.pagination import Page, apply_sort, paginate
from app.models import Campaign, Channel, Metric, User
from app.models.enums import MetricSource
from app.schemas.metric import (
    ImportCommitIn,
    ImportCommitOut,
    ImportPreviewOut,
    ImportRow,
    ImportRowError,
    ImportSummary,
    MetricFilters,
    MetricIn,
    MetricOut,
    MetricUpdate,
)
from app.services import campaign_service, channel_service
from app.services.serializers import metric_out

MAX_CSV_BYTES = 2 * 1024 * 1024  # 2MB
MAX_CSV_ROWS = 5000


def get_metric_orm(db: Session, metric_id: int) -> Metric:
    metric = db.get(Metric, metric_id)
    if metric is None:
        raise NotFound("Không tìm thấy bản ghi số liệu")
    return metric


def can_edit(user: User, metric: Metric) -> bool:
    return user.is_manager or metric.entered_by == user.id


def ensure_can_edit(user: User, metric: Metric) -> None:
    if not can_edit(user, metric):
        raise PermissionDenied("Bạn chỉ được sửa hoặc xoá số liệu do chính mình nhập")


def validate_metric_counts(
    views: int, clicks: int, conversions: int, cost: Decimal | int, field_prefix: str = ""
) -> None:
    errors: dict[str, str] = {}
    if views < 0:
        errors[f"{field_prefix}views"] = "Lượt xem không được âm"
    if clicks < 0:
        errors[f"{field_prefix}clicks"] = "Lượt click không được âm"
    if conversions < 0:
        errors[f"{field_prefix}conversions"] = "Lượt chuyển đổi không được âm"
    if cost < 0:
        errors[f"{field_prefix}cost"] = "Chi phí không được âm"

    if views == 0 and clicks > 0:
        errors[f"{field_prefix}clicks"] = "Lượt xem bằng 0 thì lượt click phải bằng 0"
    elif views > 0 and clicks > views:
        errors[f"{field_prefix}clicks"] = "Lượt click không thể lớn hơn lượt xem"

    if clicks == 0 and conversions > 0:
        errors[f"{field_prefix}conversions"] = "Lượt click bằng 0 thì lượt chuyển đổi phải bằng 0"
    elif clicks > 0 and conversions > clicks:
        errors[f"{field_prefix}conversions"] = "Lượt chuyển đổi không thể lớn hơn lượt click"

    if errors:
        raise ValidationFailed(fields=errors)


SORT_FIELDS = {
    "metric_date": Metric.metric_date,
    "views": Metric.views,
    "clicks": Metric.clicks,
    "conversions": Metric.conversions,
    "cost": Metric.cost,
    "created_at": Metric.created_at,
    "updated_at": Metric.updated_at,
}


def list_metrics(
    db: Session,
    user: User,
    filters: MetricFilters | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: str | None = None,
) -> Page[MetricOut]:
    filters = filters or MetricFilters()
    if filters.date_from and filters.date_to and filters.date_from > filters.date_to:
        raise ValidationFailed(fields={"date_to": "Ngày kết thúc phải sau hoặc bằng ngày bắt đầu"})

    stmt = select(Metric)
    if filters.campaign_id:
        stmt = stmt.where(Metric.campaign_id == filters.campaign_id)
    channel_id = filters.channel_id
    if channel_id is None and filters.channel_code:
        channel = channel_service.find_by_code(db, filters.channel_code)
        channel_id = channel.id if channel else -1
    if channel_id is not None:
        stmt = stmt.where(Metric.channel_id == channel_id)
    if filters.date_from:
        stmt = stmt.where(Metric.metric_date >= filters.date_from)
    if filters.date_to:
        stmt = stmt.where(Metric.metric_date <= filters.date_to)
    if filters.source:
        stmt = stmt.where(Metric.source == filters.source)

    stmt = apply_sort(stmt, sort, SORT_FIELDS, "-metric_date", Metric.id)
    items, total = paginate(db, stmt, page, page_size)
    return Page[MetricOut](
        items=[metric_out(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def _resolve_target(
    db: Session, campaign_id: int, channel_id: int | None, channel_code: str | None, field_prefix: str = ""
) -> tuple[Campaign, Channel]:
    campaign = campaign_service.find_campaign_for_reference(db, campaign_id, field=f"{field_prefix}campaign_id")
    ch_field = f"{field_prefix}channel_id" if channel_id is not None or not channel_code else f"{field_prefix}channel_code"
    channel = channel_service.resolve_channel(db, channel_id, channel_code, field=ch_field, require_active=False)
    if channel.id not in campaign_service.campaign_channel_ids(campaign):
        raise ValidationFailed(fields={ch_field: f"Kênh {channel.name} không thuộc chiến dịch '{campaign.name}'"})
    return campaign, channel


def upsert_metric(
    db: Session,
    user: User,
    data: MetricIn,
    source: MetricSource = MetricSource.MANUAL,
    import_batch: str | None = None,
) -> MetricOut:
    campaign, channel = _resolve_target(db, data.campaign_id, data.channel_id, data.channel_code)
    validate_metric_counts(data.views, data.clicks, data.conversions, data.cost)

    existing = db.execute(
        select(Metric).where(
            Metric.campaign_id == campaign.id,
            Metric.channel_id == channel.id,
            Metric.metric_date == data.metric_date,
        )
    ).scalar_one_or_none()

    if existing is not None:
        ensure_can_edit(user, existing)
        existing.views = data.views
        existing.clicks = data.clicks
        existing.conversions = data.conversions
        existing.cost = Decimal(data.cost)
        existing.source = source
        existing.entered_by = user.id
        if import_batch:
            existing.import_batch = import_batch
        db.commit()
        db.refresh(existing)
        return metric_out(existing)

    metric = Metric(
        campaign_id=campaign.id,
        channel_id=channel.id,
        metric_date=data.metric_date,
        views=data.views,
        clicks=data.clicks,
        conversions=data.conversions,
        cost=Decimal(data.cost),
        source=source,
        entered_by=user.id,
        import_batch=import_batch,
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric_out(metric)


def update_metric(db: Session, user: User, metric_id: int, data: MetricUpdate) -> MetricOut:
    metric = get_metric_orm(db, metric_id)
    ensure_can_edit(user, metric)

    fields = data.model_dump(exclude_unset=True)
    new_views = fields.get("views", metric.views)
    new_clicks = fields.get("clicks", metric.clicks)
    new_conversions = fields.get("conversions", metric.conversions)
    new_cost = Decimal(fields.get("cost", metric.cost))

    validate_metric_counts(new_views, new_clicks, new_conversions, new_cost)

    metric.views = new_views
    metric.clicks = new_clicks
    metric.conversions = new_conversions
    metric.cost = new_cost
    db.commit()
    db.refresh(metric)
    return metric_out(metric)


def delete_metric(db: Session, user: User, metric_id: int) -> None:
    metric = get_metric_orm(db, metric_id)
    ensure_can_edit(user, metric)
    db.delete(metric)
    db.commit()


# --- Import CSV ---------------------------------------------------------------

CSV_TEMPLATE = """date,campaign_id,campaign_name,channel_code,views,clicks,conversions,cost
2026-10-01,1,,FACEBOOK,1000,50,5,250000
2026-10-01,,Thu Đông 2026,TIKTOK,2000,120,8,400000
"""


def get_csv_template() -> str:
    return CSV_TEMPLATE


def _clean_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def preview_csv_import(
    db: Session, user: User, content: bytes, filename: str | None = None
) -> ImportPreviewOut:
    if len(content) > MAX_CSV_BYTES:
        raise PayloadTooLarge(
            f"Kích thước file vượt quá giới hạn cho phép (tối đa {MAX_CSV_BYTES // (1024 * 1024)}MB)",
            code="FILE_TOO_LARGE",
        )

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception as exc:
            raise ValidationFailed("File CSV không đúng định dạng văn bản UTF-8") from exc

    f = io.StringIO(text)
    reader = csv.reader(f)
    try:
        header_raw = next(reader)
    except StopIteration:
        raise ValidationFailed("File CSV rỗng")

    header = [_clean_header(h) for h in header_raw]
    col_map: dict[str, int] = {}
    for idx, col in enumerate(header):
        if col in ("date", "metric_date", "ngay"):
            col_map["date"] = idx
        elif col in ("campaign_id", "id_chien_dich"):
            col_map["campaign_id"] = idx
        elif col in ("campaign_name", "campaign", "ten_chien_dich"):
            col_map["campaign_name"] = idx
        elif col in ("channel_code", "channel", "kenh", "ma_kenh"):
            col_map["channel_code"] = idx
        elif col in ("views", "luot_xem", "impressions"):
            col_map["views"] = idx
        elif col in ("clicks", "luot_click"):
            col_map["clicks"] = idx
        elif col in ("conversions", "chuyen_doi"):
            col_map["conversions"] = idx
        elif col in ("cost", "chi_phi"):
            col_map["cost"] = idx

    missing = [c for c in ("date", "channel_code", "views", "clicks", "conversions", "cost") if c not in col_map]
    if missing or ("campaign_id" not in col_map and "campaign_name" not in col_map):
        raise ValidationFailed(
            "File CSV thiếu các cột bắt buộc: date, campaign_id (hoặc campaign_name), channel_code, views, clicks, conversions, cost"
        )

    # Preload campaigns and channels to avoid N+1
    campaigns_by_id: dict[int, Campaign] = {c.id: c for c in db.execute(select(Campaign)).scalars()}
    campaigns_by_name: dict[str, Campaign] = {c.name.strip().lower(): c for c in campaigns_by_id.values()}
    channels_by_code: dict[str, Channel] = {
        c.code.upper(): c for c in db.execute(select(Channel)).scalars()
    }

    # Query all existing metric keys to mark `exists` (và biết ai đã nhập để kiểm tra quyền sửa)
    existing_owner: dict[tuple[int, int, date], int | None] = {
        (cid, chid, mdate): entered_by
        for cid, chid, mdate, entered_by in db.execute(
            select(Metric.campaign_id, Metric.channel_id, Metric.metric_date, Metric.entered_by)
        ).all()
    }
    existing_keys = set(existing_owner)

    rows: list[ImportRow] = []
    errors: list[ImportRowError] = []
    total_data_rows = 0

    seen_in_batch: set[tuple[int, int, date]] = set()

    for row_idx, line in enumerate(reader, start=2):
        if not line or not any(field.strip() for field in line):
            continue
        total_data_rows += 1
        if total_data_rows > MAX_CSV_ROWS:
            raise PayloadTooLarge(
                f"Số lượng dòng dữ liệu vượt quá giới hạn cho phép (tối đa {MAX_CSV_ROWS} dòng)",
                code="FILE_TOO_LARGE",
            )

        def get_val(key: str, raw_line: list[str]) -> str:
            idx = col_map.get(key)
            if idx is not None and idx < len(raw_line):
                return raw_line[idx].strip()
            return ""

        date_str = get_val("date", line)
        cid_str = get_val("campaign_id", line)
        cname_str = get_val("campaign_name", line)
        ch_str = get_val("channel_code", line).upper()
        views_str = get_val("views", line)
        clicks_str = get_val("clicks", line)
        conv_str = get_val("conversions", line)
        cost_str = get_val("cost", line)

        # 1. Parse date
        metric_date: date | None = None
        if not date_str:
            errors.append(ImportRowError(row=row_idx, message="Thiếu ngày (date)"))
            continue
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                metric_date = datetime.strptime(date_str, fmt).replace(tzinfo=UTC).date()
                break
            except ValueError:
                pass
        if metric_date is None:
            errors.append(ImportRowError(row=row_idx, message=f"Định dạng ngày không hợp lệ: '{date_str}' (cần YYYY-MM-DD)"))
            continue

        # 2. Campaign
        campaign: Campaign | None = None
        if cid_str:
            try:
                cid = int(cid_str)
                campaign = campaigns_by_id.get(cid)
            except ValueError:
                errors.append(ImportRowError(row=row_idx, message=f"campaign_id phải là số nguyên: '{cid_str}'"))
                continue
        elif cname_str:
            campaign = campaigns_by_name.get(cname_str.strip().lower())

        if campaign is None:
            ref_info = cid_str or cname_str or "trống"
            errors.append(ImportRowError(row=row_idx, message=f"Không tìm thấy chiến dịch: '{ref_info}'"))
            continue

        # 3. Channel
        channel = channels_by_code.get(ch_str)
        if channel is None:
            errors.append(ImportRowError(row=row_idx, message=f"Không tìm thấy kênh: '{ch_str}'"))
            continue

        camp_channel_ids = {link.channel_id for link in campaign.channel_links}
        if channel.id not in camp_channel_ids:
            errors.append(
                ImportRowError(
                    row=row_idx,
                    message=f"Kênh '{channel.name}' không thuộc chiến dịch '{campaign.name}'",
                )
            )
            continue

        # 4. Parse counts & cost
        try:
            views = int(views_str) if views_str else 0
            clicks = int(clicks_str) if clicks_str else 0
            conversions = int(conv_str) if conv_str else 0
            cost_value = float(cost_str) if cost_str else 0.0
            if not math.isfinite(cost_value):
                raise ValueError("cost không hữu hạn")
            cost = int(cost_value)
        except (ValueError, OverflowError):
            errors.append(ImportRowError(row=row_idx, message="Các trường số liệu (views, clicks, conversions, cost) phải là số"))
            continue

        try:
            validate_metric_counts(views, clicks, conversions, cost)
        except ValidationFailed as vf:
            first_msg = next(iter(vf.fields.values())) if vf.fields else "Dữ liệu số không hợp lệ"
            errors.append(ImportRowError(row=row_idx, message=first_msg))
            continue

        # Check duplicate within CSV
        dedup_key = (campaign.id, channel.id, metric_date)
        if dedup_key in seen_in_batch:
            errors.append(
                ImportRowError(
                    row=row_idx,
                    message=f"Bị trùng lặp chiến dịch, kênh và ngày với một dòng trước đó trong file ({metric_date})",
                )
            )
            continue
        # Dòng ghi đè số liệu do người khác nhập: báo ngay ở bước xem trước (commit sẽ bị từ chối 403)
        if dedup_key in existing_owner and not user.is_manager and existing_owner[dedup_key] != user.id:
            errors.append(
                ImportRowError(
                    row=row_idx,
                    message="Trùng với số liệu do người khác nhập — bạn chỉ được cập nhật số liệu của chính mình",
                )
            )
            continue
        seen_in_batch.add(dedup_key)

        is_exists = dedup_key in existing_keys
        rows.append(
            ImportRow(
                row=row_idx,
                metric_date=metric_date,
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                channel_id=channel.id,
                channel_code=channel.code,
                views=views,
                clicks=clicks,
                conversions=conversions,
                cost=cost,
                exists=is_exists,
            )
        )

    inserts = sum(1 for r in rows if not r.exists)
    updates = sum(1 for r in rows if r.exists)
    summary = ImportSummary(
        total=total_data_rows,
        valid=len(rows),
        invalid=len(errors),
        inserts=inserts,
        updates=updates,
    )

    return ImportPreviewOut(rows=rows, errors=errors, summary=summary)


def commit_csv_import(db: Session, user: User, data: ImportCommitIn) -> ImportCommitOut:
    if not data.rows:
        raise ValidationFailed("Danh sách dòng commit rỗng")
    if len(data.rows) > MAX_CSV_ROWS:
        raise PayloadTooLarge(f"Tối đa {MAX_CSV_ROWS} dòng cho mỗi lần import", code="FILE_TOO_LARGE")

    import_batch = f"csv_{uuid.uuid4().hex[:12]}"
    inserted = 0
    updated = 0

    seen: set[tuple[int, int, date]] = set()

    for idx, row in enumerate(data.rows):
        prefix = f"rows.{idx}."
        campaign, channel = _resolve_target(db, row.campaign_id, row.channel_id, row.channel_code, field_prefix=prefix)
        validate_metric_counts(row.views, row.clicks, row.conversions, row.cost, field_prefix=prefix)

        key = (campaign.id, channel.id, row.metric_date)
        if key in seen:
            raise ValidationFailed(fields={f"{prefix}metric_date": f"Dòng trùng lặp (chiến dịch {campaign.id}, kênh {channel.code}, ngày {row.metric_date})"})
        seen.add(key)

        existing = db.execute(
            select(Metric).where(
                Metric.campaign_id == campaign.id,
                Metric.channel_id == channel.id,
                Metric.metric_date == row.metric_date,
            )
        ).scalar_one_or_none()

        if existing is not None:
            ensure_can_edit(user, existing)
            existing.views = row.views
            existing.clicks = row.clicks
            existing.conversions = row.conversions
            existing.cost = Decimal(row.cost)
            existing.source = MetricSource.CSV
            existing.entered_by = user.id
            existing.import_batch = import_batch
            updated += 1
        else:
            new_m = Metric(
                campaign_id=campaign.id,
                channel_id=channel.id,
                metric_date=row.metric_date,
                views=row.views,
                clicks=row.clicks,
                conversions=row.conversions,
                cost=Decimal(row.cost),
                source=MetricSource.CSV,
                entered_by=user.id,
                import_batch=import_batch,
            )
            db.add(new_m)
            inserted += 1

    db.commit()
    return ImportCommitOut(inserted=inserted, updated=updated, import_batch=import_batch)
