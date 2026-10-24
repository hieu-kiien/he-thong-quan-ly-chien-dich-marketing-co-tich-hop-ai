"""Nghiệp vụ hội thoại Trợ lý AI: Threads, Messages, SSE Turn Stream (CONTRACT §4, §5, §6)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant.bus import event_bus
from app.assistant.context import get_db_context
from app.assistant.runner_client import RunnerClient, default_runner
from app.core.config import settings
from app.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed
from app.core.security import encode_token
from app.core.timeutil import now_utc, today_vn
from app.models.ai import AiMessage, AiThread
from app.models.campaign import Campaign
from app.models.enums import AiMessageRole, AiMessageStatus
from app.models.user import User
from app.schemas.ai import (
    AiMessageOut,
    AiThreadCreate,
    AiThreadOut,
    AiThreadUpdate,
)
from app.schemas.common import CampaignRef
from app.services import channel_service
from app.services.common import like_pattern

logger = logging.getLogger(__name__)


def thread_out(thread: AiThread) -> AiThreadOut:
    camp_ref = (
        CampaignRef(id=thread.campaign.id, name=thread.campaign.name)
        if thread.campaign
        else None
    )
    return AiThreadOut(
        id=thread.id,
        user_id=thread.user_id,
        campaign_id=thread.campaign_id,
        campaign=camp_ref,
        title=thread.title,
        pinned=thread.pinned,
        last_message_at=thread.last_message_at,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


def message_out(message: AiMessage) -> AiMessageOut:
    return AiMessageOut.model_validate(message)


# --- Threads & Messages CRUD --------------------------------------------------

def create_thread(db: Session, user: User, data: AiThreadCreate) -> AiThreadOut:
    campaign_id = None
    if data.campaign_id is not None:
        camp = db.get(Campaign, data.campaign_id)
        if camp is None:
            raise ValidationFailed(fields={"campaign_id": "Chiến dịch không tồn tại"})
        campaign_id = camp.id

    thread = AiThread(
        user_id=user.id,
        campaign_id=campaign_id,
        title=(data.title or "Phiên mới").strip() or "Phiên mới",
        pinned=False,
        last_message_at=now_utc(),
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread_out(thread)


def list_threads(db: Session, user: User, q: str | None = None) -> list[AiThreadOut]:
    stmt = select(AiThread).where(AiThread.user_id == user.id)
    if q and q.strip():
        pattern = like_pattern(q.strip())
        stmt = stmt.where(AiThread.title.ilike(pattern, escape="\\"))
    stmt = stmt.order_by(AiThread.pinned.desc(), AiThread.last_message_at.desc(), AiThread.id.desc())
    threads = list(db.execute(stmt).scalars())
    return [thread_out(t) for t in threads]


def get_thread_orm(db: Session, user: User, thread_id: int) -> AiThread:
    thread = db.get(AiThread, thread_id)
    if thread is None:
        raise NotFound("Không tìm thấy phiên hội thoại")
    if thread.user_id != user.id and not user.is_manager:
        raise PermissionDenied("Bạn không có quyền truy cập phiên hội thoại này")
    return thread


def get_thread(db: Session, user: User, thread_id: int) -> AiThreadOut:
    return thread_out(get_thread_orm(db, user, thread_id))


def update_thread(db: Session, user: User, thread_id: int, data: AiThreadUpdate) -> AiThreadOut:
    thread = get_thread_orm(db, user, thread_id)
    if thread.user_id != user.id:
        raise PermissionDenied("Chỉ chủ phiên mới được sửa thông tin phiên")

    if data.campaign_id is not None:
        if data.campaign_id == 0:
            thread.campaign_id = None
        else:
            camp = db.get(Campaign, data.campaign_id)
            if camp is None:
                raise ValidationFailed(fields={"campaign_id": "Chiến dịch không tồn tại"})
            thread.campaign_id = camp.id

    if data.title is not None:
        new_title = data.title.strip()
        if new_title:
            thread.title = new_title[:200]

    if data.pinned is not None:
        thread.pinned = data.pinned

    db.commit()
    db.refresh(thread)
    return thread_out(thread)


def delete_thread(db: Session, user: User, thread_id: int) -> None:
    thread = get_thread_orm(db, user, thread_id)
    if thread.user_id != user.id and not user.is_manager:
        raise PermissionDenied("Chỉ chủ phiên mới được xoá phiên hội thoại")
    db.delete(thread)
    db.commit()


def list_messages(db: Session, user: User, thread_id: int) -> list[AiMessageOut]:
    get_thread_orm(db, user, thread_id)
    stmt = select(AiMessage).where(AiMessage.thread_id == thread_id).order_by(AiMessage.id.asc())
    messages = list(db.execute(stmt).scalars())
    return [message_out(m) for m in messages]


# --- Prompt Builder -----------------------------------------------------------

def build_prompt(db: Session, user: User, thread: AiThread, user_content: str) -> str:
    lines = ["[NGỮ CẢNH]"]
    lines.append(f"- Người dùng: {user.full_name} (Vai trò: {user.role.value})")
    today = today_vn()
    lines.append(f"- Hôm nay: {today:%d/%m/%Y} (Múi giờ Asia/Ho_Chi_Minh)")

    # Chiến dịch gắn kèm (nếu có)
    if thread.campaign_id:
        camp = db.get(Campaign, thread.campaign_id)
        if camp:
            lines.append(
                f"- Chiến dịch gắn với phiên: #{camp.id} '{camp.name}' | "
                f"Mục tiêu: {camp.goal.value} | Trạng thái: {camp.status.value} | "
                f"Ngân sách: {int(camp.budget):,} VND | "
                f"Thời gian: {camp.start_date:%d/%m/%Y} - {camp.end_date:%d/%m/%Y}"
            )

    # Kênh tiếp thị đang kích hoạt
    active_channels = channel_service.list_channels(db, user, include_inactive=False)
    ch_codes = ", ".join(c.code for c in active_channels)
    lines.append(f"- Các kênh tiếp thị đang hoạt động: {ch_codes}")

    # Nếu phiên mới hoặc chưa có session id, đưa tóm tắt ngắn các lượt trước (nếu có)
    if not thread.opencode_session_id:
        prev_messages = list(
            db.execute(
                select(AiMessage)
                .where(AiMessage.thread_id == thread.id, AiMessage.status == AiMessageStatus.COMPLETE)
                .order_by(AiMessage.id.asc())
            ).scalars()
        )
        if prev_messages:
            lines.append("\n[LỊCH SỬ HỘI THOẠI TRƯỚC ĐÓ]")
            for m in prev_messages[-6:]:
                role_label = "Người dùng" if m.role == AiMessageRole.USER else "Trợ lý AI"
                lines.append(f"{role_label}: {m.content[:300]}")

    lines.append("\n[YÊU CẦU CỦA NGƯỜI DÙNG]")
    lines.append(user_content)
    return "\n".join(lines)


# --- Trạng thái chạy & Quản lý lượt (Turn Manager) ---------------------------

@dataclass
class RunningTurn:
    thread_id: int
    message_id: int
    run_id: str | None = None
    abort_event: asyncio.Event | None = None


# Dict in-memory khoá các thread đang chạy
_running_turns: dict[int, RunningTurn] = {}
_turns_lock = asyncio.Lock()


async def is_thread_busy(thread_id: int) -> bool:
    async with _turns_lock:
        return thread_id in _running_turns


async def register_turn(thread_id: int, message_id: int) -> RunningTurn:
    async with _turns_lock:
        if thread_id in _running_turns:
            raise Conflict("Phiên hội thoại đang có lượt xử lý chưa hoàn tất", code="THREAD_BUSY")
        turn = RunningTurn(
            thread_id=thread_id,
            message_id=message_id,
            abort_event=asyncio.Event(),
        )
        _running_turns[thread_id] = turn
        return turn


async def unregister_turn(thread_id: int) -> None:
    async with _turns_lock:
        _running_turns.pop(thread_id, None)


async def stop_thread(db: Session, user: User, thread_id: int, runner: RunnerClient | None = None) -> dict[str, Any]:
    get_thread_orm(db, user, thread_id)
    r = runner or default_runner
    async with _turns_lock:
        turn = _running_turns.get(thread_id)
    if not turn:
        return {"status": "not_running"}

    if turn.abort_event:
        turn.abort_event.set()
    if turn.run_id:
        await r.abort(turn.run_id)

    # Cập nhật trạng thái tin nhắn thành STOPPED
    with get_db_context() as db_session:
        msg = db_session.get(AiMessage, turn.message_id)
        if msg and msg.status == AiMessageStatus.STREAMING:
            msg.status = AiMessageStatus.STOPPED
            db_session.commit()

    return {"status": "stopped"}


def _format_sse(event_type: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


# --- Luồng thực thi Turn Stream (SSE) -----------------------------------------

async def run_turn_stream(
    user_id: int,
    thread_id: int,
    content: str,
    runner: RunnerClient | None = None,
) -> AsyncIterator[str]:
    """Khởi chạy một lượt hội thoại stream, kết hợp runner events và MCP event bus."""
    r = runner or default_runner
    now = datetime.now(UTC)

    # 1. Khởi tạo DB records cho turn
    with get_db_context() as db:
        user = db.get(User, user_id)
        if not user or not user.is_active:
            raise PermissionDenied("Tài khoản người dùng không hoạt động")

        thread = db.get(AiThread, thread_id)
        if not thread or (thread.user_id != user.id and not user.is_manager):
            raise PermissionDenied("Không có quyền truy cập phiên này")

        # Lưu User message
        user_msg = AiMessage(
            thread_id=thread.id,
            role=AiMessageRole.USER,
            content=content,
            parts_json=[],
            status=AiMessageStatus.COMPLETE,
        )
        db.add(user_msg)
        db.flush()

        # Tự động đặt tên phiên nếu là "Phiên mới"
        if thread.title == "Phiên mới":
            clean_title = content.strip().replace("\n", " ")
            thread.title = clean_title[:60].strip() or "Phiên mới"

        # Tạo Assistant message ở trạng thái STREAMING
        assistant_msg = AiMessage(
            thread_id=thread.id,
            role=AiMessageRole.ASSISTANT,
            content="",
            parts_json=[],
            status=AiMessageStatus.STREAMING,
        )
        db.add(assistant_msg)
        thread.last_message_at = now_utc()
        db.commit()
        db.refresh(user_msg)
        db.refresh(assistant_msg)
        db.refresh(thread)

        user_msg_out = message_out(user_msg).model_dump(mode="json")
        assistant_msg_id = assistant_msg.id
        session_id = thread.opencode_session_id
        prompt = build_prompt(db, user, thread, content)

    # 2. Đăng ký turn lock
    turn = await register_turn(thread_id, assistant_msg_id)

    # 3. Tạo run-token cho MCP (10 phút)
    run_token_payload = {
        "typ": "assistant_run",
        "uid": user_id,
        "thread_id": thread_id,
        "message_id": assistant_msg_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.ASSISTANT_RUN_TOKEN_TTL_S)).timestamp()),
    }
    run_token = encode_token(run_token_payload)

    # 4. Đăng ký nhận sự kiện từ MCP event bus
    bus_queue = await event_bus.register(assistant_msg_id)

    # Hàng đợi xuất dữ liệu SSE ra ngoài
    out_queue: asyncio.Queue[str | None] = asyncio.Queue()

    # Phát message_start ngay lập tức
    await out_queue.put(
        _format_sse(
            "message_start",
            {
                "user_message": user_msg_out,
                "assistant_message": {"id": assistant_msg_id, "status": "STREAMING"},
            },
        )
    )

    async def _runner_worker() -> None:
        """Worker chạy ai-runner và bơm sự kiện vào out_queue."""
        accumulated_parts: list[str] = []
        emitted_tools: set[str] = set()
        model_name: str | None = None
        latency: int | None = None
        final_status = AiMessageStatus.COMPLETE
        error_code: str | None = None

        try:
            stream = r.stream_run(
                prompt=prompt,
                session_id=session_id,
                run_token=run_token,
                timeout_s=float(settings.ASSISTANT_TURN_TIMEOUT_S),
            )
            async for ev in stream:
                if turn.abort_event and turn.abort_event.is_set():
                    final_status = AiMessageStatus.STOPPED
                    break

                etype = ev.get("type")
                if etype == "run":
                    turn.run_id = ev.get("run_id")

                elif etype == "queued":
                    await out_queue.put(
                        _format_sse("status", {"phase": "queued", "queue_position": ev.get("position", 1)})
                    )

                elif etype == "session":
                    new_sid = ev.get("id")
                    if new_sid:
                        with get_db_context() as db_s:
                            t = db_s.get(AiThread, thread_id)
                            if t:
                                t.opencode_session_id = str(new_sid)
                                db_s.commit()

                elif etype == "text":
                    part = ev.get("text", "")
                    if part:
                        accumulated_parts.append(part)
                        full_content = "".join(accumulated_parts)
                        await out_queue.put(_format_sse("text", {"content": full_content}))

                elif etype == "tool":
                    call_id = str(ev.get("id") or ev.get("name"))
                    # Bỏ qua nếu đã được MCP event bus phát
                    if call_id not in emitted_tools:
                        emitted_tools.add(call_id)
                        await out_queue.put(
                            _format_sse(
                                "tool_call",
                                {
                                    "id": call_id,
                                    "name": ev.get("name"),
                                    "args": ev.get("input") or {},
                                    "status": ev.get("status", "done"),
                                    "summary": ev.get("summary"),
                                },
                            )
                        )

                elif etype == "done":
                    model_name = ev.get("model")
                    latency = ev.get("latency_ms")
                    break

                elif etype == "error":
                    final_status = AiMessageStatus.ERROR
                    error_code = ev.get("code", "AI_INTERNAL")
                    err_msg = ev.get("message", "Đã có lỗi từ dịch vụ AI.")
                    await out_queue.put(_format_sse("error", {"code": error_code, "message": err_msg}))
                    break

        except Exception:
            logger.exception("Lỗi ngoại lệ trong runner worker")
            final_status = AiMessageStatus.ERROR
            error_code = "AI_INTERNAL"
            await out_queue.put(
                _format_sse("error", {"code": "AI_INTERNAL", "message": "Lỗi nội bộ khi kết nối tới dịch vụ AI."})
            )

        finally:
            full_content = "".join(accumulated_parts)
            # Cập nhật DB trạng thái kết thúc
            with get_db_context() as db_final:
                msg = db_final.get(AiMessage, assistant_msg_id)
                if msg:
                    msg.content = full_content
                    msg.status = final_status
                    msg.error_code = error_code
                    msg.model = model_name
                    msg.latency_ms = latency
                    db_final.commit()
                    db_final.refresh(msg)
                    final_msg_out = message_out(msg).model_dump(mode="json")
                else:
                    final_msg_out = {"id": assistant_msg_id, "status": final_status.value}

            if final_status != AiMessageStatus.ERROR:
                await out_queue.put(_format_sse("message_end", {"message": final_msg_out}))

    async def _bus_worker() -> None:
        """Worker lắng nghe các sự kiện từ MCP event bus (tool running/done, action)."""
        while True:
            ev = await bus_queue.get()
            if ev is None:
                break
            etype = ev.get("event")
            data = ev.get("data")
            if etype == "tool_call":
                if data.get("status") == "running":
                    await out_queue.put(_format_sse("status", {"phase": "tool"}))
                await out_queue.put(_format_sse("tool_call", data))
            elif etype == "action":
                await out_queue.put(_format_sse("action", data))

    # Chạy runner worker song song
    runner_task = asyncio.create_task(_runner_worker())
    bus_task = asyncio.create_task(_bus_worker())

    def _done_callback(fut: Any) -> None:
        # Ngừng bus worker khi runner xong
        bus_task.cancel()
        out_queue.put_nowait(None)

    runner_task.add_done_callback(_done_callback)

    try:
        # 5. Yield SSE events ra response stream với heartbeat 15 giây
        while True:
            try:
                item = await asyncio.wait_for(out_queue.get(), timeout=15.0)
                if item is None:
                    break
                yield item
            except TimeoutError:
                # Heartbeat comment per CONTRACT §6 / §10
                yield ": ping\n\n"

    finally:
        # Dọn dẹp tài nguyên
        await event_bus.unregister(assistant_msg_id, bus_queue)
        await unregister_turn(thread_id)
        if not runner_task.done():
            # Client ngắt kết nối: runner vẫn tiếp tục chạy hoàn tất ở nền (hoặc abort nếu đã set)
            pass
