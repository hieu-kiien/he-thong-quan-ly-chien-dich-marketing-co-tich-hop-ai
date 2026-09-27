"""Background Scheduler Worker for MarketFlow AI.
Monitors, triggers, and executes planned content schedules (FR08).
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.models.entities import MarketingSchedule, MarketingContent

logger = logging.getLogger("marketflow.scheduler")

# Standard Vietnam Timezone (UTC+7)
VN_TIMEZONE = timezone(timedelta(hours=7))

COMMON_TZ_OFFSETS = {
    "asia/ho_chi_minh": timedelta(hours=7),
    "asia/saigon": timedelta(hours=7),
    "asia/bangkok": timedelta(hours=7),
    "asia/tokyo": timedelta(hours=9),
    "utc": timedelta(0),
    "gmt": timedelta(0),
}

_scheduler_task: Optional[asyncio.Task] = None


def get_tz_from_name(tz_name: Optional[str] = None) -> timezone:
    """Resolve timezone object from timezone name or offset string."""
    if not tz_name:
        return VN_TIMEZONE
    normalized = tz_name.strip().lower()
    if normalized in COMMON_TZ_OFFSETS:
        return timezone(COMMON_TZ_OFFSETS[normalized])

    # Offset format like +07:00 or -05:00
    if normalized.startswith(("+", "-")) and ":" in normalized:
        try:
            sign = 1 if normalized[0] == "+" else -1
            parts = normalized[1:].split(":")
            h, m = int(parts[0]), int(parts[1])
            return timezone(timedelta(hours=sign * h, minutes=sign * m))
        except Exception:
            pass

    # Try ZoneInfo if available in standard library / environment
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(tz_name)
    except Exception:
        pass

    return VN_TIMEZONE


def parse_scheduled_datetime(date_str: str, tz_name: Optional[str] = "Asia/Ho_Chi_Minh") -> datetime:
    """Parse scheduled datetime string supporting ISO 8601 and common standard formats.
    Returns timezone-aware datetime object.
    """
    if not date_str:
        raise ValueError("date_str cannot be empty")

    cleaned = date_str.strip()
    target_tz = get_tz_from_name(tz_name)

    # 1. Try fromisoformat (handles ISO 8601 with Z, +07:00, or date strings in Python 3.11+)
    try:
        dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=target_tz)
        return dt
    except ValueError:
        pass

    # 2. Try common format patterns
    patterns = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
    ]
    for pattern in patterns:
        try:
            dt = datetime.strptime(cleaned, pattern)
            return dt.replace(tzinfo=target_tz)
        except ValueError:
            continue

    raise ValueError(f"Unsupported datetime format: '{date_str}'")


def process_due_schedules(db: Optional[Session] = None) -> List[int]:
    """Scans MarketingSchedule records with status == 'PLANNED'.
    If scheduled_at <= now(), transitions schedule to 'EXECUTED'.
    Finds associated MarketingContent; if status == 'APPROVED', transitions it to 'PUBLISHED'.
    Returns list of processed schedule IDs.

    Multi-replica safety: each due schedule is claimed with a single conditional
    UPDATE (PLANNED -> EXECUTED) before its content is touched, so when several
    worker processes/replicas share the same database exactly one of them wins the
    row and the others skip it. processed_ids therefore only contains schedules
    this process actually executed.
    """
    own_session = False
    if db is None:
        from app.core.database import SessionLocal
        db = SessionLocal()
        own_session = True

    processed_ids: List[int] = []
    try:
        due_schedules = (
            db.query(MarketingSchedule)
            .filter(MarketingSchedule.status == "PLANNED")
            .all()
        )
        now_utc = datetime.now(timezone.utc)

        for schedule in due_schedules:
            try:
                scheduled_dt = parse_scheduled_datetime(schedule.scheduled_at, schedule.timezone)
                if scheduled_dt.astimezone(timezone.utc) <= now_utc:
                    # Claim the schedule atomically so only one worker/replica processes it.
                    # Cột status chỉ chấp nhận PLANNED/CANCELLED/EXECUTED (CHECK
                    # chk_schedule_status trong entities.py), nên lease được nắm bằng chính
                    # lệnh chuyển PLANNED -> EXECUTED có điều kiện: một câu UPDATE nguyên tử,
                    # chỉ worker đọc được rowcount = 1 mới được quyền xử lý. Replica thứ hai
                    # (hoặc vòng lặp kế tiếp) nhận rowcount = 0 và bỏ qua -> không xử lý
                    # trùng, không publish trùng, không ghi đè trạng thái của lịch.
                    claimed = db.query(MarketingSchedule).filter(
                        MarketingSchedule.id == schedule.id,
                        MarketingSchedule.status == "PLANNED",
                    ).update(
                        {"status": "EXECUTED"},
                        synchronize_session=False,
                    )
                    if not claimed:
                        logger.info(
                            f"Schedule {schedule.id} already claimed by another worker/replica; skipping."
                        )
                        continue
                    # Chi sau khi da nam duoc lease, moi chuyen noi dung APPROVED sang PUBLISHED.
                    content = (
                        db.query(MarketingContent)
                        .filter(MarketingContent.id == schedule.content_id)
                        .first()
                    )
                    if content and content.status == "APPROVED":
                        content.status = "PUBLISHED"
                    processed_ids.append(schedule.id)
            except Exception as e:
                logger.warning(
                    f"Error parsing schedule {schedule.id} scheduled_at '{schedule.scheduled_at}': {e}"
                )
                continue

        if processed_ids:
            db.commit()
        return processed_ids
    except Exception as e:
        if own_session:
            db.rollback()
        logger.error(f"Error processing due schedules: {e}", exc_info=True)
        raise
    finally:
        if own_session:
            db.close()


async def _scheduler_loop(interval_seconds: int = 20):
    """Background asyncio loop executing due schedules every interval_seconds."""
    logger.info(f"Scheduler worker loop started (interval: {interval_seconds}s).")
    while True:
        try:
            # process_due_schedules() là I/O blocking thuần tuý (SELECT + UPDATE + COMMIT,
            # tức là round-trip và disk I/O của DB, không có tính toán CPU để bù đắp).
            # Nếu gọi nó trực tiếp ở đây thì coroutine này giữ event loop trong suốt thời
            # gian đó: asyncio chỉ chạy được khi coroutine nhường quyền, nên mọi request
            # HTTP của server (kể cả request đang ở giữa await socket) sẽ bị đóng băng
            # đến khi query/commit xong - lặp lại mỗi interval_seconds (20s).
            # asyncio.to_thread() đẩy phần blocking sang thread của ThreadPoolExecutor,
            # event loop tiếp tục phục vụ request trong lúc worker chờ kết quả.
            processed = await asyncio.to_thread(process_due_schedules)
            if processed:
                logger.info(f"Scheduler worker executed {len(processed)} schedules: {processed}")
        except asyncio.CancelledError:
            logger.info("Scheduler worker loop received cancellation signal.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in scheduler loop: {e}", exc_info=True)

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.info("Scheduler worker loop sleep cancelled.")
            break


def start_scheduler_task(app: Optional[FastAPI] = None, interval_seconds: int = 20) -> Optional[asyncio.Task]:
    """Starts the background scheduler task on app startup."""
    global _scheduler_task
    if _scheduler_task is not None and not _scheduler_task.done():
        logger.warning("Scheduler task is already running.")
        return _scheduler_task

    try:
        loop = asyncio.get_running_loop()
        _scheduler_task = loop.create_task(_scheduler_loop(interval_seconds))
        if app is not None:
            app.state.scheduler_task = _scheduler_task
        logger.info("Scheduler background task started successfully.")
        return _scheduler_task
    except RuntimeError:
        logger.warning("No running event loop found; scheduler task not started synchronously.")
        return None


def stop_scheduler_task(app: Optional[FastAPI] = None):
    """Cleanly cancels the scheduler task on app shutdown."""
    global _scheduler_task
    task = _scheduler_task
    if app is not None and hasattr(app.state, "scheduler_task"):
        task = app.state.scheduler_task
    if task and not task.done():
        logger.info("Cancelling scheduler background task...")
        task.cancel()
        _scheduler_task = None
