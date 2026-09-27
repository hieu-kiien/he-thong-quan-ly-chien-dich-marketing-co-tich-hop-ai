"""Regression tests for the background scheduler worker (M1 concurrency hardening).

Two production defects are covered here:

1. ``_scheduler_loop`` used to call ``process_due_schedules()`` inline inside the
   asyncio event loop. That function is pure blocking DB I/O (SELECT + UPDATE +
   COMMIT), so every 20 seconds the whole event loop was frozen and no HTTP
   request could be served until the DB round-trip finished.
2. ``process_due_schedules()`` had no cross-process guard. With two replicas
   (two Render instances / two Cloudflare containers) on the same database both
   replicas read the same ``PLANNED`` row and both published the same content.
   The fix is a lease: a single conditional ``UPDATE ... WHERE status = 'PLANNED'``
   that moves the row to ``EXECUTED``. Only the worker that gets ``rowcount == 1``
   is allowed to publish the content.

Every test drives the real worker against the real (in-memory, FK + CHECK enforced)
SQLite database provided by ``conftest.db_session``. Parsing, the lease and the
publishing are not mocked: removing the conditional claim UPDATE makes
``test_claim_is_a_conditional_update_not_a_blind_write``,
``test_claim_guard_skips_schedule_already_taken_by_another_worker`` and
``test_claim_guard_respects_rival_cancellation`` fail.
"""

import asyncio
import contextlib
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import pytest
from sqlalchemy import event as sa_event
from sqlalchemy.orm import Session, sessionmaker

from app.models.entities import MarketingContent, MarketingSchedule
from app.services.scheduler import worker
from app.services.scheduler.worker import VN_TIMEZONE


# ==============================================================================
# HELPERS
# ==============================================================================
def _make_content(db: Session, status: str, title: str) -> MarketingContent:
    """Tạo MarketingContent với status chỉ định (workspace/campaign/channel/user lấy từ seed)."""
    content = MarketingContent(
        workspace_id=1,
        campaign_id=1,
        channel_id=1,
        created_by=1,
        title=title,
        body=f"Body of {title}",
        cta="Xem ngay",
        status=status,
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    return content


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _make_schedule(
    db: Session,
    content_id: int,
    scheduled_at: str,
    status: str = "PLANNED",
) -> MarketingSchedule:
    schedule = MarketingSchedule(
        content_id=content_id,
        scheduled_at=scheduled_at,
        timezone="Asia/Ho_Chi_Minh",
        status=status,
        created_by=1,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def _reload(db: Session, model, obj_id: int):
    """Đọc lại hàng từ DB (expire identity map) để kết luận dựa trên dữ liệu đã commit."""
    db.expire_all()
    return db.get(model, obj_id)


def _other_replica_session(db: Session) -> Session:
    """Session thứ hai trên cùng engine test -> mô phỏng connection của replica khác."""
    conftest_module = sys.modules.get("conftest")
    if conftest_module is None:
        import conftest as conftest_module  # type: ignore[import-not-found]
    factory = getattr(conftest_module, "TestingSessionLocal", None)
    if factory is not None:
        return factory()
    return sessionmaker(autocommit=False, autoflush=False, bind=db.get_bind())()


@contextlib.contextmanager
def _capture_sql(db: Session):
    """Gom (statement, bound parameters) của mọi câu SQL thật gửi tới engine."""
    records: List[Tuple[str, object]] = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        records.append((" ".join(statement.split()), parameters))

    engine = db.get_bind()
    sa_event.listen(engine, "before_cursor_execute", _record)
    try:
        yield records
    finally:
        sa_event.remove(engine, "before_cursor_execute", _record)


def _params(parameters: object) -> List[str]:
    if parameters is None:
        return []
    if isinstance(parameters, (list, tuple)):
        return [str(p) for p in parameters]
    return [str(parameters)]


# ==============================================================================
# TEST 1 - IDEMPOTENCY (regression quan trọng nhất)
# ==============================================================================
def test_process_due_schedules_is_idempotent(db_session: Session):
    """Gọi process_due_schedules() hai lần liên tiếp: lần 2 phải là no-op.

    Lần 1: lịch đến hạn được claim, chuyển EXECUTED, publish nội dung APPROVED.
    Lần 2: không còn lịch PLANNED đến hạn nào => list rỗng, không publish lại.
    """
    content = _make_content(db_session, status="APPROVED", title="Idempotent Post")
    schedule = _make_schedule(
        db_session,
        content_id=content.id,
        scheduled_at=_iso(datetime.now(VN_TIMEZONE) - timedelta(hours=1)),
    )
    schedule_id, content_id = schedule.id, content.id

    # --- Vong 1: phai xu ly ---
    first_run = worker.process_due_schedules(db_session)
    assert first_run == [schedule_id], f"Vong 1 phai xu ly lich, nhan duoc {first_run}"

    assert _reload(db_session, MarketingSchedule, schedule_id).status == "EXECUTED"
    assert _reload(db_session, MarketingContent, content_id).status == "PUBLISHED"

    # --- Vong 2: phai rong tuyet doi ---
    second_run = worker.process_due_schedules(db_session)
    assert second_run == [], f"Vong 2 phai rong, nhan duoc {second_run}"

    # Trang thai sau vong 2 khong doi
    assert _reload(db_session, MarketingSchedule, schedule_id).status == "EXECUTED"
    assert _reload(db_session, MarketingContent, content_id).status == "PUBLISHED"


# ==============================================================================
# TEST 2 - CHI PUBLISH NOI DUNG DA DUOC DUYET
# ==============================================================================
def test_process_due_schedules_publishes_only_approved_content(db_session: Session):
    """Lịch đến hạn chỉ được publish nội dung APPROVED; DRAFT phải giữ nguyên DRAFT."""
    approved_content = _make_content(db_session, status="APPROVED", title="Approved Post")
    draft_content = _make_content(db_session, status="DRAFT", title="Draft Post")
    past = _iso(datetime.now(VN_TIMEZONE) - timedelta(minutes=30))

    approved_schedule = _make_schedule(db_session, approved_content.id, past)
    draft_schedule = _make_schedule(db_session, draft_content.id, past)

    processed = worker.process_due_schedules(db_session)

    # Ca hai lich deu den han va deu duoc claim -> vao processed
    assert sorted(processed) == sorted([approved_schedule.id, draft_schedule.id])

    # APPROVED -> PUBLISHED
    assert _reload(db_session, MarketingContent, approved_content.id).status == "PUBLISHED"
    assert _reload(db_session, MarketingSchedule, approved_schedule.id).status == "EXECUTED"

    # DRAFT -> van DRAFT (du lich cua no da chay)
    assert _reload(db_session, MarketingContent, draft_content.id).status == "DRAFT"
    assert _reload(db_session, MarketingSchedule, draft_schedule.id).status == "EXECUTED"


# ==============================================================================
# TEST 3 - EVENT LOOP KHONG BI CHAN (asyncio.to_thread)
# ==============================================================================
def test_scheduler_loop_does_not_block_event_loop(monkeypatch: pytest.MonkeyPatch):
    """_scheduler_loop phai chay phan blocking qua asyncio.to_thread.

    Khong dua tren so doo "co ve nhanh": ham DB bi thay bang mot ham dong bo ngu
    0.3s tu ghi lai thread da chay no. Neu worker goi truc tiep trong event loop
    thi thread ident se trung thread chinh; neu qua to_thread thi khac. Them mot
    coroutine "ticker" chay song song de chung minh event loop van duoc xoay vong
    trong luc DB I/O dien ra.
    """
    main_ident = threading.get_ident()
    entered = threading.Event()
    observed: dict = {"ident": None, "calls": 0}

    def fake_process_due_schedules() -> List[int]:
        observed["calls"] += 1
        observed["ident"] = threading.get_ident()
        entered.set()
        time.sleep(0.3)  # blocking I/O gia lap (tuong duong query + commit)
        return []

    monkeypatch.setattr(worker, "process_due_schedules", fake_process_due_schedules)

    async def scenario():
        loop = asyncio.get_running_loop()
        ticks = 0
        stop_ticker = asyncio.Event()

        async def ticker():
            nonlocal ticks
            while not stop_ticker.is_set():
                await asyncio.sleep(0.005)
                ticks += 1

        ticker_task = asyncio.create_task(ticker())
        scheduler_task = asyncio.create_task(worker._scheduler_loop(interval_seconds=3600))
        try:
            # Cho (khong block event loop) toi khi ham DB duoc goi, kem timeout cung
            deadline = loop.time() + 10
            while not entered.is_set():
                if loop.time() > deadline:
                    pytest.fail("_scheduler_loop khong goi process_due_schedules trong 10s")
                await asyncio.sleep(0.005)

            # 1) Ham blocking chay o thread khac thread cua event loop
            assert observed["ident"] is not None, "process_due_schedules chua chay"
            assert observed["ident"] != main_ident, (
                "process_due_schedules chay tren thread chinh cua event loop "
                f"(ident={observed['ident']}) -> se chan toan bo HTTP traffic, "
                "phai chay qua asyncio.to_thread."
            )

            # 2) Event loop van song trong luc ham DB ngu 0.3s
            ticks_before = ticks
            await asyncio.sleep(0.35)
            assert ticks - ticks_before >= 5, (
                f"Event loop bi chan: chi {ticks - ticks_before} vong lap trong 0.35s "
                "trong khi process_due_schedules dang chay."
            )
        finally:
            stop_ticker.set()
            ticker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.wait_for(ticker_task, timeout=5)

            scheduler_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                # wait_for bao dam test khong treo du scheduler loop co loi
                await asyncio.wait_for(scheduler_task, timeout=10)

        assert scheduler_task.done() or scheduler_task.cancelled()

    async def main():
        await asyncio.wait_for(scenario(), timeout=30)

    asyncio.run(main())
    assert observed["calls"] == 1, f"Vong lap scheduler phai chay dung 1 lan, thay {observed['calls']}"


# ==============================================================================
# TEST 4 - scheduled_at RAC KHONG LAM SAP TIEN TRINH
# ==============================================================================
def test_invalid_scheduled_at_is_skipped_not_fatal(db_session: Session):
    """scheduled_at khong parse duoc bi bo qua, lich giu PLANNED, worker khong raise."""
    bad_content = _make_content(db_session, status="APPROVED", title="Bad Date Post")
    good_content = _make_content(db_session, status="APPROVED", title="Good Date Post")

    bad_schedule = _make_schedule(db_session, bad_content.id, "KHONG_PHAI_NGAY_123")
    good_schedule = _make_schedule(
        db_session,
        good_content.id,
        _iso(datetime.now(VN_TIMEZONE) - timedelta(minutes=5)),
    )

    processed = worker.process_due_schedules(db_session)  # khong raise du co du lieu rac

    assert processed == [good_schedule.id], f"Chi lich hop le duoc xu ly, nhan duoc {processed}"
    assert _reload(db_session, MarketingContent, good_content.id).status == "PUBLISHED"
    assert _reload(db_session, MarketingSchedule, good_schedule.id).status == "EXECUTED"

    assert _reload(db_session, MarketingSchedule, bad_schedule.id).status == "PLANNED"
    assert _reload(db_session, MarketingContent, bad_content.id).status == "APPROVED"


# ==============================================================================
# TEST 5 - LEASE / CLAIM: CHONG XU LY TRUNG GIUA CAC REPLICA
# ==============================================================================
def test_claim_is_a_conditional_update_not_a_blind_write(db_session: Session):
    """Lease phai la UPDATE co dieu kien tren chinh status, thuc thi that tren DB.

    Neu ai do go co che claim va quay lai gan `schedule.status = "EXECUTED"` qua
    ORM, cau SQL chi con `UPDATE ... SET status=? WHERE id=?` (khong co dieu kien
    status) -> test nay fail.
    """
    content = _make_content(db_session, status="APPROVED", title="Conditional Claim Post")
    schedule = _make_schedule(
        db_session,
        content.id,
        _iso(datetime.now(VN_TIMEZONE) - timedelta(hours=2)),
    )
    schedule_id = schedule.id

    with _capture_sql(db_session) as records:
        processed = worker.process_due_schedules(db_session)

    assert processed == [schedule_id]

    claims = []
    for sql, parameters in records:
        upper = sql.upper()
        if not upper.startswith("UPDATE MARKETING_SCHEDULES SET STATUS"):
            continue
        where_clause = upper.split("WHERE", 1)[1] if "WHERE" in upper else ""
        values = _params(parameters)
        if "ID = ?" in where_clause and "STATUS = ?" in where_clause and "PLANNED" in values:
            claims.append((sql, values))

    assert claims, (
        "Khong tim thay UPDATE co dieu kien (WHERE id = ? AND status = 'PLANNED') tren "
        f"marketing_schedules. Neu worker chi gan status qua ORM thi thieu co che lease. "
        f"Cac cau lenh da chay: {[r[0] for r in records]}"
    )
    assert claims[0][1][0] == "EXECUTED", (
        f"UPDATE phai chuyen status sang EXECUTED, nhan duoc {claims[0][1][0]!r}"
    )


def test_claim_guard_skips_schedule_already_taken_by_another_worker(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
):
    """Replica thu hai phai BO QUA lich da bi replica thu nhat nam lease.

    Mo phong dung race that tren production: SELECT cua worker da doc duoc hang
    'PLANNED', nhung truoc khi no kip claim thi worker khac ( tren connection khac)
    da commit 'EXECUTED'. Worker nay phai nhan rowcount = 0 o cau UPDATE co dieu
    kien va bo qua: khong publish, khong bao id da xu ly.
    Diem moc noi nam o parse_scheduled_datetime (duoc goi giua SELECT va claim);
    ham goc van chay that, ta chi chen them UPDATE cua "worker doi thu".
    """
    content = _make_content(db_session, status="APPROVED", title="Rival Worker Post")
    schedule = _make_schedule(
        db_session,
        content.id,
        _iso(datetime.now(VN_TIMEZONE) - timedelta(minutes=10)),
    )
    schedule_id, content_id = schedule.id, content.id

    real_parse = worker.parse_scheduled_datetime
    rival_claimed = {"done": False}

    def parse_then_rival_claims(value: str, tz_name: Optional[str] = None):
        if not rival_claimed["done"]:
            rival_claimed["done"] = True
            rival = _other_replica_session(db_session)
            try:
                rival.query(MarketingSchedule).filter(
                    MarketingSchedule.id == schedule_id,
                    MarketingSchedule.status == "PLANNED",
                ).update({"status": "EXECUTED"}, synchronize_session=False)
                rival.commit()
            finally:
                rival.close()
        return real_parse(value, tz_name)

    monkeypatch.setattr(worker, "parse_scheduled_datetime", parse_then_rival_claims)

    processed = worker.process_due_schedules(db_session)

    assert rival_claimed["done"], "Test khong chup duoc race (parse wrapper khong chay)"
    assert processed == [], (
        f"Worker thu hai da xu ly trung lich {processed}; phai bo qua vi lease da bi giu"
    )
    assert _reload(db_session, MarketingSchedule, schedule_id).status == "EXECUTED"
    assert _reload(db_session, MarketingContent, content_id).status == "APPROVED", (
        "Noi dung bi publish boi worker khong so huu lease"
    )


def test_claim_guard_respects_rival_cancellation(db_session: Session, monkeypatch: pytest.MonkeyPatch):
    """Neu hang khong con 'PLANNED' (bi CANCELLED) thi worker khong duoc publish."""
    content = _make_content(db_session, status="APPROVED", title="Rival Cancel Post")
    schedule = _make_schedule(
        db_session,
        content.id,
        _iso(datetime.now(VN_TIMEZONE) - timedelta(minutes=10)),
    )
    schedule_id, content_id = schedule.id, content.id

    real_parse = worker.parse_scheduled_datetime
    rival_cancelled = {"done": False}

    def parse_then_rival_cancels(value: str, tz_name: Optional[str] = None):
        if not rival_cancelled["done"]:
            rival_cancelled["done"] = True
            rival = _other_replica_session(db_session)
            try:
                rival.query(MarketingSchedule).filter(
                    MarketingSchedule.id == schedule_id,
                ).update({"status": "CANCELLED"}, synchronize_session=False)
                rival.commit()
            finally:
                rival.close()
        return real_parse(value, tz_name)

    monkeypatch.setattr(worker, "parse_scheduled_datetime", parse_then_rival_cancels)

    processed = worker.process_due_schedules(db_session)

    assert processed == []
    assert _reload(db_session, MarketingSchedule, schedule_id).status == "CANCELLED"
    assert _reload(db_session, MarketingContent, content_id).status == "APPROVED"


def test_two_replicas_never_publish_same_content_twice(db_session: Session):
    """Hai luot worker (mo phong 2 replica) tren cung DB: chi 1 luot duoc xu ly.

    Replica B nap hang vao identity map TRUOC khi replica A xu ly, nen session cua B
    mang snapshot 'PLANNED' cu - dung trang thai khi hai replica cung doc duoc hang
    cung luc tren production. Replica B phai khong xu ly lai va khong publish lai.
    """
    content = _make_content(db_session, status="APPROVED", title="Two Replica Post")
    schedule = _make_schedule(
        db_session,
        content.id,
        _iso(datetime.now(VN_TIMEZONE) - timedelta(minutes=20)),
    )
    schedule_id, content_id = schedule.id, content.id

    replica_b = _other_replica_session(db_session)
    try:
        stale_row = replica_b.query(MarketingSchedule).filter(
            MarketingSchedule.id == schedule_id
        ).first()
        assert stale_row is not None and stale_row.status == "PLANNED"

        replica_a_result = worker.process_due_schedules(db_session)
        replica_b.expire_all()
        replica_b_result = worker.process_due_schedules(replica_b)
    finally:
        replica_b.close()

    assert replica_a_result == [schedule_id]
    assert replica_b_result == [], "Replica thu hai xu ly trung lich da duoc xu ly"
    assert _reload(db_session, MarketingSchedule, schedule_id).status == "EXECUTED"
    assert _reload(db_session, MarketingContent, content_id).status == "PUBLISHED"
