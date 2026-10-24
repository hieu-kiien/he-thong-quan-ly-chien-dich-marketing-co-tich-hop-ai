"""Tiện ích khai báo cột dùng chung cho các model."""

from __future__ import annotations

from enum import Enum as PyEnum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Numeric

MONEY = Numeric(14, 0)


def enum_column(enum_cls: type[PyEnum], name: str) -> SAEnum:
    """Enum lưu dạng VARCHAR + CHECK (không dùng native enum để migration đơn giản, chạy cả SQLite)."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )
