"""Hàng đợi công việc AI bất đồng bộ — lưu trong chính CSDL, KHÔNG có broker ngoài.

VÌ SAO KHÔNG CELERY / REDIS / RQ / DRAMATIQ / ARQ
------------------------------------------------
Deployment thật của hệ thống là Render free: 512 MB RAM, 0.1 CPU. Một tiến trình
broker riêng (Redis) là chi phí RAM vĩnh viễn trên nền tảng không dư dả đó, và
`celery -A app worker` kéo theo cả bộ prefork đa tiến trình — mỗi tiến trình
Python ~40-60 MB. Ở 512 MB chỉ cần hai tiến trình là đã cạn. Vì vậy hàng đợi nằm
ngay trong bảng `ai_jobs` mà `Base.metadata.create_all` đã tạo, và tiến trình web
tự thực thi job bằng một vòng lặp nền giới hạn số job chạy đồng thời.

NHỰT ĐIỂM CHÍNH: nhiều tiến trình / nhiều replica cùng dùng chung hàng đợi mà
không chạy trùng. Cơ chế là `SELECT ... FOR UPDATE SKIP LOCKED` (`claim_next_job`):
trên Postgres, tiến trình thứ hai không chờ hàng đang bị khoá mà nhảy sang hàng
kế tiếp. Trên SQLite (dev/test) câu lệnh này bị dialect bỏ qua, nên tính đúng đắn
được bảo đảm thêm bằng một `UPDATE` có điều kiện `status='queued'`: chỉ worker đọc
được `rowcount == 1` mới được quyền chạy job. Đây cũng là tiền lệ đã có trong dự
án — `process_due_schedules` trong app/services/scheduler/worker.py nắm lease
bằng đúng cách này.

NHỚ: Python KHÔNG huỷ được thread đang chạy. `sweep_expired_jobs` đánh `failed`
mọi job quá `AI_JOB_TIMEOUT_SECONDS` và buông slot, nhưng thread kẹt vẫn có thể
còn sống tới khi lời gọi HTTP của provider tự hết giờ (`AI_TIMEOUT_SECONDS`). Kết
quả trả về sau thời điểm đó bị loại (mọi cập nhật đều có điều kiện `status='running'`),
và trần số thread sống được chặn cứng ở `job_worker` để một loạt job kẹt không
làm số thread nhân lên vô hạn.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.entities import AIJob

logger = logging.getLogger("marketflow.ai_jobs")

# ---------------------------------------------------------------------------
# Hằng số trạng thái / loại job.
#
# Dùng hằng số (không dùng chuỗi rời) vì trạng thái được ghi bởi worker, đọc bởi API
# và kiểm bởi CHECK constraint trong entities.py. Ba nơi phải luôn khớp nhau.
# ---------------------------------------------------------------------------
JOB_QUEUED = "queued"
JOB_RUNNING = "running"
JOB_SUCCEEDED = "succeeded"
JOB_FAILED = "failed"
JOB_CANCELLED = "cancelled"

JOB_TERMINAL_STATUSES = (JOB_SUCCEEDED, JOB_FAILED, JOB_CANCELLED)

KIND_IDEAS = "ideas"
KIND_DRAFT = "draft"
KIND_SUMMARY = "summary"
KIND_OMNICHANNEL = "omnichannel"

JOB_KINDS = (KIND_IDEAS, KIND_DRAFT, KIND_SUMMARY, KIND_OMNICHANNEL)

# Lý do thất bại dùng chung cho cả API lẫn test, để client đổi chuỗi hiển thị
# không bị lệch với những gì worker thực sự ghi.
FAILURE_TIMEOUT = "TIMEOUT"
FAILURE_CANCELLED = "CANCELLED"

# Số ứng viên job được quét mỗi lần nhặt. Nhỏ có chủ đích: hàng đợi dồn hàng trăm
# job vẫn phải cho worker lấy được việc ngay, và mỗi ứng viên bị khoá bởi tiến
# trình khác chỉ tốn một vòng `UPDATE` rẻ.
_CLAIM_CANDIDATE_LIMIT = 5


class AIJobExecutionError(RuntimeError):
    """Lỗi khi chạy job, kèm cờ cho biết có đáng thử lại hay không.

    `transient=True` nghĩa là lỗi tạm thời (mạng, timeout, 429, 5xx của provider)
    nên đáng thử lại với backoff luỹ tiến. `transient=False` là lỗi vĩnh viễn
    (payload sai, mất quyền truy cập, khoá sai) — thử lại chỉ tốn tiền gọi LLM.
    """

    def __init__(self, message: str, transient: bool = False):
        super().__init__(message)
        self.transient = bool(transient)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Gắn UTC cho datetime naive đọc ra từ CSDL.

    Cột `DateTime` trong entities.py không khai báo timezone, nên SQLite trả về
    datetime NAIVE theo giờ UTC. So sánh trực tiếp với datetime có tz sẽ ném
    TypeError — mọi phép so sánh trong module này đều đi qua đây.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _truncate(message: Optional[str], limit: int = 2000) -> str:
    """Cắt thông điệp lỗi để không phình cột `error_message` vô hạn."""
    if not message:
        return ""
    text = str(message)
    return text if len(text) <= limit else text[:limit] + "…"


# ---------------------------------------------------------------------------
# Chuẩn hoá payload + băm
# ---------------------------------------------------------------------------
def normalize_payload(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Bỏ mọi field có giá trị None khỏi payload.

    Cần thiết vì hai request giống nhau về ý nghĩa có thể khác nhau về hình thức:
    client gửi `{"tone": null}` và client không gửi `tone` đều phải sinh ra cùng
    một job (và cùng một `payload_hash`) — nếu không, một double-click kèm
    payload hơi khác sẽ lách qua chống trùng và tốn tiền gọi LLM hai lần.
    """
    if not payload:
        return {}
    return {key: value for key, value in payload.items() if value is not None}


def payload_hash(kind: str, payload: Dict[str, Any]) -> str:
    """SHA-256 của (kind + payload chuẩn hoá), dùng phát hiện tái sử dụng
    idempotency key với payload KHÁC — trường hợp đó phải trả 409 chứ không được
    âm thầm trả kết quả của lần gọi trước."""
    canonical = json.dumps(
        {"kind": kind, "payload": payload},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Phân loại lỗi: tạm thời hay vĩnh viễn
# ---------------------------------------------------------------------------
_TRANSIENT_MARKERS = (
    "timed out",
    "timeout",
    "temporarily",
    "tạm thời",
    "connection",
    "connecterror",
    "connect timeout",
    "connection reset",
    "connection refused",
    "connection aborted",
    "remote protocol error",
    "server disconnected",
    "incomplete read",
    "network is unreachable",
    "name or service not known",
    "too many requests",
    "rate limit",
    "overloaded",
    "try again",
    "http 500",
    "http 502",
    "http 503",
    "http 504",
    "httpx.",
)


def is_transient_failure(error: Any) -> bool:
    """Lỗi này có đáng thử lại không?

    Dựa trên TÊN exception trước, rồi mới tới thông điệp. Cố tình hẹp: chỉ những
    lỗi đã biết là thoáng qua mới retry. Lỗi không nhận diện được thì coi như vĩnh
    viễn — thử lại một lỗi lạ sẽ đốt tiền gọi LLM mà không có lý do.
    """
    if error is None:
        return False
    if isinstance(error, AIJobExecutionError):
        return error.transient

    name = type(error).__name__.lower()
    if name in (
        "timeouterror",
        "connecterror",
        "connecttimeout",
        "readtimeout",
        "readerror",
        "writeerror",
        "remoteprotocolerror",
        "pooltimeout",
        "networkerror",
    ):
        return True

    text = str(error).lower()
    return any(marker in text for marker in _TRANSIENT_MARKERS)


def retry_delay_seconds(attempts: int) -> float:
    """Backoff luỹ tiến có trần: lần 1 chờ base, lần 2 base*2, lần 3 base*4…

    `attempts` là số lần đã thử (>=1). Trần lấy từ cấu hình để một job hỏng lặp lại
    không kẹt hàng đợi quá lâu.
    """
    from app.core.config import settings

    base = float(settings.AI_JOB_RETRY_BASE_SECONDS)
    ceiling = float(settings.AI_JOB_RETRY_MAX_SECONDS)
    exponent = max(int(attempts) - 1, 0)
    # min() trước phép lũy thừa để attempts rất lớn không tạo float khổng lồ.
    factor = min(2.0 ** min(exponent, 32), ceiling)
    return float(min(base * factor, ceiling))


# ---------------------------------------------------------------------------
# Ghi vào hàng đợi
# ---------------------------------------------------------------------------
def find_by_idempotency_key(
    db: Session,
    user_id: int,
    idempotency_key: Optional[str],
) -> Optional[AIJob]:
    """Tìm job đã tồn tại theo khoá chống gọi trùng. `None` nếu chưa có.

    Tách riêng khỏi `enqueue_job` để tầng API kiểm tra TRƯỚC khi trừ hạn mứng: một
    retry do mạng chập chờn là CÙNG một yêu cầu logic, trừ hạn mứng hai lần sẽ
    khiến người dùng mất gấp đôi số lượt gọi AI mà không hiểu vì sao.
    """
    key = (idempotency_key or "").strip()
    if not key:
        return None
    return (
        db.query(AIJob)
        .filter(AIJob.user_id == user_id, AIJob.idempotency_key == key)
        .first()
    )


def enqueue_job(
    db: Session,
    *,
    workspace_id: Optional[int],
    user_id: int,
    kind: str,
    payload: Dict[str, Any],
    campaign_id: Optional[int] = None,
    idempotency_key: Optional[str] = None,
    max_attempts: Optional[int] = None,
    now: Optional[datetime] = None,
) -> Tuple[AIJob, bool]:
    """Đẩy một job vào hàng đợi. Trả về `(job, deduplicated)`.

    `deduplicated=True` nghĩa là job đã tồn tại từ lần gọi trùng trước đó và KHÔNG
    có lượt gọi LLM nào mới được tạo — đó là mục tiêu của khoá idempotency: một
    double-click, một lần retry của client, hay một vết mạng chập chờn không được
    biến thành hai lượt gọi AI (tiền + độ trễ là thật).

    Ràng buộc UNIQUE(user_id, idempotency_key) ở tầng CSDL là hàng phòng thủ
    cuối cùng cho trường hợp hai request song song cùng chạy tới đây.
    """
    from app.core.config import settings

    if kind not in JOB_KINDS:
        raise ValueError(f"kind AI job không hợp lệ: {kind!r}")

    now = now or now_utc()
    clean_payload = normalize_payload(payload)
    digest = payload_hash(kind, clean_payload)
    key = (idempotency_key or "").strip() or None

    if key:
        existing = (
            db.query(AIJob)
            .filter(AIJob.user_id == user_id, AIJob.idempotency_key == key)
            .first()
        )
        if existing is not None:
            # Cùng khoá + cùng payload -> trả lại job cũ. Cùng khoá + KHÁC payload
            # -> 409 (xử lý ở tầng API) chứ không được trả nhầm kết quả.
            return existing, True

    job = AIJob(
        workspace_id=workspace_id,
        user_id=user_id,
        campaign_id=campaign_id,
        kind=kind,
        status=JOB_QUEUED,
        payload_json=json.dumps(clean_payload, ensure_ascii=False, default=str),
        idempotency_key=key,
        payload_hash=digest,
        attempts=0,
        max_attempts=int(max_attempts or settings.AI_JOB_MAX_ATTEMPTS),
        queued_at=now,
        available_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        # Request song song cùng dùng một khoá idempotency đã thắng rồi.
        db.rollback()
        existing = (
            db.query(AIJob)
            .filter(AIJob.user_id == user_id, AIJob.idempotency_key == key)
            .first()
        )
        if existing is not None:
            return existing, True
        raise
    db.refresh(job)
    return job, False


def cancel_queued_job(
    db: Session,
    job_id: int,
    now: Optional[datetime] = None,
) -> bool:
    """Huỷ một job đang ở trạng thái `queued`. Trả `False` nếu không huỷ được
    (job không tồn tại, hoặc đã chạy/đã kết thúc).

    Chuyển trạng thái bằng `UPDATE` có điều kiện, KHÔNG đọc-rồi-ghi: nếu worker
    vừa nhặt job trong khoảnh khắc client bấm huỷ, rowcount = 0 và client nhận
    409 — đúng thực tế, không phải trạng thái bịa ra.
    """
    now = now or now_utc()
    result = db.execute(
        update(AIJob)
        .where(AIJob.id == job_id, AIJob.status == JOB_QUEUED)
        .values(
            status=JOB_CANCELLED,
            cancelled_at=now,
            finished_at=now,
            updated_at=now,
        )
    )
    db.commit()
    return bool(result.rowcount)


# ---------------------------------------------------------------------------
# Nhặt job (FOR UPDATE SKIP LOCKED) + kết thúc job
# ---------------------------------------------------------------------------
def claim_next_job(
    db: Session,
    now: Optional[datetime] = None,
    candidate_limit: int = _CLAIM_CANDIDATE_LIMIT,
) -> Optional[AIJob]:
    """Nhặt job đến hạn tuổi nhất và chuyển nó sang `running`.

    Đây là điểm nóng của tính đúng đắn khi nhiều tiến trình dùng chung hàng đợi:

    1. `SELECT ... FOR UPDATE SKIP LOCKED` — trên Postgres, tiến trình thứ hai thấy
       hàng đang bị khoá thì NHẢY SANG hàng kế tiếp ngay thay vì chờ, nên nhiều
       worker vẫn chạy song song thay vì xếp hàng. (SQLite không có `FOR UPDATE`
       nên dialect bỏ mệnh đề này.)
    2. `UPDATE ... WHERE status='queued'` — chốt chặn cuối, hoạt động trên CẢ HAI
       backend: chỉ worker đọc được `rowcount == 1` mới được quyền chạy job, còn
       lại bỏ qua. Nhờ vậy kể cả khi `FOR UPDATE` bị bỏ qua (SQLite) hoặc có
       race giữa SELECT và UPDATE, một job vẫn chỉ được thực thi đúng MỘT LẦN.

    `attempts` tăng ngay lúc nhặt, nên một job bị tiến trình chết giữa chừng vẫn
    bị tính là đã thử — nếu không, một job kẹt có thể được thử vô hạn lần.
    """
    now = now or now_utc()
    try:
        candidate_ids = [
            row[0]
            for row in db.execute(
                select(AIJob.id)
                .where(AIJob.status == JOB_QUEUED, AIJob.available_at <= now)
                .order_by(AIJob.available_at.asc(), AIJob.queued_at.asc(), AIJob.id.asc())
                .limit(max(1, int(candidate_limit)))
            ).all()
        ]
    except OperationalError:
        # Ví dụ tranh chấp khoá ghi trên SQLite. Không phải lỗi nghiêm trọng: chỉ
        # cần thử lại ở vòng sau, còn hơn là làm sập vòng lặp worker.
        db.rollback()
        logger.debug("Khong doc duoc danh sach job AI, bo qua vong nay.", exc_info=True)
        return None

    for job_id in candidate_ids:
        try:
            locked = db.execute(
                select(AIJob)
                .where(AIJob.id == job_id)
                .with_for_update(skip_locked=True)
            ).scalar_one_or_none()
            if locked is None:
                # Tiến trình khác đang giữ khoá hàng này (Postgres) — thử hàng sau.
                db.rollback()
                continue

            claimed = db.execute(
                update(AIJob)
                .where(AIJob.id == job_id, AIJob.status == JOB_QUEUED)
                .values(
                    status=JOB_RUNNING,
                    attempts=AIJob.attempts + 1,
                    started_at=now,
                    updated_at=now,
                )
            )
            db.commit()
            if not claimed.rowcount:
                # Có tiến trình khác vừa nhặt trước. Bỏ qua, xét ứng viên kế tiếp.
                continue

            return (
                db.query(AIJob)
                .filter(AIJob.id == job_id)
                .first()
            )
        except OperationalError:
            db.rollback()
            logger.debug("Khong nhay duoc job AI %s, bo qua.", job_id, exc_info=True)
            continue
    return None


def mark_succeeded(
    db: Session,
    job_id: int,
    result: Optional[Dict[str, Any]],
    now: Optional[datetime] = None,
) -> bool:
    """Ghi kết quả và chuyển job sang `succeeded`.

    Có điều kiện `status='running'`: nếu watchdog đã kịp đánh `failed` vì quá hạn
    thì kết quả đến muộn bị LOẠI chứ không ghi đè trạng thái — client sẽ không
    thấy trạng thái `succeeded` cho một job đã báo thất bại.
    """
    now = now or now_utc()
    result = db.execute(
        update(AIJob)
        .where(AIJob.id == job_id, AIJob.status == JOB_RUNNING)
        .values(
            status=JOB_SUCCEEDED,
            result_json=json.dumps(result, ensure_ascii=False, default=str) if result is not None else None,
            error_message=None,
            finished_at=now,
            updated_at=now,
        )
    )
    db.commit()
    return bool(result.rowcount)


def register_failure(
    db: Session,
    job_id: int,
    message: str,
    transient: bool,
    now: Optional[datetime] = None,
    reason: Optional[str] = None,
) -> str:
    """Ghi nhận một lần thử thất bại và quyết định trạng thái kế tiếp.

    Trả về trạng thái mới của job:
    - `queued` nếu đây là lỗi TẠM THỜI và còn lượt thử: job được đẩy lại hàng đợi
      với `available_at = now + backoff luỹ tiến`. Backoff được lưu trong CSDL chứ
      không phải `sleep` trong thread, nên job đang backoff không giữ slot.
    - `failed` nếu lỗi vĩnh viễn, hoặc đã hết lượt thử.

    `reason` ghi kèm mã lỗi (ví dụ `TIMEOUT`) để client phân biệt "hết giờ" với
    "provider trả về 429".
    """
    now = now or now_utc()
    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    if job is None or job.status != JOB_RUNNING:
        # Job không còn ở `running` (đã bị huỷ, hoặc watchdog đã đánh failed):
        # kết quả/lỗi đến muộn không được ghi đè.
        return job.status if job is not None else JOB_FAILED

    detail = _truncate(message)
    if reason:
        detail = f"{reason}: {detail}" if detail else reason

    if transient and job.attempts < job.max_attempts:
        delay = retry_delay_seconds(job.attempts)
        job.status = JOB_QUEUED
        job.available_at = now + timedelta(seconds=delay)
        job.error_message = detail
        job.updated_at = now
        # `started_at` giữ lại để client thấy lần chạy gần nhất bắt đầu lúc nào.
        db.commit()
        logger.warning(
            "AI job %s that bai tam thoi (lan %d/%d), thu lai sau %.1fs: %s",
            job_id, job.attempts, job.max_attempts, delay, detail,
        )
        return JOB_QUEUED

    job.status = JOB_FAILED
    job.error_message = detail
    job.finished_at = now
    job.updated_at = now
    db.commit()
    logger.error(
        "AI job %s that bai (%d/%d): %s",
        job_id, job.attempts, job.max_attempts, detail,
    )
    return JOB_FAILED


def sweep_expired_jobs(
    db: Session,
    timeout_seconds: Optional[float] = None,
    now: Optional[datetime] = None,
    limit: int = 100,
) -> List[int]:
    """Đánh `failed` mọi job `running` đã vượt thời hạn cứng. Trả về các id.

    Đây là chốt chặn cho yêu cầu "một job kẹt không bao giờ được giữ slot vô hạn".
    Nó cũng tự chữa lành trạng thái mồ côi: nếu tiến trình worker bị kill giữa
    chừng, job đó mồ côi ở `running` và không có ai để hoàn tất — vòng quét này
    vẫn dọn nó, đúng sau `timeout_seconds`.

    Chỉ `running` mới bị đụng tới; `queued` có thể chờ bao lâu cũng được vì job
    chờ không tốn bộ nhớ (chỉ một hàng trong CSDL).
    """
    from app.core.config import settings

    if timeout_seconds is None:
        timeout_seconds = float(settings.AI_JOB_TIMEOUT_SECONDS)
    now = now or now_utc()
    deadline = now - timedelta(seconds=max(float(timeout_seconds), 1.0))

    candidates = [
        (row[0], row[1])
        for row in db.execute(
            select(AIJob.id, AIJob.started_at)
            .where(AIJob.status == JOB_RUNNING)
            .order_by(AIJob.started_at.asc())
            .limit(max(1, int(limit)))
        ).all()
    ]

    expired: List[int] = []
    for job_id, started_raw in candidates:
        started = as_utc(started_raw)
        if started is None or started > deadline:
            continue
        detail = (
            f"{FAILURE_TIMEOUT}: job vượt thời hạn cứng {int(float(timeout_seconds))}s. "
            "Slot worker đã được giải phóng."
        )
        updated = db.execute(
            update(AIJob)
            .where(AIJob.id == job_id, AIJob.status == JOB_RUNNING)
            .values(
                status=JOB_FAILED,
                error_message=detail,
                finished_at=now,
                updated_at=now,
            )
        )
        if updated.rowcount:
            expired.append(job_id)

    if candidates:
        db.commit()
    if expired:
        logger.warning(
            "Da danh %d AI job vuot thoi han cua hard timeout: %s", len(expired), expired
        )
    return expired


def purge_finished_jobs(
    db: Session,
    retention_days: Optional[int] = None,
    now: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> int:
    """Xoá job đã KẾT THÚC cũ hơn `AI_JOB_RETENTION_DAYS`. Trả số dòng đã xoá.

    Chỉ xoá `succeeded`/`failed`/`cancelled`. Job `queued`/`running` là việc chưa
    xong — xoá chúng là mất dữ liệu người dùng, nên loại trừ tường minh.
    """
    from app.core.config import settings

    if retention_days is None:
        retention_days = int(settings.AI_JOB_RETENTION_DAYS)
    if limit is None:
        limit = int(settings.AI_JOB_CLEANUP_BATCH)
    now = now or now_utc()
    cutoff = now - timedelta(days=max(int(retention_days), 0))

    stale_ids = [
        row[0]
        for row in db.execute(
            select(AIJob.id)
            .where(
                AIJob.status.in_(JOB_TERMINAL_STATUSES),
                AIJob.created_at < cutoff,
            )
            .order_by(AIJob.created_at.asc())
            .limit(max(1, int(limit)))
        ).all()
    ]
    if not stale_ids:
        return 0

    db.execute(delete(AIJob).where(AIJob.id.in_(stale_ids)))
    db.commit()
    logger.info("Da don %d AI job ket thuc cu hon %d ngay.", len(stale_ids), retention_days)
    return len(stale_ids)
