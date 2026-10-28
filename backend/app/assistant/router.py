"""API endpoints cho Trợ lý Marketing AI (CONTRACT §4 assistant group)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query, Response, status
from fastapi.responses import StreamingResponse

from app.assistant import actions_service, chat_service
from app.core.errors import NotFound, PermissionDenied
from app.core.security import CurrentUser, DbSession
from app.models.ai import AiMessage, AiThread
from app.models.enums import AiActionStatus
from app.schemas.ai import (
    ActionConfirmIn,
    AiActionOut,
    AiMessageOut,
    AiThreadCreate,
    AiThreadOut,
    AiThreadUpdate,
    AssistantStatusOut,
    MessageSendIn,
)

router = APIRouter(prefix="/assistant", tags=["Trợ lý AI"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


# --- Threads ------------------------------------------------------------------

@router.get("/threads", response_model=list[AiThreadOut], summary="Danh sách phiên hội thoại")
def list_threads(
    user: CurrentUser,
    db: DbSession,
    q: Annotated[str | None, Query(description="Tìm kiếm theo tiêu đề phiên")] = None,
) -> list[AiThreadOut]:
    return chat_service.list_threads(db, user, q)


@router.post("/threads", response_model=AiThreadOut, status_code=status.HTTP_201_CREATED, summary="Tạo phiên mới")
def create_thread(
    data: AiThreadCreate,
    user: CurrentUser,
    db: DbSession,
) -> AiThreadOut:
    return chat_service.create_thread(db, user, data)


@router.get("/threads/{thread_id}", response_model=AiThreadOut, summary="Chi tiết phiên hội thoại")
def get_thread(
    thread_id: int,
    user: CurrentUser,
    db: DbSession,
) -> AiThreadOut:
    return chat_service.get_thread(db, user, thread_id)


@router.patch("/threads/{thread_id}", response_model=AiThreadOut, summary="Cập nhật phiên hội thoại")
def update_thread(
    thread_id: int,
    data: AiThreadUpdate,
    user: CurrentUser,
    db: DbSession,
) -> AiThreadOut:
    return chat_service.update_thread(db, user, thread_id, data)


@router.delete(
    "/threads/{thread_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Xoá phiên hội thoại",
)
def delete_thread(
    thread_id: int,
    user: CurrentUser,
    db: DbSession,
) -> Response:
    chat_service.delete_thread(db, user, thread_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/threads/{thread_id}/messages", response_model=list[AiMessageOut], summary="Danh sách tin nhắn của phiên")
def list_messages(
    thread_id: int,
    user: CurrentUser,
    db: DbSession,
) -> list[AiMessageOut]:
    return chat_service.list_messages(db, user, thread_id)


# --- Stream Interaction -------------------------------------------------------

@router.post("/threads/{thread_id}/messages", summary="Gửi tin nhắn & nhận luồng SSE")
async def send_message(
    thread_id: int,
    data: MessageSendIn,
    user: CurrentUser,
    db: DbSession,
) -> StreamingResponse:
    # Kiểm tra quyền, giành khoá phiên và ghi DB TRƯỚC khi mở stream: lỗi 403/404/409 trả JSON chuẩn
    ctx = await chat_service.start_turn(
        user_id=user.id,
        thread_id=thread_id,
        content=data.content,
        model=data.model,
    )
    return StreamingResponse(chat_service.stream_turn(ctx), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/threads/{thread_id}/stop", summary="Dừng lượt trả lời đang chạy")
async def stop_turn(
    thread_id: int,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    return await chat_service.stop_thread(db, user, thread_id)


@router.post("/messages/{message_id}/regenerate", summary="Tạo lại phản hồi cho tin nhắn")
async def regenerate_message(
    message_id: int,
    user: CurrentUser,
    db: DbSession,
) -> StreamingResponse:
    msg = db.get(AiMessage, message_id)
    if not msg:
        raise NotFound("Không tìm thấy tin nhắn cần tạo lại")

    thread = db.get(AiThread, msg.thread_id)
    if not thread or thread.user_id != user.id:
        raise PermissionDenied("Không có quyền truy cập phiên này")

    # Dùng lại câu hỏi gốc (không nhân đôi tin nhắn người dùng) và thay câu trả lời cuối cùng
    ctx = await chat_service.start_turn(
        user_id=user.id,
        thread_id=thread.id,
        content="",
        regenerate_message_id=message_id,
    )
    return StreamingResponse(chat_service.stream_turn(ctx), media_type="text/event-stream", headers=SSE_HEADERS)


# --- Actions (Proposals) ------------------------------------------------------

@router.get("/actions", response_model=list[AiActionOut], summary="Danh sách đề xuất thao tác")
def list_actions(
    user: CurrentUser,
    db: DbSession,
    thread_id: Annotated[int | None, Query(description="Lọc theo id phiên hội thoại")] = None,
    status: Annotated[AiActionStatus | None, Query(description="Lọc theo trạng thái đề xuất")] = None,
) -> list[AiActionOut]:
    actions = actions_service.list_actions(db, user, thread_id=thread_id, status=status)
    return [AiActionOut.model_validate(a) for a in actions]


@router.post("/actions/{action_id}/confirm", response_model=AiActionOut, summary="Xác nhận thực thi đề xuất")
def confirm_action(
    action_id: int,
    user: CurrentUser,
    db: DbSession,
    data: ActionConfirmIn | None = None,
) -> AiActionOut:
    args_override = data.args if data else None
    action = actions_service.confirm(db, user, action_id, args_override)
    return AiActionOut.model_validate(action)


@router.post("/actions/{action_id}/reject", response_model=AiActionOut, summary="Từ chối đề xuất")
def reject_action(
    action_id: int,
    user: CurrentUser,
    db: DbSession,
) -> AiActionOut:
    action = actions_service.reject(db, user, action_id)
    return AiActionOut.model_validate(action)


# --- Trạng thái AI ------------------------------------------------------------

@router.get("/status", response_model=AssistantStatusOut, summary="Trạng thái dịch vụ Trợ lý AI")
async def get_assistant_status(
    user: CurrentUser,
) -> AssistantStatusOut:
    runner_health = await chat_service.default_runner.health()
    is_ok = bool(runner_health.get("ok", False))
    rate_limited_for_s = int(runner_health.get("rate_limited_for_s") or 0)
    if not is_ok:
        last_error = runner_health.get("last_error")
    elif rate_limited_for_s > 0:
        # Không đưa log thô của nhà cung cấp ra giao diện — chỉ thông báo trung thực, dễ hiểu.
        minutes = max(1, round(rate_limited_for_s / 60))
        last_error = f"Dịch vụ AI đang hết hạn mức sử dụng, thử lại sau khoảng {minutes} phút."
    else:
        last_error = None
    return AssistantStatusOut(
        available=is_ok and rate_limited_for_s == 0,
        runner={
            "ok": is_ok,
            "version": runner_health.get("opencode_version"),
            "model": runner_health.get("model"),
        },
        last_error=last_error,
        queue_length=int(runner_health.get("queue_length", 0)),
        rate_limited_for_s=rate_limited_for_s,
    )
