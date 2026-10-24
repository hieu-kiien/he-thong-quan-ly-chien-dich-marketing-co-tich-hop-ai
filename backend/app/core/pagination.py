"""Phân trang `?page=&page_size=` và sắp xếp `?sort=field|-field` (CONTRACT §4)."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailed

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def normalize_page(page: int | None, page_size: int | None) -> tuple[int, int]:
    page = page or 1
    page_size = page_size or DEFAULT_PAGE_SIZE
    if page < 1:
        raise ValidationFailed(fields={"page": "Phải lớn hơn hoặc bằng 1"})
    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise ValidationFailed(fields={"page_size": f"Phải trong khoảng 1–{MAX_PAGE_SIZE}"})
    return page, page_size


def count_rows(db: Session, stmt: Select) -> int:
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    return int(db.execute(count_stmt).scalar_one())


def paginate(db: Session, stmt: Select, page: int, page_size: int) -> tuple[list[Any], int]:
    """Trả về (danh sách bản ghi của trang, tổng số). `stmt` đã có order_by."""
    page, page_size = normalize_page(page, page_size)
    total = count_rows(db, stmt)
    rows = db.execute(stmt.limit(page_size).offset((page - 1) * page_size)).unique().scalars().all()
    return list(rows), total


def apply_sort(stmt: Select, sort: str | None, allowed: dict[str, Any], default: str, tiebreak: Any) -> Select:
    """Áp `?sort=field` hoặc `?sort=-field`; chỉ chấp nhận trường trong `allowed`."""
    key = (sort or default).strip()
    desc = key.startswith("-")
    name = key[1:] if desc else key
    column = allowed.get(name)
    if column is None:
        raise ValidationFailed(
            fields={"sort": f"Chỉ sắp xếp theo: {', '.join(sorted(allowed))} (thêm '-' để giảm dần)"}
        )
    order = column.desc() if desc else column.asc()
    return stmt.order_by(order, tiebreak.desc() if desc else tiebreak.asc())
