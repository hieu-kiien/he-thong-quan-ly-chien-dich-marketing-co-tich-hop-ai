"""Router số liệu hiệu quả (metrics) & import CSV."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, File, Query, Response, UploadFile, status

from app.core.pagination import Page
from app.core.security import CurrentUser, DbSession
from app.models.enums import MetricSource
from app.schemas.common import Message
from app.schemas.metric import (
    ImportCommitIn,
    ImportCommitOut,
    ImportPreviewOut,
    MetricFilters,
    MetricIn,
    MetricOut,
    MetricUpdate,
)
from app.services import metric_service

router = APIRouter(prefix="/metrics", tags=["Số liệu hiệu quả"])


@router.get("", response_model=Page[MetricOut])
def list_metrics(
    user: CurrentUser,
    db: DbSession,
    campaign_id: int | None = None,
    channel_id: int | None = None,
    channel_code: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    source: MetricSource | None = None,
    sort: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[MetricOut]:
    filters = MetricFilters(
        campaign_id=campaign_id,
        channel_id=channel_id,
        channel_code=channel_code,
        date_from=date_from,
        date_to=date_to,
        source=source,
    )
    return metric_service.list_metrics(db, user, filters, page=page, page_size=page_size, sort=sort)


@router.post("", response_model=MetricOut, status_code=status.HTTP_201_CREATED)
def upsert_metric(data: MetricIn, user: CurrentUser, db: DbSession) -> MetricOut:
    return metric_service.upsert_metric(db, user, data)


@router.get("/import/template")
def get_import_template() -> Response:
    content = metric_service.get_csv_template()
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="marketflow_metrics_template.csv"'},
    )


@router.post("/import/preview", response_model=ImportPreviewOut)
async def preview_csv_import(
    user: CurrentUser,
    db: DbSession,
    file: Annotated[UploadFile, File(...)],
) -> ImportPreviewOut:
    content = await file.read()
    return metric_service.preview_csv_import(db, user, content, file.filename)


@router.post("/import/commit", response_model=ImportCommitOut)
def commit_csv_import(
    data: ImportCommitIn,
    user: CurrentUser,
    db: DbSession,
) -> ImportCommitOut:
    return metric_service.commit_csv_import(db, user, data)


@router.patch("/{metric_id}", response_model=MetricOut)
def update_metric(metric_id: int, data: MetricUpdate, user: CurrentUser, db: DbSession) -> MetricOut:
    return metric_service.update_metric(db, user, metric_id, data)


@router.delete("/{metric_id}", response_model=Message)
def delete_metric(metric_id: int, user: CurrentUser, db: DbSession) -> Message:
    metric_service.delete_metric(db, user, metric_id)
    return Message(message="Đã xoá bản ghi số liệu thành công")
