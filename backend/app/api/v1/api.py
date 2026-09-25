from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.contents import router as contents_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.ai import router as ai_router
from app.api.v1.channels import router as channels_router
from app.api.v1.schedules import router as schedules_router
from app.api.v1.workspaces import router as workspaces_router
from app.api.v1.brand_kit import router as brand_kit_router
from app.api.v1.settings import router as settings_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(campaigns_router)
api_router.include_router(contents_router)
api_router.include_router(metrics_router)
api_router.include_router(ai_router)
api_router.include_router(channels_router)
api_router.include_router(schedules_router)
api_router.include_router(workspaces_router)
api_router.include_router(brand_kit_router)
api_router.include_router(settings_router)

