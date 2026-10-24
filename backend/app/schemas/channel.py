from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import InputModel, ORMModel


class ChannelOut(ORMModel):
    id: int
    code: str
    name: str
    format_rules: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ChannelCreate(InputModel):
    code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    format_rules: str = Field(default="", max_length=5000)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def _code(cls, v: str) -> str:
        v = v.upper()
        if not v.replace("_", "").isalnum() or not v[0].isalpha() or not v.isascii():
            raise ValueError("Mã kênh chỉ gồm chữ in hoa không dấu, số và dấu gạch dưới, bắt đầu bằng chữ")
        return v


class ChannelUpdate(InputModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    format_rules: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None
