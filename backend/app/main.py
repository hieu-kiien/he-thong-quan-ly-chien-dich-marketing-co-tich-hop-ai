"""FastAPI application entrypoint for MarketFlow v2."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import api_v1_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.errors import register_exception_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate production settings fail-fast
    settings.validate_for_runtime()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers (CONTRACT §4)
register_exception_handlers(app)

# Include API v1 routes
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Hệ thống"])
async def health_check():
    # 1. Check Database
    db_status = "error"
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_status = "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health check DB error: %s", exc)
        db_status = "error"

    # 2. Check AI Runner
    ai_status = "unknown"
    if settings.AI_RUNNER_URL:
        try:
            url = f"{settings.AI_RUNNER_URL.rstrip('/')}/health"
            headers = {}
            if settings.AI_RUNNER_TOKEN:
                headers["X-Runner-Token"] = settings.AI_RUNNER_TOKEN
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    ai_status = "ok"
                else:
                    ai_status = "error"
        except Exception:  # noqa: BLE001
            ai_status = "error"

    overall_status = "ok" if db_status == "ok" else "error"
    if db_status == "ok" and ai_status == "error":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "db": db_status,
        "ai_runner": ai_status,
    }
