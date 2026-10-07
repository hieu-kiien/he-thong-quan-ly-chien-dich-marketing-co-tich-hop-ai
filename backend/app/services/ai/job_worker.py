"""Worker nền thực thi job AI — GIỚI HẠN SỐ JOB CHẠY ĐỒNG THỜI, CÓ THỜI HẠN CỨNG.

VÌ SAO CẦN, BẰNG SỐ ĐO
------------------------
* `/ai/omnichannel` đo mất 237 giây trên deployment thật (Render free: 512 MB RAM,
  0.1 CPU). Cloudflare Worker phía trước cắt ở ~100 giây -> `error code: 524`.
* Endpoint AI cũ là hàm `def` đồng bộ: mỗi lượt gọi giữ một thread của worker
  trong suốt thời gian chờ LLM. Vài lượt gọi đồng thời là đủ để bộ nhớ cạn và mọi
  route API thường bị bóp chết.

VÌ SAO KHÔNG DÙNG THƯ VIỆN HÀNG ĐỢI
------------------------------------
512 MB không chịu nổi thêm một tiến trình broker (xem app/services/jobs/queue.py).
Worker ở đây chỉ là một vòng asyncio + vài thread tự quản lý.

BA TRẤN BẢO VỆ BỘ NHỚ
----------------------
1. **Slot, giới hạn toàn tiến trình.** `SlotPool` đếm số job đang chạy; vòng lặp
   chỉ nhặt job khi còn slot trống (`AI_JOB_CONCURRENCY`, mặc định 2). Hàng đợi dồn
   bao nhiêu job cũng không sinh thêm việc chạy — phần dư nằm nguyên trong CSDL.
2. **Trần số thread.** Ngay cả khi một job quá hạn được đánh `failed` và buông slot,
   thread kẹt đó chưa chết được (Python không huỷ được thread). Số thread AI đang
   sống vì thế bị chặn cứng ở `2 * max_slots`: quá trần thì worker ngừng nhặt job,
   job mới nằm chờ trong hàng đợi thay vì làm cạn RAM.
3. **Thời hạn cứng.** `sweep_expired_jobs` đánh `failed` mọi job `running` quá hạn
   và `_release_timed_out_slots` buông đúng phiếu slot tương ứng. Job kẹt KHÔNG
   BAO GIỜ giữ slot vô hạn.

SỰ THẬT VỀ THREAD ĐÃ QUÁ HẠN (nói thẳng, không làm đẹp sự thật)
--------------------------------------------------------------
Python không huỷ được thread đang chạy. Sau khi watchdog đánh `failed` và buông
slot, thread kẹt vẫn có thể sống tới khi lời gọi HTTP tự hết giờ
(`AI_TIMEOUT_SECONDS`). Kết quả nó mang về sau đó bị LOẠI, vì mọi câu lệnh ghi
đều có điều kiện `status='running'` (`mark_succeeded` / `register_failure`).
Trong thực tế, trần `AI_TIMEOUT_SECONDS` của lớp gọi provider đã chặn việc này từ
trước; watchdog chỉ là lưới an toàn cuối cùng cho trường hợp tệ nhất.
"""

import asyncio
import logging
import threading
import time
from typing import Dict, Optional, Tuple

from sqlalchemy import update

from app.core.config import settings
from app.models.entities import AIJob
from app.services.jobs import queue as job_queue

logger = logging.getLogger("marketflow.ai_jobs.worker")


class _Slot:
    """Phiếu giữ một slot của worker, buông đúng MỘT lần.

    Cần vì khi một job quá hạn, slot được buông bởi watchdog trong khi thread thực
    thi vẫn còn sống và cuối cùng cũng sẽ tự `release` trong `finally`. Nếu cả hai
    cùng trừ thì bộ đếm slot lệch dần xuống âm và hạn mức song song bị nới lỏng
    dần — đúng thứ lớp bảo vệ bộ nhớ không được phép để xảy ra.
    """

    __slots__ = ("_pool", "_lock", "_released")

    def __init__(self, pool: "SlotPool"):
        self._pool = pool
        self._lock = threading.Lock()
        self._released = False

    @property
    def released(self) -> bool:
        return self._released

    def release(self) -> bool:
        """Trả phiếu về bộ đếm. `False` nghĩa là phiếu đã được trả trước đó."""
        with self._lock:
            if self._released:
                return False
            self._released = True
        self._pool.release_slot()
        return True


class SlotPool:
    """Bộ đếm số job AI đang chạy đồng thời TRONG TIẾN TRÌNH này.

    Cố ý là bộ đếm thuần trong bộ nhớ, không dùng `Semaphore`: watchdog phải buông
    được slot của một thread đang kẹt, mà thread kẹt thì không bao giờ tự trả phiếu.
    `try_acquire` không chặn — vòng lặp chỉ nhặt job khi còn chỗ, còn không thì chờ
    tới vòng sau.
    """

    def __init__(self, max_slots: int):
        self.max_slots = max(1, int(max_slots))
        self._cond = threading.Condition()
        self._inflight = 0
        self._live_threads = 0

    @property
    def inflight(self) -> int:
        with self._cond:
            return self._inflight

    @property
    def live_threads(self) -> int:
        with self._cond:
            return self._live_threads

    def try_acquire(self) -> bool:
        with self._cond:
            if self._inflight >= self.max_slots:
                return False
            self._inflight += 1
            return True

    def release_slot(self) -> None:
        with self._cond:
            self._inflight = max(0, self._inflight - 1)
            self._cond.notify_all()

    def thread_started(self) -> None:
        with self._cond:
            self._live_threads += 1

    def thread_finished(self) -> None:
        with self._cond:
            self._live_threads = max(0, self._live_threads - 1)
            self._cond.notify_all()

    def wait_for_capacity(self, timeout: float) -> None:
        """Chờ một slot trống, nhưng không quá `timeout` giây.

        Vì sao cần: nếu vòng lặp chỉ `try_acquire` rồi ngủ trọn một chu kỳ quét,
        một job xong sớm sẽ phải chờ tới vòng kế tiếp mới job kế tiếp chạy được.
        """
        deadline = time.monotonic() + max(float(timeout), 0.0)
        with self._cond:
            while self._inflight >= self.max_slots:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return
                self._cond.wait(timeout=remaining)


class AIJobWorker:
    """Vòng lặp nền: quét hàng đợi -> nhặt job -> chạy trong thread có giới hạn."""

    def __init__(
        self,
        *,
        max_slots: Optional[int] = None,
        poll_interval: Optional[float] = None,
        timeout_seconds: Optional[float] = None,
        cleanup_interval: Optional[float] = None,
        cleanup_batch: Optional[int] = None,
        max_attempts: Optional[int] = None,
    ):
        self.max_slots = int(max_slots if max_slots is not None else settings.AI_JOB_CONCURRENCY)
        self.poll_interval = float(
            poll_interval if poll_interval is not None else settings.AI_JOB_POLL_INTERVAL_SECONDS
        )
        self.timeout_seconds = float(
            timeout_seconds if timeout_seconds is not None else settings.AI_JOB_TIMEOUT_SECONDS
        )
        self.cleanup_interval = float(
            cleanup_interval if cleanup_interval is not None else settings.AI_JOB_CLEANUP_INTERVAL_SECONDS
        )
        self.cleanup_batch = int(
            cleanup_batch if cleanup_batch is not None else settings.AI_JOB_CLEANUP_BATCH
        )
        self.max_attempts = int(
            max_attempts if max_attempts is not None else settings.AI_JOB_MAX_ATTEMPTS
        )

        self.pool = SlotPool(self.max_slots)
        # Trần cứng cho số thread AI đang sống. Cao hơn `max_slots` để còn dư đường
        # thoát khi thread bị đánh dấu quá hạn nhưng chưa chết, nhưng vẫn là hằng
        # số: không có đường nào để số thread AI nhân lên vô hạn.
        self.thread_ceiling = max(2, self.max_slots * 2)

        self._lock = threading.Lock()
        self._slots_by_job: Dict[int, _Slot] = {}
        self._threads_by_job: Dict[int, threading.Thread] = {}
        self._stop = threading.Event()
        self._task: Optional[asyncio.Task] = None
        self._last_cleanup: float = 0.0
        self.processed_count = 0
        self.failed_count = 0
        self.timed_out_count = 0

    # ------------------------------------------------------------------
    # Vòng đời
    # ------------------------------------------------------------------
    def start(self, app=None) -> Optional[asyncio.Task]:
        if self._task is not None and not self._task.done():
            logger.warning("Worker AI job đã chạy; bỏ qua yêu cầu khởi động lại.")
            return self._task
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning(
                "Không tìm thấy event loop đang chạy nên worker AI job không được khởi "
                "động. Job đã enqueue vẫn nằm an toàn trong hàng đợi và sẽ chạy khi có "
                "tiến trình worker."
            )
            return None
        self._stop.clear()
        self._task = loop.create_task(self._loop())
        if app is not None:
            app.state.ai_job_worker_task = self._task
        logger.info(
            "Worker AI job đã khởi động (tối đa %d job đồng thời, timeout %.0fs, quét mỗi %.1fs).",
            self.max_slots, self.timeout_seconds, self.poll_interval,
        )
        return self._task

    def stop(self, app=None) -> None:
        self._stop.set()
        task = self._task
        if app is not None and hasattr(app.state, "ai_job_worker_task"):
            task = app.state.ai_job_worker_task
        if task is not None and not task.done():
            task.cancel()
        self._task = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    # ------------------------------------------------------------------
    # Vòng lặp
    # ------------------------------------------------------------------
    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                # `tick` là I/O blocking thuần tuý (SELECT/UPDATE/COMMIT). Gọi thẳng
                # ở đây sẽ giữ event loop trong suốt thời gian đó và đóng băng mọi
                # request HTTP, đúng cái lỗi mà `_scheduler_loop` đã ghi chú.
                await asyncio.to_thread(self.tick)
            except asyncio.CancelledError:
                logger.info("Worker AI job nhận tín hiệu dừng.")
                raise
            except Exception:
                # Một vòng lặp hỏng không được giết cả worker: API vẫn phải phục vụ
                # được mọi route không liên quan tới AI.
                logger.error("Vòng lặp worker AI job gặp lỗi; tiếp tục ở vòng sau.", exc_info=True)

            try:
                await asyncio.sleep(max(self.poll_interval, 0.01))
            except asyncio.CancelledError:
                logger.info("Worker AI job nhận tín hiệu dừng khi ngủ.")
                raise

    def tick(self) -> None:
        """Một vòng: quét quá hạn -> thu hồi thread -> dọn job cũ -> nhặt & chạy 1 job.

        Mỗi vòng nhặt TỐI ĐA một job, và chỉ khi đã NẮM được slot. Nhờ vậy "vượt
        trần" là không thể xảy ra: số job đang chạy không bao giờ vượt `max_slots`, dù
        hàng đợi có bao nhiêu job.

        Thứ tự cố ý là `nắm slot -> nhặt job`: nếu nhặt trước rồi mới nhắm slot thì
        giữa hai bước có khoảng trống mà job đã ở trạng thái `running` mà chưa có ai
        chạy, và nó phải chờ tới lúc watchdog dọn. Nắm slot trước thì vòng lặp chỉ
        nhặt job khi chắc chắn sẽ có chỗ để chạy.
        """
        timed_out = self._sweep_expired()
        if timed_out:
            self._release_timed_out_slots(timed_out)

        self._reap_threads()
        self._maybe_cleanup()

        if not self._has_capacity():
            self.pool.wait_for_capacity(self.poll_interval)
            return

        slot = _Slot(self.pool)
        if not self.pool.try_acquire():
            # `_has_capacity()` vừa nói còn chỗ nhưng `try_acquire` lại không được:
            # có tiến trình khác (hoặc một watchdog vừa buông slot) chen vào. Bỏ
            # qua vòng này, phần dư của hàng đợi vẫn nguyên.
            return

        job = self._claim()
        if job is None:
            slot.release()
            return

        self._spawn(job, slot)

    # ------------------------------------------------------------------
    # Chạy job
    # ------------------------------------------------------------------
    def _sweep_expired(self):
        db = _open_session()
        try:
            return job_queue.sweep_expired_jobs(db, self.timeout_seconds)
        except Exception:
            logger.warning("Quét job AI quá hạn thất bại; bỏ qua vòng này.", exc_info=True)
            return []
        finally:
            _close_session(db)

    def _claim(self) -> Optional[AIJob]:
        db = _open_session()
        try:
            return job_queue.claim_next_job(db)
        except Exception:
            logger.warning("Nhặt job AI thất bại; bỏ qua vòng này.", exc_info=True)
            return None
        finally:
            _close_session(db)

    def _spawn(self, job: AIJob, slot: _Slot) -> None:
        """Khởi chạy thread thực thi cho `job` với phiếu `slot` đã nắm sẵn.

        Ghi phiếu vào sổ TRƯỚC khi tạo thread: watchdog có thể quét ra job quá hạn
        ngay sau đó, và nó cần tìm thấy phiếu để buông slot.
        """
        job_id = int(job.id)
        self.pool.thread_started()

        def _runner():
            try:
                self._execute_job(job, slot)
            finally:
                # Dọn sổ theo thứ tự: trả phiếu TRƯỚC rồi mới xoá bản ghi, để một
                # watchdog chạy đồng thời luôn tìm thấy phiếu khi nó cần buông.
                slot.release()
                self.pool.thread_finished()
                with self._lock:
                    self._slots_by_job.pop(job_id, None)
                    self._threads_by_job.pop(job_id, None)

        thread = threading.Thread(
            target=_runner,
            name=f"marketflow-ai-job-{job_id}",
            daemon=True,
        )
        with self._lock:
            self._slots_by_job[job_id] = slot
            self._threads_by_job[job_id] = thread
        try:
            thread.start()
        except Exception:
            # Không tạo được thread (hết tài nguyên hệ thống chẳng hạn). Trả cả phiếu
            # lẫn job về hàng đợi, nếu không job sẽ kẹt ở `running` tới hết thời hạn.
            logger.error("Không tạo được thread cho AI job %s", job_id, exc_info=True)
            with self._lock:
                self._slots_by_job.pop(job_id, None)
                self._threads_by_job.pop(job_id, None)
            self.pool.thread_finished()
            slot.release()
            self._requeue_unstarted(job)

    def _execute_job(self, job: AIJob, slot: _Slot) -> None:
        job_id = int(job.id)
        db = None
        try:
            db = _open_session()
            # Import trễ: worker nằm ở tầng service còn `execute_ai_job` nằm ở tầng
            # API. Import trễ giữ cho module này không phụ thuộc tầng API khi nạp.
            from app.api.v1.ai_jobs import execute_ai_job

            result = execute_ai_job(db=db, job=job)
            job_queue.mark_succeeded(db, job_id, result)
            self.processed_count += 1
        except job_queue.AIJobExecutionError as exc:
            if slot.released:
                # Watchdog đã kịp đánh `failed` vì quá hạn: lỗi đến muộn, không ghi.
                logger.warning("AI job %s quá hạn, bỏ qua lỗi đến muộn: %s", job_id, exc)
            else:
                job_queue.register_failure(db, job_id, str(exc), transient=exc.transient)
                self.failed_count += 1
        except Exception as exc:  # noqa: BLE001 - không để thread chết âm thầm
            logger.error("AI job %s gặp lỗi không lường trước: %s", job_id, exc, exc_info=True)
            if db is not None and not slot.released:
                try:
                    job_queue.register_failure(
                        db, job_id, f"{type(exc).__name__}: {exc}", transient=False,
                    )
                except Exception:
                    logger.debug("Không ghi được lỗi cho AI job %s", job_id, exc_info=True)
            self.failed_count += 1
        finally:
            _close_session(db)

    def _requeue_unstarted(self, job: AIJob) -> None:
        """Trả một job vừa nhặt nhưng không kịp chạy về hàng đợi.

        Hoàn tác luôn `attempts` vì lượt thử chưa thực sự diễn ra — nếu không, một
        job bị hủy giữa đường sẽ mất lượt thử vô lý và có thể hết lượt trước khi
        được chạy đúng một lần.
        """
        db = _open_session()
        try:
            db.execute(
                update(AIJob)
                .where(AIJob.id == job.id, AIJob.status == job_queue.JOB_RUNNING)
                .values(
                    status=job_queue.JOB_QUEUED,
                    attempts=AIJob.attempts - 1,
                    started_at=None,
                    updated_at=job_queue.now_utc(),
                )
            )
            db.commit()
        except Exception:
            logger.debug("Không trả được AI job %s về hàng đợi", job.id, exc_info=True)
        finally:
            _close_session(db)

    # ------------------------------------------------------------------
    # Slot & thread
    # ------------------------------------------------------------------
    def _has_capacity(self) -> bool:
        return (
            self.pool.inflight < self.max_slots
            and self.pool.live_threads < self.thread_ceiling
        )

    def _release_timed_out_slots(self, job_ids) -> None:
        """Buông slot của các job vừa bị đánh quá hạn.

        Đây là chỗ hiện thực hoá "một job kẹt không bao giờ giữ slot vô hạn": watchdog
        đánh `failed` trong CSDL, còn ở đây nó trả phiếu về bộ đếm slot. Phiếu được
        đánh dấu đã buông nên khi thread kẹt cuối cùng thoát ra, `finally` của nó
        không trừ thêm một lần nữa.
        """
        with self._lock:
            slots: Tuple[_Slot, ...] = tuple(
                self._slots_by_job.get(int(job_id)) for job_id in job_ids
            )
        for slot in slots:
            if slot is not None and slot.release():
                self.timed_out_count += 1

    def _reap_threads(self) -> None:
        """Dọn bản ghi của thread đã kết thúc.

        Bình thường `finally` trong `_runner` đã tự dọn. Bước này là lưới an toàn cho
        trường hợp thread chết mà `finally` không chạy tới, vì bản ghi sót lại sẽ
        làm `live_threads` và `thread_ceiling` sai lệch so với thực tế.
        """
        with self._lock:
            dead = [
                job_id
                for job_id, thread in self._threads_by_job.items()
                if not thread.is_alive()
            ]
        for job_id in dead:
            with self._lock:
                slot = self._slots_by_job.pop(job_id, None)
                self._threads_by_job.pop(job_id, None)
            if slot is not None and slot.release():
                self.pool.thread_finished()

    def _maybe_cleanup(self) -> None:
        now = time.monotonic()
        if now - self._last_cleanup < self.cleanup_interval:
            return
        self._last_cleanup = now
        db = _open_session()
        try:
            job_queue.purge_finished_jobs(db, limit=self.cleanup_batch)
        except Exception:
            logger.warning("Dọn job AI cũ thất bại; bỏ qua vòng này.", exc_info=True)
        finally:
            _close_session(db)

    # ------------------------------------------------------------------
    # Trạng thái để chẩn đoán
    # ------------------------------------------------------------------
    def stats(self) -> Dict[str, int]:
        return {
            "max_slots": self.max_slots,
            "inflight": self.pool.inflight,
            "live_threads": self.pool.live_threads,
            "thread_ceiling": self.thread_ceiling,
            "processed": self.processed_count,
            "failed": self.failed_count,
            "timed_out": self.timed_out_count,
        }


# ----------------------------------------------------------------------
# Session
# ----------------------------------------------------------------------
def _open_session():
    # Đọc `SessionLocal` qua module `app.core.database` MỖI LẦN, đúng như
    # `process_due_schedules` làm: nếu bind tên vào namespace module lúc import thì
    # việc conftest gán lại SessionLocal cho session kiểm thử sẽ không có tác dụng ở
    # đây và worker sẽ âm thầm ghi vào CSDL thật (production / SQLite file).
    from app.core import database as _database

    return _database.SessionLocal()


def _close_session(db) -> None:
    if db is None:
        return
    try:
        db.close()
    except Exception:
        logger.debug("Không đóng được session của worker AI job", exc_info=True)


_worker: Optional[AIJobWorker] = None


def get_ai_job_worker() -> Optional[AIJobWorker]:
    """Worker hiện tại (nếu đã được tạo). Dùng cho chẩn đoán và cho test."""
    return _worker


def start_ai_job_worker(app=None) -> Optional[asyncio.Task]:
    """Khởi động worker nền. Trả `None` nếu không khởi động được.

    KHÔNG được để lỗi ở đây làm hỏng việc khởi động ứng dụng: nếu không bật được
    worker thì API vẫn phải phục vụ được mọi route không liên quan tới AI. Job đã
    enqueue vẫn nằm an toàn trong hàng đợi và sẽ được xử lý khi có tiến trình worker.
    """
    global _worker
    if not settings.AI_JOB_WORKER_ENABLED:
        logger.info(
            "AI_JOB_WORKER_ENABLED=false: bỏ qua worker AI job trong tiến trình. "
            "Job vẫn được enqueue và sẽ chạy khi có tiến trình worker riêng."
        )
        return None
    if _worker is None:
        _worker = AIJobWorker()
    try:
        return _worker.start(app)
    except Exception:
        logger.error(
            "Không khởi động được worker AI job; API vẫn phục vụ bình thường.",
            exc_info=True,
        )
        return None


def stop_ai_job_worker(app=None) -> None:
    global _worker
    if _worker is None:
        return
    try:
        _worker.stop(app)
        logger.info("Đã dừng worker AI job.")
    except Exception:
        logger.error("Lỗi khi dừng worker AI job.", exc_info=True)
