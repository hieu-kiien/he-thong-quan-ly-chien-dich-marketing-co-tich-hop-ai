"""Nghiệp vụ hội thoại Trợ lý AI: Threads, Messages, SSE Turn Stream (CONTRACT §4, §5, §6)."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.assistant.bus import event_bus
from app.assistant.context import get_db_context
from app.assistant.runner_client import RunnerClient, default_runner
from app.assistant.tools import registry
from app.core.config import settings
from app.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed
from app.core.security import encode_token
from app.core.timeutil import VN_TZ, now_utc, today_vn
from app.models.ai import AiAction, AiMessage, AiThread
from app.models.campaign import Campaign
from app.models.content import Content
from app.models.enums import AiActionStatus, AiMessageRole, AiMessageStatus
from app.models.user import User
from app.schemas.ai import (
    AiMessageOut,
    AiThreadCreate,
    AiThreadOut,
    AiThreadUpdate,
)
from app.schemas.common import CampaignRef
from app.schemas.stats import StatsFilters
from app.services import brand_service, campaign_service, channel_service, stats_service
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
        # Mở lại phiên TRỐNG đã có của chiến dịch này thay vì tạo thêm phiên rác mỗi lần bấm "Hỏi Trợ lý AI"
        empty_thread = db.execute(
            select(AiThread)
            .where(
                AiThread.user_id == user.id,
                AiThread.campaign_id == campaign_id,
                ~select(AiMessage.id).where(AiMessage.thread_id == AiThread.id).exists(),
            )
            .order_by(AiThread.id.desc())
        ).scalars().first()
        if empty_thread is not None:
            return thread_out(empty_thread)

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
    # Phiên chat là riêng tư của từng người dùng (kể cả Quản lý): chỉ chủ phiên được truy cập
    if thread.user_id != user.id:
        raise PermissionDenied("Bạn không có quyền truy cập phiên hội thoại này")
    return thread


def get_thread(db: Session, user: User, thread_id: int) -> AiThreadOut:
    return thread_out(get_thread_orm(db, user, thread_id))


def update_thread(db: Session, user: User, thread_id: int, data: AiThreadUpdate) -> AiThreadOut:
    thread = get_thread_orm(db, user, thread_id)
    if thread.user_id != user.id:
        raise PermissionDenied("Chỉ chủ phiên mới được sửa thông tin phiên")

    if data.campaign_id is not None:
        new_campaign_id: int | None
        if data.campaign_id == 0:
            new_campaign_id = None
        else:
            camp = db.get(Campaign, data.campaign_id)
            if camp is None:
                raise ValidationFailed(fields={"campaign_id": "Chiến dịch không tồn tại"})
            new_campaign_id = camp.id
        if new_campaign_id != thread.campaign_id:
            thread.campaign_id = new_campaign_id
            # Đổi ngữ cảnh chiến dịch: bắt đầu phiên OpenCode mới để lượt kế tiếp nhận ảnh chụp
            # dữ liệu của chiến dịch mới (kèm tóm tắt hội thoại trước đó).
            thread.opencode_session_id = None

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
    db.delete(thread)
    db.commit()


def list_messages(db: Session, user: User, thread_id: int) -> list[AiMessageOut]:
    get_thread_orm(db, user, thread_id)
    stmt = select(AiMessage).where(AiMessage.thread_id == thread_id).order_by(AiMessage.id.asc())
    messages = list(db.execute(stmt).scalars())
    return [message_out(m) for m in messages]


# --- Prompt Builder -----------------------------------------------------------

def _fmt_rate(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.2f}%"


def _fmt_money(value: Any) -> str:
    return "—" if value is None else f"{int(value):,} VND".replace(",", ".")


def _snapshot_lines(db: Session, user: User, thread: AiThread) -> list[str]:
    """Ảnh chụp dữ liệu (đọc qua service layer, đúng quyền người dùng) gửi kèm lượt đầu của phiên.

    Mỗi lần AI gọi công cụ là thêm một lượt gọi mô hình. Với hạn mức miễn phí, đưa sẵn dữ liệu
    hay dùng giúp trả lời nhanh hơn và tốn ít lượt hơn; AI vẫn gọi công cụ khi cần dữ liệu khác.
    """
    lines: list[str] = []
    brand = brand_service.get_brand_profile(db, user)
    if brand.brand_name:
        lines.append(f"- Thương hiệu: {brand.brand_name}. Giọng văn: {brand.tone_of_voice[:200] or '—'}")
    if brand.banned_keywords:
        words = ", ".join(f'"{k.keyword}"' for k in brand.banned_keywords[:20])
        lines.append(f"- Từ cấm của thương hiệu: {words}")

    if thread.campaign_id:
        try:
            camp = campaign_service.get_campaign(db, user, thread.campaign_id)
        except NotFound:
            return lines
        lines.append(
            f"- Chiến dịch #{camp.id} '{camp.name}': mục tiêu {camp.goal}, trạng thái {camp.status}, "
            f"{camp.start_date:%d/%m/%Y} - {camp.end_date:%d/%m/%Y}, ngân sách {_fmt_money(camp.budget)}"
        )
        lines.append(f"  - Mục tiêu chi tiết: {camp.objective[:300]}")
        lines.append(f"  - Đối tượng: {camp.target_audience[:300]}")
        lines.append(f"  - Sản phẩm: {camp.product[:300]}")
        if camp.key_message:
            lines.append(f"  - Thông điệp chính: {camp.key_message[:300]}")
        channels = ", ".join(
            f"{c.code} (dự kiến {_fmt_money(c.planned_budget)})" for c in camp.channels
        )
        lines.append(f"  - Kênh của chiến dịch: {channels}")
        today = today_vn()
        days_total = max(1, (camp.end_date - camp.start_date).days + 1)
        days_elapsed = 0 if today < camp.start_date else (days_total if today > camp.end_date else (today - camp.start_date).days + 1)
        time_pct = round(days_elapsed / days_total * 100, 1)
        s = camp.stats
        lines.append(
            f"  - Tiến độ thời gian: {days_elapsed}/{days_total} ngày ({time_pct}% thời gian), "
            f"đã dùng {s.budget_used_pct if s.budget_used_pct is not None else '—'}% ngân sách"
        )
        if s.views or s.clicks or s.conversions or s.cost:
            lines.append(
                f"  - Số liệu tổng (từ CSDL): views {s.views}, clicks {s.clicks}, chuyển đổi {s.conversions}, "
                f"chi phí {_fmt_money(s.cost)}, CTR {_fmt_rate(s.ctr)}, CVR {_fmt_rate(s.cvr)}, "
                f"CPC {_fmt_money(s.cpc)}, CPA {_fmt_money(s.cpa)}, "
                f"đã dùng {s.budget_used_pct if s.budget_used_pct is not None else '—'}% ngân sách"
            )
            planned_map = {c.code: c.planned_budget for c in camp.channels}
            for row in stats_service.get_by_channel(db, user, StatsFilters(campaign_id=camp.id)):
                planned = planned_map.get(row.channel.code)
                lines.append(
                    f"    - {row.channel.code}: views {row.views}, clicks {row.clicks}, chuyển đổi {row.conversions}, "
                    f"chi phí {_fmt_money(row.cost)} (dự kiến {_fmt_money(planned)}), CTR {_fmt_rate(row.ctr)}, CVR {_fmt_rate(row.cvr)}, "
                    f"CPC {_fmt_money(row.cpc)}, CPA {_fmt_money(row.cpa)}"
                )
        else:
            lines.append("  - Số liệu: CHƯA CÓ dữ liệu hiệu quả nào được nhập cho chiến dịch này.")
    return lines


def build_prompt(db: Session, user: User, thread: AiThread, user_content: str) -> str:
    lines = ["[NGỮ CẢNH]"]
    lines.append(f"- Người dùng: {user.full_name} (Vai trò: {user.role.value})")
    today = today_vn()
    lines.append(f"- Hôm nay: {today:%d/%m/%Y} (Múi giờ Asia/Ho_Chi_Minh)")

    first_turn_of_session = not thread.opencode_session_id
    if first_turn_of_session:
        # Lượt đầu của phiên OpenCode: gửi ảnh chụp dữ liệu; các lượt sau phiên đã nhớ ngữ cảnh.
        lines.extend(_snapshot_lines(db, user, thread))
        lines.append(
            f"- Ảnh chụp dữ liệu trên lấy lúc {datetime.now(VN_TZ):%H:%M %d/%m/%Y} (giờ Việt Nam); dùng ngay nếu đủ, "
            "chỉ gọi công cụ khi cần dữ liệu khác hoặc mới hơn."
        )
    elif thread.campaign_id:
        lines.append(f"- Chiến dịch gắn với phiên: #{thread.campaign_id}")

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


@dataclass
class TurnContext:
    """Một lượt hội thoại đã khởi tạo. Công việc chạy nền độc lập với kết nối của client."""

    thread_id: int
    out_queue: asyncio.Queue[str | None]


# Dict in-memory khoá các thread đang chạy
_running_turns: dict[int, RunningTurn] = {}
_turns_lock = asyncio.Lock()
# Giữ tham chiếu tới các task nền (tránh bị thu gom khi client ngắt kết nối giữa chừng)
_background_tasks: set[asyncio.Task[Any]] = set()


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


def _join_parts(parts: list[str]) -> str:
    """Ghép các part văn bản của OpenCode thành một markdown (mỗi part là một khối riêng)."""
    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def _prepare_regenerate(db: Session, thread: AiThread, message_id: int) -> AiMessage:
    """Chuẩn bị 'Tạo lại': dùng lại câu hỏi gốc (không nhân đôi) và bỏ câu trả lời cũ.

    Chỉ tạo lại được câu trả lời cuối cùng của phiên. Câu trả lời cũ chỉ bị xoá khi không có
    đề xuất hay nội dung nào gắn với nó (để không mất dấu vết nguồn gốc của nội dung AI).
    """
    msg = db.get(AiMessage, message_id)
    if msg is None or msg.thread_id != thread.id:
        raise NotFound("Không tìm thấy tin nhắn cần tạo lại")
    if msg.role != AiMessageRole.ASSISTANT:
        raise ValidationFailed(fields={"message_id": "Chỉ tạo lại được câu trả lời của trợ lý"})
    last_id = db.execute(select(func.max(AiMessage.id)).where(AiMessage.thread_id == thread.id)).scalar_one()
    if msg.id != last_id:
        raise Conflict("Chỉ tạo lại được câu trả lời cuối cùng của phiên", code="NOT_LAST_MESSAGE")
    prev_user = db.execute(
        select(AiMessage)
        .where(
            AiMessage.thread_id == thread.id,
            AiMessage.role == AiMessageRole.USER,
            AiMessage.id < msg.id,
        )
        .order_by(AiMessage.id.desc())
    ).scalars().first()
    if prev_user is None:
        raise NotFound("Không tìm thấy tin nhắn người dùng tương ứng để tạo lại")

    # Xoá các đề xuất chưa thực thi (PROPOSED / REJECTED / FAILED) gắn với câu trả lời cũ
    # để khi tạo lại không bị nhân đôi bong bóng trả lời của Trợ lý AI.
    db.execute(
        delete(AiAction).where(
            AiAction.message_id == msg.id,
            AiAction.status != AiActionStatus.EXECUTED,
        )
    )
    has_executed_actions = db.execute(
        select(AiAction.id)
        .where(AiAction.message_id == msg.id, AiAction.status == AiActionStatus.EXECUTED)
        .limit(1)
    ).first()
    has_contents = db.execute(select(Content.id).where(Content.ai_message_id == msg.id).limit(1)).first()
    if not has_executed_actions and not has_contents:
        db.delete(msg)
    return prev_user


# --- Luồng thực thi Turn Stream (SSE) -----------------------------------------

async def start_turn(
    user_id: int,
    thread_id: int,
    content: str,
    runner: RunnerClient | None = None,
    regenerate_message_id: int | None = None,
) -> TurnContext:
    """Khởi tạo một lượt hội thoại: kiểm tra quyền, giành khoá phiên, ghi DB, chạy nền.

    Mọi lỗi (403/404/409) được ném ra TRƯỚC khi bắt đầu stream nên trả về JSON lỗi chuẩn.
    Sau khi trả về, lượt chạy hoàn tất và được lưu kể cả khi client ngắt kết nối (F5).
    """
    r = runner or default_runner
    now = datetime.now(UTC)

    # 1. Giành khoá phiên một cách nguyên tử TRƯỚC khi ghi DB (tránh hai lượt chạy chồng nhau)
    turn = await register_turn(thread_id, 0)

    try:
        with get_db_context() as db:
            user = db.get(User, user_id)
            if not user or not user.is_active:
                raise PermissionDenied("Tài khoản người dùng không hoạt động")

            thread = db.get(AiThread, thread_id)
            if thread is None:
                raise NotFound("Không tìm thấy phiên hội thoại")
            # Phiên chat là riêng tư của từng người dùng (kể cả Quản lý)
            if thread.user_id != user.id:
                raise PermissionDenied("Không có quyền truy cập phiên này")

            if regenerate_message_id is not None:
                user_msg = _prepare_regenerate(db, thread, regenerate_message_id)
            else:
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
                clean_title = user_msg.content.strip().replace("\n", " ")
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
            token_version = user.token_version or 0
            session_id = thread.opencode_session_id
            prompt = build_prompt(db, user, thread, user_msg.content)
    except BaseException:
        await unregister_turn(thread_id)
        raise

    turn.message_id = assistant_msg_id

    # 2. Tạo run-token cho MCP (10 phút)
    run_token_payload = {
        "typ": "assistant_run",
        "uid": user_id,
        "thread_id": thread_id,
        "message_id": assistant_msg_id,
        "tv": token_version,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.ASSISTANT_RUN_TOKEN_TTL_S)).timestamp()),
    }
    run_token = encode_token(run_token_payload)

    # 3. Đăng ký nhận sự kiện từ MCP event bus
    bus_queue = await event_bus.register(assistant_msg_id)

    # Hàng đợi xuất dữ liệu SSE ra ngoài
    out_queue: asyncio.Queue[str | None] = asyncio.Queue()
    out_queue.put_nowait(
        _format_sse(
            "message_start",
            {
                "user_message": user_msg_out,
                "assistant_message": {"id": assistant_msg_id, "status": "STREAMING"},
            },
        )
    )

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
                if data.get("status") in ("done", "error"):
                    await out_queue.put(_format_sse("status", {"phase": "thinking"}))
            elif etype == "action":
                await out_queue.put(_format_sse("action", data))

    bus_task = asyncio.create_task(_bus_worker())

    async def _runner_worker() -> None:
        """Chạy ai-runner và bơm sự kiện vào out_queue; lưu kết quả cuối vào DB."""
        accumulated_parts: list[str] = []
        streaming_part = ""
        current_phase = ""
        emitted_tools: set[str] = set()
        model_name: str | None = None
        latency: int | None = None
        final_status = AiMessageStatus.COMPLETE
        error_code: str | None = None
        last_db_flush_at = 0.0

        def _flush_partial_content(content_snapshot: str, *, force: bool = False) -> None:
            nonlocal last_db_flush_at
            if not content_snapshot:
                return
            now_mono = time.monotonic()
            if not force and (now_mono - last_db_flush_at) < 1.2:
                return
            last_db_flush_at = now_mono
            with contextlib.suppress(Exception):
                with get_db_context() as db_p:
                    m = db_p.get(AiMessage, assistant_msg_id)
                    if m and m.status == AiMessageStatus.STREAMING:
                        m.content = content_snapshot
                        db_p.commit()

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
                    current_phase = "thinking"
                    await out_queue.put(_format_sse("status", {"phase": "thinking"}))

                elif etype == "queued":
                    current_phase = "queued"
                    await out_queue.put(
                        _format_sse("status", {"phase": "queued", "queue_position": ev.get("position", 1)})
                    )

                elif etype == "step":
                    streaming_part = ""
                    if current_phase != "thinking":
                        current_phase = "thinking"
                        await out_queue.put(_format_sse("status", {"phase": "thinking"}))

                elif etype == "session":
                    new_sid = ev.get("id")
                    if new_sid:
                        with get_db_context() as db_s:
                            t = db_s.get(AiThread, thread_id)
                            if t:
                                t.opencode_session_id = str(new_sid)
                                db_s.commit()

                elif etype == "text_delta":
                    delta = ev.get("delta", "")
                    if delta:
                        streaming_part += delta
                        if current_phase != "writing":
                            current_phase = "writing"
                            await out_queue.put(_format_sse("status", {"phase": "writing"}))
                        live_content = _join_parts([*accumulated_parts, streaming_part])
                        if live_content:
                            await out_queue.put(_format_sse("text", {"content": live_content}))
                            _flush_partial_content(live_content, force=False)

                elif etype == "text":
                    part = ev.get("text", "")
                    streaming_part = ""
                    if part:
                        accumulated_parts.append(part)
                        if current_phase != "writing":
                            current_phase = "writing"
                            await out_queue.put(_format_sse("status", {"phase": "writing"}))
                        # OpenCode gửi từng "part" văn bản hoàn chỉnh (trước/sau khi gọi công cụ)
                        full_content = _join_parts(accumulated_parts)
                        await out_queue.put(_format_sse("text", {"content": full_content}))
                        _flush_partial_content(full_content, force=True)

                elif etype == "tool":
                    # Xoá mọi phân đoạn delta chưa xác nhận trước khi gọi công cụ (ví dụ suy luận nội bộ)
                    streaming_part = ""
                    name = str(ev.get("name") or "")
                    # Công cụ MarketFlow chạy qua MCP của chính backend nên event bus đã phát
                    # running/done kèm tóm tắt tiếng Việt — bỏ bản sao từ runner để tránh trùng.
                    if registry.get(name) is not None:
                        continue
                    call_id = str(ev.get("id") or name)
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
            # Xả nốt sự kiện MCP (tool/action) trước khi kết thúc để không bị mất hay đảo thứ tự
            await bus_queue.put(None)
            with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError):
                await asyncio.wait_for(asyncio.shield(bus_task), timeout=2.0)

            if streaming_part.strip():
                accumulated_parts.append(streaming_part)
            full_content = _join_parts(accumulated_parts)
            # Cập nhật DB trạng thái kết thúc
            with get_db_context() as db_final:
                msg = db_final.get(AiMessage, assistant_msg_id)
                if msg:
                    if not full_content and final_status == AiMessageStatus.COMPLETE:
                        has_proposed = db_final.execute(
                            select(AiAction.id).where(AiAction.message_id == assistant_msg_id).limit(1)
                        ).first()
                        if has_proposed:
                            full_content = (
                                "Tôi đã chuẩn bị đề xuất cập nhật bên dưới. "
                                "Bạn có thể kiểm tra chi tiết ở khung bên phải và bấm **Xác nhận** để áp dụng."
                            )
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

    async def _supervisor() -> None:
        try:
            await _runner_worker()
        finally:
            # Giải phóng khoá phiên CHỈ khi lượt chạy thực sự kết thúc (kể cả khi client đã ngắt)
            bus_task.cancel()
            await event_bus.unregister(assistant_msg_id, bus_queue)
            await unregister_turn(thread_id)
            out_queue.put_nowait(None)

    supervisor = asyncio.create_task(_supervisor())
    for task in (supervisor, bus_task):
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    return TurnContext(thread_id=thread_id, out_queue=out_queue)


async def stream_turn(ctx: TurnContext) -> AsyncIterator[str]:
    """Đọc sự kiện SSE của một lượt đã khởi tạo, kèm heartbeat 15 giây (CONTRACT §6)."""
    while True:
        try:
            item = await asyncio.wait_for(ctx.out_queue.get(), timeout=15.0)
        except TimeoutError:
            yield ": ping\n\n"
            continue
        if item is None:
            break
        yield item


async def run_turn_stream(
    user_id: int,
    thread_id: int,
    content: str,
    runner: RunnerClient | None = None,
    regenerate_message_id: int | None = None,
) -> AsyncIterator[str]:
    """Tiện ích: khởi tạo rồi stream một lượt (dùng trong test)."""
    ctx = await start_turn(user_id, thread_id, content, runner, regenerate_message_id)
    async for item in stream_turn(ctx):
        yield item
