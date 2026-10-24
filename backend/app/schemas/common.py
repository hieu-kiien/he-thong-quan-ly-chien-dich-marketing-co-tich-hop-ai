"""Schema dùng chung: Ref object nhúng (CONTRACT §10.1), kiểu tiền, model input chuẩn."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

MAX_MONEY = 99_999_999_999_999  # Numeric(14,0)


def _to_int_money(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    if isinstance(value, float):
        return int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return value


MoneyOut = Annotated[int, BeforeValidator(_to_int_money)]
MoneyIn = Annotated[int, Field(ge=0, le=MAX_MONEY)]
Count = Annotated[int, Field(ge=0, le=2_000_000_000)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class InputModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


class UserRef(ORMModel):
    id: int
    full_name: str


class ChannelRef(ORMModel):
    id: int
    code: str
    name: str


class CampaignRef(ORMModel):
    id: int
    name: str


class Message(BaseModel):
    message: str
