from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.auth import router as auth_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.contents import router as contents_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.ai import router as ai_router
from app.api.v1.channels import router as channels_router
from app.api.v1.schedules import router as schedules_router

app = FastAPI(
    title=settings.APP_NAME,
    description="Hệ thống quản lý chiến dịch marketing có tích hợp AI (AIA331 - Đề tài 80300)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware hỗ trợ kết nối từ Frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các Router nghiệp vụ
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(campaigns_router, prefix=settings.API_V1_PREFIX)
app.include_router(contents_router, prefix=settings.API_V1_PREFIX)
app.include_router(metrics_router, prefix=settings.API_V1_PREFIX)
app.include_router(ai_router, prefix=settings.API_V1_PREFIX)
app.include_router(channels_router, prefix=settings.API_V1_PREFIX)
app.include_router(schedules_router, prefix=settings.API_V1_PREFIX)

@app.get("/")
def root():
    return {
        "status": "online",
        "app_name": settings.APP_NAME,
        "docs_url": "/docs",
        "api_v1": settings.API_V1_PREFIX
    }

@app.get("/health")
@app.get(f"{settings.API_V1_PREFIX}/health")
def health_check():
    return {"status": "healthy"}

