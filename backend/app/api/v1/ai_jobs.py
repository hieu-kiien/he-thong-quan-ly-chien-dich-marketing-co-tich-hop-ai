"""Hàng đợi AI bất đồng bộ: API công khai + phần chạy lại tác vụ AI.

BỐI CẢNH (số đo, không phải phỏng đoán)
---------------------------------------
Mọi endpoint trong `app/api/v1/ai.py` là hàm `def` ĐỒNG BỘ. Mỗi lượt gọi giữ một
thread của worker suốt thời gian chờ LLM. Trên Render free (512 MB RAM, 0.1 CPU),
`POST /ai/omnichannel` đo được **237 giây**, còn Cloudflare Worker phía trước cắt
ở ~100 giây và trả `error code: 524`. Vài lượt gọi đồng thời là đủ để cạn bộ nhớ và
bóp chết mọi route API thường.

Cách sửa ở đây: client `POST /ai/jobs` nhận HTTP 202 ngay lập tức, rồi `GET
/ai/jobs/{job_id}` thăm dò kết quả. Việc gọi LLM do worker nền thực hiện với số
job chạy đồng thời bị giới hạn cứng (`AI_JOB_CONCURRENCY`, mặc định 2).

Endpoint đồng bộ cũ GIỮ NGUYÊN để không làm hỏng gì trong lúc chuyển dịch.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.api.v1.campaigns import _accessible_workspace_ids, resolve_effective_workspace_id
from app.api.v1.contents import assert_workspace_access
from app.core.database import get_db
from app.core.pagination import Page, PageParams, page_params, paginate_query
from app.core.security import enforce_quota, get_current_user, quota_already_enforced
from app.models.entities import AIJob, Campaign, User, Workspace, WorkspaceMember
from app.schemas.schemas import (
    AIAngleMatrixRequest,
    AIDraftRequest,
    AIIdeaRequest,
    AIPlanRequest,
    AIPrelaunchCriticRequest,
    AISummaryRequest,
    OmnichannelRequest,
)
from app.services.jobs import queue as job_queue
from app.services.jobs.queue import AIJobExecutionError, is_transient_failure
from app.services import quota

logger = logging.getLogger("marketflow.ai_jobs")

router = APIRouter(
    prefix="/ai",
    tags=["Hàng đợi AI bất đồng bộ (Async AI Jobs)"],
)

# Model request của endpoint đồng bộ tương ứng. Đây là danh sách DUY NHẤT
# ánh xạ `kind` -> payload, để không thể lệch với `app/api/v1/ai.py`.
_KIND_REQUEST_MODELS = {
    job_queue.KIND_IDEAS: AIIdeaRequest,
    job_queue.KIND_DRAFT: AIDraftRequest,
    job_queue.KIND_SUMMARY: AISummaryRequest,
    job_queue.KIND_OMNICHANNEL: OmnichannelRequest,
    job_queue.KIND_PLAN: AIPlanRequest,
    job_queue.KIND_ANGLE_MATRIX: AIAngleMatrixRequest,
    job_queue.KIND_PRELAUNCH_CRITIC: AIPrelaunchCriticRequest,
}

# Khoá hạn mứng giống hệt endpoint đồng bộ tương ứng, để một lượt gọi AI được tính
# đúng một lần dù nó đi đường đồng bộ hay bất đồng bộ.
_KIND_QUOTA_PREFIX = {
    job_queue.KIND_IDEAS: "ai:ideas",
    job_queue.KIND_DRAFT: "ai:draft",
    job_queue.KIND_SUMMARY: "ai:summary",
    job_queue.KIND_OMNICHANNEL: "ai:omnichannel",
    job_queue.KIND_PLAN: "ai:plan",
    job_queue.KIND_ANGLE_MATRIX: "ai:angle_matrix",
    job_queue.KIND_PRELAUNCH_CRITIC: "ai:prelaunch_critic",
}

# Endpoint đồng bộ sẽ được worker gọi lại. Tên hàm được tra cứu động (import trễ)
# để tránh vòng import: app.api.v1.ai -> app.services.ai.ai_service, còn module này
# nằm cạnh nó trong cùng tầng API.
_KIND_SYNC_ENDPOINT = {
    job_queue.KIND_IDEAS: "generate_ideas",
    job_queue.KIND_DRAFT: "generate_draft",
    job_queue.KIND_SUMMARY: "generate_summary",
    job_queue.KIND_OMNICHANNEL: "generate_omnichannel",
    job_queue.KIND_PLAN: "generate_plan",
    job_queue.KIND_ANGLE_MATRIX: "generate_angle_matrix",
    job_queue.KIND_PRELAUNCH_CRITIC: "evaluate_prelaunch_critic",
}

# HTTP status nào là lỗi TẠM THỜI (đáng thử lại) khi endpoint đồng bộ ném ra.
_TRANSIENT_HTTP_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})

_HTTP_422_UNPROCESSABLE = 422


# ===========================================================================
# Schema
# ===========================================================================
class AIJobCreateRequest(BaseModel):
    """Thân request của `POST /ai/jobs`.

    Nhận ĐÚNG các field mà endpoint đồng bộ tương ứng nhận, cộng thêm `kind` và
    `idempotency_key`. Field nào không gửi thì bỏ qua (không gửi `null`), nên mặc
    định của endpoint đồng bộ vẫn có hiệu lực y hệt.
    """

    kind: str = Field(..., description="Loại tác vụ: ideas | draft | summary | omnichannel | plan | angle_matrix | prelaunch_critic")
    idempotency_key: Optional[str] = Field(
        None,
        max_length=200,
        description=(
            "Khoá chống gọi trùng. Gửi lại cùng khoá + cùng payload thì nhận đúng "
            "job cũ, KHÔNG tạo thêm lượt gọi AI nào."
        ),
    )

    # --- ideas (AIIdeaRequest) ---
    custom_topic: Optional[str] = None
    custom_product: Optional[str] = None
    custom_usp: Optional[str] = None
    channel_code: Optional[str] = None
    tone: Optional[str] = None

    # --- draft (AIDraftRequest) ---
    selected_idea: Optional[str] = Field(
        None, description="Bắt buộc với kind=draft (ý tưởng đã chọn để viết bản nháp)"
    )

    # --- omnichannel / angle_matrix / prelaunch_critic ---
    brief: Optional[str] = Field(
        None, description="Bắt buộc với kind=omnichannel (bản brief yêu cầu chiến dịch)"
    )
    target_audience: Optional[str] = None
    channels: Optional[List[str]] = None
    brand_kit_id: Optional[int] = None
    product_name: Optional[str] = None
    product_usp: Optional[str] = None
    funnel_stage: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    cta: Optional[str] = None

    # --- chung ---
    campaign_id: Optional[int] = Field(
        None, description="ID chiến dịch (bắt buộc với kind=summary và kind=plan)"
    )
    prompt_version: Optional[str] = None
    chain_id: Optional[int] = Field(
        None,
        description=(
            "Chuỗi fallback (AIModelChain) sẽ dùng cho lượt gọi này; bỏ trống "
            "thì dùng chuỗi mặc định của workspace/user nếu có."
        ),
    )

    def payload_for_queue(self) -> Dict[str, Any]:
        """Trả về payload đã chuẩn hoá để lưu vào hàng đợi (bỏ mọi field None)."""
        return job_queue.normalize_payload(self.model_dump())


class AIJobAcceptedResponse(BaseModel):
    job_id: int
    status: str
    kind: str
    deduplicated: bool = Field(
        False,
        description=(
            "True = idempotency_key đã tồn tại nên đây là job cũ được trả lại; "
            "không có lượt gọi AI nào mới được tạo."
        ),
    )
    poll_url: str


class AIJobSummaryResponse(BaseModel):
    job_id: int
    kind: str
    status: str
    attempts: int
    max_attempts: int
    campaign_id: Optional[int] = None
    queued_at: Optional[str] = None
    available_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    error: Optional[str] = None


class AIJobResponse(AIJobSummaryResponse):
    result: Optional[Dict[str, Any]] = Field(
        None,
        description="Kết quả AI khi job đã xong. Cùng cấu trúc với endpoint đồng bộ tương ứng.",
    )


AIJobListResponse = Page[AIJobSummaryResponse]


# ===========================================================================
# Phân quyền
# ===========================================================================
def assert_ai_job_access(job: AIJob, user: User, db: Session) -> None:
    """Bắt buộc ranh giới tenant cho một job AI."""
    if job.workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không xác định được không gian làm việc của tài nguyên. Từ chối truy cập.",
        )
    assert_workspace_access(
        job.workspace_id,
        user,
        db,
        denied_detail="Not authorized to access AI jobs in this workspace",
    )


def _accessible_job_workspace_ids(user: User, db: Session) -> List[int]:
    return _accessible_workspace_ids(user, db)


def resolve_job_workspace(
    db: Session,
    user: User,
    explicit_workspace_id: Optional[int] = None,
    header_workspace_id: Optional[str] = None,
    campaign_id: Optional[int] = None,
) -> int:
    """Chốt tenant cho job AI, theo thứ tự rõ ràng."""
    explicit = resolve_effective_workspace_id(db, user, explicit_workspace_id, header_workspace_id)
    if explicit is not None:
        assert_workspace_access(
            explicit,
            user,
            db,
            denied_detail="Not authorized to enqueue AI jobs in this workspace",
        )
        return int(explicit)

    if campaign_id is not None:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chiến dịch không tồn tại",
            )
        if campaign.workspace_id is not None:
            assert_workspace_access(
                campaign.workspace_id,
                user,
                db,
                denied_detail="Not authorized to enqueue AI jobs for this campaign",
            )
            return int(campaign.workspace_id)

    accessible = _accessible_workspace_ids(user, db)
    if len(accessible) == 1:
        return int(accessible[0])

    if not accessible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Bạn chưa thuộc không gian làm việc nào nên không thể tạo job AI. "
                "Hãy tạo workspace trước, hoặc truyền X-Workspace-Id."
            ),
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            "Bạn thuộc nhiều không gian làm việc nên không thể đoán job AI thuộc tenant nào. "
            "Hãy truyền header X-Workspace-Id (hoặc tham số workspace_id) để chỉ định."
        ),
    )


def _validate_job_payload(kind: str, payload: Dict[str, Any]):
    """Kiểm tra payload ngay lúc enqueue bằng CHÍNH model của endpoint đồng bộ."""
    model = _KIND_REQUEST_MODELS.get(kind)
    if model is None:
        raise HTTPException(
            status_code=_HTTP_422_UNPROCESSABLE,
            detail=f"kind không hợp lệ. Chỉ nhận: {', '.join(job_queue.JOB_KINDS)}.",
        )
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=_HTTP_422_UNPROCESSABLE,
            detail=f"Payload không hợp lệ với kind='{kind}': {exc.errors()}",
        )


# ===========================================================================
# API
# ===========================================================================
@router.post("/jobs", response_model=AIJobAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def enqueue_ai_job(
    req: AIJobCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    workspace_id: Optional[int] = Query(None, alias="workspace_id"),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
):
    """Đẩy một tác vụ AI vào hàng đợi. Trả 202 ngay, không chờ LLM."""
    kind = (req.kind or "").strip().lower()
    payload = req.payload_for_queue()
    payload.pop("kind", None)
    payload.pop("idempotency_key", None)

    _validate_job_payload(kind, payload)

    target_ws_id = resolve_job_workspace(db, current_user, workspace_id, x_workspace_id, payload.get("campaign_id"))

    existing = job_queue.find_by_idempotency_key(db, current_user.id, req.idempotency_key)
    if existing is not None:
        return _accepted_for_existing(db, existing, kind, payload, current_user)

    enforce_quota(f"{_KIND_QUOTA_PREFIX[kind]}:user={current_user.id}")

    quota.enforce(
        db,
        quota.LIMIT_AI_JOBS_PER_DAY,
        user=current_user,
        workspace_id=target_ws_id,
    )

    job, deduplicated = job_queue.enqueue_job(
        db,
        workspace_id=target_ws_id,
        user_id=current_user.id,
        kind=kind,
        payload=payload,
        campaign_id=payload.get("campaign_id"),
        idempotency_key=req.idempotency_key,
    )

    if deduplicated:
        return _accepted_for_existing(db, job, kind, payload, current_user)

    return AIJobAcceptedResponse(
        job_id=job.id,
        status=job.status,
        kind=job.kind,
        deduplicated=False,
        poll_url=f"/api/v1/ai/jobs/{job.id}",
    )


def _accepted_for_existing(
    db: Session,
    job: AIJob,
    kind: str,
    payload: Dict[str, Any],
    user: User,
) -> AIJobAcceptedResponse:
    if job.payload_hash != job_queue.payload_hash(kind, payload):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "idempotency_key đã được dùng cho một payload KHÁC. "
                "Hãy dùng khoá khác, hoặc lấy lại kết quả của job cũ."
            ),
        )
    assert_ai_job_access(job, user, db)
    return AIJobAcceptedResponse(
        job_id=job.id,
        status=job.status,
        kind=job.kind,
        deduplicated=True,
        poll_url=f"/api/v1/ai/jobs/{job.id}",
    )


@router.get("/jobs", response_model=AIJobListResponse)
def list_ai_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    kind: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pagination: PageParams = Depends(page_params),
    workspace_id: Optional[int] = Query(None, alias="workspace_id"),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
):
    query = db.query(AIJob)

    if current_user.role == "ADMIN":
        target_ws = resolve_effective_workspace_id(db, current_user, workspace_id, x_workspace_id)
        if target_ws is not None:
            query = query.filter(AIJob.workspace_id == target_ws)
    else:
        ws_ids = _accessible_job_workspace_ids(current_user, db)
        query = query.filter(AIJob.workspace_id.in_(ws_ids)) if ws_ids else query.filter(AIJob.id.is_(None))
        target_ws = resolve_effective_workspace_id(db, current_user, workspace_id, x_workspace_id)
        if target_ws is not None:
            assert_workspace_access(
                target_ws,
                current_user,
                db,
                denied_detail="Not authorized to list AI jobs of this workspace",
            )
            query = query.filter(AIJob.workspace_id == target_ws)

    query = query.filter(AIJob.workspace_id.isnot(None))

    if status_filter:
        normalized = status_filter.strip().lower()
        if normalized not in (
            job_queue.JOB_QUEUED, job_queue.JOB_RUNNING, job_queue.JOB_SUCCEEDED,
            job_queue.JOB_FAILED, job_queue.JOB_CANCELLED,
        ):
            raise HTTPException(
                status_code=_HTTP_422_UNPROCESSABLE,
                detail="status không hợp lệ. Chỉ nhận: queued, running, succeeded, failed, cancelled.",
            )
        query = query.filter(AIJob.status == normalized)

    if kind:
        normalized_kind = kind.strip().lower()
        if normalized_kind not in job_queue.JOB_KINDS:
            raise HTTPException(
                status_code=_HTTP_422_UNPROCESSABLE,
                detail=f"kind không hợp lệ. Chỉ nhận: {', '.join(job_queue.JOB_KINDS)}.",
            )
        query = query.filter(AIJob.kind == normalized_kind)

    return paginate_query(
        query.order_by(AIJob.created_at.desc(), AIJob.id.desc()),
        pagination,
        serializer=_to_summary,
    )


@router.get("/jobs/{job_id}", response_model=AIJobResponse)
def get_ai_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job AI không tồn tại")
    assert_ai_job_access(job, current_user, db)

    payload = _to_summary(job).model_dump()
    return AIJobResponse(
        **payload,
        result=_decode_json(job.result_json),
    )


@router.post("/jobs/{job_id}/cancel", response_model=AIJobAcceptedResponse)
def cancel_ai_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job AI không tồn tại")
    assert_ai_job_access(job, current_user, db)

    if job.status == job_queue.JOB_CANCELLED:
        return AIJobAcceptedResponse(
            job_id=job.id, status=job.status, kind=job.kind, deduplicated=True,
            poll_url=f"/api/v1/ai/jobs/{job.id}",
        )

    cancelled = job_queue.cancel_queued_job(db, job.id)
    if not cancelled:
        job = db.query(AIJob).filter(AIJob.id == job_id).first()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Không thể huỷ job ở trạng thái '{job.status}'. "
                "Chỉ huỷ được job đang chờ (queued)."
            ),
        )

    return AIJobAcceptedResponse(
        job_id=job.id,
        status=job_queue.JOB_CANCELLED,
        kind=job.kind,
        deduplicated=False,
        poll_url=f"/api/v1/ai/jobs/{job.id}",
    )


# ===========================================================================
# Chạy lại tác vụ AI (worker gọi vào đây)
# ===========================================================================
def execute_ai_job(db: Session, job: AIJob) -> Dict[str, Any]:
    """Chạy một job AI và trả về kết quả dạng dict; ném `AIJobExecutionError` khi lỗi."""
    from app.api.v1 import ai as ai_endpoints

    user = db.query(User).filter(User.id == job.user_id).first()
    if user is None:
        raise AIJobExecutionError(
            f"Không tìm thấy người dùng id={job.user_id} cho job AI.", transient=False
        )
    if user.status != "ACTIVE":
        raise AIJobExecutionError(
            f"Tài khoản {user.email} không còn ACTIVE nên không thể chạy job AI.",
            transient=False,
        )

    try:
        payload = json.loads(job.payload_json or "{}")
    except (TypeError, ValueError) as exc:
        raise AIJobExecutionError(f"Payload job AI hỏng: {exc}", transient=False)

    model = _KIND_REQUEST_MODELS.get(job.kind)
    if model is None:
        raise AIJobExecutionError(f"kind AI job không hợp lệ: {job.kind!r}", transient=False)
    try:
        request = model.model_validate(payload)
    except ValidationError as exc:
        raise AIJobExecutionError(
            f"Payload không hợp lệ với kind='{job.kind}': {exc.errors()}", transient=False
        )

    endpoint = getattr(ai_endpoints, _KIND_SYNC_ENDPOINT[job.kind], None)
    if endpoint is None:
        raise AIJobExecutionError(
            f"Không tìm thấy endpoint đồng bộ cho kind='{job.kind}'.", transient=False
        )

    try:
        with quota_already_enforced():
            response = endpoint(request, user, db)
    except HTTPException as exc:
        raise AIJobExecutionError(
            f"Endpoint AI trả HTTP {exc.status_code}: {exc.detail}",
            transient=exc.status_code in _TRANSIENT_HTTP_STATUSES,
        ) from None
    except Exception as exc:  # noqa: BLE001
        raise AIJobExecutionError(
            f"{type(exc).__name__}: {exc}",
            transient=is_transient_failure(exc),
        ) from None

    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json")
    return dict(response)


# ===========================================================================
# Helper
# ===========================================================================
def _decode_json(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("Kết quả job AI không parse được JSON; trả null thay vì 500.")
        return None
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _iso(value) -> Optional[str]:
    if value is None:
        return None
    try:
        return value.isoformat()
    except AttributeError:
        return str(value)


def _to_summary(job: AIJob) -> AIJobSummaryResponse:
    return AIJobSummaryResponse(
        job_id=job.id,
        kind=job.kind,
        status=job.status,
        attempts=int(job.attempts or 0),
        max_attempts=int(job.max_attempts or 1),
        campaign_id=job.campaign_id,
        queued_at=_iso(job.queued_at),
        available_at=_iso(job.available_at),
        started_at=_iso(job.started_at),
        finished_at=_iso(job.finished_at),
        cancelled_at=_iso(job.cancelled_at),
        error=job.error_message,
    )
