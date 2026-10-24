"""Tiện ích thời gian: múi giờ làm việc của team là Asia/Ho_Chi_Minh (UTC+7, không có DST)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta, timezone

VN_TZ = timezone(timedelta(hours=7), name="Asia/Ho_Chi_Minh")


def now_utc() -> datetime:
    return datetime.now(UTC)


def today_vn() -> date:
    return datetime.now(VN_TZ).date()


def to_utc(value: datetime) -> datetime:
    """Chuẩn hoá datetime về UTC; giá trị không có múi giờ được hiểu là giờ Việt Nam."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=VN_TZ)
    return value.astimezone(UTC)


def local_date(value: datetime) -> date:
    return to_utc(value).astimezone(VN_TZ).date()


def vn_day_start_utc(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=VN_TZ).astimezone(UTC)


def vn_day_end_utc(day: date) -> datetime:
    """Thời điểm bắt đầu của ngày kế tiếp (dùng với so sánh `<`)."""
    return vn_day_start_utc(day + timedelta(days=1))
