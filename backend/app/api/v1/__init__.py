"""Gom tất cả router của API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.brand import router as brand_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.channels import router as channels_router
from app.api.v1.contents import router as contents_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.schedules import router as schedules_router
from app.api.v1.stats import router as stats_router
from app.api.v1.users import router as users_router
from app.assistant.router import router as assistant_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(channels_router)
api_v1_router.include_router(campaigns_router)
api_v1_router.include_router(contents_router)
api_v1_router.include_router(schedules_router)
api_v1_router.include_router(metrics_router)
api_v1_router.include_router(stats_router)
api_v1_router.include_router(brand_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(assistant_router)
