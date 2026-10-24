from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class BrandProfile(TimestampMixin, Base):
    """Hồ sơ thương hiệu — chỉ có một dòng."""

    __tablename__ = "brand_profile"

    brand_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tone_of_voice: Mapped[str] = mapped_column(Text, default="", nullable=False)
    target_audience: Mapped[str] = mapped_column(Text, default="", nullable=False)
    guidelines: Mapped[str] = mapped_column(Text, default="", nullable=False)


class BannedKeyword(TimestampMixin, Base):
    __tablename__ = "banned_keywords"

    keyword: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
