"""Hồ sơ thương hiệu (1 dòng) và danh sách từ cấm; kiểm tra từ cấm theo quy tắc (không phải AI)."""

from __future__ import annotations

import unicodedata

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import PermissionDenied, ValidationFailed
from app.models import BannedKeyword, BrandProfile, User
from app.schemas.brand import BannedKeywordOut, BrandProfileIn, BrandProfileOut
from app.schemas.content import BannedMatch


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").casefold()


def normalize_keyword(keyword: str) -> str:
    return " ".join(normalize_text(keyword).split())


def _profile_row(db: Session) -> BrandProfile | None:
    return db.execute(select(BrandProfile).order_by(BrandProfile.id).limit(1)).scalar_one_or_none()


def list_banned_keywords(db: Session) -> list[BannedKeyword]:
    return list(db.execute(select(BannedKeyword).order_by(BannedKeyword.keyword)).scalars())


def get_brand_profile(db: Session, user: User | None = None) -> BrandProfileOut:
    row = _profile_row(db)
    keywords = [BannedKeywordOut.model_validate(k) for k in list_banned_keywords(db)]
    if row is None:
        return BrandProfileOut(
            brand_name="", description="", tone_of_voice="", target_audience="", guidelines="",
            banned_keywords=keywords, updated_at=None,
        )
    return BrandProfileOut(
        brand_name=row.brand_name,
        description=row.description,
        tone_of_voice=row.tone_of_voice,
        target_audience=row.target_audience,
        guidelines=row.guidelines,
        banned_keywords=keywords,
        updated_at=row.updated_at,
    )


def update_brand_profile(db: Session, user: User, data: BrandProfileIn) -> BrandProfileOut:
    if not user.is_manager:
        raise PermissionDenied("Chỉ Quản lý marketing được sửa hồ sơ thương hiệu")
    row = _profile_row(db)
    if row is None:
        row = BrandProfile()
        db.add(row)
    row.brand_name = data.brand_name
    row.description = data.description
    row.tone_of_voice = data.tone_of_voice
    row.target_audience = data.target_audience
    row.guidelines = data.guidelines

    if data.banned_keywords is not None:
        seen: dict[str, int] = {}
        cleaned: list[tuple[str, str | None]] = []
        for idx, item in enumerate(data.banned_keywords):
            kw = normalize_keyword(item.keyword)
            if not kw:
                raise ValidationFailed(fields={f"banned_keywords.{idx}.keyword": "Không được để trống"})
            if kw in seen:
                raise ValidationFailed(fields={f"banned_keywords.{idx}.keyword": f"Từ '{kw}' bị lặp"})
            seen[kw] = idx
            cleaned.append((kw, item.note or None))
        db.execute(delete(BannedKeyword))
        db.flush()
        for kw, note in cleaned:
            db.add(BannedKeyword(keyword=kw, note=note))
    db.commit()
    return get_brand_profile(db, user)


def check_banned(db: Session, text: str) -> list[BannedMatch]:
    """Đếm số lần mỗi từ cấm xuất hiện (không phân biệt hoa thường, chuẩn hoá Unicode NFC)."""
    haystack = " ".join(normalize_text(text).split())
    if not haystack:
        return []
    matches: list[BannedMatch] = []
    for kw in list_banned_keywords(db):
        needle = normalize_keyword(kw.keyword)
        if not needle:
            continue
        count = haystack.count(needle)
        if count:
            matches.append(BannedMatch(keyword=kw.keyword, count=count))
    return matches
