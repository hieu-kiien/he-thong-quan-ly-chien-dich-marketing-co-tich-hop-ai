from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import InputModel, ORMModel


class BannedKeywordOut(ORMModel):
    id: int
    keyword: str
    note: str | None


class BannedKeywordIn(InputModel):
    keyword: str = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=255)


class BrandProfileOut(ORMModel):
    brand_name: str
    description: str
    tone_of_voice: str
    target_audience: str
    guidelines: str
    banned_keywords: list[BannedKeywordOut]
    updated_at: datetime | None = None


class BrandProfileIn(InputModel):
    brand_name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)
    tone_of_voice: str = Field(default="", max_length=5000)
    target_audience: str = Field(default="", max_length=5000)
    guidelines: str = Field(default="", max_length=10000)
    banned_keywords: list[BannedKeywordIn] | None = Field(default=None, max_length=500)
