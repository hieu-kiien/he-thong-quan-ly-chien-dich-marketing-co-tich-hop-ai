"""Hàm tiện ích dùng chung của service layer."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, TypeVar

from sqlalchemy.orm import Session

from app.core.errors import NotFound

M = TypeVar("M")


def get_or_404(db: Session, model: type[M], obj_id: int, message: str) -> M:
    obj = db.get(model, obj_id)
    if obj is None:
        raise NotFound(message)
    return obj


def to_number(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def ratio(numerator: Any, denominator: Any, digits: int = 4) -> float | None:
    """Tỉ lệ (phân số); mẫu số 0 → None (UI hiện "—")."""
    den = to_number(denominator)
    if den == 0:
        return None
    return round(to_number(numerator) / den, digits)


def money_ratio(numerator: Any, denominator: Any, multiplier: float = 1.0) -> float | None:
    """Đơn giá VND (cpc, cpa, cpm) làm tròn 2 chữ số; mẫu số 0 → None."""
    den = to_number(denominator)
    if den == 0:
        return None
    return round(to_number(numerator) / den * multiplier, 2)


def percent(numerator: Any, denominator: Any) -> float | None:
    """Phần trăm (45.2); mẫu số 0 → None."""
    den = to_number(denominator)
    if den == 0:
        return None
    return round(to_number(numerator) / den * 100, 1)


def compute_rates(views: Any, clicks: Any, conversions: Any, cost: Any) -> dict[str, float | None]:
    """Công thức CONTRACT §4: ctr=clicks/views, cvr=conversions/clicks, cpc=cost/clicks,
    cpa=cost/conversions, cpm=cost/views*1000."""
    return {
        "ctr": ratio(clicks, views),
        "cvr": ratio(conversions, clicks),
        "cpc": money_ratio(cost, clicks),
        "cpa": money_ratio(cost, conversions),
        "cpm": money_ratio(cost, views, 1000),
    }


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def like_pattern(value: str) -> str:
    return f"%{escape_like(value.strip())}%"
