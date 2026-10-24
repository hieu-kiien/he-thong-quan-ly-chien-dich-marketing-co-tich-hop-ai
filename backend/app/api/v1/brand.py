"""Router hồ sơ thương hiệu & từ cấm."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.security import CurrentUser, DbSession
from app.schemas.brand import BrandProfileIn, BrandProfileOut
from app.services import brand_service

router = APIRouter(tags=["Hồ sơ thương hiệu"])


@router.get("/brand-profile", response_model=BrandProfileOut)
def get_brand_profile(user: CurrentUser, db: DbSession) -> BrandProfileOut:
    return brand_service.get_brand_profile(db, user)


@router.put("/brand-profile", response_model=BrandProfileOut)
def update_brand_profile(data: BrandProfileIn, user: CurrentUser, db: DbSession) -> BrandProfileOut:
    return brand_service.update_brand_profile(db, user, data)
