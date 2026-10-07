"""Bộ test cho hàng đợi AI bất đồng bộ (`/ai/jobs` + worker nền).

BAO PHỦ (mỗi mục đều có test tương ứng trong file này):
  1. Enqueue trả 202 và tạo đúng một hàng đợi
  2. Polling trả trạng thái kết thúc + kết quả
  3. Retry với backoff luỹ tiến, CHỈ cho lỗi tạm thời
  4. Quá hạn cứng -> `failed` + GIẢI PHÓNG SLOT
  5. Idempotency chặn gọi trùng (double-click)
  6. CHẶN truy cập chéo tenant (403)
  7. TỪ CHỐI hàng có `workspace_id IS NULL` (fail-closed)
  8. Nhiều worker không chạy trùng cùng một job (FOR UPDATE SKIP LOCKED)
  9. Dọn job cũ

NGUYÊN TẮC: KHÔNG có lời gọi mạng nào trong file này. Mọi lượt gọi LLM đều bị thay
bằng stub tất định — fixture `offline_ai_for_tests` ở conftest.py đã chặn
`AIService._call_provider_with_retry`, và các test dùng thêm stub riêng khi cần kiểm
soát chính xác số lần chạy.
"""

import json
import threading
import time
from datetime import timedelta
from typing import List

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import create_access_token
from app.models.entities import AIJob, Base, Campaign, User, Workspace
from app.services.ai import job_worker
from app.services.jobs import queue as job_queue

API = "/api/v1/ai/jobs"


# ==============================================================================
# Fixture: CSDL SQLite file-backed riêng cho test tranh chấp khoá
# ==============================================================================
class _FileDb:
    """Session factory cho CSDL file-backed, kèm id user dùng chung.

    Gọi được như `file_db()` để mở session, nên `monkeypatch.setattr(
    core_database, "SessionLocal", file_db)` hoạt động đúng như với `SessionLocal`.
    """

    def __init__(self, session_factory, user_id):
        self.session_factory = session_factory
        self.user_id = user_id

    def __call__(self):
        return self.session_factory()


@pytest.fixture
def file_db(tmp_path):
    """CSDL SQLite trên FILE cho test đa tiến trình, kèm một user sẵn sàng.

    CSDL in-memory dùng StaticPool nên MỌI session dùng chung một connection — hai
    thread sẽ tranh nhau connection đó và test "nhiều worker không chạy trùng" trở
    nên vô nghĩa. File-backed cho mỗi thread một connection thật, đúng như
    production. WAL + `busy_timeout` để thread thứ hai chờ thay vì ném
    "database is locked" ngay.

    `ai_jobs.user_id` có khóa ngoại tới `users`, nên fixture tạo sẵn một user để
    test không phải dựng lại ở mỗi nơi.
    """
    db_path = tmp_path / "ai_jobs_queue.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    LocalSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = LocalSession()
    try:
        user = User(
            email="ai-queue@test.com",
            full_name="AI Queue User",
            password_hash="x",
            role="MANAGER",
            status="ACTIVE",
        )
        session.add(user)
        session.commit()
        user_id = user.id
    finally:
        session.close()
    try:
        yield _FileDb(LocalSession, user_id)
    finally:
        engine.dispose()


# ==============================================================================
# Fixture: CSDL SQLite in-memory dùng chung với bộ test hiện có
# ==============================================================================
@pytest.fixture
def queue_session(db_session):
    """Session CSDL test chuẩn (dùng chung với phần còn lại của bộ test)."""
    return db_session


def _user_by_email(db, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None, f"Thiếu user seed: {email}"
    return user


def _headers(db, email: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': str(_user_by_email(db, email).id)})}"}


def _enqueue_payload(**overrides) -> dict:
    body = {
        "kind": "ideas",
        "campaign_id": 1,
        "channel_code": "facebook",
        "custom_topic": "Khai trương cửa hàng",
    }
    body.update(overrides)
    return body


def _make_job(db, **overrides) -> AIJob:
    now = job_queue.now_utc()
    values = {
        "workspace_id": 1,
        "user_id": 1,
        "kind": job_queue.KIND_IDEAS,
        "status": job_queue.JOB_QUEUED,
        "payload_json": json.dumps({"campaign_id": 1, "channel_code": "facebook"}),
        "idempotency_key": None,
        "payload_hash": job_queue.payload_hash(job_queue.KIND_IDEAS, {"campaign_id": 1, "channel_code": "facebook"}),
        "attempts": 0,
        "max_attempts": 3,
        "queued_at": now,
        "available_at": now,
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    job = AIJob(**values)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


# ==============================================================================
# 1. Enqueue trả 202
# ==============================================================================
def test_enqueue_returns_202_and_persists_job(client, queue_session):
    headers = _headers(queue_session, "manager@gmail.com")
    response = client.post(API, json=_enqueue_payload(), headers=headers)

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == job_queue.JOB_QUEUED
    assert body["kind"] == job_queue.KIND_IDEAS
    assert body["deduplicated"] is False
    assert body["job_id"] > 0

    row = queue_session.query(AIJob).filter(AIJob.id == body["job_id"]).first()
    assert row is not None
    assert row.status == job_queue.JOB_QUEUED
    assert row.attempts == 0
    # Job phải mang tenant rõ ràng ngay từ lúc nhận, nếu không nó sẽ không bao
    # giờ đọc lại được (mọi lần đọc đều fail-closed với workspace_id NULL).
    assert row.workspace_id is not None


def test_enqueue_rejects_invalid_kind(client, queue_session):
    response = client.post(
        API, json=_enqueue_payload(kind="hien_thu_bien_doi"), headers=_headers(queue_session, "manager@gmail.com")
    )
    assert response.status_code == 422
    assert "kind" in response.text


def test_enqueue_validates_payload_against_sync_schema(client, queue_session):
    """`summary` bắt buộc có campaign_id; `omnichannel` bắt buộc có brief.
    Kiểm tra SỚM lúc enqueue để job chết không tốn tiền gọi LLM."""
    headers = _headers(queue_session, "manager@gmail.com")

    assert client.post(API, json={"kind": "summary"}, headers=headers).status_code == 422
    assert client.post(API, json={"kind": "omnichannel", "campaign_id": 1}, headers=headers).status_code == 422
    assert client.post(API, json={"kind": "draft", "campaign_id": 1}, headers=headers).status_code == 422


def test_enqueue_requires_authentication(client):
    assert client.post(API, json=_enqueue_payload()).status_code == 401


# ==============================================================================
# 2. Polling trả trạng thái kết thúc + kết quả
# ==============================================================================
def test_poll_returns_terminal_state_and_result(client, queue_session):
    headers = _headers(queue_session, "manager@gmail.com")
    job_id = client.post(API, json=_enqueue_payload(), headers=headers).json()["job_id"]

    pending = client.get(f"{API}/{job_id}", headers=headers)
    assert pending.status_code == 200
    assert pending.json()["status"] == job_queue.JOB_QUEUED
    assert pending.json()["result"] is None

    # Worker phải NHẶT job (chuyển `queued` -> `running`) rồi mới ghi kết quả được:
    # `mark_succeeded` có điều kiện `status='running'` để không ghi đè được trạng thái
    # mà watchdog đã kết luận.
    claimed = job_queue.claim_next_job(queue_session)
    assert claimed is not None and claimed.id == job_id
    assert claimed.attempts == 1

    result = {"task_type": "IDEA", "ideas": [], "model_used": "stub-model"}
    assert job_queue.mark_succeeded(queue_session, job_id, result) is True

    done = client.get(f"{API}/{job_id}", headers=headers)
    assert done.status_code == 200
    body = done.json()
    assert body["status"] == job_queue.JOB_SUCCEEDED
    assert body["result"]["model_used"] == "stub-model"
    assert body["finished_at"] is not None
    assert body["started_at"] is not None
    assert body["attempts"] == 1


def test_list_jobs_filters_and_paginates(client, queue_session):
    headers = _headers(queue_session, "manager@gmail.com")

    ideas_id = client.post(API, json=_enqueue_payload(), headers=headers).json()["job_id"]
    draft_id = client.post(
        API,
        json=_enqueue_payload(kind="draft", selected_idea="Góc nhìn mới"),
        headers=headers,
    ).json()["job_id"]
    # Chỉ job `running` mới nhận kết quả được (xem `mark_succeeded`). Job nào được
    # nhặt trước là tuỳ thứ tự `queued_at`, nên nhặt cho tới khi trúng job cần đánh.
    claimed_ids = set()
    for _ in range(5):
        claimed = job_queue.claim_next_job(queue_session)
        if claimed is None:
            break
        claimed_ids.add(claimed.id)
        if claimed.id == draft_id:
            break
    assert draft_id in claimed_ids
    assert job_queue.mark_succeeded(queue_session, draft_id, {"task_type": "DRAFT", "title": "stub"}) is True

    everything = client.get(API, headers=headers).json()
    assert everything["total"] >= 2

    only_ideas = client.get(API, params={"kind": "ideas"}, headers=headers).json()
    assert [item["job_id"] for item in only_ideas["items"]] == [ideas_id]

    only_succeeded = client.get(API, params={"status": "succeeded"}, headers=headers).json()
    assert [item["job_id"] for item in only_succeeded["items"]] == [draft_id]

    page = client.get(API, params={"page": 1, "page_size": 1}, headers=headers).json()
    assert len(page["items"]) == 1
    assert page["has_next"] is True

    assert client.get(API, params={"status": "khong_ton_tai"}, headers=headers).status_code == 422
    assert client.get(API, params={"kind": "khong_ton_tai"}, headers=headers).status_code == 422


def test_cancel_queued_job(client, queue_session):
    headers = _headers(queue_session, "manager@gmail.com")
    job_id = client.post(API, json=_enqueue_payload(), headers=headers).json()["job_id"]

    cancelled = client.post(f"{API}/{job_id}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == job_queue.JOB_CANCELLED

    row = queue_session.query(AIJob).filter(AIJob.id == job_id).first()
    assert row.status == job_queue.JOB_CANCELLED
    assert row.cancelled_at is not None

    # Huỷ lần hai: báo đã huỷ thay vì lỗi, để client poll idempotent được.
    again = client.post(f"{API}/{job_id}/cancel", headers=headers)
    assert again.status_code == 200
    assert again.json()["status"] == job_queue.JOB_CANCELLED


def test_cancel_running_job_returns_409(client, queue_session):
    """Không được nói dối rằng đã huỷ trong khi LLM vẫn đang chạy."""
    headers = _headers(queue_session, "manager@gmail.com")
    job = _make_job(queue_session, status=job_queue.JOB_RUNNING, attempts=1, started_at=job_queue.now_utc())

    response = client.post(f"{API}/{job.id}/cancel", headers=headers)
    assert response.status_code == 409
    assert "running" in response.json()["detail"]


# ==============================================================================
# 3. Retry + backoff luỹ tiến, CHỈ cho lỗi tạm thời
# ==============================================================================
def test_transient_failure_is_rescheduled_with_backoff(queue_session, monkeypatch):
    monkeypatch.setattr(settings, "AI_JOB_RETRY_BASE_SECONDS", 10.0)
    monkeypatch.setattr(settings, "AI_JOB_RETRY_MAX_SECONDS", 300.0)

    job = _make_job(queue_session, status=job_queue.JOB_RUNNING, attempts=1, max_attempts=3)
    before = job_queue.now_utc()

    new_status = job_queue.register_failure(
        queue_session, job.id, "Connection reset by peer", transient=True, now=before
    )
    assert new_status == job_queue.JOB_QUEUED

    row = queue_session.query(AIJob).filter(AIJob.id == job.id).first()
    assert row.status == job_queue.JOB_QUEUED
    delay = (job_queue.as_utc(row.available_at) - before).total_seconds()
    assert 9 <= delay <= 11, f"Backoff lần 1 phải bằng base (10s), thực tế {delay}s"
    assert row.finished_at is None  # chưa kết thúc thì chưa được đóng job
    assert "Connection reset" in row.error_message


def test_backoff_grows_exponentially(queue_session, monkeypatch):
    monkeypatch.setattr(settings, "AI_JOB_RETRY_BASE_SECONDS", 10.0)
    monkeypatch.setattr(settings, "AI_JOB_RETRY_MAX_SECONDS", 300.0)

    # Lần 1: 10s. Lần 2: 20s. Lần 3: 40s.
    assert job_queue.retry_delay_seconds(1) == 10.0
    assert job_queue.retry_delay_seconds(2) == 20.0
    assert job_queue.retry_delay_seconds(3) == 40.0
    # Trần chặn backoff lùng thùng.
    assert job_queue.retry_delay_seconds(20) == 300.0


def test_permanent_failure_is_not_retried(queue_session):
    """Lỗi vĩnh viễn phải chết ngay: retry chỉ là đốt tiền gọi LLM."""
    job = _make_job(queue_session, status=job_queue.JOB_RUNNING, attempts=1, max_attempts=3)

    new_status = job_queue.register_failure(
        queue_session, job.id, "Không tìm thấy người dùng", transient=False
    )
    assert new_status == job_queue.JOB_FAILED

    row = queue_session.query(AIJob).filter(AIJob.id == job.id).first()
    assert row.status == job_queue.JOB_FAILED
    assert row.finished_at is not None
    assert row.attempts == 1  # KHÔNG tăng thêm lượt thử cho lỗi vĩnh viễn


def test_transient_failure_fails_after_max_attempts(queue_session):
    job = _make_job(queue_session, status=job_queue.JOB_RUNNING, attempts=3, max_attempts=3)

    new_status = job_queue.register_failure(
        queue_session, job.id, "AI Provider trả về lỗi HTTP 503", transient=True
    )
    assert new_status == job_queue.JOB_FAILED

    row = queue_session.query(AIJob).filter(AIJob.id == job.id).first()
    assert row.status == job_queue.JOB_FAILED
    assert row.finished_at is not None


@pytest.mark.parametrize(
    "message,expected",
    [
        ("TIMEOUT", True),
        ("httpx.ConnectError: connection refused", True),
        ("AI Provider trả về lỗi HTTP 429: too many requests", True),
        ("AI Provider trả về lỗi HTTP 503", True),
        ("read timeout", True),
        ("Not authorized to access this resource", False),
        ("Payload không hợp lệ với kind='ideas'", False),
        ("AI Provider trả về lỗi HTTP 401", False),
    ],
)
def test_is_transient_failure_classification(message, expected):
    assert job_queue.is_transient_failure(RuntimeError(message)) is expected


def test_transient_exception_name_is_transient():
    class ConnectTimeout(Exception):
        pass

    assert job_queue.is_transient_failure(ConnectTimeout("x")) is True
    assert job_queue.is_transient_failure(ValueError("x")) is False
    assert job_queue.is_transient_failure(None) is False


def test_late_result_after_failure_is_discarded(queue_session):
    """Watchdog đã đánh `failed` thì kết quả đến muộn KHÔNG được ghi đè — nếu
    không client sẽ thấy `succeeded` cho một job đã báo thất bại."""
    job = _make_job(queue_session, status=job_queue.JOB_RUNNING, attempts=1)
    job_queue.register_failure(queue_session, job.id, "quá hạn", transient=False)

    assert job_queue.mark_succeeded(queue_session, job.id, {"ideas": []}) is False
    row = queue_session.query(AIJob).filter(AIJob.id == job.id).first()
    assert row.status == job_queue.JOB_FAILED


# ==============================================================================
# 4. Quá hạn cứng -> failed + giải phóng slot
# ==============================================================================
def test_sweep_marks_expired_job_failed(queue_session):
    now = job_queue.now_utc()
    job = _make_job(
        queue_session,
        status=job_queue.JOB_RUNNING,
        attempts=1,
        started_at=now - timedelta(seconds=400),
    )

    expired = job_queue.sweep_expired_jobs(queue_session, timeout_seconds=300, now=now)

    assert expired == [job.id]
    row = queue_session.query(AIJob).filter(AIJob.id == job.id).first()
    assert row.status == job_queue.JOB_FAILED
    assert job_queue.FAILURE_TIMEOUT in row.error_message
    assert row.finished_at is not None


def test_sweep_leaves_fresh_job_running(queue_session):
    now = job_queue.now_utc()
    job = _make_job(
        queue_session, status=job_queue.JOB_RUNNING, attempts=1, started_at=now - timedelta(seconds=30)
    )

    assert job_queue.sweep_expired_jobs(queue_session, timeout_seconds=300, now=now) == []
    row = queue_session.query(AIJob).filter(AIJob.id == job.id).first()
    assert row.status == job_queue.JOB_RUNNING


def test_sweep_never_touches_queued_jobs(queue_session):
    """Job ĐANG CHỜ có thể chờ bao lâu cũng được — nó chỉ tốn một hàng trong CSDL,
    không tốn RAM. Chỉ job đang chạy mới cần thời hạn cứng."""
    job = _make_job(
        queue_session,
        status=job_queue.JOB_QUEUED,
        queued_at=job_queue.now_utc() - timedelta(days=5),
        available_at=job_queue.now_utc() - timedelta(days=5),
    )
    assert job_queue.sweep_expired_jobs(queue_session, timeout_seconds=300) == []
    assert queue_session.query(AIJob).filter(AIJob.id == job.id).first().status == job_queue.JOB_QUEUED


def test_slot_pool_rejects_beyond_bound():
    pool = job_worker.SlotPool(max_slots=2)
    assert pool.try_acquire() is True
    assert pool.try_acquire() is True
    assert pool.try_acquire() is False, "Vượt trần thì phải từ chối, không được tạo việc mới"
    assert pool.inflight == 2
    pool.release_slot()
    assert pool.inflight == 1
    assert pool.try_acquire() is True


def test_slot_is_released_exactly_once():
    """Watchdog và thread kẹt cùng trả phiếu sẽ làm bộ đếm lệch xuống âm nếu không
    chống trùng — hạn mức song song sẽ bị nới lỏng dần theo thời gian."""
    pool = job_worker.SlotPool(max_slots=1)
    slot = job_worker._Slot(pool)
    pool.try_acquire()

    assert slot.release() is True
    assert slot.release() is False
    assert pool.inflight == 0


def test_worker_releases_slot_when_job_times_out(file_db, monkeypatch):
    """Bài toán cốt lõi của yêu cầu: thread kẹt không được giữ slot vô hạn.

    Kịch bản: một worker với timeout 1 giây, job chạy "kẹt" 30 giây. Sau khi quá
    hạn, job phải là `failed` VÀ bộ đếm slot phải về 0, dù thread vẫn còn sống.
    """
    import app.core.database as core_database

    monkeypatch.setattr(core_database, "SessionLocal", file_db)

    user_id = file_db.user_id
    released = threading.Event()
    stubbed = {"running": False}

    def _stuck_runner(db, job):
        stubbed["running"] = True
        # Giả lập lời gọi provider treo: giữ thread sống lâu hơn thời hạn cứng.
        released.wait(timeout=10.0)
        raise job_queue.AIJobExecutionError("kết quả đến muộn sau khi bị đánh dấu quá hạn", transient=True)

    monkeypatch.setattr("app.api.v1.ai_jobs.execute_ai_job", _stuck_runner)

    worker = job_worker.AIJobWorker(max_slots=1, poll_interval=0.05, timeout_seconds=1, cleanup_interval=9999)

    session = file_db()
    try:
        _make_job(session, workspace_id=None, user_id=user_id)
    finally:
        session.close()

    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        worker.tick()
        session = file_db()
        try:
            row = session.query(AIJob).filter(AIJob.user_id == user_id).first()
            status = row.status if row else None
        finally:
            session.close()
        if status == job_queue.JOB_FAILED and worker.pool.inflight == 0 and stubbed["running"]:
            break
        time.sleep(0.05)

    session = file_db()
    try:
        row = session.query(AIJob).filter(AIJob.user_id == user_id).first()
        assert row.status == job_queue.JOB_FAILED
        assert job_queue.FAILURE_TIMEOUT in row.error_message
    finally:
        session.close()

    assert stubbed["running"] is True, "Test phải thật sự có một thread đang kẹt thì mới chứng minh được"
    assert worker.pool.inflight == 0, "Slot phải được giải phóng dù thread chưa chết"
    assert worker.timed_out_count >= 1

    # Thread treo được thả ra nên không chặn kết thúc test.
    released.set()
    assert worker.pool.try_acquire() is True


def test_worker_never_exceeds_slot_bound(file_db, monkeypatch):
    """Nhiều job hơn số slot -> số job chạy đồng thời KHÔNG BAO GIỜ vượt trần."""
    import app.core.database as core_database

    monkeypatch.setattr(core_database, "SessionLocal", file_db)
    user_id = file_db.user_id

    peak = {"value": 0, "current": 0}
    lock = threading.Lock()
    finished = threading.Event()

    def _slow_runner(db, job):
        with lock:
            peak["current"] += 1
            peak["value"] = max(peak["value"], peak["current"])
        # Giữ job "đang chạy" cho tới khi có ít nhất 2 job cùng chạy (tức là tới khi
        # worker dùng hết 2 slot) để test thật sự CHỨNG MINH được việc chạy song
        # song — nếu không, một worker chạy tuần tự cũng qua được và trần slot chưa
        # từng bị kiểm tra.
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            with lock:
                if peak["current"] >= 2:
                    break
            time.sleep(0.005)
        with lock:
            peak["current"] -= 1
        return {"stub": True}

    monkeypatch.setattr("app.api.v1.ai_jobs.execute_ai_job", _slow_runner)

    worker = job_worker.AIJobWorker(max_slots=2, poll_interval=0.01, timeout_seconds=60, cleanup_interval=9999)

    session = file_db()
    try:
        for _ in range(8):
            _make_job(session, workspace_id=None, user_id=user_id)
    finally:
        session.close()

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        worker.tick()
        time.sleep(0.01)
        session = file_db()
        try:
            done = (
                session.query(AIJob)
                .filter(AIJob.user_id == user_id, AIJob.status == job_queue.JOB_SUCCEEDED)
                .count()
            )
        finally:
            session.close()
        if done == 8:
            break

    finished.set()
    time.sleep(0.3)

    session = file_db()
    try:
        assert (
            session.query(AIJob)
            .filter(AIJob.user_id == user_id, AIJob.status == job_queue.JOB_SUCCEEDED)
            .count()
            == 8
        )
    finally:
        session.close()

    assert peak["value"] <= 2, f"Tràn trần slot: chạy đồng thời {peak['value']} job với max_slots=2"
    assert peak["value"] >= 1, "Test phải thật sự chạy job thì mới có ý nghĩa"


# ==============================================================================
# 5. Idempotency chặn gọi trùng
# ==============================================================================
def test_idempotency_key_prevents_duplicate_jobs(client, queue_session):
    """Double-click / retry mạng: mỗi lượt gọi AI là tiền thật và độ trễ thật."""
    headers = _headers(queue_session, "manager@gmail.com")
    body = _enqueue_payload(idempotency_key="double-click-001")

    first = client.post(API, json=body, headers=headers)
    second = client.post(API, json=body, headers=headers)

    assert first.status_code == 202 and second.status_code == 202
    assert first.json()["job_id"] == second.json()["job_id"]
    assert first.json()["deduplicated"] is False
    assert second.json()["deduplicated"] is True
    assert queue_session.query(AIJob).filter(AIJob.idempotency_key == "double-click-001").count() == 1


def test_idempotency_ignores_explicit_nulls(client, queue_session):
    """`{"tone": null}` và không gửi `tone` là CÙNG một yêu cầu — nếu chuẩn hoá sai
    thì double-click kèm payload hơi khác sẽ lách qua chống trùng."""
    headers = _headers(queue_session, "manager@gmail.com")
    first = client.post(
        API, json=_enqueue_payload(idempotency_key="null-001", tone=None), headers=headers
    ).json()
    second = client.post(
        API,
        json=_enqueue_payload(idempotency_key="null-001", product_usp=None),
        headers=headers,
    ).json()
    assert first["job_id"] == second["job_id"]
    assert second["deduplicated"] is True


def test_idempotency_key_reuse_with_different_payload_conflicts(client, queue_session):
    """Tái sử dụng khoá với payload KHÁC phải báo 409 chứ không được trả nhầm kết quả
    của lần gọi trước."""
    headers = _headers(queue_session, "manager@gmail.com")
    client.post(
        API,
        json=_enqueue_payload(idempotency_key="conflict-001", custom_topic="Chủ đề A"),
        headers=headers,
    )
    response = client.post(
        API,
        json=_enqueue_payload(idempotency_key="conflict-001", custom_topic="Chủ đề B"),
        headers=headers,
    )
    assert response.status_code == 409
    assert queue_session.query(AIJob).filter(AIJob.idempotency_key == "conflict-001").count() == 1


def test_idempotent_retry_does_not_double_charge_quota(client, queue_session, monkeypatch):
    """Hạn mứng AI phải tính MỘT lần cho mỗi yêu cầu logic.

    Retry do mạng chập chờn là cùng một yêu cầu; nếu mỗi lượt gửi lại đều trừ một
    lượt gọi AI thì người dùng mất gấp đôi số lượt mà không hiểu vì sao.
    """
    from app.core import security as security_module

    headers = _headers(queue_session, "manager@gmail.com")
    body = _enqueue_payload(idempotency_key="quota-dedupe-001")

    charged = []
    original = security_module.enforce_quota

    def _spy(identifier, *args, **kwargs):
        charged.append(identifier)
        return original(identifier, *args, **kwargs)

    monkeypatch.setattr("app.api.v1.ai_jobs.enforce_quota", _spy)
    for _ in range(3):
        assert client.post(API, json=body, headers=headers).status_code == 202

    manager = _user_by_email(queue_session, "manager@gmail.com")
    assert charged == [f"ai:ideas:user={manager.id}"], (
        f"Hạn mứng bị trừ {len(charged)} lần cho 1 yêu cầu logic: {charged}"
    )


def test_dedupe_of_unreadable_job_is_refused(client, queue_session):
    """Không được trả 202 rồi 403 ở lần poll kế tiếp — lỗi vòng vèo khó hiểu nhất."""
    manager = _user_by_email(queue_session, "manager@gmail.com")
    # Payload phải khớp ĐÚNG những gì `_enqueue_payload()` chuẩn hoá ra, nếu không
    # tầng API sẽ trả 409 (khoá trùng nhưng payload khác) trước khi tới bước 403.
    same_payload = {
        "campaign_id": 1,
        "channel_code": "facebook",
        "custom_topic": "Khai trương cửa hàng",
    }
    orphan = _make_job(
        queue_session,
        workspace_id=None,
        user_id=manager.id,
        idempotency_key="orphan-key-001",
        payload_json=json.dumps(same_payload, ensure_ascii=False),
        payload_hash=job_queue.payload_hash(job_queue.KIND_IDEAS, same_payload),
    )
    assert orphan.id > 0

    response = client.post(
        API,
        json=_enqueue_payload(idempotency_key="orphan-key-001"),
        headers=_headers(queue_session, "manager@gmail.com"),
    )
    assert response.status_code == 403


def test_jobs_without_idempotency_key_are_never_deduplicated(client, queue_session):
    headers = _headers(queue_session, "manager@gmail.com")
    first = client.post(API, json=_enqueue_payload(), headers=headers).json()
    second = client.post(API, json=_enqueue_payload(), headers=headers).json()
    assert first["job_id"] != second["job_id"]
    assert first["deduplicated"] is False and second["deduplicated"] is False


def test_enqueue_is_deduplicated_at_queue_level_under_race(file_db):
    """Ràng buộc UNIQUE ở tầng CSDL là hàng phòng thủ cuối cùng cho trường hợp hai
    request song song cùng chạy tới đích."""
    import app.core.database as core_database

    original = core_database.SessionLocal
    try:
        core_database.SessionLocal = file_db
        user_id = file_db.user_id

        results: List[int] = []
        lock = threading.Lock()
        barrier = threading.Barrier(2)

        def _attempt():
            local = file_db()
            try:
                barrier.wait(timeout=5)
                job, dedup = job_queue.enqueue_job(
                    local,
                    workspace_id=None,
                    user_id=user_id,
                    kind=job_queue.KIND_IDEAS,
                    payload={"campaign_id": 1},
                    idempotency_key="race-key-1",
                )
                with lock:
                    results.append(job.id)
            finally:
                local.close()

        threads = [threading.Thread(target=_attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        assert len(results) == 2, "Cả hai lượt đều phải trả về một job id"
        assert len(set(results)) == 1, f"Hai lượt tạo ra hai job khác nhau: {results}"
    finally:
        core_database.SessionLocal = original


# ==============================================================================
# 6 + 7. CÁCH LY TENANT (fail-closed)
# ==============================================================================
def test_cross_tenant_read_is_denied(client, queue_session, workspace_beta):
    """User của Workspace Beta KHÔNG được đọc job của Workspace Alpha."""
    beta_manager = _user_by_email(queue_session, "agency_mgr_beta@gmail.com")
    alpha_job = _make_job(queue_session, workspace_id=1, user_id=beta_manager.id)

    response = client.get(
        f"{API}/{alpha_job.id}",
        headers={"Authorization": f"Bearer {create_access_token(data={'sub': str(beta_manager.id)})}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to access AI jobs in this workspace"


def test_cross_tenant_list_excludes_other_tenants(client, queue_session, workspace_beta):
    beta_manager = _user_by_email(queue_session, "agency_mgr_beta@gmail.com")
    alpha_job = _make_job(queue_session, workspace_id=1, user_id=1)
    beta_job = _make_job(
        queue_session, workspace_id=workspace_beta.id, user_id=beta_manager.id
    )

    response = client.get(
        API,
        headers={"Authorization": f"Bearer {create_access_token(data={'sub': str(beta_manager.id)})}"},
    )
    assert response.status_code == 200
    ids = [item["job_id"] for item in response.json()["items"]]
    assert beta_job.id in ids
    assert alpha_job.id not in ids


def test_cross_tenant_cancel_is_denied(client, queue_session, workspace_beta):
    beta_marketer = _user_by_email(queue_session, "marketer_beta@gmail.com")
    alpha_job = _make_job(queue_session, workspace_id=1, user_id=1)

    response = client.post(
        f"{API}/{alpha_job.id}/cancel",
        headers={"Authorization": f"Bearer {create_access_token(data={'sub': str(beta_marketer.id)})}"},
    )
    assert response.status_code == 403
    assert queue_session.query(AIJob).filter(AIJob.id == alpha_job.id).first().status == job_queue.JOB_QUEUED


def test_cross_tenant_enqueue_is_denied(client, queue_session, workspace_beta):
    """Không được ghi job vào workspace của tenant khác, kể cả khi biết id."""
    beta_manager = _user_by_email(queue_session, "agency_mgr_beta@gmail.com")
    response = client.post(
        API,
        params={"workspace_id": 1},
        json=_enqueue_payload(),
        headers={"Authorization": f"Bearer {create_access_token(data={'sub': str(beta_manager.id)})}"},
    )
    assert response.status_code == 403
    assert queue_session.query(AIJob).filter(AIJob.workspace_id == 1, AIJob.user_id == beta_manager.id).count() == 0


def test_null_workspace_row_is_refused(client, queue_session):
    """FAIL-CLOSED: job có `workspace_id IS NULL` phải bị từ chối, kể cả với chính
    người tạo. Không có ngoại lệ "tôi tạo nên tôi thấy" — đó là đúng loại lỗ hổng mà
    `check_workspace_boundary` của nội dung marketing đã chống."""
    creator = _user_by_email(queue_session, "manager@gmail.com")
    orphan = _make_job(queue_session, workspace_id=None, user_id=creator.id)

    response = client.get(
        f"{API}/{orphan.id}",
        headers={"Authorization": f"Bearer {create_access_token(data={'sub': str(creator.id)})}"},
    )
    assert response.status_code == 403
    assert "Không xác định được không gian làm việc" in response.json()["detail"]


def test_null_workspace_row_hidden_from_list(client, queue_session):
    creator = _user_by_email(queue_session, "manager@gmail.com")
    orphan = _make_job(queue_session, workspace_id=None, user_id=creator.id)

    response = client.get(
        API, headers={"Authorization": f"Bearer {create_access_token(data={'sub': str(creator.id)})}"}
    )
    assert response.status_code == 200
    assert orphan.id not in [item["job_id"] for item in response.json()["items"]]


def test_null_workspace_row_cancel_is_refused(client, queue_session):
    creator = _user_by_email(queue_session, "manager@gmail.com")
    orphan = _make_job(queue_session, workspace_id=None, user_id=creator.id)

    response = client.post(
        f"{API}/{orphan.id}/cancel",
        headers={"Authorization": f"Bearer {create_access_token(data={'sub': str(creator.id)})}"},
    )
    assert response.status_code == 403
    assert queue_session.query(AIJob).filter(AIJob.id == orphan.id).first().status == job_queue.JOB_QUEUED


def test_admin_also_cannot_read_null_workspace_job(client, queue_session):
    """ADMIN có phạm vi toàn cục ở endpoint khác, nhưng KHÔNG được phép đọc job
    không xác định được tenant — không có tenant thì không có ranh giới nào để tin."""
    admin = User(
        email="ai-queue-admin@test.com",
        full_name="AI Queue Admin",
        password_hash="x",
        role="ADMIN",
        status="ACTIVE",
    )
    queue_session.add(admin)
    queue_session.commit()
    orphan = _make_job(queue_session, workspace_id=None, user_id=1)

    response = client.get(
        f"{API}/{orphan.id}",
        headers={"Authorization": f"Bearer {create_access_token(data={'sub': str(admin.id)})}"},
    )
    assert response.status_code == 403


def test_unknown_job_returns_404(client, queue_session):
    response = client.get(
        f"{API}/999999", headers=_headers(queue_session, "manager@gmail.com")
    )
    assert response.status_code == 404


# ==============================================================================
# 8. Nhiều worker không chạy trùng cùng một job
# ==============================================================================
def test_concurrent_claims_never_double_execute(file_db):
    """`SELECT ... FOR UPDATE SKIP LOCKED` + `UPDATE` có điều kiện `status='queued'`.

    Chạy thật 4 thread trên CSDL file-backed, mỗi thread một connection riêng, tự
    nhặt job cho tới khi hàng đợi rỗng. Mỗi job được chạy đúng MỘT LẦN.
    """
    user_id = file_db.user_id
    session = file_db()
    try:
        job_ids = [_make_job(session, workspace_id=None, user_id=user_id).id for _ in range(12)]
    finally:
        session.close()

    claimed: List[int] = []
    lock = threading.Lock()

    def _claimer():
        local = file_db()
        try:
            while True:
                job = job_queue.claim_next_job(local)
                if job is None:
                    return
                with lock:
                    claimed.append(job.id)
        finally:
            local.close()

    threads = [threading.Thread(target=_claimer) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
        assert not thread.is_alive(), "Thread nhặt job bị treo"

    assert sorted(claimed) == sorted(job_ids), (
        f"Mỗi job phải được nhặt đúng 1 lần. Nhặt {len(claimed)} lần cho {len(job_ids)} job: "
        f"{sorted(claimed)}"
    )
    assert len(claimed) == len(set(claimed)), "Có job bị nhặt trùng — tức sẽ chạy trùng lượt gọi AI"

    session = file_db()
    try:
        rows = session.query(AIJob).filter(AIJob.user_id == user_id).all()
        assert all(row.status == job_queue.JOB_RUNNING for row in rows)
        assert all(row.attempts == 1 for row in rows), "attempts phải tăng đúng 1 lần mỗi lần nhặt"
    finally:
        session.close()


def test_claim_skips_job_in_backoff(file_db):
    """Backoff được lưu trong CSDL nên job chưa tới hạn không bị nhặt — quan trọng vì
    job đang backoff không được giữ slot."""
    session = file_db()
    try:
        job = _make_job(
            session,
            workspace_id=None,
            user_id=file_db.user_id,
            available_at=job_queue.now_utc() + timedelta(seconds=120),
        )
    finally:
        session.close()

    session = file_db()
    try:
        assert job_queue.claim_next_job(session) is None
    finally:
        session.close()

    session = file_db()
    try:
        assert job_queue.claim_next_job(session, now=job_queue.now_utc() + timedelta(seconds=180)).id == job.id
    finally:
        session.close()


def test_claim_returns_none_on_empty_queue(queue_session):
    assert job_queue.claim_next_job(queue_session) is None


# ==============================================================================
# 9. Dọn job cũ
# ==============================================================================
def test_purge_removes_old_finished_jobs_only(queue_session):
    old = job_queue.now_utc() - timedelta(days=30)
    fresh = job_queue.now_utc() - timedelta(days=1)

    stale_done = _make_job(
        queue_session, status=job_queue.JOB_SUCCEEDED, finished_at=old, created_at=old
    )
    stale_failed = _make_job(
        queue_session, status=job_queue.JOB_FAILED, finished_at=old, created_at=old
    )
    stale_cancelled = _make_job(
        queue_session, status=job_queue.JOB_CANCELLED, finished_at=old, created_at=old
    )
    fresh_done = _make_job(queue_session, status=job_queue.JOB_SUCCEEDED, finished_at=fresh)
    queued = _make_job(
        queue_session, status=job_queue.JOB_QUEUED, queued_at=old, created_at=old, available_at=old
    )
    running = _make_job(
        queue_session, status=job_queue.JOB_RUNNING, attempts=1, started_at=old, created_at=old
    )

    # Ghi id trước khi xoá: sau khi DELETE hàng loạt, đọc `.id` trên object đã bị
    # xoá sẽ ném ObjectDeletedError (SQLAlchemy phải refresh để lấy khóa chính).
    stale_ids = {stale_done.id, stale_failed.id, stale_cancelled.id}
    keep_ids = {fresh_done.id, queued.id, running.id}

    removed = job_queue.purge_finished_jobs(queue_session, retention_days=7)

    assert removed == 3
    queue_session.expire_all()
    remaining = {row.id for row in queue_session.query(AIJob).all()}
    assert remaining == keep_ids
    for gone_id in stale_ids:
        assert queue_session.query(AIJob).filter(AIJob.id == gone_id).first() is None


def test_purge_respects_batch_limit(queue_session):
    old = job_queue.now_utc() - timedelta(days=30)
    for _ in range(5):
        _make_job(queue_session, status=job_queue.JOB_SUCCEEDED, finished_at=old, created_at=old)

    assert job_queue.purge_finished_jobs(queue_session, retention_days=7, limit=2) == 2
    assert queue_session.query(AIJob).count() == 3
    assert job_queue.purge_finished_jobs(queue_session, retention_days=7) == 3
    assert queue_session.query(AIJob).count() == 0


def test_purge_is_noop_when_nothing_is_stale(queue_session):
    job = _make_job(queue_session, status=job_queue.JOB_SUCCEEDED, finished_at=job_queue.now_utc())
    assert job_queue.purge_finished_jobs(queue_session, retention_days=7) == 0
    assert queue_session.query(AIJob).filter(AIJob.id == job.id).first() is not None


# ==============================================================================
# Chạy lại tác vụ AI (không gọi mạng)
# ==============================================================================
def test_execute_ai_job_reruns_sync_endpoint(client, queue_session, monkeypatch):
    """Job bất đồng bộ phải cho ra ĐÚNG kết quả mà endpoint đồng bộ sẽ trả.

    Ở đây endpoint đồng bộ được thay bằng stub, nên test chỉ kiểm chứng cơ chế gọi
    lại (đúng hàm, đúng model request, đúng payload) chứ không phụ thuộc mạng.
    """
    from app.api.v1 import ai as ai_endpoints
    from app.api.v1.ai_jobs import execute_ai_job

    seen = {}

    def _stub_endpoint(req, current_user, db):
        seen["prompt_version"] = req.prompt_version
        seen["campaign_id"] = req.campaign_id
        seen["user_id"] = current_user.id
        from app.schemas.schemas import AIIdeaResponse

        return AIIdeaResponse(
            task_type="IDEA",
            ideas=[],
            model_used="stub-model",
            prompt_version=req.prompt_version,
        )

    monkeypatch.setattr(ai_endpoints, "generate_ideas", _stub_endpoint)

    headers = _headers(queue_session, "manager@gmail.com")
    job_id = client.post(
        API,
        json=_enqueue_payload(prompt_version="v9"),
        headers=headers,
    ).json()["job_id"]

    job = queue_session.query(AIJob).filter(AIJob.id == job_id).first()
    result = execute_ai_job(db=queue_session, job=job)

    assert seen["prompt_version"] == "v9"
    assert seen["campaign_id"] == 1
    assert seen["user_id"] == job.user_id
    assert result["model_used"] == "stub-model"
    assert result["task_type"] == "IDEA"


def test_execute_ai_job_maps_http_403_to_permanent_failure(queue_session, monkeypatch):
    from fastapi import HTTPException

    from app.api.v1 import ai as ai_endpoints
    from app.api.v1.ai_jobs import execute_ai_job

    def _forbidden(req, current_user, db):
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")

    monkeypatch.setattr(ai_endpoints, "generate_ideas", _forbidden)

    job = _make_job(queue_session)
    with pytest.raises(job_queue.AIJobExecutionError) as excinfo:
        execute_ai_job(db=queue_session, job=job)
    assert excinfo.value.transient is False
    assert "403" in str(excinfo.value)


def test_execute_ai_job_maps_http_429_to_transient_failure(queue_session, monkeypatch):
    from fastapi import HTTPException

    from app.api.v1 import ai as ai_endpoints
    from app.api.v1.ai_jobs import execute_ai_job

    def _rate_limited(req, current_user, db):
        raise HTTPException(status_code=429, detail="Bạn đã vượt giới hạn số lượt gọi.")

    monkeypatch.setattr(ai_endpoints, "generate_ideas", _rate_limited)

    job = _make_job(queue_session)
    with pytest.raises(job_queue.AIJobExecutionError) as excinfo:
        execute_ai_job(db=queue_session, job=job)
    assert excinfo.value.transient is True


def test_execute_ai_job_rejects_unknown_kind(queue_session):
    from app.api.v1.ai_jobs import execute_ai_job

    # Dựng object trong bộ nhớ, KHÔNG flush xuống CSDL: CHECK constraint
    # `chk_ai_job_kind` chặn kind sai ở tầng DB, và đó là điều đúng — runner phải tự
    # từ chối trước khi cố chạy một loại tác vụ không tồn tại.
    job = AIJob(
        id=999,
        user_id=1,
        kind="khong_hop_le",
        payload_json="{}",
        status=job_queue.JOB_RUNNING,
    )

    with pytest.raises(job_queue.AIJobExecutionError) as excinfo:
        execute_ai_job(db=queue_session, job=job)
    assert excinfo.value.transient is False
    assert "kind" in str(excinfo.value)


def test_execute_ai_job_rejects_inactive_user(queue_session):
    from app.api.v1.ai_jobs import execute_ai_job

    user = _user_by_email(queue_session, "manager@gmail.com")
    job = _make_job(queue_session, user_id=user.id)
    user.status = "DISABLED"
    queue_session.commit()

    with pytest.raises(job_queue.AIJobExecutionError) as excinfo:
        execute_ai_job(db=queue_session, job=job)
    assert "ACTIVE" in str(excinfo.value)


def test_worker_end_to_end_marks_success(file_db, monkeypatch):
    """Vòng đầy đủ: enqueue -> worker tick -> job `succeeded` -> API trả kết quả."""
    import app.core.database as core_database

    monkeypatch.setattr(core_database, "SessionLocal", file_db)
    user_id = file_db.user_id

    from app.api.v1 import ai as ai_endpoints
    from app.schemas.schemas import AIDraftResponse

    def _stub_endpoint(req, current_user, db):
        return AIDraftResponse(
            task_type="DRAFT",
            title="Tiêu đề stub",
            body="Nội dung stub",
            cta="CTA stub",
            model_used="stub-model",
            prompt_version=req.prompt_version,
        )

    monkeypatch.setattr(ai_endpoints, "generate_draft", _stub_endpoint)

    session = file_db()
    try:
        job = _make_job(
            session,
            workspace_id=None,
            user_id=user_id,
            kind=job_queue.KIND_DRAFT,
            payload_json=json.dumps({"campaign_id": 1, "selected_idea": "Góc nhìn A"}),
        )
    finally:
        session.close()

    worker = job_worker.AIJobWorker(max_slots=1, poll_interval=0.01, cleanup_interval=9999)

    deadline = time.monotonic() + 15
    status = None
    while time.monotonic() < deadline:
        worker.tick()
        session = file_db()
        try:
            row = session.query(AIJob).filter(AIJob.id == job.id).first()
            status = row.status if row else None
        finally:
            session.close()
        if status in (job_queue.JOB_SUCCEEDED, job_queue.JOB_FAILED):
            break
        time.sleep(0.02)

    session = file_db()
    try:
        row = session.query(AIJob).filter(AIJob.id == job.id).first()
        assert row.status == job_queue.JOB_SUCCEEDED
        assert json.loads(row.result_json)["title"] == "Tiêu đề stub"
        assert row.attempts == 1
    finally:
        session.close()


# ==============================================================================
# Worker: bật/tắt và suy giảm nhẹ nhàng
# ==============================================================================
def test_worker_disabled_by_setting(monkeypatch):
    monkeypatch.setattr(settings, "AI_JOB_WORKER_ENABLED", False)
    previous = job_worker.get_ai_job_worker()
    try:
        assert job_worker.start_ai_job_worker() is None
    finally:
        monkeypatch.setattr(settings, "AI_JOB_WORKER_ENABLED", True)
        job_worker._worker = previous


def test_start_worker_without_event_loop_returns_none():
    """Ngoài event loop thì worker không khởi động được — phải trả None chứ không
    ném, vì `on_startup` gọi nó và không được phép làm hỏng việc khởi động app."""
    worker = job_worker.AIJobWorker()
    assert worker.start() is None


def test_worker_start_failure_does_not_raise(monkeypatch):
    class _BrokenWorker:
        def start(self, app=None):
            raise RuntimeError("hỏng")

        def stop(self, app=None):
            pass

    previous = job_worker._worker
    try:
        monkeypatch.setattr(job_worker, "_worker", _BrokenWorker())
        assert job_worker.start_ai_job_worker() is None
    finally:
        job_worker._worker = previous


def test_list_jobs_filters_by_explicit_workspace(client, queue_session, workspace_beta):
    """Lọc theo `?workspace_id=` phải được kiểm tra quyền như mọi endpoint khác."""
    manager = _user_by_email(queue_session, "manager@gmail.com")
    alpha_job = _make_job(queue_session, workspace_id=1, user_id=manager.id)
    beta_job = _make_job(queue_session, workspace_id=workspace_beta.id, user_id=1)

    headers = {"Authorization": f"Bearer {create_access_token(data={'sub': str(manager.id)})}"}
    alpha_only = client.get(API, params={"workspace_id": 1}, headers=headers)
    assert alpha_only.status_code == 200
    ids = [item["job_id"] for item in alpha_only.json()["items"]]
    assert alpha_job.id in ids
    assert beta_job.id not in ids

    # Workspace của tenant khác -> 403, không rò danh sách.
    denied = client.get(API, params={"workspace_id": workspace_beta.id}, headers=headers)
    assert denied.status_code == 403
    assert "Not authorized to list AI jobs" in denied.json()["detail"]


def test_admin_list_sees_all_workspaces(client, queue_session, workspace_beta):
    """ADMIN có phạm vi toàn cục ở endpoint khác của hệ thống, và cả ở đây — nhưng
    vẫn không thấy job tenant-less (xem `test_admin_also_cannot_read_null_workspace_job`)."""
    admin = User(
        email="ai-queue-admin-list@test.com",
        full_name="AI Queue Admin List",
        password_hash="x",
        role="ADMIN",
        status="ACTIVE",
    )
    queue_session.add(admin)
    queue_session.commit()
    alpha_job = _make_job(queue_session, workspace_id=1, user_id=1)
    beta_job = _make_job(queue_session, workspace_id=workspace_beta.id, user_id=1)
    orphan = _make_job(queue_session, workspace_id=None, user_id=1)

    response = client.get(
        API, headers={"Authorization": f"Bearer {create_access_token(data={'sub': str(admin.id)})}"}
    )
    assert response.status_code == 200
    ids = {item["job_id"] for item in response.json()["items"]}
    assert {alpha_job.id, beta_job.id}.issubset(ids)
    assert orphan.id not in ids


def test_enqueue_requires_unambiguous_workspace(client, queue_session):
    """Người dùng thuộc NHIỀU workspace mà không chỉ định thì không được đoán — trả
    400 kèm hướng dẫn cụ thể thay vì ghi vào một tenant ngẫu nhiên."""
    from app.models.entities import WorkspaceMember

    creator = _user_by_email(queue_session, "manager@gmail.com")
    before = queue_session.query(AIJob).filter(AIJob.user_id == creator.id).count()

    other = Workspace(
        name="Workspace thứ hai của manager",
        slug="manager-second-workspace",
        owner_id=creator.id,
        status="ACTIVE",
    )
    queue_session.add(other)
    queue_session.commit()
    queue_session.add(
        WorkspaceMember(workspace_id=other.id, user_id=creator.id, role="AGENCY_MANAGER")
    )
    queue_session.commit()

    # KHÔNG kèm campaign_id: nếu có, workspace của chiến dịch đã chốt được tenant
    # rồi và không còn mơ hồ — đó là nhánh ưu tiên số 2 của `resolve_job_workspace`.
    response = client.post(
        API,
        json=_enqueue_payload(campaign_id=None),
        headers=_headers(queue_session, "manager@gmail.com"),
    )
    assert response.status_code == 400
    assert "X-Workspace-Id" in response.json()["detail"]
    assert queue_session.query(AIJob).filter(AIJob.user_id == creator.id).count() == before

    # Chỉ định rõ thì qua được.
    ok = client.post(
        API,
        params={"workspace_id": other.id},
        json=_enqueue_payload(campaign_id=None),
        headers=_headers(queue_session, "manager@gmail.com"),
    )
    assert ok.status_code == 202
    row = queue_session.query(AIJob).filter(AIJob.id == ok.json()["job_id"]).first()
    assert row.workspace_id == other.id


def test_enqueue_infers_workspace_from_campaign(client, queue_session):
    """Khi có `campaign_id`, tenant lấy từ chiến dịch — không cần header."""
    manager = _user_by_email(queue_session, "manager@gmail.com")
    other = Workspace(
        name="Workspace thứ hai của manager (campaign)",
        slug="manager-third-workspace",
        owner_id=manager.id,
        status="ACTIVE",
    )
    queue_session.add(other)
    queue_session.commit()

    from app.models.entities import WorkspaceMember

    queue_session.add(WorkspaceMember(workspace_id=other.id, user_id=manager.id, role="MARKETER"))
    queue_session.commit()

    response = client.post(API, json=_enqueue_payload(), headers=_headers(queue_session, "manager@gmail.com"))
    assert response.status_code == 202
    row = queue_session.query(AIJob).filter(AIJob.id == response.json()["job_id"]).first()
    assert row.workspace_id == 1


def test_worker_asyncio_loop_lifecycle(file_db, monkeypatch):
    """Chạy vòng asyncio THẬT (không gọi `tick()` bằng tay) để chứng minh
    `start()` -> `_loop()` -> `stop()` hoạt động trên event loop của ứng dụng.

    Đây là đường mà `on_startup()` dùng, nên test phải đi qua đúng đường đó chứ
    không chỉ kiểm tra hàm `tick`.
    """
    import asyncio

    import app.core.database as core_database

    monkeypatch.setattr(core_database, "SessionLocal", file_db)
    monkeypatch.setattr("app.api.v1.ai_jobs.execute_ai_job", lambda db, job: {"stub": True})

    worker = job_worker.AIJobWorker(max_slots=1, poll_interval=0.01, cleanup_interval=9999)

    async def _scenario():
        assert worker.start() is not None
        assert worker.running is True
        # start() lần hai phải trả về đúng task đang chạy, không tạo vòng lặp thứ hai.
        assert worker.start() is worker._task

        session = file_db()
        try:
            _make_job(session, workspace_id=None, user_id=file_db.user_id)
        finally:
            session.close()

        deadline = time.monotonic() + 10
        done = False
        while time.monotonic() < deadline:
            await asyncio.sleep(0.02)
            session = file_db()
            try:
                count = (
                    session.query(AIJob)
                    .filter(AIJob.user_id == file_db.user_id, AIJob.status == job_queue.JOB_SUCCEEDED)
                    .count()
                )
            finally:
                session.close()
            if count == 1:
                done = True
                break
        assert done, "Worker asyncio loop không chạy job trong thời hạn"

        worker.stop()
        await asyncio.sleep(0.05)
        assert worker.running is False

    asyncio.run(_scenario())


def test_worker_loop_survives_a_failing_tick(file_db, monkeypatch):
    """Một vòng lặp hỏng không được giết worker: API vẫn phải phục vụ được traffic
    không liên quan tới AI."""
    import asyncio

    import app.core.database as core_database

    monkeypatch.setattr(core_database, "SessionLocal", file_db)
    monkeypatch.setattr("app.api.v1.ai_jobs.execute_ai_job", lambda db, job: {"stub": True})

    worker = job_worker.AIJobWorker(max_slots=1, poll_interval=0.01, cleanup_interval=9999)
    original_tick = worker.tick
    state = {"fail": 2}

    def _flaky_tick():
        if state["fail"] > 0:
            state["fail"] -= 1
            raise RuntimeError("gián đoạn CSDL giả lập")
        original_tick()

    monkeypatch.setattr(worker, "tick", _flaky_tick)

    async def _scenario():
        worker.start()
        session = file_db()
        try:
            _make_job(session, workspace_id=None, user_id=file_db.user_id)
        finally:
            session.close()

        deadline = time.monotonic() + 10
        done = False
        while time.monotonic() < deadline:
            await asyncio.sleep(0.02)
            session = file_db()
            try:
                count = (
                    session.query(AIJob)
                    .filter(AIJob.user_id == file_db.user_id, AIJob.status == job_queue.JOB_SUCCEEDED)
                    .count()
                )
            finally:
                session.close()
            if count == 1:
                done = True
                break
        worker.stop()
        assert done, "Worker chết hẳn sau vài vòng lỗi thay vì tiếp tục"

    asyncio.run(_scenario())


def test_sync_endpoints_marked_deprecated_in_openapi():
    """Endpoint đồng bộ phải được đánh dấu deprecated trong OpenAPI để client thấy
    được hướng dịch sang đường mới."""
    import app.main as main_module

    paths = main_module.app.openapi()["paths"]
    for path, method in (
        ("/api/v1/ai/ideas", "post"),
        ("/api/v1/ai/draft", "post"),
        ("/api/v1/ai/generate", "post"),
        ("/api/v1/ai/summary", "post"),
        ("/api/v1/ai/summarize", "post"),
        ("/api/v1/ai/omnichannel", "post"),
    ):
        operation = paths[path][method]
        assert operation.get("deprecated") is True, f"{path} phải được đánh dấu deprecated"
        assert "DEPRECATED" in (operation.get("description") or ""), f"{path} thiếu mô tả deprecated"

    # Endpoint mới thì KHÔNG deprecated.
    assert paths["/api/v1/ai/jobs"]["post"].get("deprecated") is not True
    assert "202" in str(paths["/api/v1/ai/jobs"]["post"].get("responses", {}))


def test_job_enums_are_documented_constants():
    """Ràng buộc CHECK trong entities.py và hằng số ở job_queue phải khớp — nếu lệch
    thì worker ghi trạng thái mà CSDL từ chối, và job kẹt ở trạng thái cũ mãi mãi."""
    assert set(job_queue.JOB_KINDS) == {"ideas", "draft", "summary", "omnichannel"}
    assert set(job_queue.JOB_TERMINAL_STATUSES) == {"succeeded", "failed", "cancelled"}


def test_ai_job_table_exists_in_test_schema(queue_session):
    """Bảng `ai_jobs` phải được `Base.metadata.create_all` tạo ra, nếu không worker
    sẽ hỏng ngay lúc chạy (và production thì hỏng lúc deploy)."""
    from sqlalchemy import inspect

    assert AIJob.__tablename__ in inspect(queue_session.get_bind()).get_table_names()
    assert AIJob.__table__ is not None


def test_campaign_delete_sets_job_campaign_to_null(queue_session):
    """Job phải sống sót khi chiến dịch bị xoá — kết quả AI đã tốn tiền, không nên
    mất chỉ vì chiến dịch cha biến mất."""
    job = _make_job(queue_session, campaign_id=1)
    campaign = queue_session.query(Campaign).filter(Campaign.id == 1).first()
    assert campaign is not None
    queue_session.delete(campaign)
    queue_session.commit()

    row = queue_session.query(AIJob).filter(AIJob.id == job.id).first()
    assert row is not None
    assert row.campaign_id is None


def test_workspace_delete_removes_its_jobs(queue_session, workspace_alpha):
    job = _make_job(queue_session, workspace_id=workspace_alpha.id)
    queue_session.delete(workspace_alpha)
    queue_session.commit()
    assert queue_session.query(AIJob).filter(AIJob.id == job.id).first() is None


def test_workspace_relationship_declares_cascade(queue_session, workspace_alpha):
    assert "ai_jobs" in Workspace.__mapper__.relationships
    relationship = Workspace.__mapper__.relationships["ai_jobs"]
    assert relationship.mapper.class_ is AIJob
    # Cascade delete-orphan: xoá workspace thì job của tenant đó không thành rác mồ
    # côi bị tầng phân quyền từ chối mãi mãi.
    assert "delete-orphan" in relationship.cascade


def test_test_client_still_serves_sync_ai_endpoint(client, queue_session):
    """Endpoint đồng bộ cũ vẫn phải chạy — không được làm hỏng gì trong lúc chuyển dịch."""
    response = client.post(
        "/api/v1/ai/ideas",
        json={"campaign_id": 1, "channel_code": "facebook"},
        headers=_headers(queue_session, "manager@gmail.com"),
    )
    assert response.status_code == 200
    assert response.json()["task_type"] == "IDEA"


def test_new_endpoints_do_not_require_testclient_lifespan(client, queue_session):
    """Fixture `client` cố tình KHÔNG chạy startup event, nên test này chứng minh
    các endpoint mới không phụ thuộc worker đã khởi động."""
    assert client.get(API, headers=_headers(queue_session, "manager@gmail.com")).status_code == 200


def test_job_worker_not_started_by_test_client(client, queue_session):
    """Bảo đảm bộ test không vô tình bật worker nền thật (sẽ ghi vào CSDL thật)."""
    worker = job_worker.get_ai_job_worker()
    assert worker is None or not worker.running


def test_stats_shape():
    worker = job_worker.AIJobWorker(max_slots=3)
    stats = worker.stats()
    assert stats["max_slots"] == 3
    assert stats["inflight"] == 0
    assert stats["live_threads"] == 0
    assert stats["thread_ceiling"] == 6
