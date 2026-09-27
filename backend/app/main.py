import sys
import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("marketflow.main")

from app.core.config import settings
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

app = FastAPI(
    title=settings.APP_NAME,
    description="Hệ thống quản lý chiến dịch marketing có tích hợp AI (AIA331 - Đề tài 80300)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Timing Middleware ghi nhận độ trễ xử lý API và chèn header X-Process-Time
class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.6f}"
        return response

app.add_middleware(TimingMiddleware)

# CORS Middleware hỗ trợ kết nối từ Frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
)

from fastapi.exception_handlers import request_validation_exception_handler

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if "/reject" in str(request.url.path):
        return JSONResponse(
            status_code=400,
            content={"detail": "Vui lòng cung cấp lý do từ chối cụ thể (tối thiểu 3 ký tự)"}
        )
    return await request_validation_exception_handler(request, exc)

# Đăng ký các Router nghiệp vụ
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(campaigns_router, prefix=settings.API_V1_PREFIX)
app.include_router(contents_router, prefix=settings.API_V1_PREFIX)
app.include_router(metrics_router, prefix=settings.API_V1_PREFIX)
app.include_router(ai_router, prefix=settings.API_V1_PREFIX)
app.include_router(channels_router, prefix=settings.API_V1_PREFIX)
app.include_router(schedules_router, prefix=settings.API_V1_PREFIX)
app.include_router(workspaces_router, prefix=settings.API_V1_PREFIX)
app.include_router(brand_kit_router, prefix=settings.API_V1_PREFIX)
app.include_router(settings_router, prefix=settings.API_V1_PREFIX)


from app.core.database import engine, init_db, DatabaseMigrationError

@app.on_event("startup")
def on_startup():
    try:
        init_db(engine)
    except DatabaseMigrationError as e:
        logger.critical(f"Critical database migration error during startup: {e}", exc_info=True)
        sys.exit(1)


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

